import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from apps.statistics.models import ConsolidatedStatistic
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
user, created = User.objects.get_or_create(username='homolog', defaults={'email': 'homolog@test.com'})

c = Client(SERVER_NAME='localhost')
c.force_login(user)

print("="*50)
print("1. VALIDAÇÃO DA API DE RESUMO")
print("Cenário A: 2011 até 2025 (somente HISTORICAL_LEGACY)")
res = c.get('/api/statistics/summary/', {'date_from': '2011-01-01', 'date_to': '2025-12-31'})
if res.status_code == 200:
    data = res.json()
    print("Qtd de agregados:", len(data))
    if len(data) > 0:
        print(data[0])
else:
    print(res.status_code, res.content)

print("\nCenário B: 09/07/2026 até 31/12/2026 (somente SIED_OPERATIONAL)")
res = c.get('/api/statistics/summary/', {'date_from': '2026-07-09', 'date_to': '2026-12-31'})
if res.status_code == 200:
    data = res.json()
    print("Qtd de agregados no periodo SIED:", len(data))
else:
    print(res.status_code, res.content)

print("\nCenário C: Período completo de 2026 (Divisão da data de corte)")
res = c.get('/api/statistics/summary/', {'date_from': '2026-01-01', 'date_to': '2026-12-31'})
if res.status_code == 200:
    data = res.json()
    print("Qtd de agregados em 2026:", len(data))
    if len(data) > 0:
        print(data[0])

print("\n" + "="*50)
print("2. VALIDAÇÃO DA COMPARAÇÃO PERCENTUAL")
print("Cenário A: Comparando 2025 vs 2024 (crescimento normal / redução)")
res = c.get('/api/statistics/comparison/', {'date_from': '2025-01-01', 'date_to': '2025-12-31', 'prev_date_from': '2024-01-01', 'prev_date_to': '2024-12-31'})
if res.status_code == 200:
    data = res.json()
    print("Variações calculadas:")
    for k, v in list(data['variations'].items())[:3]:
        print(f" {k}: {v}")
    print("Variações Macro:")
    for k, v in data['macro_variations'].items():
        print(f" {k}: {v}")

print("\nCenário B: Divisão por Zero (NEW_DATA / NO_CHANGE)")
res = c.get('/api/statistics/comparison/', {'date_from': '2025-01-01', 'date_to': '2025-12-31', 'prev_date_from': '2030-01-01', 'prev_date_to': '2030-12-31'})
if res.status_code == 200:
    data2 = res.json()
    print("Simulação Anterior=0 e Atual>0 (NEW_DATA):")
    for k, v in list(data2['variations'].items())[:1]:
        print(f" {k}: {v}")

res = c.get('/api/statistics/comparison/', {'date_from': '2030-01-01', 'date_to': '2030-12-31', 'prev_date_from': '2031-01-01', 'prev_date_to': '2031-12-31'})
if res.status_code == 200:
    data3 = res.json()
    print("Simulação Anterior=0 e Atual=0 (NO_CHANGE):")
    print(data3['macro_variations'])

print("\n" + "="*50)
print("3. VALIDAÇÃO DA SÉRIE HISTÓRICA")
res = c.get('/api/statistics/historical-series/')
if res.status_code == 200:
    data = res.json()
    anos = sorted(list(set([item['year'] for item in data])))
    print(f"Série Histórica abrange os anos: {anos}")

print("\n" + "="*50)
print("5. VALIDAÇÃO DE RASTREABILIDADE (SIMULANDO NOVO RELATÓRIO)")
from apps.statistics.services import generate_statistics_for_report
class MockReport:
    def __init__(self, id, status, audience_total):
        self.id = id
        self.status = status
        self.audience_total = audience_total
        self.created_at = timezone.now()

fake_report = MockReport(id=9999, status='APPROVED', audience_total=450)
generate_statistics_for_report(fake_report)
stat = ConsolidatedStatistic.objects.get(traceability_id='report_9999')
print(f"Rastreabilidade OK!")
print(f"ID Rastreável: {stat.traceability_id}")
print(f"Valor: {stat.value}")
print(f"Metodologia: {stat.methodology}")
print("Removendo relatório mock...")
stat.delete()
user.delete()
