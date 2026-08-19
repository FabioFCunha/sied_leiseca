from datetime import date, datetime, timezone
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.inspection.models import (
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalImportBatch,
    InspectionHistoricalStatistic,
    InspectionReport,
    InspectionStatistic,
)
from apps.inspection.services import InspectionStatisticsUnifiedService


class UnifiedStatisticsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="statstester@example.com",
            password="secretpassword",
            role=get_user_model().Role.ADMIN,
        )

        #
        # Histórico diário / ERA_C
        #
        self.batch = InspectionHistoricalImportBatch.objects.create(
            source_file_name="test.xlsx",
            source_file_sha256="fakehash",
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            source_file_size=100,
            status=InspectionHistoricalImportBatch.Status.COMPLETED,
            imported_by=self.user,
            started_at=datetime(
                2026,
                8,
                12,
                tzinfo=timezone.utc,
            ),
        )

        InspectionHistoricalStatistic.objects.create(
            import_batch=self.batch,
            reference_date=date(2026, 8, 5),
            reference_year=2026,
            reference_month=8,
            team="A1",
            source_team_label="Equipe A1",
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            source_sheet="D1",
            source_row=4,
            historical_approached=100,
            reconductor=5,
            four_ml=10,
            thirtythree_ml=2,
            thirtyfour_ml=1,
            refusal=3,
            fined=20,
            towed=5,
            taxi_approached=15,
            taxi_illegal=2,
            rain=1,
        )

        # Historical stat 2 (2026-08-09) - Team B1
        InspectionHistoricalStatistic.objects.create(
            import_batch=self.batch,
            reference_date=date(2026, 8, 9),
            reference_year=2026,
            reference_month=8,
            team="B1",
            source_team_label="Equipe B1",
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            source_sheet="D5",
            source_row=5,
            four_ml=None,
            thirtythree_ml=None,
            thirtyfour_ml=None,
            refusal=None,
            fined=None,
            towed=None,
        )

        #
        # Histórico anual consolidado / LEGACY / ERA_A
        #
        self.legacy_batch = (
            InspectionHistoricalImportBatch.objects.create(
                source_file_name="legacy.xlsx",
                source_file_sha256="legacy-fakehash",
                source_type=HistoricalSourceType.LEGACY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_A,
                source_file_size=200,
                status=InspectionHistoricalImportBatch.Status.COMPLETED,
                imported_by=self.user,
                started_at=datetime(
                    2026,
                    8,
                    13,
                    tzinfo=timezone.utc,
                ),
            )
        )

        # Consolidado anual 2021
        InspectionHistoricalStatistic.objects.create(
            import_batch=self.legacy_batch,
            reference_date=None,
            reference_year=2021,
            reference_month=None,
            team="",
            source_team_label="Consolidado anual",
            source_type=HistoricalSourceType.LEGACY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_A,
            source_sheet="Plan2",
            source_row=2021,
            historical_approached=153806,
            fined=67399,
            towed=867,
            historical_cnh_retained=14823,
            refusal=19063,
            administrative_art_165=715,
            criminal_art_306=146,
            criminal_art_306_other_evidence=28,
            historical_alcohol_cases=19952,
            historical_alcohol_percentage="0.1297217562",
            historical_art_307=431,
            driving_canceled_license=194,
            historical_operations=2689,
        )

        # Consolidado anual 2022
        InspectionHistoricalStatistic.objects.create(
            import_batch=self.legacy_batch,
            reference_date=None,
            reference_year=2022,
            reference_month=None,
            team="",
            source_team_label="Consolidado anual",
            source_type=HistoricalSourceType.LEGACY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_A,
            source_sheet="Plan2",
            source_row=2022,
            historical_approached=344720,
            fined=126330,
            towed=7582,
            historical_cnh_retained=22129,
            refusal=33918,
            administrative_art_165=155,
            criminal_art_306=56,
            criminal_art_306_other_evidence=52,
            historical_alcohol_cases=34181,
            historical_alcohol_percentage="0.0991558366",
            historical_art_307=691,
            driving_canceled_license=237,
            historical_operations=3514,
        )

        #
        # Operacional / SIED
        #

        # Operational stat 1 (2026-08-10) - Team A1
        report1 = InspectionReport.objects.create(
            source_id=uuid4(),
            source_created_at=datetime(
                2026,
                8,
                10,
                tzinfo=timezone.utc,
            ),
            source_updated_at=datetime(
                2026,
                8,
                10,
                tzinfo=timezone.utc,
            ),
            synced_at=datetime(
                2026,
                8,
                10,
                tzinfo=timezone.utc,
            ),
            operation_date=date(2026, 8, 10),
            team="A1",
        )

        InspectionStatistic.objects.create(
            report=report1,
            source_report_id=report1.source_id,
            operation_date=report1.operation_date,
            team=report1.team,
            snapshot_source_updated_at=report1.source_updated_at,
            operations_count=1,
            approach=100,
            reconductor=5,
            refusal=4,
            four_ml=15,
            thirtythree_ml=3,
            thirtyfour_ml=0,
            fined=30,
            towed=8,
        )

        # Operational stat 2 (2026-08-11) - Team B1
        report2 = InspectionReport.objects.create(
            source_id=uuid4(),
            source_created_at=datetime(
                2026,
                8,
                11,
                tzinfo=timezone.utc,
            ),
            source_updated_at=datetime(
                2026,
                8,
                11,
                tzinfo=timezone.utc,
            ),
            synced_at=datetime(
                2026,
                8,
                11,
                tzinfo=timezone.utc,
            ),
            operation_date=date(2026, 8, 11),
            team="B1",
        )

        InspectionStatistic.objects.create(
            report=report2,
            source_report_id=report2.source_id,
            operation_date=report2.operation_date,
            team=report2.team,
            snapshot_source_updated_at=report2.source_updated_at,
            operations_count=1,
            approach=None,
            reconductor=None,
            refusal=None,
            four_ml=None,
            thirtythree_ml=None,
            thirtyfour_ml=None,
            fined=None,
            towed=None,
        )

    #
    # Testes já existentes
    #

    def test_historical_only_period(self):
        filters = {
            "date_from": "2026-08-01",
            "date_to": "2026-08-09",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        self.assertEqual(
            result["meta"]["sources_used"],
            ["historical"],
        )
        self.assertEqual(
            result["summary"]["homologated_reports"],
            None,
        )
        # DAILY / ERA_C pertence à futura consulta territorial do Horus
        # e não compõe os indicadores oficiais da primeira aba.
        self.assertEqual(
            result["administrative_measures"]["fined"],
            20
        )
        self.assertEqual(
            result["alcohol_results"]["four_ml"],
            10
        )
        self.assertIsNone(
            result["summary"]["approach_plus_reconductor"]
        )
        self.assertEqual(
            result["occurrences"]["rain"],
            1,
        )
        self.assertEqual(
            result["coverage"]["occurrences.rain"],
            "HISTORICAL_ONLY",
        )

    def test_operational_only_period(self):
        filters = {
            "date_from": "2026-08-10",
            "date_to": "2026-08-31",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        self.assertEqual(
            result["meta"]["sources_used"],
            ["report"],
        )
        self.assertEqual(
            result["summary"]["homologated_reports"],
            2,
        )
        self.assertEqual(
            result["administrative_measures"]["fined"],
            30,
        )
        self.assertEqual(
            result["alcohol_results"]["four_ml"],
            15,
        )

        # Operational approach_plus_reconductor =
        # approach + reconductor = 100 + 5 = 105
        self.assertEqual(
            result["summary"]["approach_plus_reconductor"],
            105,
        )

        self.assertEqual(
            result["occurrences"]["rain"],
            None,
        )
        self.assertEqual(
            result["coverage"]["occurrences.rain"],
            "HISTORICAL_ONLY",
        )

    def test_cross_period(self):
        filters = {
            "date_from": "2026-08-01",
            "date_to": "2026-08-15",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        self.assertEqual(
            set(result["meta"]["sources_used"]),
            {"historical", "report"},
        )

        # DAILY / ERA_C não entra na aba oficial; somente o operacional.
        self.assertEqual(
            result["administrative_measures"]["fined"],
            50,
        )

        # Indicador incompatível no cruzamento
        self.assertIsNone(
            result["summary"]["approach_plus_reconductor"]
        )
        self.assertEqual(
            result["coverage"][
                "summary.approach_plus_reconductor"
            ],
            "PARTIAL",
        )

        # Relatórios são somente operacionais
        self.assertEqual(
            result["summary"]["homologated_reports"],
            2,
        )
        self.assertEqual(
            result["coverage"]["summary.homologated_reports"],
            "CURRENT_ONLY",
        )

    def test_null_plus_null(self):
        filters = {
            "date_from": "2026-08-09",
            "date_to": "2026-08-11",
            "team": "B1",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        self.assertIsNone(
            result["administrative_measures"]["fined"]
        )

    def test_biqueira(self):
        filters = {
            "date_from": "2026-08-01",
            "date_to": "2026-08-15",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        # DAILY / ERA_C não é somado aos indicadores oficiais.
        self.assertEqual(
            result["alcohol_results"]["four_ml"],
            25,
        )
        self.assertEqual(
            result["alcohol_results"]["thirtythree_ml"],
            5,
        )
        self.assertEqual(
            result["alcohol_results"]["thirtyfour_ml"],
            1,
        )
        self.assertEqual(
            result["coverage"]["alcohol_results.four_ml"],
            "DIRECT",
        )

    def test_team_production_unification(self):
        filters = {
            "date_from": "2026-08-01",
            "date_to": "2026-08-15",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        team_prod = {
            item["team"]: item
            for item in result["team_production"]
        }

        self.assertIn("A1", team_prod)
        self.assertIn("B1", team_prod)

        self.assertEqual(
            team_prod["A1"]["fined"],
            30,
        )

    def test_time_series_continuous(self):
        filters = {
            "date_from": "2026-08-01",
            "date_to": "2026-08-15",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        ts = {
            item["operation_date"]: item
            for item in result["time_series"]
        }

        # A série temporal oficial não usa a granularidade DAILY / ERA_C.
#         self.assertNotIn("2026-08-05", ts)
#         self.assertNotIn("2026-08-09", ts)
        self.assertIn("2026-08-10", ts)
        self.assertIn("2026-08-11", ts)

        self.assertEqual(
            ts["2026-08-10"]["fined"],
            30,
        )

    def test_view_endpoint_integration(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        url = (
            reverse("inspection-statistics-dashboard")
            + "?date_from=2026-08-01"
            + "&date_to=2026-08-15"
        )

        response = client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["administrative_measures"]["fined"],
            50,
        )

    #
    # Novos testes — série anual LEGACY / ERA_A
    #

    def test_full_legacy_year_2022(self):
        filters = {
            "date_from": "2022-01-01",
            "date_to": "2022-12-31",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        self.assertEqual(
            result["meta"]["sources_used"],
            ["historical"],
        )

        self.assertEqual(
            result["summary"]["approach"],
            344720,
        )
        self.assertEqual(
            result["summary"]["fined"],
            126330,
        )
        self.assertEqual(
            result["summary"]["towed"],
            7582,
        )
        self.assertEqual(
            result["summary"]["refusal"],
            33918,
        )
        self.assertEqual(
            result["summary"]["art307"],
            691,
        )
        self.assertEqual(
            result["summary"]["operations"],
            3514,
        )

        self.assertEqual(
            result["driver"]["historical_cnh_retained"],
            22129,
        )
        self.assertEqual(
            result["summary"]["driving_canceled_license"],
            237,
        )

    def test_full_legacy_year_2021(self):
        filters = {
            "date_from": "2021-01-01",
            "date_to": "2021-12-31",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        self.assertEqual(
            result["summary"]["approach"],
            153806,
        )
        self.assertEqual(
            result["summary"]["fined"],
            67399,
        )
        self.assertEqual(
            result["summary"]["art307"],
            431,
        )
        self.assertEqual(
            result["summary"]["operations"],
            2689,
        )

    def test_multiple_full_legacy_years_are_summed(self):
        filters = {
            "date_from": "2021-01-01",
            "date_to": "2022-12-31",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        self.assertEqual(
            result["summary"]["approach"],
            153806 + 344720,
        )
        self.assertEqual(
            result["summary"]["fined"],
            67399 + 126330,
        )
        self.assertEqual(
            result["summary"]["towed"],
            867 + 7582,
        )
        self.assertEqual(
            result["summary"]["refusal"],
            19063 + 33918,
        )
        self.assertEqual(
            result["summary"]["art307"],
            431 + 691,
        )
        self.assertEqual(
            result["summary"]["operations"],
            2689 + 3514,
        )

    def test_partial_legacy_year_does_not_use_annual_total(self):
        filters = {
            "date_from": "2022-01-01",
            "date_to": "2022-06-30",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        self.assertIsNone(
            result["summary"]["approach"]
        )
        self.assertIsNone(
            result["summary"]["fined"]
        )
        self.assertIsNone(
            result["summary"]["operations"]
        )
        self.assertIsNone(
            result["summary"]["art307"]
        )

    def test_mixed_partial_and_full_legacy_year(self):
        filters = {
            "date_from": "2021-07-01",
            "date_to": "2022-12-31",
        }

        result = InspectionStatisticsUnifiedService(
            filters
        ).get_dashboard_data()

        # 2021 está incompleto e não pode ser usado.
        # 2022 está completamente coberto.
        self.assertEqual(
            result["summary"]["approach"],
            344720,
        )
        self.assertEqual(
            result["summary"]["fined"],
            126330,
        )
        self.assertEqual(
            result["summary"]["art307"],
            691,
        )
        self.assertEqual(
            result["summary"]["operations"],
            3514,
        )

    def test_cutoff_2026_remains_unchanged(self):
        historical = InspectionStatisticsUnifiedService(
            {
                "date_from": "2026-08-09",
                "date_to": "2026-08-09",
            }
        ).get_dashboard_data()

        operational = InspectionStatisticsUnifiedService(
            {
                "date_from": "2026-08-10",
                "date_to": "2026-08-10",
            }
        ).get_dashboard_data()

        self.assertEqual(
            historical["meta"]["sources_used"],
            ["historical"],
        )
        self.assertEqual(
            operational["meta"]["sources_used"],
            ["report"],
        )