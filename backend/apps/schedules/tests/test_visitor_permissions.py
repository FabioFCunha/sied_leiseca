# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from apps.schedules.models import Agenda, Sector, Team, EventReport, SatisfactionSurvey, AccessibilityBlocklist

User = get_user_model()


class VisitorPermissionsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@test.local", password="pwd", role=User.Role.ADMIN
        )
        self.supervisor = User.objects.create_user(
            email="supervisor@test.local", password="pwd", role=User.Role.SUPERVISOR
        )
        self.visitor = User.objects.create_user(
            email="visitor@test.local", password="pwd", role=User.Role.VISITOR
        )
        
        self.sector = Sector.objects.create(name="Test Sector")
        self.team = Team.objects.create(name="Test Team")
        
        # Agendas with different statuses
        self.pending_agenda = Agenda.objects.create(
            title="Pending Agenda",
            date="2026-07-10",
            start_time="09:00",
            end_time="10:00",
            status=Agenda.Status.PENDING,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            team_ref=self.team,
        )
        
        self.approved_agenda = Agenda.objects.create(
            title="Approved Agenda",
            date="2026-07-11",
            start_time="09:00",
            end_time="10:00",
            status=Agenda.Status.APPROVED,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            team_ref=self.team,
        )

        self.cancelled_agenda = Agenda.objects.create(
            title="Cancelled Agenda",
            date="2026-07-12",
            start_time="09:00",
            end_time="10:00",
            status=Agenda.Status.CANCELLED,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            team_ref=self.team,
        )

        # Event Report
        self.event_report = EventReport.objects.create(
            agenda=self.approved_agenda,
            created_by=self.admin,
            status=EventReport.ReportStatus.SUBMITTED,
        )

        # Satisfaction Survey
        self.survey = SatisfactionSurvey.objects.create(
            agenda=self.approved_agenda,
            overall_rating=5,
            token="survey-token-xyz",
            moderation_status=SatisfactionSurvey.ModerationStatus.APPROVED,
        )

        # Accessibility Blocklist
        self.blocklist = AccessibilityBlocklist.objects.create(
            institution_location="Institution Location",
            address="Test Address",
            reason="No accessibility",
            is_active=True,
        )

    def test_visitor_cannot_list_pending_or_cancelled_agendas(self):
        self.client.force_authenticate(user=self.visitor)
        response = self.client.get("/api/agendas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data.get("results", response.data)
        ids = {item["id"] for item in results}
        
        self.assertIn(self.approved_agenda.id, ids)
        self.assertNotIn(self.pending_agenda.id, ids)
        self.assertNotIn(self.cancelled_agenda.id, ids)

    def test_visitor_cannot_retrieve_pending_or_cancelled_agenda(self):
        self.client.force_authenticate(user=self.visitor)
        
        # Pending
        response_pending = self.client.get(f"/api/agendas/{self.pending_agenda.id}/")
        self.assertEqual(response_pending.status_code, status.HTTP_404_NOT_FOUND)
        
        # Cancelled
        response_cancelled = self.client.get(f"/api/agendas/{self.cancelled_agenda.id}/")
        self.assertEqual(response_cancelled.status_code, status.HTTP_404_NOT_FOUND)

    def test_visitor_can_retrieve_approved_agenda(self):
        self.client.force_authenticate(user=self.visitor)
        response = self.client.get(f"/api/agendas/{self.approved_agenda.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Approved Agenda")

    def test_visitor_cannot_write_agenda(self):
        self.client.force_authenticate(user=self.visitor)
        
        # Create
        response_post = self.client.post("/api/agendas/", {"title": "New"}, format="json")
        self.assertEqual(response_post.status_code, status.HTTP_403_FORBIDDEN)
        
        # Update
        response_put = self.client.put(f"/api/agendas/{self.approved_agenda.id}/", {"title": "Updated"}, format="json")
        self.assertEqual(response_put.status_code, status.HTTP_403_FORBIDDEN)
        
        # Delete
        response_delete = self.client.delete(f"/api/agendas/{self.approved_agenda.id}/")
        self.assertEqual(response_delete.status_code, status.HTTP_403_FORBIDDEN)

    def test_visitor_cannot_create_internal_agenda_request(self):
        self.client.force_authenticate(user=self.visitor)
        response = self.client.post("/api/internal/agenda-request/", {"title": "Internal Request"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_visitor_only_read_event_reports(self):
        self.client.force_authenticate(user=self.visitor)
        
        # GET List
        response_get = self.client.get("/api/event-reports/")
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        
        # POST Create
        response_post = self.client.post("/api/event-reports/", {"agenda": self.approved_agenda.id}, format="json")
        self.assertEqual(response_post.status_code, status.HTTP_403_FORBIDDEN)

    def test_visitor_only_read_satisfaction_surveys(self):
        self.client.force_authenticate(user=self.visitor)
        
        # GET List
        response_get = self.client.get("/api/surveys/")
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        
        # POST Create
        response_post = self.client.post("/api/surveys/", {"agenda": self.approved_agenda.id, "overall_rating": 4, "token": "survey-token-xyz-2"}, format="json")
        self.assertEqual(response_post.status_code, status.HTTP_403_FORBIDDEN)

    def test_visitor_only_read_lookups(self):
        self.client.force_authenticate(user=self.visitor)
        
        # GET List Teams
        response_get = self.client.get("/api/teams/")
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        
        # POST Create Team
        response_post = self.client.post("/api/teams/", {"name": "New Team"}, format="json")
        self.assertEqual(response_post.status_code, status.HTTP_403_FORBIDDEN)

    def test_visitor_only_read_accessibility_blocklist(self):
        self.client.force_authenticate(user=self.visitor)
        
        # GET List should be forbidden for visitor (as they are not supervisor or admin)
        response_get = self.client.get("/api/accessibility-blocklist/")
        self.assertEqual(response_get.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_retains_full_agenda_access(self):
        self.client.force_authenticate(user=self.admin)
        
        # Can list all
        response = self.client.get("/api/agendas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        ids = {item["id"] for item in results}
        self.assertIn(self.pending_agenda.id, ids)
        self.assertIn(self.approved_agenda.id, ids)
        self.assertIn(self.cancelled_agenda.id, ids)
        
        # Can retrieve pending
        response_pending = self.client.get(f"/api/agendas/{self.pending_agenda.id}/")
        self.assertEqual(response_pending.status_code, status.HTTP_200_OK)

    def test_supervisor_retains_agenda_access(self):
        self.client.force_authenticate(user=self.supervisor)
        # Supervisors can list and retrieve if they are scoped
        response = self.client.get("/api/agendas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_delete_unprotected_agenda(self):
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.delete(f"/api/agendas/{self.pending_agenda.id}/")
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Agenda.objects.filter(id=self.pending_agenda.id).exists())

    def test_visitor_cannot_delete_agenda_explicit(self):
        self.client.force_authenticate(user=self.visitor)
        
        response = self.client.delete(f"/api/agendas/{self.pending_agenda.id}/")
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Agenda.objects.filter(id=self.pending_agenda.id).exists())

    def test_admin_cannot_delete_protected_agenda(self):
        from apps.schedules.models import EducationReport
        
        self.client.force_authenticate(user=self.admin)
        
        EducationReport.objects.create(
            agenda=self.pending_agenda,
            created_by=self.admin,
            status=EducationReport.ReportStatus.SUBMITTED,
            operation_date="2026-07-10"
        )
        
        response = self.client.delete(f"/api/agendas/{self.pending_agenda.id}/")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        detail_msg = response.data.get("detail", "").lower()
        self.assertIn("relatório técnico", detail_msg)
