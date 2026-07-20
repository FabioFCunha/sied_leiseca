import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

cmd = """
from apps.users.models import User
from apps.schedules.models import Agent, Team

print("Looking for Pitta...")
users = User.objects.filter(full_name__icontains="PITTA")
for u in users:
    print(f"User: {u.full_name}, CPF: {u.cpf}, Sector: {u.sector.name if u.sector else None}")
    
agents = Agent.objects.filter(name__icontains="PITTA")
for a in agents:
    print(f"Agent: {a.name}, CPF: {a.cpf}, Team: {a.team.name if a.team else None}")
"""
stdin, stdout, stderr = client.exec_command('docker exec -i sied_backend python manage.py shell')
stdin.write(cmd)
stdin.channel.shutdown_write()

print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
