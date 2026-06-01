from django.core.management.base import BaseCommand
from django.db import transaction

from apps.schedules.management.commands.import_education_staff_workbook import key, source_id
from apps.schedules.models import Agent, Support


class Command(BaseCommand):
    help = "Move pessoas com funcao de apoio para Apoios e remove duplicidade da lista de Agentes."

    @transaction.atomic
    def handle(self, *args, **options):
        moved = 0
        deleted_agents = 0
        updated_supports = 0

        support_agents = Agent.objects.filter(role__icontains="APOIO")
        for agent in support_agents.select_related("team"):
            support = Support.objects.filter(name__iexact=agent.name).first()
            defaults = {
                "source_id": source_id("support", agent.team.name if agent.team else "", agent.name),
                "team": agent.team,
                "role": agent.role,
                "address": agent.address,
                "is_active": True,
            }
            if support:
                changed = []
                for field, value in defaults.items():
                    if getattr(support, field) != value:
                        setattr(support, field, value)
                        changed.append(field)
                if changed:
                    support.save(update_fields=changed)
                    updated_supports += 1
            else:
                Support.objects.create(name=agent.name, **defaults)
                moved += 1

            agent.delete()
            deleted_agents += 1

        old_supports = Support.objects.filter(is_active=True).filter(team__isnull=True) | Support.objects.filter(is_active=True, address="")
        old_supports = old_supports.distinct()
        for support in old_supports:
            duplicate = (
                Support.objects.exclude(pk=support.pk)
                .filter(name__iexact=support.name, is_active=True, team__isnull=False)
                .first()
            )
            if duplicate:
                support.delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Normalizacao concluida: "
                f"{moved} apoios criados, {updated_supports} apoios atualizados, "
                f"{deleted_agents} duplicidades removidas de Agentes."
            )
        )
