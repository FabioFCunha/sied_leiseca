from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.schedules.models import Agenda, EducationReport, Sector, Team


User = get_user_model()


class EducationReportServiceOrderFilterTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin.report.filter@test.local",
            password="pwd",
            role=User.Role.ADMIN,
        )
        self.visitor = User.objects.create_user(
            email="visitor.report.filter@test.local",
            password="pwd",
            role=User.Role.VISITOR,
        )
        self.sector = Sector.objects.create(name="Report Filter Sector")
        self.team = Team.objects.create(name="Report Filter Team")
        self.agenda = Agenda.objects.create(
            title="Agenda para filtro por OS",
            date="2026-07-01",
            start_time="09:00",
            end_time="10:00",
            status=Agenda.Status.COMPLETED,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            team_ref=self.team,
        )
        self.report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.admin,
            status=EducationReport.ReportStatus.APPROVED,
            team="Report Filter Team",
            operation_date="2026-07-01",
        )

    def _search_as(self, user):
        self.client.force_authenticate(user=user)
        return self.client.get(
            "/api/education-reports/",
            {"q": str(self.agenda.service_order_number)},
        )

    def _result_ids(self, response):
        data = response.data
        results = data.get("results", data) if isinstance(data, dict) else data
        return {item["id"] for item in results}

    def test_admin_filters_reports_by_service_order_number(self):
        self.assertIsNotNone(self.agenda.service_order_number)

        response = self._search_as(self.admin)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.report.id, self._result_ids(response))

    def test_visitor_filters_approved_reports_by_service_order_number(self):
        self.assertIsNotNone(self.agenda.service_order_number)

        response = self._search_as(self.visitor)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.report.id, self._result_ids(response))
