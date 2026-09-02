from datetime import date, datetime, time, timedelta

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agenda, EducationAction, EducationReport, Sector


class DashboardOperationalPayloadTests(APITestCase):
    def setUp(self):
        self.sector, _ = Sector.objects.get_or_create(name="Educacao")
        cache.clear()
        self.manager = User.objects.create_user(
            email="dashboard-payload@example.com",
            password="password123",
            full_name="Gestor Dashboard Payload",
            role=User.Role.MANAGER,
            sector=self.sector,
            cpf="12345678901",
        )
        self.client.force_authenticate(self.manager)

    def create_agenda(self, **overrides):
        payload = {
            "title": "Acao operacional",
            "description": "Teste",
            "date": date(2026, 8, 10),
            "start_time": time(9, 0),
            "end_time": time(12, 0),
            "location": "Escola Estadual",
            "responsible": self.manager,
            "sector": self.sector,
            "created_by": self.manager,
            "status": Agenda.Status.APPROVED,
            "service_order_number": 2629,
            "requester_entity_type": "Outro",
        }
        payload.update(overrides)
        return Agenda.objects.create(**payload)

    def create_report(self, agenda, **overrides):
        payload = {
            "agenda": agenda,
            "operation_date": agenda.date,
            "team": agenda.team_name or (agenda.team_ref.name if agenda.team_ref else "") or (agenda.sector.name if agenda.sector else ""),
            "status": EducationReport.ReportStatus.DRAFT,
            "general_observations": "",
            "approximate_public": None,
            "created_by": self.manager,
        }
        payload.update(overrides)
        return EducationReport.objects.create(**payload)

    def set_report_timestamp(self, report, *, hours_after_base):
        base_time = timezone.make_aware(datetime(2026, 8, 10, 8, 0))
        timestamp = base_time + timedelta(hours=hours_after_base)
        EducationReport.objects.filter(pk=report.pk).update(created_at=timestamp, updated_at=timestamp)
        report.refresh_from_db()
        return report

    def dashboard_row(self, agenda):
        cache.clear()
        response = self.client.get(reverse("agendas-dashboard"), {"date": agenda.date.isoformat()})
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.json()["operations"]["field_operations"] if item["id"] == agenda.id)
        return row

    def test_dashboard_team_single_report_uses_that_report(self):
        agenda = self.create_agenda(team_name="ALFA")
        report = self.create_report(
            agenda=agenda,
            team="ALFA",
            status=EducationReport.ReportStatus.APPROVED,
            general_observations="Relato unico",
            approximate_public=87,
        )
        self.set_report_timestamp(report, hours_after_base=1)

        row = self.dashboard_row(agenda)

        self.assertTrue(row["has_report"])
        self.assertEqual(row["chief_report_text"], "Relato unico")
        self.assertTrue(row["chief_report_available"])
        self.assertEqual(row["latest_public_reached"], 87)
        self.assertEqual(row["report_status"], "approved")

    def test_dashboard_reached_public_matches_pdf_rule(self):
        agenda = self.create_agenda(team_name="ALFA")
        report = self.create_report(
            agenda=agenda,
            team="ALFA",
            status=EducationReport.ReportStatus.APPROVED,
            approximate_public=500000,
        )
        EducationAction.objects.create(
            report=report, agenda=agenda, start_time="09:00",
            approach=200, approached_lectures=1200, approached_actions=0,
        )

        row = self.dashboard_row(agenda)

        self.assertEqual(row["latest_public_reached"], 1200)

    def test_dashboard_team_prefers_matching_team_report(self):
        agenda = self.create_agenda(team_name="ALFA")
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="BRAVO",
                status=EducationReport.ReportStatus.APPROVED,
                general_observations="Relato de outra equipe",
                approximate_public=300,
            ),
            hours_after_base=3,
        )
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="ALFA",
                status=EducationReport.ReportStatus.RETURNED,
                general_observations="Relato da equipe correta",
                approximate_public=42,
            ),
            hours_after_base=1,
        )

        row = self.dashboard_row(agenda)

        self.assertTrue(row["has_report"])
        self.assertEqual(row["chief_report_text"], "Relato da equipe correta")
        self.assertEqual(row["latest_public_reached"], 42)
        self.assertEqual(row["report_status"], "returned")

    def test_dashboard_team_more_recent_other_team_does_not_override_match(self):
        agenda = self.create_agenda(team_name="ALFA")
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="ALFA",
                status=EducationReport.ReportStatus.APPROVED,
                general_observations="Relato certo",
                approximate_public=55,
            ),
            hours_after_base=1,
        )
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="BRAVO",
                status=EducationReport.ReportStatus.DRAFT,
                general_observations="Relato errado mais recente",
                approximate_public=999,
            ),
            hours_after_base=4,
        )

        row = self.dashboard_row(agenda)

        self.assertEqual(row["chief_report_text"], "Relato certo")
        self.assertEqual(row["latest_public_reached"], 55)
        self.assertEqual(row["report_status"], "approved")

    def test_dashboard_team_uses_most_recent_report_from_same_team(self):
        agenda = self.create_agenda(team_name="ALFA")
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="ALFA",
                status=EducationReport.ReportStatus.APPROVED,
                general_observations="Relato antigo",
                approximate_public=10,
            ),
            hours_after_base=1,
        )
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="ALFA",
                status=EducationReport.ReportStatus.DRAFT,
                general_observations="Relato mais recente",
                approximate_public=25,
            ),
            hours_after_base=2,
        )

        row = self.dashboard_row(agenda)

        self.assertTrue(row["has_report"])
        self.assertEqual(row["chief_report_text"], "Relato mais recente")
        self.assertEqual(row["latest_public_reached"], 25)
        self.assertEqual(row["report_status"], "draft")

    def test_dashboard_team_without_reports_exposes_none_state(self):
        agenda = self.create_agenda(team_name="ALFA")

        row = self.dashboard_row(agenda)

        self.assertFalse(row["has_report"])
        self.assertEqual(row["report_status"], "none")
        self.assertEqual(row["chief_report_text"], "")
        self.assertFalse(row["chief_report_available"])
        self.assertEqual(row["latest_public_reached"], 0)

    def test_dashboard_team_multiple_reports_without_match_does_not_pick_unsafe_report(self):
        agenda = self.create_agenda(team_name="ALFA")
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="BRAVO",
                status=EducationReport.ReportStatus.APPROVED,
                general_observations="Relato bravo",
                approximate_public=101,
            ),
            hours_after_base=1,
        )
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="CHARLIE",
                status=EducationReport.ReportStatus.RETURNED,
                general_observations="Relato charlie",
                approximate_public=202,
            ),
            hours_after_base=2,
        )

        row = self.dashboard_row(agenda)

        self.assertFalse(row["has_report"])
        self.assertEqual(row["report_status"], "none")
        self.assertEqual(row["chief_report_text"], "")
        self.assertFalse(row["chief_report_available"])
        self.assertEqual(row["latest_public_reached"], 0)

    def test_dashboard_team_single_report_without_match_uses_safe_fallback(self):
        agenda = self.create_agenda(team_name="ALFA")
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="BRAVO",
                status=EducationReport.ReportStatus.APPROVED,
                general_observations="Relato unico sem match",
                approximate_public=64,
            ),
            hours_after_base=1,
        )

        row = self.dashboard_row(agenda)

        self.assertTrue(row["has_report"])
        self.assertEqual(row["chief_report_text"], "Relato unico sem match")
        self.assertEqual(row["latest_public_reached"], 64)
        self.assertEqual(row["report_status"], "approved")

    def test_dashboard_designated_matches_report_using_existing_team_contract(self):
        agenda = self.create_agenda(
            service_order_mode=Agenda.ServiceOrderMode.DESIGNATED,
            team_name="",
            service_order_number=2631,
        )
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="Educacao",
                status=EducationReport.ReportStatus.SUBMITTED,
                general_observations="Relato designado",
                approximate_public=19,
            ),
            hours_after_base=1,
        )
        self.set_report_timestamp(
            self.create_report(
                agenda=agenda,
                team="Outra equipe",
                status=EducationReport.ReportStatus.APPROVED,
                general_observations="Relato incorreto",
                approximate_public=999,
            ),
            hours_after_base=2,
        )

        row = self.dashboard_row(agenda)

        self.assertEqual(row["service_order_mode"], Agenda.ServiceOrderMode.DESIGNATED)
        self.assertTrue(row["has_report"])
        self.assertEqual(row["chief_report_text"], "Relato designado")
        self.assertEqual(row["latest_public_reached"], 19)
        self.assertEqual(row["report_status"], "submitted")

    def test_dashboard_exposes_designated_operation_staffing(self):
        designated_one = User.objects.create_user(
            email="designado1@example.com",
            password="password123",
            full_name="Participante Um",
            role=User.Role.USER,
            sector=self.sector,
            cpf="12345678902",
        )
        designated_two = User.objects.create_user(
            email="designado2@example.com",
            password="password123",
            full_name="Participante Dois",
            role=User.Role.SUPPORT,
            sector=self.sector,
            cpf="12345678903",
        )
        agenda = self.create_agenda(
            service_order_mode=Agenda.ServiceOrderMode.DESIGNATED,
            service_order_number=2630,
        )
        agenda.designated_users.set([designated_one, designated_two])

        row = self.dashboard_row(agenda)

        self.assertEqual(row["service_order_mode"], Agenda.ServiceOrderMode.DESIGNATED)
        self.assertEqual(row["effective_total_count"], 2)
        self.assertEqual(row["designated_users_count"], 2)
        self.assertEqual(set(row["designated_users_names"]), {"Participante Um", "Participante Dois"})
        self.assertIn("participante(s) designado(s)", row["effective_summary"])
