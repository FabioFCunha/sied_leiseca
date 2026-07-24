import re
import json
from django.utils import timezone
from apps.statistics.models import ConsolidatedStatistic
from django.db import transaction

def _parse_materials(materials_text):
    """
    Parser tolerante que extrai quantidades de materiais.
    Retorna uma tupla: (total_materiais, total_certificados, total_revistinhas)
    """
    total = 0
    certificados = 0
    revistinhas = 0
    if not materials_text:
        return total, certificados, revistinhas
        
    for line in materials_text.splitlines():
        text = line.strip()
        if not text:
            continue
            
        text = re.sub(r"\[\s*\]", "| 0", text)
        if "|" in text:
            parts = text.rsplit("|", 1)
            name = parts[0].strip()
            quantity = parts[1].strip()
        else:
            match = re.match(r"^(?P<name>.+?)\s+-\s*(?P<quantity>\d+)\s*$", text)
            if not match:
                continue
            name = match.group("name").strip()
            quantity = match.group("quantity")
            
        q_match = re.search(r"\d+", str(quantity))
        if not q_match:
            continue
            
        try:
            q_val = int(q_match.group(0))
        except ValueError:
            q_val = 0
            
        total += q_val
        name_lower = name.lower()
        if "certificado" in name_lower:
            certificados += q_val
        if "revistinha" in name_lower or "gibi" in name_lower:
            revistinhas += q_val
            
    return total, certificados, revistinhas

@transaction.atomic
def generate_statistics_for_report(report, processed_by=None):
    """
    Gera todos os 19 indicadores oficiais da Estatística Institucional.
    """
    if report.status != 'APPROVED':
        return
        
    trace_id = f'report_{report.id}'
    
    op_date = report.operation_date if report.operation_date else report.created_at.date()
    base_kwargs = {
        'methodology': 'SIED_OPERATIONAL',
        'reference_date': op_date,
        'reference_year': op_date.year,
        'reference_month': op_date.month,
    }

    metrics_to_sync = []
    def add_metric(indicator, value, action_type=None, entity_type=None):
        if value > 0:
            metrics_to_sync.append({
                'indicator_type': indicator,
                'category_action_type': action_type,
                'category_entity_type': entity_type,
                'value': value,
            })

    # ====================================================
    # INDICADORES DE PÚBLICO E MATERIAIS (NÍVEL RELATÓRIO)
    # ====================================================
    total_audience = getattr(report, 'approximate_public', 0) or 0
    add_metric('AUDIENCE', total_audience)
    
    # Materiais consolidados no relatório
    materials_text = getattr(report, 'distribution_materials_distributed', '')
    tot_mat, tot_cert, tot_rev = _parse_materials(materials_text)
    add_metric('MATERIAL', tot_mat)
    add_metric('MATERIAL', tot_cert, entity_type='CERTIFICADOS ENTREGUES')
    add_metric('MATERIAL', tot_rev, entity_type='REVISTINHA SOPRINHO')

    # ====================================================
    # INDICADORES POR AÇÃO (PALESTRAS / AÇÕES)
    # ====================================================
    palestras_total = 0
    acoes_total = 0
    
    for action in report.actions.all():
        agenda = action.agenda
        if not agenda:
            continue
            
        action_name = (agenda.action_type_ref.name if agenda.action_type_ref else action.type_action or "").lower()
        if not action_name and agenda.action_type:
            action_name = agenda.action_type.lower()
            
        is_palestra = False
        is_acao = False
        
        if 'palestra' in action_name:
            is_palestra = True
        elif 'ação' in action_name or 'acao' in action_name or 'educação' in action_name or 'educacao' in action_name or 'blitz' in action_name or 'pedágio' in action_name or 'bar' in action_name:
            is_acao = True
        else:
            is_acao = True # default se não conseguir classificar

        entity_type_ref = str(agenda.requester_entity_type)
        entity_name_lower = entity_type_ref.lower()
        
        # Mapping rules based on ID Horus OR exact text from new SIED fields
        # Text from SIED Frontend form: "Instituição de Ensino Público", "Empresa/Órgão Privado", etc.
        
        if is_palestra:
            palestras_total += 1
            if entity_type_ref == '2' or 'escola' in entity_name_lower or ('ensino' in entity_name_lower and not 'universidade' in entity_name_lower): 
                add_metric('ACTION', 1, action_type='PALESTRA', entity_type='ESCOLA')
            elif entity_type_ref == '1' or 'universidade' in entity_name_lower or 'faculdade' in entity_name_lower: 
                add_metric('ACTION', 1, action_type='PALESTRA', entity_type='UNIVERSIDADE')
            elif entity_type_ref == '4' or 'empresa' in entity_name_lower or 'órgão' in entity_name_lower or 'orgao' in entity_name_lower:
                add_metric('ACTION', 1, action_type='PALESTRA', entity_type='EMPRESA')
            else:
                # Fallback to ESCOLA or EMPRESA if text not perfectly matching but it's a Palestra
                add_metric('ACTION', 1, action_type='PALESTRA', entity_type='ESCOLA')
                
        elif is_acao:
            acoes_total += 1
            if entity_type_ref == '7' or 'bar' in entity_name_lower or 'bares' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='BARES')
            elif entity_type_ref == '10' or 'pedágio' in entity_name_lower or 'pedagio' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='PEDAGIO')
            elif entity_type_ref == '9' or 'esporte' in entity_name_lower or 'esportes' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='ESPORTES')
            elif entity_type_ref == '8' or 'praia' in entity_name_lower or 'litoral' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='PRAIA')
            elif entity_type_ref == '5' or 'evento' in entity_name_lower or 'eventos' in entity_name_lower or 'festa' in entity_name_lower or 'show' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='EVENTOS')
            elif entity_type_ref == '12' or 'shopping' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='SHOPPING')
            elif entity_type_ref == '11' or 'praça' in entity_name_lower or 'praca' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='PRACAS')
            elif entity_type_ref == '13' or 'turístico' in entity_name_lower or 'turistico' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='PONTOS TURISTICOS')
            elif entity_type_ref == '15' or 'social' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='ACAO SOCIAL')
            elif entity_type_ref == '14' or 'fiscalização' in entity_name_lower or 'fiscalizacao' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='FISCALIZACAO')
            elif entity_type_ref == '6' or 'rua' in entity_name_lower:
                # Street action ID is 6, or text "Ação de Rua"
                # O SIED mapeou Ações de rua sem subcategoria específica. Vamos enviar para OUTROS por precaução ou um padrão histórico.
                # Historicamente a planilha não tem "Ação de rua", manda para "OUTROS".
                add_metric('ACTION', 1, action_type='ACAO', entity_type='OUTROS')
            else:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='OUTROS')

    if palestras_total > 0:
        add_metric('ACTION', palestras_total, action_type='PALESTRA', entity_type='TOTAL')
        add_metric('AUDIENCE', total_audience, action_type='PALESTRA', entity_type='TOTAL')
        
    if acoes_total > 0:
        add_metric('ACTION', acoes_total, action_type='ACAO', entity_type='TOTAL')
        add_metric('AUDIENCE', total_audience, action_type='ACAO', entity_type='TOTAL')

    # Find existing ones for this report
    existing_stats = list(ConsolidatedStatistic.objects.select_for_update().filter(
        traceability_id=trace_id
    ))
    
    touched_ids = set()

    # Aggregate metrics_to_sync to avoid duplicates (e.g. 2 actions in BARES)
    aggregated = {}
    for m in metrics_to_sync:
        key = (m['indicator_type'], m['category_action_type'], m['category_entity_type'])
        if key not in aggregated:
            aggregated[key] = 0
        aggregated[key] += m['value']

    for (ind, act, ent), val in aggregated.items():
        match = next((s for s in existing_stats 
                     if s.indicator_type == ind 
                     and s.category_action_type == act 
                     and s.category_entity_type == ent), None)
        
        if match:
            if match.value != val or match.status != 'ACTIVE':
                audit_entry = {
                    'changed_at': timezone.now().isoformat(),
                    'changed_by': processed_by.username if processed_by else 'system',
                    'previous_value': float(match.value) if match.value else None,
                    'previous_status': match.status,
                    'new_value': float(val),
                    'new_status': 'ACTIVE'
                }
                if not isinstance(match.audit_history, list):
                    match.audit_history = []
                match.audit_history.append(audit_entry)
                match.value = val
                match.status = 'ACTIVE'
                match.processed_by = processed_by
                match.processed_at = timezone.now()
                match.save()
            touched_ids.add(match.id)
        else:
            new_stat = ConsolidatedStatistic.objects.create(
                traceability_id=trace_id,
                indicator_type=ind,
                category_action_type=act,
                category_entity_type=ent,
                value=val,
                status='ACTIVE',
                processed_by=processed_by,
                processed_at=timezone.now(),
                **base_kwargs
            )
            touched_ids.add(new_stat.id)
            
    for s in existing_stats:
        if s.id not in touched_ids and s.status != 'SUSPENDED':
            audit_entry = {
                'changed_at': timezone.now().isoformat(),
                'changed_by': processed_by.username if processed_by else 'system',
                'previous_value': float(s.value),
                'previous_status': s.status,
                'new_value': float(s.value),
                'new_status': 'SUSPENDED'
            }
            if not isinstance(s.audit_history, list):
                s.audit_history = []
            s.audit_history.append(audit_entry)
            s.status = 'SUSPENDED'
            s.save()

    report.statistics_processed = True
    report.statistics_processed_at = timezone.now()
    report.statistics_processed_by = processed_by
    report.save(update_fields=['statistics_processed', 'statistics_processed_at', 'statistics_processed_by'])

@transaction.atomic
def remove_statistics_for_report(report, processed_by=None):
    _suspend_statistics_for_report(report.id, processed_by)

@transaction.atomic
def _suspend_statistics_for_report(report_id, processed_by=None):
    stats = ConsolidatedStatistic.objects.select_for_update().filter(
        traceability_id=f'report_{report_id}',
        status='ACTIVE'
    )
    for s in stats:
        audit_entry = {
            'changed_at': timezone.now().isoformat(),
            'changed_by': processed_by.username if processed_by else 'system',
            'previous_value': float(s.value),
            'previous_status': s.status,
            'new_value': float(s.value),
            'new_status': 'SUSPENDED'
        }
        if not isinstance(s.audit_history, list):
            s.audit_history = []
        s.audit_history.append(audit_entry)
        s.status = 'SUSPENDED'
        s.save()

@transaction.atomic
def invalidate_statistics(report, processed_by=None):
    """
    Invalida estatísticas previamente homologadas de um relatório, marcando-o para revalidação.
    """
    if report.statistics_processed:
        remove_statistics_for_report(report, processed_by)
        report.statistics_processed = False
        report.statistics_processed_at = None
        report.statistics_processed_by = None
        report.save(update_fields=['statistics_processed', 'statistics_processed_at', 'statistics_processed_by'])
