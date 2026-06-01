from django.conf import settings
from django.core.mail import EmailMessage
from django.core import signing
from django.utils import timezone

from .models import Agenda, SatisfactionSurvey


PUBLIC_REQUEST_SALT = "agenda-public-request-update"


def agenda_recipients(agenda):
    emails = []
    for email in [agenda.external_email, agenda.contact_email]:
        if email and email.strip().lower() not in [item.lower() for item in emails]:
            emails.append(email.strip())
    return emails


def format_date(value):
    return value.strftime("%d/%m/%Y") if value else "a confirmar"


def format_time(value):
    return value.strftime("%H:%M") if value else "a confirmar"


def protocol_line(agenda):
    return f"Protocolo: #{agenda.id}"


def agenda_details(agenda):
    return "\n".join(
        [
            protocol_line(agenda),
            f"Solicitante: {agenda.external_responsible or 'não informado'}",
            f"Atividade: {agenda.title}",
            f"Data: {format_date(agenda.date)}",
            f"Horário: {format_time(agenda.start_time)} às {format_time(agenda.end_time)}",
            f"Local: {agenda.institution_location or agenda.location or 'não informado'}",
            f"Endereço: {agenda.address or 'não informado'}",
            f"Município: {agenda.city or 'não informado'}",
        ]
    )


def scheduled_details(agenda):
    details = [agenda_details(agenda)]
    if agenda.team_name or agenda.team_ref:
        details.append(f"Equipe: {agenda.team_name or agenda.team_ref.name}")
    if agenda.chief_name or agenda.chief_ref:
        details.append(f"Chefe responsável: {agenda.chief_name or agenda.chief_ref.name}")
    if agenda.vehicle or agenda.vehicle_ref:
        details.append(f"Viatura: {agenda.vehicle or agenda.vehicle_ref.name}")
    if agenda.agents:
        details.append(f"Agentes: {agenda.agents}")
    return "\n".join(details)


def public_update_token(agenda):
    return signing.dumps({"agenda": agenda.id}, salt=PUBLIC_REQUEST_SALT)


def public_update_url(agenda):
    return f"{settings.FRONTEND_URL.rstrip('/')}/solicitar-agenda/{public_update_token(agenda)}"


def survey_url(survey):
    return f"{settings.FRONTEND_URL.rstrip('/')}/pesquisa-satisfacao/{survey.token}"


def get_or_create_survey(report):
    agenda = report.agenda
    token = signing.dumps({"agenda": agenda.id, "report": report.id}, salt="agenda-satisfaction-survey")
    survey, _ = SatisfactionSurvey.objects.get_or_create(
        agenda=agenda,
        report=report,
        defaults={
            "token": token,
            "requester_email": agenda.external_email or agenda.contact_email,
            "team": report.team or agenda.team_name,
            "chief_name": agenda.chief_name or (agenda.chief_ref.name if agenda.chief_ref else ""),
        },
    )
    return survey


def approval_message(agenda):
    return (
        f"Aprovação da solicitação - Protocolo #{agenda.id}",
        (
            "Prezado(a) solicitante,\n\n"
            "Seu pedido de apresentação da Palestra de educação no trânsito foi aprovado.\n\n"
            "Informamos que a Equipe da Educação da Operação Lei Seca fará contato, em breve, "
            "para alinhar sobre a palestra solicitada.\n\n"
            "Atenciosamente,\n"
            "Superintendência da Operação Lei Seca"
        ),
    )


def rejection_message(agenda):
    return (
        f"Resposta da solicitação - Protocolo #{agenda.id}",
        (
            "Prezado(a) solicitante,\n\n"
            "No momento, não temos condições técnicas de atender a sua solicitação.\n\n"
            "Atenciosamente,\n"
            "Superintendência da Operação Lei Seca"
        ),
    )


def available_dates_message(agenda, month, days):
    return (
        f"Datas disponíveis - Protocolo #{agenda.id}",
        (
            "Prezado(a) solicitante,\n\n"
            "Não temos disponibilidade para atender na data solicitada. "
            f"No mês {month}, temos disponibilidade nos dias {days}.\n\n"
            "Caso as datas informadas atendam sua necessidade, orientamos acessar o protocolo gerado, "
            "alterar a data da realização da palestra e nos reenviar o formulário:\n"
            f"{public_update_url(agenda)}\n\n"
            "Atenciosamente,\n"
            "Superintendência da Operação Lei Seca"
        ),
    )


def message_for_status(agenda, status):
    if status == Agenda.Status.PENDING:
        return (
            f"Solicitacao recebida - Protocolo #{agenda.id}",
            (
                "Recebemos sua solicitacao e ela sera avaliada pela equipe responsavel.\n\n"
                f"{agenda_details(agenda)}\n\n"
                "Voce recebera uma nova mensagem quando houver atualizacao do protocolo."
            ),
        )
    if status == Agenda.Status.APPROVED:
        return approval_message(agenda)
    if status == Agenda.Status.CANCELLED:
        return rejection_message(agenda)
    return None, None


def send_agenda_status_email(agenda, status=None):
    recipients = agenda_recipients(agenda)
    if not recipients:
        return False

    subject, body = message_for_status(agenda, status or agenda.status)
    if not subject:
        return False

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
    )
    email.send(fail_silently=True)
    return True


def send_agenda_available_dates_email(agenda, month, days):
    recipients = agenda_recipients(agenda)
    if not recipients:
        return False

    subject, body = available_dates_message(agenda, month, days)
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
    )
    email.send(fail_silently=True)
    return True


def send_satisfaction_survey_email(report):
    if not report.agenda_id:
        return False
    recipients = agenda_recipients(report.agenda)
    if not recipients:
        return False
    survey = get_or_create_survey(report)
    subject = f"Pesquisa de satisfação - Protocolo #{report.agenda_id}"
    body = (
        "Prezados,\n\n"
        "Solicitamos que avaliem a nosssa palestra para que possamos aprimorar as ações futuras.\n\n"
        f"Acesse a pesquisa pelo link abaixo:\n{survey_url(survey)}\n\n"
        f"Protocolo: #{report.agenda_id}\n\n"
        "Atenciosamente,\n"
        "Superintendência da Operação Lei Seca"
    )
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
    )
    email.send(fail_silently=True)
    survey.sent_at = timezone.now()
    survey.save(update_fields=["sent_at", "updated_at"])
    return True
