import sys

with open('frontend/src/pages/TechnicalReportsPage.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith('  return ('):
        lines[i] = '  return (\n    <>\n'
        break

for i in range(len(lines)-1, -1, -1):
    if lines[i].startswith('  );'):
        lines[i] = '    </>\n  );\n'
        break

start_idx = -1
for i, line in enumerate(lines):
    if '{isAttendanceModalOpen && (' in line:
        start_idx = i
        break

if start_idx != -1:
    end_idx = -1
    open_brackets = 0
    for i in range(start_idx, len(lines)):
        open_brackets += lines[i].count('{')
        open_brackets -= lines[i].count('}')
        if open_brackets == 0:
            end_idx = i
            break
    
    modal_block = lines[start_idx:end_idx+1]
    del lines[start_idx:end_idx+1]
    
    for i in range(len(lines)-1, -1, -1):
        if lines[i].strip() == '</>':
            lines = lines[:i] + modal_block + lines[i:]
            break

for i, line in enumerate(lines):
    if '<div className="modal-backdrop">' in line:
        lines[i] = line.replace('<div className="modal-backdrop">', '<div className="modal-backdrop" style={{ zIndex: 9999 }}>')
    if '<div className="modal-content" style={{ width: "600px", maxWidth: "95%" }}>' in line:
        lines[i] = line.replace('<div className="modal-content" style={{ width: "600px", maxWidth: "95%" }}>', '<article className="modal" style={{ width: "600px", maxWidth: "95%", display: "flex", flexDirection: "column", padding: "20px" }} onClick={(e) => e.stopPropagation()}>')

    if lines[i].strip() == '</div>' and i > 1000 and lines[i-1].strip() == '}':
        if '</div>' in lines[i+1]:
            lines[i] = '          </article>\n'

with open('frontend/src/pages/TechnicalReportsPage.jsx', 'w', encoding='utf-8') as f:
    f.writelines(lines)
