# -*- coding: utf-8 -*-
lines = open('apps/schedules/tests/test_report_workflow.py', 'r', encoding='utf-8').readlines()
lines[109] = '        self.assertEqual(response2.data["detail"], "Apenas relatórios aguardando conferência podem ser aprovados.")\n'
lines[120] = '        self.assertEqual(response.data["detail"], "Apenas relatórios aguardando conferência podem ser aprovados.")\n'
lines[261] = '        self.assertIn("Já existe um relatório técnico", str(response2.data))\n'

with open('apps/schedules/tests/test_report_workflow.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
