from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.accounts.serializers import sync_user_lookup


class Command(BaseCommand):
    help = "Sincroniza usuários com os cadastros de Chefes e Agentes."

    def handle(self, *args, **options):
        total = 0
        for user in User.objects.exclude(role=User.Role.ADMIN):
            sync_user_lookup(user)
            total += 1
        self.stdout.write(self.style.SUCCESS(f"{total} usuários sincronizados."))
