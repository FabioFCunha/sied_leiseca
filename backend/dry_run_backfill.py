import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.schedules.models import EducationReport
from apps.statistics.services import _parse_materials

reports = EducationReport.objects.filter(
    status=EducationReport.ReportStatus.APPROVED,
    statistics_processed=False
)

total_encontrados = EducationReport.objects.filter(status=EducationReport.ReportStatus.APPROVED).count()
total_processaveis = reports.count()
total_ignorados = total_encontrados - total_processaveis

ind_audience = 0
ind_action = 0
ind_material = 0

for report in reports:
    # Audience
    total_audience = getattr(report, 'approximate_public', 0) or 0
    if total_audience > 0:
        ind_audience += 1 # 1 record for total audience
    
    # Materials
    materials_text = getattr(report, 'distribution_materials_distributed', '')
    tot_mat, tot_cert, tot_rev = _parse_materials(materials_text)
    if tot_mat > 0:
        ind_material += 1
    if tot_cert > 0:
        ind_material += 1
    if tot_rev > 0:
        ind_material += 1
        
    # Actions
    palestras_total = 0
    acoes_total = 0
    for action in report.actions.all():
        agenda = action.agenda
        if not agenda:
            continue
        
        action_name = (agenda.action_type_ref.name if agenda.action_type_ref else action.type_action or "").lower()
        if not action_name and agenda.action_type:
            action_name = agenda.action_type.lower()
            
        if 'palestra' in action_name:
            palestras_total += 1
            ind_action += 1 # 1 record per category
        else:
            acoes_total += 1
            ind_action += 1
            
    if palestras_total > 0:
        ind_action += 1 # TOTAL palestra action
        ind_audience += 1 # TOTAL palestra audience
    if acoes_total > 0:
        ind_action += 1 # TOTAL acao action
        ind_audience += 1 # TOTAL acao audience

print("--- RESUMO DO BACKFILL ---")
print(f"Relatórios encontrados: {total_encontrados}")
print(f"Relatórios processáveis: {total_processaveis}")
print(f"Relatórios ignorados (já processados): {total_ignorados}")
print("")
print("Indicadores previstos:")
print(f"AUDIENCE: {ind_audience}")
print(f"ACTION: {ind_action}")
print(f"MATERIAL: {ind_material}")
