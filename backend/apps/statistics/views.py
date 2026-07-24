from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, date
from django.db.models import Sum, Q
from apps.statistics.models import ConsolidatedStatistic
from apps.statistics.services import aggregate_official_statistics

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

from django.conf import settings

def get_hybrid_queryset(date_from, date_to):
    """
    Returns a queryset respecting the hybrid date boundaries.
    Before 2026-07-09 -> Only HISTORICAL_LEGACY
    After 2026-07-09 -> Only SIED_OPERATIONAL
    Only ACTIVE stats are returned.
    """
    qs = ConsolidatedStatistic.objects.filter(status='ACTIVE')
    
    if not date_from or not date_to:
        return qs.none()
        
    cutoff_str = getattr(settings, 'STATISTICS_CUTOFF_DATE', '2026-07-09')
    cutoff_date = parse_date(cutoff_str) or date(2026, 7, 9)
    
    if date_to < cutoff_date:
        return qs.filter(
            methodology='HISTORICAL_LEGACY',
            reference_year__gte=date_from.year,
            reference_year__lte=date_to.year
        )
        
    if date_from >= cutoff_date:
        return qs.filter(
            methodology='SIED_OPERATIONAL',
            reference_date__gte=date_from,
            reference_date__lte=date_to
        )
        
    return qs.filter(
        Q(
            methodology='HISTORICAL_LEGACY',
            reference_year__gte=date_from.year,
            reference_year__lte=cutoff_date.year
        ) | Q(
            methodology='SIED_OPERATIONAL',
            reference_date__gte=cutoff_date,
            reference_date__lte=date_to
        )
    )


def build_category_key(indicator, action, entity):
    cat_name = action or entity or "Geral"
    return f"{indicator} - {cat_name}"

class StatisticsSummaryView(APIView):
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        date_from = parse_date(request.query_params.get('date_from'))
        date_to = parse_date(request.query_params.get('date_to'))
        
        if not date_from or not date_to:
            return Response({"error": "date_from and date_to are required"}, status=400)
            
        qs = get_hybrid_queryset(date_from, date_to)
        
        totals = aggregate_official_statistics(qs)
        response_data = [
            {"indicator": key.split(' - ', 1)[0], "category": key,
             "value": value, "methodology": "OFFICIAL_HYBRID"}
            for key, value in totals.items()
        ]
            
        return Response(response_data)


class StatisticsComparisonView(APIView):
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        date_from = parse_date(request.query_params.get('date_from'))
        date_to = parse_date(request.query_params.get('date_to'))
        prev_date_from = parse_date(request.query_params.get('prev_date_from'))
        prev_date_to = parse_date(request.query_params.get('prev_date_to'))
        
        if not all([date_from, date_to, prev_date_from, prev_date_to]):
            return Response({"error": "Missing date parameters"}, status=400)
            
        current_qs = get_hybrid_queryset(date_from, date_to)
        prev_qs = get_hybrid_queryset(prev_date_from, prev_date_to)
        
        # Agregador Dinâmico
        current_totals = aggregate_official_statistics(current_qs)
        prev_totals = aggregate_official_statistics(prev_qs)
        
        indicators = set(current_totals.keys()).union(prev_totals.keys())
        variations = {}
        
        for ind in indicators:
            curr_val = current_totals.get(ind, 0)
            prev_val = prev_totals.get(ind, 0)
            
            if prev_val == 0 and curr_val > 0:
                variations[ind] = {"variation": None, "status": "NEW_DATA"}
            elif prev_val == 0 and curr_val == 0:
                variations[ind] = {"variation": 0.0, "status": "NO_CHANGE"}
            else:
                pct = ((curr_val - prev_val) / prev_val) * 100
                variations[ind] = {"variation": round(pct, 2), "status": "CALCULATED"}
                
        # Total Macro Indicators (AUDIENCE, ACTION, MATERIAL)
        macro_keys = {
            'AUDIENCE': 'AUDIENCE - Geral',
            'ACTION': 'ACTION - Geral',
            'MATERIAL': 'MATERIAL - Geral',
        }
        macro_current = {name: current_totals[key] for name, key in macro_keys.items()}
        macro_prev = {name: prev_totals[key] for name, key in macro_keys.items()}
        macro_var = {}
        
        for ind_type in macro_current.keys():
            macro_current[ind_type] = current_totals[macro_keys[ind_type]]
            macro_prev[ind_type] = prev_totals[macro_keys[ind_type]]
            
            p_val = macro_prev[ind_type]
            c_val = macro_current[ind_type]
            if p_val == 0 and c_val > 0:
                macro_var[ind_type] = {"variation": None, "status": "NEW_DATA"}
            elif p_val == 0 and c_val == 0:
                macro_var[ind_type] = {"variation": 0.0, "status": "NO_CHANGE"}
            else:
                macro_var[ind_type] = {"variation": round(((c_val - p_val) / p_val) * 100, 2), "status": "CALCULATED"}
                
        return Response({
            "current_period": current_totals,
            "previous_period": prev_totals,
            "variations": variations,
            "macro_current": macro_current,
            "macro_prev": macro_prev,
            "macro_variations": macro_var
        })


class StatisticsHistoricalSeriesView(APIView):
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        response_data = []
        years = ConsolidatedStatistic.objects.filter(status='ACTIVE').values_list(
            'reference_year', flat=True
        ).distinct().order_by('reference_year')
        for year in years:
            totals = aggregate_official_statistics(
                get_hybrid_queryset(date(year, 1, 1), date(year, 12, 31))
            )
            for key, value in totals.items():
                response_data.append({
                    "year": year,
                    "indicator": key.split(' - ', 1)[0],
                    "category": key,
                    "methodology": "OFFICIAL_HYBRID",
                    "value": value,
                })
        return Response(response_data)

class StatisticsDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.statistics.dashboard import dashboard_payload
        today = date.today()
        date_from = parse_date(request.query_params.get('date_from')) or date(today.year, 1, 1)
        date_to = parse_date(request.query_params.get('date_to')) or today
        if date_from > date_to:
            return Response({'error': 'A data inicial não pode ser posterior à data final.'}, status=400)
        filters = {
            key: request.query_params.get(key, '').strip()
            for key in ('municipality', 'team', 'institution', 'entity', 'action_type')
        }
        return Response(dashboard_payload(date_from, date_to, filters))


class StatisticsDashboardFiltersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.schedules.models import EducationReport
        reports = EducationReport.objects.filter(
            status=EducationReport.ReportStatus.APPROVED,
            statistics_processed=True,
        )
        return Response({
            'municipalities': list(reports.exclude(agenda__city='').values_list('agenda__city', flat=True).distinct().order_by('agenda__city')),
            'teams': list(reports.exclude(team='').values_list('team', flat=True).distinct().order_by('team')),
            'entities': list(reports.exclude(agenda__requester_entity_type='').values_list('agenda__requester_entity_type', flat=True).distinct().order_by('agenda__requester_entity_type')),
            'institutions': list(reports.exclude(actions__institution_name='').values_list('actions__institution_name', flat=True).distinct().order_by('actions__institution_name')[:500]),
            'action_types': list(reports.exclude(actions__type_action='').values_list('actions__type_action', flat=True).distinct().order_by('actions__type_action')),
        })


class StatisticsDashboardCsvView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import csv
        from django.http import HttpResponse
        from apps.statistics.dashboard import dashboard_payload
        today = date.today()
        date_from = parse_date(request.query_params.get('date_from')) or date(today.year, 1, 1)
        date_to = parse_date(request.query_params.get('date_to')) or today
        filters = {key: request.query_params.get(key, '').strip() for key in ('municipality', 'team', 'institution', 'entity', 'action_type')}
        payload = dashboard_payload(date_from, date_to, filters)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="estatisticas-sied.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Ano', 'Indicador', 'Valor'])
        for row in payload['annual']:
            for indicator, value in row['values'].items():
                writer.writerow([row['year'], indicator, value])
        return response
