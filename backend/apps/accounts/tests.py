from datetime import date, time

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from config.settings import normalize_email_host_password

from apps.accounts.models import User
from apps.schedules.models import (
    Agenda,
    AgendaHistory,
    EducationAction,
    EducationReport,
    EventReport,
    SatisfactionSurvey,
    Agent,
    Support,
    Sector,
    Team,
)


class UserDeleteTests(APITestCase):
    def test_manager_can_access_users_endpoint(self):
        manager = User.objects.create_user(
            email="gestor@example.com",
            password="password123",
            full_name="Gestor",
            role=User.Role.MANAGER,
        )
        User.objects.create_user(
            email="agente@example.com",
            password="password123",
            full_name="Agente",
            role=User.Role.USER,
        )

        self.client.force_authenticate(manager)
        response = self.client.get(reverse("users-list"))

        self.assertEqual(response.status_code, 200)

    def test_delete_user_removes_linked_operational_records(self):
        sector = Sector.objects.create(name="BRAVO")
        admin = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            full_name="Admin",
            role=User.Role.ADMIN,
        )
        user = User.objects.create_user(
            email="agente@example.com",
            password="password123",
            full_name="Agente",
            role=User.Role.USER,
            sector=sector,
        )
        agenda = Agenda.objects.create(
            title="Acao educativa",
            description="Atividade",
            date=date(2026, 6, 11),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Escola",
            responsible=user,
            sector=sector,
            created_by=user,
        )
        AgendaHistory.objects.create(agenda=agenda, changed_by=user, action="Criacao")
        EventReport.objects.create(agenda=agenda, created_by=user, execution_summary="Executado")
        report = EducationReport.objects.create(
            agenda=agenda,
            operation_date=date(2026, 6, 11),
            team="BRAVO",
            created_by=user,
        )
        EducationAction.objects.create(report=report, agenda=agenda)
        SatisfactionSurvey.objects.create(agenda=agenda, report=report, token="survey-token")

        self.client.force_authenticate(admin)
        response = self.client.delete(reverse("users-detail", args=[user.id]))
        if response.status_code != 204:
            print(response.json())
        self.assertEqual(response.status_code, 204)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertTrue(Agenda.objects.filter(id=agenda.id).exists())
        self.assertTrue(AgendaHistory.objects.exists())
        self.assertTrue(EventReport.objects.exists())
        self.assertTrue(EducationReport.objects.exists())
        self.assertTrue(EducationAction.objects.exists())
        self.assertTrue(SatisfactionSurvey.objects.exists())


class UserOperationalTeamTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            full_name="Admin",
            role=User.Role.ADMIN,
        )
        self.team, _ = Team.objects.get_or_create(name="ALFA")
        self.client.force_authenticate(self.admin)

    def test_create_agent_links_user_to_lookup_team(self):
        response = self.client.post(reverse("users-list"), {
            "email": "agente@example.com",
            "full_name": "Agente Novo",
            "cpf": "12345678901",
            "phone": "21999999999",
            "role": User.Role.USER,
            "team": self.team.id,
            "is_active": True,
        }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["team_id"], self.team.id)
        self.assertEqual(response.data["team_name"], "ALFA")

        agent = Agent.objects.get(source_id=f"user:{response.data['id']}")
        self.assertEqual(agent.team, self.team)
        user = User.objects.get(id=response.data["id"])
        self.assertEqual(user.sector.name.upper(), "ALFA")

    def test_operational_user_requires_team(self):
        response = self.client.post(reverse("users-list"), {
            "email": "sem-equipe@example.com",
            "full_name": "Sem Equipe",
            "cpf": "12345678902",
            "role": User.Role.USER,
            "is_active": True,
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("team", response.data)




    def test_delete_support_lookup_deactivates_linked_user(self):
        support_team, _ = Team.objects.get_or_create(name="HOTEL")
        support_user = User.objects.create_user(
            email="apoio@example.com",
            password="password123",
            full_name="Ronaldo de Almeida Rodrigues",
            cpf="12345678901",
            role=User.Role.SUPPORT,
            is_active=True,
        )
        support = Support.objects.create(
            name="Ronaldo de Almeida Rodrigues",
            cpf="12345678901",
            role="APOIO",
            team=support_team,
            is_active=True,
            source_id=f"user:{support_user.id}",
        )

        self.client.force_authenticate(self.admin)
        response = self.client.delete(reverse("supports-detail", args=[support.id]))

        self.assertEqual(response.status_code, 204)
        support_user.refresh_from_db()
        self.assertFalse(support_user.is_active)


    def test_support_list_rebuilds_missing_lookup_from_active_support_user_sector(self):
        support_team, _ = Team.objects.get_or_create(name="HOTEL")
        support_sector, _ = Sector.objects.get_or_create(name="HOTEL")
        support_user = User.objects.create_user(
            email="ronaldo.hotel@example.com",
            password="password123",
            full_name="Ronaldo Ferreira Lima",
            cpf="01229890742",
            role=User.Role.SUPPORT,
            sector=support_sector,
            is_active=True,
        )

        self.assertFalse(Support.objects.filter(source_id=f"user:{support_user.id}").exists())

        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("supports-list"))

        self.assertEqual(response.status_code, 200)
        rows = response.data["results"] if "results" in response.data else response.data
        self.assertTrue(any(row["source_id"] == f"user:{support_user.id}" and row["team_name"] == "HOTEL" for row in rows))

        lookup = Support.objects.get(source_id=f"user:{support_user.id}")
        self.assertTrue(lookup.is_active)
        self.assertEqual(lookup.team, support_team)
        self.assertEqual(lookup.role, "APOIO")


class UserPasswordLinkTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            full_name="Admin",
            role=User.Role.ADMIN,
        )
        self.user = User.objects.create_user(
            email="agente@example.com",
            password="password123",
            full_name="Agente",
            role=User.Role.USER,
        )
        self.client.force_authenticate(self.admin)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_password_link_uses_email_backend(self):
        response = self.client.post(reverse("users-send-password-link", args=[self.user.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["password_setup_email_sent"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn(response.data["password_setup_link"], mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_send_password_link_reports_console_backend_as_not_real_email(self):
        response = self.client.post(reverse("users-send-password-link", args=[self.user.id]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["password_setup_email_sent"])
        self.assertIn("modo console", response.data["password_setup_email_error"])
        self.assertIn("password_setup_link", response.data)


class EmailSettingsTests(APITestCase):
    def test_gmail_app_password_spaces_are_removed(self):
        password = normalize_email_host_password("smtp.gmail.com", "abcd efgh ijkl mnop")

        self.assertEqual(password, "abcdefghijklmnop")

    def test_non_gmail_password_keeps_internal_spaces(self):
        password = normalize_email_host_password("smtp.example.com", " abcd efgh ")

        self.assertEqual(password, "abcd efgh")
