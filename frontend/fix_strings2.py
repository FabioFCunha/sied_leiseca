import io

pdf_file = r'd:\agenda_eventos_ols\frontend\src\utils\reportPdfGenerator.js'

with open(pdf_file, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

replacements = {
    # Exact phrases provided by user (if they exist somehow differently)
    "LEI SECA EDUCAÃ‡ÃƒO": "LEI SECA EDUCAÇÃO",
    "Sistema Integrado da EducaÃ§Ã£o â€“ SIED": "Sistema Integrado da Educação – SIED",
    "PÃ¡gina": "Página",
    "RELATÃ“RIO TÃ‰CNICO DE ATIVIDADE": "RELATÓRIO TÉCNICO DE ATIVIDADE",
    "IdentificaÃ§Ã£o da atividade": "Identificação da atividade",
    
    # Broken with \ufffd
    "EDUCAO": "EDUCAÇÃO",
    "Educao": "Educação",
    "Pgina": "Página",
    "Pblico": "Público",
    "pblico": "público",
    "RELATRIO": "RELATÓRIO",
    "TCNICO": "TÉCNICO",
    "TCNICAS": "TÉCNICAS",
    "tcnicas": "técnicas",
    "Identificao": "Identificação",
    "No": "Não",
    "no": "não",
    "Horrio": "Horário",
    "Instituio": "Instituição",
    "Municpio": "Município",
    "Responsvel": "Responsável",
    "responsvel": "responsável",
    "Frequncia": "Frequência",
    "frequncia": "frequência",
    "FREQNCIA": "FREQUÊNCIA",
    "FREQUNCIA": "FREQUÊNCIA",
    "Funo": "Função",
    "funo": "função",
    "AO": "AÇÃO",
    "Aão": "Ação",
    "Ao": "Ação",
    "ao": "ação",
    "aes": "ações",
    "Aes": "Ações",
    "Alcanado": "Alcançado",
    "alcanado": "alcançado",
    "Distribudo": "Distribuído",
    "distribudo": "distribuído",
    "distribudos": "distribuídos",
    "Ocorrncia": "Ocorrência",
    "ocorrncia": "ocorrência",
    "OCORRNCIA": "OCORRÊNCIA",
    "ocorrncias": "ocorrências",
    "Descrio": "Descrição",
    "Providncias": "Providências",
    "providncias": "providências",
    "Observaes": "Observações",
    "observaes": "observações",
    "OBSERVAES": "OBSERVAÇÕES",
    "Concluso": "Conclusão",
    "CONCLUSO": "CONCLUSÃO",
    "Validao": "Validação",
    "informaes": "informações",
    "execuo": "execução",
    "Etilmetros": "Etilômetros",
    "  atividade": " à atividade",
    "Servio": "Serviço",
}

for old, new in replacements.items():
    text = text.replace(old, new)

with open(pdf_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Replaced strings successfully.")
