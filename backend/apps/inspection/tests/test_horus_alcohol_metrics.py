from datetime import date, datetime, timezone
from uuid import uuid4

from django.test import TestCase

from apps.inspection.models import (
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalImportBatch,
    InspectionHistoricalStatistic,
    InspectionHistoricalTerritorialStatistic,
    InspectionMunicipality,
    InspectionRegion,
    InspectionReport,
    InspectionStatistic,
)
from apps.inspection.services import (
    InspectionStatisticsUnifiedService,
)


class HorusAlcoholMetricsTests(TestCase):
    def setUp(self):
        self.batch_daily = (
            InspectionHistoricalImportBatch.objects.create(
                source_file_name="daily.xlsx",
                source_file_sha256="daily-horus-alcohol",
                source_type=HistoricalSourceType.DAILY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_C,
                source_file_size=100,
                status=InspectionHistoricalImportBatch.Status.COMPLETED,
                started_at=datetime(
                    2026, 8, 20, tzinfo=timezone.utc
                ),
            )
        )
        self.batch_accumulated = (
            InspectionHistoricalImportBatch.objects.create(
                source_file_name="accumulated.xlsx",
                source_file_sha256="accumulated-horus-alcohol",
                source_type=HistoricalSourceType.ACCUMULATED,
                taxonomy_era=HistoricalTaxonomyEra.ERA_B,
                source_file_size=100,
                status=InspectionHistoricalImportBatch.Status.COMPLETED,
                started_at=datetime(
                    2026, 8, 20, tzinfo=timezone.utc
                ),
            )
        )

        self.metro = InspectionRegion.objects.create(
            code="METRO-TEST",
            name="Metropolitana Teste",
        )
        self.city = InspectionMunicipality.objects.create(
            region=self.metro,
            name="Cidade Teste",
            normalized_name="CIDADE TESTE",
        )

        self._create_accumulated_baseline_like_row()
        self._create_daily_rows()
        self._create_territorial_rows()
        self._create_operational_row()

    def _create_accumulated_baseline_like_row(self):
        InspectionHistoricalStatistic.objects.create(
            import_batch=self.batch_accumulated,
            reference_year=2026,
            team="",
            source_team_label="Acumulado 2026",
            source_type=HistoricalSourceType.ACCUMULATED,
            taxonomy_era=HistoricalTaxonomyEra.ERA_B,
            source_sheet="Plan1",
            source_row=1,
            four_ml=8913,
            thirtythree_ml=33,
            thirtyfour_ml=3,
            historical_passive_tests=2765,
            historical_approached=5000,
            historical_operations=100,
        )

    def _create_daily_rows(self):
        rows = [
            {
                "reference_date": date(2022, 10, 2),
                "team": "IGN",
                "four_ml": 999999,
                "thirtythree_ml": 999,
                "thirtyfour_ml": 999,
                "passive_tests_performed": 999999,
            },
            {
                "reference_date": date(2022, 10, 3),
                "team": "A1",
                "four_ml": 200000,
                "thirtythree_ml": 700,
                "thirtyfour_ml": 150,
                "passive_tests_performed": 100000,
            },
            {
                "reference_date": date(2024, 6, 15),
                "team": "B2",
                "four_ml": 260845,
                "thirtythree_ml": 1021,
                "thirtyfour_ml": 268,
                "passive_tests_performed": 150000,
            },
            {
                "reference_date": date(2025, 1, 10),
                "team": "A1",
                "four_ml": 100000,
                "thirtythree_ml": 500,
                "thirtyfour_ml": 50,
                "passive_tests_performed": 30000,
            },
            {
                "reference_date": date(2025, 6, 15),
                "team": "B1",
                "four_ml": 179069,
                "thirtythree_ml": 791,
                "thirtyfour_ml": 118,
                "passive_tests_performed": 59540,
            },
            {
                "reference_date": date(2026, 8, 9),
                "team": "A1",
                "four_ml": 200000,
                "thirtythree_ml": 500,
                "thirtyfour_ml": 150,
                "passive_tests_performed": 137429,
            },
            {
                "reference_date": date(2025, 5, 5),
                "team": "A1",
                "four_ml": 555555,
                "thirtythree_ml": 555,
                "thirtyfour_ml": 555,
                "passive_tests_performed": 555555,
                "is_validation_only": True,
            },
        ]

        for index, row in enumerate(rows, start=1):
            InspectionHistoricalStatistic.objects.create(
                import_batch=self.batch_daily,
                reference_year=row["reference_date"].year,
                reference_month=row["reference_date"].month,
                source_team_label=f"Equipe {row['team']}",
                source_type=HistoricalSourceType.DAILY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_C,
                source_sheet="Daily",
                source_row=index,
                is_validation_only=row.get(
                    "is_validation_only", False
                ),
                reference_date=row["reference_date"],
                team=row["team"],
                four_ml=row["four_ml"],
                thirtythree_ml=row["thirtythree_ml"],
                thirtyfour_ml=row["thirtyfour_ml"],
                passive_tests_performed=row[
                    "passive_tests_performed"
                ],
            )

    def _create_territorial_rows(self):
        InspectionHistoricalTerritorialStatistic.objects.create(
            reference_date=date(2025, 2, 1),
            team="A1",
            source_city="Cidade Teste",
            normalized_city="CIDADE TESTE",
            municipality=self.city,
            region=self.metro,
            operations_count=1,
            four_ml=123,
            thirtythree_ml=4,
            thirtyfour_ml=5,
            passive_tests_performed=60,
        )
        InspectionHistoricalTerritorialStatistic.objects.create(
            reference_date=date(2025, 2, 1),
            team="A1",
            source_city="",
            normalized_city="",
            operations_count=1,
            four_ml=9999,
            thirtythree_ml=999,
            thirtyfour_ml=999,
            passive_tests_performed=9999,
        )

    def _create_operational_row(self):
        report = InspectionReport.objects.create(
            source_id=uuid4(),
            source_created_at=datetime(
                2026, 8, 10, tzinfo=timezone.utc
            ),
            source_updated_at=datetime(
                2026, 8, 10, tzinfo=timezone.utc
            ),
            synced_at=datetime(
                2026, 8, 10, tzinfo=timezone.utc
            ),
            operation_date=date(2026, 8, 10),
            team="A1",
        )
        InspectionStatistic.objects.create(
            report=report,
            source_report_id=report.source_id,
            operation_date=report.operation_date,
            team=report.team,
            snapshot_source_updated_at=report.source_updated_at,
            operations_count=1,
            four_ml=7,
            thirtythree_ml=11,
            thirtyfour_ml=13,
            passive_tests_performed=17,
        )

    def test_full_horus_period_uses_daily_era_c_totals(self):
        result = InspectionStatisticsUnifiedService(
            {
                "date_from": "2022-10-03",
                "date_to": "2026-08-09",
            }
        ).get_dashboard_data()

        self.assertEqual(
            result["alcohol_results"]["four_ml"], 939914
        )
        self.assertEqual(
            result["alcohol_results"]["thirtythree_ml"], 3512
        )
        self.assertEqual(
            result["alcohol_results"]["thirtyfour_ml"], 736
        )
        self.assertEqual(
            result["driver"]["passive_tests_performed"], 476969
        )

    def test_year_2025_uses_daily_era_c_totals(self):
        result = InspectionStatisticsUnifiedService(
            {
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            }
        ).get_dashboard_data()

        self.assertEqual(
            result["alcohol_results"]["four_ml"], 279069
        )
        self.assertEqual(
            result["alcohol_results"]["thirtythree_ml"], 1291
        )
        self.assertEqual(
            result["alcohol_results"]["thirtyfour_ml"], 168
        )
        self.assertEqual(
            result["driver"]["passive_tests_performed"], 89540
        )

    def test_partial_2025_tracks_requested_period(self):
        result = InspectionStatisticsUnifiedService(
            {
                "date_from": "2025-01-01",
                "date_to": "2025-03-31",
            }
        ).get_dashboard_data()

        self.assertEqual(
            result["alcohol_results"]["four_ml"], 100000
        )
        self.assertEqual(
            result["alcohol_results"]["thirtythree_ml"], 500
        )
        self.assertEqual(
            result["alcohol_results"]["thirtyfour_ml"], 50
        )
        self.assertEqual(
            result["driver"]["passive_tests_performed"], 30000
        )

    def test_team_filter_tracks_daily_horus_team(self):
        result = InspectionStatisticsUnifiedService(
            {
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
                "team": "A1",
            }
        ).get_dashboard_data()

        self.assertEqual(
            result["alcohol_results"]["four_ml"], 100000
        )
        self.assertEqual(
            result["alcohol_results"]["thirtythree_ml"], 500
        )
        self.assertEqual(
            result["alcohol_results"]["thirtyfour_ml"], 50
        )
        self.assertEqual(
            result["driver"]["passive_tests_performed"], 30000
        )

    def test_period_crossing_operational_cutoff_sums_without_duplication(self):
        result = InspectionStatisticsUnifiedService(
            {
                "date_from": "2026-08-09",
                "date_to": "2026-08-20",
            }
        ).get_dashboard_data()

        self.assertEqual(
            result["alcohol_results"]["four_ml"], 200007
        )
        self.assertEqual(
            result["alcohol_results"]["thirtythree_ml"], 511
        )
        self.assertEqual(
            result["alcohol_results"]["thirtyfour_ml"], 163
        )
        self.assertEqual(
            result["driver"]["passive_tests_performed"], 137446
        )

    def test_region_uses_territorial_layer_without_statewide_baseline(self):
        result = InspectionStatisticsUnifiedService(
            {
                "region": "Metropolitana Teste",
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
                "team": "A1",
            }
        ).get_dashboard_data()

        self.assertEqual(
            result["alcohol_results"]["four_ml"], 123
        )
        self.assertEqual(
            result["alcohol_results"]["thirtythree_ml"], 4
        )
        self.assertEqual(
            result["alcohol_results"]["thirtyfour_ml"], 5
        )
        self.assertEqual(
            result["driver"]["passive_tests_performed"], 60
        )

    def test_wide_period_does_not_fall_back_to_accumulated_low_values(self):
        result = InspectionStatisticsUnifiedService(
            {
                "date_from": "2009-01-01",
                "date_to": "2026-08-20",
            }
        ).get_dashboard_data()

        self.assertEqual(
            result["alcohol_results"]["four_ml"], 939921
        )
        self.assertEqual(
            result["alcohol_results"]["thirtythree_ml"], 3523
        )
        self.assertEqual(
            result["alcohol_results"]["thirtyfour_ml"], 749
        )
        self.assertEqual(
            result["driver"]["passive_tests_performed"], 476986
        )
