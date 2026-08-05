# -*- coding: utf-8 -*-
import re
with open('apps/schedules/tests/test_report_workflow.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'Apenas relat.*?aprovados\.', 'Apenas relatórios aguardando conferência podem ser aprovados.', content)
content = re.sub(r'J.*? existe um relat.*?cnico', 'Já existe um relatório técnico', content)

with open('apps/schedules/tests/test_report_workflow.py', 'w', encoding='utf-8') as f:
    f.write(content)
