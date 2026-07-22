import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

cmd = """
from django.contrib.auth import get_user_model
User = get_user_model()
from apps.schedules.views import ShiftScheduleViewSet
from rest_framework.test import APIRequestFactory

user = User.objects.filter(full_name__icontains="Thayrone").first()
factory = APIRequestFactory()
request = factory.get('/api/shift-schedules/')
request.user = user

view = ShiftScheduleViewSet.as_view({'get': 'list'})
response = view(request)
print("Schedules for Thayrone via API:", len(response.data.get('results', response.data) if hasattr(response.data, 'get') else response.data))
"""
stdin, stdout, stderr = client.exec_command('docker exec -i sied_backend python manage.py shell')
stdin.write(cmd)
stdin.channel.shutdown_write()

print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
