from apps.statistics.models import ConsolidatedStatistic
from django.db import transaction

def generate_statistics_for_report(report):
    """
    Called only when an EducationReport is VALIDATED/APPROVED.
    It extracts data and creates the SIED_OPERATIONAL statistics.
    """
    if report.status != 'APPROVED':
        return
    
    # We clear existing stats for this report just in case to avoid duplicates
    _remove_statistics_for_report(report.id)

    stats_to_create = []
    base_kwargs = {
        'methodology': 'SIED_OPERATIONAL',
        'traceability_id': f'report_{report.id}',
        'reference_date': report.created_at.date(), # Or date of the agenda if available
        'reference_year': report.created_at.year,
        'reference_month': report.created_at.month,
    }

    # Example extracting Audience
    # Assumes report has a total_audience field or we calculate it
    # This is a placeholder structure, exact fields depend on the actual EducationReport model.
    total_audience = getattr(report, 'audience_total', 0)
    if total_audience > 0:
        stats_to_create.append(ConsolidatedStatistic(
            indicator_type='AUDIENCE',
            value=total_audience,
            **base_kwargs
        ))

    # Save to db
    if stats_to_create:
        ConsolidatedStatistic.objects.bulk_create(stats_to_create)

def update_statistics_for_report(report):
    """
    Called when an approved report is rectified/edited.
    Re-generates its statistics.
    """
    generate_statistics_for_report(report)

def remove_statistics_for_report(report):
    """
    Called when a report is cancelled or un-approved.
    """
    _remove_statistics_for_report(report.id)

def _remove_statistics_for_report(report_id):
    ConsolidatedStatistic.objects.filter(
        methodology='SIED_OPERATIONAL',
        traceability_id=f'report_{report_id}'
    ).delete()
