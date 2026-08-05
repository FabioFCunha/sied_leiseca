import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.schedules.models import ShiftSchedule
from apps.schedules.serializers import ShiftScheduleSerializer

schedules = ShiftSchedule.objects.filter(team__name__iexact='HOTEL', date__year=2026, date__month=7)
print("Schedules count:", schedules.count())
has_thayrone = False
for s in schedules:
    data = ShiftScheduleSerializer(s).data
    members = data.get('members', {})
    agents = members.get('agents', [])
    for a in agents:
        if 'Thayrone' in a.get('name', ''):
            has_thayrone = True
            break
            
print("Is Thayrone in any schedule members for July?", has_thayrone)
"""

command = 'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
