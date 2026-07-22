import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

cmd = """
from apps.schedules.models import ShiftSchedule, Agenda, EducationReport

ids = [5485, 5474, 5537, 5536, 5484, 5562]
for obj_id in ids:
    try:
        r = EducationReport.objects.filter(agenda_id=obj_id).first()
        if r:
            r.delete()
            print(f"Deleted EducationReport for Agenda {obj_id}")
    except Exception as e:
        print(f"Error deleting report {obj_id}: {e}")
        pass
    
    try:
        a = Agenda.objects.get(id=obj_id)
        a.delete()
        print(f"Deleted Agenda {obj_id}")
    except Exception as e:
        print(f"Error deleting Agenda {obj_id}: {e}")
        pass
"""
stdin, stdout, stderr = client.exec_command('docker exec -i sied_backend python manage.py shell')
stdin.write(cmd)
stdin.channel.shutdown_write()

print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
