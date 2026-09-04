from django.http import JsonResponse
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.authentication import JWTAuthentication

from .access_control import EDUCATION, INSPECTION, can_write_request, has_access_area


class UserAreaAccessMiddleware:
    PUBLIC_PREFIXES = ("/api/auth/", "/api/public/", "/api/webhooks/")
    NEUTRAL_PREFIXES = ("/api/users/", "/api/audit-logs/")
    READ_ONLY_WRITE_EXCEPTIONS = (
        "/api/auth/lgpd-consent/",
        "/api/users/ping/",
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_authentication = JWTAuthentication()

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            try:
                authenticated = self.jwt_authentication.authenticate(request)
            except APIException:
                authenticated = None
            if authenticated:
                user, token = authenticated
                request.user = user
                request.auth = token
        if not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        if (
            not can_write_request(user, request.method)
            and request.path not in self.READ_ONLY_WRITE_EXCEPTIONS
        ):
            return JsonResponse(
                {"detail": "Seu acesso é somente para visualização."},
                status=403,
            )

        if request.path.startswith(self.PUBLIC_PREFIXES + self.NEUTRAL_PREFIXES):
            return self.get_response(request)
        required_area = (
            INSPECTION
            if request.path.startswith("/api/inspection/")
            else EDUCATION
        )
        if not has_access_area(user, required_area):
            return JsonResponse(
                {"detail": "Você não possui acesso a esta modalidade."},
                status=403,
            )
        return self.get_response(request)
