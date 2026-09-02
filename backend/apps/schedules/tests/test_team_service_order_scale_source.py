from datetime import date, time

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agenda, Agent, Chief, EducationReport, Sector, ShiftSchedule, Support, Team


class TeamServiceOrderScaleSourceTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="team-scale@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin Escala",
        )
        self.client.force_authenticate(self.admin)
        self.team = Team.objects.get_or_create(name="DELTA OS ESCALA", defaults={"is_active": True})[0]
        self.other_team = Team.objects.get_or_create(name="ECHO OS ESCALA", defaults={"is_active": True})[0]
        self.sector = Sector.objects.get_or_create(name="Educacao")[0]
        self.operation_date = date(2026, 9, 2)
        self.schedule = ShiftSchedule.objects.create(
            date=self.operation_date,
            team=self.team,
            created_by=self.admin,
        )
        self.chief = Chief.objects.create(name="Chefe Delta", team=self.team, is_active=True)
        self.agent = Agent.objects.create(name="Agente Delta", team=self.team, is_active=True)
        self.support = Support.objects.create(name="Apoio Delta", team=self.team, is_active=True)
        self.url = reverse("agendas-list")

    def _base_payload(self):
        return {
            "title": "Ordem operacional",
            "description": "Teste",
            "date": self.operation_date.isoformat(),
            "start_time": "08:00",
            "end_time": "12:00",
            "location": "Centro",
            "responsible": self.admin.id,
            "sector": self.sector.id,
            "status": Agenda.Status.PENDING,
            "origin": Agenda.Origin.INTERNAL,
            "service_order_mode": Agenda.ServiceOrderMode.TEAM,
            "team_ref": self.team.id,
        }

    def test_team_service_order_accepts_team_present_in_shift_schedule(self):
        response = self.client.post(self.url, self._base_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        agenda = Agenda.objects.get(id=response.data["id"])
        self.assertEqual(agenda.team_ref_id, self.team.id)
        self.assertEqual(agenda.team_name, self.team.name)

    def test_team_service_order_rejects_team_missing_from_shift_schedule(self):
        payload = self._base_payload()
        payload["team_ref"] = self.other_team.id
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("team_ref", response.data)

    def test_team_service_order_rejects_direct_staff_payload(self):
        payload = self._base_payload()
        payload["chief_ref"] = self.chief.id
        payload["agents_ref"] = [self.agent.id]
        payload["support_1_ref"] = self.support.id
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_order_mode", response.data)

    def test_team_service_order_rejects_even_empty_direct_staff_fields_on_create(self):
        invalid_values = {
            "chief_ref": None,
            "agents_ref": [],
            "agents": "",
            "support_1_ref": None,
            "support_2_ref": None,
            "chief_name": "",
            "team_phone": "",
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field):
                payload = self._base_payload()
                payload[field] = value
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
                self.assertIn("service_order_mode", response.data)

    def test_team_service_order_rejects_empty_direct_staff_fields_on_patch_without_clearing_legacy_data(self):
        agenda = Agenda.objects.create(
            title="OS legado protegida",
            description="Teste",
            date=self.operation_date,
            start_time=time(8, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
            team_ref=self.team,
            team_name=self.team.name,
            chief_ref=self.chief,
            chief_name="Chefe legado",
            team_phone="21999999999",
            agents="Agente legado",
            support_1_ref=self.support,
            support_1="Apoio legado 1",
            support_2="Apoio legado 2",
        )
        agenda.agents_ref.add(self.agent)
        invalid_values = {
            "chief_ref": None,
            "agents_ref": [],
            "agents": "",
            "support_1_ref": None,
            "support_2_ref": None,
            "chief_name": "",
            "team_phone": "",
        }
        original = {
            "chief_ref_id": agenda.chief_ref_id,
            "chief_name": agenda.chief_name,
            "team_phone": agenda.team_phone,
            "agents": agenda.agents,
            "agent_ids": list(agenda.agents_ref.values_list("id", flat=True)),
            "support_1_ref_id": agenda.support_1_ref_id,
            "support_1": agenda.support_1,
            "support_2_ref_id": agenda.support_2_ref_id,
            "support_2": agenda.support_2,
        }
        detail_url = reverse("agendas-detail", args=[agenda.id])
        for field, value in invalid_values.items():
            with self.subTest(field=field):
                response = self.client.patch(detail_url, {field: value}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
                agenda.refresh_from_db()
                self.assertEqual(agenda.chief_ref_id, original["chief_ref_id"])
                self.assertEqual(agenda.chief_name, original["chief_name"])
                self.assertEqual(agenda.team_phone, original["team_phone"])
                self.assertEqual(agenda.agents, original["agents"])
                self.assertEqual(list(agenda.agents_ref.values_list("id", flat=True)), original["agent_ids"])
                self.assertEqual(agenda.support_1_ref_id, original["support_1_ref_id"])
                self.assertEqual(agenda.support_1, original["support_1"])
                self.assertEqual(agenda.support_2_ref_id, original["support_2_ref_id"])
                self.assertEqual(agenda.support_2, original["support_2"])

    def test_team_service_order_reads_effective_staff_from_shift_schedule(self):
        agenda = Agenda.objects.create(
            title="OS leitura",
            description="Teste",
            date=self.operation_date,
            start_time=time(8, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
            team_ref=self.team,
            team_name=self.team.name,
            chief_name="Legado divergente",
            agents="Legado divergente",
            support_1="Legado divergente",
        )
        extra_agent = Agent.objects.create(name="Agente Extra", team=self.other_team, is_active=True)
        self.schedule.extra_agents.add(extra_agent)

        response = self.client.get(reverse("agendas-detail", args=[agenda.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["staff_source"], "SHIFT_SCHEDULE")
        self.assertEqual(response.data["shift_schedule_id"], self.schedule.id)
        self.assertFalse(response.data["shift_schedule_missing"])
        self.assertIn("Agente Extra", [member["name"] for member in response.data["effective_staff"]["agents"]])
        self.assertEqual(response.data["effective_staff_warning"], "")

    def test_shift_schedule_uses_operational_roster_without_imported_duplicates(self):
        operational = Agent.objects.create(
            name="Agente Operacional Vinculado",
            team=self.team,
            is_active=True,
            source_id="user:404",
        )
        duplicate_link = Agent.objects.create(
            name="Agente Duplicado Mesmo Vinculo",
            team=self.team,
            is_active=True,
            source_id="user:404",
        )
        imported = Agent.objects.create(
            name="Agente Importado Horus",
            team=self.team,
            is_active=True,
            source_id="horus:404",
        )
        explicit_extra = Agent.objects.create(
            name="Agente Extra Importado",
            team=self.other_team,
            is_active=True,
            source_id="horus:405",
        )
        self.schedule.extra_agents.add(explicit_extra)

        agenda = Agenda.objects.create(
            title="OS sem duplicidade",
            description="Teste",
            date=self.operation_date,
            start_time=time(8, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
            team_ref=self.team,
            team_name=self.team.name,
        )
        response = self.client.get(reverse("agendas-detail", args=[agenda.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agents = response.data["effective_staff"]["agents"]
        agent_ids = [member["id"] for member in agents]
        agent_names = [member["name"] for member in agents]

        self.assertEqual(len([member for member in agents if member.get("source_id") == "user:404"]), 1)
        self.assertNotIn(imported.id, agent_ids)
        self.assertNotIn("Agente Importado Horus", agent_names)
        self.assertIn("Agente Extra Importado", agent_names)

    def test_legacy_team_service_order_without_shift_schedule_returns_warning_without_500(self):
        legacy = Agenda.objects.create(
            title="OS antiga",
            description="Teste",
            date=date(2026, 9, 3),
            start_time=time(9, 0),
            end_time=time(11, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
            team_ref=self.team,
            team_name=self.team.name,
            chief_name="Chefe legado",
            agents="Agente legado",
            support_1="Apoio legado",
        )
        response = self.client.get(reverse("agendas-detail", args=[legacy.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["shift_schedule_missing"])
        self.assertEqual(response.data["effective_staff_warning"], "Efetivo não localizado na Escala para esta data.")
        self.assertEqual(response.data["staff_source"], "LEGACY_SERVICE_ORDER")

    def test_agenda_list_preloads_scale_members_without_per_order_queries(self):
        def create_team_agenda(index):
            team = Team.objects.create(name=f"N+1 Escala {index}", is_active=True)
            ShiftSchedule.objects.create(date=self.operation_date, team=team, created_by=self.admin)
            Agent.objects.create(
                name=f"Agente N+1 {index}",
                team=team,
                is_active=True,
                source_id=f"user:{700 + index}",
            )
            return Agenda.objects.create(
                title=f"OS N+1 {index}",
                description="Teste",
                date=self.operation_date,
                start_time=time(8, 0),
                end_time=time(12, 0),
                location="Centro",
                responsible=self.admin,
                sector=self.sector,
                created_by=self.admin,
                service_order_mode=Agenda.ServiceOrderMode.TEAM,
                team_ref=team,
                team_name=team.name,
            )

        create_team_agenda(1)
        with CaptureQueriesContext(connection) as single_context:
            single_response = self.client.get(f"{self.url}?date={self.operation_date.isoformat()}")
        self.assertEqual(single_response.status_code, status.HTTP_200_OK, single_response.data)

        for index in range(2, 6):
            create_team_agenda(index)
        with CaptureQueriesContext(connection) as many_context:
            many_response = self.client.get(f"{self.url}?date={self.operation_date.isoformat()}")
        self.assertEqual(many_response.status_code, status.HTTP_200_OK, many_response.data)
        self.assertLessEqual(
            len(many_context),
            len(single_context) + 4,
            f"A listagem realizou consultas por OS: 1 OS={len(single_context)}, 5 OS={len(many_context)}",
        )

    def test_approved_report_and_its_attendance_cannot_be_changed_by_later_scale_edits(self):
        agenda = Agenda.objects.create(
            title="OS histórico aprovado",
            description="Teste",
            date=self.operation_date,
            start_time=time(8, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
            team_ref=self.team,
            team_name=self.team.name,
        )
        report = EducationReport.objects.create(
            agenda=agenda,
            operation_date=self.operation_date,
            team=self.team.name,
            education_agents="Chefia: histórico aprovado\nAgentes: histórico aprovado",
            status=EducationReport.ReportStatus.APPROVED,
            accessibility_conditions_met="YES",
            created_by=self.admin,
        )
        original_checked_members = {f"AGENT_{self.agent.id}": {"is_absent": False}}
        self.schedule.checked_members = original_checked_members
        self.schedule.save(update_fields=["checked_members"])

        response = self.client.patch(
            reverse("shift-schedules-detail", args=[self.schedule.id]),
            {"checked_members": {}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.checked_members, original_checked_members)

        response = self.client.post(
            reverse("shift-schedules-member-change", args=[self.schedule.id]),
            {
                "action": "REMOVED",
                "member_type": "AGENT",
                "member_id": self.agent.id,
                "reason": "Tentativa posterior",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertFalse(self.schedule.removed_agents.filter(id=self.agent.id).exists())

        response = self.client.get(f"/api/education-reports/{report.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["education_agents"], report.education_agents)


class ShiftScheduleDeleteProtectionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="delete-scale@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin",
        )
        self.client.force_authenticate(self.admin)
        self.team = Team.objects.get_or_create(name="HOTEL OS ESCALA", defaults={"is_active": True})[0]
        self.sector = Sector.objects.get_or_create(name="Educacao")[0]
        self.schedule = ShiftSchedule.objects.create(
            date=date(2026, 9, 2),
            team=self.team,
            created_by=self.admin,
        )
        Agenda.objects.create(
            title="OS vinculada",
            description="Teste",
            date=self.schedule.date,
            start_time=time(8, 0),
            end_time=time(12, 0),
            location="Centro",
            responsible=self.admin,
            sector=self.sector,
            created_by=self.admin,
            status=Agenda.Status.APPROVED,
            service_order_mode=Agenda.ServiceOrderMode.TEAM,
            team_ref=self.team,
            team_name=self.team.name,
        )

    def test_delete_schedule_with_linked_team_service_order_is_blocked(self):
        response = self.client.delete(reverse("shift-schedules-detail", args=[self.schedule.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Ordens de Serviço ativas vinculadas", str(response.data))
