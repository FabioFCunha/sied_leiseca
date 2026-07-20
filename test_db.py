import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

cmd = """
from apps.schedules.models import EducationReport
from apps.schedules.emails import send_satisfaction_survey_email, send_report_confirmation_email
try:
    report = EducationReport.objects.filter(status='APPROVED').first()
    if report:
        print("Testing send_satisfaction_survey_email...")
        send_satisfaction_survey_email(report)
        print("Testing send_report_confirmation_email...")
        send_report_confirmation_email(report)
        print("SUCCESS")
    else:
        print("NO REPORT FOUND")
except Exception as e:
    import traceback
    traceback.print_exc()
"""
stdin, stdout, stderr = client.exec_command('docker exec -i sied_backend python manage.py shell')
stdin.write(cmd)
stdin.channel.shutdown_write()

print("STDOUT:", stdout.read().decode('utf-8'))
print("STDERR:", stderr.read().decode('utf-8'))
