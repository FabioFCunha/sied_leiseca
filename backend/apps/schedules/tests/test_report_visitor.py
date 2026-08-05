from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.schedules.models import Agenda, EducationReport, Sector, Team


User = get_user_model()


class EducationReportVisitorTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin.visitor@test.local", password="pwd", role=User.Role.ADMIN)
        self.visitor = User.objects.create_user(email="visitor@test.local", password="pwd", role=User.Role.VISITOR)
        self.sector = Sector.objects.create(name="Visitor Sector")
        self.team = Team.objects.create(name="Visitor Team")
        self.agenda = Agenda.objects.create(
            title="Agenda Visitor",
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
        self.approved_report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.admin,
            status=EducationReport.ReportStatus.APPROVED,
            team="Visitor Team",
            operation_date="2026-07-01",
        )
        self.draft_report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.admin,
            status=EducationReport.ReportStatus.DRAFT,
            team="Visitor Team Draft",
            operation_date="2026-07-01",
        )
        self.client.force_authenticate(user=self.visitor)

    def test_visitor_lists_only_approved_reports(self):
        response = self.client.get("/api/education-reports/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        ids = {item["id"] for item in results}
        self.assertIn(self.approved_report.id, ids)
        self.assertNotIn(self.draft_report.id, ids)

    def test_visitor_receives_403_for_write_actions(self):
        write_requests = [
            lambda: self.client.post("/api/education-reports/", {"team": "X"}, format="json"),
            lambda: self.client.put(f"/api/education-reports/{self.approved_report.id}/", {"team": "X"}, format="json"),
            lambda: self.client.patch(f"/api/education-reports/{self.approved_report.id}/", {"team": "X"}, format="json"),
            lambda: self.client.delete(f"/api/education-reports/{self.approved_report.id}/"),
            lambda: self.client.post(f"/api/education-reports/{self.approved_report.id}/submit-for-review/"),
            lambda: self.client.post(f"/api/education-reports/{self.approved_report.id}/approve/"),
            lambda: self.client.post(f"/api/education-reports/{self.approved_report.id}/return-for-correction/", {"notes": "corrigir"}, format="json"),
            lambda: self.client.post(f"/api/education-reports/{self.approved_report.id}/process-statistics/"),
        ]

        for request in write_requests:
            with self.subTest(request=request):
                response = request()
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_visitor_receives_404_when_retrieving_non_approved_report(self):
        response = self.client.get(f"/api/education-reports/{self.draft_report.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)