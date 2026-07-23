import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.statistics.models import StatisticCategoryMapping, ConsolidatedStatistic
from django.conf import settings

class Command(BaseCommand):
    help = 'Importa estatísticas históricas da planilha estatisticas.xlsx para o SIED.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-legacy',
            action='store_true',
            help='Apaga todos os registros com methodology=HISTORICAL_LEGACY antes de importar.',
        )
        parser.add_argument(
            '--file',
            type=str,
            default=os.path.join(settings.BASE_DIR.parent, 'estatisticas.xlsx'),
            help='Caminho para o arquivo Excel de estatísticas.',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {file_path}'))
            return

        if options['clear_legacy']:
            count, _ = ConsolidatedStatistic.objects.filter(methodology='HISTORICAL_LEGACY').delete()
            self.stdout.write(self.style.WARNING(f'Limpou {count} registros históricos do legado.'))

        # First, ensure basic mappings exist based on our initial plan
        self.ensure_default_mappings()

        self.stdout.write('Lendo arquivo Excel...')
        df = pd.read_excel(file_path, sheet_name='Plan1')

        # Create a dictionary of mappings for quick access
        mappings = {m.original_name.strip(): m for m in StatisticCategoryMapping.objects.filter(is_active=True)}

        imported_records = []
        errors = []
        
        years_columns = []
        for col in df.columns:
            val = df.iloc[0][col]
            try:
                year = int(val)
                if year >= 2011:
                    years_columns.append(col)
            except (ValueError, TypeError):
                continue

        with transaction.atomic():
            for index, row in df.iterrows():
                # Skip the first row (header representation) and empty categories
                if index == 0 or pd.isna(row.iloc[2]):
                    continue
                
                original_category_name = str(row.iloc[2]).strip()
                
                # Check if we have a mapping
                mapping = mappings.get(original_category_name)
                if not mapping:
                    errors.append(f"Ignorado: Categoria '{original_category_name}' não possui mapeamento ativo.")
                    continue

                for col in years_columns:
                    year = int(df.iloc[0][col])
                    
                    # Se for 2026, estamos parando em 08/07/2026 segundo definição. 
                    # A importação assume que o número em 2026 na planilha é pré-corte.
                    
                    val = row[col]
                    if pd.isna(val) or val == 0:
                        continue
                    
                    # Import
                    stat = ConsolidatedStatistic(
                        reference_year=year,
                        reference_month=None,
                        reference_date=None, # Historical legacy doesn't use precise dates
                        indicator_type=mapping.indicator_type,
                        category_action_type=mapping.sied_action_type,
                        category_entity_type=mapping.sied_requester_entity,
                        value=val,
                        methodology='HISTORICAL_LEGACY',
                        traceability_id=f'legacy_{year}_{mapping.id}'
                    )
                    
                    # Validate before appending
                    try:
                        stat.full_clean()
                        imported_records.append(stat)
                    except Exception as e:
                        errors.append(f"Erro de validação {original_category_name} - {year}: {e}")

            # Bulk create
            if imported_records:
                ConsolidatedStatistic.objects.bulk_create(imported_records)
        
        self.stdout.write(self.style.SUCCESS(f'\nImportação concluída: {len(imported_records)} registros inseridos.'))
        
        if errors:
            self.stdout.write(self.style.WARNING(f'\nAvisos/Erros: {len(errors)}'))
            for err in errors[:10]:
                self.stdout.write(err)
            if len(errors) > 10:
                self.stdout.write("...e outros.")

        # REPORT AS REQUESTED BY USER
        self.stdout.write('\n--- RELATÓRIO DE IMPORTAÇÃO (AMOSTRA) ---')
        # Group by Year and Indicator Type for summary
        from django.db.models import Sum
        summary = ConsolidatedStatistic.objects.filter(methodology='HISTORICAL_LEGACY').values('reference_year', 'indicator_type').annotate(total=Sum('value')).order_by('reference_year', 'indicator_type')
        
        self.stdout.write(f"{'Ano':<6} | {'Indicador':<10} | {'Total':<10} | {'Origem'}")
        self.stdout.write("-" * 50)
        for item in summary:
            self.stdout.write(f"{item['reference_year']:<6} | {item['indicator_type']:<10} | {item['total']:<10} | HISTORICAL_LEGACY")

    def ensure_default_mappings(self):
        """Seed the basic translations we planned."""
        default_maps = [
            ('1 - ABORDADOS ', 'AUDIENCE', None, None),
            ('1.1 - ABORDADOS PALESTRAS', 'AUDIENCE', None, 'PALESTRAS'),
            ('1.2 - ABORDADOS AÇÕES', 'AUDIENCE', None, 'ACOES'),
            ('2.1 - ESCOLAS ', 'ACTION', None, 'Escola'),
            ('2.2 - UNIVERSIDADES ', 'ACTION', None, 'Universidade'),
            ('2.3 - EMPRESAS ', 'ACTION', None, 'Empresa'),
            ('3.1 - BARES', 'ACTION', None, 'Bares'),
            ('3.2 - PEDÁGIO', 'ACTION', None, 'Pedágio'),
            ('3.3 - ESPORTES', 'ACTION', None, 'Praças Esportivas'),
            ('3.4 - PRAIA', 'ACTION', None, 'Praia'),
            ('3.5 - EVENTOS', 'ACTION', None, 'Eventos'),
            ('3.6 - SHOPPING', 'ACTION', None, 'Shopping'),
            ('3.7 - AÇÃO SOCIAL', 'ACTION', None, 'Ação Social'),
            ('3.8 - OUTROS', 'ACTION', None, 'Outros'),
            ('4 - MATERIAIS DE DIVULGAÇÃO', 'MATERIAL', None, None),
            ('3 - REVISTINHA SOPRINHO ', 'MATERIAL', None, 'Soprinho'),
            ('2.4 - CERTIFICADOS ENTREGUES', 'MATERIAL', None, 'Certificados'),
        ]
        
        for orig, ind, action_id, entity in default_maps:
            StatisticCategoryMapping.objects.get_or_create(
                original_name=orig,
                defaults={
                    'indicator_type': ind,
                    'sied_requester_entity': entity,
                    'description': 'Mapeamento automático inicial.'
                }
            )
