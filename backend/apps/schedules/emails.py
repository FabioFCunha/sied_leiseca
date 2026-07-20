import logging

from django.conf import settings
from django.core import signing
from django.utils import timezone

from config.email_delivery import sanitize_email_error, send_email_message
from config.email_signature import build_signed_email

from .models import Agenda, SatisfactionSurvey


logger = logging.getLogger(__name__)
PUBLIC_REQUEST_SALT = "agenda-public-request-update"
INSTAGRAM_URL = "https://www.instagram.com/leisecarj/"


def sanitize_smtp_error(error):
    return sanitize_email_error(error)


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


def requester_name(agenda):
    return (agenda.external_responsible or "").strip() or "solicitante"


def requester_greeting(agenda):
    return f"Prezado(a) {requester_name(agenda)},"

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


def build_email(subject, body, recipients):
    return build_signed_email(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
    )


def send_email_safely(email, context):
    sent, detail = send_email_message(email)
    if not sent:
        logger.error("Nao foi possivel enviar e-mail de %s: %s", context, detail)
    return sent


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
            f"{requester_greeting(agenda)}\n\n"
            "Esperamos que esteja bem! Sua solicitação de apresentação da Palestra de educação no trânsito foi aprovada!\n\n"
            "Queremos agradecer pela sua admiração! Informamos que a nossa Equipe da Educação entrará em contato "
            "para alinhar toda a dinâmica e necessidades sobre a palestra solicitada, o mais rápido possível. "
            "Por isso, mantenha-se atento(a) aos meios de contato disponibilizados na solicitação. Desde já queremos "
            "te convidar para começar a transformar o trânsito com a gente! Se conecte conosco acessando o nosso "
            f"instagram e fique por dentro de tudo que acontece na Operação Lei Seca: {INSTAGRAM_URL}.\n\n"
            "Nos encontraremos, em breve!\n\n"
            "Atenciosamente,\n\n"
            "Superintendência da Operação Lei Seca."
        ),
    )

def rejection_message(agenda):
    return (
        f"Resposta da solicitação - Protocolo #{agenda.id}",
        (
            f"{requester_greeting(agenda)}\n\n"
            "Nós queremos agradecer a sua confiança! Esperamos que esteja bem! Neste momento, não temos condições "
            "técnicas para fornecer a palestra no lugar proposto, por isso, não será possível a sua continuidade para "
            "a sua solicitação. Mas isso não significa que você não pode ter outros momentos conosco, ao contrário! "
            "Sabemos que essa notícia não é a esperada, mas desde já queremos estender o convite a futuras oportunidades "
            "para transformarmos o trânsito com a gente.\n\n"
            "Se conecte conosco acessando o nosso instagram e fique por dentro de tudo que acontece na Operação Lei Seca: "
            f"{INSTAGRAM_URL}. Agradecemos mais uma vez sua solicitação e a sua admiração! Esperamos te encontrar por aí!\n\n"
            "Atenciosamente,\n\n"
            "Superintendência da Operação Lei Seca."
        ),
    )

def available_dates_message(agenda, month, days, custom_message=""):
    if custom_message:
        return (f"Datas disponíveis - Protocolo #{agenda.id}", custom_message)
    return (
        f"Datas disponíveis - Protocolo #{agenda.id}",
        (
            f"{requester_greeting(agenda)}\n\n"
            "Nós queremos agradecer a sua confiança! Esperamos que esteja bem! Neste momento, não temos disponibilidade "
            "para atender na data solicitada. Sabemos que essa notícia não é a esperada, mas isso não significa que você "
            "não pode ter outro momento conosco, ao contrário! "
            f"Para lhe ajudar, informamos que no mês {month}, temos os seguintes dias disponíveis: {days}.\n\n"
            f"Caso algum destes dias atenda a sua necessidade, será necessário que acesse o número de protocolo #{agenda.id} "
            "para conseguir realizar a alteração de data e nos reenviar o formulário.\n"
            f"{public_update_url(agenda)}\n\n"
            "Aguardamos o seu retorno e agradecemos a atenção e a sua admiração! Esperamos te encontrar logo!\n\n"
            "Atenciosamente,\n\n"
            "Superintendência da Operação Lei Seca."
        ),
    )

def message_for_status(agenda, status):
    if status == Agenda.Status.PENDING:
        return (
            f"Solicitação recebida - Protocolo #{agenda.id}",
            (
                "Prezado(a) solicitante,\n\n"
                "Agradecemos o seu interesse em contar com a Operação Lei Seca e pela oportunidade de construirmos, "
                "juntos, ações que promovam a conscientização e a preservação de vidas no trânsito.\n\n"
                "Recebemos a sua solicitação com satisfação e informamos que ela será analisada por nossa equipe.\n\n"
                "Confira abaixo os dados do seu protocolo:\n\n"
                f"{agenda_details(agenda)}\n\n"
                "Enquanto aguarda o nosso retorno, lhe convidamos a acompanhar as ações, campanhas e novidades da "
                "Operação Lei Seca por meio de nossas redes sociais, especialmente em nosso Instagram: "
                f"{INSTAGRAM_URL}.\n\n"
                "Atenciosamente,\n"
                "Superintendência da Operação Lei Seca."
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

    email = build_email(subject, body, recipients)
    return send_email_safely(email, f"status da agenda #{agenda.id}")


def send_agenda_available_dates_email(agenda, month, days, custom_message=""):
    recipients = agenda_recipients(agenda)
    if not recipients:
        return False

    subject, body = available_dates_message(agenda, month, days, custom_message=custom_message)
    email = build_email(subject, body, recipients)
    return send_email_safely(email, f"datas disponiveis da agenda #{agenda.id}")


def send_satisfaction_survey_email(report):
    if not report.agenda_id:
        return False
    recipients = agenda_recipients(report.agenda)
    if not recipients:
        return False
    survey = get_or_create_survey(report)
    subject = f"Pesquisa de satisfação - Protocolo #{report.agenda_id}"
    body = (
        "Prezado(a),\n\n"
        "Sabia que a opinião é muito importante para nós? Ela contribui diretamente para o aprimoramento das próximas ações e atividades que desenvolvemos. Por isso, gostaríamos de te convidar a compartilhar sua experiência por meio da nossa Pesquisa de Satisfação.\n\n"
        "Sua participação é rápida, voluntária, segura e essencial para identificar oportunidades de melhoria.\n\n"
        f"Para responder, acesse o link abaixo:\n{survey_url(survey)}\n\n"
        "Agradecemos, desde já, pelo seu tempo e pela valiosa contribuição.\n\n"
        "Atenciosamente,\n"
        "Superintendência da Operação Lei Seca"
    )
    email = build_email(subject, body, recipients)
    sent = send_email_safely(email, f"pesquisa de satisfacao da agenda #{report.agenda_id}")
    if not sent:
        return False
    survey.sent_at = timezone.now()
    survey.save(update_fields=["sent_at", "updated_at"])
    return True


def send_accessibility_rejection_email(data):
    # Suporta tanto dicionário (vindo do serializer/request) quanto instância de Agenda
    if hasattr(data, "external_email"):
        external_email = data.external_email
        contact_email = getattr(data, "contact_email", "")
        institution = getattr(data, "institution_location", "") or getattr(data, "location", "") or "instituição"
    else:
        external_email = data.get("external_email")
        contact_email = data.get("contact_email")
        institution = data.get("institution_location") or data.get("location") or "instituição"

    recipients = []
    for email in [external_email, contact_email]:
        if email and email.strip():
            recipients.append(email.strip())
    if not recipients:
        return False

    subject = "Recusa de solicitação - Operação Lei Seca"
    body = (
        "Prezado(a)!\n\n"
        "Agradecemos o interesse em receber a palestra da Operação Lei Seca novamente!\n\n"
        "Durante a análise técnica, após a última palestra no local indicado na solicitação, verificamos que, "
        "ele ainda não possui todas as condições de acessibilidade necessárias para garantir a participação segura e "
        "confortável de todos os integrantes de nossa equipe, especialmente de nossos palestrantes cadeirantes, "
        "que participam ativamente das ações educativas.\n\n"
        "Gostaríamos de destacar que a inclusão é um valor fundamental para nós!\n\n"
        "Permanecemos à disposição e teremos grande satisfação em reavaliar a solicitação caso, futuramente, "
        "o espaço receba as adequações necessárias de acessibilidade.\n\n"
        "Agradecemos pela compreensão!\n\n"
        "Atenciosamente,\n"
        "Superintendência da Operação Lei Seca."
    )
    email = build_email(subject, body, recipients)
    return send_email_safely(email, f"recusa de acessibilidade para {institution}")

def send_report_confirmation_email(report):
    agenda = report.agenda
    if not agenda:
        return False
        
    recipients = []
    if agenda.chief_ref and getattr(agenda.chief_ref, 'email', None):
        recipients.append(getattr(agenda.chief_ref, 'email'))
    elif agenda.responsible and agenda.responsible.email:
        recipients.append(agenda.responsible.email)
        
    if not recipients:
        return False

    subject = f"Confirmação de Recebimento - Relatório Técnico #{agenda.id}"
    operation_date_str = report.operation_date.strftime("%d/%m/%Y") if report.operation_date else "N/A"
    body = (
        f"Olá,\n\n"
        f"Confirmamos o recebimento com sucesso do relatório técnico para a agenda '{agenda.title}' (Protocolo #{agenda.id}), preenchido pela equipe {report.team}.\n"
        f"Agradecemos o envio. O relatório já está disponível no painel da plataforma para consulta.\n\n"
        f"Data da operação: {operation_date_str}\n\n"
        f"Atenciosamente,\n\n"
        f"Sistema Agenda Lei Seca"
    )
    email = build_email(subject, body, recipients)
    return send_email_safely(email, f"confirmacao de relatorio #{agenda.id}")

def send_report_reminder_email(agenda):
    recipients = []
    if agenda.chief_ref and getattr(agenda.chief_ref, 'email', None):
        recipients.append(getattr(agenda.chief_ref, 'email'))
    elif agenda.responsible and agenda.responsible.email:
        recipients.append(agenda.responsible.email)
        
    if not recipients:
        return False

    subject = f"Lembrete: Preencha o Relatório Técnico - Protocolo #{agenda.id}"
    operation_date_str = agenda.date.strftime("%d/%m/%Y") if agenda.date else "N/A"
    body = (
        f"Olá,\n\n"
        f"Lembramos que a operação para a agenda '{agenda.title}' (Protocolo #{agenda.id}) ocorreu no dia de hoje ({operation_date_str}).\n"
        f"Por favor, acesse o painel da plataforma e preencha o Relatório Técnico referente a esta operação.\n\n"
        f"Atenciosamente,\n\n"
        f"Sistema Agenda Lei Seca"
    )
    email = build_email(subject, body, recipients)
    return send_email_safely(email, f"lembrete de relatorio #{agenda.id}")
