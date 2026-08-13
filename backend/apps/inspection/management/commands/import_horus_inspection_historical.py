import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from apps.inspection.horus_historical_import import (
    HorusHistoricalImportError,
    HorusHistoricalImportService,
)


class Command(BaseCommand):
    help = (
        "Valida ou importa o historico "
        "consolidado do Horus entre "
        "2023-01-01 e 2026-08-09."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help=(
                "Caminho do JSON exportado "
                "do Horus."
            ),
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Somente valida o arquivo; "
                "nao grava no banco."
            ),
        )

        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Aplica a importacao no "
                "banco do SIED."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        is_dry_run = bool(
            options.get(
                "dry_run"
            )
        )

        is_apply = bool(
            options.get(
                "apply"
            )
        )

        if (
            is_dry_run
            == is_apply
        ):
            raise CommandError(
                "Informe exatamente um: "
                "--dry-run ou --apply."
            )

        service = (
            HorusHistoricalImportService()
        )

        try:
            if is_dry_run:
                report = (
                    service.dry_run(
                        options["file"]
                    )
                )
            else:
                report = (
                    service.apply(
                        options["file"]
                    )
                )

        except (
            HorusHistoricalImportError
        ) as exc:
            raise CommandError(
                str(exc)
            ) from exc

        self.stdout.write(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

        if (
            report.get(
                "validation",
                {},
            ).get("valid")
        ):
            self.stdout.write(
                self.style.SUCCESS(
                    "Validacao historica "
                    "do Horus concluida "
                    "com sucesso."
                )
            )