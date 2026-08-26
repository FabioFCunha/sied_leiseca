from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from openpyxl import Workbook

from apps.inspection.management.commands.replace_inspection_historical import Command
from apps.inspection.models import (
    InspectionHistoricalImportBatch, InspectionHistoricalStatistic,
    InspectionHistoricalTerritorialStatistic, InspectionMunicipality, InspectionRegion,
)


class ReplaceInspectionHistoricalTests(TestCase):
    headers = ["Ano", "Data", "Equipe", "Município", "Apto para importação", "Pendências", "Alcoolemia calculada", "Aba de origem", "Linha de origem", "Ajustes realizados", "Abordados", "Multados", "Rebocados", "CNH recolhidas", "Testes com biqueira", "Recondutores", "Recusas", "De 0,0 a 0,10", "De 0,11 a 0,29", "Mais de 0,30", "Presos por outros motivos", "Total de ações"]

    def setUp(self):
        self.municipality = InspectionMunicipality.objects.get(normalized_name="RIO DE JANEIRO")
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def rows(self):
        return [
            [2023, date(2023, 1, 1), "a1", "Rio de Janeiro", True, "", 3, "Origem", 10, "ajuste", 10, 2, 1, 1, 8, 2, 1, 1, 1, 1, 0, 2],
            [2023, date(2023, 1, 2), "a2", "Rio de Janeiro", True, "", 0, "Origem", 11, "", 20, 3, 2, 0, 9, 3, 0, 0, 0, 0, 0, 3],
        ]

    def control(self, rows):
        values = [0] * 10
        for row in rows:
            values[0] += 1
            for index, column in enumerate([21, 10, 11, 12, 13, 14, 15, 16, 6], 1): values[index] += row[column]
        return {2023: tuple(values)}

    def workbook(self, rows=None):
        path = Path(self.tmp.name) / "base.xlsx"; wb = Workbook(); ws = wb.active; ws.title = "Base Importacao"; ws.append(self.headers)
        for row in rows or self.rows(): ws.append(row)
        wb.create_sheet("Resumo"); wb.save(path); return str(path)

    def command(self, *args):
        rows = self.rows()
        with patch.object(Command, "expected_rows", 2), patch.object(Command, "control_totals", self.control(rows)):
            return call_command("replace_inspection_historical", *args)

    def test_mode_guards_and_dry_run_do_not_write(self):
        path = self.workbook(); before = InspectionHistoricalImportBatch.objects.count()
        self.command("--file", path, "--dry-run")
        self.assertEqual(InspectionHistoricalImportBatch.objects.count(), before)
        for args in [("--file", path), ("--file", path, "--apply"), ("--file", path, "--apply", "--confirm", "wrong"), ("--file", path, "--dry-run", "--apply", "--confirm", "REPLACE-2023-2026")]:
            with self.assertRaises(CommandError): self.command(*args)

    def test_validation_rejections(self):
        cases = {
            "wrong_count": self.rows()[:1],
            "duplicate": [self.rows()[0], self.rows()[0]],
            "outside_date": [[*self.rows()[0][:1], date(2026, 8, 4), *self.rows()[0][2:]], self.rows()[1]],
            "empty_team": [[2023, date(2023,1,1), "", *self.rows()[0][3:]], self.rows()[1]],
            "empty_city": [[2023, date(2023,1,1), "a1", "", *self.rows()[0][4:]], self.rows()[1]],
            "unknown_city": [[2023, date(2023,1,1), "a1", "Desconhecido", *self.rows()[0][4:]], self.rows()[1]],
            "not_apt": [[2023, date(2023,1,1), "a1", "Rio de Janeiro", False, *self.rows()[0][5:]], self.rows()[1]],
            "pending": [[2023, date(2023,1,1), "a1", "Rio de Janeiro", True, "x", *self.rows()[0][6:]], self.rows()[1]],
            "negative": [[*self.rows()[0][:10], -1, *self.rows()[0][11:]], self.rows()[1]],
            "alcohol": [[*self.rows()[0][:6], 99, *self.rows()[0][7:]], self.rows()[1]],
        }
        for name, rows in cases.items():
            with self.subTest(name=name), self.assertRaises(CommandError): self.command("--file", self.workbook(rows), "--dry-run")

    def test_apply_replaces_only_authorized_rows_and_rolls_back(self):
        batch = InspectionHistoricalImportBatch.objects.create(source_file_name="old", source_file_sha256="a" * 64, source_type="DAILY", taxonomy_era="ERA_C", source_file_size=1, status="COMPLETED", started_at="2026-01-01T00:00Z")
        target = InspectionHistoricalStatistic.objects.create(reference_date=date(2023,1,1), reference_year=2023, reference_month=1, team="OLD", source_team_label="OLD", source_type="DAILY", taxonomy_era="ERA_C", source_sheet="x", source_row=1, import_batch=batch)
        preserved = InspectionHistoricalStatistic.objects.create(reference_date=date(2026,8,4), reference_year=2026, reference_month=8, team="KEEP", source_team_label="KEEP", source_type="DAILY", taxonomy_era="ERA_C", source_sheet="x", source_row=2, import_batch=batch)
        legacy = InspectionHistoricalStatistic.objects.create(reference_date=date(2023,1,1), reference_year=2023, reference_month=1, team="LEGACY", source_team_label="LEGACY", source_type="LEGACY", taxonomy_era="ERA_A", source_sheet="x", source_row=3, import_batch=batch, is_validation_only=True)
        InspectionHistoricalTerritorialStatistic.objects.create(reference_date=date(2023,1,1), team="OLD", reports_count=1)
        outside = InspectionHistoricalTerritorialStatistic.objects.create(reference_date=date(2026,8,4), team="KEEP", reports_count=1)
        self.command("--file", self.workbook(), "--apply", "--confirm", "REPLACE-2023-2026")
        self.assertFalse(InspectionHistoricalStatistic.objects.filter(pk=target.pk).exists())
        self.assertTrue(InspectionHistoricalStatistic.objects.filter(pk=preserved.pk).exists()); self.assertTrue(InspectionHistoricalStatistic.objects.filter(pk=legacy.pk).exists())
        self.assertTrue(InspectionHistoricalTerritorialStatistic.objects.filter(pk=outside.pk).exists())
        self.assertEqual(InspectionHistoricalStatistic.objects.filter(reference_date__range=(date(2023,1,1), date(2026,8,3)), source_type="DAILY", taxonomy_era="ERA_C", is_validation_only=False).count(), 2)
        batch = InspectionHistoricalImportBatch.objects.latest("started_at")
        self.assertEqual(batch.status, "COMPLETED"); self.assertEqual(batch.rows_imported, 2)
        row = InspectionHistoricalStatistic.objects.get(team="A1")
        self.assertEqual((row.source_sheet, row.source_row, row.source_workbook_label), ("Origem", 10, "base.xlsx")); self.assertIn("ajuste", row.notes)
        territory = InspectionHistoricalTerritorialStatistic.objects.get(team="a1")
        self.assertEqual((territory.municipality, territory.region), (self.municipality, self.municipality.region))
