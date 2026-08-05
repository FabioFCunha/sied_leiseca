import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.schedules.models import Agent
from apps.accounts.models import User

thayrone = User.objects.filter(full_name__icontains="Thayrone").first()
print(f"User ID: {thayrone.id}, CPF: {thayrone.cpf}")

agents = Agent.objects.filter(name__icontains="Thayrone")
for a in agents:
    print(f"Agent ID: {a.id}, Name: {a.name}, CPF: {a.cpf}, Team: {a.team.name if a.team else None}, Source ID: {a.source_id}")

from apps.schedules.models import Chief, Support
chiefs = Chief.objects.filter(name__icontains="Thayrone")
for c in chiefs:
    print(f"Chief ID: {c.id}, Name: {c.name}, CPF: {c.cpf}, Team: {c.team.name if c.team else None}, Source ID: {c.source_id}")

supports = Support.objects.filter(name__icontains="Thayrone")
for s in supports:
    print(f"Support ID: {s.id}, Name: {s.name}, CPF: {s.cpf}, Team: {s.team.name if s.team else None}, Source ID: {s.source_id}")

"""

command = 'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
