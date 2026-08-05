# -*- coding: utf-8 -*-
lines = open('apps/schedules/tests/test_report_workflow.py', 'r', encoding='utf-8').readlines()
with open('apps/schedules/tests/test_report_workflow.py', 'w', encoding='utf-8') as f:
    for line in lines:
        line = line.replace('Apenas relat\ufffdrios aguardando confer\ufffdncia podem ser aprovados.', 'Apenas relatórios aguardando conferência podem ser aprovados.')
        line = line.replace('J\ufffd existe um relat\ufffdrio t\ufffdcnico', 'Já existe um relatório técnico')
        f.write(line)
