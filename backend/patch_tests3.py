# -*- coding: utf-8 -*-
with open('apps/schedules/tests/test_report_workflow.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('Apenas relatrios aguardando conferncia podem ser aprovados.', 'Apenas relatórios aguardando conferência podem ser aprovados.')
content = content.replace('J existe um relatrio tcnico', 'Já existe um relatório técnico')

with open('apps/schedules/tests/test_report_workflow.py', 'w', encoding='utf-8') as f:
    f.write(content)
