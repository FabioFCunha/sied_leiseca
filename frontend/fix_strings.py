import io

pdf_file = r'd:\agenda_eventos_ols\frontend\src\utils\reportPdfGenerator.js'

with open(pdf_file, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

replacements = {
    # Specific ones requested by user
    "LEI SECA EDUCAÃ‡ÃƒO": "LEI SECA EDUCAÇÃO",
    "Sistema Integrado da EducaÃ§Ã£o â€“ SIED": "Sistema Integrado da Educação – SIED",
    "PÃ¡gina": "Página",
    "RELATÃ“RIO TÃ‰CNICO DE ATIVIDADE": "RELATÓRIO TÉCNICO DE ATIVIDADE",
    "IdentificaÃ§Ã£o da atividade": "Identificação da atividade",
    
    # Generic broken char replacements
    "Educao": "Educação",
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
    "FREQUNCIA": "FREQUÊNCIA",
    "Funo": "Função",
    "funo": "função",
    "AO": "AÇÃO",
    "Ao": "Ação",
    "ao": "ação",
    "aes": "ações",
    "Aes": "Ações",
    "Alcanado": "Alcançado",
    "alcanado": "alcançado",
    "Estimado": "Estimado",
    "Distribudo": "Distribuído",
    "distribudo": "distribuído",
    "distribudos": "distribuídos",
    "Ocorrncia": "Ocorrência",
    "ocorrncia": "ocorrência",
    "OCORRNCIA": "OCORRÊNCIA",
    "ocorrncias": "ocorrências",
    "Descrio": "Descrição",
    "Descrio": "Descrição",
    "Providncias": "Providências",
    "providncias": "providências",
    "Observaes": "Observações",
    "Observaes": "Observações",
    "observaes": "observações",
    "OBSERVAES": "OBSERVAÇÕES",
    "Concluso": "Conclusão",
    "CONCLUSO": "CONCLUSÃO",
    "Validao": "Validação",
    "Validao": "Validação",
    "informaes": "informações",
    "informaes": "informações",
    "execuo": "execução",
    "execuo": "execução",
    "Etilmetros": "Etilômetros",
    " atividade": "à atividade",
}

for old, new in replacements.items():
    text = text.replace(old, new)

with open(pdf_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Replaced strings successfully.")
