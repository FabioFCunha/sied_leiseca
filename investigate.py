import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.core.settings')
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
django.setup()

from apps.schedules.models import EducationReport, Agenda

total_reports = EducationReport.objects.count()
print(f"Total EducationReport: {total_reports}")

agendas_with_street = Agenda.objects.exclude(street_action_details={}).exclude(street_action_details__isnull=True).count()
reports_with_street = EducationReport.objects.exclude(street_action_details={}).exclude(street_action_details__isnull=True).count()
print(f"Agendas with street_action_details: {agendas_with_street}")
print(f"Reports with street_action_details: {reports_with_street}")

agendas_with_request = Agenda.objects.exclude(request_details={}).exclude(request_details__isnull=True).count()
reports_with_request = EducationReport.objects.exclude(request_details={}).exclude(request_details__isnull=True).count()
print(f"Agendas with request_details: {agendas_with_request}")
print(f"Reports with request_details: {reports_with_request}")

from django.db.models import Count
status_counts = EducationReport.objects.values('status').annotate(count=Count('status'))
print("Reports by status:")
for s in status_counts:
    print(f"  {s['status']}: {s['count']}")
