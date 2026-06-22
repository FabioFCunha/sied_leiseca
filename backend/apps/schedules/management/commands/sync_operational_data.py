import json
import os
from pathlib import Path

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction

from apps.accounts.models import AuditLog, User
from apps.accounts.serializers import sync_all_user_lookups


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures"
DATA_FILE = FIXTURE_DIR / "render_operational_data.json"
USER_MAP_FILE = FIXTURE_DIR / "render_user_map.json"


class Command(BaseCommand):
    help = "Sincroniza uma vez os dados operacionais locais, preservando os usuarios existentes."

    def add_arguments(self, parser):
        parser.add_argument("--sync-version", required=True, help="Identificador unico desta carga.")

    def handle(self, *args, **options):
        version = options["sync_version"].strip()
        marker = {"sync_operational_data_version": version}
        if AuditLog.objects.filter(module="deployment", metadata__sync_operational_data_version=version).exists():
            self.stdout.write(f"Carga operacional {version} ja aplicada.")
            return

        if not DATA_FILE.exists() or not USER_MAP_FILE.exists():
            raise CommandError("Arquivos da carga operacional nao encontrados.")

        records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        local_users = json.loads(USER_MAP_FILE.read_text(encoding="utf-8"))
        fallback_user = self._fallback_user()
        users_by_email = {user.email.lower(): user.pk for user in User.objects.all()}
        users_by_local_pk = {
            int(local_pk): users_by_email.get(email.lower(), fallback_user.pk)
            for local_pk, email in local_users.items()
        }
        remapped = self._remap_user_references(records, users_by_local_pk)

        with transaction.atomic():
            self._clear_operational_data()
            for item in serializers.deserialize("json", json.dumps(remapped)):
                item.save()
            self._reset_sequences()
            sync_all_user_lookups()
            AuditLog.objects.create(
                user=fallback_user,
                action=AuditLog.Action.UPDATE,
                module="deployment",
                description=f"Carga operacional {version} aplicada.",
                metadata=marker,
            )

        self.stdout.write(self.style.SUCCESS(f"Carga operacional {version} aplicada com sucesso."))

    def _fallback_user(self):
        admin_email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@agenda.local").lower()
        user = User.objects.filter(email__iexact=admin_email).first()
        user = user or User.objects.filter(is_superuser=True, is_active=True).order_by("pk").first()
        if not user:
            raise CommandError("Nenhum administrador do Render encontrado para associar os registros.")
        return user

    def _remap_user_references(self, records, users_by_local_pk):
        for record in records:
            model = apps.get_model(record["model"])
            for field in model._meta.fields:
                if field.remote_field and field.remote_field.model is User:
                    local_pk = record["fields"].get(field.name)
                    if local_pk is not None:
                        production_pk = users_by_local_pk.get(int(local_pk))
                        if production_pk is None:
                            raise CommandError(f"Usuario local {local_pk} sem mapeamento.")
                        record["fields"][field.name] = production_pk
        return records

    def _clear_operational_data(self):
        AuditLog.objects.all().delete()
        session_model = apps.get_model("sessions", "Session")
        if session_model._meta.db_table in connection.introspection.table_names():
            session_model.objects.all().delete()
        schedule_models = list(apps.get_app_config("schedules").get_models())
        for model in reversed(schedule_models):
            model.objects.all().delete()

    def _reset_sequences(self):
        schedule_models = list(apps.get_app_config("schedules").get_models())
        statements = connection.ops.sequence_reset_sql(no_style(), schedule_models)
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
