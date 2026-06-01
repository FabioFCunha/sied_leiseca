from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.models import User


class AgendaPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == "destroy":
            return request.user.role == User.Role.ADMIN
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == User.Role.ADMIN:
            return True
        if request.method in SAFE_METHODS:
            if user.role == User.Role.SUPERVISOR:
                return obj.sector_id == user.sector_id
            return obj.created_by_id == user.id or obj.responsible_id == user.id
        if user.role == User.Role.SUPERVISOR:
            return obj.sector_id == user.sector_id
        return obj.created_by_id == user.id and obj.status == obj.Status.PENDING


class AdminOrReadSectorPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == User.Role.ADMIN
