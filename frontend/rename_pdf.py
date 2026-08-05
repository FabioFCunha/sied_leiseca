import os

page_file = r'd:\agenda_eventos_ols\frontend\src\pages\TechnicalReportsPage.jsx'

with open(page_file, 'r', encoding='utf-8') as f:
    page = f.read()

page = page.replace(
    'import { generatePdfHtml } from "../utils/reportPdfGenerator.js";',
    'import { generateTechnicalReportPdf } from "../utils/reportPdfGenerator.js";'
)
page = page.replace(
    'generatePdfHtml(form, selectedAgenda, attendanceForm)',
    'generateTechnicalReportPdf(form, selectedAgenda, attendanceForm)'
)

with open(page_file, 'w', encoding='utf-8') as f:
    f.write(page)
print("Done")
