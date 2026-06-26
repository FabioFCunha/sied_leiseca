import logging

from django.conf import settings

from config.email_delivery import sanitize_email_error, send_email_message
from config.email_signature import build_signed_email


logger = logging.getLogger(__name__)


def sanitize_smtp_error(error):
    return sanitize_email_error(error)


def send_password_setup_email(user, link):
    message = build_signed_email(
        subject="Acesso ao SIED Sistema Integrado da Educação",
        body=(
            f"Ola, {user.full_name or user.email}.\n\n"
            "Seu acesso ao SIED Sistema Integrado da Educação foi criado.\n\n"
            "Para definir sua senha, acesse o link abaixo:\n"
            f"{link}\n\n"
            "Se voce nao esperava esta mensagem, ignore este e-mail."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
    )
    sent, detail = send_email_message(message)
    if not sent:
        logger.error("Nao foi possivel enviar e-mail de definicao de senha para %s: %s", user.email, detail)
    return sent, detail
