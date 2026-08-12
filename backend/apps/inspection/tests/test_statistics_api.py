import uuid
from datetime import date, datetime, timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.inspection.models import InspectionReport, InspectionReportOperation, InspectionStatistic, InspectionStatisticsDecisionHistory
from apps.schedules.models import Sector


class InspectionStatisticsApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.sector_cooadm = Sector.objects.create(name="OLS/CooAdm")
        self.other_sector = Sector.objects.create(name="Subsecretaria")
        self.allowed_user = get_user_model().objects.create_user(
            email="cooadm@example.com",
            password="secret123",
            full_name="Usuario CooAdm",
            role=get_user_model().Role.VISITOR,
            sector=self.sector_cooadm,
        )
        self.denied_user = get_user_model().objects.create_user(
            email="manager@example.com",
            password="secret123",
            full_name="Gestor Bloqueado",
            role=get_user_model().Role.MANAGER,
            sector=self.other_sector,
        )
        self.other_visitor = get_user_model().objects.create_user(
            email="visitor-other@example.com",
            password="secret123",
            full_name="Visitante Outro Setor",
            role=get_user_model().Role.VISITOR,
            sector=self.other_sector,
        )
        self.admin_user = get_user_model().objects.create_user(
            email="admin@example.com",
            password="secret123",
            full_name="Admin Bloqueado",
            role=get_user_model().Role.ADMIN,
            sector=self.other_sector,
        )
        self.supervisor_user = get_user_model().objects.create_user(
            email="supervisor@example.com",
            password="secret123",
            full_name="Supervisor Bloqueado",
            role=get_user_model().Role.SUPERVISOR,
            sector=self.other_sector,
        )
        self.superuser_without_institution = get_user_model().objects.create_superuser(
            email="root@example.com",
            password="secret123",
            full_name="Superusuario Tecnico",
            sector=self.other_sector,
        )
        self.report = InspectionReport.objects.create(
            source_id=uuid.uuid4(),
            source_created_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc),
            synced_at=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
            operation_date=date(2026, 8, 10),
            team="A3",
            management_id=None,
            military_chief_source_id=None,
            segov_team_civil="Equipe civil ficticia",
            segov_team_military="Equipe militar ficticia",
            change_ols="Sem alteracoes",
            agent_detran=2,
            number_trailers=0,
            change_support="",
            cars="VTR-01",
            changes_general="Sem alteracoes",
        )
        InspectionReportOperation.objects.create(
            report=self.report,
            source_id=uuid.uuid4(),
            source_created_at=datetime(2026, 8, 10, 8, 5, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 35, tzinfo=timezone.utc),
            address_operation="Rua Ficticia, 100",
            locality="Vista Alegre",
            another_not_listed="",
            departure_meeting_point="20:00",
            operation_assembly="20:45",
            first_approach="21:40",
            closing="02:00",
            approach=93,
            reconductor=10,
            refusal=5,
            celebrities_authorities=0,
            four_ml=88,
            thirtythree_ml=0,
            thirtyfour_ml=0,
            passive_tests_performed=0,
            changes_material="",
            cnh_collected=0,
            fined=44,
            towed=0,
            removal_resolutions=270,
            arrests_means_evidence=0,
            art307=0,
            criminal_occurrences=0,
            driving_canceled_license=1,
            vehicle_resolutions="003 contran",
            administrative_tests="Sem Alteracoes",
            cep="21250-392",
            street="Rua Ficticia",
            city="Rio de Janeiro",
            district="Vista Alegre",
            number="",
        )

    def test_visitor_ols_cooadm_can_include_report(self):
        self.client.force_authenticate(self.allowed_user)

        response = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_visitor_ols_cooadm_can_exclude_report(self):
        self.client.force_authenticate(self.allowed_user)

        response = self.client.post(
            reverse("inspection-reports-exclude-from-statistics", args=[self.report.id]),
            {"reason": "Possivel inconsistência no quantitativo informado."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_visitor_other_sector_cannot_include_report(self):
        self.client.force_authenticate(self.other_visitor)

        response = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_outside_ols_cooadm_cannot_include_report(self):
        self.client.force_authenticate(self.admin_user)

        response = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_include_report(self):
        self.client.force_authenticate(self.denied_user)

        response = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_cannot_include_report(self):
        self.client.force_authenticate(self.supervisor_user)

        response = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_without_institutional_representation_cannot_include_report(self):
        self.client.force_authenticate(self.superuser_without_institution)

        response = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_include_creates_snapshot_and_history(self):
        self.client.force_authenticate(self.allowed_user)

        response = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["result"], "included")
        self.report.refresh_from_db()
        self.assertEqual(self.report.statistics_status, InspectionReport.StatisticsStatus.INCLUDED)
        self.assertEqual(self.report.statistics_reviewed_by, self.allowed_user)
        self.assertIsNotNone(self.report.statistics_reviewed_at)
        self.assertIsNotNone(self.report.statistics_snapshot)
        self.assertEqual(self.report.statistics_snapshot["report"]["team"], "A3")
        self.assertEqual(self.report.statistics_snapshot["operations"][0]["removal_resolutions"], 270)
        self.assertTrue(
            InspectionStatisticsDecisionHistory.objects.filter(
                report=self.report,
                new_status=InspectionReport.StatisticsStatus.INCLUDED,
                changed_by=self.allowed_user,
            ).exists()
        )
        self.assertTrue(InspectionStatistic.objects.filter(report=self.report).exists())

    def test_exclude_requires_reason(self):
        self.client.force_authenticate(self.allowed_user)

        response = self.client.post(reverse("inspection-reports-exclude-from-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", response.data)

    def test_exclude_stores_reason_and_history(self):
        self.client.force_authenticate(self.allowed_user)

        response = self.client.post(
            reverse("inspection-reports-exclude-from-statistics", args=[self.report.id]),
            {"reason": "Possivel inconsistência no quantitativo de deliberacoes."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["result"], "excluded")
        self.report.refresh_from_db()
        self.assertEqual(self.report.statistics_status, InspectionReport.StatisticsStatus.EXCLUDED)
        self.assertEqual(self.report.statistics_exclusion_reason, "Possivel inconsistência no quantitativo de deliberacoes.")
        self.assertEqual(self.report.statistics_reviewed_by, self.allowed_user)
        self.assertIsNone(self.report.statistics_snapshot)
        self.assertTrue(
            InspectionStatisticsDecisionHistory.objects.filter(
                report=self.report,
                new_status=InspectionReport.StatisticsStatus.EXCLUDED,
                changed_by=self.allowed_user,
            ).exists()
        )

    def test_included_report_cannot_be_included_again(self):
        self.client.force_authenticate(self.allowed_user)
        first = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)

        response = self.client.post(reverse("inspection-reports-include-in-statistics", args=[self.report.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(InspectionStatistic.objects.filter(report=self.report).count(), 1)
