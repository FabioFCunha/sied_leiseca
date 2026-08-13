"""
Testes do mecanismo de push histórico Horus → VPS.

Cobre:
  - InspectionHistoricalPushService (serviço puro)
  - InspectionHistoricalPushView (endpoint HTTP)
  - Comando push_horus_inspection_historical (--dry-run)

Casos testados:
  1. Criação bem-sucedida (201)
  2. Idempotência: reenvio idêntico retorna already_exists (200)
  3. Conflito: dados diferentes retornam 409 sem gravação silenciosa
  4. Validação: source_type errado → 400
  5. Validação: taxonomy_era errada → 400
  6. Validação: reference_date após 09/08/2026 → 400
  7. Validação: reference_date antes de 01/01/2023 → 400
  8. Validação: team vazio → 400
  9. Autenticação: token ausente → 403
  10. Autenticação: token errado → 403
  11. Lote: SHA-256 correto cria lote técnico único
  12. Lote: mesmo SHA-256 reutiliza lote existente
  13. Lote: rows_imported incrementa a cada criação
  14. Serviço: CheckConstraint do model é respeitado
  15. Comando: --dry-run sem send não grava
"""

import json
import tempfile
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.inspection.horus_historical_push import (
    PUSH_DATE_FROM,
    PUSH_DATE_TO,
    HorusHistoricalPushConflict,
    HorusHistoricalPushError,
    HorusHistoricalPushService,
)
from apps.inspection.models import (
    HISTORICAL_CUTOFF_DATE,
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalImportBatch,
    InspectionHistoricalStatistic,
)

VALID_TOKEN = "test-historical-push-token-abc123"
FAKE_SHA256 = "a" * 64


def _base_payload(**overrides):
    """Payload válido mínimo para o endpoint."""
    data = {
        "file_sha256": FAKE_SHA256,
        "source_type": "DAILY",
        "taxonomy_era": "ERA_C",
        "reference_date": "2023-01-15",
        "team": "A1",
        "source_row": 1,
        "reports_count": 3,
        "operations_count": 4,
        "approach": 210,
        "reconductor": 30,
        "refusal": 5,
        "fined": 12,
        "towed": 1,
        "cnh_collected": 0,
        "four_ml": 200,
        "thirtythree_ml": 0,
        "thirtyfour_ml": 0,
        "passive_tests_performed": 0,
        "removal_resolutions": 0,
        "arrests_means_evidence": 0,
        "art307": 0,
        "criminal_occurrences": 0,
        "driving_canceled_license": 0,
    }
    data.update(overrides)
    return data


def _service_payload(**overrides):
    """Payload válido mínimo para o serviço (sem file_sha256)."""
    data = {
        "source_type": "DAILY",
        "taxonomy_era": "ERA_C",
        "reference_date": "2023-01-15",
        "team": "A1",
        "source_row": 1,
        "reports_count": 3,
        "operations_count": 4,
        "approach": 210,
        "reconductor": 30,
        "refusal": 5,
        "fined": 12,
        "towed": 1,
        "cnh_collected": None,
        "four_ml": 200,
        "thirtythree_ml": None,
        "thirtyfour_ml": None,
        "passive_tests_performed": None,
        "removal_resolutions": None,
        "arrests_means_evidence": None,
        "art307": None,
        "criminal_occurrences": None,
        "driving_canceled_license": None,
    }
    data.update(overrides)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Testes do Serviço (sem HTTP)
# ─────────────────────────────────────────────────────────────────────────────


class HorusHistoricalPushServiceTests(TestCase):
    def setUp(self):
        self.service = HorusHistoricalPushService()

    # Caso 1 — Criação bem-sucedida
    def test_push_single_creates_record(self):
        data = _service_payload()
        result = self.service.push_single(data, file_sha256=FAKE_SHA256)

        self.assertEqual(result["result"], "created")
        self.assertIn("id", result)
        self.assertEqual(result["reference_date"], "2023-01-15")
        self.assertEqual(result["team"], "A1")

        stat = InspectionHistoricalStatistic.objects.get(pk=result["id"])
        self.assertEqual(stat.source_type, HistoricalSourceType.DAILY)
        self.assertEqual(stat.taxonomy_era, HistoricalTaxonomyEra.ERA_C)
        self.assertEqual(stat.historical_approached, 210)
        self.assertEqual(stat.reconductor, 30)

    # Caso 2 — Idempotência: reenvio idêntico
    def test_push_single_idempotent_same_data(self):
        data = _service_payload()
        result1 = self.service.push_single(data, file_sha256=FAKE_SHA256)
        result2 = self.service.push_single(data, file_sha256=FAKE_SHA256)

        self.assertEqual(result1["result"], "created")
        self.assertEqual(result2["result"], "already_exists")
        self.assertEqual(result1["id"], result2["id"])

        # Apenas 1 registro no banco
        self.assertEqual(
            InspectionHistoricalStatistic.objects.filter(
                reference_date=date(2023, 1, 15),
                team="A1",
                source_type=HistoricalSourceType.DAILY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            ).count(),
            1,
        )

    # Caso 3 — Conflito: dados diferentes
    def test_push_single_conflict_raises_exception(self):
        data = _service_payload()
        self.service.push_single(data, file_sha256=FAKE_SHA256)

        modified = _service_payload(approach=999)  # valor diferente
        with self.assertRaises(HorusHistoricalPushConflict) as ctx:
            self.service.push_single(modified, file_sha256=FAKE_SHA256)

        exc = ctx.exception
        self.assertIn("historical_approached", exc.differences)
        self.assertEqual(exc.differences["historical_approached"]["existing"], 210)
        self.assertEqual(exc.differences["historical_approached"]["incoming"], 999)

        # Garantia: o registro original NÃO foi alterado
        stat = InspectionHistoricalStatistic.objects.get(pk=exc.existing_id)
        self.assertEqual(stat.historical_approached, 210)

    # Caso 11 — Lote criado pelo SHA-256
    def test_batch_created_by_sha256(self):
        data = _service_payload()
        result = self.service.push_single(data, file_sha256=FAKE_SHA256)

        batch = InspectionHistoricalImportBatch.objects.get(
            pk=result["batch_id"]
        )
        self.assertEqual(batch.source_file_sha256, FAKE_SHA256)
        self.assertEqual(batch.source_type, HistoricalSourceType.DAILY)
        self.assertEqual(batch.taxonomy_era, HistoricalTaxonomyEra.ERA_C)

    # Caso 12 — Mesmo SHA-256 reutiliza lote
    def test_same_sha256_reuses_batch(self):
        data1 = _service_payload(reference_date="2023-01-15", team="A1", source_row=1)
        data2 = _service_payload(reference_date="2023-01-16", team="A2", source_row=2)

        r1 = self.service.push_single(data1, file_sha256=FAKE_SHA256)
        r2 = self.service.push_single(data2, file_sha256=FAKE_SHA256)

        self.assertEqual(r1["batch_id"], r2["batch_id"])
        self.assertEqual(
            InspectionHistoricalImportBatch.objects.filter(
                source_file_sha256=FAKE_SHA256
            ).count(),
            1,
        )

    # Caso 13 — rows_imported incrementa
    def test_batch_rows_imported_increments(self):
        data1 = _service_payload(reference_date="2023-01-15", team="A1", source_row=1)
        data2 = _service_payload(reference_date="2023-01-16", team="A2", source_row=2)

        self.service.push_single(data1, file_sha256=FAKE_SHA256)
        self.service.push_single(data2, file_sha256=FAKE_SHA256)

        batch = InspectionHistoricalImportBatch.objects.get(
            source_file_sha256=FAKE_SHA256
        )
        self.assertEqual(batch.rows_imported, 2)

    # Caso 14 — CheckConstraint do model
    def test_service_rejects_date_after_cutoff_via_model(self):
        forbidden_date = HISTORICAL_CUTOFF_DATE + timedelta(days=1)
        data = _service_payload(reference_date=forbidden_date.isoformat())
        with self.assertRaises(HorusHistoricalPushError):
            self.service.push_single(data, file_sha256=FAKE_SHA256)

    # Validação: source_type errado
    def test_service_rejects_wrong_source_type(self):
        data = _service_payload(source_type="LEGACY")
        with self.assertRaises(HorusHistoricalPushError) as ctx:
            self.service.push_single(data, file_sha256=FAKE_SHA256)
        self.assertIn("source_type", str(ctx.exception))

    # Validação: taxonomy_era errada
    def test_service_rejects_wrong_taxonomy_era(self):
        data = _service_payload(taxonomy_era="ERA_A")
        with self.assertRaises(HorusHistoricalPushError) as ctx:
            self.service.push_single(data, file_sha256=FAKE_SHA256)
        self.assertIn("taxonomy_era", str(ctx.exception))

    # Validação: data anterior ao limite
    def test_service_rejects_date_before_range(self):
        data = _service_payload(reference_date="2022-12-31")
        with self.assertRaises(HorusHistoricalPushError) as ctx:
            self.service.push_single(data, file_sha256=FAKE_SHA256)
        self.assertIn("2023-01-01", str(ctx.exception))

    # Validação: team vazio
    def test_service_rejects_empty_team(self):
        data = _service_payload(team="")
        with self.assertRaises(HorusHistoricalPushError) as ctx:
            self.service.push_single(data, file_sha256=FAKE_SHA256)
        self.assertIn("team", str(ctx.exception))

    # Normalização: team em minúsculas é normalizado para uppercase
    def test_service_normalizes_team_to_uppercase(self):
        data = _service_payload(team="a1")
        result = self.service.push_single(data, file_sha256=FAKE_SHA256)
        stat = InspectionHistoricalStatistic.objects.get(pk=result["id"])
        self.assertEqual(stat.team, "A1")

    # Corte: data exata do cutoff (2026-08-09) deve ser aceita
    def test_service_accepts_cutoff_date(self):
        data = _service_payload(
            reference_date=PUSH_DATE_TO.isoformat(),
            team="B1",
            source_row=999,
        )
        result = self.service.push_single(data, file_sha256=FAKE_SHA256)
        self.assertEqual(result["result"], "created")

    # Corte: data inicial exata (2023-01-01) deve ser aceita
    def test_service_accepts_start_date(self):
        data = _service_payload(
            reference_date=PUSH_DATE_FROM.isoformat(),
            team="C1",
            source_row=1,
        )
        result = self.service.push_single(data, file_sha256=FAKE_SHA256)
        self.assertEqual(result["result"], "created")


# ─────────────────────────────────────────────────────────────────────────────
# Testes do Endpoint HTTP
# ─────────────────────────────────────────────────────────────────────────────


@override_settings(INSPECTION_SYNC_TOKEN=VALID_TOKEN)
class InspectionHistoricalPushViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("inspection_sync_historical_push")

    def _post(self, payload, token=VALID_TOKEN):
        headers = {}
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    # Caso 1 — 201 Created
    def test_post_creates_record_returns_201(self):
        response = self._post(_base_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["result"], "created")
        self.assertIn("id", body)
        self.assertEqual(body["reference_date"], "2023-01-15")
        self.assertEqual(body["team"], "A1")

    # Caso 2 — 200 already_exists
    def test_post_idempotent_returns_200(self):
        self._post(_base_payload())
        response = self._post(_base_payload())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["result"], "already_exists")

        # Apenas 1 registro no banco
        self.assertEqual(
            InspectionHistoricalStatistic.objects.filter(
                reference_date=date(2023, 1, 15),
                team="A1",
            ).count(),
            1,
        )

    # Caso 3 — 409 Conflict
    def test_post_conflict_returns_409_no_silent_update(self):
        self._post(_base_payload())
        response = self._post(_base_payload(approach=9999))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        body = response.json()
        self.assertEqual(body["result"], "conflict")
        self.assertIn("differences", body)
        self.assertIn("historical_approached", body["differences"])

        # O registro original NÃO foi alterado
        stat = InspectionHistoricalStatistic.objects.get(
            reference_date=date(2023, 1, 15),
            team="A1",
        )
        self.assertEqual(stat.historical_approached, 210)

    # Caso 4 — 400 source_type inválido
    def test_post_invalid_source_type_returns_400(self):
        response = self._post(_base_payload(source_type="LEGACY"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Caso 5 — 400 taxonomy_era inválida
    def test_post_invalid_taxonomy_era_returns_400(self):
        response = self._post(_base_payload(taxonomy_era="ERA_A"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Caso 6 — 400 data posterior ao corte
    def test_post_date_after_cutoff_returns_400(self):
        forbidden = (HISTORICAL_CUTOFF_DATE + timedelta(days=1)).isoformat()
        response = self._post(_base_payload(reference_date=forbidden))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Caso 7 — 400 data anterior ao início
    def test_post_date_before_start_returns_400(self):
        response = self._post(_base_payload(reference_date="2022-12-31"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Caso 8 — 400 team vazio
    def test_post_empty_team_returns_400(self):
        response = self._post(_base_payload(team=""))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Caso 9 — 403 sem token
    def test_post_without_token_returns_403(self):
        response = self.client.post(
            self.url,
            data=json.dumps(_base_payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Caso 10 — 403 token errado
    def test_post_wrong_token_returns_403(self):
        response = self._post(_base_payload(), token="token-errado")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Caso 11 — Lote criado pelo SHA-256
    def test_post_creates_batch_by_sha256(self):
        response = self._post(_base_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        batch_id = response.json()["batch_id"]

        batch = InspectionHistoricalImportBatch.objects.get(pk=batch_id)
        self.assertEqual(batch.source_file_sha256, FAKE_SHA256)
        self.assertEqual(batch.source_type, HistoricalSourceType.DAILY)
        self.assertEqual(batch.taxonomy_era, HistoricalTaxonomyEra.ERA_C)

    # Validação: SHA-256 inválido (não hexadecimal)
    def test_post_invalid_sha256_returns_400(self):
        response = self._post(_base_payload(file_sha256="invalid-sha"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Validação: SHA-256 comprimento errado
    def test_post_wrong_length_sha256_returns_400(self):
        response = self._post(_base_payload(file_sha256="a" * 32))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Dois registros diferentes no mesmo dia → dois creates distintos
    def test_post_two_teams_same_date_creates_two_records(self):
        payload_a1 = _base_payload(team="A1", source_row=1)
        payload_b1 = _base_payload(team="B1", source_row=2)

        r1 = self._post(payload_a1)
        r2 = self._post(payload_b1)

        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(r1.json()["id"], r2.json()["id"])

        self.assertEqual(
            InspectionHistoricalStatistic.objects.filter(
                reference_date=date(2023, 1, 15)
            ).count(),
            2,
        )

    # LEGACY / ERA_A existente não é tocado
    def test_post_does_not_affect_legacy_era_a_records(self):
        from apps.inspection.models import InspectionHistoricalImportBatch

        # Cria um lote LEGACY / ERA_A manualmente
        from django.utils import timezone

        legacy_batch = InspectionHistoricalImportBatch.objects.create(
            source_file_name="legacy.xlsx",
            source_file_sha256="b" * 64,
            source_file_size=1024,
            source_type=HistoricalSourceType.LEGACY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_A,
            status=InspectionHistoricalImportBatch.Status.COMPLETED,
            started_at=timezone.now(),
            rows_imported=1,
        )
        legacy_stat = InspectionHistoricalStatistic.objects.create(
            reference_year=2020,
            reference_month=6,
            team="A1",
            source_type=HistoricalSourceType.LEGACY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_A,
            import_batch=legacy_batch,
            source_sheet="legado",
            source_row=1,
        )

        # Push de um registro DAILY/ERA_C
        response = self._post(_base_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # LEGACY não foi tocado
        self.assertEqual(
            InspectionHistoricalStatistic.objects.filter(
                source_type=HistoricalSourceType.LEGACY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_A,
            ).count(),
            1,
        )
        legacy_stat.refresh_from_db()
        self.assertEqual(legacy_stat.team, "A1")


# ─────────────────────────────────────────────────────────────────────────────
# Testes do Comando de Gerenciamento (--dry-run)
# ─────────────────────────────────────────────────────────────────────────────


class PushHorusInspectionHistoricalCommandDryRunTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _make_json(self, rows=None, *, name="horus_historical.json"):
        if rows is None:
            rows = [
                {
                    "reference_date": "2023-01-15",
                    "team": "A1",
                    "source_type": "DAILY",
                    "taxonomy_era": "ERA_C",
                    "source_row": 1,
                    "reports_count": 3,
                    "operations_count": 4,
                    "approach": 210,
                    "reconductor": 30,
                    "refusal": 5,
                    "fined": 12,
                    "towed": 1,
                    "cnh_collected": None,
                    "four_ml": 200,
                    "thirtythree_ml": None,
                    "thirtyfour_ml": None,
                    "passive_tests_performed": None,
                    "removal_resolutions": None,
                    "arrests_means_evidence": None,
                    "art307": None,
                    "criminal_occurrences": None,
                    "driving_canceled_license": None,
                    "reference_year": 2023,
                    "reference_month": 1,
                    "source_sheet": "HORUS",
                    "source_team_label": "A1",
                }
            ]

        payload = {
            "metadata": {
                "source": "HORUS",
                "source_type": "DAILY",
                "taxonomy_era": "ERA_C",
                "date_from": "2023-01-01",
                "date_to": "2026-08-09",
                "read_only_source": True,
                "granularity": "reference_date+team",
            },
            "summary": {
                "rows": len(rows),
                "reports": sum(r.get("reports_count", 0) for r in rows),
                "operations": sum(r.get("operations_count", 0) for r in rows),
                "teams": 1,
                "date_start": rows[0]["reference_date"] if rows else None,
                "date_end": rows[-1]["reference_date"] if rows else None,
            },
            "annual_controls": {},
            "teams": list({r["team"] for r in rows}),
            "rows": rows,
        }

        path = Path(self.temp_dir.name) / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(path)

    # Caso 15 — --dry-run não grava
    def test_dry_run_does_not_create_records(self):
        file_path = self._make_json()
        out = StringIO()

        call_command(
            "push_horus_inspection_historical",
            "--file",
            file_path,
            "--url",
            "https://sied-leiseca.online/api/inspection/sync/historical/push/",
            "--dry-run",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("DRY-RUN", output)
        self.assertIn("found", output)

        # Nenhum registro foi criado
        self.assertEqual(InspectionHistoricalStatistic.objects.count(), 0)
        self.assertEqual(InspectionHistoricalImportBatch.objects.count(), 0)

    # --send sem token deve lançar CommandError
    def test_send_without_token_raises_command_error(self):
        file_path = self._make_json()

        import unittest.mock as mock

        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "push_horus_inspection_historical",
                    "--file",
                    file_path,
                    "--url",
                    "https://sied-leiseca.online/api/inspection/sync/historical/push/",
                    "--send",
                )
        self.assertIn("token", str(ctx.exception).lower())

    # --dry-run e --send juntos devem lançar CommandError
    def test_dry_run_and_send_together_raises_command_error(self):
        file_path = self._make_json()

        with self.assertRaises(CommandError) as ctx:
            call_command(
                "push_horus_inspection_historical",
                "--file",
                file_path,
                "--url",
                "https://sied-leiseca.online/api/inspection/sync/historical/push/",
                "--dry-run",
                "--send",
            )
        self.assertIn("exatamente", str(ctx.exception).lower())

    # Arquivo JSON com metadados errados deve lançar CommandError
    def test_invalid_json_metadata_raises_command_error(self):
        payload = {
            "metadata": {
                "source": "HORUS",
                "source_type": "WRONG",  # inválido
                "taxonomy_era": "ERA_C",
                "date_from": "2023-01-01",
                "date_to": "2026-08-09",
            },
            "rows": [],
        }
        path = Path(self.temp_dir.name) / "bad.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(CommandError):
            call_command(
                "push_horus_inspection_historical",
                "--file",
                str(path),
                "--url",
                "https://sied-leiseca.online/api/inspection/sync/historical/push/",
                "--dry-run",
            )

    # --limit no dry-run mostra contagem correta
    def test_dry_run_with_limit_shows_correct_count(self):
        rows = [
            {
                "reference_date": f"2023-01-{day:02d}",
                "team": "A1",
                "source_type": "DAILY",
                "taxonomy_era": "ERA_C",
                "source_row": day,
                "reports_count": 1,
                "operations_count": 1,
                "approach": 10,
                "reconductor": 1,
                "refusal": 0,
                "fined": 0,
                "towed": 0,
                "reference_year": 2023,
                "reference_month": 1,
                "source_sheet": "HORUS",
                "source_team_label": "A1",
            }
            for day in range(1, 6)
        ]
        file_path = self._make_json(rows=rows)
        out = StringIO()

        call_command(
            "push_horus_inspection_historical",
            "--file",
            file_path,
            "--url",
            "https://sied-leiseca.online/api/inspection/sync/historical/push/",
            "--dry-run",
            "--limit",
            "2",
            stdout=out,
        )

        output = out.getvalue()
        # found deve mostrar o total (5), não o limit
        self.assertIn("5", output)
        # limit=2 deve estar na saída
        self.assertIn("2", output)
