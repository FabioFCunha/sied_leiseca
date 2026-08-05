# -*- coding: utf-8 -*-
with open('apps/schedules/tests/test_report_workflow.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Fix string 1
content = re.sub(
    r'Apenas relat\ufffdrios aguardando confer\ufffdncia podem ser aprovados\.',
    'Apenas relatórios aguardando conferência podem ser aprovados.',
    content
)

# Fix string 2
content = re.sub(
    r'J\ufffd existe um relat\ufffdrio t\ufffdcnico',
    'Já existe um relatório técnico',
    content
)

with open('apps/schedules/tests/test_report_workflow.py', 'w', encoding='utf-8') as f:
    f.write(content)
