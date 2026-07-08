from django.db.models import Q
from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.models import User


def agent_agenda_filter(user):
    query = Q(created_by=user) | Q(responsible=user)
    cpf = "".join(char for char in str(user.cpf or "") if char.isdigit())
    if cpf:
        query |= Q(agents_ref__cpf=cpf)
    if user.full_name:
        query |= Q(agents_ref__name__iexact=user.full_name) | Q(agents__icontains=user.full_name)
    if user.sector_id and user.sector and user.sector.name:
        query |= Q(team_ref__name__iexact=user.sector.name) | Q(team_name__iexact=user.sector.name)
    return query


def user_can_read_agenda(user, agenda):
    if agenda.created_by_id == user.id or agenda.responsible_id == user.id:
        return True
    cpf = "".join(char for char in str(user.cpf or "") if char.isdigit())
    if cpf and agenda.agents_ref.filter(cpf=cpf).exists():
        return True
    if user.full_name:
        if agenda.agents_ref.filter(name__iexact=user.full_name).exists():
            return True
        if user.full_name.casefold() in (agenda.agents or "").casefold():
            return True
    if user.sector_id and user.sector and user.sector.name:
        sector_name = user.sector.name.casefold()
        team_ref_name = agenda.team_ref.name.casefold() if agenda.team_ref else ""
        return sector_name in {team_ref_name, (agenda.team_name or "").casefold()}
    return False


class AgendaPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == "destroy":
            return request.user.is_admin_role
        if request.method not in SAFE_METHODS:
            return request.user.is_admin_role
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_admin_role or user.role == User.Role.VISITOR:
            return True
        if request.method in SAFE_METHODS:
            if user.role == User.Role.SUPERVISOR:
                return obj.sector_id == user.sector_id
            return user_can_read_agenda(user, obj)
        return False


class AdminOrReadSectorPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_admin_role


class ShiftSchedulePermission(BasePermission):
    def _can_manage_shift_schedule(self, user):
        return getattr(user, "is_admin_role", False)

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == User.Role.VISITOR:
            if request.method in SAFE_METHODS and request.user.sector and request.user.sector.name == "Subsecretaria":
                pass
            else:
                return False
        if view.__class__.__name__ == "ShiftScheduleViewSet" and view.action in {"create", "update", "partial_update", "destroy", "absence"}:
            return self._can_manage_shift_schedule(request.user)
        if view.action in {"approve", "reject", "destroy"}:
            return self._can_manage_shift_schedule(request.user)
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == User.Role.VISITOR:
            if request.method in SAFE_METHODS and request.user.sector and request.user.sector.name == "Subsecretaria":
                pass
            else:
                return False
        if view.__class__.__name__ == "ShiftScheduleViewSet" and view.action in {"update", "partial_update", "destroy", "absence"}:
            return self._can_manage_shift_schedule(request.user)
        if view.action in {"approve", "reject", "destroy"}:
            return self._can_manage_shift_schedule(request.user)
        return True
