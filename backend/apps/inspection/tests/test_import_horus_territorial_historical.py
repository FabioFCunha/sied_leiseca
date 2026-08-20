from datetime import date
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.inspection.management.commands.import_horus_territorial_historical import (
    HISTORICAL_DATE_FROM,
    HISTORICAL_DATE_TO,
)
from apps.inspection.models import (
    InspectionHistoricalTerritorialStatistic,
    InspectionMunicipality,
)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.connection.executed_sql.append((" ".join(sql.split()), params))
        self._rows = list(self.connection.rows)

    def fetchall(self):
        return list(self._rows)


class FakeConnection:
    def __init__(self, rows):
        self.rows = list(rows)
        self.executed_sql = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


class ImportHorusTerritorialHistoricalTests(TestCase):
    def _row(
        self,
        *,
        section_id,
        operation_id,
        operation_date,
        team="A1",
        source_city="",
        address_operation="",
        has_rain=0,
        approach=0,
        reconductor=0,
        refusal=0,
        fined=0,
        towed=0,
        cnh_collected=0,
        four_ml=0,
        thirtythree_ml=0,
        thirtyfour_ml=0,
        passive_tests_performed=0,
        removal_resolutions=0,
        arrests_means_evidence=0,
        art307=0,
        criminal_occurrences=0,
        driving_canceled_license=0,
    ):
        return (
            section_id,
            operation_id,
            operation_date,
            team,
            source_city,
            address_operation,
            has_rain,
            approach,
            reconductor,
            refusal,
            fined,
            towed,
            cnh_collected,
            four_ml,
            thirtythree_ml,
            thirtyfour_ml,
            passive_tests_performed,
            removal_resolutions,
            arrests_means_evidence,
            art307,
            criminal_occurrences,
            driving_canceled_license,
        )

    def _run_command(self, rows):
        connection = FakeConnection(rows)

        with patch(
            "apps.inspection.management.commands.import_horus_territorial_historical.HorusInspectionSyncer.connect_horus",
            return_value=connection,
        ):
            call_command("import_horus_territorial_historical")

        return connection

    def test_import_uses_historical_date_window_and_quoted_address_operation(self):
        connection = self._run_command([])

        self.assertEqual(len(connection.executed_sql), 1)
        sql, params = connection.executed_sql[0]
        self.assertIn('st."addressOperation"', sql)
        self.assertEqual(
            params,
            (HISTORICAL_DATE_FROM, HISTORICAL_DATE_TO),
        )
        self.assertTrue(connection.closed)

    def test_prefix_rules_apply_without_city_fallback_and_cover_all_years(self):
        rows = [
            self._row(
                section_id="s2022",
                operation_id="o2022",
                operation_date=date(2022, 10, 3),
                team="A1",
                source_city="",
                address_operation="Base 0.11 Avenida Brasil",
                approach=10,
                fined=4,
                refusal=1,
            ),
            self._row(
                section_id="s2023",
                operation_id="o2023",
                operation_date=date(2023, 5, 20),
                team="A2",
                source_city="",
                address_operation="Posto 4.07 Trevo",
                approach=20,
                fined=8,
                refusal=2,
            ),
            self._row(
                section_id="s2024",
                operation_id="o2024",
                operation_date=date(2024, 7, 11),
                team="A3",
                source_city="Cidade Divergente",
                address_operation="Rota 5.01 Praia",
                approach=30,
                fined=12,
                refusal=3,
            ),
            self._row(
                section_id="s2025",
                operation_id="o2025a",
                operation_date=date(2025, 3, 9),
                team="B1",
                source_city="",
                address_operation="Trecho 11.07 BR",
                has_rain=1,
                approach=40,
                fined=16,
                refusal=4,
            ),
            self._row(
                section_id="s2025",
                operation_id="o2025b",
                operation_date=date(2025, 3, 9),
                team="B1",
                source_city="",
                address_operation="Sem prefixo",
                has_rain=1,
                approach=50,
                fined=20,
                refusal=5,
            ),
            self._row(
                section_id="s2026",
                operation_id="o2026",
                operation_date=date(2026, 8, 9),
                team="C1",
                source_city="",
                address_operation="Fiscalizacao 8.05",
                approach=60,
                fined=24,
                refusal=6,
            ),
        ]

        self._run_command(rows)

        imported = list(
            InspectionHistoricalTerritorialStatistic.objects.order_by(
                "reference_date",
                "team",
            )
        )
        self.assertEqual(len(imported), 5)

        by_date = {
            item.reference_date: item
            for item in imported
        }

        self.assertEqual(
            by_date[date(2022, 10, 3)].municipality.name,
            "Rio de Janeiro",
        )
        self.assertEqual(
            by_date[date(2023, 5, 20)].municipality.name,
            "Magé",
        )

        row_2024 = by_date[date(2024, 7, 11)]
        self.assertEqual(row_2024.municipality.name, "Niterói")
        self.assertEqual(row_2024.source_city, "Cidade Divergente")
        self.assertEqual(
            row_2024.normalized_city,
            "CIDADE DIVERGENTE",
        )

        row_2025 = by_date[date(2025, 3, 9)]
        self.assertEqual(row_2025.municipality.name, "Angra dos Reis")
        self.assertEqual(row_2025.operations_count, 2)
        self.assertEqual(row_2025.reports_count, 1)
        self.assertEqual(row_2025.approach, 90)
        self.assertEqual(row_2025.fined, 36)
        self.assertEqual(row_2025.refusal, 9)
        self.assertEqual(row_2025.rain, 1)

        self.assertEqual(
            by_date[date(2026, 8, 9)].municipality.name,
            "Cachoeiras de Macacu",
        )

    def test_fallback_exact_city_classifies_when_no_other_evidence(self):
        rows = [
            self._row(
                section_id="s1",
                operation_id="o1",
                operation_date=date(2025, 1, 1),
                source_city="Niterói",
                address_operation="Sem codigo",
                approach=10,
                fined=5,
                refusal=2,
            )
        ]

        self._run_command(rows)

        row = InspectionHistoricalTerritorialStatistic.objects.get()
        self.assertEqual(row.source_city, "Niterói")
        self.assertEqual(row.normalized_city, "NITEROI")
        self.assertEqual(row.municipality.name, "Niterói")
        self.assertEqual(row.region.name, "Metropolitana")

    def test_prefix_priority_wins_over_city(self):
        rows = [
            self._row(
                section_id="s1",
                operation_id="o1",
                operation_date=date(2025, 1, 1),
                source_city="Niterói",
                address_operation="Trecho 4.07",
                approach=10,
            )
        ]

        self._run_command(rows)

        row = InspectionHistoricalTerritorialStatistic.objects.get()
        self.assertEqual(row.municipality.name, "Magé")

    def test_unique_prefix_inheritance_wins_over_city(self):
        rows = [
            self._row(
                section_id="s1",
                operation_id="o1",
                operation_date=date(2025, 1, 1),
                source_city="Niterói",
                address_operation="Trecho 5.01",
                approach=10,
            ),
            self._row(
                section_id="s1",
                operation_id="o2",
                operation_date=date(2025, 1, 1),
                source_city="Magé",
                address_operation="Sem codigo",
                approach=20,
            ),
        ]

        self._run_command(rows)

        inherited = (
            InspectionHistoricalTerritorialStatistic.objects
            .filter(source_city="Magé")
            .get()
        )
        self.assertEqual(inherited.municipality.name, "Niterói")

    def test_city_conflict_with_multiple_prefixes_stays_unclassified(self):
        rows = [
            self._row(
                section_id="s1",
                operation_id="o1",
                operation_date=date(2025, 1, 1),
                address_operation="Trecho 5.01",
                approach=10,
            ),
            self._row(
                section_id="s1",
                operation_id="o2",
                operation_date=date(2025, 1, 1),
                address_operation="Trecho 4.07",
                approach=20,
            ),
            self._row(
                section_id="s1",
                operation_id="o3",
                operation_date=date(2025, 1, 1),
                source_city="Porciúncula",
                address_operation="Sem codigo",
                approach=30,
            ),
        ]

        self._run_command(rows)

        row = (
            InspectionHistoricalTerritorialStatistic.objects
            .filter(source_city="Porciúncula")
            .get()
        )
        self.assertIsNone(row.municipality)
        self.assertIsNone(row.region)

    def test_multiple_valid_prefixes_block_inheritance(self):
        rows = [
            self._row(
                section_id="s1",
                operation_id="o1",
                operation_date=date(2025, 5, 1),
                address_operation="Trecho 5.01",
                approach=10,
            ),
            self._row(
                section_id="s1",
                operation_id="o2",
                operation_date=date(2025, 5, 1),
                address_operation="Trecho 4.07",
                approach=20,
            ),
            self._row(
                section_id="s1",
                operation_id="o3",
                operation_date=date(2025, 5, 1),
                address_operation="Sem prefixo",
                approach=30,
                fined=12,
                refusal=6,
            ),
        ]

        self._run_command(rows)

        unclassified = (
            InspectionHistoricalTerritorialStatistic.objects.filter(
                municipality__isnull=True
            ).get()
        )
        self.assertEqual(unclassified.operations_count, 1)
        self.assertEqual(unclassified.approach, 30)
        self.assertEqual(unclassified.fined, 12)
        self.assertEqual(unclassified.refusal, 6)

    def test_unknown_prefix_stays_unclassified_without_inheritance(self):
        rows = [
            self._row(
                section_id="s1",
                operation_id="o1",
                operation_date=date(2024, 1, 1),
                address_operation="Trecho 4.07",
                approach=10,
            ),
            self._row(
                section_id="s1",
                operation_id="o2",
                operation_date=date(2024, 1, 1),
                address_operation="Trecho 11.16",
                approach=20,
                fined=9,
                refusal=3,
            ),
        ]

        self._run_command(rows)

        unknown_row = (
            InspectionHistoricalTerritorialStatistic.objects.filter(
                municipality__isnull=True
            ).get()
        )
        self.assertEqual(unknown_row.operations_count, 1)
        self.assertEqual(unknown_row.approach, 20)
        self.assertEqual(unknown_row.fined, 9)
        self.assertEqual(unknown_row.refusal, 3)

    def test_no_prefix_and_no_valid_inheritance_stays_unclassified(self):
        rows = [
            self._row(
                section_id="s1",
                operation_id="o1",
                operation_date=date(2023, 1, 1),
                address_operation="Sem prefixo",
                approach=15,
                fined=7,
                refusal=2,
            )
        ]

        self._run_command(rows)

        row = InspectionHistoricalTerritorialStatistic.objects.get()
        self.assertIsNone(row.municipality)
        self.assertIsNone(row.region)
        self.assertEqual(row.operations_count, 1)
        self.assertEqual(row.approach, 15)
        self.assertEqual(row.fined, 7)
        self.assertEqual(row.refusal, 2)

    def test_unknown_city_without_other_evidence_stays_unclassified(self):
        rows = [
            self._row(
                section_id="s1",
                operation_id="o1",
                operation_date=date(2025, 1, 1),
                source_city="Cidade Inventada",
                address_operation="Sem codigo",
                approach=15,
            )
        ]

        self._run_command(rows)

        row = InspectionHistoricalTerritorialStatistic.objects.get()
        self.assertIsNone(row.municipality)
        self.assertIsNone(row.region)

    def test_porciuncula_without_address_operation_classifies_by_city_when_safe(self):
        rows = [
            self._row(
                section_id="s22",
                operation_id="o22a",
                operation_date=date(2025, 8, 22),
                team="C3",
                source_city="Porciúncula",
                address_operation="",
                approach=50,
                reconductor=14,
                fined=25,
                refusal=11,
                four_ml=37,
                thirtythree_ml=2,
            ),
            self._row(
                section_id="s22",
                operation_id="o22b",
                operation_date=date(2025, 8, 22),
                team="C3",
                source_city="Porciúncula",
                address_operation="",
                approach=4,
                reconductor=1,
                fined=2,
                refusal=1,
                four_ml=3,
            ),
            self._row(
                section_id="s23",
                operation_id="o23",
                operation_date=date(2025, 8, 23),
                team="C3",
                source_city="Porciúncula",
                address_operation="",
                approach=115,
                reconductor=15,
                fined=22,
                refusal=16,
                four_ml=99,
                arrests_means_evidence=1,
            ),
        ]

        self._run_command(rows)

        porciuncula = InspectionMunicipality.objects.get(
            name="Porciúncula"
        )
        rows = list(
            InspectionHistoricalTerritorialStatistic.objects
            .filter(municipality=porciuncula)
            .order_by("reference_date")
        )

        self.assertEqual(len(rows), 2)

        row_22, row_23 = rows
        self.assertEqual(row_22.reference_date, date(2025, 8, 22))
        self.assertEqual(row_22.operations_count, 2)
        self.assertEqual(row_22.approach, 54)
        self.assertEqual(row_22.reconductor, 15)
        self.assertEqual(row_22.fined, 27)

        self.assertEqual(row_23.reference_date, date(2025, 8, 23))
        self.assertEqual(row_23.operations_count, 1)
        self.assertEqual(row_23.approach, 115)
        self.assertEqual(row_23.reconductor, 15)
        self.assertEqual(row_23.fined, 22)
