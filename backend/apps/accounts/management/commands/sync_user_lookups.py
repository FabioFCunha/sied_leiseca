from django.core.management.base import BaseCommand

from apps.accounts.serializers import sync_all_user_lookups


class Command(BaseCommand):
    help = "Sincroniza usuários operacionais com os cadastros de Chefes, Agentes e Apoios."

    def handle(self, *args, **options):
        total = sync_all_user_lookups()
        self.stdout.write(self.style.SUCCESS(f"{total} usuários sincronizados."))
