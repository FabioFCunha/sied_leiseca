from django.core.management.base import BaseCommand
from apps.statistics.models import ConsolidatedStatistic
from apps.schedules.models import EducationReport

class Command(BaseCommand):
    help = 'Diagnostic command for statistics integrity'

    def handle(self, *args, **options):
        self.stdout.write("--- INICIANDO DIAGNÓSTICO DE INTEGRIDADE ESTATÍSTICA ---")
        
        # 1. Reports validados (statistics_processed=True) sem ConsolidatedStatistic ACTIVE
        processed_reports = EducationReport.objects.filter(statistics_processed=True)
        reports_without_active_stats = []
        for report in processed_reports:
            if not ConsolidatedStatistic.objects.filter(traceability_id=f'report_{report.id}', status='ACTIVE').exists():
                reports_without_active_stats.append(report.id)
                
        if reports_without_active_stats:
            self.stdout.write(self.style.WARNING(f"⚠ {len(reports_without_active_stats)} relatórios 'statistics_processed=True' sem estatística ACTIVE."))
        else:
            self.stdout.write(self.style.SUCCESS("✔ Nenhum relatório órfão de estatística."))

        # 2. ConsolidatedStatistic sem relatório vinculado
        sied_stats = ConsolidatedStatistic.objects.filter(methodology='SIED_OPERATIONAL')
        stats_without_reports = []
        for stat in sied_stats:
            if stat.traceability_id.startswith('report_'):
                report_id = stat.traceability_id.replace('report_', '')
                if not EducationReport.objects.filter(id=report_id).exists():
                    stats_without_reports.append(stat.id)
                    
        if stats_without_reports:
            self.stdout.write(self.style.ERROR(f"✖ {len(stats_without_reports)} estatísticas operacionais sem EducationReport associado!"))
        else:
            self.stdout.write(self.style.SUCCESS("✔ Nenhuma estatística sem relatório original."))

        # 3. Duplicidades
        from django.db.models import Count
        duplicates = ConsolidatedStatistic.objects.filter(status='ACTIVE').values(
            'traceability_id', 'indicator_type', 'category_action_type', 'category_entity_type'
        ).annotate(count=Count('id')).filter(count__gt=1)
        
        if duplicates:
            self.stdout.write(self.style.ERROR(f"✖ Foram encontradas {len(duplicates)} linhas duplicadas na estatística!"))
        else:
            self.stdout.write(self.style.SUCCESS("✔ Nenhuma duplicidade ativa encontrada."))

        self.stdout.write("--- DIAGNÓSTICO CONCLUÍDO ---")
