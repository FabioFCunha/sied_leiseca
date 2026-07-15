from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.schedules.models import EducationReport, Agenda

User = get_user_model()

class EducationReportWorkflowTests(APITestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_user(email="admin@teste.com", password="pwd", role=User.Role.ADMIN)
        self.manager = User.objects.create_user(email="manager@teste.com", password="pwd", role=User.Role.MANAGER)
        self.chief = User.objects.create_user(email="chief@teste.com", password="pwd", role=User.Role.SUPERVISOR)
        self.agent = User.objects.create_user(email="agent@teste.com", password="pwd", role=User.Role.USER)
        self.visitor = User.objects.create_user(email="visitor@teste.com", password="pwd", role=User.Role.VISITOR)

        from apps.schedules.models import Sector
        self.sector = Sector.objects.create(name="Test Sector")

        # Create agenda
        self.chief = User.objects.create_user(email="chief@example.com", password="password", role=User.Role.USER, sector=self.sector)

        from apps.schedules.models import Team, ShiftSchedule
        self.team = Team.objects.create(name="Team A")
        
        self.agenda = Agenda.objects.create(
            title="Acao Teste",
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
        
        self.schedule = ShiftSchedule.objects.create(
            team=self.team,
            date=self.agenda.date,
            created_by=self.admin,
        )

        # Create report as draft
        self.report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.chief,
            status=EducationReport.ReportStatus.DRAFT,
            team="Team A",
            operation_date="2026-07-01",
        )

    def test_chief_cannot_approve_or_return(self):
        self.client.force_authenticate(user=self.chief)
        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()

        response = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(f"/api/education-reports/{self.report.id}/return-for-correction/", {"notes": "fix it"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agent_and_visitor_cannot_approve(self):
        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()

        for user in [self.agent, self.visitor]:
            self.client.force_authenticate(user=user)
            response = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_approve_and_return(self):
        self.client.force_authenticate(user=self.manager)
        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()

        response = self.client.post(f"/api/education-reports/{self.report.id}/return-for-correction/", {"notes": "needs fix"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, EducationReport.ReportStatus.RETURNED)

        self.report.status = EducationReport.ReportStatus.PENDING_REVIEW
        self.report.save()
        
        response = self.client.post(f"/api/education-reports/{self.report.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, EducationReport.ReportStatus.APPROVED)

    def test_admin_can_edit_approved_report_via_put_or_patch(self):
        self.client.force_authenticate(user=self.admin)
        self.report.status = EducationReport.ReportStatus.APPROVED
        self.report.save()

        # PUT
        response = self.client.put(f"/api/education-reports/{self.report.id}/", {
            "team": "Team B",
            "agenda": self.agenda.id,
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # PATCH
        response = self.client.patch(f"/api/education-reports/{self.report.id}/", {
            "status": "APPROVED"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_status_cannot_be_changed_via_payload(self):
        self.client.force_authenticate(user=self.admin)
        
        # Try to create directly as APPROVED
        response = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team D",
            "operation_date": "2026-07-01",
            "status": "APPROVED",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        if response.status_code != 201:
            print(response.json())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_report = EducationReport.objects.get(id=response.data["id"])
        self.assertEqual(new_report.status, EducationReport.ReportStatus.DRAFT)

        # Try to patch status to APPROVED
        response = self.client.patch(f"/api/education-reports/{new_report.id}/", {
            "status": "APPROVED"
        }, format="json")
        if response.status_code != 200:
            print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_report.refresh_from_db()
        self.assertEqual(new_report.status, EducationReport.ReportStatus.DRAFT)

    def test_create_draft_and_submit(self):
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team E",
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report_id = response.data["id"]
        
        response = self.client.post(f"/api/education-reports/{report_id}/submit-for-review/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        report = EducationReport.objects.get(id=report_id)
        self.assertEqual(report.status, EducationReport.ReportStatus.PENDING_REVIEW)
        
    def test_prevent_duplicate_reports_same_agenda_and_team(self):
        self.client.force_authenticate(user=self.admin)
        
        response1 = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team F",
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        response2 = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team F",
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Já existe um relatório técnico", str(response2.data))
        
    def test_update_own_report_without_duplication_error(self):
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post("/api/education-reports/", {
            "agenda": self.agenda.id,
            "team": "Team C",
            "operation_date": "2026-07-01",
            "actions": [],
            "accessibility_conditions_met": "YES"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report_id = response.data["id"]
        
        response = self.client.patch(f"/api/education-reports/{report_id}/", {
            "team": "Team G",
            "general_observations": "Updated"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["general_observations"], "Updated")
        
    def test_return_correct_and_resubmit(self):
        self.client.force_authenticate(user=self.manager)
        
        report = EducationReport.objects.create(
            agenda=self.agenda,
            created_by=self.chief,
            status=EducationReport.ReportStatus.PENDING_REVIEW,
            team="Team H",
            operation_date="2026-07-01",
        )
        
        response = self.client.post(f"/api/education-reports/{report.id}/return-for-correction/", {"notes": "fix"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f"/api/education-reports/{report.id}/", {
            "general_observations": "Fixed"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.post(f"/api/education-reports/{report.id}/submit-for-review/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, EducationReport.ReportStatus.PENDING_REVIEW)
