import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMessage


logger = logging.getLogger(__name__)


def sanitize_smtp_error(error):
    message = str(error)
    password = getattr(settings, "EMAIL_HOST_PASSWORD", "")
    if password:
        message = message.replace(password, "***")
    return message[:500]


def send_password_setup_email(user, link):
    message = EmailMessage(
        subject="Acesso ao Agenda Educação OLS",
        body=(
            f"Olá, {user.full_name or user.email}.\n\n"
            "Seu acesso ao Agenda Educação OLS foi criado.\n\n"
            "Para definir sua senha, acesse o link abaixo:\n"
            f"{link}\n\n"
            "Se você não esperava esta mensagem, ignore este e-mail."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
    )
    message.encoding = "utf-8"
    try:
        message.send(fail_silently=False)
    except smtplib.SMTPException as exc:
        detail = sanitize_smtp_error(exc)
        logger.exception("Nao foi possivel enviar e-mail de definicao de senha para %s: %s", user.email, detail)
        return False, detail
    except Exception as exc:
        detail = sanitize_smtp_error(exc)
        if detail:
            detail = f"{exc.__class__.__name__}: {detail}"
        else:
            detail = exc.__class__.__name__
        logger.exception("Nao foi possivel enviar e-mail de definicao de senha para %s: %s", user.email, detail)
        return False, detail
    return True, ""
