import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

cmd = """
from django.contrib.auth import get_user_model
User = get_user_model()
from apps.schedules.views import ShiftScheduleViewSet
from django.test import RequestFactory

user = User.objects.filter(full_name__icontains="Thayrone").first()
request = RequestFactory().get('/api/shift-schedules/')
request.user = user

view = ShiftScheduleViewSet()
view.request = request
qs = view.get_queryset()
print("Schedules for Thayrone via API:", qs.count())
"""
stdin, stdout, stderr = client.exec_command('docker exec -i sied_backend python manage.py shell')
stdin.write(cmd)
stdin.channel.shutdown_write()

print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
