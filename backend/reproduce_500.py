import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.schedules.models import EducationReport, Agenda, Sector
from apps.schedules.serializers import EducationReportSerializer
from django.contrib.auth import get_user_model
User = get_user_model()

try:
    user = User.objects.create(email="test500@ex.com", role="AGENT", full_name="Test")
except Exception:
    user = User.objects.filter(email="test500@ex.com").first()

try:
    sector = Sector.objects.create(name="Test Sector")
except Exception:
    sector = Sector.objects.first()

try:
    agenda = Agenda.objects.create(title="Test", date="2026-07-20", start_time="10:00", end_time="12:00", sector=sector, created_by=user, responsible=user)
except Exception:
    agenda = Agenda.objects.first()

payload = {
    "source": "LOCAL",
    "agenda": agenda.id,
    "operation_date": "2026-07-20",
    "team": "Equipe 1",
    "actions": [
        {
            "type_action": "Blitz Educativa",
            "place_action": "Rua 1",
            "public_action": "Pedestres",
            "quantity_action": 10
        }
    ]
}

serializer = EducationReportSerializer(data=payload)
if serializer.is_valid():
    try:
        report = serializer.save(created_by=user, status="DRAFT")
        print("Success!")
    except Exception as e:
        print("Error on save:")
        traceback.print_exc()
else:
    print("Serializer errors:", serializer.errors)
