import json
from django.utils import timezone
from apps.statistics.models import ConsolidatedStatistic
from django.db import transaction

@transaction.atomic
def generate_statistics_for_report(report, processed_by=None):
    """
    Cria ou atualiza as estatísticas operacionais de um relatório.
    """
    if report.status != 'APPROVED':
        return
        
    trace_id = f'report_{report.id}'
    base_kwargs = {
        'methodology': 'SIED_OPERATIONAL',
        'reference_date': report.created_at.date(), # Or date of the agenda if available
        'reference_year': report.created_at.year,
        'reference_month': report.created_at.month,
    }

    # Extract all metrics from the report.
    # In a real scenario, we loop over all report data to generate different indicator metrics.
    # For this example, we'll map audience_total to 'AUDIENCE'.
    metrics_to_sync = []
    
    total_audience = getattr(report, 'audience_total', 0)
    if total_audience > 0:
        metrics_to_sync.append({
            'indicator_type': 'AUDIENCE',
            'category_action_type': None,
            'category_entity_type': None,
            'value': total_audience,
        })
        
    # Find existing ones for this report
    existing_stats = list(ConsolidatedStatistic.objects.select_for_update().filter(
        traceability_id=trace_id
    ))
    
    # Track which ones we touch
    touched_ids = set()

    for m in metrics_to_sync:
        match = next((s for s in existing_stats 
                     if s.indicator_type == m['indicator_type'] 
                     and s.category_action_type == m['category_action_type'] 
                     and s.category_entity_type == m['category_entity_type']), None)
        
        if match:
            # Update existing
            if match.value != m['value'] or match.status != 'ACTIVE':
                # Register audit
                audit_entry = {
                    'changed_at': timezone.now().isoformat(),
                    'changed_by': processed_by.username if processed_by else 'system',
                    'previous_value': float(match.value) if match.value else None,
                    'previous_status': match.status,
                    'new_value': float(m['value']),
                    'new_status': 'ACTIVE'
                }
                
                # Append to history
                if not isinstance(match.audit_history, list):
                    match.audit_history = []
                match.audit_history.append(audit_entry)
                
                match.value = m['value']
                match.status = 'ACTIVE'
                match.processed_by = processed_by
                match.processed_at = timezone.now()
                match.save()
            
            touched_ids.add(match.id)
        else:
            # Create new
            new_stat = ConsolidatedStatistic.objects.create(
                traceability_id=trace_id,
                indicator_type=m['indicator_type'],
                category_action_type=m['category_action_type'],
                category_entity_type=m['category_entity_type'],
                value=m['value'],
                status='ACTIVE',
                processed_by=processed_by,
                processed_at=timezone.now(),
                **base_kwargs
            )
            touched_ids.add(new_stat.id)
            
    # For existing stats not in the current payload, we suspend them
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

@transaction.atomic
def update_statistics_for_report(report, processed_by=None):
    generate_statistics_for_report(report, processed_by)

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
