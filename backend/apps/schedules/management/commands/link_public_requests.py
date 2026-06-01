from difflib import SequenceMatcher
import re
import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.schedules.models import Agenda, AgendaHistory
from apps.schedules.views import snapshot_for


def normalize(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def similarity(left, right):
    return SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def best_name_score(request, action):
    request_name = request.institution_location or request.location or request.title
    action_names = [
        action.institution_location,
        action.location,
        action.title,
    ]
    return max(similarity(request_name, name) for name in action_names if name)


class Command(BaseCommand):
    help = "Relaciona solicitações públicas importadas com agendas internas já lançadas."

    def add_arguments(self, parser):
        parser.add_argument("--threshold", type=float, default=0.90)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"] and not options["dry_run"]:
            cleared = Agenda.objects.filter(origin=Agenda.Origin.PUBLIC_FORM, linked_action__isnull=False).update(linked_action=None)
            self.stdout.write(self.style.WARNING(f"{cleared} vínculos removidos."))

        actions = list(Agenda.objects.exclude(origin=Agenda.Origin.PUBLIC_FORM).only(
            "id", "title", "date", "start_time", "institution_location", "location", "city"
        ))
        requests = Agenda.objects.filter(origin=Agenda.Origin.PUBLIC_FORM).select_related("created_by", "linked_action")

        linked = updated = skipped = 0
        samples = []
        for request in requests:
            match, score = self.find_match(request, actions)
            if not match or score < options["threshold"]:
                skipped += 1
                continue

            if request.linked_action_id == match.id:
                linked += 1
                continue

            updated += 1
            if len(samples) < 8:
                samples.append((request.id, match.id, score, request.institution_location, match.institution_location or match.location or match.title))
            if not options["dry_run"]:
                request.linked_action = match
                request.save(update_fields=["linked_action"])
                AgendaHistory.objects.create(
                    agenda=request,
                    changed_by=request.created_by,
                    action="VINCULO_ACAO",
                    snapshot=snapshot_for(request),
                )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry-run: nenhum vínculo foi gravado."))
        for request_id, action_id, score, request_name, action_name in samples:
            self.stdout.write(f"{request_id} -> {action_id} ({score:.2f}) {request_name} => {action_name}")
        self.stdout.write(self.style.SUCCESS(f"Vínculos existentes: {linked}. Novos/alterados: {updated}. Sem vínculo confiável: {skipped}."))

    def find_match(self, request, actions):
        best = None
        best_score = 0
        for action in actions:
            if action.date != request.date:
                continue
            score = best_name_score(request, action)
            if action.start_time == request.start_time:
                score += 0.04
            if normalize(request.city) and normalize(action.city) and normalize(request.city) != normalize(action.city):
                score -= 0.12
            if score > best_score:
                best = action
                best_score = score
        return best, best_score
