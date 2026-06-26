from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .emails import send_accessibility_rejection_email
from .models import Agenda, AgendaHistory


ACCESSIBILITY_REJECTION_REASON = (
    "Solicitação recusada por restrição de acessibilidade: no último evento foi identificado que "
    "o local não atende às condições necessárias para receber a equipe com cadeirantes."
)


def schedule_accessibility_rejection(agenda, block, *, now=None):
    if not block or not block.is_active:
        return agenda

    agenda.accessibility_block = block
    agenda.accessibility_rejection_due_at = (now or timezone.now()) + timedelta(minutes=5)
    agenda.accessibility_rejection_sent_at = None
    agenda.save(update_fields=[
        "accessibility_block",
        "accessibility_rejection_due_at",
        "accessibility_rejection_sent_at",
        "updated_at",
    ])
    return agenda


def process_accessibility_rejection(agenda, block):
    if not block or not block.is_active:
        return agenda

    agenda.accessibility_block = block
    agenda.status = Agenda.Status.CANCELLED
    agenda.cancel_reason = ACCESSIBILITY_REJECTION_REASON

    if send_accessibility_rejection_email(agenda):
        agenda.accessibility_rejection_sent_at = timezone.now()

    agenda.save(update_fields=[
        "accessibility_block",
        "status",
        "cancel_reason",
        "accessibility_rejection_sent_at",
        "updated_at",
    ])

    AgendaHistory.objects.create(
        agenda=agenda,
        changed_by=agenda.created_by,
        action="RECUSA_ACESSIBILIDADE",
        snapshot={
            "status": agenda.status,
            "cancel_reason": agenda.cancel_reason,
            "accessibility_block_id": block.id,
        },
    )
    return agenda


def process_due_accessibility_rejections(*, now=None):
    reference = now or timezone.now()
    agendas = Agenda.objects.select_related("accessibility_block", "created_by").filter(
        accessibility_block__isnull=False,
        accessibility_rejection_due_at__lte=reference,
        accessibility_rejection_sent_at__isnull=True,
        status=Agenda.Status.PENDING,
    )

    processed = 0
    for agenda in agendas:
        if not agenda.accessibility_block or not agenda.accessibility_block.is_active:
            continue
        process_accessibility_rejection(agenda, agenda.accessibility_block)
        processed += 1
    return processed
