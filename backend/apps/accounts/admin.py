from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import AuditLog, User
from .serializers import sync_user_lookup, find_bound_conflict, user_lookup_source_id

def validate_user_lookup_conflict(user, cpf):
    if not cpf:
        return
    from apps.schedules.models import Chief, Agent, Support
    model = {
        User.Role.SUPERVISOR: Chief,
        User.Role.USER: Agent,
        User.Role.SUPPORT: Support,
    }.get(user.role)
    if not model:
        return
        
    expected_source_id = user_lookup_source_id(user)
    conflict, reason = find_bound_conflict(
        model=model,
        cpf=cpf,
        name="",  # Não precisamos checar nome aqui para bloqueio
        excluding_source_id=expected_source_id,
    )
    if conflict:
        raise DjangoValidationError({"cpf": "O CPF informado já se encontra vinculado a outro perfil operacional."})


class CustomUserChangeForm(UserChangeForm):
    def clean(self):
        cleaned_data = super().clean()
        validate_user_lookup_conflict(self.instance, cleaned_data.get("cpf"))
        return cleaned_data

class CustomUserCreationForm(UserCreationForm):
    def clean(self):
        cleaned_data = super().clean()
        user = self.instance
        user.role = cleaned_data.get("role", User.Role.USER)
        validate_user_lookup_conflict(user, cleaned_data.get("cpf"))
        return cleaned_data


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ("email", "full_name", "role", "sector", "is_active", "is_on_vacation", "is_staff")
    list_filter = ("role", "sector", "is_active", "is_on_vacation")
    search_fields = ("email", "full_name")
    ordering = ("full_name",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Perfil", {"fields": ("full_name", "role", "sector")}),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from django.db import transaction
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from django.contrib import messages
        try:
            with transaction.atomic():
                sync_user_lookup(obj)
        except DRFValidationError as e:
            messages.warning(request, f"Aviso de Sincronização: {e.detail}")
        except Exception as e:
            messages.error(request, f"Erro interno ao sincronizar: {str(e)}")

    def delete_model(self, request, obj):
        from apps.accounts.services import deactivate_user
        deactivate_user(obj)

    def delete_queryset(self, request, queryset):
        from apps.accounts.services import deactivate_user
        for obj in queryset:
            deactivate_user(obj)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "module", "description", "ip_address")
    list_filter = ("action", "module", "created_at")
    search_fields = ("user__email", "user__full_name", "description", "ip_address")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
