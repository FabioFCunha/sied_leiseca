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
        html_body=(
            f'<div style="text-align: justify; font-family: sans-serif;">'
            f"Olá, {user.full_name or user.email}.<br><br>"
            "Seu acesso ao <strong>SIED Sistema Integrado da Educação</strong> foi criado.<br><br>"
            "Para definir sua senha, clique no botão ou link abaixo:<br><br>"
            f'<a href="{link}" style="display: inline-block; padding: 10px 20px; background-color: #0b5ed7; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Criar Minha Senha</a><br><br>'
            f'<small>Ou copie e cole o seguinte endereço no seu navegador: <br><a href="{link}">{link}</a></small><br><br>'
            "Se você não esperava esta mensagem, ignore este e-mail."
            f'</div>'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
    )
    sent, detail = send_email_message(message)
    if not sent:
        logger.error("Nao foi possivel enviar e-mail de definicao de senha para %s: %s", user.email, detail)
    return sent, detail
