import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.schedules.models import Agenda
from django.db.models import Q

def clean_ghost_agendas():
    # Looking for agendas that are cancelled AND have no meaningful institution/requester
    ghosts = Agenda.objects.filter(
        status=Agenda.Status.CANCELLED
    ).filter(
        Q(institution_location__in=["", "-", None]) &
        Q(external_responsible__in=["", "-", None])
    )
    
    count = ghosts.count()
    if count > 0:
        print(f"Encontradas {count} solicitações 'fantasmas' (sem dados e canceladas).")
        # To avoid deleting things accidentally, let's just delete the ones that meet strict criteria
        deleted_count, _ = ghosts.delete()
        print(f"Limpeza concluída! Foram apagados {deleted_count} registros do banco.")
    else:
        print("Nenhuma solicitação 'fantasma' foi encontrada.")

if __name__ == "__main__":
    clean_ghost_agendas()
