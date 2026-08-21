import re
import json
import unicodedata
from collections import defaultdict
from django.utils import timezone
from apps.statistics.models import ConsolidatedStatistic
from django.db import transaction
from django.db.models import Sum

OFFICIAL_KEYS = (
    'AUDIENCE - Geral', 'AUDIENCE - PALESTRAS', 'AUDIENCE - ACOES',
    'ACTION - Geral', 'ACTION - Escola', 'ACTION - Universidade',
    'ACTION - Empresa', 'ACTION - Bares', 'ACTION - Ped\u00e1gio',
    'ACTION - Pra\u00e7as Esportivas', 'ACTION - Praia', 'ACTION - Eventos',
    'ACTION - Shopping', 'ACTION - A\u00e7\u00e3o Social', 'ACTION - Outros',
    'ACTION - Pra\u00e7as/Parques P\u00fablicos',
    'ACTION - Pontos tur\u00edsticos', 'ACTION - A\u00e7\u00e3o conjunta com a fiscaliza\u00e7\u00e3o',
    'MATERIAL - Geral', 'MATERIAL - Certificados', 'MATERIAL - Soprinho',
)

ENTITY_KEYS = {
    'ESCOLA': 'Escola', 'ESCOLAS': 'Escola',
    'UNIVERSIDADE': 'Universidade', 'UNIVERSIDADES': 'Universidade',
    'EMPRESA': 'Empresa', 'EMPRESAS': 'Empresa',
    'BARES': 'Bares', 'PEDAGIO': 'Ped\u00e1gio',
    'ESPORTES': 'Pra\u00e7as Esportivas', 'PRACAS ESPORTIVAS': 'Pra\u00e7as Esportivas',
    'PRAIA': 'Praia', 'EVENTOS': 'Eventos',
    'SHOPPING': 'Shopping', 'SHOPPING CENTRO COMERCIAL': 'Shopping',
    'ACAO SOCIAL': 'A\u00e7\u00e3o Social', 'OUTROS': 'Outros',
    'PRACAS': 'Pra\u00e7as/Parques P\u00fablicos',
    'PRACAS PARQUES PUBLICOS': 'Pra\u00e7as/Parques P\u00fablicos',
    'PONTOS TURISTICOS': 'Pontos tur\u00edsticos',
    'FISCALIZACAO': 'A\u00e7\u00e3o conjunta com a fiscaliza\u00e7\u00e3o',
    'CERTIFICADOS': 'Certificados',
    'CERTIFICADOS ENTREGUES': 'Certificados',
    'SOPRINHO': 'Soprinho', 'REVISTINHA SOPRINHO': 'Soprinho',
}

def _normalized_statistic_name(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    text = text.encode('ascii', 'ignore').decode('ascii').upper()
    return re.sub(r'[^A-Z0-9]+', ' ', text).strip()



def _street_detail_labels(*sources):
    labels = []
    for source in sources:
        if isinstance(source, dict):
            values = source.values()
        elif isinstance(source, list):
            values = source
        elif isinstance(source, str):
            values = [source]
        else:
            continue
        for item in values:
            if isinstance(item, dict):
                value = next((item.get(key) for key in ('type', 'label', 'name', 'action_type', 'street_action_type') if item.get(key)), '')
            else:
                value = item
            if value:
                labels.append(str(value))
    return labels


def _street_entity_from_details(*sources):
    for label in _street_detail_labels(*sources):
        normalized = _normalized_statistic_name(label)
        if normalized in ENTITY_KEYS:
            return normalized
        if 'BAR' in normalized:
            return 'BARES'
        if 'PEDAGIO' in normalized:
            return 'PEDAGIO'
        if 'ESPORTE' in normalized or 'PRACAS ESPORTIVAS' in normalized:
            return 'ESPORTES'
        if 'PRAIA' in normalized:
            return 'PRAIA'
        if 'EVENTO' in normalized:
            return 'EVENTOS'
        if 'SHOPPING' in normalized:
            return 'SHOPPING'
        if 'FISCALIZA' in normalized:
            return 'FISCALIZACAO'
        if 'SOCIAL' in normalized:
            return 'ACAO SOCIAL'
        if 'TURIST' in normalized:
            return 'PONTOS TURISTICOS'
        if 'PRACA' in normalized or 'PARQUE' in normalized:
            return 'PRACAS'
        if 'OUTRO' in normalized:
            return 'OUTROS'
    return ''


STREET_ACTION_COUNTER_ENTITIES = (
    ('bars', 'BARES'),
    ('tolls', 'PEDAGIO'),
    ('sports', 'ESPORTES'),
    ('beach', 'PRAIA'),
    ('events', 'EVENTOS'),
    ('shopping', 'SHOPPING'),
    ('parks', 'PRACAS'),
    ('tourist_spots', 'PONTOS TURISTICOS'),
    ('social_actions', 'ACAO SOCIAL'),
    ('joint_inspections', 'FISCALIZACAO'),
    ('other_actions', 'OUTROS'),
)


def _positive_counter(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _street_entity_from_action_counters(action):
    for field, entity in STREET_ACTION_COUNTER_ENTITIES:
        if _positive_counter(getattr(action, field, 0)) > 0:
            return entity
    return ''

def _action_audience_value(action, is_palestra=False):
    if is_palestra:
        primary = _positive_counter(getattr(action, 'approached_lectures', 0))
    else:
        primary = _positive_counter(getattr(action, 'approached_actions', 0))
    return primary or _positive_counter(getattr(action, 'approach', 0))


def _agreement_audience_value(action):
    return _positive_counter(getattr(action, 'approached_lectures', 0))

def aggregate_official_rows(rows):
    totals = defaultdict(float)
    for row in rows:
        indicator = row['indicator_type']
        action = _normalized_statistic_name(row.get('category_action_type__name'))
        entity = _normalized_statistic_name(row.get('category_entity_type'))
        value = float(row.get('total') or 0)
        if indicator == 'AUDIENCE':
            if not action and not entity:
                totals['AUDIENCE - Geral'] += value
            elif (action == 'PALESTRA' and entity == 'TOTAL') or (not action and entity == 'PALESTRAS'):
                totals['AUDIENCE - PALESTRAS'] += value
            elif (action == 'ACAO' and entity == 'TOTAL') or (not action and entity == 'ACOES'):
                totals['AUDIENCE - ACOES'] += value
        elif indicator == 'ACTION':
            if entity == 'TOTAL':
                totals['ACTION - Geral'] += value
            elif entity in ENTITY_KEYS:
                totals[f"ACTION - {ENTITY_KEYS[entity]}"] += value
                if row.get('methodology') == 'HISTORICAL_LEGACY':
                    totals['ACTION - Geral'] += value
        elif indicator == 'MATERIAL':
            if not action and not entity:
                totals['MATERIAL - Geral'] += value
            elif entity in ENTITY_KEYS:
                totals[f"MATERIAL - {ENTITY_KEYS[entity]}"] += value
    return {key: totals[key] for key in OFFICIAL_KEYS}


def aggregate_official_statistics(queryset):
    rows = queryset.values(
        'methodology', 'indicator_type', 'category_action_type__name',
        'category_entity_type',
    ).annotate(total=Sum('value'))
    return aggregate_official_rows(rows)

def _material_rows(payload):
    if isinstance(payload, dict):
        if any(key in payload for key in ('name', 'material', 'kit', 'dynamic_name')):
            name = next((payload.get(key) for key in ('name', 'material', 'kit', 'dynamic_name') if payload.get(key)), '')
            quantity = next((payload.get(key) for key in ('quantity', 'value', 'count', 'amount') if payload.get(key) is not None), 0)
            yield name, quantity
        else:
            for name, quantity in payload.items():
                yield name, quantity
    elif isinstance(payload, list):
        for item in payload:
            yield from _material_rows(item)


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
    parsed_rows = []
    if isinstance(materials_text, (dict, list)):
        parsed_rows = list(_material_rows(materials_text))
    elif isinstance(materials_text, str) and materials_text.lstrip().startswith(('[', '{')):
        try:
            parsed_rows = list(_material_rows(json.loads(materials_text)))
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed_rows = []
    if parsed_rows:
        materials_text = '\n'.join(f'{name} | {quantity}' for name, quantity in parsed_rows)

        
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
    from apps.schedules.models import ActionType

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
    
    # Materiais consolidados no relatório
    actions = list(report.actions.all())
    report_materials = getattr(report, 'distribution_materials_distributed', '')
    material_payloads = [report_materials] if str(report_materials or '').strip() else []
    if not material_payloads:
        material_payloads = list(dict.fromkeys(
            action.distribution_materials_distributed
            for action in actions
            if str(getattr(action, 'distribution_materials_distributed', '') or '').strip()
        ))
    material_totals = [_parse_materials(payload) for payload in material_payloads]
    tot_mat, tot_cert, tot_rev = (sum(values) for values in zip(*material_totals)) if material_totals else (0, 0, 0)
    add_metric('MATERIAL', tot_mat)
    add_metric('MATERIAL', tot_cert, entity_type='CERTIFICADOS ENTREGUES')
    add_metric('MATERIAL', tot_rev, entity_type='REVISTINHA SOPRINHO')

    # ====================================================
    # INDICADORES POR AÇÃO (PALESTRAS / AÇÕES)
    # ====================================================
    palestras_total = 0
    acoes_total = 0
    palestras_audience = 0
    acoes_audience = 0
    
    for action in actions:
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
        street_entity = _street_entity_from_details(
            getattr(action, 'street_action_details', None),
            getattr(report, 'street_action_details', None),
            getattr(agenda, 'street_action_details', None),
        ) or _street_entity_from_action_counters(action) or _street_entity_from_details(getattr(action, 'type_action', None)) or _street_entity_from_details(getattr(agenda, 'action_type', None))
        entity_name_lower = (street_entity or entity_type_ref).lower()
        institution_name_lower = str(getattr(action, 'institution_name', '') or getattr(agenda, 'institution_location', '') or '').lower()
        is_school_context = (
            'escolinha' in action_name
            or 'escola nota 10' in action_name
            or 'nota 10' in action_name
            or 'escola' in institution_name_lower
            or 'col?gio' in institution_name_lower
            or 'colegio' in institution_name_lower
        )
        
        # Mapping rules based on ID Horus OR exact text from new SIED fields
        # Text from SIED Frontend form: "Instituição de Ensino Público", "Empresa/Órgão Privado", etc.
        
        if is_palestra:
            palestras_total += 1
            palestras_audience += _action_audience_value(action, is_palestra=True)
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
            acoes_audience += _action_audience_value(action, is_palestra=False)
            if entity_type_ref == '2' or is_school_context or 'escola' in entity_name_lower or ('ensino' in entity_name_lower and not 'universidade' in entity_name_lower):
                add_metric('ACTION', 1, action_type='ACAO', entity_type='ESCOLA')
            elif entity_type_ref == '7' or 'bar' in entity_name_lower or 'bares' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='BARES')
            elif entity_type_ref == '10' or 'pedágio' in entity_name_lower or 'pedagio' in entity_name_lower:
                add_metric('ACTION', 1, action_type='ACAO', entity_type='PEDAGIO')
            elif entity_type_ref == '9' or 'esport' in entity_name_lower:
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

    action_audience_total = palestras_audience + acoes_audience
    total_audience = action_audience_total or (getattr(report, 'approximate_public', 0) or 0)
    add_metric('AUDIENCE', total_audience)

    if palestras_total > 0:
        add_metric('ACTION', palestras_total, action_type='PALESTRA', entity_type='TOTAL')
        add_metric('AUDIENCE', palestras_audience or total_audience, action_type='PALESTRA', entity_type='TOTAL')
        
    if acoes_total > 0:
        add_metric('ACTION', acoes_total, action_type='ACAO', entity_type='TOTAL')
        add_metric('AUDIENCE', acoes_audience or total_audience, action_type='ACAO', entity_type='TOTAL')

    # ====================================================
    # INDICADORES DE CONVÊNIOS EDUCACIONAIS (ESCOLA / ESCOLINHA NOTA 10)
    # ====================================================
    agreement_actions = {}
    for action in actions:
        agenda = action.agenda
        ind = getattr(action, 'agreement_indicator', None)
        if not ind:
            from apps.schedules.agreement_indicators import derive_education_agreement_indicator
            kind = getattr(action, 'requester_entity_kind', None) or (getattr(agenda, 'requester_entity_kind', None) if agenda else None)
            nature = getattr(action, 'requester_entity_nature', None) or (getattr(agenda, 'requester_entity_nature', None) if agenda else None)
            age = getattr(action, 'age_range', None) or (getattr(agenda, 'age_range', None) if agenda else None)
            ind = derive_education_agreement_indicator(kind, nature, age)
        
        if ind in ['ESCOLA_NOTA_10', 'ESCOLINHA_NOTA_10']:
            if ind not in agreement_actions:
                agreement_actions[ind] = {'actions': 0, 'audience': 0}
            agreement_actions[ind]['actions'] += 1
            agreement_actions[ind]['audience'] += _agreement_audience_value(action)

    for agreement_name, data in agreement_actions.items():
        if data['actions'] > 0:
            add_metric('ACTION', data['actions'], action_type=agreement_name, entity_type='EDUCATIONAL_AGREEMENT')
        add_metric('AUDIENCE', data['audience'], action_type=agreement_name, entity_type='EDUCATIONAL_AGREEMENT')

    action_type_names = {
        'ACAO': 'Ação',
        'PALESTRA': 'Palestra',
        'ESCOLA_NOTA_10': 'Escola Nota 10',
        'ESCOLINHA_NOTA_10': 'Escolinha Nota 10',
    }
    resolved_action_types = {}
    for action_type_code in {
        metric['category_action_type'] for metric in metrics_to_sync
        if metric['category_action_type'] is not None
    }:
        action_type_name = action_type_names.get(action_type_code)
        if action_type_name is None:
            raise ValueError(f"Tipo de acao estatistica desconhecido: '{action_type_code}'.")
        try:
            resolved_action_types[action_type_code] = ActionType.objects.get(name__iexact=action_type_name)
        except ActionType.DoesNotExist as exc:
            raise ValueError(
                f"Tipo de acao obrigatorio para a estatistica nao cadastrado: '{action_type_name}'."
            ) from exc
        except ActionType.MultipleObjectsReturned as exc:
            raise ValueError(
                f"Mais de um tipo de acao corresponde a categoria estatistica '{action_type_name}'."
            ) from exc
    for metric in metrics_to_sync:
        if metric['category_action_type'] is not None:
            metric['category_action_type'] = resolved_action_types[metric['category_action_type']]

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
