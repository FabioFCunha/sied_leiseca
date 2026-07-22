import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

cmd = """
from apps.schedules.models import ShiftSchedule, Agenda
from apps.reports.models import EducationReport

ids = [5485, 5474, 5537, 5536, 5484, 5562]
for obj_id in ids:
    print(f"ID {obj_id}:")
    try:
        a = Agenda.objects.get(id=obj_id)
        print(f"  - Agenda: {a.date} - {a.event_name}")
    except Exception:
        pass
    try:
        r = EducationReport.objects.get(id=obj_id)
        print(f"  - EducationReport: {r.status} - Agenda ID: {r.agenda_id}")
    except Exception:
        pass
    try:
        s = ShiftSchedule.objects.get(id=obj_id)
        print(f"  - ShiftSchedule: {s.date} - {s.team.name if s.team else 'No team'}")
    except Exception:
        pass
"""
stdin, stdout, stderr = client.exec_command('docker exec -i sied_backend python manage.py shell')
stdin.write(cmd)
stdin.channel.shutdown_write()

print("STDOUT:", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:", stderr.read().decode('utf-8', errors='ignore'))
