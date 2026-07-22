import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.schedules.models import Agenda
agendas = Agenda.objects.filter(title="AppSheet - Sem Título")
print(f"Found {agendas.count()} agendas to fix.")

updated = 0
for agenda in agendas:
    new_title_suffix = agenda.team_name or agenda.action_type or "Sem Título"
    agenda.title = f"AppSheet - {new_title_suffix}"
    if len(agenda.title) > 175:
        agenda.title = agenda.title[:175] + "..."
    agenda.save(update_fields=['title'])
    updated += 1

print(f"Successfully updated {updated} agendas.")
"""

command = f'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
