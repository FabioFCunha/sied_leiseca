from django.conf import settings
from apps.accounts.models import User
from rest_framework.permissions import BasePermission


def _normalized_sector_name(user):
    return str(getattr(getattr(user, "sector", None), "name", "") or "").strip()


class HasInspectionSyncToken(BasePermission):
    message = "Autenticacao tecnica invalida."

    def has_permission(self, request, view):
        expected = str(getattr(settings, "INSPECTION_SYNC_TOKEN", "") or "")
        if not expected:
            return False

        auth_header = str(request.headers.get("Authorization", "") or "").strip()
        provided = ""
        if auth_header.lower().startswith("bearer "):
            provided = auth_header[7:].strip()
        else:
            provided = str(request.headers.get("X-Inspection-Sync-Token", "") or "").strip()

        return bool(provided) and provided == expected


class CanReviewInspectionStatistics(BasePermission):
    message = "Apenas usuarios da OLS/CooAdm podem homologar relatorios de Fiscalizacao."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return (
            user.role == User.Role.VISITOR
            and getattr(user, "sector", None) is not None
            and _normalized_sector_name(user) == "OLS/CooAdm"
        )


class CanViewInspectionStatisticsDashboard(BasePermission):
    message = "Voce nao tem permissao para consultar a Estatistica de Fiscalizacao."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.role in {User.Role.ADMIN, User.Role.MANAGER, User.Role.SUPERVISOR}:
            return True
        return (
            user.role == User.Role.VISITOR
            and getattr(user, "sector", None) is not None
            and _normalized_sector_name(user) == "OLS/CooAdm"
        )
