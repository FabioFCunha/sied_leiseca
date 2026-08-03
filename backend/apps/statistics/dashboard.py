from calendar import monthrange
import hashlib
from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.schedules.models import Agenda, EducationAction, EducationReport
from apps.statistics.models import ConsolidatedStatistic
from apps.statistics.historical_baseline import HISTORICAL_BASELINE
from apps.statistics.services import _street_entity_from_action_counters, _street_entity_from_details, aggregate_official_rows, aggregate_official_statistics
from apps.statistics.views import get_hybrid_queryset


LECTURE_KEYS = ('ACTION - Escola', 'ACTION - Universidade', 'ACTION - Empresa')
STREET_KEYS = (
    'ACTION - Bares', 'ACTION - Pedágio', 'ACTION - Praças Esportivas',
    'ACTION - Praia', 'ACTION - Eventos', 'ACTION - Shopping',
    'ACTION - Ação Social', 'ACTION - Outros',
    'ACTION - Praças/Parques Públicos', 'ACTION - Pontos turísticos',
    'ACTION - Ação conjunta com a fiscalização',
)
DIMENSION_FILTERS = ('municipality', 'team', 'institution', 'entity', 'action_type')
OFFICIAL_TEAMS = ('ALFA', 'BRAVO', 'CHARLIE', 'DELTA', 'ECHO', 'FOX', 'GOLF', 'HOTEL')

OPERATIONAL_COMPARISON_START = date(2026, 7, 9)
DASHBOARD_OPERATIONAL_START = date(2026, 7, 1)


def _shift_month(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def comparison_period(date_from, date_to):
    if date_to < date(OPERATIONAL_COMPARISON_START.year + 1, OPERATIONAL_COMPARISON_START.month, OPERATIONAL_COMPARISON_START.day):
        return {
            'from': _shift_month(date_from, -1),
            'to': _shift_month(date_to, -1),
            'type': 'previous_month',
            'label': 'm\u00eas anterior',
        }
    try:
        previous_from = date_from.replace(year=date_from.year - 1)
    except ValueError:
        previous_from = date(date_from.year - 1, 2, 28)
    try:
        previous_to = date_to.replace(year=date_to.year - 1)
    except ValueError:
        previous_to = date(date_to.year - 1, 2, 28)
    return {
        'from': previous_from,
        'to': previous_to,
        'type': 'previous_year',
        'label': 'mesmo per\u00edodo do ano anterior',
    }

CATEGORY_LABELS = {
    'ACTION - Escola': 'Escolas', 'ACTION - Universidade': 'Universidades',
    'ACTION - Empresa': 'Empresas', 'ACTION - Bares': 'Bares',
    'ACTION - Pedágio': 'Pedágio', 'ACTION - Praças Esportivas': 'Esportes',
    'ACTION - Praia': 'Praia', 'ACTION - Eventos': 'Eventos',
    'ACTION - Shopping': 'Shopping/Centro Comercial',
    'ACTION - Ação Social': 'Ação Social', 'ACTION - Outros': 'Outros',
    'ACTION - Praças/Parques Públicos': 'Praças/Parques Públicos',
    'ACTION - Pontos turísticos': 'Pontos turísticos',
    'ACTION - Ação conjunta com a fiscalização': 'Ação conjunta com a fiscalização',
}



ENTITY_EQUIVALENTS = {
    "A\u00e7\u00e3o de Rua": [
        "6",
        "6 P\u00fablico",
        "A\u00e7\u00e3o de Rua",
    ],
    "Institui\u00e7\u00e3o de Ensino P\u00fablico": [
        "Escola",
        "Institui\u00e7\u00e3o de Ensino P\u00fablico",
    ],
    "Empresa/\u00d3rg\u00e3o P\u00fablico": [
        "Empresa/\u00d3rg\u00e3o P\u00fablico",
    ],
    "Organiza\u00e7\u00e3o de evento Privado": [
        "Organiza\u00e7\u00e3o de evento Privado",
    ],
    "Organiza\u00e7\u00e3o de evento P\u00fablico": [
        "Organiza\u00e7\u00e3o de evento P\u00fablico",
    ],
}


def entity_filter_values(value):
    return ENTITY_EQUIVALENTS.get(value, [value])


def derived_totals(totals):
    values = dict(totals)
    lectures = sum(float(values.get(key, 0) or 0) for key in LECTURE_KEYS)
    categorized_street = sum(float(values.get(key, 0) or 0) for key in STREET_KEYS)
    actions_total = float(values.get('ACTION - Geral', 0) or 0)
    street = max(actions_total - lectures, categorized_street, 0)
    values['LECTURES - Geral'] = lectures
    values['STREET_ACTIONS - Geral'] = street
    values['AVERAGE_AUDIENCE'] = (
        float(values.get('AUDIENCE - Geral', 0) or 0) / actions_total
        if actions_total else 0
    )
    return values


def variation(current, previous):
    current = float(current or 0)
    previous = float(previous or 0)
    if not previous:
        return {'absolute': current, 'percentage': None if current else 0, 'status': 'NEW' if current else 'STABLE'}
    percentage = ((current - previous) / previous) * 100
    return {'absolute': current - previous, 'percentage': round(percentage, 2), 'status': 'UP' if percentage > 0 else 'DOWN' if percentage < 0 else 'STABLE'}


def _parse_expected_public_value(*values):
    import re
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        if text.isdigit():
            return int(text)
        numbers = [int(match) for match in re.findall(r'\d+', text)]
        if numbers:
            return max(numbers)
    return 0


def _expected_public_queryset(date_from, date_to, filters):
    qs = Agenda.objects.filter(date__range=(date_from, date_to)).exclude(status=Agenda.Status.CANCELLED)
    qs = qs.filter(Q(origin=Agenda.Origin.PUBLIC_FORM) | ~Q(audience='') | Q(participant_range__isnull=False)).exclude(
        Q(audience='') & (Q(participant_range='') | Q(participant_range__isnull=True))
    )
    if filters.get('municipality'):
        qs = qs.filter(city__iexact=filters['municipality'])
    if filters.get('team'):
        qs = qs.filter(team_name__iexact=filters['team'])
    if filters.get('institution'):
        qs = qs.filter(institution_location__icontains=filters['institution'])
    if filters.get('entity'):
        qs = qs.filter(requester_entity_type__in=entity_filter_values(filters['entity']))
    if filters.get('action_type'):
        qs = qs.filter(action_type__icontains=filters['action_type'])
    return qs


def _expected_public_total(date_from, date_to, filters):
    return sum(
        _parse_expected_public_value(agenda.audience, agenda.participant_range)
        for agenda in _expected_public_queryset(date_from, date_to, filters).only('audience', 'participant_range')
    )


def _reports_without_public_total(date_from, date_to, filters):
    return _operational_reports(date_from, date_to, filters).filter(
        Q(approximate_public__isnull=True) | Q(approximate_public=0)
    ).count()


def _administrative_demands_queryset(date_from, date_to, filters):
    qs = Agenda.objects.filter(
        date__range=(date_from, date_to),
        origin=Agenda.Origin.INTERNAL,
        requester_entity_type="Demanda Administrativa",
    ).exclude(status__in=[Agenda.Status.CANCELLED, "REJECTED", "REFUSED"])
    if filters.get('municipality'):
        qs = qs.filter(city__iexact=filters['municipality'])
    if filters.get('team'):
        qs = qs.filter(Q(team_name__iexact=filters['team']) | Q(team_ref__name__iexact=filters['team']))
    if filters.get('institution'):
        qs = qs.filter(institution_location__icontains=filters['institution'])
    if filters.get('entity'):
        if "Demanda Administrativa" not in entity_filter_values(filters['entity']):
            return qs.none()
    if filters.get('action_type'):
        qs = qs.filter(Q(action_type__icontains=filters['action_type']) | Q(action_type_ref__name__icontains=filters['action_type']))
    return qs


def _administrative_demands_payload(date_from, date_to, filters):
    labels = {
        Agenda.AdministrativeDemandType.TRAVEL: "Deslocamento de viagem",
        Agenda.AdministrativeDemandType.INTERVIEW: "Entrevista",
        Agenda.AdministrativeDemandType.MEETING: "Reunião",
    }
    codes = [
        Agenda.AdministrativeDemandType.TRAVEL,
        Agenda.AdministrativeDemandType.INTERVIEW,
        Agenda.AdministrativeDemandType.MEETING,
    ]
    grouped = {
        row['administrative_demand_type']: int(row['total'] or 0)
        for row in _administrative_demands_queryset(date_from, date_to, filters)
        .values('administrative_demand_type')
        .annotate(total=Count('id'))
    }
    total = sum(grouped.get(code, 0) for code in codes)
    items = []
    for code in codes:
        value = grouped.get(code, 0)
        items.append({
            'code': code,
            'label': labels[code],
            'value': value,
            'percentage': round((value / total) * 100, 2) if total else 0.0,
        })
    return {
        'total': total,
        'items': items,
    }


def _operational_reports(date_from, date_to, filters):
    qs = EducationReport.objects.filter(
        status=EducationReport.ReportStatus.APPROVED,
        statistics_processed=True,
        operation_date__range=(date_from, date_to),
    ).select_related('agenda', 'agenda__municipality_ref')
    if filters.get('municipality'):
        qs = qs.filter(agenda__city__iexact=filters['municipality'])
    if filters.get('team'):
        qs = qs.filter(team__iexact=filters['team'])
    if filters.get('institution'):
        qs = qs.filter(actions__institution_name__icontains=filters['institution']).distinct()
    if filters.get('entity'):
        qs = qs.filter(agenda__requester_entity_type__in=entity_filter_values(filters['entity']))
    if filters.get('action_type'):
        qs = qs.filter(actions__type_action__icontains=filters['action_type']).distinct()
    return qs


def filtered_statistics(date_from, date_to, filters):
    qs = get_hybrid_queryset(date_from, date_to)
    if _has_dimension_filters(filters):
        trace_ids = [f'report_{pk}' for pk in _operational_reports(date_from, date_to, filters).values_list('pk', flat=True)]
        qs = qs.filter(methodology='SIED_OPERATIONAL', traceability_id__in=trace_ids)
    return qs


def _grouped_statistics(queryset, field):
    grouped = {}
    rows = queryset.values(
        field, 'methodology', 'indicator_type',
        'category_action_type__name', 'category_entity_type',
    ).annotate(total=Sum('value')).order_by(field)
    for row in rows:
        grouped.setdefault(row[field], []).append(row)
    return grouped


def _has_dimension_filters(filters):
    return any(filters.get(key) for key in DIMENSION_FILTERS)


def _add_totals(base, addition):
    values = dict(base)
    for key, value in addition.items():
        values[key] = float(values.get(key, 0) or 0) + float(value or 0)
    return values


def _annual_series(filters):
    current_year = date.today().year
    grouped = _grouped_statistics(
        filtered_statistics(date(2011, 1, 1), date(current_year, 12, 31), filters).filter(methodology='SIED_OPERATIONAL'),
        'reference_year',
    )
    years = set(grouped)
    if not _has_dimension_filters(filters):
        years.update(HISTORICAL_BASELINE)
    return [
        {
            'year': year,
            'values': derived_totals(_add_totals(
                {} if _has_dimension_filters(filters) else HISTORICAL_BASELINE.get(year, {}),
                aggregate_official_rows(grouped.get(year, [])),
            )),
        }
        for year in sorted(year for year in years if year)
    ]


def _monthly_series(year, filters):
    grouped = _grouped_statistics(
        filtered_statistics(date(year, 1, 1), date(year, 12, 31), filters).filter(reference_month__isnull=False),
        'reference_month',
    )
    return [
        {'month': month, 'values': derived_totals(aggregate_official_rows(grouped.get(month, [])))}
        for month in range(1, 13)
    ]



def _visual_monthly_series(year, filters):
    rows = _monthly_series(year, filters)
    if _has_dimension_filters(filters) or year not in HISTORICAL_BASELINE:
        return rows
    monthly_baseline = {
        key: float(value or 0) / 6
        for key, value in HISTORICAL_BASELINE.get(year, {}).items()
    }
    visual_rows = []
    for row in rows:
        values = dict(row['values'])
        if row['month'] <= 6:
            values = derived_totals(_add_totals(values, monthly_baseline))
        visual_rows.append({'month': row['month'], 'values': values})
    return visual_rows

def _daily_series(date_from, date_to, filters):
    grouped = _grouped_statistics(
        filtered_statistics(date_from, date_to, filters).filter(reference_date__isnull=False),
        'reference_date',
    )
    rows = []
    current = date_from
    while current <= date_to:
        rows.append({
            'date': current.isoformat(),
            'day_label': current.strftime('%d/%m'),
            'values': derived_totals(aggregate_official_rows(grouped.get(current, []))),
        })
        current += timedelta(days=1)
    return rows

def _action_audience_value(action, report=None, is_palestra=False):
    primary = getattr(action, 'approached_lectures' if is_palestra else 'approached_actions', 0) or 0
    return primary or getattr(action, 'approach', 0) or getattr(report, 'approximate_public', 0) or 0

def _category_audience(date_from, date_to, filters):
    reports = _operational_reports(date_from, date_to, filters)
    actions = EducationAction.objects.filter(report__in=reports).select_related('agenda', 'report', 'agenda__action_type_ref')
    result = {key: 0 for key in (*LECTURE_KEYS, *STREET_KEYS)}
    for action in actions:
        agenda = action.agenda
        report = action.report
        if not agenda or not report:
            continue
        street_entity = _street_entity_from_details(
            getattr(action, 'street_action_details', None),
            getattr(report, 'street_action_details', None),
            getattr(agenda, 'street_action_details', None),
        ) or _street_entity_from_action_counters(action) or _street_entity_from_details(getattr(action, 'type_action', None)) or _street_entity_from_details(getattr(agenda, 'action_type', None))
        entity = str(street_entity or agenda.requester_entity_type or '').casefold()
        action_name = str((agenda.action_type_ref.name if agenda.action_type_ref else '') or action.type_action or '').casefold()
        institution_name = str(getattr(action, 'institution_name', '') or getattr(agenda, 'institution_location', '') or '').casefold()
        is_school_context = (
            'escolinha' in action_name
            or 'escola nota 10' in action_name
            or 'nota 10' in action_name
            or 'escola' in institution_name
            or 'colégio' in institution_name
            or 'colegio' in institution_name
        )
        if 'palestra' in action_name:
            key = 'ACTION - Universidade' if ('universidade' in entity or 'faculdade' in entity or entity == '1') else 'ACTION - Empresa' if ('empresa' in entity or 'órgão' in entity or 'orgao' in entity or entity == '4') else 'ACTION - Escola'
        elif 'escola' in entity or ('ensino' in entity and 'universidade' not in entity) or is_school_context: key = 'ACTION - Escola'
        elif 'bar' in entity or entity == '7': key = 'ACTION - Bares'
        elif 'pedágio' in entity or 'pedagio' in entity or entity == '10': key = 'ACTION - Pedágio'
        elif 'esport' in entity or entity == '9': key = 'ACTION - Praças Esportivas'
        elif 'praia' in entity or entity == '8': key = 'ACTION - Praia'
        elif 'evento' in entity or entity == '5': key = 'ACTION - Eventos'
        elif 'shopping' in entity or entity == '12': key = 'ACTION - Shopping'
        elif 'turíst' in entity or 'turist' in entity or entity == '13': key = 'ACTION - Pontos turísticos'
        elif 'fiscaliza' in entity or entity == '14': key = 'ACTION - Ação conjunta com a fiscalização'
        elif 'social' in entity or entity == '15': key = 'ACTION - Ação Social'
        elif 'praça' in entity or 'praca' in entity or 'parque' in entity or entity == '11': key = 'ACTION - Praças/Parques Públicos'
        else: key = 'ACTION - Outros'
        audience = _action_audience_value(action, report, is_palestra=('palestra' in action_name))
        result[key] += float(audience or 0)
    return result
def _rankings(date_from, date_to, filters, daily=None):
    reports = _operational_reports(date_from, date_to, filters)
    municipalities = list(
        reports.values('agenda__city')
        .annotate(actions=Count('actions', distinct=True), audience=Coalesce(Sum('approximate_public'), 0))
        .filter(Q(actions__gt=0) | Q(audience__gt=0))
        .order_by('-actions')[:15]
    )
    teams = list(
        reports.filter(team__in=OFFICIAL_TEAMS)
        .values('team')
        .annotate(actions=Count('actions', distinct=True), audience=Coalesce(Sum('approximate_public'), 0))
        .order_by('-actions')[:8]
    )
    for row in municipalities + teams:
        row['average'] = round(float(row['audience'] or 0) / row['actions'], 2) if row['actions'] else 0
    daily = daily if daily is not None else _daily_series(date_from, date_to, filters)
    official_by_date = {
        date.fromisoformat(row['date']): int(round(float(row.get('values', {}).get('ACTION - Geral', 0) or 0)))
        for row in daily
    }
    raw_by_date = {}
    heatmap_rows = (
        reports.values('operation_date', 'agenda__start_time')
        .annotate(total=Count('actions', distinct=True))
        .order_by('operation_date', 'agenda__start_time')
    )
    for row in heatmap_rows:
        operation_date = row.get('operation_date')
        if not operation_date:
            continue
        start_time = row.get('agenda__start_time')
        hour = start_time.hour if start_time else 9
        slot = f"{max(6, min(21, hour)):02d}:00"
        raw_by_date.setdefault(operation_date, {})[slot] = raw_by_date.setdefault(operation_date, {}).get(slot, 0) + int(row.get('total') or 0)

    heatmap = []
    for operation_date, official_total in official_by_date.items():
        if official_total <= 0:
            continue
        slots = raw_by_date.get(operation_date) or {'09:00': official_total}
        raw_total = sum(slots.values())
        if raw_total <= 0:
            adjusted = {'09:00': official_total}
        elif raw_total == official_total:
            adjusted = slots
        else:
            portions = []
            used = 0
            for slot, raw_value in slots.items():
                exact = (raw_value * official_total) / raw_total
                base = int(exact)
                used += base
                portions.append([slot, base, exact - base])
            for item in sorted(portions, key=lambda value: value[2], reverse=True)[:max(0, official_total - used)]:
                item[1] += 1
            adjusted = {slot: value for slot, value, _ in portions if value > 0}
        for slot, total in sorted(adjusted.items()):
            heatmap.append({
                'date': operation_date.isoformat(),
                'day': operation_date.weekday(),
                'day_label': operation_date.strftime('%d/%m'),
                'slot': slot,
                'total': total,
            })
    return {'municipalities': municipalities, 'teams': teams, 'heatmap': heatmap}


def dashboard_payload(date_from, date_to, filters):
    date_from = max(date_from, DASHBOARD_OPERATIONAL_START)
    signature = f"{date_from}:{date_to}:{sorted(filters.items())}"
    cache_key = f"statistics-dashboard:{hashlib.sha256(signature.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    current = derived_totals(aggregate_official_statistics(filtered_statistics(date_from, date_to, filters)))
    current['EXPECTED_PUBLIC'] = _expected_public_total(date_from, date_to, filters)
    current['REPORTS_WITHOUT_PUBLIC'] = _reports_without_public_total(date_from, date_to, filters)
    comparison = comparison_period(date_from, date_to)
    previous_from = comparison['from']
    previous_to = comparison['to']
    previous = derived_totals(aggregate_official_statistics(filtered_statistics(previous_from, previous_to, filters)))
    previous['EXPECTED_PUBLIC'] = _expected_public_total(previous_from, previous_to, filters)
    previous['REPORTS_WITHOUT_PUBLIC'] = _reports_without_public_total(previous_from, previous_to, filters)
    keys = set(current) | set(previous)
    comparisons = {key: variation(current.get(key, 0), previous.get(key, 0)) for key in keys}
    annual = _annual_series(filters)
    monthly = _monthly_series(date_to.year, filters)
    visual_monthly = _visual_monthly_series(date_to.year, filters)
    daily = _daily_series(date_from, date_to, filters)
    category_audience = _category_audience(date_from, date_to, filters)
    categories = [
        {
            'key': key,
            'label': CATEGORY_LABELS[key],
            'value': current.get(key, 0),
            'previous': previous.get(key, 0),
            'audience': category_audience.get(key, 0),
        }
        for key in (*LECTURE_KEYS, *STREET_KEYS)
    ]
    rankings = _rankings(date_from, date_to, filters, daily)
    administrative_demands = _administrative_demands_payload(date_from, date_to, filters)
    payload = {
        'period': {'from': date_from, 'to': date_to, 'previous_from': previous_from, 'previous_to': previous_to, 'comparison_type': comparison['type'], 'comparison_label': comparison['label']},
        'summary': current, 'previous': previous, 'comparisons': comparisons,
        'annual': annual, 'monthly': monthly, 'visual_monthly': visual_monthly, 'daily': daily, 'categories': categories,
        'administrative_demands': administrative_demands,
        **rankings,
        'metadata': {'historical_dimensions': False, 'operational_dimensions_from': '2026-07-09', 'comparison_label': comparison['label'], 'comparison_type': comparison['type']},
    }
    cache.set(cache_key, payload, 300)
    return payload
