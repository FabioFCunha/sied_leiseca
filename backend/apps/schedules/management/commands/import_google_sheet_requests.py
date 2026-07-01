from datetime import datetime, timedelta
import csv
import hashlib
import io
from pathlib import Path
import re
import unicodedata
from urllib.request import urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.schedules.models import ActionType, Agenda, AgendaHistory, Municipality, Neighborhood, Sector
from apps.schedules.views import snapshot_for


DEFAULT_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vSvpcYQgC2bZ43g8rCpmhrEZPwyfwk347zMvGSdlEhMtcbLfHxMZqtZ5r5GQvKdi8RrlAZa-PL0rsqT/"
    "pub?gid=1806126196&single=true&output=csv"
)


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def key(value):
    text = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def first(data, *needles):
    wanted = [key(needle) for needle in needles]
    for header, value in data.items():
        header_key = key(header)
        if all(needle in header_key for needle in wanted):
            return clean(value)
    return ""


def parse_date(value):
    text = clean(value)
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_time(value):
    text = clean(value)
    if not text:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            pass
    return None


def parse_int(value):
    match = re.search(r"\d+", clean(value))
    return int(match.group()) if match else None


def source_id_for(data):
    basis = "|".join(
        [
            first(data, "CARIMBO"),
            first(data, "DATA PRETENDIDA"),
            first(data, "INSTITUICAO", "ORGANIZACAO"),
            first(data, "E MAIL"),
            first(data, "CPF"),
        ]
    )
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:24]
    return f"google-sheet:{digest}"


def get_lookup(model, name):
    name = clean(name)
    if not name:
        return None
    found = model.objects.filter(name__iexact=name).first()
    return found or model.objects.create(name=name)


class Command(BaseCommand):
    help = "Importa solicitações publicadas em CSV pelo Google Sheets para a tabela de agendas."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=settings.PUBLIC_REQUESTS_CSV_URL or DEFAULT_CSV_URL)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--clear-existing", action="store_true")
        parser.add_argument("--clear-all-statuses", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.MANAGER]).first()
        if not admin:
            raise CommandError("Crie um usuário administrador antes de importar solicitações.")

        if options["clear_existing"]:
            summary = self.clear_existing_requests(options["dry_run"], clear_all_statuses=options["clear_all_statuses"])
            action = "seriam removidas" if options["dry_run"] else "removidas"
            self.stdout.write(
                self.style.WARNING(
                    f"{summary['deleted']} solicita??es p?blicas {action} antes da importa??o"
                    f" (bloqueadas por relat?rio t?cnico: {summary['protected']})."
                )
            )

        content = self.fetch_csv(options["url"])
        reader = csv.reader(io.StringIO(content))
        raw_headers = next(reader, [])
        headers = [
            clean(header) or f"__blank_{index}"
            for index, header in enumerate(raw_headers)
        ]
        sector, _ = Sector.objects.get_or_create(
            name="Solicitações externas",
            defaults={"description": "Solicitações importadas do Google Forms/Sheets."},
        )

        created = updated = skipped = 0
        for index, row in enumerate(reader, start=2):
            if options["limit"] and created + updated + skipped >= options["limit"]:
                break
            result = self.import_row(dict(zip(headers, row)), index, admin, sector, options["dry_run"])
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry-run: nada foi gravado no banco."))
        self.stdout.write(self.style.SUCCESS(f"Google Sheet: {created} criadas, {updated} atualizadas, {skipped} ignoradas."))

    def fetch_csv(self, url):
        source = (url or "").strip()
        if not source:
            raise CommandError("Informe --url ou defina PUBLIC_REQUESTS_CSV_URL.")

        candidate = Path(source)
        if candidate.exists() and candidate.is_file():
            return candidate.read_text(encoding="utf-8-sig")

        with urlopen(source, timeout=45) as response:
            return response.read().decode("utf-8-sig")

    def clear_existing_requests(self, dry_run, clear_all_statuses=False):
        qs = Agenda.objects.filter(origin=Agenda.Origin.PUBLIC_FORM)
        if not clear_all_statuses:
            qs = qs.filter(status=Agenda.Status.PENDING)

        protected_ids = list(qs.filter(technical_reports__isnull=False).values_list("id", flat=True).distinct())
        deletable_qs = qs.exclude(id__in=protected_ids)
        deleted = deletable_qs.count()
        if not dry_run and deleted:
            deletable_qs.delete()
        return {
            "matched": qs.count(),
            "deleted": deleted,
            "protected": len(protected_ids),
        }

    def import_row(self, row, index, admin, sector, dry_run):
        data = {clean(header): value for header, value in row.items() if header is not None}
        agenda_date = parse_date(first(data, "DATA PRETENDIDA"))
        action_type = first(data, "MODALIDADE PRETENDIDA")
        institution = first(data, "INSTITUICAO", "ORGANIZACAO")
        start_time = parse_time(first(data, "HORARIO PRETENDIDO")) or parse_time(first(data, "INFORMAR HORARIO"))

        if not agenda_date or not institution or not action_type:
            return "skipped"

        start_time = start_time or datetime.strptime("09:00", "%H:%M").time()
        end_time = (datetime.combine(agenda_date, start_time) + timedelta(hours=1)).time().replace(second=0, microsecond=0)
        comments = first(data, "COMENTARIOS", "SUGESTOES")
        timestamp = first(data, "CARIMBO")
        address = first(data, "ENDERECO DE REALIZACAO")
        city = first(data, "CIDADE")
        neighborhood = first(data, "BAIRRO")
        source_id = source_id_for(data)
        title = f"{action_type} - {institution}"[:180]

        defaults = {
            "title": title,
            "description": comments or "Solicitação importada do Google Forms.",
            "date": agenda_date,
            "start_time": start_time,
            "end_time": end_time,
            "location": institution[:180],
            "action_type": action_type,
            "action_type_ref": get_lookup(ActionType, action_type),
            "institution_location": institution,
            "quantity": parse_int(first(data, "NUMERO APROXIMADO")) or parse_int(first(data, "PARTICIPANTES")),
            "actions_count": parse_int(first(data, "QUANTIDADE DE ACOES")),
            "schedule_text": clean(first(data, "HORARIO PRETENDIDO")),
            "time_2": parse_time(first(data, "HORARIO 2")),
            "time_3": parse_time(first(data, "HORARIO 3")),
            "address": address,
            "neighborhood": neighborhood,
            "neighborhood_ref": get_lookup(Neighborhood, neighborhood),
            "city": city,
            "state": first(data, "UF") or first(data, "ESTADO"),
            "municipality_ref": get_lookup(Municipality, city),
            "external_responsible": first(data, "NOME COMPLETO"),
            "external_responsible_phone": first(data, "TELEFONE"),
            "external_email": first(data, "E MAIL"),
            "contact_email": first(data, "ENDERECO DE E MAIL"),
            "requester_cpf": first(data, "CPF"),
            "requester_role": first(data, "CARGO", "FUNCAO"),
            "requester_entity_type": first(data, "DESCRICAO DA ENTIDADE"),
            "audience": first(data, "PUBLICO"),
            "age_ranges": first(data, "FAIXA ETARIA"),
            "has_ramps": first(data, "RAMPAS"),
            "has_elevators": first(data, "ELEVADORES"),
            "has_accessible_bathrooms": first(data, "BANHEIROS ADAPTADOS"),
            "media_equipment": first(data, "DISPOE DE"),
            "image_authorization": self.image_authorization(data),
            "status": Agenda.Status.PENDING,
            "origin": Agenda.Origin.PUBLIC_FORM,
            "notes": self.notes(comments, timestamp, index),
            "responsible": admin,
            "sector": sector,
            "created_by": admin,
        }

        if dry_run:
            return "updated" if Agenda.objects.filter(source_id=source_id).exists() else "created"

        agenda, created = Agenda.objects.update_or_create(source_id=source_id, defaults=defaults)
        if created:
            AgendaHistory.objects.create(
                agenda=agenda,
                changed_by=admin,
                action="IMPORTACAO_GOOGLE_SHEET",
                snapshot=snapshot_for(agenda),
            )
            return "created"
        return "updated"

    def image_authorization(self, data):
        for header, value in data.items():
            if (key(header).startswith("BLANK") or key(header) == "AUTORIZACAO DE USO DE IMAGEM") and "AUTORIZA" in clean(value).upper():
                return clean(value)
            if "NAO SE APLICA" in key(value):
                return clean(value)
        return first(data, "AUTORIZA")

    def notes(self, comments, timestamp, index):
        parts = [f"Importado do Google Forms/Sheets. Linha CSV: {index}."]
        if timestamp:
            parts.append(f"Carimbo de data/hora: {timestamp}.")
        if comments:
            parts.append(comments)
        return "\n".join(parts)
