from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .emails import send_accessibility_rejection_email
from .models import Agenda, AgendaHistory


ACCESSIBILITY_REJECTION_DELAY = timedelta(minutes=5)
ACCESSIBILITY_REJECTION_REASON = (
    "Solicitação recusada por restrição de acessibilidade: no último evento foi identificado que "
    "o local não atende às condições necessárias para receber a equipe com cadeirantes."
)


def schedule_accessibility_rejection(agenda, block, now=None):
    if not block:
        return agenda
    due_at = (now or timezone.now()) + ACCESSIBILITY_REJECTION_DELAY
    agenda.accessibility_block = block
    agenda.accessibility_rejection_due_at = due_at
    agenda.accessibility_rejection_sent_at = None
    agenda.save(update_fields=[
        "accessibility_block",
        "accessibility_rejection_due_at",
        "accessibility_rejection_sent_at",
        "updated_at",
    ])
    AgendaHistory.objects.create(
        agenda=agenda,
        changed_by=agenda.created_by,
        action="RECUSA_ACESSIBILIDADE_AGENDADA",
        snapshot={
            "accessibility_block_id": block.id,
            "accessibility_rejection_due_at": due_at.isoformat(),
            "reason": block.reason,
        },
    )
    return agenda


def process_due_accessibility_rejections(now=None, limit=50):
    now = now or timezone.now()
    processed = 0
    queryset = (
        Agenda.objects.select_related("accessibility_block", "created_by")
        .filter(
            accessibility_rejection_due_at__isnull=False,
            accessibility_rejection_due_at__lte=now,
            accessibility_rejection_sent_at__isnull=True,
        )
        .order_by("accessibility_rejection_due_at", "id")[:limit]
    )
    for agenda in queryset:
        block = agenda.accessibility_block
        if block and not block.is_active:
            agenda.accessibility_block = None
            agenda.accessibility_rejection_due_at = None
            agenda.save(update_fields=["accessibility_block", "accessibility_rejection_due_at", "updated_at"])
            continue

        if agenda.status != Agenda.Status.CANCELLED or agenda.cancel_reason != ACCESSIBILITY_REJECTION_REASON:
            agenda.status = Agenda.Status.CANCELLED
            agenda.cancel_reason = ACCESSIBILITY_REJECTION_REASON
            agenda.save(update_fields=["status", "cancel_reason", "updated_at"])
            AgendaHistory.objects.create(
                agenda=agenda,
                changed_by=agenda.created_by,
                action="RECUSA_ACESSIBILIDADE",
                snapshot={
                    "status": agenda.status,
                    "cancel_reason": agenda.cancel_reason,
                    "accessibility_block_id": block.id if block else None,
                },
            )

        if send_accessibility_rejection_email(agenda):
            agenda.accessibility_rejection_sent_at = now
            agenda.save(update_fields=["accessibility_rejection_sent_at", "updated_at"])
            processed += 1
    return processed
