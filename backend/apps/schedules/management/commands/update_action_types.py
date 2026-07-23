"""
Management command para padronizar os registros de ActionType
conforme a nova classificação oficial da Educação OLS.

Registros oficiais são ativados/criados.
Registros obsoletos são desativados (is_active=False).
Nenhum registro é apagado.
Execução segura e repetível via update_or_create.
"""
from django.core.management.base import BaseCommand
from apps.schedules.models import ActionType


# IDs dos registros que devem permanecer ativos
KEEP_ACTIVE_IDS = {6, 28, 29, 39, 42, 53}

# Novos registros a criar (caso não existam)
NEW_RECORDS = [
    "Palestra Escola Privada",
    "Palestra Escola Pública",
]


class Command(BaseCommand):
    help = "Padroniza os registros de ActionType conforme a classificação oficial da Educação OLS."

    def handle(self, *args, **options):
        activated = 0
        created = 0
        deactivated = 0

        # 1. Garantir que os registros oficiais existentes estejam ativos
        for record in ActionType.objects.filter(id__in=KEEP_ACTIVE_IDS):
            if not record.is_active:
                record.is_active = True
                record.save(update_fields=["is_active"])
                activated += 1
                self.stdout.write(self.style.SUCCESS(f"  Ativado: {record.name} (id={record.id})"))
            else:
                self.stdout.write(f"  Já ativo: {record.name} (id={record.id})")

        # 2. Criar novos registros necessários
        for name in NEW_RECORDS:
            obj, was_created = ActionType.objects.update_or_create(
                name=name,
                defaults={"is_active": True},
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  Criado: {obj.name} (id={obj.id})"))
            else:
                self.stdout.write(f"  Já existe: {obj.name} (id={obj.id})")

        # 3. Desativar todos os registros que NÃO estão na lista oficial
        new_names = set(NEW_RECORDS)
        obsolete = ActionType.objects.filter(is_active=True).exclude(id__in=KEEP_ACTIVE_IDS).exclude(name__in=new_names)
        for record in obsolete:
            record.is_active = False
            record.save(update_fields=["is_active"])
            deactivated += 1
            self.stdout.write(self.style.WARNING(f"  Desativado: {record.name} (id={record.id})"))

        # Resumo
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Concluído: {activated} ativados, {created} criados, {deactivated} desativados."))
