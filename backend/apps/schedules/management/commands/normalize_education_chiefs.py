from django.core.management.base import BaseCommand

from apps.schedules.models import Agenda, Chief


ALIASES = {
    "Aldomir": "ALDOMIR TORRES DE OLIVEIRA",
    "Vitor": "VITOR PARADIZZO CELESTINO",
    "Vitor Paradizzo": "VITOR PARADIZZO CELESTINO",
    "Douglas": "DOUGLAS VIEIRA AMADOR",
    "Douglas Amador": "DOUGLAS VIEIRA AMADOR",
    "Eleni": "ELENI MARTINS",
    "ELISANGELA": "ELISANGELA CUNHA MONTEIRO",
    "Elisângela Monteiro": "ELISANGELA CUNHA MONTEIRO",
    "M. Gomes": "MARCELO GOMES DE ARAUJO",
    "Marcelo Gomes": "MARCELO GOMES DE ARAUJO",
    "Rafaella": "RAFAELLA GOMES SILVA",
    "Wallace": "WALLACE ABREU DOS SANTOS",
}


class Command(BaseCommand):
    help = "Consolida chefes abreviados nos cadastros completos da educacao e remove nomes fora do padrao."

    def handle(self, *args, **options):
        merged = 0
        removed = 0
        for old_name, new_name in ALIASES.items():
            old = Chief.objects.filter(name__iexact=old_name).first()
            new = Chief.objects.filter(name__iexact=new_name).first()
            if not old or not new:
                continue
            if old.phone and not new.phone:
                new.phone = old.phone
                new.save(update_fields=["phone"])
            Agenda.objects.filter(chief_ref=old).update(chief_ref=new, chief_name=new.name)
            old.delete()
            merged += 1

        removed += Chief.objects.filter(name__iexact="Aline").delete()[0]
        removed += Chief.objects.filter(team__isnull=True).delete()[0]
        Chief.objects.filter(team__isnull=False, address__gt="").update(is_active=True)

        self.stdout.write(self.style.SUCCESS(f"Chefes consolidados: {merged}. Registros fora do padrao removidos: {removed}."))
