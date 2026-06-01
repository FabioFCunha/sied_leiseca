from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "role", "sector", "is_active", "is_staff")
    list_filter = ("role", "sector", "is_active")
    search_fields = ("email", "full_name")
    ordering = ("full_name",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Perfil", {"fields": ("full_name", "role", "sector")}),
    )
