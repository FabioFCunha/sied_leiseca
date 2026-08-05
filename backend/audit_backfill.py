import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.schedules.models import EducationReport, EducationAction, Agenda, ActionType
from apps.statistics.models import ConsolidatedStatistic
from apps.statistics.services import generate_statistics_for_report
from django.utils import timezone

# Criar dados de teste (relatório COM material e SEM material)

# 1. Report COM material
# 1. Report COM material
# 1. Report COM material
# 1. Report COM material
# 1. Report COM material
agenda1 = Agenda.objects.create(
    title="Teste Palestra Escola",
    requester_entity_type="2", # Simulando ID Horus para Escola
    action_type="Palestra Escola",
    status="APPROVED",
    date=timezone.now().date()
)

report1 = EducationReport.objects.create(
    agenda=agenda1,
    operation_date=timezone.now().date(),
    status="APPROVED",
    approximate_public=100,
    distribution_materials_distributed="Certificado | 50\nRevistinha Soprinho - 200\nNaoExiste - 10"
)

action1 = EducationAction.objects.create(
    report=report1,
    agenda=agenda1,
    type_action="Palestra"
)

# 2. Report SEM material
agenda2 = Agenda.objects.create(
    title="Teste Ação Praia",
    requester_entity_type="Praia", # Texto direto (SIED)
    action_type="Ação de Rua",
    status="APPROVED",
    date=timezone.now().date()
)

report2 = EducationReport.objects.create(
    agenda=agenda2,
    operation_date=timezone.now().date(),
    status="APPROVED",
    approximate_public=50,
    distribution_materials_distributed="Certificado | 0" # Nenhum material
)

action2 = EducationAction.objects.create(
    report=report2,
    agenda=agenda2,
    type_action="Ação"
)

reports = [report1, report2]

for r in reports:
    print(f"\n--- TESTANDO REPORT ID {r.id} ---")
    print("--- 1a EXECUCAO ---")
    generate_statistics_for_report(r)
    count1 = ConsolidatedStatistic.objects.filter(traceability_id=f'report_{r.id}', status='ACTIVE').count()
    print(f"Stats ativas: {count1}")
    
    print("--- 2a EXECUCAO (Idempotência) ---")
    generate_statistics_for_report(r)
    count2 = ConsolidatedStatistic.objects.filter(traceability_id=f'report_{r.id}', status='ACTIVE').count()
    print(f"Stats ativas após 2a exec: {count2} (deve ser igual a {count1})")
    
    print("Indicadores gerados:")
    for s in ConsolidatedStatistic.objects.filter(traceability_id=f'report_{r.id}', status='ACTIVE'):
        print(f" -> {s.indicator_type} | {s.category_action_type} | {s.category_entity_type} = {s.value}")
