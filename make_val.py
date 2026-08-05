import io

content = """cd D:\\agenda_eventos_ols
Select-String -Path frontend\\src\\utils\\reportPdfGenerator.js -Pattern "Ã|Â|\ufffd|â€“|EducaÃ|PÃ|RelatÃ|AÃ|NÃ"
"""

with open(r'd:\agenda_eventos_ols\validate.ps1', 'w', encoding='utf-8') as f:
    f.write(content)
