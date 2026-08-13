import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from apps.inspection.horus_historical_export import (
    HorusHistoricalExporter,
)


class Command(BaseCommand):
    help = (
        "Exporta o historico da Fiscalizacao "
        "do Horus entre 2023-01-01 e "
        "2026-08-09, somente por SELECT."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            required=True,
            help=(
                "Caminho do arquivo JSON "
                "a ser gerado."
            ),
        )

    def handle(self, *args, **options):
        output = options["output"]

        try:
            result = (
                HorusHistoricalExporter()
                .export(output)
            )
        except Exception as exc:
            raise CommandError(
                f"Falha na exportacao "
                f"historica do Horus: {exc}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Exportacao historica "
                "do Horus concluida."
            )
        )

        self.stdout.write(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )