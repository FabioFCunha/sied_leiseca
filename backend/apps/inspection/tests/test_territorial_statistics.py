import uuid
from datetime import date, datetime, timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.inspection.models import (
    InspectionHistoricalTerritorialStatistic,
    InspectionMunicipality,
    InspectionRegion,
    InspectionReport,
    InspectionReportOperation,
)
from apps.inspection.territorial_statistics import (
    InspectionTerritorialStatisticsService,
)


class InspectionTerritorialStatisticsServiceTestCase(
    TestCase
):
    def setUp(self):
        self.metropolitana = (
            InspectionRegion.objects.get(
                code="METROPOLITANA"
            )
        )
        self.costa_verde = (
            InspectionRegion.objects.get(
                name="Costa Verde"
            )
        )
        self.niteroi = (
            InspectionMunicipality.objects.get(
                name="Niterói"
            )
        )
        self.sao_goncalo = (
            InspectionMunicipality.objects.get(
                name="São Gonçalo"
            )
        )
        self.angra = (
            InspectionMunicipality.objects.get(
                name="Angra dos Reis"
            )
        )

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

    def _create_historical_row(
        self,
        *,
        reference_date,
        team,
        municipality=None,
        operations_count,
        approach,
        refusal=0,
        thirtythree_ml=0,
        thirtyfour_ml=0,
        arrests_means_evidence=0,
        fined=0,
        source_city=None,
        normalized_city=None,
    ):
        region = (
            municipality.region
            if municipality is not None
            else None
        )

        return (
            InspectionHistoricalTerritorialStatistic
            .objects.create(
                reference_date=reference_date,
                team=team,
                municipality=municipality,
                region=region,
                source_city=(
                    source_city
                    if source_city is not None
                    else (
                        municipality.name
                        if municipality
                        else ""
                    )
                ),
                normalized_city=(
                    normalized_city
                    if normalized_city is not None
                    else (
                        municipality.normalized_name
                        if municipality
                        else ""
                    )
                ),
                reports_count=1,
                operations_count=operations_count,
                approach=approach,
                refusal=refusal,
                thirtythree_ml=thirtythree_ml,
                thirtyfour_ml=thirtyfour_ml,
                arrests_means_evidence=(
                    arrests_means_evidence
                ),
                fined=fined,
            )
        )

    def test_only_historical_period_uses_historical_source(self):
        self._create_historical_row(
            reference_date=date(2023, 1, 15),
            team="A1",
            municipality=self.niteroi,
            operations_count=3,
            approach=120,
            refusal=12,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2023-01-01",
                    "date_to": "2023-12-31",
                }
            ).get_data()
        )

        self.assertEqual(
            data["meta"]["sources_used"],
            ["historical"],
        )
        self.assertEqual(
            data["summary"]["operations"],
            3,
        )
        self.assertEqual(
            data["summary"]["classified_operations"],
            3,
        )
        self.assertEqual(
            data["summary"]["approach"],
            120,
        )
        self.assertEqual(
            data["highlighted_operations"],
            [],
        )
        self.assertFalse(
            data["meta"][
                "historical_highlighted_supported"
            ]
        )

    def test_only_operational_period_uses_operational_source(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=25,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2026-08-10",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["meta"]["sources_used"],
            ["operational"],
        )
        self.assertEqual(
            data["summary"]["operations"],
            1,
        )
        self.assertEqual(
            len(data["highlighted_operations"]),
            1,
        )

    def test_period_crossing_cut_sums_without_overlap(self):
        self._create_historical_row(
            reference_date=date(2026, 8, 9),
            team="A1",
            municipality=self.niteroi,
            operations_count=2,
            approach=40,
            refusal=4,
        )

        report_operational = self._create_report(
            team="A1",
            operation_date="2026-08-10",
        )
        self._create_operation(
            report=report_operational,
            city="Angra dos Reis",
            approach=60,
            refusal=6,
        )

        report_pre_cutoff = self._create_report(
            team="A1",
            operation_date="2026-08-09",
        )
        self._create_operation(
            report=report_pre_cutoff,
            city="Niterói",
            approach=999,
            refusal=999,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2026-08-09",
                    "date_to": "2026-08-10",
                }
            ).get_data()
        )

        self.assertEqual(
            data["meta"]["sources_used"],
            ["historical", "operational"],
        )
        self.assertEqual(
            data["summary"]["operations"],
            3,
        )
        self.assertEqual(
            data["summary"]["approach"],
            100,
        )
        self.assertEqual(
            data["summary"]["refusal"],
            10,
        )

    def test_start_before_coverage_does_not_invent_territorialization(self):
        self._create_historical_row(
            reference_date=date(2022, 10, 3),
            team="A1",
            municipality=self.niteroi,
            operations_count=5,
            approach=50,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2009-01-01",
                    "date_to": "2022-10-03",
                }
            ).get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            5,
        )
        self.assertEqual(
            data["summary"]["approach"],
            50,
        )
        self.assertEqual(
            data["meta"][
                "territorial_coverage_from"
            ],
            "2022-10-03",
        )

    def test_region_filter_applies_to_both_sources(self):
        self._create_historical_row(
            reference_date=date(2023, 5, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=4,
            approach=40,
        )
        self._create_historical_row(
            reference_date=date(2023, 5, 1),
            team="A1",
            municipality=self.angra,
            operations_count=7,
            approach=70,
        )

        report = self._create_report(
            team="A1",
            operation_date="2026-08-12",
        )
        self._create_operation(
            report=report,
            city="Rio de Janeiro",
            approach=30,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "region": "Metropolitana",
                    "date_from": "2023-01-01",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            5,
        )
        self.assertEqual(
            data["summary"]["approach"],
            70,
        )
        self.assertEqual(
            data["summary"]["unclassified_operations"],
            0,
        )
        self.assertEqual(
            len(data["regions"]),
            1,
        )
        self.assertEqual(
            data["regions"][0]["region_code"],
            "METROPOLITANA",
        )

    def test_municipality_filter_applies_to_both_sources(self):
        self._create_historical_row(
            reference_date=date(2024, 2, 10),
            team="A1",
            municipality=self.niteroi,
            operations_count=2,
            approach=20,
        )
        self._create_historical_row(
            reference_date=date(2024, 2, 10),
            team="A1",
            municipality=self.sao_goncalo,
            operations_count=5,
            approach=50,
        )

        report = self._create_report(
            team="A1",
            operation_date="2026-08-11",
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=15,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "municipality": "niteroi",
                    "date_from": "2024-01-01",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            3,
        )
        self.assertEqual(
            data["summary"]["approach"],
            35,
        )
        self.assertEqual(
            data["regions"][0]["municipalities"][0][
                "municipality"
            ],
            "Niterói",
        )

    def test_team_filter_applies_to_both_sources(self):
        self._create_historical_row(
            reference_date=date(2025, 1, 20),
            team="A1",
            municipality=self.niteroi,
            operations_count=3,
            approach=30,
        )
        self._create_historical_row(
            reference_date=date(2025, 1, 20),
            team="B2",
            municipality=self.niteroi,
            operations_count=4,
            approach=40,
        )

        report_a1 = self._create_report(
            team="A1",
            operation_date="2026-08-12",
        )
        self._create_operation(
            report=report_a1,
            city="Niterói",
            approach=10,
        )

        report_b2 = self._create_report(
            team="B2",
            operation_date="2026-08-12",
        )
        self._create_operation(
            report=report_b2,
            city="Niterói",
            approach=20,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "team": "A1",
                    "date_from": "2025-01-01",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            4,
        )
        self.assertEqual(
            data["summary"]["approach"],
            40,
        )

    def test_unclassified_without_filter_includes_historical_and_operational(self):
        self._create_historical_row(
            reference_date=date(2023, 3, 1),
            team="A1",
            municipality=None,
            operations_count=5,
            approach=50,
            source_city="NÃO CLASSIFICADO",
            normalized_city="NAO CLASSIFICADO",
        )
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )
        self._create_operation(
            report=report,
            city="Municipio Inexistente",
            approach=10,
            refusal=2,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2023-01-01",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            6,
        )
        self.assertEqual(
            data["summary"]["classified_operations"],
            0,
        )
        self.assertEqual(
            data["summary"]["unclassified_operations"],
            6,
        )
        self.assertEqual(
            len(data["unclassified"]),
            2,
        )

    def test_unclassified_are_excluded_when_there_is_territorial_filter(self):
        self._create_historical_row(
            reference_date=date(2023, 3, 1),
            team="A1",
            municipality=None,
            operations_count=5,
            approach=50,
            source_city="NÃO CLASSIFICADO",
            normalized_city="NAO CLASSIFICADO",
        )
        self._create_historical_row(
            reference_date=date(2023, 3, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=2,
            approach=20,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "region": "Metropolitana",
                    "date_from": "2023-01-01",
                    "date_to": "2023-12-31",
                }
            ).get_data()
        )

        self.assertEqual(
            data["summary"]["operations"],
            2,
        )
        self.assertEqual(
            data["summary"]["unclassified_operations"],
            0,
        )
        self.assertEqual(
            data["unclassified"],
            [],
        )

    def test_alcohol_percentage_is_recalculated_after_union(self):
        self._create_historical_row(
            reference_date=date(2024, 4, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=2,
            approach=10,
            refusal=5,
        )

        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=90,
            refusal=9,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["summary"]["alcohol_cases"],
            14,
        )
        self.assertEqual(
            data["summary"]["approach"],
            100,
        )
        self.assertAlmostEqual(
            data["summary"]["alcohol_percentage"],
            14.0,
        )

    def test_endpoint_contract_is_preserved(self):
        self._create_historical_row(
            reference_date=date(2023, 6, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=10,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2023-01-01",
                    "date_to": "2023-12-31",
                }
            ).get_data()
        )

        self.assertEqual(
            set(data.keys()),
            {
                "meta",
                "summary",
                "metropolitan",
                "interior",
                "regions",
                "highlighted_operations",
                "unclassified",
            },
        )
        self.assertIn("sources_used", data["meta"])
        self.assertIn(
            "territorial_coverage_from",
            data["meta"],
        )


class InspectionTerritorialStatisticsEndpointTestCase(
    TestCase
):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create(
            email="territorial@example.com",
            password="secret123",
            role=user_model.Role.ADMIN,
        )
        self.client = APIClient()
        self.client.force_authenticate(
            user=self.user
        )
        self.url = reverse(
            "inspection-territorial-statistics"
        )

    def test_endpoint_returns_unified_contract(self):
        response = self.client.get(
            self.url,
            {
                "date_from": "2009-01-01",
                "date_to": "2026-08-20",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            set(response.data.keys()),
            {
                "meta",
                "summary",
                "metropolitan",
                "interior",
                "regions",
                "highlighted_operations",
                "unclassified",
            },
        )
