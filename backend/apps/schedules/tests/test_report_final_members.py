from datetime import date, time

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.models import User
from apps.schedules.models import Agenda, Agent, Chief, Sector, ShiftSchedule, ShiftSwapRequest, Support, Team
from apps.schedules.serializers import ShiftScheduleSerializer
from apps.schedules.services import (
    get_effective_members,
    get_expected_attendance_member_keys,
)


class ReportFinalMembersTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="report-members@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Administrador",
        )
        self.sector = Sector.objects.get_or_create(name="Educacao")[0]
        self.team = Team.objects.create(name="EQUIPE TESTE", is_active=True)
        self.other_team = Team.objects.create(name="EQUIPE EXTRA", is_active=True)
        self.operation_date = date(2026, 8, 5)
        self.schedule = ShiftSchedule.objects.create(
            date=self.operation_date,
            team=self.team,
            created_by=self.admin,
        )
        self.chief = Chief.objects.create(
            name="Chefe da OS",
            team=self.team,
            is_active=True,
            source_id="user:101",
        )
        self.kept_agent = Agent.objects.create(
            name="Agente Mantido",
            team=self.team,
            is_active=True,
            source_id="user:102",
        )
        self.removed_agent = Agent.objects.create(
            name="Agente Removido",
            team=self.team,
            is_active=True,
            source_id="user:103",
        )
        self.omitted_team_agent = Agent.objects.create(
            name="Agente Fora da OS",
            team=self.team,
            is_active=True,
            source_id="user:104",
        )
        self.extra_agent = Agent.objects.create(
            name="Agente Extra",
            team=self.other_team,
            is_active=True,
            source_id="external-directory:105",
        )
        self.support = Support.objects.create(
            name="Apoio da OS",
            team=self.team,
            is_active=True,
            source_id="user:106",
        )
        self.agenda = Agenda.objects.create(
            title="OS com efetivo final",
            description="Teste",
            date=self.operation_date,
            start_time=time(8, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            team_ref=self.team,
            chief_ref=self.chief,
            support_1_ref=self.support,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
        )
        self.agenda.agents_ref.set([self.kept_agent, self.removed_agent])
        self.schedule.removed_agents.add(self.removed_agent)
        self.schedule.extra_agents.add(self.extra_agent, self.kept_agent)

    def test_shift_schedule_composition_drives_report_and_attendance(self):
        members = get_effective_members(self.schedule, self.agenda)
        agent_names = [member["name"] for member in members["agents"]]

        self.assertEqual(agent_names.count("Agente Mantido"), 1)
        self.assertIn("Agente Extra", agent_names)
        self.assertNotIn("Agente Removido", agent_names)
        self.assertIn("Agente Fora da OS", agent_names)
        self.assertEqual([member["name"] for member in members["chiefs"]], ["Chefe da OS"])
        self.assertEqual([member["name"] for member in members["supports"]], ["Apoio da OS"])

        expected = get_expected_attendance_member_keys(self.agenda, self.schedule)
        self.assertEqual(
            expected,
            {
                f"CHIEF_{self.chief.id}",
                f"AGENT_{self.omitted_team_agent.id}",
                f"AGENT_{self.kept_agent.id}",
                f"AGENT_{self.extra_agent.id}",
                f"SUPPORT_{self.support.id}",
            },
        )

    def test_shift_schedule_without_context_keeps_same_effective_extra_once(self):
        legacy_members = get_effective_members(self.schedule)
        contextual_members = get_effective_members(self.schedule, self.agenda)

        legacy_agent_names = [member["name"] for member in legacy_members["agents"]]
        contextual_agent_names = [member["name"] for member in contextual_members["agents"]]
        self.assertIn("Agente Extra", legacy_agent_names)
        self.assertIn("Agente Extra", contextual_agent_names)
        self.assertEqual(contextual_agent_names.count("Agente Mantido"), 1)
        self.assertEqual(contextual_agent_names.count("Agente Extra"), 1)

    def test_schedule_payload_uses_the_linked_shift_schedule_composition(self):
        request = APIRequestFactory().get(
            f"/api/shift-schedules/{self.schedule.id}/?agenda={self.agenda.id}"
        )
        request.user = self.admin

        payload = ShiftScheduleSerializer(
            self.schedule,
            context={"request": request, "context_agenda": self.agenda},
        ).data

        agent_names = [member["name"] for member in payload["members"]["agents"]]
        self.assertEqual(agent_names.count("Agente Mantido"), 1)
        self.assertIn("Agente Extra", agent_names)
        self.assertNotIn("Agente Removido", agent_names)
        self.assertIn("Agente Fora da OS", agent_names)
        self.assertTrue(payload["members"]["context_resolved"])

    def test_context_ignores_inactive_references_and_keeps_two_supports_separate(self):
        inactive_agent = Agent.objects.create(
            name="Agente Inativo",
            team=self.team,
            is_active=False,
        )
        second_support = Support.objects.create(
            name="Segundo Apoio",
            team=self.team,
            is_active=True,
            source_id="user:107",
        )
        self.agenda.agents_ref.set([inactive_agent])
        self.agenda.support_2_ref = second_support
        self.agenda.save(update_fields=["support_2_ref"])

        members = get_effective_members(self.schedule, self.agenda)

        self.assertNotIn("Agente Inativo", [member["name"] for member in members["agents"]])
        self.assertCountEqual(
            [member["name"] for member in members["supports"]],
            ["Apoio da OS", "Segundo Apoio"],
        )

    def test_context_with_null_references_still_uses_shift_schedule(self):
        empty_agenda = Agenda.objects.create(
            title="OS sem referencias", description="Teste", date=self.operation_date,
            start_time=time(8), end_time=time(12), location="Centro", responsible=self.admin,
            sector=self.sector, created_by=self.admin, team_ref=self.team,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
        )

        members = get_effective_members(self.schedule, empty_agenda)

        self.assertTrue(members["context_resolved"])
        self.assertEqual([member["name"] for member in members["chiefs"]], ["Chefe da OS"])
        self.assertCountEqual(
            [member["name"] for member in members["agents"]],
            ["Agente Extra", "Agente Fora da OS", "Agente Mantido"],
        )
        self.assertEqual([member["name"] for member in members["supports"]], ["Apoio da OS"])

    def test_contextual_swap_only_replaces_a_member_that_belongs_to_the_service_order(self):
        replacement = Agent.objects.create(name="Substituto", team=self.other_team, is_active=True)
        ShiftSwapRequest.objects.create(
            schedule=self.schedule,
            requester=self.admin,
            member_type=ShiftSwapRequest.MemberType.AGENT,
            from_member_id=self.kept_agent.id,
            from_member_name=self.kept_agent.name,
            target_team=self.other_team,
            to_member_id=replacement.id,
            to_member_name=replacement.name,
            status=ShiftSwapRequest.Status.APPROVED,
            decided_by=self.admin,
        )
        members = get_effective_members(self.schedule, self.agenda)
        self.assertIn("Substituto", [member["name"] for member in members["agents"]])
        self.assertNotIn("Agente Mantido", [member["name"] for member in members["agents"]])

    def test_contextual_swap_replaces_any_member_that_belongs_to_the_shift_schedule(self):
        replacement = Agent.objects.create(name="Substituto Indevido", team=self.other_team, is_active=True)
        ShiftSwapRequest.objects.create(
            schedule=self.schedule,
            requester=self.admin,
            member_type=ShiftSwapRequest.MemberType.AGENT,
            from_member_id=self.omitted_team_agent.id,
            from_member_name=self.omitted_team_agent.name,
            target_team=self.other_team,
            to_member_id=replacement.id,
            to_member_name=replacement.name,
            status=ShiftSwapRequest.Status.APPROVED,
            decided_by=self.admin,
        )
        members = get_effective_members(self.schedule, self.agenda)
        self.assertIn("Substituto Indevido", [member["name"] for member in members["agents"]])


class ShiftScheduleAgendaContextApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="context-admin@test.com", password="pwd", role=User.Role.ADMIN, full_name="Admin"
        )
        self.team = Team.objects.create(name="CONTEXTO ALFA", is_active=True)
        self.other_team = Team.objects.create(name="CONTEXTO BRAVO", is_active=True)
        self.sector = Sector.objects.get_or_create(name=self.team.name)[0]
        self.operation_date = date(2026, 8, 5)
        self.schedule = ShiftSchedule.objects.create(date=self.operation_date, team=self.team, created_by=self.admin)
        self.agent = Agent.objects.create(name="Agente Alfa", team=self.team, is_active=True)
        self.agenda = Agenda.objects.create(
            title="OS valida", description="Teste", date=self.operation_date,
            start_time=time(8), end_time=time(12), location="Centro", responsible=self.admin,
            sector=self.sector, created_by=self.admin, team_ref=self.team,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
        )
        self.agenda.agents_ref.add(self.agent)
        self.url = f"/api/shift-schedules/{self.schedule.id}/"
        self.client.force_authenticate(self.admin)

    def _agenda(self, **overrides):
        values = {
            "title": "Outra OS", "description": "Teste", "date": self.operation_date,
            "start_time": time(8), "end_time": time(12), "location": "Centro",
            "responsible": self.admin, "sector": self.sector, "created_by": self.admin,
            "team_ref": self.team, "service_order_mode": Agenda.ServiceOrderMode.TEAM,
        }
        values.update(overrides)
        return Agenda.objects.create(**values)

    def test_valid_context_and_legacy_payload_are_distinct(self):
        contextual = self.client.get(f"{self.url}?agenda={self.agenda.id}")
        legacy = self.client.get(self.url)
        self.assertEqual(contextual.status_code, status.HTTP_200_OK, contextual.data)
        self.assertTrue(contextual.data["members"]["context_resolved"])
        self.assertEqual(legacy.status_code, status.HTTP_200_OK, legacy.data)
        self.assertFalse(legacy.data["members"]["context_resolved"])

    def test_invalid_context_parameters_are_rejected_without_legacy_fallback(self):
        self.assertEqual(self.client.get(f"{self.url}?agenda=abc").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(f"{self.url}?agenda=999999").status_code, status.HTTP_404_NOT_FOUND)
        other_date = self._agenda(date=date(2026, 8, 6))
        self.assertEqual(self.client.get(f"{self.url}?agenda={other_date.id}").status_code, status.HTTP_400_BAD_REQUEST)
        other_team = self._agenda(team_ref=self.other_team)
        self.assertEqual(self.client.get(f"{self.url}?agenda={other_team.id}").status_code, status.HTTP_400_BAD_REQUEST)
        designated = self._agenda(service_order_mode=Agenda.ServiceOrderMode.DESIGNATED)
        response = self.client.get(f"{self.url}?agenda={designated.id}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("modo equipe", str(response.data))

    def test_schedule_reader_without_agenda_access_receives_not_found(self):
        reader = User.objects.create_user(
            email="context-reader@test.com", password="pwd", role=User.Role.USER,
            full_name="Leitor", sector=self.sector,
        )
        hidden = self._agenda(team_ref=self.other_team)
        self.client.force_authenticate(reader)
        response = self.client.get(f"{self.url}?agenda={hidden.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_supervisor_calendar_view_cannot_expand_agenda_context_access(self):
        supervisor = User.objects.create_user(
            email="context-supervisor@test.com", password="pwd", role=User.Role.SUPERVISOR,
            full_name="Supervisor", sector=self.sector,
        )
        hidden = self._agenda(team_ref=self.other_team)
        self.client.force_authenticate(supervisor)

        response = self.client.get(
            f"{self.url}?agenda={hidden.id}&calendar_view=1"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotIn("members", response.data)
