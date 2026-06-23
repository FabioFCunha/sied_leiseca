from django.core.management.base import BaseCommand

from apps.schedules.accessibility import process_due_accessibility_rejections


class Command(BaseCommand):
    help = "Processa recusas de acessibilidade agendadas e envia os e-mails vencidos."

    def handle(self, *args, **options):
        total = process_due_accessibility_rejections()
        self.stdout.write(self.style.SUCCESS(f"{total} recusa(s) de acessibilidade processada(s)."))
