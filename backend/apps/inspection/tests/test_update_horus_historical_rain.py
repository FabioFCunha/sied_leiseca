import csv
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.inspection.models import (
    InspectionHistoricalImportBatch,
    InspectionHistoricalStatistic,
)


class UpdateHorusHistoricalRainCommandTests(TestCase):
    def setUp(self):
        now = timezone.now()

        self.import_batch = InspectionHistoricalImportBatch.objects.create(
            source_file_name="HORUS_TEST.csv",
            source_file_sha256="0" * 64,
            source_type="DAILY",
            taxonomy_era="ERA_C",
            source_file_size=0,
            status="COMPLETED",
            started_at=now,
            finished_at=now,
            rows_found=1,
            rows_valid=1,
            rows_imported=1,
            rows_ignored=0,
            errors_count=0,
            warnings_count=0,
            report_json={},
        )

    def make_stat(self, **overrides):
        data = {
            "reference_date": date(2026, 1, 13),
            "reference_year": 2026,
            "reference_month": 1,
            "team": "BRAVO",
            "source_team_label": "BRAVO",
            "source_type": "DAILY",
            "source_sheet": "HORUS",
            "source_row": 1,
            "taxonomy_era": "ERA_C",
            "import_batch": self.import_batch,
            "source_workbook_label": "HORUS_PUSH_HTTPS",
            "is_validation_only": False,
            "rain": None,
        }

        data.update(overrides)

        return InspectionHistoricalStatistic.objects.create(**data)

    def write_csv(self, directory, rows):
        path = Path(directory) / "rain.csv"

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "reference_date",
                    "team",
                    "rain",
                ],
            )

            writer.writeheader()
            writer.writerows(rows)

        return path

    def test_dry_run_does_not_persist(self):
        stat = self.make_stat()

        with TemporaryDirectory() as tmp:
            path = self.write_csv(
                tmp,
                [
                    {
                        "reference_date": "2026-01-13",
                        "team": "BRAVO",
                        "rain": "1",
                    }
                ],
            )

            call_command(
                "update_horus_historical_rain",
                file=str(path),
            )

        stat.refresh_from_db()

        self.assertIsNone(stat.rain)

    def test_apply_updates_only_rain(self):
        stat = self.make_stat(
            refusal=7,
            four_ml=100,
        )

        with TemporaryDirectory() as tmp:
            path = self.write_csv(
                tmp,
                [
                    {
                        "reference_date": "2026-01-13",
                        "team": "BRAVO",
                        "rain": "2",
                    }
                ],
            )

            call_command(
                "update_horus_historical_rain",
                file=str(path),
                apply=True,
            )

        stat.refresh_from_db()

        self.assertEqual(stat.rain, 2)

        # Garante que o comando não altera outros indicadores.
        self.assertEqual(stat.refusal, 7)
        self.assertEqual(stat.four_ml, 100)

    def test_rejects_date_after_historical_cutoff(self):
        self.make_stat()

        with TemporaryDirectory() as tmp:
            path = self.write_csv(
                tmp,
                [
                    {
                        "reference_date": "2026-08-10",
                        "team": "BRAVO",
                        "rain": "1",
                    }
                ],
            )

            with self.assertRaises(CommandError):
                call_command(
                    "update_horus_historical_rain",
                    file=str(path),
                )

    def test_rejects_not_found_key(self):
        self.make_stat()

        with TemporaryDirectory() as tmp:
            path = self.write_csv(
                tmp,
                [
                    {
                        "reference_date": "2026-01-14",
                        "team": "BRAVO",
                        "rain": "1",
                    }
                ],
            )

            with self.assertRaises(CommandError):
                call_command(
                    "update_horus_historical_rain",
                    file=str(path),
                )