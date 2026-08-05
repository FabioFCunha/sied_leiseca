import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.schedules.models import Agenda, Team, Sector

print("Agendas without team_ref:", Agenda.objects.filter(team_ref__isnull=True).exclude(team_name="").count())
print("Agendas without sector:", Agenda.objects.filter(sector__isnull=True).exclude(team_name="").count())

teams = {t.name.upper(): t for t in Team.objects.all()}
sectors = {s.name.upper(): s for s in Sector.objects.all()}

updated = 0
for agenda in Agenda.objects.filter(team_ref__isnull=True).exclude(team_name=""):
    t_name = agenda.team_name.upper().strip()
    team = teams.get(t_name)
    sector = sectors.get(t_name)
    
    if team or sector:
        if team:
            agenda.team_ref = team
        if sector:
            agenda.sector = sector
        agenda.save(update_fields=['team_ref', 'sector'])
        updated += 1

print(f"Updated {updated} agendas with team_ref/sector.")
"""

command = 'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
