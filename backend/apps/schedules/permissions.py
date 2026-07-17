from django.db.models import Q
from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.models import User


def team_agenda_filter(user, prefix=""):
    if not (user.sector_id and user.sector and user.sector.name):
        return Q(pk__in=[])
    return Q(**{f"{prefix}team_ref__name__iexact": user.sector.name}) | Q(**{f"{prefix}team_name__iexact": user.sector.name})


def supervisor_agenda_filter(user, prefix=""):
    query = Q(**{f"{prefix}responsible": user}) | Q(**{f"{prefix}designated_users": user})
    source_id = f"user:{user.id}"
    query |= Q(**{f"{prefix}chief_ref__source_id": source_id})
    cpf = "".join(char for char in str(user.cpf or "") if char.isdigit())
    if cpf and len(cpf) == 11:
        formatted_cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        query |= Q(**{f"{prefix}chief_ref__cpf": cpf}) | Q(**{f"{prefix}chief_ref__cpf": formatted_cpf})
    elif cpf:
        query |= Q(**{f"{prefix}chief_ref__cpf": cpf})
    query |= team_agenda_filter(user, prefix)
    return query


def agent_agenda_filter(user):
    query = Q(created_by=user) | Q(responsible=user) | Q(designated_users=user)
    cpf = "".join(char for char in str(user.cpf or "") if char.isdigit())
    if cpf:
        query |= Q(agents_ref__cpf=cpf)
    if user.full_name:
        query |= Q(agents_ref__name__iexact=user.full_name) | Q(agents__icontains=user.full_name)
    query |= team_agenda_filter(user)
    return query


def supervisor_can_read_agenda(user, agenda):
    if agenda.created_by_id == user.id or agenda.responsible_id == user.id:
        return True
    if agenda.designated_users.filter(id=user.id).exists():
        return True
    source_id = f"user:{user.id}"
    if agenda.chief_ref and agenda.chief_ref.source_id == source_id:
        return True
    cpf = "".join(char for char in str(user.cpf or "") if char.isdigit())
    chief_cpf = "".join(char for char in str(getattr(agenda.chief_ref, "cpf", "") or "") if char.isdigit())
    if cpf and chief_cpf and cpf == chief_cpf:
        return True
    if user.sector_id and user.sector and user.sector.name:
        sector_name = user.sector.name.casefold()
        team_ref_name = agenda.team_ref.name.casefold() if agenda.team_ref else ""
        if sector_name in {team_ref_name, (agenda.team_name or "").casefold()}:
            return True
    return False


def user_can_read_agenda(user, agenda):
    if agenda.created_by_id == user.id or agenda.responsible_id == user.id:
        return True
    if agenda.designated_users.filter(id=user.id).exists():
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
        if user.is_admin_role or user.role in [User.Role.VISITOR, User.Role.ALMOXARIFADO]:
            return True
        if request.method in SAFE_METHODS:
            if user.role == User.Role.SUPERVISOR:
                return supervisor_can_read_agenda(user, obj)
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
        if request.user.role in [User.Role.VISITOR, User.Role.ALMOXARIFADO]:
            if request.method in SAFE_METHODS and request.user.sector and request.user.sector.name == "Subsecretaria":
                pass
            else:
                return False
        if view.__class__.__name__ == "ShiftScheduleViewSet":
            if view.action in {"create", "update", "destroy"}:
                return self._can_manage_shift_schedule(request.user)
            if view.action == "partial_update":
                if self._can_manage_shift_schedule(request.user):
                    return True
                if request.data and set(request.data.keys()) == {"checked_members"}:
                    return request.user.role == User.Role.SUPERVISOR
                return False
            if view.action == "absence":
                return self._can_manage_shift_schedule(request.user) or request.user.role == User.Role.SUPERVISOR
        if view.action in {"approve", "reject", "destroy"}:
            return self._can_manage_shift_schedule(request.user)
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role in [User.Role.VISITOR, User.Role.ALMOXARIFADO]:
            if request.method in SAFE_METHODS and request.user.sector and request.user.sector.name == "Subsecretaria":
                pass
            else:
                return False
        if view.__class__.__name__ == "ShiftScheduleViewSet":
            if view.action in {"update", "destroy"}:
                return self._can_manage_shift_schedule(request.user)
            if view.action in {"absence", "partial_update"}:
                if self._can_manage_shift_schedule(request.user):
                    return True

                if view.action == "partial_update":
                    if not request.data or set(request.data.keys()) != {"checked_members"}:
                        return False

                if request.user.role != User.Role.SUPERVISOR:
                    self.message = "Somente o chefe escalado, Gestor ou Administrador pode gerenciar a frequência desta equipe."
                    return False

                user_id_str = f"user:{request.user.id}"
                cpf = "".join(c for c in (request.user.cpf or "") if c.isdigit())
                formatted_cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf

                def match_chief(chief):
                    if chief.source_id == user_id_str: return True
                    if cpf and chief.cpf and (chief.cpf == cpf or chief.cpf == formatted_cpf): return True
                    return False

                if obj.team:
                    removed_ids = set(obj.removed_chiefs.values_list("id", flat=True))
                    for chief in obj.team.chiefs.all():
                        if chief.id not in removed_ids and match_chief(chief):
                            return True

                for chief in obj.extra_chiefs.all():
                    if match_chief(chief):
                        return True

                self.message = "Somente o chefe escalado, Gestor ou Administrador pode gerenciar a frequência desta equipe."
                return False
        if view.action in {"approve", "reject", "destroy"}:
            return self._can_manage_shift_schedule(request.user)
        return True
