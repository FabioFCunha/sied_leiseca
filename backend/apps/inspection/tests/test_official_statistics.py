import uuid
from copy import deepcopy
from datetime import date, datetime, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.inspection.models import InspectionReport, InspectionStatistic, InspectionStatisticsDecisionHistory
from apps.inspection.services import (
    InspectionOfficialStatisticService,
    InspectionStatisticsService,
    build_official_statistic_fields_from_snapshot,
)
from apps.schedules.models import Sector


class InspectionOfficialStatisticServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="cooadm@example.com",
            password="secret123",
            full_name="Usuario CooAdm",
            role=get_user_model().Role.VISITOR,
            sector=Sector.objects.create(name="OLS/CooAdm"),
        )
        self.report = InspectionReport.objects.create(
            source_id=uuid.uuid4(),
            source_created_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc),
            synced_at=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
            operation_date=date(2026, 8, 10),
            team="A3",
            statistics_status=InspectionReport.StatisticsStatus.PENDING,
        )
        self.snapshot = {
            "report": {
                "source_id": str(self.report.source_id),
                "source_created_at": "2026-08-10T08:00:00+00:00",
                "source_updated_at": "2026-08-10T08:30:00+00:00",
                "operation_date": "2026-08-10",
                "team": "A3",
            },
            "operations": [
                {
                    "source_id": str(uuid.uuid4()),
                    "approach": 93,
                    "reconductor": 10,
                    "refusal": 5,
                    "celebrities_authorities": 0,
                    "four_ml": 88,
                    "thirtythree_ml": 0,
                    "thirtyfour_ml": 0,
                    "passive_tests_performed": 0,
                    "cnh_collected": 0,
                    "fined": 44,
                    "towed": 0,
                    "removal_resolutions": 270,
                    "arrests_means_evidence": 0,
                    "art307": 0,
                    "criminal_occurrences": 0,
                    "driving_canceled_license": 1,
                    "fines": [{"source_id": 123, "quant": 2}],
                }
            ],
            "traceability": {
                "source_updated_at": "2026-08-10T08:30:00+00:00",
                "statistics_reviewed_at": "2026-08-12T12:00:00+00:00",
                "statistics_reviewed_by": {
                    "id": 1,
                    "full_name": "Usuario CooAdm",
                    "email": "cooadm@example.com",
                },
            },
        }
        self.service = InspectionOfficialStatisticService()

    def mark_included(self, snapshot=None):
        self.report.statistics_status = InspectionReport.StatisticsStatus.INCLUDED
        self.report.statistics_snapshot = snapshot if snapshot is not None else deepcopy(self.snapshot)
        self.report.statistics_reviewed_by = self.user
        self.report.statistics_reviewed_at = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        self.report.save(
            update_fields=[
                "statistics_status",
                "statistics_snapshot",
                "statistics_reviewed_by",
                "statistics_reviewed_at",
            ]
        )

    def test_pending_report_does_not_generate_statistic(self):
        with self.assertRaises(ValidationError):
            self.service.generate_for_report(self.report, generated_by=self.user)
        self.assertEqual(InspectionStatistic.objects.count(), 0)

    def test_excluded_report_does_not_generate_statistic(self):
        self.report.statistics_status = InspectionReport.StatisticsStatus.EXCLUDED
        self.report.statistics_snapshot = deepcopy(self.snapshot)
        self.report.save(update_fields=["statistics_status", "statistics_snapshot"])

        with self.assertRaises(ValidationError):
            self.service.generate_for_report(self.report, generated_by=self.user)
        self.assertEqual(InspectionStatistic.objects.count(), 0)

    def test_snapshot_absent_blocks_generation(self):
        self.report.statistics_status = InspectionReport.StatisticsStatus.INCLUDED
        self.report.save(update_fields=["statistics_status"])

        with self.assertRaises(ValidationError):
            self.service.generate_for_report(self.report, generated_by=self.user)
        self.assertEqual(InspectionStatistic.objects.count(), 0)

    def test_included_generates_official_statistic_for_a3(self):
        self.mark_included()

        result = self.service.generate_for_report(self.report, generated_by=self.user)
        statistic = result.statistic

        self.assertEqual(result.outcome, "created")
        self.assertEqual(statistic.operations_count, 1)
        self.assertEqual(statistic.approach, 93)
        self.assertEqual(statistic.refusal, 5)
        self.assertEqual(statistic.fined, 44)
        self.assertEqual(statistic.removal_resolutions, 270)

    def test_generation_is_idempotent(self):
        self.mark_included()
        first = self.service.generate_for_report(self.report, generated_by=self.user)
        second = self.service.generate_for_report(self.report, generated_by=self.user)

        self.assertEqual(first.outcome, "created")
        self.assertEqual(second.outcome, "existing")
        self.assertEqual(InspectionStatistic.objects.count(), 1)

    def test_multiple_operations_are_summed(self):
        snapshot = deepcopy(self.snapshot)
        snapshot["operations"] = [
            {
                "source_id": str(uuid.uuid4()),
                "approach": 100,
                "reconductor": 10,
                "refusal": 5,
                "celebrities_authorities": 0,
                "four_ml": 50,
                "thirtythree_ml": 1,
                "thirtyfour_ml": 0,
                "passive_tests_performed": 2,
                "cnh_collected": 0,
                "fined": 30,
                "towed": 1,
                "removal_resolutions": 200,
                "arrests_means_evidence": 0,
                "art307": 0,
                "criminal_occurrences": 1,
                "driving_canceled_license": 0,
                "fines": [],
            },
            {
                "source_id": str(uuid.uuid4()),
                "approach": 80,
                "reconductor": 5,
                "refusal": 3,
                "celebrities_authorities": 1,
                "four_ml": 38,
                "thirtythree_ml": 2,
                "thirtyfour_ml": 1,
                "passive_tests_performed": 0,
                "cnh_collected": 1,
                "fined": 20,
                "towed": 0,
                "removal_resolutions": 70,
                "arrests_means_evidence": 1,
                "art307": 1,
                "criminal_occurrences": 0,
                "driving_canceled_license": 1,
                "fines": [],
            },
        ]
        self.mark_included(snapshot=snapshot)

        statistic = self.service.generate_for_report(self.report, generated_by=self.user).statistic

        self.assertEqual(statistic.operations_count, 2)
        self.assertEqual(statistic.approach, 180)
        self.assertEqual(statistic.refusal, 8)
        self.assertEqual(statistic.fined, 50)
        self.assertEqual(statistic.removal_resolutions, 270)

    def test_null_plus_null_results_in_null(self):
        snapshot = deepcopy(self.snapshot)
        snapshot["operations"] = [
            {"source_id": str(uuid.uuid4()), "approach": 10, "refusal": None, "fined": 1},
            {"source_id": str(uuid.uuid4()), "approach": 20, "refusal": None, "fined": 2},
        ]
        self.mark_included(snapshot=snapshot)

        statistic = self.service.generate_for_report(self.report, generated_by=self.user).statistic

        self.assertIsNone(statistic.refusal)
        self.assertEqual(statistic.approach, 30)

    def test_value_plus_null_results_in_value(self):
        snapshot = deepcopy(self.snapshot)
        snapshot["operations"] = [
            {"source_id": str(uuid.uuid4()), "approach": 10, "refusal": 3, "fined": 1},
            {"source_id": str(uuid.uuid4()), "approach": 20, "refusal": None, "fined": 2},
        ]
        self.mark_included(snapshot=snapshot)

        statistic = self.service.generate_for_report(self.report, generated_by=self.user).statistic

        self.assertEqual(statistic.refusal, 3)

    def test_zero_is_preserved(self):
        snapshot = deepcopy(self.snapshot)
        snapshot["operations"] = [
            {"source_id": str(uuid.uuid4()), "approach": 0, "refusal": 0, "fined": 0, "four_ml": 0},
        ]
        self.mark_included(snapshot=snapshot)

        statistic = self.service.generate_for_report(self.report, generated_by=self.user).statistic

        self.assertEqual(statistic.approach, 0)
        self.assertEqual(statistic.refusal, 0)
        self.assertEqual(statistic.fined, 0)
        self.assertEqual(statistic.four_ml, 0)

    def test_fined_does_not_come_from_fines_sum(self):
        self.mark_included()

        statistic = self.service.generate_for_report(self.report, generated_by=self.user).statistic

        self.assertEqual(statistic.fined, 44)
        self.assertNotEqual(statistic.fined, 2)

    def test_horus_update_after_review_does_not_change_existing_statistic(self):
        self.mark_included()
        statistic = self.service.generate_for_report(self.report, generated_by=self.user).statistic

        self.report.has_source_update_after_statistics_review = True
        self.report.source_update_after_statistics_review_at = datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc)
        self.report.statistics_snapshot = deepcopy(self.snapshot)
        self.report.save(
            update_fields=[
                "has_source_update_after_statistics_review",
                "source_update_after_statistics_review_at",
                "statistics_snapshot",
            ]
        )

        statistic.refresh_from_db()
        self.assertEqual(statistic.approach, 93)
        self.assertEqual(statistic.removal_resolutions, 270)

    def test_snapshot_is_the_only_source_for_official_statistic(self):
        fields = build_official_statistic_fields_from_snapshot(deepcopy(self.snapshot))

        self.assertEqual(fields["approach"], 93)
        self.assertEqual(fields["fined"], 44)
        self.assertEqual(fields["removal_resolutions"], 270)


class InspectionStatisticsServiceIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="cooadm@example.com",
            password="secret123",
            full_name="Usuario CooAdm",
            role=get_user_model().Role.VISITOR,
            sector=Sector.objects.create(name="OLS/CooAdm"),
        )
        self.report = InspectionReport.objects.create(
            source_id=uuid.uuid4(),
            source_created_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc),
            synced_at=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
            operation_date=date(2026, 8, 10),
            team="A3",
        )
        self.report.operations.create(
            source_id=uuid.uuid4(),
            source_created_at=datetime(2026, 8, 10, 8, 5, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 35, tzinfo=timezone.utc),
            approach=93,
            reconductor=10,
            refusal=5,
            celebrities_authorities=0,
            four_ml=88,
            thirtythree_ml=0,
            thirtyfour_ml=0,
            passive_tests_performed=0,
            cnh_collected=0,
            fined=44,
            towed=0,
            removal_resolutions=270,
            arrests_means_evidence=0,
            art307=0,
            criminal_occurrences=0,
            driving_canceled_license=1,
        )

    def test_include_generates_official_statistic(self):
        result = InspectionStatisticsService().include_report(self.report.id, user=self.user)

        self.assertEqual(result.outcome, "included")
        self.report.refresh_from_db()
        self.assertEqual(self.report.statistics_status, InspectionReport.StatisticsStatus.INCLUDED)
        self.assertTrue(InspectionStatistic.objects.filter(report=self.report).exists())

    def test_generation_failure_rolls_back_homologation(self):
        with patch(
            "apps.inspection.services.InspectionOfficialStatisticService.generate_for_report",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                InspectionStatisticsService().include_report(self.report.id, user=self.user)

        self.report.refresh_from_db()
        self.assertEqual(self.report.statistics_status, InspectionReport.StatisticsStatus.PENDING)
        self.assertIsNone(self.report.statistics_snapshot)
        self.assertEqual(InspectionStatistic.objects.count(), 0)
        self.assertEqual(InspectionStatisticsDecisionHistory.objects.count(), 0)
