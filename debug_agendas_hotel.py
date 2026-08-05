import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.schedules.models import Agenda
from django.db.models import Q

# Check exact team names in Agenda
team_names = Agenda.objects.filter(team_name__icontains='hotel').values_list('team_name', flat=True).distinct()
print("Agenda team_names matching 'hotel':", [f"'{t}'" for t in team_names])

# Check what agendas Thayrone would see
from apps.accounts.models import User
thayrone = User.objects.filter(full_name__icontains='Thayrone').first()
if thayrone:
    from apps.schedules.permissions import agent_agenda_filter
    from django.db.models import Count
    agendas = Agenda.objects.filter(agent_agenda_filter(thayrone))
    print(f"Thayrone can see {agendas.count()} agendas.")
    
    # Check just the team_agenda_filter
    from apps.schedules.permissions import team_agenda_filter
    agendas_team = Agenda.objects.filter(team_agenda_filter(thayrone))
    print(f"Thayrone can see {agendas_team.count()} agendas via team_agenda_filter.")
    
    # Let's see how many agendas there are for his sector name exactly
    exact = Agenda.objects.filter(Q(team_ref__name=thayrone.sector.name) | Q(team_name=thayrone.sector.name))
    print(f"Agendas matching exact case: {exact.count()}")
    
    iexact = Agenda.objects.filter(Q(team_ref__name__iexact=thayrone.sector.name) | Q(team_name__iexact=thayrone.sector.name))
    print(f"Agendas matching iexact case: {iexact.count()}")
"""

command = 'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
