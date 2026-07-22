import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

cmd = """
from django.contrib.auth import get_user_model
User = get_user_model()
from apps.schedules.views import ShiftScheduleViewSet
from rest_framework.test import APIRequestFactory, force_authenticate

user = User.objects.filter(full_name__icontains="Thayrone").first()
factory = APIRequestFactory()
request = factory.get('/api/shift-schedules/', {'date_from': '2026-07-01', 'date_to': '2026-07-31'})
force_authenticate(request, user=user)

view = ShiftScheduleViewSet.as_view({'get': 'list'})
try:
    response = view(request)
    if response.status_code != 200:
        print("Error:", response.status_code)
        print(response.data)
    else:
        print("Success!")
        data = response.data.get('results', response.data) if hasattr(response.data, 'get') else response.data
        print(len(data))
except Exception as e:
    import traceback
    traceback.print_exc()
"""
stdin, stdout, stderr = client.exec_command('docker exec -i sied_backend python manage.py shell')
stdin.write(cmd)
stdin.channel.shutdown_write()

print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
