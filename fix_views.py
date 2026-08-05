# -*- coding: utf-8 -*-
with open('backend/apps/schedules/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

try:
    content = content.encode('cp1252').decode('utf-8')
except Exception as e:
    print('Error:', e)
    # Just fix the specific strings
    content = content.replace('relatÃ³rio', 'relatório')
    content = content.replace('RelatÃ³rio', 'Relatório')
    content = content.replace('conferÃªncia', 'conferência')
    content = content.replace('frequÃªncia', 'frequência')
    content = content.replace('estatÃ\xadstica', 'estatística')
    content = content.replace('AdministraÃ§Ã£o', 'Administração')
    content = content.replace('solicitaÃ§Ãµes', 'solicitações')
    content = content.replace('mÃºltiplas', 'múltiplas')
    content = content.replace('tÃ©cnico', 'técnico')

with open('backend/apps/schedules/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
