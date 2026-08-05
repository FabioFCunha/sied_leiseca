# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from apps.schedules.models import Agenda, Sector, Team

User = get_user_model()


class CalendarChiefVisibilityTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@test.local", password="pwd", role=User.Role.ADMIN
        )
        
        # Sectors & Teams
        self.sector_alpha = Sector.objects.create(name="ALPHA")
        self.sector_beta = Sector.objects.create(name="BETA")
        
        self.team_alpha = Team.objects.create(name="ALPHA")
        self.team_beta = Team.objects.create(name="BETA")

        # Users
        self.chief_alpha = User.objects.create_user(
            email="chief_alpha@test.local", password="pwd", role=User.Role.SUPERVISOR, sector=self.sector_alpha
        )
        self.agent_alpha = User.objects.create_user(
            email="agent_alpha@test.local", password="pwd", role=User.Role.USER, sector=self.sector_alpha
        )
        self.support_alpha = User.objects.create_user(
            email="support_alpha@test.local", password="pwd", role=User.Role.SUPPORT, sector=self.sector_alpha
        )
        self.visitor = User.objects.create_user(
            email="visitor@test.local", password="pwd", role=User.Role.VISITOR
        )

        # Agendas
        self.agenda_alpha = Agenda.objects.create(
            title="Agenda Alpha Team",
            date="2026-07-20",
            start_time="09:00",
            end_time="10:00",
            status=Agenda.Status.APPROVED,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector_alpha,
            team_ref=self.team_alpha,
        )

        self.agenda_beta = Agenda.objects.create(
            title="Agenda Beta Team",
            date="2026-07-20",
            start_time="14:00",
            end_time="15:00",
            status=Agenda.Status.APPROVED,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector_beta,
            team_ref=self.team_beta,
        )

        self.agenda_beta_pending = Agenda.objects.create(
            title="Agenda Beta Team Pending",
            date="2026-07-20",
            start_time="16:00",
            end_time="17:00",
            status=Agenda.Status.PENDING,
            origin=Agenda.Origin.PUBLIC_FORM,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector_beta,
            team_ref=self.team_beta,
        )

    def test_chief_sees_all_agendas_with_calendar_view(self):
        self.client.force_authenticate(user=self.chief_alpha)
        response = self.client.get("/api/agendas/?calendar_view=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        ids = {item["id"] for item in results}
        
        # Chefe deve ver ALPHA e BETA
        self.assertIn(self.agenda_alpha.id, ids)
        self.assertIn(self.agenda_beta.id, ids)
        self.assertIn(self.agenda_beta_pending.id, ids)

    def test_chief_cannot_see_all_agendas_without_calendar_view(self):
        self.client.force_authenticate(user=self.chief_alpha)
        response = self.client.get("/api/agendas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        ids = {item["id"] for item in results}
        
        # Sem calendar_view, vê apenas sua equipe ALPHA
        self.assertIn(self.agenda_alpha.id, ids)
        self.assertNotIn(self.agenda_beta.id, ids)

    def test_chief_can_retrieve_other_team_agenda_in_calendar(self):
        self.client.force_authenticate(user=self.chief_alpha)
        response = self.client.get(f"/api/agendas/{self.agenda_beta.id}/?calendar_view=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_chief_cannot_retrieve_other_team_agenda_without_calendar_view(self):
        self.client.force_authenticate(user=self.chief_alpha)
        response = self.client.get(f"/api/agendas/{self.agenda_beta.id}/")
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_chief_cannot_write_other_team_agenda(self):
        self.client.force_authenticate(user=self.chief_alpha)
        
        # Test PUT
        response_put = self.client.put(
            f"/api/agendas/{self.agenda_beta.id}/?calendar_view=1",
            {"title": "Attempt Hack"},
            format="json"
        )
        self.assertEqual(response_put.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test DELETE
        response_delete = self.client.delete(f"/api/agendas/{self.agenda_beta.id}/?calendar_view=1")
        self.assertEqual(response_delete.status_code, status.HTTP_403_FORBIDDEN)

    def test_agent_cannot_see_other_team_agendas_even_with_calendar_view(self):
        self.client.force_authenticate(user=self.agent_alpha)
        
        response = self.client.get("/api/agendas/?calendar_view=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        ids = {item["id"] for item in results}
        
        # Agente não é Chefe, portanto não deve ver BETA mesmo passando calendar_view=1
        self.assertIn(self.agenda_alpha.id, ids)
        self.assertNotIn(self.agenda_beta.id, ids)

    def test_support_cannot_see_other_team_agendas_even_with_calendar_view(self):
        self.client.force_authenticate(user=self.support_alpha)
        
        response = self.client.get("/api/agendas/?calendar_view=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        ids = {item["id"] for item in results}
        
        # Apoio não é Chefe
        self.assertIn(self.agenda_alpha.id, ids)
        self.assertNotIn(self.agenda_beta.id, ids)

    def test_visitor_access_not_altered_by_calendar_view(self):
        self.client.force_authenticate(user=self.visitor)
        response_normal = self.client.get("/api/agendas/")
        response_calendar = self.client.get("/api/agendas/?calendar_view=1")
        
        self.assertEqual(response_normal.status_code, status.HTTP_200_OK)
        self.assertEqual(response_calendar.status_code, status.HTTP_200_OK)
        
        ids_normal = {
            item["id"]
            for item in response_normal.data.get("results", response_normal.data)
        }
        ids_calendar = {
            item["id"]
            for item in response_calendar.data.get("results", response_calendar.data)
        }
        self.assertEqual(ids_calendar, ids_normal)

    def test_admin_retains_access(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/agendas/?calendar_view=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        ids = {item["id"] for item in results}
        self.assertIn(self.agenda_alpha.id, ids)
        self.assertIn(self.agenda_beta.id, ids)
