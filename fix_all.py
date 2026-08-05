# -*- coding: utf-8 -*-
import re

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix views.py double encoding
    content = content.replace('JÃ¡', 'Já')
    content = content.replace('relatÃ³rio', 'relatório')
    content = content.replace('RelatÃ³rio', 'Relatório')
    content = content.replace('tÃ©cnico', 'técnico')
    content = content.replace('conferÃªncia', 'conferência')
    content = content.replace('frequÃªncia', 'frequência')
    content = content.replace('estatÃ\xadstica', 'estatística')
    content = content.replace('AdministraÃ§Ã£o', 'Administração')
    content = content.replace('solicitaÃ§Ãµes', 'solicitações')
    content = content.replace('mÃºltiplas', 'múltiplas')
    content = content.replace('AprovaÃ§Ã£o', 'Aprovação')
    content = content.replace('DevoluÃ§Ã£o', 'Devolução')
    
    # Fix test_report_workflow.py broken utf-8 chars (\ufffd)
    content = content.replace('J\ufffd existe um relat\ufffdrio t\ufffdcnico', 'Já existe um relatório técnico')
    content = content.replace('Apenas relat\ufffdrios aguardando confer\ufffdncia', 'Apenas relatórios aguardando conferência')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('backend/apps/schedules/views.py')
fix_file('backend/apps/schedules/tests/test_report_workflow.py')
