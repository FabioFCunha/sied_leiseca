import datetime
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.inspection.models import (
    InspectionHistoricalStatistic,
    InspectionHistoricalTerritorialStatistic,
    InspectionReport,
    InspectionStatistic,
    InspectionReportOperation,
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalImportBatch
)
from apps.inspection.territorial import resolve_territory

class TerritorialFilterTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.user, _ = get_user_model().objects.get_or_create(
            email="statstester@example.com",
            defaults={
                "password": "secretpassword",
                "role": get_user_model().Role.ADMIN
            }
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("inspection-statistics-dashboard")

        batch = InspectionHistoricalImportBatch.objects.create(
            source_file_sha256="test",
            source_file_name="test.json",
            source_file_size=100,
            started_at=datetime.datetime.now()
        )
        # Create unclassified data
        InspectionHistoricalTerritorialStatistic.objects.create(
            reference_date=datetime.date(2023, 1, 1),
            team="A1",
            source_city="",
            normalized_city="",
            reports_count=1,
            operations_count=5,
            approach=10
        )
        from apps.inspection.models import InspectionRegion, InspectionMunicipality
        reg_metro = InspectionRegion.objects.get(name="Metropolitana")
        mun_rj = InspectionMunicipality.objects.get(name="Rio de Janeiro")
        
        reg_costa = InspectionRegion.objects.get(name="Costa Verde")
        mun_manga = InspectionMunicipality.objects.get(name="Mangaratiba")
        
        # Create Metropolitana data
        InspectionHistoricalTerritorialStatistic.objects.create(
            reference_date=datetime.date(2023, 1, 1),
            team="A1",
            source_city="Rio de Janeiro",
            normalized_city="RIO DE JANEIRO",
            region=reg_metro,
            municipality=mun_rj,
            reports_count=1,
            operations_count=10,
            approach=50,
            rain=1
        )
        # Costa Verde
        InspectionHistoricalTerritorialStatistic.objects.create(
            reference_date=datetime.date(2023, 1, 1),
            team="B1",
            source_city="Mangaratiba",
            normalized_city="MANGARATIBA",
            region=reg_costa,
            municipality=mun_manga,
            reports_count=1,
            operations_count=2,
            approach=5
        )
        
        # Operational data > 10/08/2026
        report = InspectionReport.objects.create(
            team="A1",
            operation_date=datetime.date(2026, 8, 15),
            source_id="11111111-1111-1111-1111-111111111111",
            source_created_at=datetime.datetime.now(),
            source_updated_at=datetime.datetime.now(),
            synced_at=datetime.datetime.now()
        )
        InspectionStatistic.objects.create(
            report=report,
            source_report_id=report.id,
            operation_date=report.operation_date,
            team=report.team,
            snapshot_source_updated_at=datetime.datetime.now(),
            operations_count=1,
            approach=100
        )
        InspectionReportOperation.objects.create(
            report=report,
            source_id="00000000-0000-0000-0000-000000000000",
            source_created_at=datetime.datetime.now(),
            source_updated_at=datetime.datetime.now(),
            city="Rio de Janeiro",
            approach=100
        )

    def test_sem_region(self):
        # 1. Sem region: dashboard idêntico ao comportamento atual.
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_regiao_valida(self):
        # 2. Região válida: somente sua produção.
        from apps.inspection.models import InspectionHistoricalTerritorialStatistic
        res = self.client.get(self.url, {"region": "Metropolitana"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["summary"]["approach"], 150) # 50 from historical + 100 from operational

    def test_regiao_invalida(self):
        # 3. Região inválida: HTTP 400.
        res = self.client.get(self.url, {"region": "InvalidRegion"})
        self.assertEqual(res.status_code, 400)
        
    def test_regiao_sem_registros(self):
        # 4. Região sem registros: estrutura válida com zeros.
        res = self.client.get(self.url, {"region": "Serrana"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["summary"]["approach"], 0)

    def test_team_and_region(self):
        # 5. team + region
        res = self.client.get(self.url, {"region": "Costa Verde", "team": "B1"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["summary"]["approach"], 5)

    def test_periodo_anterior_2022(self):
        # 4. Filtro em período que não tem territorialidade retorna zeros (ou None).
        res = self.client.get(self.url, {"region": "Metropolitana", "date_from": "2020-01-01", "date_to": "2021-12-31"})
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data["summary"]["approach"])

    def test_periodo_atravessando_2022(self):
        # 7. período atravessando 03/10/2022
        res = self.client.get(self.url, {"region": "Metropolitana", "date_from": "2020-01-01", "date_to": "2023-12-31"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["summary"]["approach"], 50)

    def test_periodo_atravessando_2026(self):
        # 8. período atravessando 10/08/2026
        res = self.client.get(self.url, {"region": "Metropolitana", "date_from": "2026-01-01", "date_to": "2026-12-31"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["summary"]["approach"], 100) # Only operational is in 2026 in this DB
        
    def test_municipio_nao_classificado(self):
        # 11. município não classificado: não entra em região conhecida.
        res = self.client.get(self.url, {"region": "Metropolitana"})
        self.assertEqual(res.data["summary"]["approach"], 150) # The unclassified record with 10 approach should NOT be included

    def test_costa_verde(self):
        # 12. Costa Verde
        res = self.client.get(self.url, {"region": "Costa Verde"})
        self.assertEqual(res.data["summary"]["approach"], 5)

    def test_chuva_acompanha_region(self):
        # 18. chuva acompanha region
        res = self.client.get(self.url, {"region": "Metropolitana"})
        self.assertIsNone(res.data["occurrences"]["rain"])

    def test_limpar_region(self):
        # 20. limpar region restaura exatamente o resultado estadual.
        res_with = self.client.get(self.url, {"region": "Metropolitana"})
        res_without = self.client.get(self.url)
        self.assertNotEqual(res_with.data["summary"]["approach"], res_without.data["summary"]["approach"])
