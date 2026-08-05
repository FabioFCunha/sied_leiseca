import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.schedules.serializers import EducationActionSerializer

serializer = EducationActionSerializer()

try:
    res = serializer.validate_distribution_materials_distributed("Certificado | 10")
    print("SUCCESS 10:", res)
except Exception as e:
    print("ERROR 10:", e)
