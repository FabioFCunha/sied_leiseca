import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.schedules.models import EducationReport, EducationAction
print("Total reports:", EducationReport.objects.count())
print("Total actions:", EducationAction.objects.count())
print("Approved reports:", EducationReport.objects.filter(status='APPROVED').count())
