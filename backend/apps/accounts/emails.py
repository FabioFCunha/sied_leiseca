import logging

from django.conf import settings
from django.core.mail import EmailMessage


logger = logging.getLogger(__name__)


def send_password_setup_email(user, link):
    message = EmailMessage(
        subject="Acesso ao Agenda Educacao OLS",
        body=(
            f"Ola, {user.full_name or user.email}.\n\n"
            "Seu acesso ao Agenda Educacao OLS foi criado.\n\n"
            "Para definir sua senha, acesse o link abaixo:\n"
            f"{link}\n\n"
            "Se voce nao esperava esta mensagem, ignore este e-mail."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
    )
    try:
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Nao foi possivel enviar e-mail de definicao de senha para %s", user.email)
        return False
    return True
