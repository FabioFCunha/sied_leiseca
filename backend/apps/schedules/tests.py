from datetime import date, time

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.emails import approval_message, available_dates_message, message_for_status, rejection_message
from apps.schedules.models import Agenda, Agent, EducationAction, EducationReport, Sector, ShiftSchedule, Team
from apps.schedules.serializers import EducationReportSerializer, PublicAgendaRequestSerializer



@override_settings(FRONTEND_URL="https://agenda.example.com")
class AgendaEmailMessageTests(SimpleTestCase):
    def setUp(self):
        self.agenda = Agenda(id=123, external_responsible="Maria da Silva")

    def test_approval_message_greets_requester_by_name(self):
        _, body = approval_message(self.agenda)

        self.assertTrue(body.startswith("Prezado(a) Maria da Silva,"))

    def test_rejection_message_greets_requester_by_name(self):
        _, body = rejection_message(self.agenda)

        self.assertTrue(body.startswith("Prezado(a) Maria da Silva,"))

    def test_available_dates_message_greets_requester_by_name(self):
        _, body = available_dates_message(self.agenda, "06/2026", "23/06/2026")

        self.assertTrue(body.startswith("Prezado(a) Maria da Silva,"))

    def test_requester_name_ignores_surrounding_whitespace(self):
        self.agenda.external_responsible = "  João Souza  "

        _, body = approval_message(self.agenda)

        self.assertTrue(body.startswith("Prezado(a) João Souza,"))


    def test_pending_message_uses_requested_confirmation_text(self):
        self.agenda.title = "Palestra Presencial - FACHA"
        self.agenda.date = date(2026, 6, 30)
        self.agenda.start_time = time(22, 28)
        self.agenda.end_time = time(23, 28)
        self.agenda.institution_location = "FACHA"
        self.agenda.address = "Rua Muniz Barreto, nº 51"
        self.agenda.city = "Rio de Janeiro"

        subject, body = message_for_status(self.agenda, Agenda.Status.PENDING)

        self.assertEqual(subject, "Solicitação recebida - Protocolo #123")
        self.assertTrue(body.startswith("Prezado(a) solicitante,\n\nAgradecemos o seu interesse"))
        self.assertIn("Confira abaixo os dados do seu protocolo:\n\nProtocolo: #123", body)
        self.assertIn("Horário: 22:28 às 23:28", body)
        self.assertIn("https://www.instagram.com/leisecarj/", body)
        self.assertTrue(body.endswith("Atenciosamente,\nSuperintendência da Operação Lei Seca."))

class PublicAgendaRequestSerializerTests(TestCase):
    def valid_data(self):
        return {
            "title": "Palestra bilíngue - Escola",
            "description": "Solicitação pública",
            "date": "2026-07-20",
            "start_time": "10:00",
            "end_time": "11:00",
            "action_type": "Palestra bilíngue (Inglês)",
            "institution_location": "Escola Modelo",
            "address": "Rua Exemplo, 10",
            "city": "Rio de Janeiro",
            "external_responsible": "Maria da Silva",
            "external_responsible_phone": "21999999999",
            "external_email": "maria@example.com",
            "requester_entity_type": "Escola Municipal",
            "participant_range": "51 a 100",
            "age_ranges": "09 até 13 anos",
            "accessibility_access": "Não se aplica, pois será realizado no térreo",
            "has_accessible_bathrooms": "Sim",
            "quantity": 100,
        }

    def test_accepts_options_from_updated_public_form(self):
        serializer = PublicAgendaRequestSerializer(data=self.valid_data())

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_multiple_age_ranges(self):
        data = self.valid_data()
        data["age_ranges"] = "04 até 8 anos, 09 até 13 anos"

        serializer = PublicAgendaRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("age_ranges", serializer.errors)

    def test_serializer_ignores_blocked_address(self):
        from apps.schedules.models import AccessibilityBlocklist

        # Create an active accessibility block on the address
        AccessibilityBlocklist.objects.create(
            address="Rua Exemplo, 10",
            is_active=True,
            reason="Não acessível"
        )

        data = self.valid_data()
        serializer = PublicAgendaRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)


class EducationReportSerializerTests(APITestCase):
    def test_accepts_long_resources_summary(self):
        sector = Sector.objects.create(name="EDUCACAO")
        manager = User.objects.create_user(
            email="report@example.com",
            password="password123",
            full_name="Gestor Relatorio",
            role=User.Role.MANAGER,
            sector=sector,
        )
        agenda = Agenda.objects.create(
            title="Acao educativa",
            description="Atividade educativa",
            date=date(2026, 6, 22),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Escola Municipal",
            responsible=manager,
            sector=sector,
            created_by=manager,
        )
        serializer = EducationReportSerializer(data={
            "agenda": agenda.id,
            "operation_date": "2026-06-22",
            "team": "Equipe Educacao",
            "breathalyzers": "Recursos, kits e materiais\n" + ("Kit educativo completo\n" * 20),
            "status": EducationReport.ReportStatus.DRAFT,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_admin_can_list_saved_reports(self):
        sector = Sector.objects.create(name="EDUCACAO RELATORIOS")
        admin = User.objects.create_user(
            email="admin-report@example.com",
            password="password123",
            full_name="Admin Relatorio",
            role=User.Role.ADMIN,
            sector=sector,
        )
        agenda = Agenda.objects.create(
            title="Acao educativa",
            description="Atividade educativa",
            date=date(2026, 6, 22),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Escola Municipal",
            responsible=admin,
            sector=sector,
            created_by=admin,
        )
        EducationReport.objects.create(
            agenda=agenda,
            operation_date=agenda.date,
            team="Equipe Educacao",
            created_by=admin,
        )
        self.client.force_authenticate(admin)

        response = self.client.get(reverse("education-reports-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

class TeamLookupTests(APITestCase):
    def test_manager_can_create_and_list_custom_team(self):
        manager = User.objects.create_user(
            email="gestor-equipes@example.com",
            password="password123",
            full_name="Gestor Equipes",
            role=User.Role.MANAGER,
        )

        self.client.force_authenticate(manager)
        create_response = self.client.post(reverse("teams-list"), {"name": "Equipe Extra", "is_active": True})
        list_response = self.client.get(reverse("teams-list"), {"page_size": 1000})

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["name"], "EQUIPE EXTRA")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        rows = payload["results"] if "results" in payload else payload
        self.assertIn("EQUIPE EXTRA", [row["name"] for row in rows])

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

class DashboardMetricsTests(APITestCase):
    def test_average_approaches_per_team_uses_distinct_report_teams(self):
        sector = Sector.objects.create(name="EDUCACAO")
        manager = User.objects.create_user(
            email="dashboard@example.com",
            password="password123",
            full_name="Gestor Dashboard",
            role=User.Role.MANAGER,
            sector=sector,
        )

        def create_report(day, team, approach):
            agenda = Agenda.objects.create(
                title=f"Acao {day}",
                description="Atividade educativa",
                date=date(2026, 6, day),
                start_time=time(9, 0),
                end_time=time(10, 0),
                location="Escola Municipal",
                responsible=manager,
                sector=sector,
                created_by=manager,
                origin=Agenda.Origin.PUBLIC_FORM,
            )
            report = EducationReport.objects.create(
                agenda=agenda,
                operation_date=agenda.date,
                team=team,
                status=EducationReport.ReportStatus.SUBMITTED,
                created_by=manager,
            )
            EducationAction.objects.create(report=report, agenda=agenda, approach=approach)

        create_report(10, "Equipe Alfa", 10)
        create_report(11, " equipe alfa ", 20)
        create_report(12, "Equipe Beta", 30)

        self.client.force_authenticate(manager)
        response = self.client.get(
            reverse("agendas-dashboard"),
            {"date_from": "2026-06-01", "date_to": "2026-06-30"},
        )

        self.assertEqual(response.status_code, 200)
        metrics = response.json()["chief_fillings"]
        self.assertEqual(metrics["teams_count"], 2)
        self.assertEqual(metrics["average_approaches_per_team"], 30.0)


class PublicAgendaRequestRejectionEmailTests(APITestCase):
    def test_sends_email_on_blocked_address_rejection(self):
        from django.core import mail
        from django.utils import timezone
        from datetime import timedelta
        from apps.schedules.models import AccessibilityBlocklist, Agenda
        from apps.schedules.accessibility import process_due_accessibility_rejections

        # Create active block on the address
        block = AccessibilityBlocklist.objects.create(
            address="Rua Exemplo, 10",
            is_active=True,
            reason="Não acessível"
        )

        data = {
            "title": "Palestra bilíngue - Escola",
            "description": "Solicitação pública",
            "date": "2026-07-20",
            "start_time": "10:00",
            "end_time": "11:00",
            "action_type": "Palestra bilíngue (Inglês)",
            "institution_location": "Escola Modelo",
            "address": "Rua Exemplo, 10",
            "city": "Rio de Janeiro",
            "external_responsible": "Maria da Silva",
            "external_responsible_phone": "21999999999",
            "external_email": "maria@example.com",
            "requester_entity_type": "Escola Municipal",
            "participant_range": "51 a 100",
            "age_ranges": "09 até 13 anos",
            "accessibility_access": "Não se aplica, pois será realizado no térreo",
            "has_accessible_bathrooms": "Sim",
            "quantity": 100,
        }

        # Submit request
        response = self.client.post(reverse("public_agenda_request"), data)

        self.assertEqual(response.status_code, 201)
        
        # Verify agenda has block + rejection scheduled
        agenda = Agenda.objects.get(id=response.json()["protocol"])
        self.assertEqual(agenda.status, Agenda.Status.PENDING)
        self.assertEqual(agenda.accessibility_block, block)
        self.assertIsNotNone(agenda.accessibility_rejection_due_at)
        self.assertIsNone(agenda.accessibility_rejection_sent_at)

        # Check outbox - should have 0 emails (since pending email is sent on_commit and APITestCase rolls back transaction)
        self.assertEqual(len(mail.outbox), 0)

        # Run process_due_accessibility_rejections with simulated time (+6 minutes)
        processed = process_due_accessibility_rejections(now=timezone.now() + timedelta(minutes=6))
        self.assertEqual(processed, 1)

        # Verify agenda is cancelled
        agenda.refresh_from_db()
        self.assertEqual(agenda.status, Agenda.Status.CANCELLED)
        self.assertIsNotNone(agenda.accessibility_rejection_sent_at)

        # Check outbox - should now have 1 email (the rejection email)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Recusa de solicitação - Operação Lei Seca")
        self.assertIn("maria@example.com", email.to)
        self.assertIn("Agradecemos o interesse em receber a palestra da Operação Lei Seca novamente", email.body)
        self.assertIn("Durante a análise técnica, após a última palestra no local indicado na solicitação", email.body)
