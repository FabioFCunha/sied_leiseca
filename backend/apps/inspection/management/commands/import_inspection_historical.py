from django.core.management.base import BaseCommand, CommandError

from apps.inspection.historical_import import InspectionHistoricalDryRunService


class Command(BaseCommand):
    help = "Executa a analise em dry-run da planilha historica de Fiscalizacao."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Caminho para o arquivo XLSX historico.")
        parser.add_argument("--dry-run", action="store_true", help="Executa somente a leitura e validacao do arquivo.")
        parser.add_argument("--apply", action="store_true", help="Aplica a importacao real no banco de dados.")
        parser.add_argument("--source-type", type=str, help="Filtra por tipo de fonte (ex: DAILY).")
        parser.add_argument("--taxonomy-era", type=str, help="Filtra por era (ex: ERA_C).")

    def handle(self, *args, **options):
        file_path = options["file"]
        is_dry_run = options.get("dry_run")
        is_apply = options.get("apply")
        source_type = options.get("source_type")
        taxonomy_era = options.get("taxonomy_era")

        if not is_dry_run and not is_apply:
            raise CommandError("Voce deve especificar --dry-run ou --apply.")

        if is_apply and is_dry_run:
            raise CommandError("Nao pode especificar --dry-run e --apply simultaneamente.")

        if is_apply:
            if source_type != "DAILY" or taxonomy_era != "ERA_C":
                raise CommandError("Nesta etapa, a aplicação real está autorizada somente para ERA_C / DAILY até 09/08/2026.")

            from apps.inspection.historical_import import InspectionHistoricalImportService
            report = InspectionHistoricalImportService().apply(
                file_path=file_path,
                source_type=source_type,
                taxonomy_era=taxonomy_era,
            )
        else:
            report = InspectionHistoricalDryRunService().render_report(file_path)

        self.stdout.write(report)
