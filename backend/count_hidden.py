import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.schedules.models import EducationReport, Agenda

reports_hidden = EducationReport.objects.filter(agenda__date__lt="2026-07-08")
print(f"Relatórios técnicos (EducationReport) ocultos (agenda < 2026-07-08): {reports_hidden.count()}")
for status, name in EducationReport.ReportStatus.choices:
    count = reports_hidden.filter(status=status).count()
    if count > 0:
        print(f" - {name}: {count}")

agendas_hidden = Agenda.objects.filter(technical_reports__isnull=True, date__lt="2026-07-08").exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED])
print(f"Agendas pendentes de relatório ocultas (date < 2026-07-08): {agendas_hidden.count()}")
