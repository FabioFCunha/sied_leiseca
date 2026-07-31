import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.schedules.geocoding import GeocodingError, geocode_address, normalize_agenda_address
from apps.schedules.models import Agenda


class Command(BaseCommand):
    help = "Calcula e persiste coordenadas de agendas por meio de um backfill controlado."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Simula sem modificar registros.")
        parser.add_argument("--limit", type=int, help="Quantidade máxima de agendas a processar.")
        parser.add_argument("--agenda-id", type=int, help="Protocolo de uma única agenda a processar.")
        parser.add_argument(
            "--debug-geocoding",
            action="store_true",
            help="Exibe diagnóstico detalhado das consultas de geocodificação.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=1.1,
            help="Intervalo em segundos entre consultas (mínimo: 1 segundo).",
        )
        parser.add_argument(
            "--retry-not-found",
            action="store_true",
            help="Consulta novamente endereços anteriormente não localizados.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Confirma explicitamente o processamento real sem limite.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options.get("limit")
        agenda_id = options.get("agenda_id")
        debug_geocoding = options["debug_geocoding"]
        retry_not_found = options["retry_not_found"]
        interval = max(float(options["interval"]), 1.0)

        if limit is not None and limit <= 0:
            raise CommandError("--limit deve ser maior que zero.")
        if not dry_run and limit is None and agenda_id is None and not options["all"]:
            raise CommandError("Informe --limit ou use --all para confirmar o processamento real de todas as agendas.")

        summary = {"processed": 0, "found": 0, "not_found": 0, "ignored": 0, "errors": 0}
        queried = False
        queryset = Agenda.objects.select_related("neighborhood_ref", "municipality_ref").order_by("id")
        if agenda_id is not None:
            queryset = queryset.filter(id=agenda_id)
            if not queryset.exists():
                self.stdout.write(self.style.WARNING(f"Agenda {agenda_id} não encontrada; nenhum registro processado."))
                return

        for agenda in queryset.iterator():
            normalized_address = normalize_agenda_address(agenda)
            unchanged = agenda.geocoding_address == normalized_address
            already_found = (
                unchanged
                and agenda.geocoding_status == Agenda.GeocodingStatus.FOUND
                and agenda.latitude is not None
                and agenda.longitude is not None
            )
            already_not_found = unchanged and agenda.geocoding_status == Agenda.GeocodingStatus.NOT_FOUND
            if already_found or (already_not_found and not retry_not_found):
                summary["ignored"] += 1
                continue
            if limit is not None and summary["processed"] >= limit:
                break

            summary["processed"] += 1
            if debug_geocoding:
                self.stdout.write(f"[geocoding] Agenda: {agenda.id}")
                self.stdout.write(f"[geocoding] Endereço original: {agenda.address or '(vazio)'}")
                self.stdout.write(f"[geocoding] Endereço normalizado: {normalized_address or '(vazio)'}")
            if not normalized_address:
                if debug_geocoding:
                    self.stdout.write(
                        "[geocoding] Não encontrado: endereço original ausente ou vazio após normalização."
                    )
                summary["not_found"] += 1
                self.stdout.write(f"Agenda {agenda.id}: endereço ausente.")
                if not dry_run:
                    agenda.latitude = None
                    agenda.longitude = None
                    agenda.geocoding_address = ""
                    agenda.geocoding_status = Agenda.GeocodingStatus.NOT_FOUND
                    agenda.geocoding_attempted_at = timezone.now()
                    agenda.save(update_fields=[
                        "latitude", "longitude", "geocoding_address", "geocoding_status", "geocoding_attempted_at",
                    ])
                continue

            if queried:
                time.sleep(interval)
            try:
                if debug_geocoding:
                    coordinates = geocode_address(normalized_address, diagnostic=self.stdout.write)
                else:
                    coordinates = geocode_address(normalized_address)
                queried = True
            except GeocodingError as exc:
                queried = True
                summary["errors"] += 1
                if debug_geocoding:
                    cause = exc.__cause__ or exc
                    self.stderr.write(
                        f"[geocoding] Agenda {agenda.id} — exceção/timeout: "
                        f"{type(cause).__name__}: {str(cause)[:240]}"
                    )
                self.stderr.write(f"Agenda {agenda.id}: falha na consulta; registro preservado.")
                continue

            attempted_at = timezone.now()
            if coordinates is None:
                summary["not_found"] += 1
                self.stdout.write(f"Agenda {agenda.id}: endereço não localizado.")
                if not dry_run:
                    agenda.latitude = None
                    agenda.longitude = None
                    agenda.geocoding_address = normalized_address
                    agenda.geocoding_status = Agenda.GeocodingStatus.NOT_FOUND
                    agenda.geocoding_attempted_at = attempted_at
                    agenda.save(update_fields=[
                        "latitude", "longitude", "geocoding_address", "geocoding_status", "geocoding_attempted_at",
                    ])
                continue

            summary["found"] += 1
            self.stdout.write(f"Agenda {agenda.id}: localizada.")
            if not dry_run:
                agenda.latitude, agenda.longitude = coordinates
                agenda.geocoding_address = normalized_address
                agenda.geocoding_status = Agenda.GeocodingStatus.FOUND
                agenda.geocoding_attempted_at = attempted_at
                agenda.save(update_fields=[
                    "latitude", "longitude", "geocoding_address", "geocoding_status", "geocoding_attempted_at",
                ])

        mode = "SIMULAÇÃO" if dry_run else "GRAVAÇÃO"
        self.stdout.write(self.style.SUCCESS(
            f"{mode} concluída — processados: {summary['processed']}; localizados: {summary['found']}; "
            f"não localizados: {summary['not_found']}; ignorados: {summary['ignored']}; erros: {summary['errors']}."
        ))
