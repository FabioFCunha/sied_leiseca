import io

pdf_file = r'd:\agenda_eventos_ols\frontend\src\utils\reportPdfGenerator.js'

with open(pdf_file, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

replacements = {
    # Provide the exact \ufffd char
    "EDUCA\ufffdO": "EDUCAÇÃO",
    "Educa\ufffdo": "Educação",
    "P\ufffdgina": "Página",
    "P\ufffblico": "Público",
    "p\ufffblico": "público",
    "RELAT\ufffdRIO": "RELATÓRIO",
    "T\ufffdCNICO": "TÉCNICO",
    "T\ufffdCNICAS": "TÉCNICAS",
    "t\ufffdcnicas": "técnicas",
    "Identifica\ufffdo": "Identificação",
    "N\ufffdo": "Não",
    "n\ufffdo": "não",
    "Hor\ufffdrio": "Horário",
    "Institui\ufffdo": "Instituição",
    "Munic\ufffdpio": "Município",
    "Respons\ufffdvel": "Responsável",
    "respons\ufffdvel": "responsável",
    "Frequ\ufffdncia": "Frequência",
    "frequ\ufffdncia": "frequência",
    "FREQ\ufffdNCIA": "FREQUÊNCIA",
    "Fun\ufffdo": "Função",
    "fun\ufffdo": "função",
    "A\ufffdO": "AÇÃO",
    "A\ufffdo": "Ação",
    "a\ufffdo": "ação",
    "a\ufffdes": "ações",
    "A\ufffdes": "Ações",
    "Alcan\ufffdado": "Alcançado",
    "alcan\ufffdado": "alcançado",
    "Distribu\ufffddo": "Distribuído",
    "distribu\ufffddo": "distribuído",
    "distribu\ufffddos": "distribuídos",
    "Ocorr\ufffdncia": "Ocorrência",
    "ocorr\ufffdncia": "ocorrência",
    "OCORR\ufffdNCIA": "OCORRÊNCIA",
    "ocorr\ufffdncias": "ocorrências",
    "Descri\ufffdo": "Descrição",
    "Provid\ufffdncias": "Providências",
    "provid\ufffdncias": "providências",
    "Observa\ufffdes": "Observações",
    "observa\ufffdes": "observações",
    "OBSERVA\ufffdES": "OBSERVAÇÕES",
    "Conclus\ufffdo": "Conclusão",
    "CONCLUS\ufffdO": "CONCLUSÃO",
    "Valida\ufffdo": "Validação",
    "informa\ufffdes": "informações",
    "execu\ufffdo": "execução",
    "Etil\ufffdmetros": "Etilômetros",
    "\ufffd atividade": "à atividade",
    "Servi\ufffdo": "Serviço",
    " Educa\ufffdo ": " Educação ",
    "–": "–",
    "EducaÃ§Ã£o": "Educação",
    "Ã": "Á", # generic fallback just in case
}

for old, new in replacements.items():
    text = text.replace(old, new)

with open(pdf_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Replaced strings successfully.")
