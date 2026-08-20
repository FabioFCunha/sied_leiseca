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
    InspectionTerritorialRankingService,
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
        self.rio = (
            InspectionMunicipality.objects.get(
                name="Rio de Janeiro"
            )
        )
        self.duque_de_caxias = (
            InspectionMunicipality.objects.get(
                name="Duque de Caxias"
            )
        )
        self.comendador_levy = (
            InspectionMunicipality.objects.get(
                name="Comendador Levy Gasparian"
            )
        )

    def _create_report(
        self,
        *,
        team,
        operation_date,
        statistics_status=InspectionReport.StatisticsStatus.INCLUDED,
        changes_general="",
        statistics_classification=None,
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
            changes_general=changes_general,
            statistics_classification=(
                statistics_classification
                or {}
            ),
        )

    def _create_operation(
        self,
        *,
        report,
        city,
        approach,
        reconductor=0,
        refusal=0,
        thirtythree_ml=0,
        thirtyfour_ml=0,
        arrests_means_evidence=0,
        fined=0,
        towed=0,
        cnh_collected=0,
        removal_resolutions=0,
        criminal_occurrences=0,
    ):
        now = datetime.now(timezone.utc)

        return InspectionReportOperation.objects.create(
            report=report,
            source_id=uuid.uuid4(),
            source_created_at=now,
            source_updated_at=now,
            city=city,
            approach=approach,
            reconductor=reconductor,
            refusal=refusal,
            thirtythree_ml=thirtythree_ml,
            thirtyfour_ml=thirtyfour_ml,
            arrests_means_evidence=arrests_means_evidence,
            fined=fined,
            towed=towed,
            cnh_collected=cnh_collected,
            removal_resolutions=removal_resolutions,
            criminal_occurrences=criminal_occurrences,
        )

    def _create_historical_row(
        self,
        *,
        reference_date,
        team,
        municipality=None,
        operations_count,
        approach,
        reconductor=0,
        refusal=0,
        thirtythree_ml=0,
        thirtyfour_ml=0,
        arrests_means_evidence=0,
        fined=0,
        towed=0,
        cnh_collected=0,
        removal_resolutions=0,
        criminal_occurrences=0,
        source_city=None,
        normalized_city=None,
        rain=0,
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
                rain=rain,
                approach=approach,
                reconductor=reconductor,
                refusal=refusal,
                thirtythree_ml=thirtythree_ml,
                thirtyfour_ml=thirtyfour_ml,
                arrests_means_evidence=(
                    arrests_means_evidence
                ),
                fined=fined,
                towed=towed,
                cnh_collected=cnh_collected,
                removal_resolutions=removal_resolutions,
                criminal_occurrences=criminal_occurrences,
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

    def test_operational_pending_statistics_status_does_not_appear(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
            statistics_status=(
                InspectionReport
                .StatisticsStatus
                .PENDING
            ),
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
            data["summary"]["operations"],
            0,
        )
        self.assertEqual(
            data["regions"],
            [],
        )

    def test_operational_included_statistics_status_appears(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
            statistics_status=(
                InspectionReport
                .StatisticsStatus
                .INCLUDED
            ),
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
            data["summary"]["operations"],
            1,
        )
        self.assertEqual(
            data["summary"]["classified_operations"],
            1,
        )
        self.assertEqual(
            data["regions"][0]["municipalities"][0][
                "municipality"
            ],
            "Niterói",
        )

    def test_operational_excluded_statistics_status_does_not_appear(self):
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
            data["summary"]["operations"],
            0,
        )
        self.assertEqual(
            data["regions"],
            [],
        )

    def test_operational_report_enters_only_after_becoming_included(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
            statistics_status=(
                InspectionReport
                .StatisticsStatus
                .PENDING
            ),
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=75,
            refusal=10,
        )

        pending_data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2026-08-10",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            pending_data["summary"]["operations"],
            0,
        )

        report.statistics_status = (
            InspectionReport
            .StatisticsStatus
            .INCLUDED
        )
        report.save(
            update_fields=["statistics_status"]
        )

        included_data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2026-08-10",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            included_data["summary"]["operations"],
            1,
        )
        self.assertEqual(
            included_data["summary"]["approach"],
            75,
        )
        self.assertEqual(
            included_data["regions"][0]["region_code"],
            "METROPOLITANA",
        )
        self.assertEqual(
            included_data["regions"][0][
                "municipalities"
            ][0]["municipality"],
            "Niterói",
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

    def test_operational_aliases_consolidate_with_official_names(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )
        self._create_operation(
            report=report,
            city="RJ",
            approach=10,
        )
        self._create_operation(
            report=report,
            city="Rio de Janeiro",
            approach=20,
        )
        self._create_operation(
            report=report,
            city="Imbariê",
            approach=30,
        )
        self._create_operation(
            report=report,
            city="Duque de Caxias",
            approach=40,
        )
        self._create_operation(
            report=report,
            city="Com.Levy Gasparian",
            approach=50,
        )
        self._create_operation(
            report=report,
            city="Comendador Levy Gasparian",
            approach=60,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2026-08-10",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        metro = next(
            region
            for region in data["regions"]
            if region["region_code"]
            == "METROPOLITANA"
        )

        municipalities = {
            item["municipality"]: item
            for item in metro["municipalities"]
        }

        self.assertEqual(
            municipalities["Rio de Janeiro"][
                "metrics"
            ]["operations"],
            2,
        )
        self.assertEqual(
            municipalities["Rio de Janeiro"][
                "metrics"
            ]["approach"],
            30,
        )
        self.assertEqual(
            municipalities["Duque de Caxias"][
                "metrics"
            ]["operations"],
            2,
        )
        self.assertEqual(
            municipalities["Duque de Caxias"][
                "metrics"
            ]["approach"],
            70,
        )

        centro_sul = next(
            region
            for region in data["regions"]
            if region["region_code"]
            == "CENTRO_SUL_FLUMINENSE"
        )
        centro_sul_municipalities = {
            item["municipality"]: item
            for item in centro_sul[
                "municipalities"
            ]
        }

        self.assertEqual(
            centro_sul_municipalities[
                "Comendador Levy Gasparian"
            ]["metrics"]["operations"],
            2,
        )
        self.assertEqual(
            centro_sul_municipalities[
                "Comendador Levy Gasparian"
            ]["metrics"]["approach"],
            110,
        )

    def test_historical_municipality_with_rain_preserves_indicator(self):
        self._create_historical_row(
            reference_date=date(2025, 5, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=2,
            approach=20,
            rain=1,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2025-05-01",
                    "date_to": "2025-05-31",
                }
            ).get_data()
        )

        municipality = data["regions"][0][
            "municipalities"
        ][0]

        self.assertEqual(
            municipality["municipality"],
            "Niterói",
        )
        self.assertEqual(
            municipality["rain"],
            1,
        )

    def test_operational_municipality_with_rain_preserves_indicator(self):
        rainy_report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
            changes_general="Operação com chuva intensa",
        )
        self._create_operation(
            report=rainy_report,
            city="Niterói",
            approach=10,
        )
        self._create_operation(
            report=rainy_report,
            city="Niterói",
            approach=15,
        )

        dry_report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )
        self._create_operation(
            report=dry_report,
            city="São Gonçalo",
            approach=12,
        )

        data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2026-08-10",
                    "date_to": "2026-08-16",
                }
            ).get_data()
        )

        municipalities = {
            item["municipality"]: item
            for item in data["regions"][0][
                "municipalities"
            ]
        }

        self.assertEqual(
            municipalities["Niterói"]["rain"],
            1,
        )
        self.assertEqual(
            municipalities["São Gonçalo"]["rain"],
            0,
        )

    def test_rain_period_filter_changes_indicator(self):
        self._create_historical_row(
            reference_date=date(2025, 5, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=10,
            rain=1,
        )
        self._create_historical_row(
            reference_date=date(2025, 6, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=10,
            rain=0,
        )

        may_data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2025-05-01",
                    "date_to": "2025-05-31",
                }
            ).get_data()
        )
        june_data = (
            InspectionTerritorialStatisticsService(
                {
                    "date_from": "2025-06-01",
                    "date_to": "2025-06-30",
                }
            ).get_data()
        )

        self.assertEqual(
            may_data["regions"][0][
                "municipalities"
            ][0]["rain"],
            1,
        )
        self.assertEqual(
            june_data["regions"][0][
                "municipalities"
            ][0]["rain"],
            0,
        )

    def test_unknown_alias_remains_unclassified(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )
        self._create_operation(
            report=report,
            city="Municipio sem alias seguro",
            approach=25,
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


class InspectionTerritorialRankingServiceTestCase(
    InspectionTerritorialStatisticsServiceTestCase
):
    def test_top_10_is_sorted_desc_and_name_tiebreaker(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.sao_goncalo,
            operations_count=1,
            approach=100,
            refusal=11,
        )
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            refusal=11,
        )
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.angra,
            operations_count=1,
            approach=100,
            refusal=5,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "alcohol_cases",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["municipality"],
            "Niterói",
        )
        self.assertEqual(
            data["ranking"][1]["municipality"],
            "São Gonçalo",
        )
        self.assertEqual(
            data["ranking"][2]["municipality"],
            "Angra dos Reis",
        )

    def test_only_historical_period_uses_historical_source(self):
        self._create_historical_row(
            reference_date=date(2023, 7, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=3,
            approach=120,
            refusal=12,
        )

        data = (
            InspectionTerritorialRankingService(
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
            data["ranking"][0]["operations"],
            3,
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
            refusal=8,
        )

        data = (
            InspectionTerritorialRankingService(
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
            data["ranking"][0]["municipality"],
            "Niterói",
        )

    def test_pending_is_excluded_from_ranking(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
            statistics_status=InspectionReport.StatisticsStatus.PENDING,
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=8,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2026-08-10",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"],
            [],
        )

    def test_excluded_is_excluded_from_ranking(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
            statistics_status=InspectionReport.StatisticsStatus.EXCLUDED,
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=8,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2026-08-10",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"],
            [],
        )

    def test_included_operational_enters_ranking(self):
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
            statistics_status=InspectionReport.StatisticsStatus.INCLUDED,
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=100,
            refusal=8,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2026-08-10",
                    "date_to": "2026-08-20",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["municipality"],
            "Niterói",
        )

    def test_mixed_period_sums_without_overlap(self):
        self._create_historical_row(
            reference_date=date(2026, 8, 9),
            team="A1",
            municipality=self.niteroi,
            operations_count=2,
            approach=40,
            refusal=4,
        )
        post_cut = self._create_report(
            team="A1",
            operation_date="2026-08-10",
        )
        self._create_operation(
            report=post_cut,
            city="Niterói",
            approach=60,
            refusal=6,
        )
        pre_cut = self._create_report(
            team="A1",
            operation_date="2026-08-09",
        )
        self._create_operation(
            report=pre_cut,
            city="Niterói",
            approach=999,
            refusal=999,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2026-08-09",
                    "date_to": "2026-08-10",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["operations"],
            3,
        )
        self.assertEqual(
            data["ranking"][0]["approach"],
            100,
        )
        self.assertEqual(
            data["ranking"][0]["alcohol_cases"],
            10,
        )

    def test_region_filter_limits_ranking(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            refusal=10,
        )
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.angra,
            operations_count=1,
            approach=100,
            refusal=20,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "region": "Metropolitana",
                }
            ).get_data()
        )

        self.assertEqual(
            len(data["ranking"]),
            1,
        )
        self.assertEqual(
            data["ranking"][0]["municipality"],
            "Niterói",
        )

    def test_team_filter_limits_ranking(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            refusal=10,
        )
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="B2",
            municipality=self.sao_goncalo,
            operations_count=1,
            approach=100,
            refusal=20,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "team": "A1",
                }
            ).get_data()
        )

        self.assertEqual(
            len(data["ranking"]),
            1,
        )
        self.assertEqual(
            data["ranking"][0]["municipality"],
            "Niterói",
        )

    def test_specific_municipality_returns_position_without_destroying_reference_ranking(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.rio,
            operations_count=1,
            approach=100,
            refusal=30,
        )
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            refusal=20,
        )
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.sao_goncalo,
            operations_count=1,
            approach=100,
            refusal=10,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "region": "Metropolitana",
                    "municipality": "Niterói",
                }
            ).get_data()
        )

        self.assertEqual(
            len(data["ranking"]),
            1,
        )
        self.assertEqual(
            data["ranking"][0]["municipality"],
            "Niterói",
        )
        self.assertEqual(
            data["ranking"][0]["position"],
            2,
        )
        self.assertEqual(
            data["ranking"][0]["total_municipalities"],
            3,
        )

    def test_indicator_fined(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            fined=25,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "fined",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["value"],
            25,
        )

    def test_indicator_cnh_collected(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            cnh_collected=7,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "cnh_collected",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["value"],
            7,
        )

    def test_indicator_towed(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            towed=3,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "towed",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["value"],
            3,
        )

    def test_indicator_refusal(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            refusal=6,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "refusal",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["value"],
            6,
        )

    def test_indicator_reconductor(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            reconductor=4,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "reconductor",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["value"],
            4,
        )

    def test_indicator_removal_resolutions(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            removal_resolutions=5,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "removal_resolutions",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["value"],
            5,
        )

    def test_indicator_criminal_occurrences(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            criminal_occurrences=2,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "criminal_occurrences",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["value"],
            2,
        )

    def test_indicator_arrests_means_evidence(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=100,
            arrests_means_evidence=9,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "arrests_means_evidence",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["value"],
            9,
        )

    def test_alcohol_percentage_is_recalculated(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=50,
            refusal=5,
        )
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=50,
            refusal=15,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2026-08-20",
                    "indicator": "alcohol_percentage",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["alcohol_cases"],
            20,
        )
        self.assertEqual(
            data["ranking"][0]["approach"],
            100,
        )
        self.assertAlmostEqual(
            data["ranking"][0]["value"],
            20.0,
        )

    def test_fined_per_100_approaches_is_recalculated(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=20,
            fined=10,
        )
        report = self._create_report(
            team="A1",
            operation_date="2026-08-15",
        )
        self._create_operation(
            report=report,
            city="Niterói",
            approach=80,
            fined=20,
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2026-08-20",
                    "indicator": "fined_per_100_approaches",
                }
            ).get_data()
        )

        self.assertEqual(
            data["ranking"][0]["fined"],
            30,
        )
        self.assertEqual(
            data["ranking"][0]["approach"],
            100,
        )
        self.assertAlmostEqual(
            data["ranking"][0]["value"],
            30.0,
        )

    def test_relative_indicators_return_zero_when_approach_is_zero(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=self.niteroi,
            operations_count=1,
            approach=0,
            refusal=5,
            fined=7,
        )

        alcohol_data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "alcohol_percentage",
                }
            ).get_data()
        )
        fined_data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                    "indicator": "fined_per_100_approaches",
                }
            ).get_data()
        )

        self.assertEqual(
            alcohol_data["ranking"][0]["value"],
            0,
        )
        self.assertEqual(
            fined_data["ranking"][0]["value"],
            0,
        )

    def test_unclassified_are_excluded_from_ranking(self):
        self._create_historical_row(
            reference_date=date(2024, 1, 1),
            team="A1",
            municipality=None,
            operations_count=5,
            approach=50,
            refusal=5,
            source_city="NÃO CLASSIFICADO",
            normalized_city="NAO CLASSIFICADO",
        )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                }
            ).get_data()
        )

        self.assertEqual(
            data["summary"]["municipalities_considered"],
            0,
        )
        self.assertEqual(
            data["ranking"],
            [],
        )

    def test_default_limit_is_10(self):
        for index in range(11):
            self._create_historical_row(
                reference_date=date(2024, 1, 1),
                team="A1",
                municipality=self.niteroi if index == 0 else self.sao_goncalo if index == 1 else self.angra if index == 2 else self.rio if index == 3 else self.duque_de_caxias if index == 4 else self.comendador_levy,
                operations_count=1,
                approach=100 + index,
                refusal=index,
                source_city=None,
            )

        data = (
            InspectionTerritorialRankingService(
                {
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-31",
                }
            ).get_data()
        )

        self.assertEqual(
            data["meta"]["limit"],
            10,
        )

    def test_max_limit_is_50(self):
        data = (
            InspectionTerritorialRankingService(
                {
                    "limit": 999,
                }
            ).get_data()
        )

        self.assertEqual(
            data["meta"]["limit"],
            50,
        )


class InspectionTerritorialRankingEndpointTestCase(
    TestCase
):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create(
            email="ranking@example.com",
            password="secret123",
            role=user_model.Role.ADMIN,
        )
        self.client = APIClient()
        self.client.force_authenticate(
            user=self.user
        )
        self.url = reverse(
            "inspection-territorial-ranking"
        )

    def test_endpoint_contract(self):
        response = self.client.get(
            self.url,
            {
                "date_from": "2022-10-03",
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
                "summary",
                "ranking",
                "meta",
            },
        )
