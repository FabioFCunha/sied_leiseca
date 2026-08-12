import uuid
from datetime import date, datetime, timezone

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.inspection.models import (
    InspectionFine,
    InspectionReport,
    InspectionReportOperation,
    InspectionReportStatusHistory,
    InspectionStatistic,
    InspectionStatisticsDecisionHistory,
)


class InspectionModelsTests(TestCase):
    def make_report(self, **overrides):
        payload = {
            "source_id": uuid.uuid4(),
            "source_created_at": datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
            "source_updated_at": datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc),
            "synced_at": datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
            "operation_date": date(2026, 8, 10),
            "team": "A3",
            "management_id": 12,
            "military_chief_source_id": uuid.uuid4(),
            "segov_team_civil": "Civil 1",
            "segov_team_military": "Militar 1",
            "change_ols": "Sem alteracoes",
            "agent_detran": 4,
            "number_trailers": 2,
            "change_support": "Apoio normal",
            "cars": "VTR-01",
            "changes_general": "Operacao regular",
        }
        payload.update(overrides)
        return InspectionReport.objects.create(**payload)

    def make_operation(self, report, **overrides):
        payload = {
            "report": report,
            "source_id": uuid.uuid4(),
            "source_created_at": datetime(2026, 8, 10, 8, 5, tzinfo=timezone.utc),
            "source_updated_at": datetime(2026, 8, 10, 8, 35, tzinfo=timezone.utc),
            "address_operation": "Rua A",
            "locality": "Centro",
            "another_not_listed": "",
            "departure_meeting_point": "Base",
            "operation_assembly": "08:00",
            "first_approach": "08:30",
            "closing": "10:00",
            "approach": 93,
            "reconductor": 10,
            "refusal": 5,
            "celebrities_authorities": 0,
            "four_ml": 88,
            "thirtythree_ml": 0,
            "thirtyfour_ml": 0,
            "passive_tests_performed": 15,
            "changes_material": "Sem ocorrencias",
            "cnh_collected": 0,
            "fined": 44,
            "towed": 0,
            "removal_resolutions": 270,
            "arrests_means_evidence": 0,
            "art307": 1,
            "criminal_occurrences": 0,
            "driving_canceled_license": 1,
            "vehicle_resolutions": "Nenhuma",
            "administrative_tests": "Padrao",
            "cep": "20000-000",
            "street": "Rua A",
            "city": "Rio de Janeiro",
            "district": "Centro",
            "number": "100",
        }
        payload.update(overrides)
        return InspectionReportOperation.objects.create(**payload)

    def make_fine(self, operation, **overrides):
        payload = {
            "operation": operation,
            "source_id": 1001,
            "art": "165",
            "quant": 3,
            "source_created_at": datetime(2026, 8, 10, 8, 6, tzinfo=timezone.utc),
            "source_updated_at": datetime(2026, 8, 10, 8, 36, tzinfo=timezone.utc),
        }
        payload.update(overrides)
        return InspectionFine.objects.create(**payload)

    def test_creates_inspection_report(self):
        report = self.make_report()

        self.assertEqual(report.status, InspectionReport.ReportStatus.SYNCED)
        self.assertEqual(report.statistics_status, InspectionReport.StatisticsStatus.PENDING)
        self.assertEqual(report.team, "A3")
        self.assertEqual(report.management_id, 12)

    def test_report_source_id_is_unique(self):
        source_id = uuid.uuid4()
        self.make_report(source_id=source_id)

        with self.assertRaises(IntegrityError):
            self.make_report(source_id=source_id)

    def test_report_can_have_multiple_operations(self):
        report = self.make_report()
        self.make_operation(report, address_operation="Rua A")
        self.make_operation(report, source_id=uuid.uuid4(), address_operation="Rua B")

        self.assertEqual(report.operations.count(), 2)

    def test_operation_can_have_multiple_fines(self):
        report = self.make_report()
        operation = self.make_operation(report)
        self.make_fine(operation, source_id=1001, art="165", quant=3)
        self.make_fine(operation, source_id=1002, art="306", quant=2)

        self.assertEqual(operation.fines.count(), 2)

    def test_fined_is_independent_from_sum_of_fines(self):
        report = self.make_report()
        operation = self.make_operation(report, fined=44)
        self.make_fine(operation, source_id=1001, quant=3)
        self.make_fine(operation, source_id=1002, quant=2)

        self.assertEqual(operation.fined, 44)
        self.assertEqual(sum(f.quant or 0 for f in operation.fines.all()), 5)

    def test_preserves_anomalous_removal_resolutions_value(self):
        report = self.make_report()
        operation = self.make_operation(report, removal_resolutions=270)

        self.assertEqual(operation.removal_resolutions, 270)

    def test_preserves_real_external_case_for_team_a3_on_2026_08_10(self):
        report = self.make_report(team="A3", operation_date=date(2026, 8, 10))
        operation = self.make_operation(
            report,
            approach=93,
            reconductor=10,
            refusal=5,
            four_ml=88,
            thirtythree_ml=0,
            thirtyfour_ml=0,
            fined=44,
            towed=0,
            cnh_collected=0,
            removal_resolutions=270,
            driving_canceled_license=1,
        )

        self.assertEqual(report.team, "A3")
        self.assertEqual(report.operation_date, date(2026, 8, 10))
        self.assertEqual(operation.approach, 93)
        self.assertEqual(operation.reconductor, 10)
        self.assertEqual(operation.refusal, 5)
        self.assertEqual(operation.four_ml, 88)
        self.assertEqual(operation.thirtythree_ml, 0)
        self.assertEqual(operation.thirtyfour_ml, 0)
        self.assertEqual(operation.fined, 44)
        self.assertEqual(operation.towed, 0)
        self.assertEqual(operation.cnh_collected, 0)
        self.assertEqual(operation.removal_resolutions, 270)
        self.assertEqual(operation.driving_canceled_license, 1)

    def test_optional_fields_can_be_null_or_blank(self):
        report = self.make_report(
            management_id=None,
            military_chief_source_id=None,
            segov_team_civil="",
            segov_team_military="",
            change_ols="",
            agent_detran=None,
            number_trailers=None,
            change_support="",
            cars="",
            changes_general="",
        )
        operation = self.make_operation(
            report,
            address_operation="",
            locality="",
            departure_meeting_point="",
            operation_assembly="",
            first_approach="",
            closing="",
            approach=None,
            reconductor=None,
            refusal=None,
            celebrities_authorities=None,
            four_ml=None,
            thirtythree_ml=None,
            thirtyfour_ml=None,
            passive_tests_performed=None,
            changes_material="",
            cnh_collected=None,
            fined=None,
            towed=None,
            removal_resolutions=None,
            arrests_means_evidence=None,
            art307=None,
            criminal_occurrences=None,
            driving_canceled_license=None,
            vehicle_resolutions="",
            administrative_tests="",
            cep="",
            street="",
            city="",
            district="",
            number="",
        )

        self.assertIsNone(report.management_id)
        self.assertIsNone(operation.approach)
        self.assertEqual(operation.address_operation, "")

    def test_null_and_zero_are_preserved_as_distinct_values(self):
        report = self.make_report()
        operation = self.make_operation(
            report,
            approach=None,
            reconductor=0,
            refusal=None,
            four_ml=0,
            cnh_collected=None,
            towed=0,
        )

        self.assertIsNone(operation.approach)
        self.assertEqual(operation.reconductor, 0)
        self.assertIsNone(operation.refusal)
        self.assertEqual(operation.four_ml, 0)
        self.assertIsNone(operation.cnh_collected)
        self.assertEqual(operation.towed, 0)

    def test_creates_status_history(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="manager@example.com",
            password="secret123",
            role=user_model.Role.MANAGER,
        )
        report = self.make_report()

        history = InspectionReportStatusHistory.objects.create(
            report=report,
            old_status=InspectionReport.ReportStatus.SYNCED,
            new_status=InspectionReport.ReportStatus.PENDING_REVIEW,
            changed_by=user,
            notes="Encaminhado para revisao",
        )

        self.assertEqual(report.status_history.count(), 1)
        self.assertEqual(history.changed_by, user)
        self.assertEqual(history.new_status, InspectionReport.ReportStatus.PENDING_REVIEW)

    def test_creates_statistics_history(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="cooadm@example.com",
            password="secret123",
            role=user_model.Role.VISITOR,
        )
        report = self.make_report()

        history = InspectionStatisticsDecisionHistory.objects.create(
            report=report,
            old_status=InspectionReport.StatisticsStatus.PENDING,
            new_status=InspectionReport.StatisticsStatus.EXCLUDED,
            changed_by=user,
            notes="Inconsistencia no quantitativo.",
        )

        self.assertEqual(report.statistics_history.count(), 1)
        self.assertEqual(history.changed_by, user)
        self.assertEqual(history.new_status, InspectionReport.StatisticsStatus.EXCLUDED)

    def test_creates_official_statistic(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="generator@example.com",
            password="secret123",
            role=user_model.Role.VISITOR,
        )
        report = self.make_report()

        statistic = InspectionStatistic.objects.create(
            report=report,
            source_report_id=report.source_id,
            operation_date=report.operation_date,
            team=report.team,
            snapshot_source_updated_at=report.source_updated_at,
            generated_by=user,
            operations_count=1,
            approach=93,
            reconductor=10,
            refusal=5,
            celebrities_authorities=0,
            four_ml=88,
            thirtythree_ml=0,
            thirtyfour_ml=0,
            passive_tests_performed=15,
            cnh_collected=0,
            fined=44,
            towed=0,
            removal_resolutions=270,
            arrests_means_evidence=0,
            art307=1,
            criminal_occurrences=0,
            driving_canceled_license=1,
        )

        self.assertEqual(statistic.report, report)
        self.assertEqual(statistic.source_report_id, report.source_id)
        self.assertEqual(statistic.approach, 93)

    def test_relationship_delete_behavior_is_cascade_and_user_is_set_null(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email="reviewer@example.com",
            password="secret123",
            role=user_model.Role.MANAGER,
        )
        report = self.make_report()
        operation = self.make_operation(report)
        fine = self.make_fine(operation)
        history = InspectionReportStatusHistory.objects.create(
            report=report,
            old_status=InspectionReport.ReportStatus.SYNCED,
            new_status=InspectionReport.ReportStatus.APPROVED,
            changed_by=user,
        )
        statistics_history = InspectionStatisticsDecisionHistory.objects.create(
            report=report,
            old_status=InspectionReport.StatisticsStatus.PENDING,
            new_status=InspectionReport.StatisticsStatus.INCLUDED,
            changed_by=user,
        )
        statistic = InspectionStatistic.objects.create(
            report=report,
            source_report_id=report.source_id,
            operation_date=report.operation_date,
            team=report.team,
            snapshot_source_updated_at=report.source_updated_at,
            generated_by=user,
            operations_count=1,
        )

        user.delete()
        history.refresh_from_db()
        statistics_history.refresh_from_db()
        statistic.refresh_from_db()
        self.assertIsNone(history.changed_by)
        self.assertIsNone(statistics_history.changed_by)
        self.assertIsNone(statistic.generated_by)

        report.delete()
        self.assertFalse(InspectionReportOperation.objects.filter(pk=operation.pk).exists())
        self.assertFalse(InspectionFine.objects.filter(pk=fine.pk).exists())
        self.assertFalse(InspectionReportStatusHistory.objects.filter(pk=history.pk).exists())
        self.assertFalse(InspectionStatisticsDecisionHistory.objects.filter(pk=statistics_history.pk).exists())
        self.assertFalse(InspectionStatistic.objects.filter(pk=statistic.pk).exists())
