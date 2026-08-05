import os
import re

pdf_file = r'd:\agenda_eventos_ols\frontend\src\utils\reportPdfGenerator.js'
page_file = r'd:\agenda_eventos_ols\frontend\src\pages\TechnicalReportsPage.jsx'

with open(pdf_file, 'r', encoding='utf-8') as f:
    pdf_content = f.read()

# Fix function name
pdf_content = pdf_content.replace('generatePdfHtml', 'generateTechnicalReportPdf')

# Fix the dynamic block
pdf_content = re.sub(
    r'if\s*\(action\.equipment_materials_distributed\s*&&\s*action\.equipment_materials_distributed\.trim\(\)\)\s*\{[\s\S]*?\}',
    '''if (action.dynamics_applied && action.dynamics_applied.trim()) {
      const din = action.dynamics_applied.replace(/\\n/g, ", ").replace(/\\|/g, "-");
      actionData.push(["Dinâmica aplicada", din]);
    }''',
    pdf_content
)

# Fix any weird UTF-8 just in case
pdf_content = pdf_content.replace('EDUCAÃ‡ÃƒO', 'EDUCAÇÃO')
pdf_content = pdf_content.replace('RELATÃ“RIO', 'RELATÓRIO')
pdf_content = pdf_content.replace('PÃºblico', 'Público')
pdf_content = pdf_content.replace('OcorrÃªncia', 'Ocorrência')
pdf_content = pdf_content.replace('PÃ¡gina', 'Página')

with open(pdf_file, 'w', encoding='utf-8') as f:
    f.write(pdf_content)


with open(page_file, 'r', encoding='utf-8') as f:
    page_content = f.read()

page_content = page_content.replace('generatePdfHtml', 'generateTechnicalReportPdf')
page_content = page_content.replace('Dinǽmica', 'Dinâmica')
page_content = page_content.replace('distribuda', 'distribuída')
page_content = page_content.replace('distribudo', 'distribuído')

# Fix applyAgenda to populate dynamics_applied
old_apply = '''    const initialEquipment = serializeMaterialRows([...selectedMaterials.dynamics, ...selectedMaterials.supports]);'''
new_apply = '''    const initialEquipment = serializeMaterialRows(selectedMaterials.supports);
    const initialDynamics = serializeMaterialRows(selectedMaterials.dynamics);'''
page_content = page_content.replace(old_apply, new_apply)

old_action = '''        equipment_materials_removed: currentAction.equipment_materials_removed || initialEquipment,
        equipment_materials_distributed: currentAction.equipment_materials_distributed || initialEquipment,'''
new_action = '''        equipment_materials_removed: currentAction.equipment_materials_removed || initialEquipment,
        equipment_materials_distributed: currentAction.equipment_materials_distributed || initialEquipment,
        dynamics_applied: currentAction.dynamics_applied || initialDynamics,'''
page_content = page_content.replace(old_action, new_action)

# Fix the emptyAction
old_empty = '''  equipment_materials_distributed: "","'''.strip()
new_empty = '''  equipment_materials_distributed: "",
  dynamics_applied: "","''.strip()
page_content = page_content.replace(old_empty, new_empty)

# Fix the UI block
old_ui = '''                  const handleDynDist = (val) => {
                    const combined = [val, supDist].filter(Boolean).join("\\n");
                    updateAction(index, "equipment_materials_distributed", combined);
                  };
                  const handleSupDist = (val) => {
                    const combined = [dynDist, val].filter(Boolean).join("\\n");
                    updateAction(index, "equipment_materials_distributed", combined);
                  };'''

new_ui = '''                  const handleDynDist = (val) => {
                    updateAction(index, "dynamics_applied", val);
                  };
                  const handleSupDist = (val) => {
                    updateAction(index, "equipment_materials_distributed", val);
                  };'''
page_content = page_content.replace(old_ui, new_ui)

# Make sure UI shows dynamics_applied instead of dynDist
page_content = page_content.replace('dynDist || cats.dynamics.join("\\n")', 'action.dynamics_applied || cats.dynamics.join("\\n")')
page_content = page_content.replace('supDist || cats.supports.join("\\n")', 'action.equipment_materials_distributed || cats.supports.join("\\n")')
page_content = page_content.replace('supRem || cats.supports.join("\\n")', 'action.equipment_materials_removed || cats.supports.join("\\n")')


with open(page_file, 'w', encoding='utf-8') as f:
    f.write(page_content)

print("Done")
