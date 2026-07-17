from datetime import date, time

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agenda, Chief, Sector, Team


class AgendaSupervisorVisibilityTests(APITestCase):
    def setUp(self):
        self.team_sector = Sector.objects.get_or_create(name="HOTEL")[0]
        self.other_sector = Sector.objects.get_or_create(name="GOLF")[0]
        self.request_sector = Sector.objects.get_or_create(name="Solicitações internas")[0]
        self.team = Team.objects.get_or_create(name="HOTEL", defaults={"is_active": True})[0]
        self.other_team = Team.objects.get_or_create(name="GOLF", defaults={"is_active": True})[0]
        self.supervisor = User.objects.create_user(
            email="eleni@test.com",
            password="pwd",
            role=User.Role.SUPERVISOR,
            full_name="Eleni Martins",
            cpf="12345678901",
            sector=self.team_sector,
            is_active=True,
        )
        self.same_name_other_team = User.objects.create_user(
            email="eleni-golf@test.com",
            password="pwd",
            role=User.Role.SUPERVISOR,
            full_name="Eleni Martins",
            cpf="10987654321",
            sector=self.other_sector,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            email="admin-vis@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin Visibilidade",
            is_active=True,
        )
        self.other_chief = Chief.objects.create(name="Outro Chefe", cpf="99988877766", team=self.team, is_active=True)
        self.agenda = Agenda.objects.create(
            title="OS equipe HOTEL",
            description="Teste de visibilidade",
            date=date(2026, 7, 14),
            start_time=time(9, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.request_sector,
            created_by=self.admin,
            status=Agenda.Status.APPROVED,
            service_order_number=2419,
            team_ref=self.team,
            team_name="HOTEL",
            chief_ref=self.other_chief,
            chief_name="Outro Chefe",
        )
        self.same_name_agenda = Agenda.objects.create(
            title="OS sem vínculo confiável",
            description="Não deve liberar por nome",
            date=date(2026, 7, 16),
            start_time=time(9, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.request_sector,
            created_by=self.admin,
            status=Agenda.Status.APPROVED,
            service_order_number=5410,
            team_ref=self.team,
            team_name="HOTEL",
            chief_name="Eleni Martins",
        )
        self.client.force_authenticate(self.supervisor)

    def _results(self, response):
        return response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data

    def test_supervisor_sees_team_agenda_in_default_list(self):
        response = self.client.get(reverse("agendas-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.agenda.id, [row["id"] for row in self._results(response)])

    def test_supervisor_sees_team_agenda_in_reportable_pending_list(self):
        response = self.client.get(f"{reverse('agendas-list')}?reportable=true&pending_report=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.agenda.id, [row["id"] for row in self._results(response)])

    def test_supervisor_can_open_agenda_detail_from_team_match(self):
        response = self.client.get(reverse("agendas-detail", args=[self.agenda.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.agenda.id)

    def test_same_name_without_team_source_or_cpf_does_not_grant_access(self):
        self.client.force_authenticate(self.same_name_other_team)
        response = self.client.get(reverse("agendas-detail", args=[self.same_name_agenda.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_same_name_users_do_not_share_list_access(self):
        self.client.force_authenticate(self.same_name_other_team)
        response = self.client.get(f"{reverse('agendas-list')}?reportable=true&pending_report=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in self._results(response)]
        self.assertNotIn(self.same_name_agenda.id, ids)
        self.assertNotIn(self.agenda.id, ids)
