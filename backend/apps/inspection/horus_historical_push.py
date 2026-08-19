"""
Serviço de recepção do histórico Horus via push HTTPS.

Fluxo por registro:
  1. Valida source_type = DAILY, taxonomy_era = ERA_C,
     2023-01-01 ≤ reference_date ≤ 2026-08-09
  2. Localiza (ou cria) o lote técnico pelo SHA-256 do arquivo exportado
  3. transaction.atomic + SELECT FOR UPDATE no lote
  4. Procura registro existente pela chave natural
     (reference_date, team, DAILY, ERA_C)
     ├─ não existe → CREATE → "created"   (HTTP 201)
     ├─ igual      → "already_exists"     (HTTP 200)
     └─ diferente  → "conflict"           (HTTP 409 — sem gravação silenciosa)
"""

from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.inspection.models import (
    HISTORICAL_CUTOFF_DATE,
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalImportBatch,
    InspectionHistoricalStatistic,
)


PUSH_DATE_FROM = date(2023, 1, 1)
PUSH_DATE_TO = HISTORICAL_CUTOFF_DATE  # 2026-08-09

HISTORICAL_EXTENSION_2022_FROM = date(2022, 10, 3)
HISTORICAL_EXTENSION_2022_TO = date(2022, 12, 31)

MAINTENANCE_ACTION_STANDARD = "UPSERT_HISTORICAL"
MAINTENANCE_ACTION_IMPORT_2022 = "IMPORT_2022"
MAINTENANCE_ACTION_UPDATE_RAIN = "UPDATE_RAIN"

PUSH_SOURCE_TYPE = HistoricalSourceType.DAILY
PUSH_TAXONOMY_ERA = HistoricalTaxonomyEra.ERA_C

# Nome técnico do arquivo de lote criado pelo push HTTPS
PUSH_BATCH_FILE_NAME = "HORUS_PUSH_HTTPS"

# Campos numéricos que são copiados do payload para o model.
# A igualdade é verificada apenas nestes campos (rastreabilidade de conflito).
NUMERIC_FIELD_MAP = {
    # payload_key: model_field
    "approach": "historical_approached",
    "reconductor": "reconductor",
    "refusal": "refusal",
    "fined": "fined",
    "towed": "towed",
    "cnh_collected": "cnh_collected",
    "four_ml": "four_ml",
    "thirtythree_ml": "thirtythree_ml",
    "thirtyfour_ml": "thirtyfour_ml",
    "passive_tests_performed": "passive_tests_performed",
    "removal_resolutions": "removal_resolutions",
    "arrests_means_evidence": "arrests_means_evidence",
    "art307": "historical_art_307",
    "criminal_occurrences": "criminal_occurrences",
    "driving_canceled_license": "driving_canceled_license",
    "reports_count": None,           # armazenado em source_row (veja abaixo)
    "operations_count": "operations_count",
}


class HorusHistoricalPushError(Exception):
    """Erro de validação de entrada — resulta em HTTP 400."""


class HorusHistoricalPushConflict(Exception):
    """Registro já existe com dados diferentes — resulta em HTTP 409."""

    def __init__(self, message: str, existing_id: int, differences: dict):
        super().__init__(message)
        self.existing_id = existing_id
        self.differences = differences


def _validate_payload(data: dict) -> dict:
    """
    Valida os campos obrigatórios do payload e retorna um dict limpo.
    Lança HorusHistoricalPushError em caso de falha.
    """
    errors = []

    # source_type
    if data.get("source_type") != PUSH_SOURCE_TYPE:
        errors.append(
            f"source_type deve ser '{PUSH_SOURCE_TYPE}'; "
            f"recebido: '{data.get('source_type')}'."
        )

    # taxonomy_era
    if data.get("taxonomy_era") != PUSH_TAXONOMY_ERA:
        errors.append(
            f"taxonomy_era deve ser '{PUSH_TAXONOMY_ERA}'; "
            f"recebido: '{data.get('taxonomy_era')}'."
        )

    # reference_date
    raw_date = data.get("reference_date")
    reference_date = None
    if not raw_date:
        errors.append("reference_date é obrigatório.")
    else:
        try:
            reference_date = date.fromisoformat(str(raw_date))
        except (TypeError, ValueError):
            errors.append(
                f"reference_date inválida: '{raw_date}'. "
                "Use o formato YYYY-MM-DD."
            )

    if reference_date is not None:
        if reference_date < PUSH_DATE_FROM:
            errors.append(
                f"reference_date {reference_date} anterior ao limite "
                f"{PUSH_DATE_FROM}."
            )
        if reference_date > PUSH_DATE_TO:
            errors.append(
                f"reference_date {reference_date} posterior ao corte "
                f"histórico {PUSH_DATE_TO}."
            )

    # team
    team = str(data.get("team") or "").strip().upper()
    if not team:
        errors.append("team não pode ser vazio.")

    if errors:
        raise HorusHistoricalPushError(
            "Validação falhou: " + " | ".join(errors)
        )

    return {
        "reference_date": reference_date,
        "team": team,
        "source_row": int(data.get("source_row") or 0),
        "reports_count": int(data.get("reports_count") or 0),
        "operations_count": data.get("operations_count"),
        "approach": data.get("approach"),
        "reconductor": data.get("reconductor"),
        "refusal": data.get("refusal"),
        "fined": data.get("fined"),
        "towed": data.get("towed"),
        "cnh_collected": data.get("cnh_collected"),
        "four_ml": data.get("four_ml"),
        "thirtythree_ml": data.get("thirtythree_ml"),
        "thirtyfour_ml": data.get("thirtyfour_ml"),
        "passive_tests_performed": data.get("passive_tests_performed"),
        "removal_resolutions": data.get("removal_resolutions"),
        "arrests_means_evidence": data.get("arrests_means_evidence"),
        "art307": data.get("art307"),
        "criminal_occurrences": data.get("criminal_occurrences"),
        "driving_canceled_license": data.get("driving_canceled_license"),
    }


def _find_or_create_batch(sha256: str) -> InspectionHistoricalImportBatch:
    """
    Localiza o lote técnico pelo SHA-256 do arquivo exportado.
    Se não existir ainda, cria-o com status PENDING.
    O SHA-256 identifica unicamente a extração do Horus.
    """
    batch, _created = (
        InspectionHistoricalImportBatch.objects.get_or_create(
            source_file_sha256=sha256,
            source_type=PUSH_SOURCE_TYPE,
            taxonomy_era=PUSH_TAXONOMY_ERA,
            defaults={
                "source_file_name": PUSH_BATCH_FILE_NAME,
                "source_file_size": 0,
                "status": InspectionHistoricalImportBatch.Status.PENDING,
                "started_at": timezone.now(),
                "rows_found": 0,
                "rows_valid": 0,
                "rows_imported": 0,
                "rows_ignored": 0,
                "errors_count": 0,
                "warnings_count": 0,
            },
        )
    )
    return batch


def _stat_fingerprint(stat: InspectionHistoricalStatistic) -> dict:
    """Retorna os campos comparáveis de um registro existente."""
    return {
        "historical_approached": stat.historical_approached,
        "reconductor": stat.reconductor,
        "refusal": stat.refusal,
        "fined": stat.fined,
        "towed": stat.towed,
        "cnh_collected": stat.cnh_collected,
        "four_ml": stat.four_ml,
        "thirtythree_ml": stat.thirtythree_ml,
        "thirtyfour_ml": stat.thirtyfour_ml,
        "passive_tests_performed": stat.passive_tests_performed,
        "removal_resolutions": stat.removal_resolutions,
        "arrests_means_evidence": stat.arrests_means_evidence,
        "historical_art_307": stat.historical_art_307,
        "criminal_occurrences": stat.criminal_occurrences,
        "driving_canceled_license": stat.driving_canceled_license,
        "operations_count": stat.operations_count,
    }


def _payload_fingerprint(cleaned: dict) -> dict:
    """Retorna os campos comparáveis do payload recebido."""
    return {
        "historical_approached": cleaned["approach"],
        "reconductor": cleaned["reconductor"],
        "refusal": cleaned["refusal"],
        "fined": cleaned["fined"],
        "towed": cleaned["towed"],
        "cnh_collected": cleaned["cnh_collected"],
        "four_ml": cleaned["four_ml"],
        "thirtythree_ml": cleaned["thirtythree_ml"],
        "thirtyfour_ml": cleaned["thirtyfour_ml"],
        "passive_tests_performed": cleaned["passive_tests_performed"],
        "removal_resolutions": cleaned["removal_resolutions"],
        "arrests_means_evidence": cleaned["arrests_means_evidence"],
        "historical_art_307": cleaned["art307"],
        "criminal_occurrences": cleaned["criminal_occurrences"],
        "driving_canceled_license": cleaned["driving_canceled_license"],
        "operations_count": cleaned["operations_count"],
    }


def _detect_differences(existing_fp: dict, incoming_fp: dict) -> dict:
    """Retorna dict com os campos que diferem entre existente e novo."""
    diffs = {}
    for key in existing_fp:
        ev = existing_fp[key]
        iv = incoming_fp.get(key)
        if ev != iv:
            diffs[key] = {"existing": ev, "incoming": iv}
    return diffs


class HorusHistoricalPushService:
    """
    Serviço que persiste um único registro histórico do Horus
    recebido via push HTTPS.
    """

    def push_single(
        self,
        data: dict,
        *,
        file_sha256: str,
        workbook_label: str = PUSH_BATCH_FILE_NAME,
    ) -> dict:
        """
        Parâmetros
        ----------
        data : dict
            Payload de um único registro do array ``rows`` do JSON exportado.
        file_sha256 : str
            SHA-256 do arquivo JSON exportado (rastreabilidade do lote).
        workbook_label : str
            Rótulo para o campo source_workbook_label (default: HORUS_PUSH_HTTPS).

        Retorno
        -------
        dict com:
            result        : "created" | "already_exists" | (lança exception em conflict)
            id            : id do InspectionHistoricalStatistic
            reference_date: str YYYY-MM-DD
            team          : str
            batch_id      : int
        """
        # Passo 1: validação de entrada
        cleaned = _validate_payload(data)

        # Passo 2: lote pelo SHA-256
        batch = _find_or_create_batch(file_sha256)

        # Passo 3: gravação atômica com lock no lote
        with transaction.atomic():
            # Lock do lote para evitar race condition entre instâncias paralelas
            locked_batch = (
                InspectionHistoricalImportBatch.objects
                .select_for_update()
                .get(pk=batch.pk)
            )

            # Passo 4: busca pela chave natural
            existing = (
                InspectionHistoricalStatistic.objects
                .filter(
                    reference_date=cleaned["reference_date"],
                    team=cleaned["team"],
                    source_type=PUSH_SOURCE_TYPE,
                    taxonomy_era=PUSH_TAXONOMY_ERA,
                )
                .first()
            )

            if existing is not None:
                # Compara fingerprint
                existing_fp = _stat_fingerprint(existing)
                incoming_fp = _payload_fingerprint(cleaned)
                diffs = _detect_differences(existing_fp, incoming_fp)

                if diffs:
                    raise HorusHistoricalPushConflict(
                        f"Conflito para {cleaned['reference_date']} / "
                        f"{cleaned['team']}: "
                        f"{len(diffs)} campo(s) divergente(s).",
                        existing_id=existing.pk,
                        differences=diffs,
                    )

                # Igual — idempotente
                return {
                    "result": "already_exists",
                    "id": existing.pk,
                    "reference_date": cleaned["reference_date"].isoformat(),
                    "team": cleaned["team"],
                    "batch_id": locked_batch.pk,
                }

            # Não existe → cria
            stat = InspectionHistoricalStatistic(
                reference_date=cleaned["reference_date"],
                reference_year=cleaned["reference_date"].year,
                reference_month=cleaned["reference_date"].month,
                team=cleaned["team"],
                source_team_label=cleaned["team"],
                source_type=PUSH_SOURCE_TYPE,
                taxonomy_era=PUSH_TAXONOMY_ERA,
                import_batch=locked_batch,
                source_sheet="HORUS",
                source_row=cleaned["source_row"],
                source_workbook_label=workbook_label,
                notes=(
                    "Fonte oficial Horus; "
                    "push via HTTPS; "
                    "consolidado por data e equipe."
                ),
                # Campos de dados
                historical_approached=cleaned["approach"],
                reconductor=cleaned["reconductor"],
                refusal=cleaned["refusal"],
                fined=cleaned["fined"],
                towed=cleaned["towed"],
                cnh_collected=cleaned["cnh_collected"],
                four_ml=cleaned["four_ml"],
                thirtythree_ml=cleaned["thirtythree_ml"],
                thirtyfour_ml=cleaned["thirtyfour_ml"],
                passive_tests_performed=cleaned["passive_tests_performed"],
                removal_resolutions=cleaned["removal_resolutions"],
                arrests_means_evidence=cleaned["arrests_means_evidence"],
                historical_art_307=cleaned["art307"],
                criminal_occurrences=cleaned["criminal_occurrences"],
                driving_canceled_license=cleaned["driving_canceled_license"],
                operations_count=cleaned["operations_count"],
                historical_operations=cleaned["operations_count"],
            )
            # full_clean() + save() — garante CheckConstraint do model
            stat.save()

            # Atualiza contador do lote
            locked_batch.rows_imported += 1
            locked_batch.save(update_fields=["rows_imported"])

        return {
            "result": "created",
            "id": stat.pk,
            "reference_date": cleaned["reference_date"].isoformat(),
            "team": cleaned["team"],
            "batch_id": locked_batch.pk,
        }

def _validate_maintenance_common(
    data: dict,
    *,
    date_from: date,
    date_to: date,
    require_rain: bool = True,
) -> dict:
    """
    Valida payloads das operações técnicas de manutenção histórica.

    Regras invariáveis:
    - somente DAILY / ERA_C;
    - data dentro do intervalo explicitamente permitido;
    - equipe obrigatória;
    - rain inteiro não negativo quando exigido.
    """
    errors = []

    if data.get("source_type") != PUSH_SOURCE_TYPE:
        errors.append(
            f"source_type deve ser '{PUSH_SOURCE_TYPE}'; "
            f"recebido: '{data.get('source_type')}'."
        )

    if data.get("taxonomy_era") != PUSH_TAXONOMY_ERA:
        errors.append(
            f"taxonomy_era deve ser '{PUSH_TAXONOMY_ERA}'; "
            f"recebido: '{data.get('taxonomy_era')}'."
        )

    raw_date = data.get("reference_date")
    reference_date = None

    if not raw_date:
        errors.append("reference_date é obrigatório.")
    else:
        try:
            if isinstance(raw_date, date):
                reference_date = raw_date
            else:
                reference_date = date.fromisoformat(str(raw_date))
        except (TypeError, ValueError):
            errors.append(
                f"reference_date inválida: '{raw_date}'. "
                "Use o formato YYYY-MM-DD."
            )

    if reference_date is not None:
        if reference_date < date_from or reference_date > date_to:
            errors.append(
                f"reference_date {reference_date} fora do intervalo "
                f"permitido {date_from} a {date_to}."
            )

    team = str(data.get("team") or "").strip().upper()
    if not team:
        errors.append("team não pode ser vazio.")

    rain = data.get("rain")
    if require_rain:
        if rain is None:
            errors.append("rain é obrigatório.")
        else:
            try:
                rain = int(rain)
            except (TypeError, ValueError):
                errors.append("rain deve ser um inteiro não negativo.")
            else:
                if rain < 0:
                    errors.append("rain deve ser um inteiro não negativo.")

    if errors:
        raise HorusHistoricalPushError(
            "Validação falhou: " + " | ".join(errors)
        )

    return {
        "reference_date": reference_date,
        "team": team,
        "source_row": int(data.get("source_row") or 0),
        "reports_count": int(data.get("reports_count") or 0),
        "operations_count": data.get("operations_count"),
        "rain": rain,
        "approach": data.get("approach"),
        "reconductor": data.get("reconductor"),
        "refusal": data.get("refusal"),
        "fined": data.get("fined"),
        "towed": data.get("towed"),
        "cnh_collected": data.get("cnh_collected"),
        "four_ml": data.get("four_ml"),
        "thirtythree_ml": data.get("thirtythree_ml"),
        "thirtyfour_ml": data.get("thirtyfour_ml"),
        "passive_tests_performed": data.get("passive_tests_performed"),
        "removal_resolutions": data.get("removal_resolutions"),
        "arrests_means_evidence": data.get("arrests_means_evidence"),
        "art307": data.get("art307"),
        "criminal_occurrences": data.get("criminal_occurrences"),
        "driving_canceled_license": data.get("driving_canceled_license"),
    }


def _maintenance_fingerprint(cleaned: dict) -> dict:
    """
    Fingerprint usado apenas para a extensão de 2022.

    Inclui rain para garantir idempotência integral do registro criado.
    """
    return {
        **_payload_fingerprint(cleaned),
        "rain": cleaned["rain"],
    }


def _existing_maintenance_fingerprint(
    stat: InspectionHistoricalStatistic,
) -> dict:
    return {
        **_stat_fingerprint(stat),
        "rain": stat.rain,
    }


class HorusHistorical2022PushService:
    """
    Cria exclusivamente a extensão DAILY / ERA_C de 03/10/2022 a 31/12/2022.

    Registros existentes nunca são sobrescritos:
    - iguais: already_exists;
    - diferentes: conflito 409.
    """

    def push_single(
        self,
        data: dict,
        *,
        file_sha256: str,
        workbook_label: str = "HORUS_PUSH_HTTPS_2022",
    ) -> dict:
        cleaned = _validate_maintenance_common(
            data,
            date_from=HISTORICAL_EXTENSION_2022_FROM,
            date_to=HISTORICAL_EXTENSION_2022_TO,
            require_rain=True,
        )

        batch = _find_or_create_batch(file_sha256)

        with transaction.atomic():
            locked_batch = (
                InspectionHistoricalImportBatch.objects
                .select_for_update()
                .get(pk=batch.pk)
            )

            existing = (
                InspectionHistoricalStatistic.objects
                .select_for_update()
                .filter(
                    reference_date=cleaned["reference_date"],
                    team=cleaned["team"],
                    source_type=PUSH_SOURCE_TYPE,
                    taxonomy_era=PUSH_TAXONOMY_ERA,
                )
                .first()
            )

            if existing is not None:
                existing_fp = _existing_maintenance_fingerprint(
                    existing
                )
                incoming_fp = _maintenance_fingerprint(
                    cleaned
                )
                diffs = _detect_differences(
                    existing_fp,
                    incoming_fp,
                )

                if diffs:
                    raise HorusHistoricalPushConflict(
                        f"Conflito para {cleaned['reference_date']} / "
                        f"{cleaned['team']}: "
                        f"{len(diffs)} campo(s) divergente(s).",
                        existing_id=existing.pk,
                        differences=diffs,
                    )

                return {
                    "result": "already_exists",
                    "id": existing.pk,
                    "reference_date": (
                        cleaned["reference_date"].isoformat()
                    ),
                    "team": cleaned["team"],
                    "batch_id": locked_batch.pk,
                }

            stat = InspectionHistoricalStatistic(
                reference_date=cleaned["reference_date"],
                reference_year=cleaned["reference_date"].year,
                reference_month=cleaned["reference_date"].month,
                team=cleaned["team"],
                source_team_label=cleaned["team"],
                source_type=PUSH_SOURCE_TYPE,
                taxonomy_era=PUSH_TAXONOMY_ERA,
                import_batch=locked_batch,
                source_sheet="HORUS",
                source_row=cleaned["source_row"],
                source_workbook_label=workbook_label,
                notes=(
                    "Fonte oficial Horus; extensão histórica de 2022; "
                    "push via HTTPS; consolidado por data e equipe."
                ),
                historical_approached=cleaned["approach"],
                reconductor=cleaned["reconductor"],
                refusal=cleaned["refusal"],
                fined=cleaned["fined"],
                towed=cleaned["towed"],
                cnh_collected=cleaned["cnh_collected"],
                four_ml=cleaned["four_ml"],
                thirtythree_ml=cleaned["thirtythree_ml"],
                thirtyfour_ml=cleaned["thirtyfour_ml"],
                passive_tests_performed=(
                    cleaned["passive_tests_performed"]
                ),
                removal_resolutions=cleaned["removal_resolutions"],
                arrests_means_evidence=(
                    cleaned["arrests_means_evidence"]
                ),
                historical_art_307=cleaned["art307"],
                criminal_occurrences=(
                    cleaned["criminal_occurrences"]
                ),
                driving_canceled_license=(
                    cleaned["driving_canceled_license"]
                ),
                operations_count=cleaned["operations_count"],
                historical_operations=cleaned["operations_count"],
                rain=cleaned["rain"],
            )

            stat.save()

            locked_batch.rows_imported += 1
            locked_batch.save(
                update_fields=["rows_imported"]
            )

        return {
            "result": "created",
            "id": stat.pk,
            "reference_date": (
                cleaned["reference_date"].isoformat()
            ),
            "team": cleaned["team"],
            "batch_id": locked_batch.pk,
        }


class HorusHistoricalRainUpdateService:
    """
    Atualiza exclusivamente InspectionHistoricalStatistic.rain.

    Nenhum outro campo histórico é alterado.
    O registro DAILY / ERA_C precisa existir previamente.
    """

    def update_single(self, data: dict) -> dict:
        cleaned = _validate_maintenance_common(
            data,
            date_from=HISTORICAL_EXTENSION_2022_FROM,
            date_to=HISTORICAL_CUTOFF_DATE,
            require_rain=True,
        )

        with transaction.atomic():
            existing = (
                InspectionHistoricalStatistic.objects
                .select_for_update()
                .filter(
                    reference_date=cleaned["reference_date"],
                    team=cleaned["team"],
                    source_type=PUSH_SOURCE_TYPE,
                    taxonomy_era=PUSH_TAXONOMY_ERA,
                    is_validation_only=False,
                )
                .first()
            )

            if existing is None:
                raise HorusHistoricalPushError(
                    "Registro histórico DAILY / ERA_C não encontrado "
                    f"para {cleaned['reference_date']} / "
                    f"{cleaned['team']}."
                )

            old_rain = existing.rain
            new_rain = cleaned["rain"]

            if old_rain == new_rain:
                return {
                    "result": "unchanged",
                    "id": existing.pk,
                    "reference_date": (
                        cleaned["reference_date"].isoformat()
                    ),
                    "team": cleaned["team"],
                    "rain": new_rain,
                }

            existing.rain = new_rain
            existing.save(
                update_fields=["rain"]
            )

        return {
            "result": "updated",
            "id": existing.pk,
            "reference_date": (
                cleaned["reference_date"].isoformat()
            ),
            "team": cleaned["team"],
            "old_rain": old_rain,
            "rain": new_rain,
        }
