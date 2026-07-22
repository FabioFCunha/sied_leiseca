import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.schedules.models import Agenda, AgendaHistory
agendas = Agenda.objects.filter(title__icontains='Sem Título')
print(f'Total agendas com Sem Título: {agendas.count()}')

for agenda in agendas[:5]:
    history = AgendaHistory.objects.filter(agenda=agenda).order_by('-created_at')
    print(f'\\nAgenda {agenda.id} - Current title: {agenda.title}')
    for h in history:
        print(f'  - {h.created_at}: {h.action} -> {h.snapshot.get("title", "No title in snapshot")}')
"""

command = f'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
