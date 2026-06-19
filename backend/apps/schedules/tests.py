from datetime import date, time

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agenda, Agent, Sector, ShiftSchedule, Team


class ShiftSwapPermissionTests(APITestCase):
    def setUp(self):
        self.team_alpha, _ = Team.objects.get_or_create(name="ALFA")
        self.team_beta, _ = Team.objects.get_or_create(name="BETA")
        self.sector_alpha, _ = Sector.objects.get_or_create(name="ALFA")
        self.manager = User.objects.create_user(
            email="gestor-troca@example.com",
            password="password123",
            full_name="Gestor Troca",
            role=User.Role.MANAGER,
        )
        self.schedule = ShiftSchedule.objects.create(
            date=date(2026, 6, 20),
            team=self.team_alpha,
            created_by=self.manager,
        )
        self.own_agent = Agent.objects.create(name="Agente Proprio", cpf="11111111111", team=self.team_alpha, is_active=True)
        self.other_agent = Agent.objects.create(name="Agente Colega", cpf="22222222222", team=self.team_alpha, is_active=True)
        self.replacement = Agent.objects.create(name="Agente Substituto", cpf="33333333333", team=self.team_beta, is_active=True)

    def swap_payload(self, from_member):
        return {
            "schedule": self.schedule.id,
            "member_type": "AGENT",
            "from_member_id": from_member.id,
            "target_team": self.team_beta.id,
            "to_member_id": self.replacement.id,
            "reason": "Troca operacional",
        }

    def test_agent_can_request_swap_only_for_self(self):
        agent_user = User.objects.create_user(
            email="agente-troca@example.com",
            password="password123",
            full_name="Agente Proprio",
            cpf="11111111111",
            role=User.Role.USER,
        )
        self.client.force_authenticate(agent_user)

        own_response = self.client.post(reverse("shift-swaps-list"), self.swap_payload(self.own_agent))
        other_response = self.client.post(reverse("shift-swaps-list"), self.swap_payload(self.other_agent))

        self.assertEqual(own_response.status_code, 201)
        self.assertEqual(other_response.status_code, 400)
        self.assertIn("proprio", str(other_response.json()))

    def test_supervisor_can_request_swap_for_any_member_of_own_team(self):
        supervisor = User.objects.create_user(
            email="chefe-troca@example.com",
            password="password123",
            full_name="Chefe Alfa",
            role=User.Role.SUPERVISOR,
            sector=self.sector_alpha,
        )
        self.client.force_authenticate(supervisor)

        response = self.client.post(reverse("shift-swaps-list"), self.swap_payload(self.other_agent))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["from_member_name"], "Agente Colega")

    def test_supervisor_cannot_request_swap_for_another_team(self):
        team_bravo, _ = Team.objects.get_or_create(name="BRAVO")
        schedule = ShiftSchedule.objects.create(
            date=date(2026, 6, 21),
            team=team_bravo,
            created_by=self.manager,
        )
        bravo_agent = Agent.objects.create(name="Agente Bravo", cpf="44444444444", team=team_bravo, is_active=True)
        supervisor = User.objects.create_user(
            email="chefe-fora@example.com",
            password="password123",
            full_name="Chefe Alfa",
            role=User.Role.SUPERVISOR,
            sector=self.sector_alpha,
        )
        self.client.force_authenticate(supervisor)

        response = self.client.post(reverse("shift-swaps-list"), {
            "schedule": schedule.id,
            "member_type": "AGENT",
            "from_member_id": bravo_agent.id,
            "target_team": self.team_beta.id,
            "to_member_id": self.replacement.id,
            "reason": "Troca operacional",
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn("propria equipe", str(response.json()))

class AgendaAccessTests(APITestCase):
    def test_agent_user_can_list_agenda_where_they_are_scheduled(self):
        sector = Sector.objects.create(name="ALFA")
        manager = User.objects.create_user(
            email="gestor@example.com",
            password="password123",
            full_name="Gestor OLS",
            role=User.Role.MANAGER,
            sector=sector,
        )
        agent_user = User.objects.create_user(
            email="agente@example.com",
            password="password123",
            full_name="Agente Escalado",
            cpf="12345678901",
            role=User.Role.USER,
        )
        agent = Agent.objects.create(name="Agente Escalado", cpf="12345678901", is_active=True)
        agenda = Agenda.objects.create(
            title="Palestra educativa",
            description="Atividade agendada",
            date=date(2026, 6, 10),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Escola Municipal",
            responsible=manager,
            sector=sector,
            created_by=manager,
        )
        agenda.agents_ref.add(agent)

        self.client.force_authenticate(agent_user)
        response = self.client.get(
            reverse("agendas-list"),
            {"date_from": "2026-06-01", "date_to": "2026-06-30"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        rows = payload["results"] if "results" in payload else payload
        self.assertEqual([row["id"] for row in rows], [agenda.id])
