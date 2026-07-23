from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, date
from django.db.models import Sum, Q
from apps.statistics.models import ConsolidatedStatistic

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
        
        summary_data = qs.values(
            'indicator_type', 
            'category_action_type__name', 
            'category_entity_type', 
            'methodology'
        ).annotate(total=Sum('value'))
        
        response_data = []
        for item in summary_data:
            key = build_category_key(
                item['indicator_type'], 
                item['category_action_type__name'], 
                item['category_entity_type']
            )
            response_data.append({
                "indicator": item['indicator_type'],
                "category": key,
                "value": float(item['total'] or 0),
                "methodology": item['methodology']
            })
            
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
        def aggregate_totals(qs):
            raw = qs.values('indicator_type', 'category_action_type__name', 'category_entity_type').annotate(total=Sum('value'))
            totals = {}
            for item in raw:
                key = build_category_key(item['indicator_type'], item['category_action_type__name'], item['category_entity_type'])
                totals[key] = totals.get(key, 0) + float(item['total'] or 0)
            return totals
            
        current_totals = aggregate_totals(current_qs)
        prev_totals = aggregate_totals(prev_qs)
        
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
        macro_current = { 'AUDIENCE': 0, 'ACTION': 0, 'MATERIAL': 0 }
        macro_prev = { 'AUDIENCE': 0, 'ACTION': 0, 'MATERIAL': 0 }
        macro_var = {}
        
        for ind_type in macro_current.keys():
            macro_current[ind_type] = sum(v for k, v in current_totals.items() if k.startswith(ind_type))
            macro_prev[ind_type] = sum(v for k, v in prev_totals.items() if k.startswith(ind_type))
            
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
        qs = ConsolidatedStatistic.objects.filter(status='ACTIVE').order_by('reference_year')
        
        series = qs.values(
            'reference_year', 
            'indicator_type', 
            'category_action_type__name', 
            'category_entity_type', 
            'methodology'
        ).annotate(total=Sum('value'))
        
        response_data = []
        for item in series:
            key = build_category_key(
                item['indicator_type'], 
                item['category_action_type__name'], 
                item['category_entity_type']
            )
            response_data.append({
                "year": item['reference_year'],
                "indicator": item['indicator_type'],
                "category": key,
                "methodology": item['methodology'],
                "value": float(item['total'] or 0)
            })
            
        return Response(response_data)
