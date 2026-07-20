import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.abspath('e:\\agenda_eventos_ols\\backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.schedules.models import EducationReport, ShiftSchedule
from apps.schedules.services import get_expected_attendance_member_keys

reports = EducationReport.objects.filter(status=EducationReport.ReportStatus.DRAFT)

print(f"Found {reports.count()} DRAFT reports.")

for report in reports:
    schedules = ShiftSchedule.objects.filter(date=report.operation_date)
    if report.agenda and report.agenda.team_ref_id:
        schedules = schedules.filter(team_id=report.agenda.team_ref_id)
    elif report.team:
        schedules = schedules.filter(team__name=report.team)
    
    schedule = schedules.first()
    if not schedule:
        print(f"Report {report.id}: No schedule found.")
        continue

    expected = get_expected_attendance_member_keys(report.agenda, schedule)
    checked = set(schedule.checked_members.keys()) if schedule.checked_members else set()

    missing = expected - checked
    extra = checked - expected
    
    print(f"\n--- Report {report.id} ---")
    print(f"Expected: {expected}")
    print(f"Checked : {checked}")
    if missing:
        print(f"MISSING : {missing}")
    if extra:
        print(f"EXTRA   : {extra}")
