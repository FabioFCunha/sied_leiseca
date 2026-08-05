# -*- coding: utf-8 -*-
import re
with open('apps/schedules/tests/test_report_workflow.py', 'r', encoding='utf-8') as f:
    content = f.read()

m1 = re.search(r'Apenas relat.*?aprovados\.', content)
if m1:
    content = content.replace(m1.group(0), 'Apenas relatórios aguardando conferência podem ser aprovados.')

m2 = re.search(r'J.*? existe um relat.*?rio t.*?cnico', content)
if m2:
    content = content.replace(m2.group(0), 'Já existe um relatório técnico')

with open('apps/schedules/tests/test_report_workflow.py', 'w', encoding='utf-8') as f:
    f.write(content)
