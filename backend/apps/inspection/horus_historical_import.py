import hashlib
import json
from datetime import date
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.inspection.models import (
    HISTORICAL_CUTOFF_DATE,
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalImportBatch,
    InspectionHistoricalStatistic,
)


EXPECTED_DATE_FROM = date(2023, 1, 1)
EXPECTED_DATE_TO = date(2026, 8, 9)

EXPECTED_ROWS = 11225
EXPECTED_REPORTS = 11497
EXPECTED_OPERATIONS = 12836

EXPECTED_ANNUAL = {
    2023: {
        "reports": 3262,
        "operations": 4029,
        "approach": 259879,
        "reconductor": 43859,
        "refusal": 33798,
        "fined": 110968,
        "towed": 7068,
    },
    2024: {
        "reports": 3159,
        "operations": 3510,
        "approach": 236147,
        "reconductor": 43526,
        "refusal": 29764,
        "fined": 104692,
        "towed": 70,
    },
    2025: {
        "reports": 3171,
        "operations": 3367,
        "approach": 312003,
        "reconductor": 44553,
        "refusal": 29420,
        "fined": 117932,
        "towed": 48,
    },
    2026: {
        "reports": 1905,
        "operations": 1930,
        "approach": 178130,
        "reconductor": 23265,
        "refusal": 14874,
        "fined": 61710,
        "towed": 16,
    },
}


class HorusHistoricalImportError(Exception):
    pass


def compute_sha256(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def nullable_sum(rows, field_name):
    values = [
        row.get(field_name)
        for row in rows
        if row.get(field_name) is not None
    ]

    if not values:
        return None

    return sum(values)


class HorusHistoricalImportService:
    def load_file(self, file_path):
        path = Path(file_path)

        if not path.exists():
            raise HorusHistoricalImportError(
                f"Arquivo nao encontrado: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise HorusHistoricalImportError(
                f"JSON invalido: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise HorusHistoricalImportError(
                "O JSON historico precisa conter um objeto na raiz."
            )

        return path, payload

    def validate(self, file_path):
        path, payload = self.load_file(
            file_path
        )

        errors = []
        warnings = []

        metadata = payload.get(
            "metadata"
        ) or {}

        summary = payload.get(
            "summary"
        ) or {}

        annual_controls = payload.get(
            "annual_controls"
        ) or {}

        rows = payload.get(
            "rows"
        )

        if not isinstance(rows, list):
            errors.append(
                "Campo rows ausente ou invalido."
            )
            rows = []

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

        if (
            metadata.get("date_from")
            != EXPECTED_DATE_FROM.isoformat()
        ):
            errors.append(
                "Data inicial diferente de 2023-01-01."
            )

        if (
            metadata.get("date_to")
            != EXPECTED_DATE_TO.isoformat()
        ):
            errors.append(
                "Data final diferente de 2026-08-09."
            )

        if (
            metadata.get("read_only_source")
            is not True
        ):
            errors.append(
                "O arquivo nao declara origem read-only."
            )

        if len(rows) != EXPECTED_ROWS:
            errors.append(
                f"Quantidade de linhas divergente: "
                f"{len(rows)} != {EXPECTED_ROWS}."
            )

        if (
            summary.get("reports")
            != EXPECTED_REPORTS
        ):
            errors.append(
                "Quantidade total de relatorios divergente."
            )

        if (
            summary.get("operations")
            != EXPECTED_OPERATIONS
        ):
            errors.append(
                "Quantidade total de operacoes divergente."
            )

        seen_keys = set()

        parsed_rows = []

        for index, raw_row in enumerate(
            rows,
            start=1,
        ):
            if not isinstance(
                raw_row,
                dict,
            ):
                errors.append(
                    f"Linha {index}: formato invalido."
                )
                continue

            try:
                reference_date = (
                    date.fromisoformat(
                        raw_row[
                            "reference_date"
                        ]
                    )
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                errors.append(
                    f"Linha {index}: "
                    "reference_date invalida."
                )
                continue

            if (
                reference_date
                < EXPECTED_DATE_FROM
                or reference_date
                > EXPECTED_DATE_TO
            ):
                errors.append(
                    f"Linha {index}: data fora "
                    f"da faixa autorizada: "
                    f"{reference_date}."
                )

            if (
                reference_date
                > HISTORICAL_CUTOFF_DATE
            ):
                errors.append(
                    f"Linha {index}: data supera "
                    "o corte historico."
                )

            team = str(
                raw_row.get(
                    "team"
                )
                or ""
            ).strip()

            if not team:
                errors.append(
                    f"Linha {index}: equipe vazia."
                )

            key = (
                reference_date,
                team.upper(),
            )

            if key in seen_keys:
                errors.append(
                    f"Linha {index}: duplicidade "
                    f"data/equipe {key}."
                )

            seen_keys.add(key)

            expected_year = (
                reference_date.year
            )

            expected_month = (
                reference_date.month
            )

            if (
                raw_row.get(
                    "reference_year"
                )
                != expected_year
            ):
                errors.append(
                    f"Linha {index}: "
                    "reference_year inconsistente."
                )

            if (
                raw_row.get(
                    "reference_month"
                )
                != expected_month
            ):
                errors.append(
                    f"Linha {index}: "
                    "reference_month inconsistente."
                )

            parsed_rows.append(
                {
                    **raw_row,
                    "_reference_date": (
                        reference_date
                    ),
                    "_team": team,
                    "_source_row": index,
                }
            )

        calculated_reports = sum(
            int(
                row.get(
                    "reports_count"
                )
                or 0
            )
            for row in parsed_rows
        )

        calculated_operations = sum(
            int(
                row.get(
                    "operations_count"
                )
                or 0
            )
            for row in parsed_rows
        )

        if (
            calculated_reports
            != EXPECTED_REPORTS
        ):
            errors.append(
                f"Soma interna dos relatorios "
                f"divergente: "
                f"{calculated_reports} "
                f"!= {EXPECTED_REPORTS}."
            )

        if (
            calculated_operations
            != EXPECTED_OPERATIONS
        ):
            errors.append(
                f"Soma interna das operacoes "
                f"divergente: "
                f"{calculated_operations} "
                f"!= {EXPECTED_OPERATIONS}."
            )

        calculated_annual = {}

        for year, expected in (
            EXPECTED_ANNUAL.items()
        ):
            year_rows = [
                row
                for row in parsed_rows
                if (
                    row[
                        "_reference_date"
                    ].year
                    == year
                )
            ]

            calculated = {
                "reports": sum(
                    int(
                        row.get(
                            "reports_count"
                        )
                        or 0
                    )
                    for row in year_rows
                ),
                "operations": sum(
                    int(
                        row.get(
                            "operations_count"
                        )
                        or 0
                    )
                    for row in year_rows
                ),
                "approach": nullable_sum(
                    year_rows,
                    "approach",
                ),
                "reconductor": nullable_sum(
                    year_rows,
                    "reconductor",
                ),
                "refusal": nullable_sum(
                    year_rows,
                    "refusal",
                ),
                "fined": nullable_sum(
                    year_rows,
                    "fined",
                ),
                "towed": nullable_sum(
                    year_rows,
                    "towed",
                ),
            }

            calculated_annual[
                str(year)
            ] = calculated

            for field_name, expected_value in (
                expected.items()
            ):
                if (
                    calculated.get(
                        field_name
                    )
                    != expected_value
                ):
                    errors.append(
                        f"{year}/{field_name}: "
                        f"{calculated.get(field_name)} "
                        f"!= {expected_value}."
                    )

            file_control = (
                annual_controls.get(
                    str(year)
                )
                or {}
            )

            for field_name, expected_value in (
                expected.items()
            ):
                if (
                    file_control.get(
                        field_name
                    )
                    != expected_value
                ):
                    errors.append(
                        f"annual_controls "
                        f"{year}/{field_name} "
                        "divergente."
                    )

        file_sha256 = compute_sha256(
            path
        )

        existing_batch = (
            InspectionHistoricalImportBatch
            .objects
            .filter(
                source_file_sha256=(
                    file_sha256
                ),
                source_type=(
                    HistoricalSourceType.DAILY
                ),
                taxonomy_era=(
                    HistoricalTaxonomyEra.ERA_C
                ),
            )
            .first()
        )

        overlap_count = (
            InspectionHistoricalStatistic
            .objects
            .filter(
                source_type=(
                    HistoricalSourceType.DAILY
                ),
                taxonomy_era=(
                    HistoricalTaxonomyEra.ERA_C
                ),
                reference_date__gte=(
                    EXPECTED_DATE_FROM
                ),
                reference_date__lte=(
                    EXPECTED_DATE_TO
                ),
            )
            .count()
        )

        if existing_batch:
            errors.append(
                f"O mesmo arquivo ja possui "
                f"lote registrado: "
                f"{existing_batch.id} / "
                f"{existing_batch.status}."
            )

        if overlap_count:
            errors.append(
                f"Existem {overlap_count} "
                "registros DAILY / ERA_C "
                "na faixa que seria importada."
            )

        report = {
            "file": {
                "path": str(
                    path.resolve()
                ),
                "name": path.name,
                "sha256": file_sha256,
                "size": (
                    path.stat().st_size
                ),
            },
            "metadata": metadata,
            "summary": {
                "rows": len(
                    parsed_rows
                ),
                "reports": (
                    calculated_reports
                ),
                "operations": (
                    calculated_operations
                ),
                "date_from": (
                    EXPECTED_DATE_FROM
                    .isoformat()
                ),
                "date_to": (
                    EXPECTED_DATE_TO
                    .isoformat()
                ),
                "overlap_count": (
                    overlap_count
                ),
            },
            "annual_controls": (
                calculated_annual
            ),
            "validation": {
                "valid": not errors,
                "errors_count": len(
                    errors
                ),
                "warnings_count": len(
                    warnings
                ),
            },
            "errors": errors,
            "warnings": warnings,
        }

        return (
            report,
            parsed_rows,
        )

    def dry_run(self, file_path):
        report, _rows = self.validate(
            file_path
        )

        return report

    def apply(self, file_path):
        report, rows = self.validate(
            file_path
        )

        if report["errors"]:
            raise HorusHistoricalImportError(
                "Importacao recusada porque "
                "o dry-run possui erros."
            )

        file_data = report["file"]

        compact_report = {
            "metadata": (
                report["metadata"]
            ),
            "summary": (
                report["summary"]
            ),
            "annual_controls": (
                report[
                    "annual_controls"
                ]
            ),
            "validation": (
                report["validation"]
            ),
            "warnings": (
                report["warnings"]
            ),
        }

        with transaction.atomic():
            batch = (
                InspectionHistoricalImportBatch
                .objects
                .create(
                    source_file_name=(
                        file_data["name"]
                    ),
                    source_file_sha256=(
                        file_data["sha256"]
                    ),
                    source_file_size=(
                        file_data["size"]
                    ),
                    source_type=(
                        HistoricalSourceType.DAILY
                    ),
                    taxonomy_era=(
                        HistoricalTaxonomyEra.ERA_C
                    ),
                    status=(
                        InspectionHistoricalImportBatch
                        .Status
                        .PENDING
                    ),
                    started_at=(
                        timezone.now()
                    ),
                    rows_found=len(
                        rows
                    ),
                    rows_valid=len(
                        rows
                    ),
                    rows_imported=0,
                    rows_ignored=0,
                    errors_count=0,
                    warnings_count=len(
                        report[
                            "warnings"
                        ]
                    ),
                    report_json=(
                        compact_report
                    ),
                )
            )

            statistics = []

            for row in rows:
                statistics.append(
                    InspectionHistoricalStatistic(
                        reference_date=(
                            row[
                                "_reference_date"
                            ]
                        ),
                        reference_year=(
                            row[
                                "_reference_date"
                            ].year
                        ),
                        reference_month=(
                            row[
                                "_reference_date"
                            ].month
                        ),
                        team=row[
                            "_team"
                        ],
                        source_team_label=(
                            row[
                                "_team"
                            ]
                        ),
                        source_type=(
                            HistoricalSourceType.DAILY
                        ),
                        source_sheet=(
                            "HORUS"
                        ),
                        source_row=(
                            row[
                                "_source_row"
                            ]
                        ),
                        taxonomy_era=(
                            HistoricalTaxonomyEra.ERA_C
                        ),
                        import_batch=(
                            batch
                        ),
                        source_workbook_label=(
                            file_data[
                                "name"
                            ]
                        ),
                        notes=(
                            "Fonte oficial Horus; "
                            "consolidado por data "
                            "e equipe."
                        ),

                        historical_approached=(
                            row.get(
                                "approach"
                            )
                        ),

                        reconductor=(
                            row.get(
                                "reconductor"
                            )
                        ),

                        refusal=(
                            row.get(
                                "refusal"
                            )
                        ),

                        fined=(
                            row.get(
                                "fined"
                            )
                        ),

                        towed=(
                            row.get(
                                "towed"
                            )
                        ),

                        cnh_collected=(
                            row.get(
                                "cnh_collected"
                            )
                        ),

                        four_ml=(
                            row.get(
                                "four_ml"
                            )
                        ),

                        thirtythree_ml=(
                            row.get(
                                "thirtythree_ml"
                            )
                        ),

                        thirtyfour_ml=(
                            row.get(
                                "thirtyfour_ml"
                            )
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
                            row.get(
                                "art307"
                            )
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
                            row.get(
                                "operations_count"
                            )
                        ),

                        historical_operations=(
                            row.get(
                                "operations_count"
                            )
                        ),
                    )
                )

            InspectionHistoricalStatistic.objects.bulk_create(
                statistics,
                batch_size=1000,
            )

            batch.rows_imported = len(
                statistics
            )

            batch.status = (
                InspectionHistoricalImportBatch
                .Status
                .COMPLETED
            )

            batch.finished_at = (
                timezone.now()
            )

            batch.save(
                update_fields=[
                    "rows_imported",
                    "status",
                    "finished_at",
                ]
            )

        report[
            "import_result"
        ] = {
            "batch_id": batch.id,
            "rows_imported": len(
                statistics
            ),
            "status": "COMPLETED",
        }

        return report