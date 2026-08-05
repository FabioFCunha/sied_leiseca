from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.schedules.models import Agenda, Agent, EducationReport, Sector, ShiftSchedule, Support, Team
from apps.schedules.services import get_effective_members, get_expected_member_keys
from saneamento_ronaldo import clean_data

User = get_user_model()


RONALDO_CPF = "01229890742"
RONALDO_NAME = "Ronaldo da Conceicao Ferreira Lima"


class RonaldoSupportFixTests(TestCase):
    def setUp(self):
        self.team, _ = Team.objects.get_or_create(name="HOTEL")
        self.sector, _ = Sector.objects.get_or_create(name="HOTEL")

        self.agent_user = User.objects.create_user(
            email="agent@example.com",
            password="pwd",
            full_name="Agente Legitimo",
            cpf="99999999999",
            role=User.Role.USER,
        )
        self.agent = Agent.objects.create(
            name="Agente Legitimo",
            cpf="99999999999",
            team=self.team,
            source_id=f"user:{self.agent_user.id}",
        )

        self.fernanda_user = User.objects.create_user(
            email="fernanda@example.com",
            password="pwd",
            full_name="Fernanda Cristina",
            cpf="10222047712",
            role=User.Role.SUPPORT,
        )
        self.fernanda = Support.objects.create(
            name="Fernanda Cristina",
            cpf="10222047712",
            team=self.team,
            source_id=f"user:{self.fernanda_user.id}",
        )

        self.ronaldo_user = User.objects.create_user(
            email="ronaldo@example.com",
            password="pwd",
            full_name=RONALDO_NAME,
            cpf=RONALDO_CPF,
            role=User.Role.SUPPORT,
        )
        self.ronaldo_support = Support.objects.create(
            name=RONALDO_NAME,
            cpf=RONALDO_CPF,
            team=self.team,
            source_id=f"user:{self.ronaldo_user.id}",
        )
        self.ronaldo_agent = Agent.objects.create(
            name=RONALDO_NAME,
            cpf=RONALDO_CPF,
            team=self.team,
            source_id=f"user:{self.ronaldo_user.id}",
        )

        self.schedule = ShiftSchedule.objects.create(
            date=date(2026, 7, 24),
            team=self.team,
            created_by=self.agent_user,
        )

    def member_ids(self):
        members = get_effective_members(self.schedule)
        return {
            "agents": {member["id"] for member in members["agents"]},
            "supports": {member["id"] for member in members["supports"]},
        }

    def test_support_role_member_appears_only_as_support(self):
        ids = self.member_ids()

        self.assertIn(self.fernanda.id, ids["supports"])
        self.assertNotIn(self.fernanda.id, ids["agents"])

    def test_support_user_with_agent_and_support_links_stays_only_in_supports(self):
        ids = self.member_ids()

        self.assertIn(self.ronaldo_support.id, ids["supports"])
        self.assertNotIn(self.ronaldo_agent.id, ids["agents"])

    def test_user_role_member_appears_only_as_agent(self):
        ids = self.member_ids()

        self.assertIn(self.agent.id, ids["agents"])
        self.assertNotIn(self.agent.id, ids["supports"])

    def test_user_role_with_residual_support_link_stays_only_in_agents(self):
        user = User.objects.create_user(
            email="residual@example.com",
            password="pwd",
            full_name="Agente Residual",
            cpf="88888888888",
            role=User.Role.USER,
        )
        agent = Agent.objects.create(
            name="Agente Residual",
            cpf="88888888888",
            team=self.team,
            source_id=f"user:{user.id}",
        )
        support = Support.objects.create(
            name="Agente Residual",
            cpf="88888888888",
            team=self.team,
            source_id=f"user:{user.id}",
        )

        ids = self.member_ids()

        self.assertIn(agent.id, ids["agents"])
        self.assertNotIn(support.id, ids["supports"])

    def test_member_without_active_role_preserves_original_category(self):
        inactive_user = User.objects.create_user(
            email="inactive@example.com",
            password="pwd",
            full_name="Usuario Inativo",
            cpf="77777777777",
            role=User.Role.SUPPORT,
            is_active=False,
        )
        agent = Agent.objects.create(
            name="Usuario Inativo",
            cpf="77777777777",
            team=self.team,
            source_id=f"user:{inactive_user.id}",
        )

        ids = self.member_ids()

        self.assertIn(agent.id, ids["agents"])

    def test_existing_report_is_sanitized_without_duplicate_support(self):
        agenda = Agenda.objects.create(
            title="Operacao Hotel",
            description="Atendimento operacional",
            date=date(2026, 7, 24),
            start_time=time(8, 0),
            end_time=time(12, 0),
            location="Hotel",
            team_name="HOTEL",
            agents=f"Agente Legitimo; {RONALDO_NAME}",
            support_1="Fernanda Cristina",
            created_by=self.agent_user,
            responsible=self.agent_user,
            sector=self.sector,
        )
        agenda.agents_ref.add(self.agent, self.ronaldo_agent)
        report = EducationReport.objects.create(
            operation_date=date(2026, 7, 24),
            team="HOTEL",
            education_agents=f"Chefe: Ninguem\nAgentes: Agente Legitimo; {RONALDO_NAME}\nApoio: Fernanda Cristina",
            created_by=self.agent_user,
            agenda=agenda,
        )

        clean_data(RONALDO_CPF, dry_run=False)

        agenda.refresh_from_db()
        report.refresh_from_db()
        self.assertNotIn(RONALDO_NAME, agenda.agents)
        self.assertFalse(agenda.agents_ref.filter(id=self.ronaldo_agent.id).exists())
        self.assertIn(RONALDO_NAME, {agenda.support_1, agenda.support_2})
        before_support_block, support_block = report.education_agents.split("\nApoio:", 1)
        self.assertNotIn(RONALDO_NAME, before_support_block)
        self.assertEqual(support_block.count(RONALDO_NAME), 1)

    def test_frequency_expected_keys_use_correct_classification(self):
        expected = get_expected_member_keys(self.schedule)

        self.assertIn(f"SUPPORT_{self.ronaldo_support.id}", expected)
        self.assertNotIn(f"AGENT_{self.ronaldo_agent.id}", expected)
