# -*- coding: utf-8 -*-
with open('apps/schedules/tests/test_report_workflow.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Fix string 1
content = re.sub(
    r'Apenas relat.rios aguardando confer.ncia podem ser aprovados\.',
    'Apenas relatórios aguardando conferência podem ser aprovados.',
    content
)

# Fix string 2
content = re.sub(
    r'J. existe um relat.rio t.cnico',
    'Já existe um relatório técnico',
    content
)

with open('apps/schedules/tests/test_report_workflow.py', 'w', encoding='utf-8') as f:
    f.write(content)
