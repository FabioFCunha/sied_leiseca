from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import LoginSerializer, UserSerializer


class UserAccessPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_admin_role


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = []


class PasswordResetRequestView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get("email")
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        link = None
        if user:
            link = UserSerializer(user).data["password_setup_link"]
        return Response(
            {
                "detail": "Se o e-mail existir, enviaremos instruções para recuperação de senha.",
                "password_setup_link": link,
            },
            status=status.HTTP_200_OK,
        )


class SetPasswordView(APIView):
    permission_classes = []

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")
        if not uid or not token or not password:
            return Response({"detail": "Link ou senha inválidos."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Link inválido."}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Link expirado ou inválido."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"detail": "Senha cadastrada com sucesso."})


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, UserAccessPermission]

    def get_queryset(self):
        queryset = User.objects.select_related("sector").order_by("full_name")
        user = self.request.user
        if user.is_admin_role:
            return queryset
        if user.is_supervisor_role:
            return queryset.filter(sector_id=user.sector_id, is_active=True)
        return queryset.filter(id=user.id)
