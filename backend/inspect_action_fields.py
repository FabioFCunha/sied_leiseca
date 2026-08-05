import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.schedules.models import EducationAction
from django.db.models import Sum

print("Sum of distributed_certificates:", EducationAction.objects.aggregate(Sum('distributed_certificates')))
print("Sum of gibis:", EducationAction.objects.aggregate(Sum('gibis')))
print("Sum of folders:", EducationAction.objects.aggregate(Sum('distributed_folders')))
print("Sum of publicity_materials:", EducationAction.objects.aggregate(Sum('publicity_materials')))
