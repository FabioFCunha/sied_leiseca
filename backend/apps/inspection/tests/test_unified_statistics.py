from datetime import date, datetime, timezone
import json
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from apps.inspection.models import (
    InspectionStatistic,
    InspectionHistoricalStatistic,
    InspectionHistoricalImportBatch,
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionReport,
)
from apps.inspection.services import InspectionStatisticsUnifiedService


class UnifiedStatisticsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="statstester@example.com",
            password="secretpassword",
            role=get_user_model().Role.ADMIN,
        )
        self.batch = InspectionHistoricalImportBatch.objects.create(
            source_file_name="test.xlsx",
            source_file_sha256="fakehash",
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            source_file_size=100,
            status=InspectionHistoricalImportBatch.Status.COMPLETED,
            imported_by=self.user,
            started_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        )

        # Historical stat 1 (2026-08-05) - Team A1
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

        # Operational stat 1 (2026-08-10) - Team A1
        report1 = InspectionReport.objects.create(
            source_id=uuid4(),
            source_created_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
            synced_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
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
            source_created_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
            synced_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
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

    def test_historical_only_period(self):
        filters = {"date_from": "2026-08-01", "date_to": "2026-08-09"}
        result = InspectionStatisticsUnifiedService(filters).get_dashboard_data()

        self.assertEqual(result["meta"]["sources_used"], ["historical"])
        self.assertEqual(result["summary"]["homologated_reports"], None)
        self.assertEqual(result["administrative_measures"]["fined"], 20)
        self.assertEqual(result["alcohol_results"]["four_ml"], 10)

        # Historical approach_plus_reconductor = four_ml + refusal = 10 + 3 = 13
        self.assertEqual(result["summary"]["approach_plus_reconductor"], 13)
        self.assertEqual(result["occurrences"]["rain"], 1)
        self.assertEqual(result["coverage"]["occurrences.rain"], "HISTORICAL_ONLY")

    def test_operational_only_period(self):
        filters = {"date_from": "2026-08-10", "date_to": "2026-08-31"}
        result = InspectionStatisticsUnifiedService(filters).get_dashboard_data()

        self.assertEqual(result["meta"]["sources_used"], ["report"])
        self.assertEqual(result["summary"]["homologated_reports"], 2)
        self.assertEqual(result["administrative_measures"]["fined"], 30)
        self.assertEqual(result["alcohol_results"]["four_ml"], 15)

        # Operational approach_plus_reconductor = approach + reconductor = 100 + 5 = 105
        self.assertEqual(result["summary"]["approach_plus_reconductor"], 105)
        self.assertEqual(result["occurrences"]["rain"], None)
        self.assertEqual(result["coverage"]["occurrences.rain"], "HISTORICAL_ONLY")

    def test_cross_period(self):
        filters = {"date_from": "2026-08-01", "date_to": "2026-08-15"}
        result = InspectionStatisticsUnifiedService(filters).get_dashboard_data()

        self.assertEqual(set(result["meta"]["sources_used"]), {"historical", "report"})
        # Fined: 20 (hist) + 30 (op) = 50
        self.assertEqual(result["administrative_measures"]["fined"], 50)

        # approach_plus_reconductor in cross period should be None because it's partial/incompatible
        self.assertIsNone(result["summary"]["approach_plus_reconductor"])
        self.assertEqual(result["coverage"]["summary.approach_plus_reconductor"], "PARTIAL")

        # Relatorios is operational only
        self.assertEqual(result["summary"]["homologated_reports"], 2)
        self.assertEqual(result["coverage"]["summary.homologated_reports"], "CURRENT_ONLY")

    def test_null_plus_null(self):
        filters = {"date_from": "2026-08-09", "date_to": "2026-08-11", "team": "B1"}
        result = InspectionStatisticsUnifiedService(filters).get_dashboard_data()

        # B1 has None in both periods for fined
        self.assertIsNone(result["administrative_measures"]["fined"])

    def test_biqueira(self):
        # four_ml (10 hist + 15 op) + thirtythree_ml (2 hist + 3 op) + thirtyfour_ml (1 hist + 0 op)
        filters = {"date_from": "2026-08-01", "date_to": "2026-08-15"}
        result = InspectionStatisticsUnifiedService(filters).get_dashboard_data()

        self.assertEqual(result["alcohol_results"]["four_ml"], 25)
        self.assertEqual(result["alcohol_results"]["thirtythree_ml"], 5)
        self.assertEqual(result["alcohol_results"]["thirtyfour_ml"], 1)
        self.assertEqual(result["coverage"]["alcohol_results.four_ml"], "DIRECT")

    def test_team_production_unification(self):
        filters = {"date_from": "2026-08-01", "date_to": "2026-08-15"}
        result = InspectionStatisticsUnifiedService(filters).get_dashboard_data()

        team_prod = {t["team"]: t for t in result["team_production"]}
        self.assertIn("A1", team_prod)
        self.assertIn("B1", team_prod)

        # A1 fined: 20 + 30 = 50
        self.assertEqual(team_prod["A1"]["fined"], 50)

    def test_time_series_continuous(self):
        filters = {"date_from": "2026-08-01", "date_to": "2026-08-15"}
        result = InspectionStatisticsUnifiedService(filters).get_dashboard_data()

        ts = {t["operation_date"]: t for t in result["time_series"]}
        self.assertIn("2026-08-05", ts)
        self.assertIn("2026-08-09", ts)
        self.assertIn("2026-08-10", ts)
        self.assertIn("2026-08-11", ts)

        self.assertEqual(ts["2026-08-05"]["fined"], 20)
        self.assertEqual(ts["2026-08-10"]["fined"], 30)

    def test_view_endpoint_integration(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        url = reverse("inspection-statistics-dashboard") + "?date_from=2026-08-01&date_to=2026-08-15"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["administrative_measures"]["fined"], 50)
