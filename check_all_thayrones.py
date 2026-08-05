import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.accounts.models import User
users = User.objects.filter(full_name__icontains="Thayrone")
for u in users:
    print(f"ID: {u.id}, Name: {u.full_name}, Email: {u.email}, CPF: {u.cpf}, Role: {u.role}, Active: {u.is_active}, Sector: {u.sector.name if u.sector else None}")
"""

command = 'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
