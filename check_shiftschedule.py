import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

py_script = """
from apps.schedules.models import ShiftSchedule
from apps.accounts.models import User
thayrone = User.objects.filter(full_name__icontains="Thayrone").first()
if thayrone:
    from apps.schedules.views import ShiftScheduleViewSet
    from rest_framework.test import APIRequestFactory
    factory = APIRequestFactory()
    request = factory.get("/api/schedules/shift-schedules/")
    request.user = thayrone
    view = ShiftScheduleViewSet()
    view.request = request
    view.action = "list"
    view.format_kwarg = None
    qs = view.get_queryset()
    print(f"Thayrone can see {qs.count()} shift schedules in API.")
    print("Dates:", sorted(list(qs.values_list('date', flat=True)[:10])))
"""

command = 'docker exec -i sied_backend python manage.py shell'
stdin, stdout, stderr = client.exec_command(command)
stdin.write(py_script)
stdin.channel.shutdown_write()

print('OUT:', stdout.read().decode('utf-8'))
print('ERR:', stderr.read().decode('utf-8'))
client.close()
