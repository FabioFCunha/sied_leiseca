import uuid
from datetime import date, datetime, timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.inspection.models import InspectionReport, InspectionStatistic
from apps.schedules.models import Sector


class InspectionStatisticsDashboardApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.sector_ols = Sector.objects.create(name="OLS/CooAdm")
        self.sector_other = Sector.objects.create(name="Subsecretaria")
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            email="manager-dashboard@example.com",
            password="secret123",
            full_name="Gestor Dashboard",
            role=user_model.Role.MANAGER,
            sector=self.sector_other,
        )
        self.supervisor = user_model.objects.create_user(
            email="supervisor-dashboard@example.com",
            password="secret123",
            full_name="Supervisor Dashboard",
            role=user_model.Role.SUPERVISOR,
            sector=self.sector_other,
        )
        self.admin = user_model.objects.create_user(
            email="admin-dashboard@example.com",
            password="secret123",
            full_name="Admin Dashboard",
            role=user_model.Role.ADMIN,
            sector=self.sector_other,
        )
        self.ols_visitor = user_model.objects.create_user(
            email="ols-dashboard@example.com",
            password="secret123",
            full_name="Visitante OLS",
            role=user_model.Role.VISITOR,
            sector=self.sector_ols,
        )
        self.other_visitor = user_model.objects.create_user(
            email="visitor-dashboard@example.com",
            password="secret123",
            full_name="Visitante Outro Setor",
            role=user_model.Role.VISITOR,
            sector=self.sector_other,
        )
        self.education_user = user_model.objects.create_user(
            email="education-stats@example.com",
            password="secret123",
            full_name="Usuario Educacao",
            role=user_model.Role.ADMIN,
            sector=self.sector_other,
        )
        self.url = reverse("inspection-statistics-dashboard")

    def _make_report(self, *, team, operation_date, statistics_status, source_suffix):
        return InspectionReport.objects.create(
            source_id=uuid.UUID(f"00000000-0000-0000-0000-0000000000{source_suffix:02d}"),
            source_created_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc),
            synced_at=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
            operation_date=operation_date,
            team=team,
            statistics_status=statistics_status,
        )

    def _make_statistic(
        self,
        *,
        team,
        operation_date,
        source_suffix,
        operations_count=1,
        approach=0,
        reconductor=0,
        refusal=0,
        fined=0,
        towed=0,
        cnh_collected=0,
        passive_tests_performed=0,
        four_ml=0,
        thirtythree_ml=0,
        thirtyfour_ml=0,
        removal_resolutions=0,
        criminal_occurrences=0,
        art307=0,
        driving_canceled_license=0,
        arrests_means_evidence=0,
        celebrities_authorities=0,
    ):
        report = self._make_report(
            team=team,
            operation_date=operation_date,
            statistics_status=InspectionReport.StatisticsStatus.INCLUDED,
            source_suffix=source_suffix,
        )
        return InspectionStatistic.objects.create(
            report=report,
            source_report_id=report.source_id,
            operation_date=operation_date,
            team=team,
            snapshot_source_updated_at=datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc),
            generated_by=self.ols_visitor,
            operations_count=operations_count,
            approach=approach,
            reconductor=reconductor,
            refusal=refusal,
            fined=fined,
            towed=towed,
            cnh_collected=cnh_collected,
            passive_tests_performed=passive_tests_performed,
            four_ml=four_ml,
            thirtythree_ml=thirtythree_ml,
            thirtyfour_ml=thirtyfour_ml,
            removal_resolutions=removal_resolutions,
            criminal_occurrences=criminal_occurrences,
            art307=art307,
            driving_canceled_license=driving_canceled_license,
            arrests_means_evidence=arrests_means_evidence,
            celebrities_authorities=celebrities_authorities,
        )

    def _seed_dashboard_data(self):
        self._make_statistic(
            team="A3",
            operation_date=date(2026, 8, 10),
            source_suffix=1,
            operations_count=1,
            approach=93,
            reconductor=10,
            refusal=5,
            fined=44,
            towed=0,
            cnh_collected=0,
            passive_tests_performed=0,
            four_ml=88,
            thirtythree_ml=0,
            thirtyfour_ml=0,
            removal_resolutions=270,
            criminal_occurrences=0,
            art307=0,
            driving_canceled_license=1,
            arrests_means_evidence=0,
            celebrities_authorities=0,
        )
        self._make_statistic(
            team="A5",
            operation_date=date(2026, 8, 11),
            source_suffix=2,
            operations_count=2,
            approach=50,
            reconductor=8,
            refusal=2,
            fined=10,
            towed=1,
            cnh_collected=1,
            passive_tests_performed=3,
            four_ml=12,
            thirtythree_ml=4,
            thirtyfour_ml=1,
            removal_resolutions=15,
            criminal_occurrences=2,
            art307=1,
            driving_canceled_license=0,
            arrests_means_evidence=1,
            celebrities_authorities=1,
        )
        self._make_report(
            team="PENDING",
            operation_date=date(2026, 8, 11),
            statistics_status=InspectionReport.StatisticsStatus.PENDING,
            source_suffix=3,
        )
        self._make_report(
            team="EXCLUDED",
            operation_date=date(2026, 8, 12),
            statistics_status=InspectionReport.StatisticsStatus.EXCLUDED,
            source_suffix=4,
        )

    def test_empty_dashboard_returns_official_empty_state(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["meta"]["has_data"])
        self.assertEqual(response.data["summary"]["homologated_reports"], 0)
        self.assertIsNone(response.data["summary"]["approach"])
        self.assertEqual(response.data["team_production"], [])
        self.assertEqual(response.data["time_series"], [])

    def test_included_statistics_appear_in_dashboard(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["meta"]["has_data"])
        self.assertEqual(response.data["summary"]["homologated_reports"], 2)

    def test_pending_reports_do_not_appear(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        teams = {row["team"] for row in response.data["team_production"]}
        self.assertNotIn("PENDING", teams)

    def test_excluded_reports_do_not_appear(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        teams = {row["team"] for row in response.data["team_production"]}
        self.assertNotIn("EXCLUDED", teams)

    def test_filter_date_from(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url, {"date_from": "2026-08-11"})

        self.assertEqual(response.data["summary"]["homologated_reports"], 1)
        self.assertEqual(response.data["summary"]["approach"], 50)

    def test_filter_date_to(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url, {"date_to": "2026-08-10"})

        self.assertEqual(response.data["summary"]["homologated_reports"], 1)
        self.assertEqual(response.data["summary"]["approach"], 93)

    def test_filter_team(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url, {"team": "A5"})

        self.assertEqual(response.data["summary"]["homologated_reports"], 1)
        self.assertEqual(response.data["summary"]["approach"], 50)
        self.assertEqual(response.data["team_production"][0]["team"], "A5")

    def test_combined_filters(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(
            self.url,
            {"date_from": "2026-08-11", "date_to": "2026-08-11", "team": "A5"},
        )

        self.assertEqual(response.data["summary"]["homologated_reports"], 1)
        self.assertEqual(response.data["summary"]["operations"], 2)

    def test_sum_of_approach(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["summary"]["approach"], 143)

    def test_sum_of_refusal(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["summary"]["refusal"], 7)
        self.assertEqual(response.data["alcohol_results"]["refusal"], 7)

    def test_sum_of_fined(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["summary"]["fined"], 54)
        self.assertEqual(response.data["administrative_measures"]["fined"], 54)

    def test_sum_of_operations(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["summary"]["operations"], 3)

    def test_a3_preserves_270_when_homologated(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url, {"team": "A3"})

        self.assertEqual(response.data["summary"]["removal_resolutions"], 270)
        self.assertEqual(response.data["administrative_measures"]["removal_resolutions"], 270)

    def test_team_production_is_aggregated_and_sorted_by_approach(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["team_production"][0]["team"], "A3")
        self.assertEqual(response.data["team_production"][0]["approach"], 93)
        self.assertEqual(response.data["team_production"][1]["team"], "A5")

    def test_time_series_is_grouped_by_operation_date(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["time_series"][0]["operation_date"], "2026-08-10")
        self.assertEqual(response.data["time_series"][0]["approach"], 93)
        self.assertEqual(response.data["time_series"][1]["operation_date"], "2026-08-11")
        self.assertEqual(response.data["time_series"][1]["fined"], 10)

    def test_unauthenticated_user_is_blocked(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manager_can_consult_dashboard(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_visitor_ols_cooadm_can_consult_dashboard(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.ols_visitor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_endpoint_does_not_change_data(self):
        self._seed_dashboard_data()
        self.client.force_authenticate(self.manager)
        before_reports = InspectionReport.objects.count()
        before_statistics = InspectionStatistic.objects.count()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(InspectionReport.objects.count(), before_reports)
        self.assertEqual(InspectionStatistic.objects.count(), before_statistics)

    def test_education_statistics_endpoint_remains_available(self):
        self.client.force_authenticate(self.education_user)

        response = self.client.get("/api/statistics/dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refusal_all_null_returns_null(self):
        self._make_statistic(
            team="A3",
            operation_date=date(2026, 8, 10),
            source_suffix=11,
            approach=10,
            refusal=None,
            fined=1,
        )
        self._make_statistic(
            team="A5",
            operation_date=date(2026, 8, 11),
            source_suffix=12,
            approach=20,
            refusal=None,
            fined=2,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertIsNone(response.data["summary"]["refusal"])
        self.assertIsNone(response.data["alcohol_results"]["refusal"])

    def test_refusal_zero_plus_null_returns_zero(self):
        self._make_statistic(
            team="A3",
            operation_date=date(2026, 8, 10),
            source_suffix=13,
            refusal=0,
        )
        self._make_statistic(
            team="A5",
            operation_date=date(2026, 8, 11),
            source_suffix=14,
            refusal=None,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["summary"]["refusal"], 0)

    def test_refusal_value_plus_null_returns_value(self):
        self._make_statistic(
            team="A3",
            operation_date=date(2026, 8, 10),
            source_suffix=15,
            refusal=3,
        )
        self._make_statistic(
            team="A5",
            operation_date=date(2026, 8, 11),
            source_suffix=16,
            refusal=None,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["summary"]["refusal"], 3)

    def test_refusal_value_plus_value_returns_sum(self):
        self._make_statistic(
            team="A3",
            operation_date=date(2026, 8, 10),
            source_suffix=17,
            refusal=3,
        )
        self._make_statistic(
            team="A5",
            operation_date=date(2026, 8, 11),
            source_suffix=18,
            refusal=2,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.data["summary"]["refusal"], 5)

    def test_team_production_preserves_null_semantics(self):
        self._make_statistic(
            team="A3",
            operation_date=date(2026, 8, 10),
            source_suffix=19,
            refusal=None,
        )
        self._make_statistic(
            team="A5",
            operation_date=date(2026, 8, 11),
            source_suffix=20,
            refusal=0,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        rows = {row["team"]: row for row in response.data["team_production"]}
        self.assertIsNone(rows["A3"]["refusal"])
        self.assertEqual(rows["A5"]["refusal"], 0)

    def test_time_series_preserves_null_semantics(self):
        self._make_statistic(
            team="A3",
            operation_date=date(2026, 8, 10),
            source_suffix=21,
            refusal=None,
        )
        self._make_statistic(
            team="A5",
            operation_date=date(2026, 8, 11),
            source_suffix=22,
            refusal=3,
        )
        self.client.force_authenticate(self.manager)

        response = self.client.get(self.url)

        rows = {row["operation_date"]: row for row in response.data["time_series"]}
        self.assertIsNone(rows["2026-08-10"]["refusal"])
        self.assertEqual(rows["2026-08-11"]["refusal"], 3)
