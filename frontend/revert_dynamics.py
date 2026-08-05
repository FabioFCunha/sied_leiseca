import re

page_file = r'd:\agenda_eventos_ols\frontend\src\pages\TechnicalReportsPage.jsx'
pdf_file = r'd:\agenda_eventos_ols\frontend\src\utils\reportPdfGenerator.js'

with open(page_file, 'r', encoding='utf-8') as f:
    page = f.read()

# Remove dynamics_applied from emptyAction
page = page.replace('\n  dynamics_applied: "",', '')

# Revert applyAgenda
page = page.replace(
    'const initialEquipment = serializeMaterialRows(selectedMaterials.supports);\n    const initialDynamics = serializeMaterialRows(selectedMaterials.dynamics);',
    'const initialEquipment = serializeMaterialRows([...selectedMaterials.dynamics, ...selectedMaterials.supports]);'
)

# Revert applyAgenda action assignment
page = page.replace(
    '\n        dynamics_applied: currentAction.dynamics_applied || initialDynamics,',
    ''
)

with open(page_file, 'w', encoding='utf-8') as f:
    f.write(page)


with open(pdf_file, 'r', encoding='utf-8') as f:
    pdf = f.read()

pdf = re.sub(
    r'\s*if\s*\(action\.dynamics_applied\s*&&\s*action\.dynamics_applied\.trim\(\)\)\s*\{[\s\S]*?\}',
    '',
    pdf
)

with open(pdf_file, 'w', encoding='utf-8') as f:
    f.write(pdf)

print("Done")
