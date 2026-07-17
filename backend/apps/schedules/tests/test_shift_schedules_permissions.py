from datetime import date, time
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from apps.accounts.models import User
from apps.schedules.models import ShiftSchedule, Team, Agent, Chief, Support, Agenda, Sector

class ShiftSchedulePermissionsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.team1, _ = Team.objects.get_or_create(name="ALFA")
        self.team2, _ = Team.objects.get_or_create(name="BRAVO")

        self.admin = User.objects.create_user(
            email="admin@test.com", password="pwd", role="ADMIN", full_name="Admin User"
        )
        self.no_link_user = User.objects.create_user(
            email="none@test.com", password="pwd", role="USER", full_name="John Doe", cpf="111.111.111-11"
        )
        
        self.agent1_user = User.objects.create_user(
            email="agent1@test.com", password="pwd", role="USER", full_name="Carlos Silva", cpf="222.222.222-22"
        )
        self.agent2_user_same_name = User.objects.create_user(
            email="agent2@test.com", password="pwd", role="USER", full_name="Carlos Silva", cpf="333.333.333-33"
        )
        self.agent_empty_cpf = User.objects.create_user(
            email="empty_cpf@test.com", password="pwd", role="USER", full_name="Pedro Paulo", cpf=""
        )

        self.agent_record = Agent.objects.create(
            name="Carlos Silva", cpf="22222222222", source_id="user:9999"  # Simulando source_id diferente ou legado
        )
        self.agent_record2 = Agent.objects.create(
            name="Pedro Paulo", cpf="44444444444", source_id="user:8888" # CPF diferente, source diferente, mesmo nome de agent_empty_cpf
        )

        self.schedule_alfa = ShiftSchedule.objects.create(
            date=date(2026, 7, 10), team=self.team1, created_by=self.admin
        )
        self.schedule_alfa.extra_agents.add(self.agent_record)
        
        self.schedule_bravo = ShiftSchedule.objects.create(
            date=date(2026, 7, 11), team=self.team2, created_by=self.admin
        )
        self.schedule_bravo.extra_agents.add(self.agent_record2)

        self.url = reverse('shift-schedules-list')

    def test_admin_sees_all(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 2)

    def test_no_link_user_sees_none(self):
        self.client.force_authenticate(user=self.no_link_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Deve ser None e não vazar escalas!
        self.assertEqual(len(res.data['results']), 0)

    def test_fallback_cpf_matches_properly(self):
        # Carlos Silva com CPF 222 tem que ver a escala ALFA pelo fallback de CPF
        self.client.force_authenticate(user=self.agent1_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['team_name'], "ALFA")

    def test_same_name_different_cpf_does_not_share_schedule(self):
        # Carlos Silva com CPF 333 (não cadastrado como Agent com esse CPF) 
        # NÃO pode ver a escala do Carlos Silva do CPF 222
        self.client.force_authenticate(user=self.agent2_user_same_name)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 0)

    def test_empty_cpf_does_not_match_by_name_alone(self):
        # Pedro Paulo não tem CPF e não tem setor associado. 
        # Mesmo existindo um Agent "Pedro Paulo" com CPF 444, ele não deve cruzar dados
        self.client.force_authenticate(user=self.agent_empty_cpf)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 0)

    def test_empty_cpf_matches_by_name_and_sector(self):
        # Se Pedro Paulo não tem CPF, ele só cruza se o nome for idêntico e a equipe for idêntica
        from apps.schedules.models import Sector
        sector, _ = Sector.objects.get_or_create(name="BRAVO")
        self.agent_empty_cpf.sector = sector
        self.agent_empty_cpf.save()
        self.client.force_authenticate(user=self.agent_empty_cpf)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Ele bate por team_id de qualquer jeito (porque q_filter |= team_id=user.sector_id)
        # Mas o fallback do agent_ids também vai rolar porque name e team_id batem
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['team_name'], "BRAVO")




    def test_support_list_hides_user_bound_record_when_linked_user_is_inactive(self):
        support_team, _ = Team.objects.get_or_create(name="INDIA")
        inactive_user = User.objects.create_user(
            email="apoio.inativo@test.com",
            password="pwd",
            role=User.Role.SUPPORT,
            full_name="Ronaldo de Almeida Rodrigues",
            cpf="98765432100",
            is_active=False,
        )
        Support.objects.create(
            name="Ronaldo de Almeida Rodrigues",
            cpf="98765432100",
            team=support_team,
            role="APOIO",
            is_active=True,
            source_id=f"user:{inactive_user.id}",
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("supports-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if "results" in response.data else response.data
        self.assertNotIn("Ronaldo de Almeida Rodrigues", [row["name"] for row in rows])

class SupportListSyncResilienceTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-supports@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin Supports",
        )
        self.team, _ = Team.objects.get_or_create(name="HOTEL")

    def test_supports_list_ignores_sync_conflict_and_returns_200(self):
        suffix = "500001"
        conflict_user = User.objects.create_user(
            email=f"support-conflict-{suffix}@test.com",
            password="pwd",
            role=User.Role.SUPPORT,
            full_name=f"Apoio Conflito {suffix}",
            cpf=f"91{suffix}001",
            is_active=True,
        )
        Support.objects.create(
            name=f"Nome CPF {suffix}",
            cpf=f"91{suffix}001",
            team=self.team,
            role="APOIO",
            is_active=True,
        )
        Support.objects.create(
            name=f"Apoio Conflito {suffix}",
            cpf=f"93{suffix}003",
            team=self.team,
            role="APOIO",
            is_active=True,
        )
        healthy_user = User.objects.create_user(
            email="support-healthy@test.com",
            password="pwd",
            role=User.Role.SUPPORT,
            full_name="Apoio Saudavel",
            cpf="94999999999",
            is_active=True,
        )
        Support.objects.create(
            name="Apoio Saudavel",
            cpf="94999999999",
            team=self.team,
            role="APOIO",
            is_active=True,
            source_id=f"user:{healthy_user.id}",
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("supports-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if "results" in response.data else response.data
        names = [row["name"] for row in rows]
        self.assertIn("Apoio Saudavel", names)
        self.assertIn("Apoio Conflito 500001", names)
        self.assertIn("Nome CPF 500001", names)

class ShiftScheduleDeleteSyncTests(APITestCase):
    def setUp(self):
        self.team, _ = Team.objects.get_or_create(name="HOTEL")
        self.team_sector, _ = Sector.objects.get_or_create(name="HOTEL")
        self.request_sector, _ = Sector.objects.get_or_create(name="Solicitacoes internas")
        self.admin = User.objects.create_user(
            email="admin-scale@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin Escala",
        )
        self.chief_user = User.objects.create_user(
            email="chefe-hotel@test.com",
            password="pwd",
            role=User.Role.SUPERVISOR,
            full_name="Chefe Hotel",
            cpf="12345678901",
            sector=self.team_sector,
        )
        self.chief = Chief.objects.create(
            name="Chefe Hotel",
            cpf="12345678901",
            team=self.team,
            is_active=True,
            source_id=f"user:{self.chief_user.id}",
        )
        self.agent = Agent.objects.create(
            name="Agente Hotel",
            cpf="10987654321",
            team=self.team,
            is_active=True,
        )
        self.schedule = ShiftSchedule.objects.create(
            date=date(2026, 7, 18),
            team=self.team,
            created_by=self.admin,
        )
        self.agenda = Agenda.objects.create(
            title="Acao de teste",
            description="Agenda aprovada",
            date=date(2026, 7, 18),
            start_time=time(10, 0),
            end_time=time(12, 0),
            location="Centro",
            team_name=self.team.name,
            team_ref=self.team,
            chief_name=self.chief.name,
            chief_ref=self.chief,
            team_phone="21999999999",
            agents="Agente Hotel",
            responsible=self.admin,
            sector=self.request_sector,
            created_by=self.admin,
            status=Agenda.Status.APPROVED,
        )
        self.agenda.agents_ref.add(self.agent)

    def test_deleting_schedule_clears_agenda_assignment_and_removes_chief_calendar_visibility(self):
        self.client.force_authenticate(self.chief_user)
        before = self.client.get(
            reverse("agendas-list"),
            {"date_from": "2026-07-01", "date_to": "2026-07-31"},
        )
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        before_rows = before.data["results"] if "results" in before.data else before.data
        self.assertEqual([row["id"] for row in before_rows], [self.agenda.id])

        self.client.force_authenticate(self.admin)
        delete_response = self.client.delete(reverse("shift-schedules-detail", args=[self.schedule.id]))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        self.agenda.refresh_from_db()
        self.assertEqual(self.agenda.team_name, "")
        self.assertIsNone(self.agenda.team_ref)
        self.assertEqual(self.agenda.chief_name, "")
        self.assertIsNone(self.agenda.chief_ref)
        self.assertEqual(self.agenda.team_phone, "")
        self.assertEqual(self.agenda.agents, "")
        self.assertFalse(self.agenda.agents_ref.exists())

        self.client.force_authenticate(self.chief_user)
        after = self.client.get(
            reverse("agendas-list"),
            {"date_from": "2026-07-01", "date_to": "2026-07-31"},
        )
        self.assertEqual(after.status_code, status.HTTP_200_OK)
        after_rows = after.data["results"] if "results" in after.data else after.data
        self.assertEqual(after_rows, [])


class ShiftScheduleAttendanceWorkflowTests(APITestCase):
    def setUp(self):
        self.team, _ = Team.objects.get_or_create(name="DELTA")
        self.team_sector, _ = Sector.objects.get_or_create(name="DELTA")
        self.admin = User.objects.create_user(
            email="admin-attendance@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin Attendance",
        )
        self.manager = User.objects.create_user(
            email="manager-attendance@test.com",
            password="pwd",
            role=User.Role.MANAGER,
            full_name="Manager Attendance",
        )
        self.chief_user = User.objects.create_user(
            email="chief-attendance@test.com",
            password="pwd",
            role=User.Role.SUPERVISOR,
            full_name="Chefe Attendance",
            cpf="12345678901",
            sector=self.team_sector,
        )
        self.other_supervisor = User.objects.create_user(
            email="other-supervisor@test.com",
            password="pwd",
            role=User.Role.SUPERVISOR,
            full_name="Outro Chefe",
            cpf="99999999999",
        )
        self.chief = Chief.objects.create(
            name="Chefe Attendance",
            cpf="12345678901",
            team=self.team,
            is_active=True,
            source_id=f"user:{self.chief_user.id}",
        )
        self.schedule = ShiftSchedule.objects.create(
            date=date(2026, 7, 17),
            team=self.team,
            created_by=self.admin,
        )
        self.report_url = reverse("shift-schedules-report-attendance", args=[self.schedule.id])
        self.approve_url = reverse("shift-schedules-approve-attendance", args=[self.schedule.id])

    def test_supervisor_can_report_attendance(self):
        self.client.force_authenticate(self.chief_user)
        response = self.client.post(self.report_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.attendance_reported)
        self.assertIsNotNone(self.schedule.attendance_reported_at)
        self.assertFalse(self.schedule.attendance_approved)
        self.assertIsNone(self.schedule.attendance_approved_at)

    def test_report_attendance_resets_previous_approval(self):
        self.schedule.attendance_reported = True
        self.schedule.attendance_approved = True
        self.schedule.save(update_fields=["attendance_reported", "attendance_approved"])
        self.client.force_authenticate(self.chief_user)
        response = self.client.post(self.report_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.attendance_reported)
        self.assertFalse(self.schedule.attendance_approved)
        self.assertIsNone(self.schedule.attendance_approved_at)

    def test_scheduler_can_approve_reported_attendance(self):
        self.schedule.attendance_reported = True
        self.schedule.save(update_fields=["attendance_reported"])
        self.client.force_authenticate(self.manager)
        response = self.client.post(self.approve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.attendance_approved)
        self.assertIsNotNone(self.schedule.attendance_approved_at)

    def test_supervisor_cannot_approve_attendance(self):
        self.schedule.attendance_reported = True
        self.schedule.save(update_fields=["attendance_reported"])
        self.client.force_authenticate(self.chief_user)
        response = self.client.post(self.approve_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unlinked_supervisor_cannot_report_attendance(self):
        self.client.force_authenticate(self.other_supervisor)
        response = self.client.post(self.report_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
