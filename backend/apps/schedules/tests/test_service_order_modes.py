from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agenda, Agent, Chief, Sector, ShiftSchedule, Support, Team
from apps.schedules.services import get_expected_attendance_member_keys, get_expected_member_keys


class AgendaDesignatedModeApiTests(APITestCase):
    def setUp(self):
        self.sector = Sector.objects.get_or_create(name="Solicitacoes")[0]
        self.team_a = Team.objects.get_or_create(name="ALFA", defaults={"is_active": True})[0]
        self.team_b = Team.objects.get_or_create(name="BRAVO", defaults={"is_active": True})[0]
        self.admin = User.objects.create_user(
            email="admin-designated@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin Designated",
            is_active=True,
        )
        self.user_one = User.objects.create_user(
            email="one@test.com",
            password="pwd",
            role=User.Role.SUPPORT,
            full_name="Participante Um",
            sector=self.sector,
            is_active=True,
        )
        self.user_two = User.objects.create_user(
            email="two@test.com",
            password="pwd",
            role=User.Role.USER,
            full_name="Participante Dois",
            sector=self.sector,
            is_active=True,
        )
        self.inactive_user = User.objects.create_user(
            email="inactive@test.com",
            password="pwd",
            role=User.Role.USER,
            full_name="Inativo",
            sector=self.sector,
            is_active=False,
        )
        self.chief = Chief.objects.create(name="Chefe Alfa", team=self.team_a, is_active=True)
        self.agent = Agent.objects.create(name="Agente Alfa", team=self.team_a, is_active=True)
        self.support = Support.objects.create(name="Apoio Alfa", team=self.team_a, is_active=True)
        self.client.force_authenticate(self.admin)
        self.url = reverse("agendas-list")

    def _base_payload(self):
        return {
            "title": "Agenda teste",
            "description": "Descricao valida",
            "date": "2026-07-20",
            "start_time": "09:00",
            "end_time": "12:00",
            "location": "Centro",
            "responsible": self.admin.id,
            "sector": self.sector.id,
            "status": Agenda.Status.PENDING,
            "origin": Agenda.Origin.INTERNAL,
        }

    def test_create_designated_requires_participants(self):
        payload = {
            **self._base_payload(),
            "service_order_mode": Agenda.ServiceOrderMode.DESIGNATED,
            "designated_users": [],
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("designated_users", response.data)

    def test_create_designated_rejects_hybrid_composition(self):
        payload = {
            **self._base_payload(),
            "service_order_mode": Agenda.ServiceOrderMode.DESIGNATED,
            "designated_users": [self.user_one.id],
            "team_ref": self.team_a.id,
            "chief_ref": self.chief.id,
            "agents_ref": [self.agent.id],
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_order_mode", response.data)

    def test_create_designated_accepts_multiple_active_users(self):
        payload = {
            **self._base_payload(),
            "service_order_mode": Agenda.ServiceOrderMode.DESIGNATED,
            "designated_users": [self.user_one.id, self.user_two.id],
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        agenda = Agenda.objects.get(id=response.data["id"])
        self.assertEqual(agenda.service_order_mode, Agenda.ServiceOrderMode.DESIGNATED)
        self.assertCountEqual(list(agenda.designated_users.values_list("id", flat=True)), [self.user_one.id, self.user_two.id])

    def test_create_designated_rejects_inactive_user(self):
        payload = {
            **self._base_payload(),
            "service_order_mode": Agenda.ServiceOrderMode.DESIGNATED,
            "designated_users": [self.inactive_user.id],
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("designated_users", response.data)

    def test_patch_team_to_designated_requires_operational_fields_removed(self):
        agenda = Agenda.objects.create(
            title="Agenda operacional",
            description="Com equipe",
            date=date(2026, 7, 21),
            start_time=time(9, 0),
            end_time=time(12, 0),
            location="Centro",
            team_name=self.team_a.name,
            team_ref=self.team_a,
            chief_name=self.chief.name,
            chief_ref=self.chief,
            agents=self.agent.name,
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            status=Agenda.Status.PENDING,
        )
        agenda.agents_ref.add(self.agent)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {"service_order_mode": Agenda.ServiceOrderMode.DESIGNATED, "designated_users": [self.user_one.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_order_mode", response.data)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {
                "service_order_mode": Agenda.ServiceOrderMode.DESIGNATED,
                "designated_users": [self.user_one.id],
                "team_ref": None,
                "team_name": "",
                "chief_ref": None,
                "chief_name": "",
                "team_phone": "",
                "agents_ref": [],
                "agents": "",
                "support_1_ref": None,
                "support_1": "",
                "support_2_ref": None,
                "support_2": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.service_order_mode, Agenda.ServiceOrderMode.DESIGNATED)
        self.assertEqual(list(agenda.designated_users.values_list("id", flat=True)), [self.user_one.id])

    def test_patch_designated_to_team_requires_designated_users_empty(self):
        agenda = Agenda.objects.create(
            title="Agenda designada",
            description="Somente participantes",
            date=date(2026, 7, 22),
            start_time=time(10, 0),
            end_time=time(13, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            status=Agenda.Status.PENDING,
            service_order_mode=Agenda.ServiceOrderMode.DESIGNATED,
        )
        agenda.designated_users.set([self.user_one])

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {
                "service_order_mode": Agenda.ServiceOrderMode.TEAM,
                "team_ref": self.team_a.id,
                "chief_ref": self.chief.id,
                "agents_ref": [self.agent.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("designated_users", response.data)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {
                "service_order_mode": Agenda.ServiceOrderMode.TEAM,
                "designated_users": [],
                "team_ref": self.team_a.id,
                "team_name": self.team_a.name,
                "chief_ref": self.chief.id,
                "chief_name": self.chief.name,
                "agents_ref": [self.agent.id],
                "agents": self.agent.name,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.service_order_mode, Agenda.ServiceOrderMode.TEAM)
        self.assertFalse(agenda.designated_users.exists())


class AgendaDesignatedPermissionsTests(APITestCase):
    def setUp(self):
        self.sector = Sector.objects.get_or_create(name="Hotel")[0]
        self.admin = User.objects.create_user(email="admin-perm@test.com", password="pwd", role=User.Role.ADMIN, full_name="Admin")
        self.designated = User.objects.create_user(email="designated@test.com", password="pwd", role=User.Role.SUPPORT, full_name="Designado", sector=self.sector)
        self.other = User.objects.create_user(email="other@test.com", password="pwd", role=User.Role.USER, full_name="Outro", sector=self.sector)
        self.agenda = Agenda.objects.create(
            title="Agenda acesso",
            description="Teste",
            date=date(2026, 7, 23),
            start_time=time(14, 0),
            end_time=time(16, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            status=Agenda.Status.APPROVED,
            service_order_mode=Agenda.ServiceOrderMode.DESIGNATED,
        )
        self.agenda.designated_users.set([self.designated])

    def test_designated_user_can_view_agenda(self):
        self.client.force_authenticate(self.designated)
        response = self.client.get(reverse("agendas-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if "results" in response.data else response.data
        self.assertEqual([row["id"] for row in rows], [self.agenda.id])

    def test_non_designated_user_does_not_gain_access(self):
        self.client.force_authenticate(self.other)
        response = self.client.get(reverse("agendas-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(rows, [])


class DesignatedAttendanceHelperTests(TestCase):
    def setUp(self):
        self.sector = Sector.objects.get_or_create(name="Escala")[0]
        self.team_a = Team.objects.get_or_create(name="ALFA", defaults={"is_active": True})[0]
        self.team_b = Team.objects.get_or_create(name="BRAVO", defaults={"is_active": True})[0]
        self.admin = User.objects.create_user(email="admin-helper@test.com", password="pwd", role=User.Role.ADMIN, full_name="Admin")
        self.support_user = User.objects.create_user(email="support-helper@test.com", password="pwd", role=User.Role.SUPPORT, full_name="Apoio Helper", cpf="12345678901", sector=self.sector, is_active=True)
        self.agent_user = User.objects.create_user(email="agent-helper@test.com", password="pwd", role=User.Role.USER, full_name="Agente Helper", cpf="98765432100", sector=self.sector, is_active=True)
        self.inactive_user = User.objects.create_user(email="inactive-helper@test.com", password="pwd", role=User.Role.USER, full_name="Inativo Helper", cpf="22233344455", sector=self.sector, is_active=False)
        self.support_lookup = Support.objects.create(name="Apoio Helper", cpf="12345678901", source_id=f"user:{self.support_user.id}", team=self.team_a, is_active=True)
        self.agent_lookup = Agent.objects.create(name="Agente Helper", cpf="98765432100", source_id=f"user:{self.agent_user.id}", team=self.team_b, is_active=True)
        Agent.objects.create(name="Inativo Helper", cpf="22233344455", source_id=f"user:{self.inactive_user.id}", team=self.team_b, is_active=True)
        self.schedule = ShiftSchedule.objects.create(date=date(2026, 7, 24), team=self.team_a, created_by=self.admin)
        self.schedule.extra_supports.add(self.support_lookup)
        self.agenda = Agenda.objects.create(
            title="Agenda helper",
            description="Teste helper",
            date=date(2026, 7, 24),
            start_time=time(8, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            status=Agenda.Status.APPROVED,
            team_ref=self.team_a,
        )

    def test_designated_mode_returns_only_selected_keys(self):
        self.agenda.service_order_mode = Agenda.ServiceOrderMode.DESIGNATED
        self.agenda.save(update_fields=["service_order_mode"])
        self.agenda.designated_users.set([self.support_user, self.agent_user, self.inactive_user])

        keys = get_expected_attendance_member_keys(self.agenda, self.schedule)
        self.assertEqual(keys, {f"SUPPORT_{self.support_lookup.id}", f"AGENT_{self.agent_lookup.id}"})

    def test_team_mode_delegates_to_existing_helper(self):
        self.agenda.service_order_mode = Agenda.ServiceOrderMode.TEAM
        self.agenda.save(update_fields=["service_order_mode"])
        expected = get_expected_member_keys(self.schedule)
        received = get_expected_attendance_member_keys(self.agenda, self.schedule)
        self.assertEqual(received, expected)
