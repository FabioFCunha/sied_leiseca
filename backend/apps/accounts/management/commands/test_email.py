from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Envia um e-mail de teste usando as configuracoes SMTP atuais."

    def add_arguments(self, parser):
        parser.add_argument("to", help="E-mail de destino para o teste.")

    def handle(self, *args, **options):
        recipient = options["to"].strip()
        if not recipient:
            raise CommandError("Informe um e-mail de destino.")

        message = EmailMessage(
            subject="Teste de e-mail - Agenda Educacao",
            body=(
                "Este e um e-mail de teste do Agenda Educacao.\n\n"
                f"EMAIL_HOST: {settings.EMAIL_HOST}\n"
                f"EMAIL_PORT: {settings.EMAIL_PORT}\n"
                f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}\n"
                f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}\n"
                f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
            reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
        )
        sent = message.send(fail_silently=False)
        self.stdout.write(self.style.SUCCESS(f"E-mail de teste enviado: {sent}"))
