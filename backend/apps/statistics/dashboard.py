from calendar import monthrange
import hashlib
from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from apps.schedules.models import EducationAction, EducationReport
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
        qs = qs.filter(agenda__requester_entity_type__iexact=filters['entity'])
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
        ) or _street_entity_from_action_counters(action)
        entity = str(street_entity or agenda.requester_entity_type or '').casefold()
        action_name = str((agenda.action_type_ref.name if agenda.action_type_ref else '') or action.type_action or '').casefold()
        institution_name = str(getattr(action, 'institution_name', '') or getattr(agenda, 'institution_location', '') or '').casefold()
        is_school_context = (
            'escolinha' in action_name
            or 'escola nota 10' in action_name
            or 'nota 10' in action_name
            or 'escola' in institution_name
            or 'col?gio' in institution_name
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
        audience = action.approach or report.approximate_public
        result[key] += float(audience or 0)
    return result
def _rankings(date_from, date_to, filters):
    reports = _operational_reports(date_from, date_to, filters)
    municipalities = list(reports.values('agenda__city').annotate(actions=Count('actions', distinct=True), audience=Coalesce(Sum('approximate_public'), 0)).order_by('-actions')[:15])
    teams = list(
        reports.filter(team__in=OFFICIAL_TEAMS)
        .values('team')
        .annotate(actions=Count('actions', distinct=True), audience=Coalesce(Sum('approximate_public'), 0))
        .order_by('-actions')[:8]
    )
    for row in municipalities + teams:
        row['average'] = round(float(row['audience'] or 0) / row['actions'], 2) if row['actions'] else 0
    heatmap = list(reports.values('operation_date').annotate(actions=Count('actions', distinct=True), audience=Coalesce(Sum('approximate_public'), 0)).order_by('operation_date'))
    return {'municipalities': municipalities, 'teams': teams, 'heatmap': heatmap}


def dashboard_payload(date_from, date_to, filters):
    signature = f"{date_from}:{date_to}:{sorted(filters.items())}"
    cache_key = f"statistics-dashboard:{hashlib.sha256(signature.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    current = derived_totals(aggregate_official_statistics(filtered_statistics(date_from, date_to, filters)))
    try:
        previous_from = date_from.replace(year=date_from.year - 1)
    except ValueError:
        previous_from = date(date_from.year - 1, 2, 28)
    try:
        previous_to = date_to.replace(year=date_to.year - 1)
    except ValueError:
        previous_to = date(date_to.year - 1, 2, 28)
    previous = derived_totals(aggregate_official_statistics(filtered_statistics(previous_from, previous_to, filters)))
    keys = set(current) | set(previous)
    comparisons = {key: variation(current.get(key, 0), previous.get(key, 0)) for key in keys}
    annual = _annual_series(filters)
    monthly = _monthly_series(date_to.year, filters)
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
    rankings = _rankings(date_from, date_to, filters)
    payload = {
        'period': {'from': date_from, 'to': date_to, 'previous_from': previous_from, 'previous_to': previous_to},
        'summary': current, 'previous': previous, 'comparisons': comparisons,
        'annual': annual, 'monthly': monthly, 'categories': categories,
        **rankings,
        'metadata': {'historical_dimensions': False, 'operational_dimensions_from': '2026-07-09'},
    }
    cache.set(cache_key, payload, 300)
    return payload
