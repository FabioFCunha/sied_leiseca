from datetime import date, datetime, time

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.schedules.models import Agenda, EducationReport, Sector
from apps.schedules.views import build_agenda_operational_window, classify_operational_status


class DashboardOperationalStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="dashboard@example.com", cpf="11111111111")
        self.sector = Sector.objects.create(name="Dashboard Test")
        self.tz = timezone.get_current_timezone()

    def aware(self, year, month, day, hour, minute):
        return timezone.make_aware(datetime(year, month, day, hour, minute), self.tz)

    def create_agenda(self, *, agenda_date, start_time, end_time, status=Agenda.Status.APPROVED):
        return Agenda.objects.create(
            title="Ação operacional",
            description="Teste",
            date=agenda_date,
            start_time=start_time,
            end_time=end_time,
            location="Local",
            requester_entity_type="Outro",
            responsible=self.user,
            sector=self.sector,
            created_by=self.user,
            status=status,
        )

    def test_classifies_basic_operational_states(self):
        agenda = self.create_agenda(
            agenda_date=date(2026, 8, 10),
            start_time=time(9, 0),
            end_time=time(12, 0),
        )

        cases = [
            ("future", self.aware(2026, 8, 10, 8, 59), "scheduled", "PRÓXIMA"),
            ("in_progress", self.aware(2026, 8, 10, 10, 0), "in_progress", "EM ANDAMENTO"),
            ("completed", self.aware(2026, 8, 10, 12, 0), "completed", "REALIZADA"),
        ]

        for _, now_dt, expected_key, expected_badge in cases:
            key, badge, _ = classify_operational_status(
                agenda_date=agenda.date,
                start_time=agenda.start_time,
                end_time=agenda.end_time,
                agenda_status=agenda.status,
                now_dt=now_dt,
            )
            self.assertEqual(key, expected_key)
            self.assertEqual(badge, expected_badge)

    def test_cancelled_has_priority_before_during_and_after(self):
        agenda = self.create_agenda(
            agenda_date=date(2026, 8, 10),
            start_time=time(9, 0),
            end_time=time(12, 0),
            status=Agenda.Status.CANCELLED,
        )

        for now_dt in (
            self.aware(2026, 8, 10, 8, 0),
            self.aware(2026, 8, 10, 10, 0),
            self.aware(2026, 8, 10, 13, 0),
        ):
            key, badge, label = classify_operational_status(
                agenda_date=agenda.date,
                start_time=agenda.start_time,
                end_time=agenda.end_time,
                agenda_status=agenda.status,
                now_dt=now_dt,
            )
            self.assertEqual(key, "cancelled")
            self.assertEqual(badge, "CANCELADA")
            self.assertEqual(label, "Cancelada")

    def test_report_status_does_not_change_realizada(self):
        agenda = self.create_agenda(
            agenda_date=date(2026, 8, 10),
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        now_dt = self.aware(2026, 8, 10, 12, 30)

        statuses = [
            None,
            EducationReport.ReportStatus.DRAFT,
            EducationReport.ReportStatus.PENDING_REVIEW,
            EducationReport.ReportStatus.APPROVED,
        ]

        for report_status in statuses:
            if report_status:
                EducationReport.objects.create(
                    agenda=agenda,
                    operation_date=agenda.date,
                    team="ALFA",
                    created_by=self.user,
                    status=report_status,
                )

            key, badge, _ = classify_operational_status(
                agenda_date=agenda.date,
                start_time=agenda.start_time,
                end_time=agenda.end_time,
                agenda_status=agenda.status,
                now_dt=now_dt,
            )
            self.assertEqual(key, "completed")
            self.assertEqual(badge, "REALIZADA")
            EducationReport.objects.all().delete()

    def test_cross_midnight_window_and_classification(self):
        agenda = self.create_agenda(
            agenda_date=date(2026, 8, 10),
            start_time=time(23, 45),
            end_time=time(0, 0),
        )

        start_dt, end_dt = build_agenda_operational_window(
            agenda_date=agenda.date,
            start_time=agenda.start_time,
            end_time=agenda.end_time,
            tz=self.tz,
        )

        self.assertEqual(start_dt.isoformat(), self.aware(2026, 8, 10, 23, 45).isoformat())
        self.assertEqual(end_dt.isoformat(), self.aware(2026, 8, 11, 0, 0).isoformat())

        cases = [
            (self.aware(2026, 8, 10, 23, 44), "scheduled"),
            (self.aware(2026, 8, 10, 23, 50), "in_progress"),
            (self.aware(2026, 8, 11, 0, 1), "completed"),
        ]

        for now_dt, expected_key in cases:
            key, _, _ = classify_operational_status(
                agenda_date=agenda.date,
                start_time=agenda.start_time,
                end_time=agenda.end_time,
                agenda_status=agenda.status,
                now_dt=now_dt,
            )
            self.assertEqual(key, expected_key)

    def test_cancelled_cross_midnight_stays_cancelled(self):
        agenda = self.create_agenda(
            agenda_date=date(2026, 8, 10),
            start_time=time(23, 45),
            end_time=time(0, 0),
            status=Agenda.Status.CANCELLED,
        )

        key, badge, _ = classify_operational_status(
            agenda_date=agenda.date,
            start_time=agenda.start_time,
            end_time=agenda.end_time,
            agenda_status=agenda.status,
            now_dt=self.aware(2026, 8, 10, 23, 50),
        )

        self.assertEqual(key, "cancelled")
        self.assertEqual(badge, "CANCELADA")

    def test_cross_midnight_in_progress_until_end_time(self):
        agenda = self.create_agenda(
            agenda_date=date(2026, 8, 10),
            start_time=time(22, 0),
            end_time=time(1, 30),
        )

        key, badge, label = classify_operational_status(
            agenda_date=agenda.date,
            start_time=agenda.start_time,
            end_time=agenda.end_time,
            agenda_status=agenda.status,
            now_dt=self.aware(2026, 8, 11, 0, 30),
        )

        self.assertEqual(key, "in_progress")
        self.assertEqual(badge, "EM ANDAMENTO")
        self.assertEqual(label, "Em andamento")

    def test_cross_midnight_becomes_completed_after_end_time(self):
        agenda = self.create_agenda(
            agenda_date=date(2026, 8, 10),
            start_time=time(22, 0),
            end_time=time(1, 30),
        )

        key, badge, label = classify_operational_status(
            agenda_date=agenda.date,
            start_time=agenda.start_time,
            end_time=agenda.end_time,
            agenda_status=agenda.status,
            now_dt=self.aware(2026, 8, 11, 1, 31),
        )

        self.assertEqual(key, "completed")
        self.assertEqual(badge, "REALIZADA")
        self.assertEqual(label, "Realizada")
