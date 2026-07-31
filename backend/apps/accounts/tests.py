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
    ShiftSchedule,
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


class LookupSynchronizationTests(APITestCase):
    def setUp(self):
        from apps.accounts.models import User
        from apps.schedules.models import Team, Sector, Support, Chief, Agent, EducationReport, Agenda
        from datetime import date, time

        self.admin = User.objects.create_user(
            email="admin_sync@example.com",
            password="password123",
            full_name="Admin Sync",
            role=User.Role.ADMIN,
        )
        self.team, _ = Team.objects.get_or_create(name="SYNC_TEAM")
        self.sector, _ = Sector.objects.get_or_create(name="SYNC_SECTOR")
        self.date = date(2026, 7, 15)
        self.time = time(10, 0)

    def test_lookup_already_bound_is_updated_without_duplication(self):
        from apps.accounts.serializers import upsert_user_lookup
        user = User.objects.create_user(
            email="user1@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
        )
        # Create already bound lookup
        lookup = Support.objects.create(
            name="Ronaldo Lima",
            source_id=f"user:{user.id}",
            role="APOIO",
            is_active=True,
        )

        # Sync again
        res = upsert_user_lookup(Support, user, "APOIO")
        self.assertIsNotNone(res)
        self.assertEqual(res.id, lookup.id)
        self.assertEqual(Support.objects.filter(source_id=f"user:{user.id}").count(), 1)

    def test_legacy_lookup_with_same_cpf_and_no_user_reused(self):
        from apps.accounts.serializers import upsert_user_lookup
        legacy = Support.objects.create(
            name="Old Support",
            cpf="12345678901",
            source_id="",
            role="APOIO",
            is_active=True,
        )
        user = User.objects.create_user(
            email="user2@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            cpf="12345678901",
            role=User.Role.SUPPORT,
        )

        res = upsert_user_lookup(Support, user, "APOIO")
        self.assertIsNotNone(res)
        self.assertEqual(res.id, legacy.id)
        self.assertEqual(res.source_id, f"user:{user.id}")
        self.assertEqual(res.name, "Ronaldo Lima") # Updated to user's name

    def test_legacy_lookup_is_not_reused_by_name_only(self):
        from apps.accounts.serializers import upsert_user_lookup
        from rest_framework.exceptions import ValidationError

        legacy = Support.objects.create(
            name="Ronaldo Lima",
            cpf="",
            source_id="",
            role="APOIO",
            is_active=True,
        )
        user = User.objects.create_user(
            email="user3@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
        )

        with self.assertRaises(ValidationError):
            upsert_user_lookup(Support, user, "APOIO")

        legacy.refresh_from_db()
        self.assertEqual(legacy.source_id, "")
        self.assertFalse(Support.objects.filter(source_id=f"user:{user.id}").exists())
    def test_lookup_bound_to_other_user_not_overwritten_by_name(self):
        from apps.accounts.serializers import upsert_user_lookup
        user_a = User.objects.create_user(
            email="usera@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
        )
        lookup_a = Support.objects.create(
            name="Ronaldo Lima",
            source_id=f"user:{user_a.id}",
            role="APOIO",
            is_active=True,
        )

        user_b = User.objects.create_user(
            email="userb@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
        )

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            upsert_user_lookup(Support, user_b, "APOIO")
        # O conflito não pode alterar lookup_a
        lookup_a.refresh_from_db()
        self.assertEqual(lookup_a.source_id, f"user:{user_a.id}")
        self.assertEqual(lookup_a.name, "Ronaldo Lima")
        # Não deve criar um novo lookup com o mesmo nome
        self.assertFalse(Support.objects.filter(source_id=f"user:{user_b.id}").exists())

    def test_two_users_with_same_name_different_cpfs_not_associated(self):
        from apps.accounts.serializers import upsert_user_lookup
        user_a = User.objects.create_user(
            email="user_a_cpf@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            cpf="11111111111",
            role=User.Role.SUPPORT,
        )
        lookup_a = Support.objects.create(
            name="Ronaldo Lima",
            cpf="11111111111",
            source_id=f"user:{user_a.id}",
            role="APOIO",
            is_active=True,
        )

        user_b = User.objects.create_user(
            email="user_b_cpf@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            cpf="22222222222",
            role=User.Role.SUPPORT,
        )

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            upsert_user_lookup(Support, user_b, "APOIO")
        lookup_a.refresh_from_db()
        self.assertEqual(lookup_a.source_id, f"user:{user_a.id}")
        self.assertEqual(lookup_a.cpf, "11111111111")

    def test_coincident_cpf_bound_to_other_user_not_reused(self):
        from apps.accounts.serializers import upsert_user_lookup
        lookup_a = Support.objects.create(
            name="User A",
            cpf="12345678901",
            source_id="user:9999",
            role="APOIO",
            is_active=True,
        )

        user_b = User.objects.create_user(
            email="user_b_coincident@example.com",
            password="pass",
            full_name="User B",
            cpf="12345678901",
            role=User.Role.SUPPORT,
        )

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            upsert_user_lookup(Support, user_b, "APOIO")
        lookup_a.refresh_from_db()
        self.assertEqual(lookup_a.source_id, "user:9999")

    def test_integrity_error_does_not_break_main_transaction(self):
        from django.db import transaction, IntegrityError
        from apps.accounts.serializers import safe_save_lookup

        support_a = Support.objects.create(
            name="Support A",
            cpf="99999999999",
            role="APOIO",
            is_active=True,
        )

        support_b = Support(
            name="Support B",
            cpf="99999999999", # duplicado para gerar IntegrityError
            role="APOIO",
            is_active=True,
        )

        with transaction.atomic():
            self.admin.full_name = "Admin Alterado"
            self.admin.save()

            from rest_framework.exceptions import ValidationError
            with self.assertRaises(ValidationError):
                safe_save_lookup(support_b, user=self.admin, model_name="Support")

            support_a.name = "Support A Alterado"
            support_a.save()

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.full_name, "Admin Alterado")
        support_a.refresh_from_db()
        self.assertEqual(support_a.name, "Support A Alterado")

    def test_sync_active_users_continues_processing_after_conflict(self):
        from apps.accounts.serializers import sync_active_users_for_role

        user_conflict = User.objects.create_user(
            email="conflict@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
        )
        user_ok = User.objects.create_user(
            email="ok@example.com",
            password="pass",
            full_name="Unique Name support",
            role=User.Role.SUPPORT,
        )

        user_other = User.objects.create_user(
            email="other@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
        )
        Support.objects.create(
            name="Ronaldo Lima",
            source_id=f"user:{user_other.id}",
            role="APOIO",
            is_active=True,
        )

        sync_active_users_for_role(User.Role.SUPPORT)

        self.assertFalse(Support.objects.filter(source_id=f"user:{user_conflict.id}").exists())
        self.assertTrue(Support.objects.filter(source_id=f"user:{user_ok.id}").exists())

    def test_technical_report_approval_succeeds_even_with_lookup_conflict(self):
        from apps.schedules.models import ShiftSchedule, EducationReport

        manager = User.objects.create_user(
            email="manager_sync@example.com",
            password="pass",
            full_name="Manager Sync",
            role=User.Role.MANAGER,
        )

        user_conflict = User.objects.create_user(
            email="conflict_approval@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
            is_active=True,
        )
        user_other = User.objects.create_user(
            email="other_approval@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
        )
        Support.objects.create(
            name="Ronaldo Lima",
            source_id=f"user:{user_other.id}",
            role="APOIO",
            is_active=True,
        )

        agenda = Agenda.objects.create(
            title="Agenda Teste",
            date=self.date,
            start_time=self.time,
            end_time=self.time,
            created_by=manager,
            responsible=manager,
            sector=self.sector,
        )
        schedule = ShiftSchedule.objects.create(
            date=self.date,
            team=self.team,
            created_by=manager,
        )

        report = EducationReport.objects.create(
            operation_date=self.date,
            agenda=agenda,
            team="SYNC_TEAM",
            status=EducationReport.ReportStatus.PENDING_REVIEW,
            created_by=manager,
        )

        self.client.force_authenticate(user=manager)
        url = reverse("education-reports-approve", args=[report.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.status, EducationReport.ReportStatus.APPROVED)

    def test_supports_list_succeeds_even_with_lookup_conflict(self):
        user_conflict = User.objects.create_user(
            email="conflict_list@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
            is_active=True,
        )
        user_other = User.objects.create_user(
            email="other_list@example.com",
            password="pass",
            full_name="Ronaldo Lima",
            role=User.Role.SUPPORT,
        )
        Support.objects.create(
            name="Ronaldo Lima",
            source_id=f"user:{user_other.id}",
            role="APOIO",
            is_active=True,
        )

        self.client.force_authenticate(user=self.admin)
        url = reverse("supports-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

class OperationalRoleChangeSynchronizationTests(APITestCase):
    def setUp(self):
        self.hotel, _ = Team.objects.get_or_create(name="HOTEL")
        self.alfa, _ = Team.objects.get_or_create(name="ALFA")
        self.hotel_33, _ = Team.objects.get_or_create(id=33, defaults={"name": "HOTEL 33"})
        self.admin = User.objects.create_user(
            email="admin-role-sync@example.com",
            password="password123",
            full_name="Administrador",
            role=User.Role.ADMIN,
        )

    def test_agent_to_support_updates_current_lookup_and_preserves_history(self):
        from apps.accounts.serializers import sync_user_lookup

        user = User.objects.create_user(
            email="agent-to-support@example.com",
            password="pass",
            full_name="Pessoa Operacional",
            cpf="123.456.789-01",
            role=User.Role.USER,
            vacation_start=date(2026, 8, 1),
            vacation_end=date(2026, 8, 10),
        )
        agent = Agent.objects.create(
            source_id=f"user:{user.id}",
            name=user.full_name,
            cpf="12345678901",
            team=self.alfa,
            role="AGENTE",
            is_active=True,
        )
        schedule = ShiftSchedule.objects.create(
            date=date(2026, 7, 20),
            team=self.alfa,
            created_by=self.admin,
        )
        schedule.extra_agents.add(agent)

        user.role = User.Role.SUPPORT
        user.full_name = "Pessoa Operacional Atualizada"
        user.cpf = "123.456.789-01"
        user.save()
        sync_user_lookup(user, team=self.hotel)

        agent.refresh_from_db()
        support = Support.objects.get(source_id=f"user:{user.id}")
        self.assertFalse(agent.is_active)
        self.assertTrue(support.is_active)
        self.assertEqual(support.name, "Pessoa Operacional Atualizada")
        self.assertEqual(support.cpf, "12345678901")
        self.assertEqual(support.team, self.hotel)
        self.assertEqual(support.vacation_start, date(2026, 8, 1))
        self.assertEqual(support.vacation_end, date(2026, 8, 10))
        self.assertTrue(schedule.extra_agents.filter(id=agent.id).exists())

    def test_support_to_agent_inactivates_previous_role(self):
        from apps.accounts.serializers import sync_user_lookup

        user = User.objects.create_user(
            email="support-to-agent@example.com",
            password="pass",
            full_name="Apoio Convertido",
            cpf="98765432100",
            role=User.Role.SUPPORT,
        )
        support = Support.objects.create(
            source_id=f"user:{user.id}",
            name=user.full_name,
            cpf=user.cpf,
            team=self.hotel,
            role="APOIO",
            is_active=True,
        )

        user.role = User.Role.USER
        user.save(update_fields=["role"])
        sync_user_lookup(user, team=self.alfa)

        support.refresh_from_db()
        agent = Agent.objects.get(source_id=f"user:{user.id}")
        self.assertFalse(support.is_active)
        self.assertTrue(agent.is_active)
        self.assertEqual(agent.team, self.alfa)

    def test_repeated_sync_is_idempotent(self):
        from apps.accounts.serializers import sync_user_lookup

        user = User.objects.create_user(
            email="idempotent-support@example.com",
            password="pass",
            full_name="Apoio Idempotente",
            cpf="11122233344",
            role=User.Role.SUPPORT,
        )

        sync_user_lookup(user, team=self.hotel)
        first_id = Support.objects.get(source_id=f"user:{user.id}").id
        sync_user_lookup(user, team=self.hotel)
        sync_user_lookup(user, team=self.hotel)

        self.assertEqual(Support.objects.filter(source_id=f"user:{user.id}").count(), 1)
        self.assertEqual(Support.objects.get(source_id=f"user:{user.id}").id, first_id)
        self.assertFalse(Agent.objects.filter(source_id=f"user:{user.id}", is_active=True).exists())

    def test_bound_record_of_another_user_is_never_reused(self):
        from apps.accounts.serializers import sync_user_lookup
        from rest_framework.exceptions import ValidationError

        owner = User.objects.create_user(
            email="cpf-owner@example.com",
            password="pass",
            full_name="Titular do Cadastro",
            cpf="55566677788",
            role=User.Role.SUPPORT,
        )
        owned_support = Support.objects.create(
            source_id=f"user:{owner.id}",
            name=owner.full_name,
            cpf=owner.cpf,
            team=self.hotel,
            role="APOIO",
            is_active=True,
        )
        other = User.objects.create_user(
            email="cpf-conflict@example.com",
            password="pass",
            full_name="Outra Pessoa",
            cpf="555.666.777-88",
            role=User.Role.SUPPORT,
        )
        previous_agent = Agent.objects.create(
            source_id=f"user:{other.id}",
            name=other.full_name,
            cpf="55566677788",
            team=self.alfa,
            role="AGENTE",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            sync_user_lookup(other, team=self.alfa)

        previous_agent.refresh_from_db()
        self.assertTrue(previous_agent.is_active)

        owned_support.refresh_from_db()
        self.assertEqual(owned_support.source_id, f"user:{owner.id}")
        self.assertEqual(owned_support.name, owner.full_name)
        self.assertFalse(Support.objects.filter(source_id=f"user:{other.id}").exists())

    def test_ronaldo_case_uses_source_id_and_corrects_stale_support(self):
        from apps.accounts.serializers import sync_user_lookup

        user = User.objects.create_user(
            id=71,
            email="ronaldo@example.com",
            password="pass",
            full_name="Ronaldo da Conceição Ferreira Lima",
            cpf="012.298.907-42",
            role=User.Role.SUPPORT,
            vacation_start=date(2026, 9, 1),
            vacation_end=date(2026, 9, 5),
        )
        agent = Agent.objects.create(
            id=37,
            source_id="user:71",
            name="Ronaldo da Conceição Ferreira Lima",
            cpf="01229890742",
            team=self.hotel_33,
            role="AGENTE",
            is_active=True,
        )
        support = Support.objects.create(
            id=12,
            source_id="user:71",
            name="Ronaldo de Almeida Rodrigues",
            cpf="99988877766",
            team=self.hotel_33,
            role="APOIO",
            is_active=False,
        )

        sync_user_lookup(user, team=self.hotel_33)
        sync_user_lookup(user, team=self.hotel_33)

        agent.refresh_from_db()
        support.refresh_from_db()
        self.assertEqual(agent.id, 37)
        self.assertFalse(agent.is_active)
        self.assertEqual(agent.name, user.full_name)
        self.assertEqual(support.id, 12)
        self.assertTrue(support.is_active)
        self.assertEqual(support.name, "Ronaldo da Conceição Ferreira Lima")
        self.assertEqual(support.cpf, "01229890742")
        self.assertEqual(support.team_id, 33)
        self.assertEqual(support.source_id, "user:71")
        self.assertEqual(support.vacation_start, date(2026, 9, 1))
        self.assertEqual(support.vacation_end, date(2026, 9, 5))
        self.assertEqual(Support.objects.filter(source_id="user:71").count(), 1)
