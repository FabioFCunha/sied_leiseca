import os

path = 'apps/schedules/views.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('EducationReport.ReportStatus.SUBMITTED', 'EducationReport.ReportStatus.APPROVED')
content = content.replace('technical_reports__status="SUBMITTED"', 'technical_reports__status="APPROVED"')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
