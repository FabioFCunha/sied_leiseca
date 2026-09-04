from django.conf import settings
from apps.accounts.models import User
from rest_framework.permissions import BasePermission

FABIO_CUNHA_CPF = "08922040793"
FABIO_CUNHA_EMAIL = "fabiocunhaosp@gmail.com"


def _only_digits(value):
    return "".join(character for character in str(value or "") if character.isdigit())


def can_review_inspection_report(user):
    """Returns the restricted set of users allowed to decide inspection reports."""
    if not user or not user.is_authenticated:
        return False

    # Existing institutional reviewer access remains unchanged.
    if (
        user.role == User.Role.VISITOR
        and getattr(user, "sector", None) is not None
        and _normalized_sector_name(user) == "OLS/CooAdm"
    ):
        return True

    # Fabio's CPF is the stable primary identifier. Username and email are
    # compatibility fallbacks for deployments where the login was migrated
    # without the CPF field.
    return (
        _only_digits(getattr(user, "cpf", "")) == FABIO_CUNHA_CPF
        or _only_digits(getattr(user, "username", "")) == FABIO_CUNHA_CPF
        or str(getattr(user, "email", "") or "").strip().lower() == FABIO_CUNHA_EMAIL
    )


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
    message = "Voce nao tem permissao para homologar relatorios de Fiscalizacao."

    def has_permission(self, request, view):
        return can_review_inspection_report(getattr(request, "user", None))


class CanViewInspectionStatisticsDashboard(BasePermission):
    message = "Voce nao tem permissao para consultar a Estatistica de Fiscalizacao."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_read_only", False):
            return True
        if user.role in {User.Role.ADMIN, User.Role.MANAGER, User.Role.SUPERVISOR}:
            return True
        return (
            user.role == User.Role.VISITOR
            and getattr(user, "sector", None) is not None
            and _normalized_sector_name(user) == "OLS/CooAdm"
        )
