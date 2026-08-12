import json

from django.core.management.base import BaseCommand, CommandError

from apps.inspection.horus_sync import HorusInspectionSyncer, HorusSyncError, parse_date_from_option


class Command(BaseCommand):
    help = "Sincroniza relatorios de Fiscalizacao do Horus para a API tecnica do SIED em modo somente leitura."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Consulta e valida localmente, sem enviar para o SIED.")
        parser.add_argument("--limit", type=int, default=None, help="Limita a quantidade de relatorios por execucao.")
        parser.add_argument(
            "--date-from",
            type=str,
            default=None,
            help="Data inicial no formato YYYY-MM-DD. Nesta versao nao permite data anterior a 2026-08-10.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit <= 0:
            raise CommandError("--limit deve ser maior que zero.")

        try:
            date_from = parse_date_from_option(options.get("date_from"))
            result = HorusInspectionSyncer().run(
                date_from=date_from,
                limit=limit,
                dry_run=bool(options.get("dry_run")),
            )
        except HorusSyncError as exc:
            raise CommandError(str(exc)) from exc
        except ValueError as exc:
            raise CommandError(f"Parametro invalido: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Sincronizacao concluida."))
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
