import os

page_file = r'd:\agenda_eventos_ols\frontend\src\pages\TechnicalReportsPage.jsx'
pdf_file = r'd:\agenda_eventos_ols\frontend\src\utils\reportPdfGenerator.js'

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

# payload logic
page = page.replace(
    'equipment_materials_distributed: "",\n  distribution_materials_removed:',
    'equipment_materials_distributed: "",\n  dynamics_applied: "",\n  distribution_materials_removed:'
)

page = page.replace(
    'const initialEquipment = serializeMaterialRows([...selectedMaterials.dynamics, ...selectedMaterials.supports]);',
    'const initialEquipment = serializeMaterialRows(selectedMaterials.supports);\n    const initialDynamics = serializeMaterialRows(selectedMaterials.dynamics);'
)

page = page.replace(
    'equipment_materials_distributed: currentAction.equipment_materials_distributed || initialEquipment,\n        distribution_materials_removed:',
    'equipment_materials_distributed: currentAction.equipment_materials_distributed || initialEquipment,\n        dynamics_applied: currentAction.dynamics_applied || initialDynamics,\n        distribution_materials_removed:'
)

with open(page_file, 'w', encoding='utf-8') as f:
    f.write(page)


with open(pdf_file, 'r', encoding='utf-8') as f:
    pdf = f.read()

# fix the broken doc init
pdf = pdf.replace(
    'export async function generateTechnicalReportPdf(form, selectedAgenda, attendanceForm) {\n    orientation: "portrait",',
    'export async function generateTechnicalReportPdf(form, selectedAgenda, attendanceForm) {\n  const doc = new jsPDF({\n    orientation: "portrait",'
)

pdf = pdf.replace('generatePdfHtml', 'generateTechnicalReportPdf')

pdf = pdf.replace(
    'if (action.equipment_materials_distributed && action.equipment_materials_distributed.trim()) {',
    'if (action.dynamics_applied && action.dynamics_applied.trim()) {'
)
pdf = pdf.replace(
    'const din = action.equipment_materials_distributed.replace',
    'const din = action.dynamics_applied.replace'
)
pdf = pdf.replace(
    'actionData.push(["Dinâmica utilizada", din]);',
    'actionData.push(["Dinâmica aplicada", din]);'
)

# Fix UTF-8 strings
pdf = pdf.replace('EDUCAÃ‡ÃƒO', 'EDUCAÇÃO')
pdf = pdf.replace('RELATÃ“RIO', 'RELATÓRIO')
pdf = pdf.replace('PÃºblico', 'Público')
pdf = pdf.replace('OcorrÃªncia', 'Ocorrência')
pdf = pdf.replace('PÃ¡gina', 'Página')

with open(pdf_file, 'w', encoding='utf-8') as f:
    f.write(pdf)

print("Done")
