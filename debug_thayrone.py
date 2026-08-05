import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.accounts.models import User
from apps.schedules.models import Team, Sector, Agent

user = User.objects.filter(full_name__icontains='Thayrone').first()
if user:
    print(f"User: {user.full_name}")
    print(f"CPF: {user.cpf}")
    print(f"Role: {user.role}")
    print(f"Sector: {user.sector.name if user.sector else 'None'} (ID: {user.sector_id if user.sector else 'None'})")
    
    # Check team matching
    teams = Team.objects.filter(name__iexact=user.sector.name) if user.sector else []
    print(f"Matching Teams for Sector '{user.sector.name if user.sector else ''}': {[t.name for t in teams]}")
    
    agent = Agent.objects.filter(cpf=user.cpf).first()
    if agent:
        print(f"Agent matched by CPF: {agent.name}, Team: {agent.team.name if agent.team else 'None'}")
else:
    print("User not found.")
"""

command = 'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
