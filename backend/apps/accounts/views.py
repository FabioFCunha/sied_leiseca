import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from config.email_delivery import send_email_message
from config.email_signature import build_signed_email

from .audit import log_audit
from .emails import send_password_setup_email
from .models import AuditLog, User
from .serializers import AuditLogSerializer, LoginSerializer, UserSerializer


logger = logging.getLogger(__name__)

SYSTEM_USER_EMAILS = {"solicitacao.publica@agenda.local"}


def is_system_user(user):
    return bool(user and user.email in SYSTEM_USER_EMAILS)


def can_manage_users(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.is_admin_role))


def delete_user_dependencies(user):
    from apps.schedules.models import (
        Agenda,
        AgendaHistory,
        EducationAction,
        EducationReport,
        EventReport,
        SatisfactionSurvey,
    )

    agendas = Agenda.objects.filter(Q(created_by=user) | Q(responsible=user))
    EducationReport.objects.filter(Q(created_by=user) | Q(agenda__in=agendas)).delete()
    EventReport.objects.filter(created_by=user).delete()
    EducationAction.objects.filter(agenda__in=agendas).delete()
    SatisfactionSurvey.objects.filter(agenda__in=agendas).delete()
    AgendaHistory.objects.filter(changed_by=user).delete()
    agendas.delete()


class UserAccessPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return can_manage_users(request.user)
        return can_manage_users(request.user)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        email = request.data.get("email")
        user = User.objects.filter(email__iexact=email).first()
        if response.status_code == status.HTTP_200_OK and user:
            log_audit(
                request,
                AuditLog.Action.LOGIN,
                "Autenticacao",
                f"Login realizado por {user.full_name or user.email}.",
                user=user,
            )
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_active:
            return Response({"detail": "Usuário inativo."}, status=status.HTTP_401_UNAUTHORIZED)
        data = UserSerializer(request.user).data
        data.pop("password_setup_link", None)
        return Response(data)


class PasswordResetRequestView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get("email")
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        link = None
        if user:
            link = UserSerializer(user).data["password_setup_link"]
            message = build_signed_email(
                subject="Recuperação de senha - SIED Sistema Integrado da Educação",
                body=(
                    "Recebemos uma solicitação para recuperar seu acesso ao SIED Sistema Integrado da Educação.\n\n"
                    "Para definir uma nova senha, acesse o link abaixo:\n"
                    f"{link}\n\n"
                    "Se você não solicitou essa recuperação, ignore esta mensagem."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
                reply_to=[settings.AGENDA_REPLY_TO_EMAIL] if settings.AGENDA_REPLY_TO_EMAIL else None,
            )
            sent, detail = send_email_message(message)
            if not sent:
                logger.error("Nao foi possivel enviar e-mail de recuperacao de senha para %s: %s", user.email, detail)
            log_audit(
                request,
                AuditLog.Action.PASSWORD_RESET,
                "Autenticacao",
                f"Recuperacao de senha solicitada para {user.full_name or user.email}.",
                user=user,
            )
        return Response(
            {
                "detail": "Se o e-mail existir, enviaremos instrucoes para recuperacao de senha.",
                "password_setup_link": link if settings.DEBUG else None,
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
            return Response({"detail": "Link ou senha invalidos."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Link invalido."}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Link expirado ou invalido."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=["password"])
        log_audit(
            request,
            AuditLog.Action.SET_PASSWORD,
            "Autenticacao",
            f"Senha definida para {user.full_name or user.email}.",
            user=user,
        )
        return Response({"detail": "Senha cadastrada com sucesso."})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_superuser:
            return AuditLog.objects.none()
        queryset = AuditLog.objects.select_related("user").all()
        params = self.request.query_params
        if params.get("user"):
            queryset = queryset.filter(user_id=params["user"])
        if params.get("action"):
            queryset = queryset.filter(action=params["action"])
        if params.get("module"):
            queryset = queryset.filter(module__iexact=params["module"])
        if params.get("date_from"):
            queryset = queryset.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            queryset = queryset.filter(created_at__date__lte=params["date_to"])
        if params.get("q"):
            term = params["q"].strip()
            queryset = queryset.filter(
                Q(description__icontains=term)
                | Q(module__icontains=term)
                | Q(user__full_name__icontains=term)
                | Q(user__email__icontains=term)
                | Q(ip_address__icontains=term)
            )
        return queryset


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, UserAccessPermission]

    @action(detail=True, methods=["post"], url_path="send-password-link")
    def send_password_link(self, request, pk=None):
        user = self.get_object()
        if is_system_user(user):
            return Response({"detail": "Usuário técnico do sistema não pode receber link de senha."}, status=status.HTTP_400_BAD_REQUEST)
        data = UserSerializer(user, context=self.get_serializer_context()).data
        sent, email_error = send_password_setup_email(user, data["password_setup_link"])
        log_audit(
            request,
            AuditLog.Action.PASSWORD_LINK,
            "Usuarios",
            f"Link de senha gerado para {user.full_name or user.email}.",
            {"target_user_id": user.id, "email_sent": sent},
        )
        return Response(
            {
                "detail": "Link de senha enviado por e-mail." if sent else f"Nao foi possivel enviar o e-mail; copie o link de senha manualmente. Erro: {email_error}",
                "password_setup_link": data["password_setup_link"],
                "password_setup_email_sent": sent,
                "password_setup_email_error": email_error,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.id == request.user.id:
            return Response({"detail": "Voce nao pode excluir o proprio usuario conectado."}, status=status.HTTP_400_BAD_REQUEST)
        if is_system_user(instance):
            return Response({"detail": "Usuário técnico do sistema não pode ser excluído."}, status=status.HTTP_400_BAD_REQUEST)
        target = {"target_user_id": instance.id, "email": instance.email, "role": instance.role}
        label = instance.full_name or instance.email
        try:
            with transaction.atomic():
                delete_user_dependencies(instance)
                response = super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Não foi possível excluir todos os vínculos deste usuário automaticamente."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if response.status_code < 400:
            log_audit(
                request,
                AuditLog.Action.DELETE,
                "Usuarios",
                f"Usuario excluido: {label}.",
                target,
            )
        return response

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = UserSerializer(user, context=self.get_serializer_context()).data
        sent, email_error = send_password_setup_email(user, data["password_setup_link"])
        log_audit(
            request,
            AuditLog.Action.CREATE,
            "Usuarios",
            f"Usuario cadastrado: {user.full_name or user.email}.",
            {"target_user_id": user.id, "role": user.role, "email_sent": sent},
        )
        data["password_setup_email_sent"] = sent
        data["password_setup_email_error"] = email_error
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        if is_system_user(self.get_object()):
            return Response({"detail": "Usuário técnico do sistema não pode ser editado."}, status=status.HTTP_400_BAD_REQUEST)
        response = super().update(request, *args, **kwargs)
        if response.status_code < 400:
            user = self.get_object()
            log_audit(
                request,
                AuditLog.Action.UPDATE,
                "Usuarios",
                f"Usuario atualizado: {user.full_name or user.email}.",
                {"target_user_id": user.id, "role": user.role},
            )
        return response

    def get_queryset(self):
        queryset = User.objects.select_related("sector").exclude(email__in=SYSTEM_USER_EMAILS).order_by("full_name")
        user = self.request.user
        if can_manage_users(user):
            return queryset
        return queryset.filter(id=user.id)

    @action(detail=False, methods=["post"], url_path="ping", permission_classes=[IsAuthenticated])
    def ping(self, request):
        user = request.user
        user.last_activity = timezone.now()
        user.save(update_fields=["last_activity"])
        return Response({"status": "ok"})

    @action(detail=False, methods=["get"], url_path="online", permission_classes=[IsAuthenticated, UserAccessPermission])
    def online(self, request):
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
        online_users = User.objects.filter(last_activity__gte=five_minutes_ago).exclude(email__in=SYSTEM_USER_EMAILS).order_by("full_name")
        serializer = self.get_serializer(online_users, many=True)
        return Response(serializer.data)
