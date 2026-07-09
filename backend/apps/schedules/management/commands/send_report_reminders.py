import logging
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.schedules.models import Agenda, EducationReport
from apps.schedules.emails import send_report_reminder_email

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Dispara lembretes de fim de dia para chefes preencherem o relatorio tecnico."

    def handle(self, *args, **options):
        today = date.today()
        # Buscar agendas do dia que não foram canceladas e que não possuem relatório enviado
        agendas = Agenda.objects.filter(
            date=today,
            status__in=[Agenda.Status.APPROVED, Agenda.Status.COMPLETED]
        ).exclude(
            technical_reports__status=EducationReport.ReportStatus.SUBMITTED
        ).distinct()

        sent_count = 0
        for agenda in agendas:
            try:
                if send_report_reminder_email(agenda):
                    sent_count += 1
            except Exception as e:
                logger.error(f"Erro ao enviar lembrete para agenda #{agenda.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"{sent_count} lembretes enviados com sucesso."))
