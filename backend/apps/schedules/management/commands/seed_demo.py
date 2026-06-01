from datetime import date, time, timedelta

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.schedules.models import Agenda, AgendaHistory, Sector
from apps.schedules.views import snapshot_for


class Command(BaseCommand):
    help = "Cria usuários, equipes e agendas iniciais para teste."

    def handle(self, *args, **options):
        operations, _ = Sector.objects.get_or_create(
            name="Operações", defaults={"description": "Escalas e atividades operacionais"}
        )
        support, _ = Sector.objects.get_or_create(
            name="Atendimento", defaults={"description": "Servicos e compromissos com clientes"}
        )
        field, _ = Sector.objects.get_or_create(
            name="Campo", defaults={"description": "Equipes externas"}
        )

        admin = self._user(
            "admin@agenda.local",
            "Admin Agenda",
            User.Role.ADMIN,
            operations,
            "Admin@12345",
            is_staff=True,
            is_superuser=True,
        )
        supervisor = self._user(
            "supervisor@agenda.local",
            "Supervisor Operações",
            User.Role.SUPERVISOR,
            operations,
            "Supervisor@12345",
        )
        regular = self._user(
            "usuario@agenda.local",
            "Usuario Comum",
            User.Role.USER,
            support,
            "Usuario@12345",
        )

        samples = [
            ("Reuniao de alinhamento", operations, supervisor, admin, date.today(), time(9, 0), time(10, 0), "Sala 01", Agenda.Status.APPROVED),
            ("Atendimento tecnico", support, regular, regular, date.today(), time(14, 0), time(15, 30), "Unidade Centro", Agenda.Status.PENDING),
            ("Escala externa", field, supervisor, admin, date.today() + timedelta(days=1), time(8, 0), time(12, 0), "Base Norte", Agenda.Status.APPROVED),
            ("Fechamento semanal", operations, supervisor, supervisor, date.today() + timedelta(days=2), time(16, 0), time(17, 0), "Sala 02", Agenda.Status.COMPLETED),
        ]

        for title, sector, responsible, creator, day, start, end, location, status in samples:
            agenda, created = Agenda.objects.get_or_create(
                title=title,
                date=day,
                start_time=start,
                defaults={
                    "description": f"Agenda de exemplo: {title}.",
                    "end_time": end,
                    "location": location,
                    "vehicle": "VTR-01",
                    "team_name": sector.name,
                    "chief_name": responsible.full_name,
                    "team_phone": "(11) 90000-0000",
                    "agents": "Agente 1; Agente 2",
                    "action_type": "Atividade programada",
                    "institution_location": location,
                    "quantity": 1,
                    "schedule_text": f"{start:%H:%M} as {end:%H:%M}",
                    "address": "Endereço de exemplo",
                    "neighborhood": "Centro",
                    "city": "São Paulo",
                    "external_responsible": responsible.full_name,
                    "external_responsible_phone": "(11) 98888-8888",
                    "external_email": "contato@agenda.local",
                    "audience": "Público interno",
                    "activity_type": "Operacional",
                    "responsible": responsible,
                    "sector": sector,
                    "status": status,
                    "notes": "Registro criado pelo seed inicial.",
                    "created_by": creator,
                },
            )
            if created:
                AgendaHistory.objects.create(
                    agenda=agenda,
                    changed_by=creator,
                    action="CRIACAO_SEED",
                    snapshot=snapshot_for(agenda),
                )

        self.stdout.write(self.style.SUCCESS("Dados iniciais criados/atualizados."))

    def _user(self, email, name, role, sector, password, **flags):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "full_name": name,
                "role": role,
                "sector": sector,
                "is_active": True,
                **flags,
            },
        )
        if created:
            user.set_password(password)
        user.full_name = name
        user.role = role
        user.sector = sector
        for key, value in flags.items():
            setattr(user, key, value)
        user.save()
        return user
