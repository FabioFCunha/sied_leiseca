import os
import django
import pandas as pd
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.statistics.models import StatisticCategoryMapping, ConsolidatedStatistic

def validate():
    # 1. Validation of De -> Para
    mappings = StatisticCategoryMapping.objects.filter(is_active=True)
    de_para = []
    for m in mappings:
        action_name = m.sied_action_type.name if m.sied_action_type else "Geral"
        entity_name = m.sied_requester_entity if m.sied_requester_entity else "N/A"
        
        classification = f"{m.get_indicator_type_display()} / "
        if m.indicator_type == 'ACTION':
            classification += f"{action_name} ({entity_name})"
        else:
            classification += f"{entity_name}"
            
        de_para.append(f"{m.original_name} -> {classification}")
        
    print("=== DE -> PARA ===")
    for item in sorted(de_para):
        print(item)
        
    print("\n=== VALIDAÇÃO QUANTITATIVA ===")
    file_path = 'e:/agenda_eventos_ols/estatisticas.xlsx'
    df = pd.read_excel(file_path, sheet_name='Plan1')
    
    print(f"{'Ano':<6} | {'Categoria Original':<30} | {'Planilha':<10} | {'Banco':<10} | {'Dif'}")
    print("-" * 75)
    
    years_columns = []
    for col in df.columns:
        try:
            val = int(df.iloc[0][col])
            if val >= 2011:
                years_columns.append(col)
        except (ValueError, TypeError):
            pass

    for index, row in df.iterrows():
        if index == 0 or pd.isna(row.iloc[2]):
            continue
            
        original_category = str(row.iloc[2]).strip()
        mapping = mappings.filter(original_name=original_category).first()
        
        if not mapping:
            continue
            
        for col in years_columns:
            year = int(df.iloc[0][col])
            val_planilha = row[col]
            if pd.isna(val_planilha) or val_planilha == 0:
                continue
                
            val_banco_agregado = ConsolidatedStatistic.objects.filter(
                methodology='HISTORICAL_LEGACY',
                reference_year=year,
                traceability_id=f'legacy_{year}_{mapping.id}'
            ).aggregate(Sum('value'))['value__sum'] or 0
            
            diff = float(val_planilha) - float(val_banco_agregado)
            
            print(f"{year:<6} | {original_category[:30]:<30} | {val_planilha:<10} | {val_banco_agregado:<10} | {diff}")

if __name__ == '__main__':
    validate()
