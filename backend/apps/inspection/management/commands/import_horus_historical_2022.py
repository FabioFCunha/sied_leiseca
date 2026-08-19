import json
from datetime import date
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction
from django.utils import timezone

from apps.inspection.models import (
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalImportBatch,
    InspectionHistoricalStatistic,
)


DATE_FROM = date(2022, 10, 3)
DATE_TO = date(2022, 12, 31)

EXPECTED_ROWS = 856
EXPECTED_REPORTS = 896
EXPECTED_OPERATIONS = 1051
EXPECTED_RAIN = 207


class Command(BaseCommand):
    help = (
        "Importa exclusivamente a extensao historica "
        "DAILY / ERA_C do Horus de 03/10/2022 a "
        "31/12/2022, sem alterar registros posteriores."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="JSON historico completo exportado do Horus.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida sem gravar.",
        )

        parser.add_argument(
            "--apply",
            action="store_true",
            help="Grava exclusivamente os registros de 2022.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        apply = bool(options["apply"])

        if dry_run == apply:
            raise CommandError(
                "Informe exatamente um: --dry-run ou --apply."
            )

        path = Path(options["file"])

        if not path.exists():
            raise CommandError(
                f"Arquivo nao encontrado: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(
                f"Falha ao ler JSON: {exc}"
            ) from exc

        metadata = payload.get("metadata") or {}
        rows = payload.get("rows")

        if not isinstance(rows, list):
            raise CommandError(
                "Campo rows ausente ou invalido."
            )

        errors = []

        if metadata.get("source") != "HORUS":
            errors.append(
                "metadata.source deve ser HORUS."
            )

        if (
            metadata.get("source_type")
            != HistoricalSourceType.DAILY
        ):
            errors.append(
                "metadata.source_type deve ser DAILY."
            )

        if (
            metadata.get("taxonomy_era")
            != HistoricalTaxonomyEra.ERA_C
        ):
            errors.append(
                "metadata.taxonomy_era deve ser ERA_C."
            )

        if metadata.get("date_from") != "2022-10-03":
            errors.append(
                "metadata.date_from deve ser 2022-10-03."
            )

        if metadata.get("date_to") != "2026-08-09":
            errors.append(
                "metadata.date_to deve ser 2026-08-09."
            )

        if metadata.get("read_only_source") is not True:
            errors.append(
                "Arquivo nao declara origem read-only."
            )

        selected_rows = []
        seen_keys = set()

        for index, raw_row in enumerate(
            rows,
            start=1,
        ):
            if not isinstance(raw_row, dict):
                errors.append(
                    f"Linha {index}: formato invalido."
                )
                continue

            try:
                reference_date = date.fromisoformat(
                    raw_row["reference_date"]
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                errors.append(
                    f"Linha {index}: reference_date invalida."
                )
                continue

            if not (
                DATE_FROM
                <= reference_date
                <= DATE_TO
            ):
                continue

            team = str(
                raw_row.get("team") or ""
            ).strip()

            if not team:
                errors.append(
                    f"Linha {index}: equipe vazia."
                )
                continue

            key = (
                reference_date,
                team.upper(),
            )

            if key in seen_keys:
                errors.append(
                    f"Linha {index}: duplicidade "
                    f"data/equipe {key}."
                )
                continue

            seen_keys.add(key)

            if (
                raw_row.get("reference_year")
                != reference_date.year
            ):
                errors.append(
                    f"Linha {index}: "
                    "reference_year inconsistente."
                )

            if (
                raw_row.get("reference_month")
                != reference_date.month
            ):
                errors.append(
                    f"Linha {index}: "
                    "reference_month inconsistente."
                )

            selected_rows.append(
                {
                    **raw_row,
                    "_reference_date": reference_date,
                    "_team": team,
                    "_source_row": index,
                }
            )

        calculated_rows = len(selected_rows)

        calculated_reports = sum(
            int(
                row.get("reports_count") or 0
            )
            for row in selected_rows
        )

        calculated_operations = sum(
            int(
                row.get("operations_count") or 0
            )
            for row in selected_rows
        )

        calculated_rain = sum(
            int(
                row.get("rain") or 0
            )
            for row in selected_rows
        )

        if calculated_rows != EXPECTED_ROWS:
            errors.append(
                "Quantidade de linhas de 2022 divergente: "
                f"{calculated_rows} != {EXPECTED_ROWS}."
            )

        if calculated_reports != EXPECTED_REPORTS:
            errors.append(
                "Quantidade de relatorios de 2022 divergente: "
                f"{calculated_reports} != {EXPECTED_REPORTS}."
            )

        if calculated_operations != EXPECTED_OPERATIONS:
            errors.append(
                "Quantidade de operacoes de 2022 divergente: "
                f"{calculated_operations} "
                f"!= {EXPECTED_OPERATIONS}."
            )

        if calculated_rain != EXPECTED_RAIN:
            errors.append(
                "Quantidade de chuva de 2022 divergente: "
                f"{calculated_rain} != {EXPECTED_RAIN}."
            )

        existing_qs = (
            InspectionHistoricalStatistic.objects.filter(
                source_type=HistoricalSourceType.DAILY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_C,
                reference_date__gte=DATE_FROM,
                reference_date__lte=DATE_TO,
            )
        )

        existing_count = existing_qs.count()

        if existing_count:
            errors.append(
                f"Ja existem {existing_count} registros "
                "DAILY / ERA_C de 2022. "
                "Importacao recusada para evitar duplicidade."
            )

        self.stdout.write("=" * 80)
        self.stdout.write("EXTENSAO HISTORICA HORUS — 2022")
        self.stdout.write("=" * 80)

        self.stdout.write(
            f"Arquivo: {path.resolve()}"
        )
        self.stdout.write(
            f"Periodo selecionado: {DATE_FROM} a {DATE_TO}"
        )
        self.stdout.write(
            f"Linhas: {calculated_rows}"
        )
        self.stdout.write(
            f"Relatorios: {calculated_reports}"
        )
        self.stdout.write(
            f"Operacoes: {calculated_operations}"
        )
        self.stdout.write(
            f"Chuva: {calculated_rain}"
        )
        self.stdout.write(
            f"Ja existentes DAILY/ERA_C: {existing_count}"
        )

        if errors:
            self.stdout.write("")
            self.stdout.write("ERROS:")

            for error in errors:
                self.stdout.write(
                    f"- {error}"
                )

            raise CommandError(
                "Validacao da extensao historica "
                "de 2022 falhou."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Validacao de 2022 concluida sem erros."
            )
        )

        if dry_run:
            self.stdout.write(
                "DRY-RUN: nenhuma alteracao "
                "foi realizada."
            )
            return

        with transaction.atomic():
            batch = (
                InspectionHistoricalImportBatch.objects.create(
                    source_file_name=path.name,
                    source_file_sha256=(
                        "HORUS_2022_EXTENSION_"
                        + timezone.now().strftime(
                            "%Y%m%d%H%M%S%f"
                        )
                    ),
                    source_file_size=path.stat().st_size,
                    source_type=HistoricalSourceType.DAILY,
                    taxonomy_era=HistoricalTaxonomyEra.ERA_C,
                    status=(
                        InspectionHistoricalImportBatch
                        .Status.PENDING
                    ),
                    started_at=timezone.now(),
                    rows_found=calculated_rows,
                    rows_valid=calculated_rows,
                    rows_imported=0,
                    rows_ignored=0,
                    errors_count=0,
                    warnings_count=0,
                    report_json={
                        "extension": "HORUS_2022",
                        "date_from": DATE_FROM.isoformat(),
                        "date_to": DATE_TO.isoformat(),
                        "rows": calculated_rows,
                        "reports": calculated_reports,
                        "operations": calculated_operations,
                        "rain": calculated_rain,
                    },
                )
            )

            statistics = []

            for row in selected_rows:
                statistics.append(
                    InspectionHistoricalStatistic(
                        reference_date=row[
                            "_reference_date"
                        ],
                        reference_year=row[
                            "_reference_date"
                        ].year,
                        reference_month=row[
                            "_reference_date"
                        ].month,
                        team=row["_team"],
                        source_team_label=row["_team"],
                        source_type=(
                            HistoricalSourceType.DAILY
                        ),
                        source_sheet="HORUS",
                        source_row=row["_source_row"],
                        taxonomy_era=(
                            HistoricalTaxonomyEra.ERA_C
                        ),
                        import_batch=batch,
                        source_workbook_label=path.name,
                        notes=(
                            "Fonte oficial Horus; "
                            "extensao historica de 2022; "
                            "consolidado por data e equipe."
                        ),

                        historical_approached=(
                            row.get("approach")
                        ),
                        reconductor=(
                            row.get("reconductor")
                        ),
                        refusal=row.get("refusal"),
                        fined=row.get("fined"),
                        towed=row.get("towed"),
                        cnh_collected=(
                            row.get("cnh_collected")
                        ),
                        four_ml=row.get("four_ml"),
                        thirtythree_ml=(
                            row.get("thirtythree_ml")
                        ),
                        thirtyfour_ml=(
                            row.get("thirtyfour_ml")
                        ),
                        passive_tests_performed=(
                            row.get(
                                "passive_tests_performed"
                            )
                        ),
                        removal_resolutions=(
                            row.get(
                                "removal_resolutions"
                            )
                        ),
                        arrests_means_evidence=(
                            row.get(
                                "arrests_means_evidence"
                            )
                        ),
                        historical_art_307=(
                            row.get("art307")
                        ),
                        criminal_occurrences=(
                            row.get(
                                "criminal_occurrences"
                            )
                        ),
                        driving_canceled_license=(
                            row.get(
                                "driving_canceled_license"
                            )
                        ),
                        operations_count=(
                            row.get("operations_count")
                        ),
                        historical_operations=(
                            row.get("operations_count")
                        ),

                        # Indicador histórico de chuva,
                        # calculado no export diretamente
                        # das observações do HORUS.
                        rain=row.get("rain"),
                    )
                )

            InspectionHistoricalStatistic.objects.bulk_create(
                statistics,
                batch_size=1000,
            )

            batch.rows_imported = len(statistics)
            batch.status = (
                InspectionHistoricalImportBatch
                .Status.COMPLETED
            )
            batch.finished_at = timezone.now()

            batch.save(
                update_fields=[
                    "rows_imported",
                    "status",
                    "finished_at",
                ]
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"IMPORTACAO CONCLUIDA: "
                f"{len(statistics)} registros "
                "de 2022 inseridos."
            )
        )