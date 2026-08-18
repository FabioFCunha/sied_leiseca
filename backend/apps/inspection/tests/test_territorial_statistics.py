import uuid
from datetime import datetime, timezone

from django.test import TestCase

from apps.inspection.models import (
    InspectionReport,
    InspectionReportOperation,
)
from apps.inspection.territorial_statistics import (
    InspectionTerritorialStatisticsService,
)


class InspectionTerritorialStatisticsServiceTestCase(TestCase):
    def _create_report(
        self,
        *,
        team,
        operation_date,
        statistics_status=InspectionReport.StatisticsStatus.INCLUDED,
    ):
        now = datetime.now(timezone.utc)

        return InspectionReport.objects.create(
            source_id=uuid.uuid4(),
            source_created_at=now,
            source_updated_at=now,
            synced_at=now,
            operation_date=operation_date,
            team=team,
            statistics_status=statistics_status,
        )

    def _create_operation(
        self,
        *,
        report,
        city,
        approach,
        refusal=0,
        thirtythree_ml=0,
        thirtyfour_ml=0,
        arrests_means_evidence=0,
        fined=0,
        towed=0,
    ):
        now = datetime.now(timezone.utc)

        return InspectionReportOperation.objects.create(
            report=report,
            source_id=uuid.uuid4(),
            source_created_at=now,
            source_updated_at=now,
            city=city,
            approach=approach,
            refusal=refusal,
            thirtythree_ml=thirtythree_ml,
            thirtyfour_ml=thirtyfour_ml,
            arrests_means_evidence=arrests_means_evidence,
            fined=fined,
            towed=towed,
        )

    def test_groups_metropolitan_and_interior(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )

        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=10,
        )

        self._create_operation(
            report=report,
            city="Angra dos Reis",
            approach=100,
            refusal=20,
        )

        data = (
            InspectionTerritorialStatisticsService({})
            .get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            2,
        )

        self.assertEqual(
            data["summary"]["classified_operations"],
            2,
        )

        self.assertEqual(
            data["metropolitan"]["operations"],
            1,
        )

        self.assertEqual(
            data["interior"]["operations"],
            1,
        )

        self.assertEqual(
            data["metropolitan"]["approach"],
            100,
        )

        self.assertEqual(
            data["interior"]["approach"],
            100,
        )

    def test_alcohol_cases_follow_official_formula(self):
        report = self._create_report(
            team="A9",
            operation_date="2026-08-15",
        )

        self._create_operation(
            report=report,
            city="Angra dos Reis",
            approach=100,
            refusal=20,
            thirtythree_ml=3,
            thirtyfour_ml=1,
            arrests_means_evidence=1,
        )

        data = (
            InspectionTerritorialStatisticsService({})
            .get_data()
        )

        self.assertEqual(
            data["summary"]["alcohol_cases"],
            25,
        )

        self.assertEqual(
            data["summary"]["alcohol_percentage"],
            25.0,
        )

    def test_25_percent_is_highlighted(self):
        report = self._create_report(
            team="A9",
            operation_date="2026-08-15",
        )

        self._create_operation(
            report=report,
            city="Angra dos Reis",
            approach=100,
            refusal=25,
        )

        data = (
            InspectionTerritorialStatisticsService({})
            .get_data()
        )

        self.assertEqual(
            len(data["highlighted_operations"]),
            1,
        )

        highlighted = data[
            "highlighted_operations"
        ][0]

        self.assertEqual(
            highlighted["municipality"],
            "Angra dos Reis",
        )

        self.assertEqual(
            highlighted["region"],
            "Costa Verde",
        )

        self.assertEqual(
            highlighted["territorial_group"],
            "INTERIOR",
        )

        self.assertEqual(
            highlighted["alcohol_percentage"],
            25.0,
        )

    def test_below_25_percent_is_not_highlighted(self):
        report = self._create_report(
            team="A9",
            operation_date="2026-08-15",
        )

        self._create_operation(
            report=report,
            city="Angra dos Reis",
            approach=1000,
            refusal=249,
        )

        data = (
            InspectionTerritorialStatisticsService({})
            .get_data()
        )

        self.assertEqual(
            data["summary"]["alcohol_percentage"],
            24.9,
        )

        self.assertEqual(
            data["highlighted_operations"],
            [],
        )

    def test_31_7_percent_is_highlighted(self):
        report = self._create_report(
            team="A9",
            operation_date="2026-08-15",
        )

        self._create_operation(
            report=report,
            city="Angra dos Reis",
            approach=101,
            refusal=29,
            thirtythree_ml=3,
        )

        data = (
            InspectionTerritorialStatisticsService({})
            .get_data()
        )

        highlighted = data[
            "highlighted_operations"
        ][0]

        self.assertEqual(
            highlighted["alcohol_cases"],
            32,
        )

        self.assertEqual(
            highlighted["alcohol_percentage"],
            31.68,
        )

    def test_unknown_city_is_unclassified(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )

        self._create_operation(
            report=report,
            city="Municipio Inexistente",
            approach=50,
            refusal=5,
        )

        data = (
            InspectionTerritorialStatisticsService({})
            .get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            1,
        )

        self.assertEqual(
            data["summary"]["classified_operations"],
            0,
        )

        self.assertEqual(
            data["summary"]["unclassified_operations"],
            1,
        )

        self.assertEqual(
            len(data["unclassified"]),
            1,
        )

    def test_region_filter_changes_summary(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )

        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=10,
        )

        self._create_operation(
            report=report,
            city="Angra dos Reis",
            approach=200,
            refusal=20,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "region": "METROPOLITANA",
                }
            )
            .get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            1,
        )

        self.assertEqual(
            data["summary"]["approach"],
            100,
        )

        self.assertEqual(
            data["interior"]["operations"],
            0,
        )

        self.assertEqual(
            data["metropolitan"]["operations"],
            1,
        )

    def test_municipality_filter_changes_summary(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )

        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=10,
        )

        self._create_operation(
            report=report,
            city="São Gonçalo",
            approach=200,
            refusal=20,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "municipality": "niteroi",
                }
            )
            .get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            1,
        )

        self.assertEqual(
            data["summary"]["approach"],
            100,
        )

        self.assertEqual(
            data["regions"][0][
                "municipalities"
            ][0]["municipality"],
            "Niterói",
        )

    def test_excluded_report_is_not_counted(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
            statistics_status=(
                InspectionReport
                .StatisticsStatus
                .EXCLUDED
            ),
        )

        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=30,
        )

        data = (
            InspectionTerritorialStatisticsService({})
            .get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            0,
        )

    def test_before_operational_cutoff_is_not_counted(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-09",
        )

        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=30,
        )

        data = (
            InspectionTerritorialStatisticsService({})
            .get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            0,
        )