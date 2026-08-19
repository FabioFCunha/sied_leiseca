import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.inspection.models import (
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalImportBatch,
    InspectionHistoricalStatistic,
    InspectionHistoricalTerritorialStatistic,
)
from apps.inspection.territorial import resolve_territory
from apps.schedules.models import Sector


class RegionalMetricsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("inspection-statistics-dashboard")

        User = get_user_model()
        self.user = User.objects.create_user(
            email="regional.metrics@example.com",
            password="secret123",
            full_name="Regional Metrics Test",
            role=User.Role.VISITOR,
            sector=Sector.objects.create(name="OLS/CooAdm"),
        )
        self.client.force_authenticate(user=self.user)

        batch = InspectionHistoricalImportBatch.objects.create(
            source_file_sha256="test",
            source_file_name="test.json",
            source_file_size=100,
            started_at=timezone.now(),
        )

        InspectionHistoricalStatistic.objects.create(
            reference_date=datetime.date(2025, 9, 6),
            team="B4",
            source_type=HistoricalSourceType.DAILY,
            taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            is_validation_only=False,
            rain=1,
            historical_operations=10,
            historical_approached=100,
            source_sheet="Sheet1",
            source_row=1,
            import_batch=batch,
        )

        territory = resolve_territory("Rio de Janeiro")

        InspectionHistoricalTerritorialStatistic.objects.create(
            reference_date=datetime.date(2025, 9, 6),
            team="B4",
            source_city="",
            normalized_city="",
            operations_count=5,
            approach=50,
            rain=1,
        )

        InspectionHistoricalTerritorialStatistic.objects.create(
            reference_date=datetime.date(2025, 9, 6),
            team="B4",
            source_city="Rio de Janeiro",
            normalized_city="RIO DE JANEIRO",
            region_id=territory["region_id"],
            municipality_id=territory["municipality_id"],
            operations_count=5,
            approach=50,
            rain=1,
        )

    def test_region_vazio_mantem_estadual(self):
        """Sem region, período parcial dentro da cobertura DAILY/ERA_C
        deve retornar os indicadores do registro diário."""
        res = self.client.get(
            self.url,
            {
                "date_from": "2025-09-01",
                "date_to": "2025-09-30",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["occurrences"]["rain"], 1)
        self.assertEqual(res.data["summary"]["approach"], 100)

    def test_nao_classificados_nao_entram(self):
        res = self.client.get(
            self.url,
            {
                "region": "Metropolitana",
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["summary"]["approach"], 50)

    def test_rain_historico_regional_is_none(self):
        res = self.client.get(
            self.url,
            {
                "region": "Metropolitana",
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data["occurrences"]["rain"])

    def test_metadata_cobertura(self):
        res = self.client.get(
            self.url,
            {
                "region": "Metropolitana",
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            },
        )
        self.assertEqual(res.status_code, 200)

        cov = res.data["meta"]["territorial_coverage"]["approach"]
        self.assertEqual(cov["classified"], 50)
        self.assertEqual(cov["unclassified"], 50)
        self.assertEqual(cov["total"], 100)
        self.assertEqual(cov["classified_percentage"], 50.0)