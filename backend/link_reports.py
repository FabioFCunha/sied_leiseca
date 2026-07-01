import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.schedules.models import EducationReport, Agenda

team_map = {
    'A': 'ALFA', 'B': 'BRAVO', 'C': 'CHARLIE', 'D': 'DELTA', 
    'E': 'ECHO', 'F': 'FOX', 'G': 'GOLF', 'H': 'HOTEL', 
    'I': 'INDIA', 'J': 'JULIET', 'K': 'KILO', 'L': 'LIMA', 'M': 'MIKE'
}

reports = EducationReport.objects.filter(agenda__isnull=True)
linked = 0
for r in reports:
    r_team = team_map.get(r.team, r.team).lower()
    agendas = Agenda.objects.filter(date=r.operation_date)
    agendas = [a for a in agendas if (a.sector and a.sector.name.lower().startswith(r_team)) or a.team_name.lower().startswith(r_team)]
    if agendas:
        r.agenda = agendas[0]
        r.save()
        linked += 1

print(f'Linked: {linked}')
