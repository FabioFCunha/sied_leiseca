from rest_framework.test import APIClient
import uuid
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import datetime
from apps.accounts.models import User
from apps.inspection.models import (
    InspectionHistoricalStatistic,
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionReport,
    InspectionReportOperation,
    InspectionStatistic,
    InspectionHistoricalImportBatch
)

class PartialDailyCoverageTests(APITestCase):
    def setUp(self):
        self.url = reverse("inspection-statistics-dashboard")
        from django.contrib.auth import get_user_model
        self.user, _ = get_user_model().objects.get_or_create(
            email="statstester@example.com",
            defaults={
                "password": "secretpassword",
                "role": get_user_model().Role.ADMIN
            }
        )
        self.client.force_authenticate(user=self.user)
        self.batch = InspectionHistoricalImportBatch.objects.create(
            source_type=HistoricalSourceType.DAILY,
            source_file_name="dummy.xlsx",
            source_file_size=1024,
            started_at=datetime.datetime.now(),
            status="COMPLETED"
        )
        def create_stat(**kwargs):
            kwargs.setdefault("source_sheet", "dummy")
            if not hasattr(self, "row_counter"): self.row_counter = 1
            self.row_counter += 1
            kwargs.setdefault("source_row", self.row_counter)
            kwargs.setdefault("import_batch", self.batch)
            InspectionHistoricalStatistic.objects.create(**kwargs)
        
        # 1. BEFORE DAILY (02/10/2022)
        create_stat(
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            is_validation_only=False,
            reference_date=datetime.date(2022, 10, 2),
            team="A1",
            historical_operations=10,
            historical_approached=100,
            fined=20,
            refusal=5,
            rain=0
        )
        
        # 2. EXACT START OF DAILY (03/10/2022)
        create_stat(
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            is_validation_only=False,
            reference_date=datetime.date(2022, 10, 3),
            team="A1",
            historical_operations=5,
            historical_approached=50,
            fined=10,
            refusal=2,
            rain=1
        )
        
        # 3. DURING DAILY (e.g. 2022-12-15)
        create_stat(
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            is_validation_only=False,
            reference_date=datetime.date(2022, 12, 15),
            team="A2",
            historical_operations=2,
            historical_approached=30,
            fined=5,
            refusal=1,
            rain=0
        )
        
        # 4. PARTIAL 2023
        create_stat(
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            is_validation_only=False,
            reference_date=datetime.date(2023, 5, 10),
            team="A1",
            historical_operations=3,
            historical_approached=40,
            fined=8,
            refusal=3,
            rain=1
        )
        
        # 5. PARTIAL 2024
        create_stat(
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            is_validation_only=False,
            reference_date=datetime.date(2024, 6, 20),
            team="A2",
            historical_operations=4,
            historical_approached=60,
            fined=12,
            refusal=4,
            rain=0
        )
        
        # 6. PARTIAL 2025
        create_stat(
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            is_validation_only=False,
            reference_date=datetime.date(2025, 7, 25),
            team="A1",
            historical_operations=1,
            historical_approached=20,
            fined=4,
            refusal=1,
            rain=1
        )
        
        # 7. DAILY UNTIL 09/08/2026
        create_stat(
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            is_validation_only=False,
            reference_date=datetime.date(2026, 8, 9),
            team="A1",
            historical_operations=2,
            historical_approached=35,
            fined=7,
            refusal=2,
            rain=0
        )
        
        # 8. OPERATIONAL FROM 10/08/2026
        report = InspectionReport.objects.create(
            operation_date=datetime.date(2026, 8, 10),
            team="A2",
            source_id=uuid.uuid4(),
            source_created_at=datetime.datetime.now(),
            source_updated_at=datetime.datetime.now(),
            synced_at=datetime.datetime.now(),
            statistics_classification={},
            status="APPROVED"
        )
        InspectionStatistic.objects.create(
            report=report,
            source_report_id=report.source_id,
            operation_date=report.operation_date,
            snapshot_source_updated_at=report.source_updated_at,
            operations_count=1,
            approach=45,
            fined=9,
            refusal=3
        )

    def test_2022_11_to_2023_03(self):
        # 1. 2022-11-01 a 2023-03-31 sem region
        res = self.client.get(self.url, {"date_from": "2022-11-01", "date_to": "2023-03-31"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["meta"]["has_data"])
        self.assertEqual(res.data["summary"]["operations"], 2) # from 2022-12-15
        self.assertEqual(res.data["summary"]["approach"], 30)
        self.assertEqual(res.data["summary"]["fined"], 5)
        self.assertEqual(res.data["summary"]["refusal"], 1)
        self.assertEqual(res.data["occurrences"]["rain"], 0)

    def test_partial_2023(self):
        # 2. Período parcial de 2023: usa DAILY/ERA_C
        res = self.client.get(self.url, {"date_from": "2023-05-01", "date_to": "2023-05-31"})
        self.assertTrue(res.data["meta"]["has_data"])
        self.assertEqual(res.data["summary"]["approach"], 40)

    def test_partial_2024(self):
        # 3. Período parcial de 2024: usa DAILY/ERA_C
        res = self.client.get(self.url, {"date_from": "2024-06-01", "date_to": "2024-06-30"})
        self.assertTrue(res.data["meta"]["has_data"])
        self.assertEqual(res.data["summary"]["approach"], 60)

    def test_partial_2025(self):
        # 4. Período parcial de 2025: usa DAILY/ERA_C
        res = self.client.get(self.url, {"date_from": "2025-07-01", "date_to": "2025-07-31"})
        self.assertTrue(res.data["meta"]["has_data"])
        self.assertEqual(res.data["summary"]["approach"], 20)

    def test_exact_start_daily(self):
        # 5. 03/10/2022: início exato da cobertura DAILY
        res = self.client.get(self.url, {"date_from": "2022-10-03", "date_to": "2022-10-03"})
        self.assertTrue(res.data["meta"]["has_data"])
        self.assertEqual(res.data["summary"]["approach"], 50)

    def test_before_daily_start(self):
        # 6. 02/10/2022: não utilizar DAILY antes do início
        res = self.client.get(self.url, {"date_from": "2022-10-02", "date_to": "2022-10-02"})
        self.assertFalse(res.data["meta"]["has_data"])
        self.assertIsNone(res.data["summary"]["approach"])

    def test_crossing_daily_start(self):
        # 7. Período atravessando 03/10/2022: não inventar granularidade anterior
        res = self.client.get(self.url, {"date_from": "2022-10-02", "date_to": "2022-10-04"})
        self.assertTrue(res.data["meta"]["has_data"])
        self.assertEqual(res.data["summary"]["approach"], 50) # only grabs from 10/03

    def test_crossing_operational_start(self):
        # 8. 01/08/2026 a 20/08/2026: DAILY até 09/08 + operacional desde 10/08
        res = self.client.get(self.url, {"date_from": "2026-08-01", "date_to": "2026-08-20"})
        self.assertTrue(res.data["meta"]["has_data"])
        # 35 from daily (09/08) + 45 from operational (10/08)
        self.assertEqual(res.data["summary"]["approach"], 80)

    def test_has_data_not_false_if_daily_exists(self):
        # 9. Se DAILY possuir produção: meta.has_data não pode ser false
        res = self.client.get(self.url, {"date_from": "2022-12-01", "date_to": "2022-12-31"})
        self.assertTrue(res.data["meta"]["has_data"])

    def test_team_and_partial_period(self):
        # 10. Filtro team + período parcial
        res = self.client.get(self.url, {"date_from": "2022-10-01", "date_to": "2022-12-31", "team": "A1"})
        # 2022-10-02 is ignored. 2022-10-03 (A1) = 50. 2022-12-15 (A2) is ignored.
        self.assertTrue(res.data["meta"]["has_data"])
        self.assertEqual(res.data["summary"]["approach"], 50)
