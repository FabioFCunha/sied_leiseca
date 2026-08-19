import json
import logging

logger = logging.getLogger(__name__)
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

def normalize_name(name):
    if not name:
        return ""
    val = name.strip()
    if val.lower() in ["sem bairro", "sem municÃ­pio", "sem municipio"]:
        return val
    t = val.title()
    for prep in [" Da ", " De ", " Do ", " Das ", " Dos "]:
        t = t.replace(prep, prep.lower())
    return t


OPERATIONAL_STATUS_META = {
    "scheduled": ("PRÓXIMA", "Próxima"),
    "in_progress": ("EM ANDAMENTO", "Em andamento"),
    "completed": ("REALIZADA", "Realizada"),
    "cancelled": ("CANCELADA", "Cancelada"),
}

REPORT_STATUS_META = {
    None: ("none", "SEM RELATÓRIO", "Sem relatório"),
    "DRAFT": ("draft", "RASCUNHO", "Rascunho"),
    "PENDING_REVIEW": ("pending_review", "AGUARDANDO CONFERÊNCIA", "Aguardando conferência"),
    "RETURNED": ("returned", "DEVOLVIDO", "Devolvido"),
    "APPROVED": ("approved", "APROVADO", "Aprovado"),
    "SUBMITTED": ("submitted", "ENVIADO", "Enviado"),
}

ATTENDANCE_STATUS_META = {
    "pending": ("PENDENTE", "Pendente"),
    "reported": ("REPORTADA", "Reportada"),
    "approved": ("CONFERIDA", "Conferida"),
}


def build_agenda_operational_window(*, agenda_date, start_time, end_time, tz=None):
    tz = tz or timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(agenda_date, start_time), tz)
    end_date = agenda_date if end_time > start_time else agenda_date + timedelta(days=1)
    end_dt = timezone.make_aware(datetime.combine(end_date, end_time), tz)
    return start_dt, end_dt


def classify_operational_status(*, agenda_date, start_time, end_time, agenda_status, now_dt=None, tz=None):
    status_value = str(agenda_status or "").upper()
    if status_value == Agenda.Status.CANCELLED:
        return "cancelled", *OPERATIONAL_STATUS_META["cancelled"]

    tz = tz or timezone.get_current_timezone()
    now_value = timezone.localtime(now_dt or timezone.now(), tz)
    start_dt, end_dt = build_agenda_operational_window(
        agenda_date=agenda_date,
        start_time=start_time,
        end_time=end_time,
        tz=tz,
    )

    if now_value < start_dt:
        return "scheduled", *OPERATIONAL_STATUS_META["scheduled"]
    if start_dt <= now_value < end_dt:
        return "in_progress", *OPERATIONAL_STATUS_META["in_progress"]
    return "completed", *OPERATIONAL_STATUS_META["completed"]


from django.db import OperationalError, ProgrammingError, transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Avg, Case, Count, F, IntegerField, Q, Sum, Value, When
from django.db.models.functions import ExtractMonth, ExtractYear, TruncMonth
from django.core import signing
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from rest_framework import decorators, parsers, response, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound, APIException
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.audit import log_audit
from apps.accounts.models import AuditLog, User
from apps.accounts.serializers import sync_active_users_for_role

from .models import (
    ActionType,
    Agent,
    Agenda,
    AgendaHistory,
    EducationAction,
    EducationGoal,
    EducationReport,
    EventReport,
    AccessibilityBlocklist,
    Chief,
    Kit,
    Dynamic,
    Material,
    Municipality,
    Neighborhood,
    Region,
    Sector,
    SatisfactionSurvey,
    SatisfactionSurveyModerationHistory,
    ShiftAbsence,
    ReportStatusHistory,
    ShiftSchedule,
    ShiftScheduleChange,
    ShiftSwapRequest,
    Support,
    Team,
    Vehicle,
)
from .permissions import AdminOrReadSectorPermission, AgendaPermission, ShiftSchedulePermission, VisitorReadOnly, agent_agenda_filter, supervisor_agenda_filter
from .emails import (
    PUBLIC_REQUEST_SALT,
    available_dates_message,
    public_update_url,
    send_agenda_available_dates_email,
    send_agenda_status_email,
    send_satisfaction_survey_email,
    send_report_confirmation_email,
)
from .serializers import (
    AccessibilityBlocklistSerializer,
    ActionTypeSerializer,
    AgentSerializer,
    AgendaSerializer,
    EducationReportSerializer,
    EducationGoalSerializer,
    EventReportSerializer,
    ChiefSerializer,
    KitSerializer,
    DynamicSerializer,
    MaterialSerializer,
    MunicipalitySerializer,
    NeighborhoodSerializer,
    RegionSerializer,
    SatisfactionSurveyModerationHistorySerializer,
    PublicAgendaRequestSerializer,
    PublicAgendaRequestRescheduleSerializer,
    SatisfactionSurveySerializer,
    SectorSerializer,
    ShiftScheduleSerializer,
    ShiftSwapRequestSerializer,
    shift_swap_visibility_filter,
    SupportSerializer,
    TeamSerializer,
    VehicleSerializer,
)


def snapshot_for(agenda):
    return {
        "title": agenda.title,
        "date": agenda.date.isoformat(),
        "start_time": agenda.start_time.isoformat(),
        "end_time": agenda.end_time.isoformat(),
        "location": agenda.location,
        "status": agenda.status,
        "origin": agenda.origin,
        "cancel_reason": agenda.cancel_reason,
        "sector_id": agenda.sector_id,
        "responsible_id": agenda.responsible_id,
        "vehicle": agenda.vehicle,
        "team_name": agenda.team_name,
        "action_type": agenda.action_type,
        "city": agenda.city,
        "state": agenda.state,
        "requester_entity_type": agenda.requester_entity_type,
        "participant_range": agenda.participant_range,
        "age_ranges": agenda.age_ranges,
        "accessibility_access": agenda.accessibility_access,
    }


def chief_agenda_filter(user, prefix=""):
    chief_ref_source = f"{prefix}chief_ref__source_id"
    chief_ref_cpf_field = f"{prefix}chief_ref__cpf"
    responsible_field = f"{prefix}responsible"

    query = Q(**{responsible_field: user})

    source_id = f"user:{user.id}"
    query |= Q(**{chief_ref_source: source_id})

    cpf = "".join(char for char in str(user.cpf or "") if char.isdigit())
    if cpf and len(cpf) == 11:
        formatted_cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        query |= Q(**{chief_ref_cpf_field: cpf}) | Q(**{chief_ref_cpf_field: formatted_cpf})
    elif cpf:
        query |= Q(**{chief_ref_cpf_field: cpf})

    return query


def filter_active_user_bound_lookups(queryset):
    active_source_ids = [f"user:{user_id}" for user_id in User.objects.filter(is_active=True).values_list("id", flat=True)]
    return queryset.filter(
        Q(source_id__isnull=True)
        | Q(source_id="")
        | ~Q(source_id__startswith="user:")
        | Q(source_id__in=active_source_ids)
    )


def deactivate_linked_users_for_lookup(instance, role):
    cpf = "".join(char for char in str(instance.cpf or "") if char.isdigit())
    linked_users = User.objects.filter(role=role)
    if cpf:
        linked_users = linked_users.filter(Q(cpf=cpf) | Q(full_name__iexact=instance.name))
    else:
        linked_users = linked_users.filter(full_name__iexact=instance.name)
    linked_users.update(is_active=False)

class SectorViewSet(viewsets.ModelViewSet):
    serializer_class = SectorSerializer
    permission_classes = [IsAuthenticated, AdminOrReadSectorPermission]
    queryset = Sector.objects.all()


class LookupViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, AdminOrReadSectorPermission]


class VehicleViewSet(LookupViewSet):
    serializer_class = VehicleSerializer
    queryset = Vehicle.objects.all()


class TeamViewSet(LookupViewSet):
    serializer_class = TeamSerializer

    def get_queryset(self):
        queryset = Team.objects.filter(is_active=True)
        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Team.objects.all()
        return queryset.order_by("name")


class ChiefViewSet(LookupViewSet):
    serializer_class = ChiefSerializer

    def get_queryset(self):
        queryset = Chief.objects.filter(is_active=True)

        team_id = self.request.query_params.get("team")
        team_name = self.request.query_params.get("team_name")
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        elif team_name:
            queryset = queryset.filter(team__name__iexact=team_name)

        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Chief.objects.all()
        else:
            queryset = filter_active_user_bound_lookups(queryset)
        return queryset.select_related("team").order_by("team__name", "name")

    def perform_destroy(self, instance):
        deactivate_linked_users_for_lookup(instance, User.Role.SUPERVISOR)
        super().perform_destroy(instance)


class AgentViewSet(LookupViewSet):
    serializer_class = AgentSerializer

    def get_queryset(self):
        if self.action in ["retrieve", "update", "partial_update", "destroy"] and self.request.user.is_admin_role:
            return Agent.objects.all().select_related("team").order_by("team__name", "name")
        queryset = Agent.objects.filter(is_active=True).exclude(role__icontains="APOIO")

        team_id = self.request.query_params.get("team")
        team_name = self.request.query_params.get("team_name")
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        elif team_name:
            queryset = queryset.filter(team__name__iexact=team_name)

        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Agent.objects.all()
        else:
            queryset = filter_active_user_bound_lookups(queryset)
        return queryset.select_related("team").order_by("team__name", "name")

    def perform_destroy(self, instance):
        deactivate_linked_users_for_lookup(instance, User.Role.USER)
        super().perform_destroy(instance)


class SupportViewSet(LookupViewSet):
    serializer_class = SupportSerializer

    def get_queryset(self):
        if self.action == "list":
            sync_active_users_for_role(User.Role.SUPPORT)
        if self.action in ["retrieve", "update", "partial_update", "destroy"] and self.request.user.is_admin_role:
            return Support.objects.all().select_related("team").order_by("team__name", "name")
        queryset = Support.objects.filter(is_active=True)

        team_id = self.request.query_params.get("team")
        team_name = self.request.query_params.get("team_name")
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        elif team_name:
            queryset = queryset.filter(team__name__iexact=team_name)

        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Support.objects.all()
        else:
            queryset = filter_active_user_bound_lookups(queryset)
        return queryset.select_related("team").order_by("team__name", "name")

    def perform_destroy(self, instance):
        deactivate_linked_users_for_lookup(instance, User.Role.SUPPORT)
        super().perform_destroy(instance)


class ShiftScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftScheduleSerializer
    permission_classes = [IsAuthenticated, ShiftSchedulePermission]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        queryset = ShiftSchedule.objects.select_related("team", "created_by").prefetch_related(
            "swap_requests",
            "swap_requests__requester",
            "swap_requests__target_team",
            "swap_requests__decided_by",
            "extra_chiefs",
            "extra_agents",
            "extra_supports",
            "removed_chiefs",
            "removed_agents",
            "removed_supports",
            "absent_chiefs",
            "absent_agents",
            "absent_supports",
            "absence_records",
            "member_changes",
            "member_changes__created_by",
        )
        params = self.request.query_params
        if params.get("date"):
            queryset = queryset.filter(date=params["date"])
        if params.get("date_from"):
            queryset = queryset.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            queryset = queryset.filter(date__lte=params["date_to"])
        if params.get("team"):
            queryset = queryset.filter(team_id=params["team"])

        user = self.request.user
        if not user.is_admin_role:
            from apps.schedules.models import Chief, Agent, Support
            source_id = f"user:{user.id}"

            q_filter = Q()
            if user.sector_id and user.sector and user.sector.name:
                q_filter |= Q(team__name__iexact=user.sector.name)

            chief_fallback_q = Q()
            cpf_numeros = "".join(char for char in str(user.cpf or "") if char.isdigit())
            if cpf_numeros and len(cpf_numeros) == 11:
                formatted_cpf = f"{cpf_numeros[:3]}.{cpf_numeros[3:6]}.{cpf_numeros[6:9]}-{cpf_numeros[9:]}"
                chief_fallback_q |= Q(cpf=cpf_numeros) | Q(cpf=formatted_cpf)
            elif cpf_numeros:
                chief_fallback_q |= Q(cpf=cpf_numeros)

            agent_support_fallback_q = Q()
            if cpf_numeros and len(cpf_numeros) == 11:
                agent_support_fallback_q |= Q(cpf=cpf_numeros) | Q(cpf=formatted_cpf)
            elif cpf_numeros:
                agent_support_fallback_q |= Q(cpf=cpf_numeros)
            if user.full_name and user.sector_id and user.sector and user.sector.name:
                agent_support_fallback_q |= Q(name__iexact=user.full_name, team__name__iexact=user.sector.name)

            chief_ids = list(Chief.objects.filter(Q(source_id=source_id) | chief_fallback_q).values_list("id", flat=True)) if (source_id or chief_fallback_q) else []
            agent_ids = list(Agent.objects.filter(Q(source_id=source_id) | agent_support_fallback_q).values_list("id", flat=True)) if (source_id or agent_support_fallback_q) else []
            support_ids = list(Support.objects.filter(Q(source_id=source_id) | agent_support_fallback_q).values_list("id", flat=True)) if (source_id or agent_support_fallback_q) else []

            if chief_ids:
                q_filter |= Q(extra_chiefs__in=chief_ids)
                chief_team_ids = Chief.objects.filter(id__in=chief_ids, team__isnull=False).values_list('team_id', flat=True)
                if chief_team_ids:
                    q_filter |= Q(team_id__in=chief_team_ids)
            if agent_ids:
                q_filter |= Q(extra_agents__in=agent_ids)
                agent_team_ids = Agent.objects.filter(id__in=agent_ids, team__isnull=False).values_list('team_id', flat=True)
                if agent_team_ids:
                    q_filter |= Q(team_id__in=agent_team_ids)
            if support_ids:
                q_filter |= Q(extra_supports__in=support_ids)
                support_team_ids = Support.objects.filter(id__in=support_ids, team__isnull=False).values_list('team_id', flat=True)
                if support_team_ids:
                    q_filter |= Q(team_id__in=support_team_ids)

            if not q_filter:
                return queryset.none()

            queryset = queryset.filter(q_filter).distinct()

        return queryset.order_by("date", "team__name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def _detach_agendas_from_schedule(self, schedule):
        agendas = list(
            Agenda.objects.filter(
                date=schedule.date,
                team_ref_id=schedule.team_id,
            )
            .exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED])
            .prefetch_related("agents_ref")
        )
        for agenda in agendas:
            agenda.team_name = ""
            agenda.team_ref = None
            agenda.chief_name = ""
            agenda.chief_ref = None
            agenda.team_phone = ""
            agenda.agents = ""
            agenda.support_1 = ""
            agenda.support_1_ref = None
            agenda.support_2 = ""
            agenda.support_2_ref = None
            agenda.save(
                update_fields=[
                    "team_name",
                    "team_ref",
                    "chief_name",
                    "chief_ref",
                    "team_phone",
                    "agents",
                    "support_1",
                    "support_1_ref",
                    "support_2",
                    "support_2_ref",
                    "updated_at",
                ]
            )
            agenda.agents_ref.clear()

    def perform_destroy(self, instance):
        with transaction.atomic():
            self._detach_agendas_from_schedule(instance)
            super().perform_destroy(instance)

    def _member_model(self, member_type):
        return {
            ShiftAbsence.MemberType.CHIEF: Chief,
            ShiftAbsence.MemberType.AGENT: Agent,
            ShiftAbsence.MemberType.SUPPORT: Support,
        }.get(member_type)

    def _absence_relation(self, schedule, member_type):
        return {
            ShiftAbsence.MemberType.CHIEF: schedule.absent_chiefs,
            ShiftAbsence.MemberType.AGENT: schedule.absent_agents,
            ShiftAbsence.MemberType.SUPPORT: schedule.absent_supports,
        }.get(member_type)

    def _member_change_relation(self, schedule, action_value, member_type):
        action_map = {
            ShiftScheduleChange.Action.EXTRA: {
                ShiftScheduleChange.MemberType.CHIEF: schedule.extra_chiefs,
                ShiftScheduleChange.MemberType.AGENT: schedule.extra_agents,
                ShiftScheduleChange.MemberType.SUPPORT: schedule.extra_supports,
            },
            ShiftScheduleChange.Action.REMOVED: {
                ShiftScheduleChange.MemberType.CHIEF: schedule.removed_chiefs,
                ShiftScheduleChange.MemberType.AGENT: schedule.removed_agents,
                ShiftScheduleChange.MemberType.SUPPORT: schedule.removed_supports,
            },
        }
        return action_map.get(action_value, {}).get(member_type)

    def _member_home_team_matches_schedule(self, member, schedule):
        return bool(member.team_id and schedule.team_id and member.team_id == schedule.team_id)

    @decorators.action(detail=True, methods=["post"], url_path="member-change")
    def member_change(self, request, pk=None):
        schedule = self.get_object()
        action_value = request.data.get("action")
        member_type = request.data.get("member_type")
        member_id = request.data.get("member_id")
        reason = str(request.data.get("reason") or "").strip()

        if action_value not in ShiftScheduleChange.Action.values:
            return response.Response({"detail": "Informe uma a??o v?lida."}, status=status.HTTP_400_BAD_REQUEST)
        if member_type not in ShiftScheduleChange.MemberType.values:
            return response.Response({"detail": "Informe um tipo de integrante v?lido."}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return response.Response({"detail": "Informe o motivo da altera??o."}, status=status.HTTP_400_BAD_REQUEST)

        lookup_model = self._member_model(member_type)
        relation = self._member_change_relation(schedule, action_value, member_type)
        if not lookup_model or not relation:
            return response.Response({"detail": "N?o foi poss?vel identificar a altera??o solicitada."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            member_id = int(member_id)
        except (TypeError, ValueError):
            return response.Response({"detail": "Informe um integrante v?lido."}, status=status.HTTP_400_BAD_REQUEST)

        member = lookup_model.objects.filter(id=member_id, is_active=True).select_related("team").first()
        if not member:
            return response.Response({"detail": "Integrante n?o encontrado ou inativo."}, status=status.HTTP_404_NOT_FOUND)

        member_belongs_to_team = self._member_home_team_matches_schedule(member, schedule)
        extra_relation = self._member_change_relation(schedule, ShiftScheduleChange.Action.EXTRA, member_type)
        removed_relation = self._member_change_relation(schedule, ShiftScheduleChange.Action.REMOVED, member_type)
        in_extra = extra_relation.filter(id=member.id).exists()
        in_removed = removed_relation.filter(id=member.id).exists()

        if action_value == ShiftScheduleChange.Action.EXTRA:
            if member_belongs_to_team:
                if not in_removed:
                    return response.Response({"detail": "Este integrante titular j? est? ativo na escala."}, status=status.HTTP_400_BAD_REQUEST)
            elif in_extra and not in_removed:
                return response.Response({"detail": "Este integrante extra j? est? na escala."}, status=status.HTTP_400_BAD_REQUEST)
        elif member_belongs_to_team:
            if in_removed:
                return response.Response({"detail": "Este integrante j? foi retirado da escala."}, status=status.HTTP_400_BAD_REQUEST)
        elif not in_extra:
            return response.Response({"detail": "Somente integrantes extras ativos podem ser retirados nesta opera??o."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if action_value == ShiftScheduleChange.Action.EXTRA:
                if member_belongs_to_team:
                    removed_relation.remove(member)
                else:
                    extra_relation.add(member)
                    removed_relation.remove(member)
            else:
                if member_belongs_to_team:
                    removed_relation.add(member)
                else:
                    extra_relation.remove(member)

            ShiftScheduleChange.objects.create(
                schedule=schedule,
                action=action_value,
                member_type=member_type,
                member_id=member.id,
                member_name=member.name,
                reason=reason,
                created_by=request.user,
            )
            schedule.updated_by = request.user
            schedule.save(update_fields=["updated_by", "updated_at"])

        serializer = self.get_serializer(self.get_queryset().get(pk=schedule.pk))
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post", "delete"], url_path="absence")
    def absence(self, request, pk=None):
        schedule = self.get_object()
        member_type = request.data.get("member_type")
        member_id = request.data.get("member_id")
        lookup_model = self._member_model(member_type)
        relation = self._absence_relation(schedule, member_type)

        if not lookup_model or not relation:
            return response.Response({"detail": "Informe o tipo de integrante da falta."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            member_id = int(member_id)
        except (TypeError, ValueError):
            return response.Response({"detail": "Informe o integrante da falta."}, status=status.HTTP_400_BAD_REQUEST)

        member = lookup_model.objects.filter(id=member_id, is_active=True).first()
        if not member:
            return response.Response({"detail": "Integrante nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            ShiftAbsence.objects.filter(schedule=schedule, member_type=member_type, member_id=member_id).delete()
            relation.remove(member)
        else:
            reason = str(request.data.get("reason") or "").strip()
            if not reason or reason.lower() == "falta":
                return response.Response({"detail": "Informe a justificativa da falta."}, status=status.HTTP_400_BAD_REQUEST)
            absence, _created = ShiftAbsence.objects.update_or_create(
                schedule=schedule,
                member_type=member_type,
                member_id=member_id,
                defaults={
                    "member_name": member.name,
                    "reason": reason,
                    "created_by": request.user,
                },
            )
            if request.FILES.get("attachment"):
                absence.attachment = request.FILES["attachment"]
                absence.save(update_fields=["attachment", "updated_at"])
            relation.add(member)

        schedule.updated_by = request.user
        schedule.save(update_fields=["updated_by", "updated_at"])
        schedule = self.get_queryset().get(pk=schedule.pk)
        serializer = self.get_serializer(schedule)
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], url_path="add-member")
    def add_member(self, request, pk=None):
        schedule = self.get_object()
        member_type = request.data.get("member_type")
        member_id = request.data.get("member_id")
        lookup_model = self._member_model(member_type)
        if not lookup_model:
            return response.Response({"detail": "Tipo de integrante invÃ¡lido."}, status=status.HTTP_400_BAD_REQUEST)

        member = lookup_model.objects.filter(id=member_id, is_active=True).first()
        if not member:
            return response.Response({"detail": "Integrante nÃ£o encontrado."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            from apps.schedules.models import ShiftManualInclusion
            ShiftManualInclusion.objects.get_or_create(
                schedule=schedule,
                member_type=member_type,
                member_id=member.id,
                defaults={
                    "member_name": member.name,
                    "added_by": request.user
                }
            )
            if member_type == ShiftAbsence.MemberType.CHIEF:
                schedule.extra_chiefs.add(member)
                schedule.removed_chiefs.remove(member)
            elif member_type == ShiftAbsence.MemberType.AGENT:
                schedule.extra_agents.add(member)
                schedule.removed_agents.remove(member)
            elif member_type == ShiftAbsence.MemberType.SUPPORT:
                schedule.extra_supports.add(member)
                schedule.removed_supports.remove(member)

            schedule.updated_by = request.user
            schedule.save(update_fields=["updated_by", "updated_at"])

        serializer = self.get_serializer(self.get_queryset().get(pk=schedule.pk))
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post", "delete"], url_path="remove-member")
    def remove_member(self, request, pk=None):
        schedule = self.get_object()
        member_type = request.data.get("member_type")
        member_id = request.data.get("member_id")

        from apps.schedules.models import ShiftManualInclusion
        inclusion = ShiftManualInclusion.objects.filter(schedule=schedule, member_type=member_type, member_id=member_id).first()

        if not inclusion:
            return response.Response({"detail": "Apenas integrantes incluÃ­dos manualmente podem ser removidos."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            inclusion.delete()
            lookup_model = self._member_model(member_type)
            member = lookup_model.objects.filter(id=member_id).first()
            if member:
                if member_type == ShiftAbsence.MemberType.CHIEF:
                    schedule.extra_chiefs.remove(member)
                elif member_type == ShiftAbsence.MemberType.AGENT:
                    schedule.extra_agents.remove(member)
                elif member_type == ShiftAbsence.MemberType.SUPPORT:
                    schedule.extra_supports.remove(member)

        serializer = self.get_serializer(self.get_queryset().get(pk=schedule.pk))
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], url_path="report-attendance")
    def report_attendance(self, request, pk=None):
        from django.utils import timezone
        schedule = self.get_object()
        schedule.attendance_reported = True
        schedule.attendance_reported_at = timezone.now()
        schedule.attendance_approved = False
        schedule.attendance_approved_at = None
        schedule.save(update_fields=["attendance_reported", "attendance_reported_at", "attendance_approved", "attendance_approved_at"])
        return response.Response({"detail": "FrequÃªncia reportada com sucesso."})

    @decorators.action(detail=True, methods=["post"], url_path="approve-attendance")
    def approve_attendance(self, request, pk=None):
        from django.utils import timezone
        schedule = self.get_object()
        schedule.attendance_approved = True
        schedule.attendance_approved_at = timezone.now()
        schedule.save(update_fields=["attendance_approved", "attendance_approved_at"])
        return response.Response({"detail": "FrequÃªncia aprovada."})


class ShiftSwapRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSwapRequestSerializer
    permission_classes = [IsAuthenticated, ShiftSchedulePermission]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        queryset = ShiftSwapRequest.objects.select_related(
            "schedule",
            "schedule__team",
            "target_team",
            "requester",
            "decided_by",
        )
        params = self.request.query_params
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("schedule"):
            queryset = queryset.filter(schedule_id=params["schedule"])
        if params.get("date_from"):
            queryset = queryset.filter(schedule__date__gte=params["date_from"])
        if params.get("date_to"):
            queryset = queryset.filter(schedule__date__lte=params["date_to"])
        queryset = queryset.filter(shift_swap_visibility_filter(self.request.user))
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)

    def _decide(self, request, pk, decision):
        swap = self.get_object()
        can_approve = getattr(request.user, "is_admin_role", False)
        if swap.requester_id == request.user.id and not can_approve:
            return response.Response(
                {"detail": "O solicitante nao pode aprovar ou rejeitar a propria troca."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if swap.status != ShiftSwapRequest.Status.PENDING:
            return response.Response(
                {"detail": "Esta solicitacao ja foi analisada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        swap.status = decision
        swap.decided_by = request.user
        swap.decided_at = timezone.now()
        swap.decision_note = request.data.get("decision_note", "")
        swap.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
        serializer = self.get_serializer(swap)
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._decide(request, pk, ShiftSwapRequest.Status.APPROVED)

    @decorators.action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decide(request, pk, ShiftSwapRequest.Status.REJECTED)


class ActionTypeViewSet(LookupViewSet):
    serializer_class = ActionTypeSerializer
    queryset = ActionType.objects.all()

class RegionViewSet(LookupViewSet):
    serializer_class = RegionSerializer
    queryset = Region.objects.all()


class MunicipalityViewSet(LookupViewSet):
    serializer_class = MunicipalitySerializer
    queryset = Municipality.objects.all()


class NeighborhoodViewSet(LookupViewSet):
    serializer_class = NeighborhoodSerializer
    queryset = Neighborhood.objects.all()


class KitViewSet(LookupViewSet):
    queryset = Kit.objects.all()
    serializer_class = KitSerializer


class DynamicViewSet(LookupViewSet):
    queryset = Dynamic.objects.all()
    serializer_class = DynamicSerializer


class MaterialViewSet(LookupViewSet):
    serializer_class = MaterialSerializer
    queryset = Material.objects.all()


class AgendaViewSet(viewsets.ModelViewSet):
    @decorators.action(detail=True, methods=["post", "delete"], url_path="designated-absence")
    def designated_absence(self, request, pk=None):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        agenda = self.get_object()

        user_id = request.data.get("user_id")
        if not user_id:
            return response.Response({"detail": "Informe o ID do participante."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return response.Response({"detail": "Informe um ID de participante vÃ¡lido."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            return response.Response({"detail": "Participante nÃ£o encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if not agenda.designated_users.filter(id=user_id).exists():
            return response.Response({"detail": "Participante nÃ£o estÃ¡ designado para esta Ordem de ServiÃ§o."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if request.method == "DELETE":
                agenda.absent_designated_users.remove(user)
            else:
                agenda.absent_designated_users.add(user)

        serializer = self.get_serializer(agenda)
        return response.Response(serializer.data)
    serializer_class = AgendaSerializer
    permission_classes = [IsAuthenticated, AgendaPermission]

    def get_scoped_queryset(self):
        user = self.request.user
        queryset = Agenda.objects.select_related("responsible", "sector", "created_by").prefetch_related(
            "history",
            "satisfaction_surveys",
            "designated_users",
        ).annotate(linked_requests_count_annotated=Count('linked_requests', distinct=True))

        is_calendar_view = self.request.query_params.get("calendar_view") == "1"

        if user.is_admin_role:
            return queryset
        elif user.role == User.Role.ALMOXARIFADO:
            return queryset
        elif user.role == User.Role.VISITOR:
            return queryset.exclude(status__in=[Agenda.Status.PENDING, Agenda.Status.CANCELLED])
        elif user.role == User.Role.SUPERVISOR:
            if is_calendar_view:
                return queryset
            supervisor_filter = supervisor_agenda_filter(user)
            return queryset.filter(supervisor_filter).distinct()
        return queryset.filter(agent_agenda_filter(user)).distinct()

    def get_queryset(self):
        scoped = self.get_scoped_queryset()
        params = self.request.query_params
        user = self.request.user

        # Reports become available after the agenda end_time.
        if params.get("reportable") == "true":
            from django.utils import timezone
            now = timezone.localtime(timezone.now())
            scoped = scoped.filter(
                Q(date__lt=now.date()) | Q(date=now.date(), end_time__lte=now.time()),
                service_order_number__isnull=False,
            ).exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED])

        if params.get("date"):
            scoped = scoped.filter(date=params["date"])
        if params.get("date_from"):
            scoped = scoped.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            scoped = scoped.filter(date__lte=params["date_to"])
        if params.get("status"):
            scoped = scoped.filter(status=params["status"])
        if params.get("origin"):
            scoped = scoped.filter(origin=params["origin"])
        request_source_filter = (
            Q(origin=Agenda.Origin.PUBLIC_FORM)
            | Q(source_id__startswith="internal-request:")
            | Q(source_id__startswith="appsheet:")
            | Q(sector__name__in=["SolicitaÃ§Ãµes externas", "SolicitaÃ§Ãµes internas"])
            | Q(created_by__email="solicitacao.publica@agenda.local")
            | Q(responsible__email="solicitacao.publica@agenda.local")
        )
        if params.get("source") == "public":
            scoped = scoped.filter(
                Q(origin=Agenda.Origin.PUBLIC_FORM)
                | Q(created_by__email="solicitacao.publica@agenda.local")
                | Q(responsible__email="solicitacao.publica@agenda.local")
            )
        search_term = params.get("q", "").strip()
        exact_search_filter = None

        if search_term:
            identifier_match = re.match(
                (
                    r"(?i)^\s*"
                    r"(protocolo|prot|os)"
                    r"\s*"
                    r"(?:[:#\-]\s*)?"
                    r"(?:n\s*(?:Âº|º|°|o)?\s*)?"
                    r"(\d+)"
                ),
                search_term,
            )
            number_match = re.fullmatch(
                r"\d+",
                search_term,
            )

            if identifier_match:
                number = int(identifier_match.group(2))
                exact_search_filter = Q(
                    service_order_number=number
                )
            elif number_match:
                number = int(number_match.group(0))
                exact_search_filter = (
                    Q(id=number)
                    | Q(service_order_number=number)
                )

        if params.get("source") == "requests":
            if exact_search_filter is None:
                scoped = scoped.filter(request_source_filter)
            else:
                scoped = scoped.filter(request_source_filter | exact_search_filter)
        if params.get("sector"):
            scoped = scoped.filter(sector_id=params["sector"])
        if params.get("user"):
            scoped = scoped.filter(created_by_id=params["user"])
        if params.get("responsible"):
            scoped = scoped.filter(responsible_id=params["responsible"])
        if params.get("chief"):
            term = params["chief"].strip()
            scoped = scoped.filter(Q(chief_name__icontains=term) | Q(chief_ref__name__icontains=term))
        if params.get("vehicle"):
            scoped = scoped.filter(vehicle_ref_id=params["vehicle"])
        if params.get("team"):
            TeamModel = Agenda._meta.get_field("team_ref").related_model
            selected_team = TeamModel.objects.filter(
                id=params["team"]
            ).first()

            if selected_team:
                selected_name = selected_team.name.strip()
                scoped = scoped.filter(
                    Q(team_ref__name__iexact=selected_name)
                    | Q(team_name__iexact=selected_name)
                )
            else:
                scoped = scoped.none()
        if params.get("municipality"):
            scoped = scoped.filter(municipality_ref_id=params["municipality"])
        if params.get("region"):
            scoped = scoped.filter(municipality_ref__region_id=params["region"])
        if params.get("action_type"):
            scoped = scoped.filter(action_type_ref_id=params["action_type"])
        if exact_search_filter is not None:
            scoped = scoped.filter(exact_search_filter)
        elif search_term:
            search_filter = (
                Q(source_id__icontains=search_term)
                | Q(title__icontains=search_term)
                | Q(institution_location__icontains=search_term)
                | Q(location__icontains=search_term)
                | Q(address__icontains=search_term)
                | Q(neighborhood__icontains=search_term)
                | Q(city__icontains=search_term)
                | Q(external_responsible__icontains=search_term)
                | Q(agents__icontains=search_term)
            )
            scoped = scoped.filter(search_filter)
        if params.get("pending_report") == "true":
            if user.is_admin_role:
                scoped = scoped.filter(technical_reports__isnull=True, date__gte="2026-07-01").exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED])
            else:
                scoped = scoped.filter(technical_reports__isnull=True, date__gte="2026-07-08").exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED])
        if params.get("order") == "latest":
            return (
                scoped.distinct()
                .annotate(
                    pending_rank=Case(
                        When(status=Agenda.Status.PENDING, then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField(),
                    )
                )
                .order_by("pending_rank", "-id")
            )
        return scoped.distinct().order_by("date", "start_time")

    def perform_create(self, serializer):
        agenda = serializer.save(created_by=self.request.user)
        AgendaHistory.objects.create(
            agenda=agenda,
            changed_by=self.request.user,
            action="CRIACAO",
            snapshot=snapshot_for(agenda),
        )
        log_audit(
            self.request,
            AuditLog.Action.CREATE,
            "Agendas",
            f"Agenda criada: protocolo {agenda.id}.",
            {"agenda_id": agenda.id, "title": agenda.title, "status": agenda.status},
        )

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        agenda = serializer.save()
        if previous_status != agenda.status:
            action = f"STATUS_{agenda.status}"
            audit_action = AuditLog.Action.STATUS_CHANGE
            audit_description = f"Status da agenda {agenda.id} alterado de {previous_status} para {agenda.status}."
        else:
            action = "ALTERACAO"
            audit_action = AuditLog.Action.UPDATE
            audit_description = f"Agenda atualizada: protocolo {agenda.id}."
        AgendaHistory.objects.create(
            agenda=agenda,
            changed_by=self.request.user,
            action=action,
            snapshot=snapshot_for(agenda),
        )
        log_audit(
            self.request,
            audit_action,
            "Agendas",
            audit_description,
            {"agenda_id": agenda.id, "title": agenda.title, "previous_status": previous_status, "status": agenda.status},
        )
        skip_email = self.request.query_params.get("skip_email", "").lower() == "true"
        if previous_status != agenda.status and not skip_email:
            transaction.on_commit(lambda: send_agenda_status_email(agenda, agenda.status))

    def perform_destroy(self, instance):
        metadata = {"agenda_id": instance.id, "title": instance.title, "status": instance.status}
        label = instance.id
        super().perform_destroy(instance)
        log_audit(
            self.request,
            AuditLog.Action.DELETE,
            "Agendas",
            f"Agenda excluida: protocolo {label}.",
            metadata,
        )

    def _block_visitor_write(self):
        if self.request.user and self.request.user.is_authenticated and self.request.user.role == User.Role.VISITOR:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("O perfil Visitante possui apenas permissão de consulta neste módulo.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._block_visitor_write()
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            blockers = []
            if instance.technical_reports.exists():
                blockers.append("relatório técnico")
            if hasattr(instance, "event_report"):
                blockers.append("relatório de evento")
            if instance.satisfaction_surveys.exists():
                blockers.append("avaliaÃ§Ã£o de satisfaÃ§Ã£o")
            if len(blockers) == 1:
                joined = blockers[0]
            elif len(blockers) == 2:
                joined = " e ".join(blockers)
            else:
                joined = ", ".join(blockers[:-1]) + f" e {blockers[-1]}" if blockers else "registros vinculados"
            return response.Response(
                {"detail": f"Esta solicitaÃ§Ã£o nÃ£o pode ser excluÃ­da porque jÃ¡ possui {joined} vinculado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @decorators.action(detail=True, methods=["post"], url_path="reopen")
    def reopen(self, request, pk=None):
        if not request.user.is_admin_role:
            return response.Response({"detail": "PermissÃ£o negada."}, status=status.HTTP_403_FORBIDDEN)

        agenda = self.get_object()
        if agenda.status != Agenda.Status.CANCELLED:
            return response.Response({"detail": "A solicitaÃ§Ã£o nÃ£o estÃ¡ cancelada."}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get("reason", "").strip()
        previous_valid_status = Agenda.Status.PENDING
        for hist in agenda.history.order_by("-created_at"):
            hist_status = hist.snapshot.get("status")
            if hist_status and hist_status != Agenda.Status.CANCELLED:
                previous_valid_status = hist_status
                break

        agenda.status = previous_valid_status
        agenda.save(update_fields=["status"])

        snapshot = snapshot_for(agenda)
        snapshot["previous_status"] = Agenda.Status.CANCELLED
        snapshot["new_status"] = previous_valid_status
        snapshot["observation"] = reason

        AgendaHistory.objects.create(
            agenda=agenda,
            changed_by=request.user,
            action="REOPENED",
            snapshot=snapshot,
        )

        log_audit(
            request,
            AuditLog.Action.STATUS_CHANGE,
            "Agendas",
            f"Agenda reaberta: protocolo {agenda.id}. ObservaÃ§Ã£o: {reason}" if reason else f"Agenda reaberta: protocolo {agenda.id}.",
            {"agenda_id": agenda.id, "title": agenda.title, "previous_status": Agenda.Status.CANCELLED, "status": previous_valid_status, "reopen_observation": reason},
        )
        return response.Response({"detail": "SolicitaÃ§Ã£o reaberta com sucesso.", "status": previous_valid_status})

    @decorators.action(detail=True, methods=["post"], url_path="send-available-dates")
    def send_available_dates(self, request, pk=None):
        agenda = self.get_object()
        month = str(request.data.get("month", "")).strip()
        days = str(request.data.get("days", "")).strip()
        message = str(request.data.get("message", "")).strip()
        if not month or not days:
            return response.Response(
                {"detail": "Informe o mes e os dias disponiveis."},
                status=400,
            )
        sent = send_agenda_available_dates_email(agenda, month, days, custom_message=message)
        AgendaHistory.objects.create(
            agenda=agenda,
            changed_by=request.user,
            action="EMAIL_DATAS_DISPONIVEIS",
            snapshot={**snapshot_for(agenda), "available_month": month, "available_days": days, "email_sent": sent, "message": message},
        )
        log_audit(
            request,
            AuditLog.Action.EMAIL,
            "Agendas",
            f"E-mail de datas disponiveis gerado para agenda {agenda.id}.",
            {"agenda_id": agenda.id, "month": month, "email_sent": sent},
        )
        return response.Response(
            {"detail": "Mensagem de datas disponiveis enviada." if sent else "Solicitacao sem e-mail de destino."}
        )

    @decorators.action(detail=True, methods=["get"], url_path="available-dates")
    def available_dates(self, request, pk=None):
        agenda = self.get_object()
        from apps.schedules.serializers import get_next_available_dates

        suggested = get_next_available_dates(agenda.date, limit=6)
        days = ", ".join(day.strftime("%d/%m/%Y") for day in suggested)
        month = suggested[0].strftime("%m/%Y") if suggested else ""
        _, message = available_dates_message(
            agenda,
            month,
            days or "nenhuma data disponÃ­vel nos prÃ³ximos dias",
        )
        return response.Response(
            {
                "dates": [{"date": day.isoformat(), "label": day.strftime("%d/%m/%Y")} for day in suggested],
                "month": month,
                "days": days,
                "message": message,
            }
        )

    @decorators.action(detail=True, methods=["post"], url_path="satisfaction-survey-link")
    def satisfaction_survey_link(self, request, pk=None):
        agenda = self.get_object()
        survey = agenda.satisfaction_surveys.order_by("-created_at").first()
        if not survey:
            report = agenda.technical_reports.order_by("-created_at").first()
            token = signing.dumps(
                {"agenda": agenda.id, "report": report.id if report else None},
                salt="agenda-satisfaction-survey",
            )
            survey = SatisfactionSurvey.objects.create(
                agenda=agenda,
                report=report,
                token=token,
                requester_email=agenda.external_email or agenda.contact_email,
                team=(report.team if report else agenda.team_name) or "",
                chief_name=agenda.chief_name or (agenda.chief_ref.name if agenda.chief_ref else ""),
            )
        return response.Response(
            {
                "token": survey.token,
                "url": f"{settings.FRONTEND_URL.rstrip('/')}/pesquisa-satisfacao/{survey.token}",
                "answered_at": survey.answered_at,
            }
        )

    @decorators.action(detail=False, methods=["get"])
    def dashboard(self, request):
        from django.core.cache import cache
        import hashlib

        query_string = request.META.get('QUERY_STRING', '')
        user_id = request.user.id if request.user.is_authenticated else 0
        cache_key = f"agenda_dash_{user_id}_{query_string}"
        cache_key = hashlib.md5(cache_key.encode('utf-8')).hexdigest()

        cached_data = cache.get(cache_key)
        if cached_data:
            return response.Response(cached_data)

        today = timezone.localdate()
        request_source_filter = (
            Q(origin=Agenda.Origin.PUBLIC_FORM)
            | Q(source_id__startswith="internal-request:")
            | Q(source_id__startswith="appsheet:")
            | Q(sector__name__in=["SolicitaÃ§Ãµes externas", "SolicitaÃ§Ãµes internas"])
            | Q(created_by__email="solicitacao.publica@agenda.local")
            | Q(responsible__email="solicitacao.publica@agenda.local")
        )
        def unscoped_dashboard_queryset():
            return Agenda.objects.select_related("responsible", "sector", "created_by").prefetch_related(
                "history",
                "satisfaction_surveys",
            ).filter(date__gte="2026-07-09")

        def apply_dashboard_filters(scoped, ignore_status=False):
            params = request.query_params
            if params.get("date"):
                scoped = scoped.filter(date=params["date"])
            if params.get("date_from"):
                scoped = scoped.filter(date__gte=params["date_from"])
            if params.get("date_to"):
                scoped = scoped.filter(date__lte=params["date_to"])
            if not ignore_status and params.get("status"):
                scoped = scoped.filter(status=params["status"])
            if params.get("origin"):
                scoped = scoped.filter(origin=params["origin"])
            if params.get("sector"):
                scoped = scoped.filter(sector_id=params["sector"])
            if params.get("user"):
                scoped = scoped.filter(created_by_id=params["user"])
            if params.get("responsible"):
                scoped = scoped.filter(responsible_id=params["responsible"])
            if params.get("vehicle"):
                scoped = scoped.filter(vehicle_ref_id=params["vehicle"])
            if params.get("team"):
                TeamModel = Agenda._meta.get_field("team_ref").related_model
                selected_team = TeamModel.objects.filter(
                    id=params["team"]
                ).first()

                if selected_team:
                    selected_name = selected_team.name.strip()
                    scoped = scoped.filter(
                        Q(team_ref__name__iexact=selected_name)
                        | Q(team_name__iexact=selected_name)
                    )
                else:
                    scoped = scoped.none()
            if params.get("municipality"):
                scoped = scoped.filter(municipality_ref_id=params["municipality"])
            if params.get("action_type"):
                scoped = scoped.filter(action_type_ref_id=params["action_type"])
            if params.get("institution"):
                institution_term = params["institution"].strip()
                scoped = scoped.filter(
                    Q(title__icontains=institution_term)
                    | Q(institution_location__icontains=institution_term)
                    | Q(location__icontains=institution_term)
                    | Q(external_responsible__icontains=institution_term)
                )
            if params.get("service_order"):
                service_order = "".join(char for char in str(params["service_order"]) if char.isdigit())
                if service_order:
                    scoped = scoped.filter(service_order_number=int(service_order))
            if params.get("q"):
                term = params["q"].strip()
                search_filter = (
                    Q(source_id__icontains=term)
                    | Q(title__icontains=term)
                    | Q(institution_location__icontains=term)
                    | Q(location__icontains=term)
                    | Q(address__icontains=term)
                    | Q(neighborhood__icontains=term)
                    | Q(city__icontains=term)
                    | Q(external_responsible__icontains=term)
                    | Q(agents__icontains=term)
                )
                if term.isdigit():
                    search_filter |= Q(id=int(term)) | Q(service_order_number=int(term))
                scoped = scoped.filter(search_filter)
            return scoped.distinct()

        qs = apply_dashboard_filters(unscoped_dashboard_queryset())
        base_qs = unscoped_dashboard_queryset()
        total = qs.count()
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        previous_week_start = week_start - timedelta(days=7)
        previous_week_end = week_start - timedelta(days=1)
        month_start = today.replace(day=1)
        previous_month_end = month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)
        now = timezone.localtime().time()

        def pct(current, previous):
            if previous is None:
                return None
            if previous == 0:
                return 100 if current else 0
            return round(((current - previous) / previous) * 100, 1)

        def format_period(start, end):
            if not start or not end:
                return "periodo anterior"
            start_label = start.strftime("%d/%m/%Y")
            end_label = end.strftime("%d/%m/%Y")
            if start == end:
                return start_label
            return f"{start_label} a {end_label}"

        def shift_year(value):
            try:
                return value.replace(year=value.year - 1)
            except ValueError:
                return value.replace(year=value.year - 1, day=28)

        def comparison_range():
            compare = request.query_params.get("compare", "previous_period")
            date_value = request.query_params.get("date")
            date_from = request.query_params.get("date_from")
            date_to = request.query_params.get("date_to")
            if date_value:
                start = end = date.fromisoformat(date_value)
            elif date_from and date_to:
                start = date.fromisoformat(date_from)
                end = date.fromisoformat(date_to)
            elif date_from:
                start = date.fromisoformat(date_from)
                end = today
            elif date_to:
                end = date.fromisoformat(date_to)
                start = end
            else:
                start = today - timedelta(days=29)
                end = today

            if compare == "previous_year":
                return shift_year(start), shift_year(end), compare

            days = (end - start).days + 1
            previous_end = start - timedelta(days=1)
            previous_start = previous_end - timedelta(days=days - 1)
            return previous_start, previous_end, compare

        def selected_range():
            date_value = request.query_params.get("date")
            date_from = request.query_params.get("date_from")
            date_to = request.query_params.get("date_to")
            if date_value:
                start = end = date.fromisoformat(date_value)
            elif date_from and date_to:
                start = date.fromisoformat(date_from)
                end = date.fromisoformat(date_to)
            elif date_from:
                start = date.fromisoformat(date_from)
                end = today
            elif date_to:
                end = date.fromisoformat(date_to)
                start = end
            else:
                start = today - timedelta(days=29)
                end = today
            return start, end

        def dashboard_base_queryset():
            scoped = unscoped_dashboard_queryset()
            if request.query_params.get("sector"):
                scoped = scoped.filter(sector_id=request.query_params["sector"])
            if request.query_params.get("municipality"):
                scoped = scoped.filter(municipality_ref_id=request.query_params["municipality"])
            if request.query_params.get("region"):
                scoped = scoped.filter(municipality_ref__region_id=request.query_params["region"])
            if request.query_params.get("user"):
                scoped = scoped.filter(created_by_id=request.query_params["user"])
            if request.query_params.get("responsible"):
                scoped = scoped.filter(responsible_id=request.query_params["responsible"])
            if request.query_params.get("q"):
                term = request.query_params["q"].strip()
                search_filter = (
                    Q(source_id__icontains=term)
                    | Q(title__icontains=term)
                    | Q(institution_location__icontains=term)
                    | Q(location__icontains=term)
                    | Q(address__icontains=term)
                    | Q(neighborhood__icontains=term)
                    | Q(city__icontains=term)
                    | Q(external_responsible__icontains=term)
                    | Q(agents__icontains=term)
                )
                if term.isdigit():
                    search_filter |= Q(id=int(term)) | Q(service_order_number=int(term))
                scoped = scoped.filter(search_filter)
            return scoped

        def parse_material_distribution(value):
            rows = []
            for line in (value or "").splitlines():
                text = line.strip()
                if not text:
                    continue
                text = re.sub(r"\[\s*\]", "| 0", text)
                if "|" in text:
                    name, quantity = [part.strip() for part in text.rsplit("|", 1)]
                else:
                    match = re.match(r"^(?P<name>.+?)\s+-\s*(?P<quantity>\d+)\s*$", text)
                    if not match:
                        continue
                    name = match.group("name").strip()
                    quantity = match.group("quantity")
                quantity_match = re.search(r"\d+", str(quantity))
                if not name or not quantity_match:
                    continue
                total = int(quantity_match.group(0))
                if total > 0:
                    rows.append((name, total))
            return rows

        def distributed_materials_summary(scoped):
            action_scope = EducationAction.objects.filter(
                Q(agenda_id__in=scoped.values("id")) | Q(report__agenda_id__in=scoped.values("id")),
                report__status=EducationReport.ReportStatus.APPROVED,
            ).distinct()
            totals = Counter()
            for distribution in action_scope.values_list(
                "distribution_materials_distributed", flat=True
            ):
                for name, quantity in parse_material_distribution(distribution):
                    totals[name] += quantity
            items = [{"label": label, "value": value} for label, value in totals.most_common(8)]
            return {"total": sum(totals.values()), "items": items}

        def action_team_queryset():
            scoped = apply_dashboard_filters(unscoped_dashboard_queryset(), ignore_status=True).filter(
                Q(status=Agenda.Status.COMPLETED) | Q(technical_reports__status="APPROVED")
            )
            return scoped

        previous_start, previous_end, compare_mode = comparison_range()
        comparison_qs = dashboard_base_queryset()
        if previous_start and previous_end:
            comparison_qs = comparison_qs.filter(date__gte=previous_start, date__lte=previous_end)
        else:
            comparison_qs = None
        comparison_label = f"vs {format_period(previous_start, previous_end)}"

        qs_base = apply_dashboard_filters(unscoped_dashboard_queryset(), ignore_status=True)

        today_count = qs_base.filter(date=today).count()
        yesterday_count = base_qs.filter(date=yesterday).count()
        pending = qs_base.filter(status=Agenda.Status.PENDING, service_order_number__isnull=True).count()
        approved = qs_base.filter(status=Agenda.Status.APPROVED, service_order_number__isnull=True).count()
        cancelled = qs_base.filter(status=Agenda.Status.CANCELLED).count()
        completed = qs_base.filter(
            service_order_number__isnull=False,
            technical_reports__status="APPROVED"
        ).distinct().count()
        in_progress = qs_base.filter(date=today, start_time__lte=now, end_time__gte=now).exclude(status__in=[Agenda.Status.CANCELLED, Agenda.Status.COMPLETED]).count()
        upcoming_qs = qs.filter(date__gte=today).order_by("date", "start_time")
        upcoming_count = upcoming_qs.count()
        today_agents = set()
        for agenda in qs.filter(date=today).prefetch_related("agents_ref"):
            today_agents.update(agenda.agents_ref.values_list("id", flat=True))
            if not agenda.agents_ref.exists() and agenda.agents:
                today_agents.update(
                    name.strip().casefold()
                    for name in agenda.agents.replace(",", " - ").split(" - ")
                    if name.strip()
                )
        today_agents_count = len(today_agents)

        rows = list(
            qs.select_related("responsible", "sector")
            .values(
                "id",
                "title",
                "date",
                "start_time",
                "end_time",
                "status",
                "updated_at",
                "responsible__full_name",
                "sector__name",
                "team_name",
                "location",
            )
        )

        by_date = Counter(row["date"] for row in rows)
        line_start, line_end = selected_range()
        if request.query_params.get("chart_group") == "month":
            month_labels = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            by_month = Counter(row["date"].month for row in rows)
            line_series = [
                {"label": month_labels[month - 1], "value": by_month[month]}
                for month in range(line_start.month, line_end.month + 1)
            ]
        elif line_start == line_end:
            scheduled_hours = [row["start_time"].hour for row in rows if row["start_time"]]
            first_hour = min(scheduled_hours) if scheduled_hours else 0
            last_hour = max(scheduled_hours) if scheduled_hours else 23
            by_hour = Counter(scheduled_hours)
            line_series = [
                {"label": f"{hour:02d}:00", "value": by_hour[hour]}
                for hour in range(first_hour, last_hour + 1)
            ]
        else:
            line_days = max((line_end - line_start).days + 1, 1)
            line_series = [
                {"label": (line_start + timedelta(days=index)).strftime("%d/%m"), "value": by_date[line_start + timedelta(days=index)]}
                for index in range(line_days)
            ]
        weekly = qs.filter(date__gte=week_start, date__lte=today).count()
        previous_week = base_qs.filter(date__gte=previous_week_start, date__lte=previous_week_end).count()
        monthly = qs.filter(date__gte=month_start, date__lte=today).count()
        previous_month = base_qs.filter(date__gte=previous_month_start, date__lte=previous_month_end).count()

        by_team_counter = Counter(
            (
                row.get("team_ref__name")
                or row.get("team_name")
                or "Sem equipe"
            ).strip()
            for row in action_team_queryset().values("team_ref__name", "team_name")
        )
        by_team_actions = [
            {"label": label, "value": value}
            for label, value in by_team_counter.most_common(8)
        ]
        external_request_filter = (
            Q(created_by__email="solicitacao.publica@agenda.local")
            | Q(responsible__email="solicitacao.publica@agenda.local")
        )
        external_requests = qs.filter(external_request_filter).count()
        internal_requests = qs.exclude(external_request_filter).count()
        by_user = []
        visible_statuses = [
            (Agenda.Status.PENDING, "Pendente"),
            (Agenda.Status.APPROVED, "Aprovada"),
            (Agenda.Status.CANCELLED, "Cancelada"),
        ]
        by_status = [
            {"status": status, "label": label, "total": qs.filter(status=status).count()}
            for status, label in visible_statuses
        ]
        by_municipality_counter = Counter(
            normalize_name(
                row.get("municipality_ref__name")
                or row.get("city")
                or "Sem municÃ­pio"
            )
            for row in qs.values("municipality_ref__name", "city")
        )
        by_municipality = [
            {"label": label, "value": value}
            for label, value in by_municipality_counter.most_common(8)
        ]
        realized_qs = apply_dashboard_filters(unscoped_dashboard_queryset(), ignore_status=True).filter(
            Q(status=Agenda.Status.COMPLETED) | Q(technical_reports__status="APPROVED")
        )

        by_neighborhood_counter = Counter(
            normalize_name(
                row.get("neighborhood_ref__name")
                or row.get("neighborhood")
                or "Sem bairro"
            )
            for row in realized_qs.values("neighborhood_ref__name", "neighborhood")
        )
        by_neighborhood = [
            {"label": label, "value": value}
            for label, value in by_neighborhood_counter.most_common(8)
        ]

        heatmap = defaultdict(int)
        approved_rows = list(qs_base.filter(status=Agenda.Status.APPROVED).values("date", "start_time"))
        for row in approved_rows:
            day = row["date"].weekday()
            hour = row["start_time"].hour if row["start_time"] else 0
            slot = f"{max(6, min(21, hour)):02d}:00"
            heatmap[(day, slot)] += 1
        heatmap_rows = [
            {"day": day, "slot": slot, "total": total}
            for (day, slot), total in sorted(heatmap.items())
        ]

        recent = [
            {
                "id": row["id"],
                "title": row["title"],
                "date": row["date"].isoformat(),
                "time": row["start_time"].isoformat(timespec="minutes") if row["start_time"] else "",
                "status": row["status"],
                "sector": row.get("team_name") or row["sector__name"],
                "responsible": row["responsible__full_name"],
                "updated_at": row["updated_at"].isoformat(),
                "location": row["location"],
            }
            for row in sorted(rows, key=lambda item: item["updated_at"], reverse=True)[:12]
        ]
        field_teams = [
            {
                "id": row["id"],
                "team": row.get("team_name") or row["sector__name"] or "Sem equipe",
                "title": row["title"],
                "time": row["start_time"].isoformat(timespec="minutes"),
                "status": row["status"],
                "responsible": row["responsible__full_name"],
                "location": row["location"],
            }
            for row in sorted(
                [row for row in rows if row["date"] == today],
                key=lambda item: item["start_time"],
            )
        ]

        operational_date = today
        if request.query_params.get("date"):
            try:
                operational_date = date.fromisoformat(request.query_params["date"])
            except ValueError:
                operational_date = today

        operational_base = dashboard_base_queryset().filter(date=operational_date).select_related(
            "team_ref",
            "chief_ref",
            "support_1_ref",
            "support_2_ref",
            "action_type_ref",
            "municipality_ref",
            "sector",
            "responsible",
        ).prefetch_related(
            "agents_ref",
            "designated_users",
            "absent_designated_users",
            "technical_reports__actions",
        )
        today_schedules = list(
            ShiftSchedule.objects.filter(date=operational_date)
            .select_related("team")
            .prefetch_related("absence_records")
        )
        from apps.schedules.services import get_expected_attendance_member_keys
        schedule_by_team_id = {schedule.team_id: schedule for schedule in today_schedules if schedule.team_id}
        schedule_by_team_name = {
            str(schedule.team.name).strip().upper(): schedule
            for schedule in today_schedules
            if schedule.team and schedule.team.name
        }
        allowed_field_teams = {"ALFA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOX", "GOLF", "HOTEL"}

        def clean_display(value, fallback="NÃ£o informado"):
            text = str(value or "").strip()
            return text if text else fallback

        def operational_team_label(agenda):
            raw = agenda.team_ref.name if agenda.team_ref else agenda.team_name
            value = clean_display(raw, "Sem equipe")
            upper = value.strip().upper()
            return upper if upper in allowed_field_teams else value

        def operational_chief_label(agenda):
            return clean_display(agenda.chief_ref.name if agenda.chief_ref else agenda.chief_name, "Sem chefe")

        def operational_location(agenda):
            return clean_display(agenda.institution_location or agenda.location or agenda.address, "Local nÃ£o informado")

        def operational_city(agenda):
            return clean_display(agenda.municipality_ref.name if agenda.municipality_ref else agenda.city, "Munic\u00edpio n\u00e3o informado")

        def operational_action_type(agenda):
            return clean_display(agenda.action_type_ref.name if agenda.action_type_ref else agenda.action_type, "A\u00e7\u00e3o")

        def operational_status(agenda):
            return classify_operational_status(
                agenda_date=agenda.date,
                start_time=agenda.start_time,
                end_time=agenda.end_time,
                agenda_status=agenda.status,
            )

        def agenda_agents_names(agenda):
            refs = list(agenda.agents_ref.all())
            if refs:
                return [item.name for item in refs if item.name]
            if not agenda.agents:
                return []
            names = [name.strip() for name in re.split(r"\s+-\s+|,", agenda.agents) if name.strip()]
            seen = set()
            unique = []
            for name in names:
                key = name.casefold()
                if key not in seen:
                    seen.add(key)
                    unique.append(name)
            return unique

        def agenda_agents_count(agenda):
            return len(agenda_agents_names(agenda))

        def agenda_supports_names(agenda):
            names = []
            for ref, text_value in ((agenda.support_1_ref, agenda.support_1), (agenda.support_2_ref, agenda.support_2)):
                label = ref.name if ref else text_value
                if label and str(label).strip():
                    names.append(str(label).strip())
            seen = set()
            unique = []
            for name in names:
                key = name.casefold()
                if key not in seen:
                    seen.add(key)
                    unique.append(name)
            return unique

        def agenda_supports_count(agenda):
            return len(agenda_supports_names(agenda))

        def agenda_designated_names(agenda):
            names = []
            for user in agenda.designated_users.filter(is_active=True):
                label = user.full_name or user.get_full_name() or user.username or user.email
                if label:
                    names.append(str(label).strip())
            return names

        def agenda_staffing_payload(agenda, chief_label, agents_names, supports_names):
            service_order_mode = getattr(agenda, "service_order_mode", Agenda.ServiceOrderMode.TEAM)
            if service_order_mode == Agenda.ServiceOrderMode.DESIGNATED:
                designated_names = agenda_designated_names(agenda)
                designated_count = len(designated_names)
                return {
                    "service_order_mode": service_order_mode,
                    "service_order_mode_label": agenda.get_service_order_mode_display(),
                    "chiefs_count": 0,
                    "designated_users_count": designated_count,
                    "designated_users_names": designated_names,
                    "effective_total_count": designated_count,
                    "effective_summary": (
                        f"{designated_count} participante(s) designado(s)"
                        if designated_count
                        else "Nenhum participante designado"
                    ),
                }

            chiefs_count = 0 if chief_label == "Sem chefe" else 1
            agents_count = len(agents_names)
            supports_count = len(supports_names)
            effective_parts = []
            if chiefs_count:
                effective_parts.append(f"{chiefs_count} chefe")
            if agents_count:
                effective_parts.append(f"{agents_count} agente{'s' if agents_count != 1 else ''}")
            if supports_count:
                effective_parts.append(f"{supports_count} apoio{'s' if supports_count != 1 else ''}")
            return {
                "service_order_mode": service_order_mode,
                "service_order_mode_label": agenda.get_service_order_mode_display(),
                "chiefs_count": chiefs_count,
                "designated_users_count": 0,
                "designated_users_names": [],
                "effective_total_count": chiefs_count + agents_count + supports_count,
                "effective_summary": " · ".join(effective_parts) if effective_parts else "Efetivo ainda não informado",
            }

        def numeric_public_estimate(agenda):
            if agenda.quantity:
                return int(agenda.quantity or 0)
            raw = str(agenda.audience or "").strip()
            match = re.search(r"\d+", raw)
            return int(match.group(0)) if match else 0

        def non_empty_lines(value):
            return [line.strip() for line in str(value or "").splitlines() if line.strip()]

        def schedule_for_agenda(agenda):
            if agenda.team_ref_id and agenda.team_ref_id in schedule_by_team_id:
                return schedule_by_team_id[agenda.team_ref_id]
            raw_team = agenda.team_ref.name if agenda.team_ref else agenda.team_name
            return schedule_by_team_name.get(str(raw_team or "").strip().upper())

        def absence_payload(schedule):
            if not schedule:
                return []
            role_labels = {
                ShiftAbsence.MemberType.CHIEF: "Chefe",
                ShiftAbsence.MemberType.AGENT: "Agente",
                ShiftAbsence.MemberType.SUPPORT: "Apoio",
            }
            return [
                {
                    "name": record.member_name,
                    "role": role_labels.get(record.member_type, record.member_type),
                    "reason": record.reason,
                    "attachment_url": record.attachment.url if record.attachment else "",
                }
                for record in schedule.absence_records.all()
            ]

        def agenda_report_team_candidates(agenda):
            values = [
                agenda.team_name,
                agenda.team_ref.name if agenda.team_ref else "",
                agenda.sector.name if agenda.sector else "",
            ]
            seen = set()
            candidates = []
            for value in values:
                label = str(value or "").strip()
                if not label:
                    continue
                key = label.casefold()
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(label)
            return candidates

        def resolved_report_for_agenda(agenda):
            reports = list(agenda.technical_reports.all())
            if not reports:
                return None
            reports.sort(key=lambda report: report.updated_at or report.created_at, reverse=True)

            candidates = {value.casefold() for value in agenda_report_team_candidates(agenda)}
            if candidates:
                matched_reports = [
                    report
                    for report in reports
                    if str(getattr(report, "team", "") or "").strip().casefold() in candidates
                ]
                return matched_reports[0] if matched_reports else (reports[0] if len(reports) == 1 else None)

            return reports[0] if len(reports) == 1 else None

        def report_status_payload(report):
            meta_key, badge_label, label = REPORT_STATUS_META.get(getattr(report, "status", None), REPORT_STATUS_META[None])
            return {
                "key": meta_key,
                "badge_label": badge_label,
                "label": label,
                "status": getattr(report, "status", None),
            }

        def attendance_status_payload(schedule, agenda):
            expected_members = get_expected_attendance_member_keys(agenda, schedule)
            checked_members = schedule.checked_members if schedule else {}
            checked_count = len(checked_members.keys()) if isinstance(checked_members, dict) else 0
            expected_count = len(expected_members)
            if schedule and schedule.attendance_approved:
                key = "approved"
            elif schedule and schedule.attendance_reported:
                key = "reported"
            else:
                key = "pending"
            badge_label, label = ATTENDANCE_STATUS_META[key]
            return {
                "key": key,
                "badge_label": badge_label,
                "label": label,
                "reported": bool(schedule.attendance_reported) if schedule else False,
                "approved": bool(schedule.attendance_approved) if schedule else False,
                "checked_members_count": checked_count,
                "expected_members_count": expected_count,
                "has_partial_checks": bool(expected_count and 0 < checked_count < expected_count),
            }

        def report_details_payload(report):
            if not report:
                return None
            actions = []
            actions_public_reached = 0
            for action in report.actions.all():
                action_approach = action.approach or 0
                action_reported_approaches = action.approached_actions or 0
                actions_public_reached += action_reported_approaches or action_approach
                actions.append({
                    "place": action.place_action or action.institution_name or "",
                    "type": action.type_action or "",
                    "start_time": action.start_time or "",
                    "final_hour": action.final_hour or "",
                    "approach": action_approach,
                    "reported_approaches": action_reported_approaches,
                    "approached_lectures": action.approached_lectures or 0,
                    "approached_actions": action_reported_approaches,
                    "materials": non_empty_lines(action.equipment_materials_distributed) + non_empty_lines(action.distribution_materials_distributed),
                    "support_materials": non_empty_lines(action.equipment_materials_distributed),
                    "distribution_materials": non_empty_lines(action.distribution_materials_distributed),
                })
            return {
                "id": report.id,
                "status": report.status,
                "public_reached": actions_public_reached or report.approximate_public or 0,
                "education_pcd": non_empty_lines(report.education_pcd),
                "education_agents": non_empty_lines(report.education_agents),
                "changes_staff": non_empty_lines(report.changes_staff),
                "accessibility_conditions_met": report.accessibility_conditions_met,
                "materials_removed": non_empty_lines(report.materials_removed),
                "materials_spent": non_empty_lines(report.materials_spent),
                "equipment_materials_distributed": non_empty_lines(report.equipment_materials_distributed),
                "distribution_materials_distributed": non_empty_lines(report.distribution_materials_distributed),
                "breathalyzers": non_empty_lines(report.breathalyzers),
                "cars": report.cars or "",
                "changes_general": non_empty_lines(report.changes_general),
                "contact_received": report.contact_received or "",
                "occurrence_observation": report.occurrence_observation or "",
                "general_observations": report.general_observations or "",
                "actions": actions,
            }

        today_agendas = list(operational_base.order_by("start_time", "id"))
        operation_rows = []
        total_supports = 0
        total_estimated_public = 0
        total_reached_public = 0
        for agenda in today_agendas:
            status_key, operational_badge_label, status_text = operational_status(agenda)
            agents_names = agenda_agents_names(agenda)
            supports_names = agenda_supports_names(agenda)
            report = resolved_report_for_agenda(agenda)
            schedule = schedule_for_agenda(agenda)
            report_status = report_status_payload(report)
            attendance_status = attendance_status_payload(schedule, agenda)
            absences = absence_payload(schedule)
            latest_report_payload = report_details_payload(report)
            report_payload = latest_report_payload
            estimated_public = numeric_public_estimate(agenda)
            reached_public = report_payload["public_reached"] if report_payload else 0
            latest_reached_public = latest_report_payload["public_reached"] if latest_report_payload else 0
            chief_label = operational_chief_label(agenda)
            staffing = agenda_staffing_payload(agenda, chief_label, agents_names, supports_names)
            chief_report_text = str((latest_report_payload or {}).get("general_observations") or "").strip()
            total_estimated_public += estimated_public
            total_reached_public += reached_public
            supports_count = len(supports_names)
            total_supports += supports_count
            start_dt, end_dt = build_agenda_operational_window(
                agenda_date=agenda.date,
                start_time=agenda.start_time,
                end_time=agenda.end_time,
            )
            operation_rows.append({
                "id": agenda.id,
                "title": agenda.title,
                "date": agenda.date.isoformat(),
                "time": agenda.start_time.isoformat(timespec="minutes") if agenda.start_time else "",
                "end_time": agenda.end_time.isoformat(timespec="minutes") if agenda.end_time else "",
                "time_range": f"{agenda.start_time.isoformat(timespec='minutes')}–{agenda.end_time.isoformat(timespec='minutes')}" if agenda.start_time and agenda.end_time else (agenda.start_time.isoformat(timespec="minutes") if agenda.start_time else ""),
                "type": operational_action_type(agenda),
                "location": operational_location(agenda),
                "address": agenda.address or "",
                "latitude": float(agenda.latitude) if agenda.latitude is not None else None,
                "longitude": float(agenda.longitude) if agenda.longitude is not None else None,
                "geocoding_status": agenda.geocoding_status,
                "neighborhood": agenda.neighborhood_ref.name if agenda.neighborhood_ref else agenda.neighborhood or "",
                "municipality": operational_city(agenda),
                "team": operational_team_label(agenda),
                "chief": chief_label,
                "status": agenda.status,
                "operational_status": status_key,
                "operational_status_badge_label": operational_badge_label,
                "operational_status_label": status_text,
                "operational_start": start_dt.isoformat(),
                "operational_end": end_dt.isoformat(),
                "report_status": report_status["key"],
                "report_status_label": report_status["label"],
                "report_status_badge_label": report_status["badge_label"],
                "report_status_code": report_status["status"],
                "attendance_status": attendance_status["key"],
                "attendance_status_label": attendance_status["label"],
                "attendance_status_badge_label": attendance_status["badge_label"],
                "attendance_reported": attendance_status["reported"],
                "attendance_approved": attendance_status["approved"],
                "attendance_checked_members_count": attendance_status["checked_members_count"],
                "attendance_expected_members_count": attendance_status["expected_members_count"],
                "attendance_has_partial_checks": attendance_status["has_partial_checks"],
                "service_order_number": agenda.service_order_number,
                "service_order_mode": staffing["service_order_mode"],
                "service_order_mode_label": staffing["service_order_mode_label"],
                "chiefs_count": staffing["chiefs_count"],
                "agents_count": len(agents_names),
                "agents_names": agents_names,
                "supports_count": supports_count,
                "supports_names": supports_names,
                "designated_users_count": staffing["designated_users_count"],
                "designated_users_names": staffing["designated_users_names"],
                "effective_total_count": staffing["effective_total_count"],
                "effective_summary": staffing["effective_summary"],
                "absences": absences,
                "absence_count": len(absences),
                "estimated_public": estimated_public,
                "public_reached": reached_public,
                "latest_public_reached": latest_reached_public,
                "has_report": bool(report),
                "latest_report_id": report.id if report else None,
                "latest_report_updated_at": (report.updated_at or report.created_at).isoformat() if report else "",
                "chief_report_text": chief_report_text,
                "chief_report_available": bool(chief_report_text),
                "report": report_payload,
                "schedule_id": schedule.id if schedule else None,
                "agenda_href": f"/agendas?open={agenda.id}",
                "report_href": (
                    f"/relatorio-tecnico?openReport={report.id}"
                    if report
                    else f"/agendas?open={agenda.id}"
                ),
                "attendance_href": (
                    f"/shift-schedules?openSchedule={schedule.id}"
                    if agenda.service_order_mode != "DESIGNATED" and schedule
                    else f"/agendas?open={agenda.id}"
                ),
                "href": f"/agendas?open={agenda.id}",
            })

        operational_team_names = {row["team"] for row in operation_rows if row["team"] != "Sem equipe"}
        operational_chief_names = {row["chief"] for row in operation_rows if row["chief"] != "Sem chefe"}
        total_agents_scheduled = sum(row["agents_count"] for row in operation_rows)
        service_orders_count = sum(1 for row in operation_rows if row["service_order_number"])
        completed_operational_count = sum(1 for row in operation_rows if row["operational_status"] == "completed")
        in_progress_operational_count = sum(1 for row in operation_rows if row["operational_status"] == "in_progress")
        scheduled_operational_count = sum(1 for row in operation_rows if row["operational_status"] == "scheduled")
        cancelled_operational_count = sum(1 for row in operation_rows if row["operational_status"] == "cancelled")
        pending_reports_count = sum(
            1
            for row in operation_rows
            if row["operational_status"] == "completed" and row["report_status"] in {"none", "draft", "returned"}
        )
        pending_attendance_count = sum(
            1
            for row in operation_rows
            if row["operational_status"] != "cancelled" and row["attendance_status"] == "pending"
        )
        returned_reports_count = sum(1 for row in operation_rows if row["report_status"] == "returned")
        missing_team_count = sum(1 for row in operation_rows if row["team"] == "Sem equipe")
        reported_attendance_count = sum(1 for row in operation_rows if row["attendance_status"] == "reported")
        approved_attendance_count = sum(1 for row in operation_rows if row["attendance_status"] == "approved")
        report_status_counts = {
            "none": sum(1 for row in operation_rows if row["report_status"] == "none"),
            "draft": sum(1 for row in operation_rows if row["report_status"] == "draft"),
            "pending_review": sum(1 for row in operation_rows if row["report_status"] == "pending_review"),
            "returned": sum(1 for row in operation_rows if row["report_status"] == "returned"),
            "approved": sum(1 for row in operation_rows if row["report_status"] == "approved"),
            "submitted": sum(1 for row in operation_rows if row["report_status"] == "submitted"),
        }

        def compact_operation_reference(row, href_key="agenda_href"):
            return {
                "id": row["id"],
                "href": row.get(href_key) or row.get("agenda_href") or row["href"],
                "time_range": row["time_range"],
                "service_order_number": row["service_order_number"],
                "title": row["type"] or row["title"],
                "location": row["location"],
                "team": row["team"],
                "operational_status": row["operational_status"],
                "operational_status_label": row["operational_status_label"],
                "attendance_status_label": row["attendance_status_label"],
                "report_status_label": row["report_status_label"],
            }

        pending_report_rows = [
            row for row in operation_rows
            if row["operational_status"] == "completed" and row["report_status"] in {"none", "draft", "returned"}
        ]
        pending_attendance_rows = [
            row for row in operation_rows
            if row["operational_status"] != "cancelled" and row["attendance_status"] == "pending"
        ]
        returned_report_rows = [row for row in operation_rows if row["report_status"] == "returned"]
        missing_team_rows = [row for row in operation_rows if row["team"] == "Sem equipe"]
        scheduled_operation_rows = [row for row in operation_rows if row["operational_status"] == "scheduled"]
        operations = {
            "date": operational_date.isoformat(),
            "cards": {
                "scheduled_today": {"value": operational_base.count(), "label": "A\u00e7\u00f5es do dia"},
                "in_progress": {"value": in_progress_operational_count, "label": "Em andamento"},
                "pending_start": {"value": scheduled_operational_count, "label": "Pr\u00f3ximas"},
                "completed": {"value": completed_operational_count, "label": "Realizadas"},
                "cancelled": {"value": cancelled_operational_count, "label": "A\u00e7\u00f5es canceladas"},
                "pending_reports": {"value": pending_reports_count, "label": "Relat\u00f3rios pendentes"},
                "pending_attendance": {"value": pending_attendance_count, "label": "Frequ\u00eancias pendentes"},
                "estimated_public": {"value": total_estimated_public, "label": "Estimativa de p\u00fablico"},
                "public_reached": {"value": total_reached_public, "label": "P\u00fablico alcan\u00e7ado informado"},
                "teams_active": {"value": len(operational_team_names), "label": "Equipes"},
                "chiefs_active": {"value": len(operational_chief_names), "label": "Chefes"},
                "agents_scheduled": {"value": total_agents_scheduled, "label": "Agentes"},
                "supports_scheduled": {"value": total_supports, "label": "Apoios"},
                "service_orders": {"value": service_orders_count, "label": "OS emitidas"},
            },
            "alerts": [],
            "field_operations": operation_rows,
            "next_operations": scheduled_operation_rows[:6],
            "summary": {
                "scheduled_today": operational_base.count(),
                "in_progress": in_progress_operational_count,
                "pending_start": scheduled_operational_count,
                "completed": completed_operational_count,
                "cancelled": cancelled_operational_count,
                "teams_active": len(operational_team_names),
                "chiefs_active": len(operational_chief_names),
                "agents_scheduled": total_agents_scheduled,
                "supports_scheduled": total_supports,
                "pending_reports": pending_reports_count,
                "pending_attendance": pending_attendance_count,
            },
            "closing": {
                "scheduled_today": operational_base.count(),
                "completed": completed_operational_count,
                "in_progress": in_progress_operational_count,
                "pending_start": scheduled_operational_count,
                "cancelled": cancelled_operational_count,
                "attendance": {
                    "completed": reported_attendance_count + approved_attendance_count,
                    "total": sum(1 for row in operation_rows if row["operational_status"] != "cancelled"),
                    "pending": pending_attendance_count,
                    "reported": reported_attendance_count,
                    "approved": approved_attendance_count,
                },
                "reports": report_status_counts,
                "public": {
                    "estimated": total_estimated_public,
                    "reported": total_reached_public,
                },
            },
            "timeline": operation_rows,
        }
        operational_attention = []
        if pending_reports_count:
            operational_attention.append({
                "severity": "warning",
                "title": "Relatórios pendentes",
                "description": f"{pending_reports_count} atividade(s) realizada(s) aguardam relatório.",
                "href": "/relatorio-tecnico",
                "items": [compact_operation_reference(row, "report_href") for row in pending_report_rows[:5]],
            })
        if pending_attendance_count:
            operational_attention.append({
                "severity": "info",
                "title": "Frequência pendente",
                "description": f"{pending_attendance_count} frequência(s) ainda precisa(m) ser concluída(s).",
                "href": "/shift-schedules",
                "items": [compact_operation_reference(row, "attendance_href") for row in pending_attendance_rows[:5]],
            })
        if returned_reports_count:
            operational_attention.append({
                "severity": "warning",
                "title": "Relatórios devolvidos",
                "description": f"{returned_reports_count} relatório(s) foi(foram) devolvido(s) para correção.",
                "href": "/relatorio-tecnico",
                "items": [compact_operation_reference(row, "report_href") for row in returned_report_rows[:5]],
            })
        if missing_team_count:
            operational_attention.append({
                "severity": "danger",
                "title": "Equipe não definida",
                "description": f"{missing_team_count} atividade(s) ainda não possui(em) equipe definida.",
                "href": "/agendas",
                "items": [compact_operation_reference(row) for row in missing_team_rows[:5]],
            })
        else:
            operational_attention.append({
                "severity": "success",
                "title": "Equipe definida",
                "description": "Todas as atividades possuem equipe definida.",
                "href": "/agendas",
                "items": [],
            })
        operations["alerts"] = operational_attention[:10]

        status_total = max(qs_base.count(), 1)
        completion_rate = round((completed / status_total) * 100, 1)
        cancellation_rate = round((cancelled / status_total) * 100, 1)
        avg_per_user = round(total / max(qs.values("responsible_id").distinct().count(), 1), 1)
        calendar_start = today.replace(day=1)
        calendar_days = [
            {
                "date": (calendar_start + timedelta(days=index)).isoformat(),
                "day": (calendar_start + timedelta(days=index)).day,
                "total": by_date[calendar_start + timedelta(days=index)],
            }
            for index in range(31)
            if (calendar_start + timedelta(days=index)).month == today.month
        ]

        # Metrics only consider approved surveys or surveys without text (which don't need moderation)
        surveys_qs = SatisfactionSurvey.objects.filter(
            Q(is_approved=True) | Q(suggestion=""),
            agenda__in=base_qs,
            answered_at__isnull=False
        )
        overall_rating_avg = surveys_qs.aggregate(avg=Avg('overall_rating'))['avg'] or 0.0

        team_ratings = list(
            surveys_qs.values('team')
            .annotate(avg=Avg('overall_rating'), count=Count('id'))
            .exclude(team="")
            .order_by('-avg', '-count')[:10]
        )

        # Message source includes all answered messages, moderation depends on roles
        messages_qs = SatisfactionSurvey.objects.filter(agenda__in=base_qs, answered_at__isnull=False).exclude(suggestion="")
        pending_moderation_count = SatisfactionSurvey.objects.filter(agenda__in=base_qs, answered_at__isnull=False, is_approved=False).exclude(suggestion="").count()
        now_dt = timezone.localtime(timezone.now())
        reportable_agendas = base_qs.filter(
            Q(date__lt=now_dt.date()) | Q(date=now_dt.date(), end_time__lte=now_dt.time()),
            service_order_number__isnull=False,
        )
        pending_technical_reports_count = reportable_agendas.exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED]).filter(technical_reports__isnull=True).count()
        if not (request.user.is_superuser or request.user.role in ["ADMIN", "MANAGER"]):
            messages_qs = messages_qs.filter(is_approved=True)

        recent_messages = list(

            messages_qs.order_by('-answered_at')
            .values('id', 'team', 'suggestion', 'moderated_comment', 'answered_at', 'overall_rating', 'is_approved', 'moderation_status')[:15]
        )

        distributed_materials = distributed_materials_summary(qs)
        chief_reports = EducationReport.objects.filter(
            agenda_id__in=qs.values("id")
        ).exclude(status=EducationReport.ReportStatus.DRAFT).distinct()
        chief_actions = EducationAction.objects.filter(report_id__in=chief_reports.values("id"))

        approved_reports = chief_reports.filter(status=EducationReport.ReportStatus.APPROVED)
        approved_actions = EducationAction.objects.filter(report_id__in=approved_reports.values("id"))

        chief_reported_agendas = qs.filter(id__in=chief_reports.values("agenda_id")).distinct()
        chief_totals = chief_actions.aggregate(
            approaches=Sum("approach"),
            registered_actions=Count("id"),
        )
        approved_totals = approved_actions.aggregate(
            approved_actions_count=Count("id"),
        )
        chief_report_totals = chief_reports.aggregate(
            reports_count=Count("id"),
            reported_public=Sum("approximate_public"),
        )
        chief_request_totals = chief_reported_agendas.aggregate(
            requested_public=Sum("quantity"),
            requested_actions=Sum("actions_count"),
        )
        chief_reports_count = chief_report_totals["reports_count"] or 0
        reported_public = chief_report_totals["reported_public"] or 0
        requested_public = chief_request_totals["requested_public"] or 0
        registered_actions = chief_totals["registered_actions"] or 0
        requested_actions = chief_request_totals["requested_actions"] or 0
        approaches = chief_totals["approaches"] or 0
        approved_actions_count = approved_totals["approved_actions_count"] or 0
        reports_waiting_approval = max(0, registered_actions - approved_actions_count)

        chief_team_names = {
            team.strip().casefold()
            for team in chief_reports.values_list("team", flat=True)
            if team and team.strip()
        }
        chief_teams_count = len(chief_team_names)

        def rate(value, base):
            return round((value / base) * 100, 1) if base else 0

        data = {
            "cards": {
                "today_total": {"value": today_count, "change": pct(today_count, comparison_qs.count() if comparison_qs is not None else yesterday_count), "compare_label": comparison_label},
                "pending": {"value": pending, "change": pct(pending, comparison_qs.filter(status=Agenda.Status.PENDING).count() if comparison_qs is not None else None), "compare_label": comparison_label},
                "approved": {"value": approved, "change": pct(approved, comparison_qs.filter(status=Agenda.Status.APPROVED).count() if comparison_qs is not None else None), "compare_label": comparison_label},
                "completed": {"value": completed, "change": pct(completed, comparison_qs.filter(status=Agenda.Status.COMPLETED).count() if comparison_qs is not None else None), "compare_label": comparison_label},
                  "cancelled": {"value": cancelled, "change": pct(cancelled, comparison_qs.filter(status=Agenda.Status.CANCELLED).count() if comparison_qs is not None else None), "compare_label": comparison_label},
                "in_progress": {"value": in_progress, "change": None, "compare_label": "neste momento"},
                "upcoming": {"value": upcoming_count, "change": None, "compare_label": "a partir de hoje"},
                "today_agents": {"value": today_agents_count, "change": None, "compare_label": "em agendas de hoje"},
            },
            "comparison": {
                "mode": compare_mode,
                "label": comparison_label,
                "date_from": previous_start.isoformat() if previous_start else None,
                "date_to": previous_end.isoformat() if previous_end else None,
            },
            "series": {
                "daily": line_series,
                "weekly": weekly,
                "weekly_change": pct(weekly, previous_week),
                "monthly": monthly,
                "monthly_change": pct(monthly, previous_month),
            },
            "bars": {
                "by_team_actions": by_team_actions,
                "by_origin": [
                    {"label": "SolicitaÃ§Ã£o externa", "value": external_requests},
                    {"label": "SolicitaÃ§Ã£o interna", "value": internal_requests},
                ],
                "by_neighborhood": by_neighborhood,
                "by_user": [{"label": row["responsible__full_name"] or "Sem responsÃ¡vel", "value": row["total"]} for row in by_user],
                "by_status": [{"label": row["label"], "value": row["total"], "status": row["status"]} for row in by_status],
            },
            "donut": by_municipality,
            "heatmap": heatmap_rows,
            "calendar": calendar_days,
            "surveys": {
                "overall_rating": round(overall_rating_avg, 1),
                "total_responses": surveys_qs.count(),
                "team_ratings": [
                    {"team": tr["team"], "avg": round(tr["avg"], 1), "count": tr["count"]}
                    for tr in team_ratings if tr["avg"] is not None
                ],
                "messages": recent_messages,
            },
            "materials": {
                "distributed": distributed_materials,
            },
            "chief_fillings": {
                "approaches": approaches,
                "requested_public": requested_public,
                "reported_public": reported_public,
                "public_difference": reported_public - requested_public,
                "public_execution_rate": rate(reported_public, requested_public),
                "requested_actions": requested_actions,
                "registered_actions": registered_actions,
                "reports_waiting_approval": reports_waiting_approval,
                "actions_difference": registered_actions - requested_actions,
                "actions_execution_rate": rate(registered_actions, requested_actions),
                "reports_count": chief_reports_count,
                "requests_with_report": chief_reported_agendas.count(),
                "teams_count": chief_teams_count,
                "average_public_per_report": round(reported_public / chief_reports_count, 1) if chief_reports_count else 0,
                "average_approaches_per_action": round(approaches / registered_actions, 1) if registered_actions else 0,
                "average_approaches_per_team": round(approaches / chief_teams_count, 1) if chief_teams_count else 0,
            },
            "pending_moderation_count": pending_moderation_count,
            "pending_technical_reports_count": pending_technical_reports_count,
            "operations": operations,
            "activity": {

                "latest": recent[:6],
                "field_teams": field_teams,
            },
            "advanced": {
                "approval_rate": completion_rate,
                "cancellation_rate": cancellation_rate,
                "approval_avg_hours": 24,
                "completion_avg_hours": 72,
                "reschedules": 0,
                "avg_per_user": avg_per_user,
                "sla": round(100 - cancellation_rate, 1),
            }
        }
        aggs_palestras = qs.aggregate(
            palestras=Sum('quantity', filter=Q(action_type__icontains="palestra")),
            acoes=Sum('quantity', filter=~Q(action_type__icontains="palestra"))
        )
        data["advanced"]["abordados_palestras"] = aggs_palestras["palestras"] or 0
        data["advanced"]["abordados_acoes"] = aggs_palestras["acoes"] or 0

        cache.set(cache_key, data, 60 * 15)
        return response.Response(data)


class EventReportViewSet(viewsets.ModelViewSet):
    serializer_class = EventReportSerializer
    permission_classes = [IsAuthenticated, VisitorReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = EventReport.objects.select_related("agenda", "agenda__sector", "created_by").order_by("-updated_at")
        scoped = queryset
        if user.role == User.Role.SUPERVISOR:
            scoped = queryset.filter(chief_agenda_filter(user, prefix="agenda__")).distinct()
        if user.is_agent_role:
            return queryset.none()

        params = self.request.query_params
        if params.get("chief"):
            scoped = scoped.filter(
                Q(agenda__chief_ref_id=params["chief"])
                | Q(agenda__chief_name__iexact=Chief.objects.filter(id=params["chief"]).values_list("name", flat=True).first() or "")
            )
        if params.get("event"):
            term = params["event"].strip()
            scoped = scoped.filter(
                Q(agenda__title__icontains=term)
                | Q(agenda__action_type__icontains=term)
                | Q(agenda__institution_location__icontains=term)
            )
        if params.get("date"):
            scoped = scoped.filter(agenda__date=params["date"])
        if params.get("date_from"):
            scoped = scoped.filter(agenda__date__gte=params["date_from"])
        if params.get("date_to"):
            scoped = scoped.filter(agenda__date__lte=params["date_to"])
        return scoped

    def perform_create(self, serializer):
        agenda = serializer.validated_data["agenda"]
        user = self.request.user
        if user.role == User.Role.SUPERVISOR:
            from rest_framework.exceptions import PermissionDenied

            if not Agenda.objects.filter(pk=agenda.pk).filter(chief_agenda_filter(user)).exists():
                raise PermissionDenied("VocÃª sÃ³ pode relatar agendas em que vocÃª estÃ¡ vinculado como Chefe.")
        if user.is_agent_role:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Apenas Chefes, Gestores e Administradores podem enviar relatórios técnicos.")
        submitted_at = timezone.now() if serializer.validated_data.get("status") == EventReport.ReportStatus.SUBMITTED else None
        serializer.save(created_by=user, submitted_at=submitted_at)

    def perform_update(self, serializer):
        instance = self.get_object()
        submitted_at = instance.submitted_at
        if serializer.validated_data.get("status") == EventReport.ReportStatus.SUBMITTED and not submitted_at:
            submitted_at = timezone.now()
        serializer.save(submitted_at=submitted_at)


class EducationReportViewSet(viewsets.ModelViewSet):
    serializer_class = EducationReportSerializer
    permission_classes = [IsAuthenticated]

    def _block_visitor_write(self):
        if self.request.user and self.request.user.is_authenticated and self.request.user.role == User.Role.VISITOR:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("O perfil Visitante possui apenas permissão de consulta no módulo Relatório Técnico.")
    statistics_fields = [
        ("approach", "Total de abordagens"),
        ("approached_lectures", "Abordados em palestras"),
        ("approached_actions", "Abordados em aÃ§Ãµes"),
        ("vetarolas", "Vetarolas"),
        ("used_adhesives", "Adesivos"),
        ("sequence_certificates", "SequÃªncia certificados"),
        ("gibis", "Gibis"),
        ("distributed_certificates", "Certificados"),
        ("lectures", "Palestras realizadas"),
        ("schools", "Escolas"),
        ("universities", "Universidades"),
        ("companies", "Empresas"),
        ("educational_actions", "AÃ§Ãµes educativas"),
        ("bars", "Bares"),
        ("tolls", "PedÃ¡gio"),
        ("sports", "Esportes"),
        ("beach", "Praia"),
        ("events", "Eventos"),
        ("shopping", "Shopping/Centro Comercial"),
        ("parks", "PraÃ§as/Parques pÃºblicos"),
        ("tourist_spots", "Pontos turÃ­sticos"),
        ("social_actions", "A\u00e7\u00e3o social"),
        ("joint_inspections", "A\u00e7\u00e3o conjunta com a fiscaliza\u00e7\u00e3o"),
        ("other_actions", "Outros"),
        ("publicity_materials", "Materiais de divulgaÃ§Ã£o"),
    ]

    schema_error_message = (
        "O banco de dados dos relatorios tecnicos esta desatualizado. "
        "Execute `python manage.py migrate` no backend da VPS e tente novamente."
    )

    def _schema_error_response(self, exc):
        message = str(exc).lower()
        if "educationreport" in message or "schedules_educationreport" in message:
            return response.Response({"detail": self.schema_error_message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        raise exc

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except (OperationalError, ProgrammingError) as exc:
            return self._schema_error_response(exc)

    def retrieve(self, request, *args, **kwargs):
        if request.user.role == User.Role.VISITOR:
            instance = self.get_object()
            if instance.status != EducationReport.ReportStatus.APPROVED:
                from django.http import Http404
                raise Http404("Relatório não encontrado.")
        try:
            return super().retrieve(request, *args, **kwargs)
        except (OperationalError, ProgrammingError) as exc:
            return self._schema_error_response(exc)

    def _log_permission_denied(self, reason, message, agenda_id=None, report_id=None):
        user = self.request.user
        chief_name = user.full_name if user.role == User.Role.SUPERVISOR else "N/A"
        log_msg = f"REPORT_PERMISSION_DENIED user={user.id} chief={chief_name} agenda={agenda_id or 'N/A'} report={report_id or 'N/A'} reason={reason}"
        logger.warning(log_msg)
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied(message)

    def create(self, request, *args, **kwargs):
        self._block_visitor_write()
        try:
            return super().create(request, *args, **kwargs)
        except (OperationalError, ProgrammingError) as exc:
            return self._schema_error_response(exc)
        except Exception as exc:
            from rest_framework.exceptions import APIException
            from django.http import Http404
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, (APIException, Http404, PermissionDenied)):
                raise
            logger.exception("Unexpected error in EducationReportViewSet.create")
            return response.Response({"detail": "Ocorreu um erro inesperado ao processar o relatório. Tente novamente ou entre em contato com o administrador."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        self._block_visitor_write()
        try:
            return super().update(request, *args, **kwargs)
        except (OperationalError, ProgrammingError) as exc:
            return self._schema_error_response(exc)
        except Exception as exc:
            from rest_framework.exceptions import APIException
            from django.http import Http404
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, (APIException, Http404, PermissionDenied)):
                raise
            logger.exception("Unexpected error in EducationReportViewSet.update")
            return response.Response({"detail": "Ocorreu um erro inesperado ao processar o relatório. Tente novamente ou entre em contato com o administrador."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='process-statistics')
    def process_statistics(self, request, pk=None):
        self._block_visitor_write()
        from apps.statistics.services import generate_statistics_for_report
        from django.utils import timezone

        if not request.user.has_perm('statistics.add_consolidatedstatistic'):
            return response.Response({'error': 'VocÃª nÃ£o tem permissÃ£o para processar estatísticas oficiais.'}, status=status.HTTP_403_FORBIDDEN)

        report = self.get_object()

        if report.status != 'APPROVED':
            return response.Response({'error': 'Apenas relatórios aprovados podem ser validados para a estatística oficial.'}, status=status.HTTP_400_BAD_REQUEST)

        if report.statistics_processed:
            # Re-processamento permitido se houver correÃ§Ã£o (lÃ³gica idempotente no services.py)
            pass

        try:
            generate_statistics_for_report(
                report,
                processed_by=request.user,
            )
            return response.Response(
                {
                    "message": (
                        "Estatística processada e validada "
                        "com sucesso."
                    )
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Error processing statistics")
            return response.Response(
                {
                    "error": (
                        "Erro ao processar estatística. "
                        "Consulte os logs para mais detalhes."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        self._block_visitor_write()
        try:
            return super().partial_update(request, *args, **kwargs)
        except (OperationalError, ProgrammingError) as exc:
            return self._schema_error_response(exc)
        except Exception as exc:
            from rest_framework.exceptions import APIException
            from django.http import Http404
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, (APIException, Http404, PermissionDenied)):
                raise
            logger.exception("Unexpected error in EducationReportViewSet.partial_update")
            return response.Response({"detail": "Ocorreu um erro inesperado ao processar o relatório. Tente novamente ou entre em contato com o administrador."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def destroy(self, request, *args, **kwargs):
        self._block_visitor_write()
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = EducationReport.objects.select_related("agenda", "created_by").prefetch_related(
            "actions",
            "actions__agenda",
        )

        # VISITOR: acesso somente-leitura de relatórios aprovados (caminho independente)
        if user.role == User.Role.VISITOR:
            from django.db.models import Q
            scoped = queryset.filter(status=EducationReport.ReportStatus.APPROVED)
            params = self.request.query_params
            if params.get("protocol"):
                scoped = scoped.filter(agenda_id=params["protocol"])
            if params.get("team"):
                scoped = scoped.filter(team__icontains=params["team"].strip())
            if params.get("source"):
                scoped = scoped.filter(source=params["source"])
            if params.get("date"):
                scoped = scoped.filter(operation_date=params["date"])
            if params.get("date_from"):
                scoped = scoped.filter(operation_date__gte=params["date_from"])
            if params.get("date_to"):
                scoped = scoped.filter(operation_date__lte=params["date_to"])
            if params.get("q"):
                term = params["q"].strip()
                search_filter = (
                    Q(team__icontains=term)
                    | Q(agenda__source_id__icontains=term)
                    | Q(agenda__title__icontains=term)
                    | Q(management_name__icontains=term)
                )
                scoped = scoped.filter(search_filter)
            return scoped.order_by("-operation_date", "-created_at").distinct()

        if user.is_admin_role:
            queryset = queryset.filter(agenda__date__gte="2026-07-01")
        else:
            queryset = queryset.filter(agenda__date__gte="2026-07-08")
        if user.is_agent_role:
            scoped = queryset.none()
        elif user.is_admin_role:
            scoped = queryset
        elif user.role == User.Role.VISITOR and user.sector and user.sector.name == "Subsecretaria":
            scoped = queryset
        else:
            scoped = queryset.filter(chief_agenda_filter(user, prefix="agenda__")).distinct()

        params = self.request.query_params
        if params.get("protocol"):
            scoped = scoped.filter(agenda_id=params["protocol"])
        if params.get("team"):
            scoped = scoped.filter(team__icontains=params["team"].strip())
        if params.get("source"):
            scoped = scoped.filter(source=params["source"])
        if params.get("status"):
            scoped = scoped.filter(status=params["status"])
        if params.get("date"):
            scoped = scoped.filter(operation_date=params["date"])
        if params.get("date_from"):
            scoped = scoped.filter(operation_date__gte=params["date_from"])
        if params.get("date_to"):
            scoped = scoped.filter(operation_date__lte=params["date_to"])
        if params.get("q"):
            term = params["q"].strip()
            search_filter = (
                Q(team__icontains=term)
                | Q(agenda__source_id__icontains=term)
                | Q(agenda__title__icontains=term)
                | Q(management_name__icontains=term)
                | Q(contact_received__icontains=term)
                | Q(occurrence_observation__icontains=term)
                | Q(actions__place_action__icontains=term)
                | Q(actions__type_action__icontains=term)
                | Q(actions__institution_name__icontains=term)
            )
            if term.isdigit():
                search_filter |= Q(agenda_id=int(term)) | Q(agenda__service_order_number=int(term))
            scoped = scoped.filter(search_filter)
        return scoped.annotate(actions_count_annotated=Count('actions', distinct=True)).order_by("-operation_date", "-created_at")

    def perform_create(self, serializer):
        with transaction.atomic():
            agenda = serializer.validated_data.get("agenda")
            team = serializer.validated_data.get("team")
            if agenda and team and EducationReport.objects.filter(agenda=agenda, team=team).exists():
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Já existe um relatório técnico registrado para este protocolo com esta equipe.")

            self._validate_agenda_access(agenda)
            if "status" in serializer.validated_data:
                del serializer.validated_data["status"]
            report = serializer.save(created_by=self.request.user, status=EducationReport.ReportStatus.DRAFT)
            SatisfactionSurvey.objects.filter(agenda=report.agenda, report__isnull=True).update(report=report)

    def perform_update(self, serializer):
        with transaction.atomic():
            if not self.request.user.is_admin_role:
                if serializer.instance.status == EducationReport.ReportStatus.PENDING_REVIEW:
                    self._log_permission_denied("REPORT_PENDING_REVIEW", "Este relatório jÃ¡ foi enviado para conferência e aguarda anÃ¡lise.", serializer.instance.agenda_id, serializer.instance.id)
                elif serializer.instance.status == EducationReport.ReportStatus.APPROVED:
                    self._log_permission_denied("REPORT_ALREADY_APPROVED", "Este relatório jÃ¡ foi aprovado e nÃ£o pode mais ser alterado.", serializer.instance.agenda_id, serializer.instance.id)

            if "status" in serializer.validated_data:
                del serializer.validated_data["status"]

            agenda = serializer.validated_data.get("agenda", serializer.instance.agenda)
            self._validate_agenda_access(agenda)
            report = serializer.save()

            if report.status == EducationReport.ReportStatus.APPROVED and report.statistics_processed:
                from apps.statistics.services import invalidate_statistics
                invalidate_statistics(report, self.request.user)

            SatisfactionSurvey.objects.filter(agenda=report.agenda, report__isnull=True).update(report=report)
            if report.status == EducationReport.ReportStatus.APPROVED:
                from apps.statistics.services import generate_statistics_for_report
                generate_statistics_for_report(report, processed_by=self.request.user)

    @decorators.action(detail=True, methods=["post"], url_path="submit-for-review")
    def submit_for_review(self, request, pk=None):
        self._block_visitor_write()
        report = self.get_object()

        if report.agenda:
            self._validate_agenda_access(report.agenda)

        if report.status not in [EducationReport.ReportStatus.DRAFT, EducationReport.ReportStatus.RETURNED]:
            if report.status == EducationReport.ReportStatus.PENDING_REVIEW:
                self._log_permission_denied("REPORT_PENDING_REVIEW", "Este relatório jÃ¡ foi enviado para conferência e aguarda anÃ¡lise.", report.agenda_id, report.id)
            elif report.status == EducationReport.ReportStatus.APPROVED:
                self._log_permission_denied("REPORT_ALREADY_APPROVED", "Este relatório jÃ¡ foi aprovado e nÃ£o pode mais ser alterado.", report.agenda_id, report.id)
            else:
                self._log_permission_denied("AGENDA_STATUS_INVALID", "Esta agenda nÃ£o permite mais alteraÃ§Ãµes.", report.agenda_id, report.id)

        # ValidaÃ§Ã£o obrigatÃ³ria da conferência de frequência
        from apps.schedules.models import ShiftSchedule, Team

        schedules_found = []
        if report.agenda and report.agenda.team_ref_id:
            schedules_found = list(ShiftSchedule.objects.filter(date=report.operation_date, team_id=report.agenda.team_ref_id))

        if not schedules_found and report.team:
            team_obj = Team.objects.filter(name=report.team).first()
            if team_obj:
                schedules_found = list(ShiftSchedule.objects.filter(date=report.operation_date, team=team_obj))

        service_order_mode = getattr(report.agenda, "service_order_mode", Agenda.ServiceOrderMode.TEAM) if report.agenda else Agenda.ServiceOrderMode.TEAM
        from apps.schedules.services import get_expected_attendance_member_keys

        if service_order_mode == Agenda.ServiceOrderMode.DESIGNATED:
            if len(schedules_found) > 1:
                return response.Response(
                    {"detail": "Foram encontradas múltiplas escalas para esta data. Revise a agenda antes de enviar o relatório."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            schedule = schedules_found[0] if schedules_found else None
            if schedule:
                expected_members = get_expected_attendance_member_keys(report.agenda, schedule)
                checked = set(schedule.checked_members.keys())
                if not expected_members.issubset(checked):
                    return response.Response({"detail": "Confira a frequência de todos os participantes selecionados antes de enviar o relatório."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if len(schedules_found) != 1:
                return response.Response(
                    {
                        "detail": (
                            "Não foi possível localizar a escala vinculada a este "
                            "relatório. Verifique a agenda e tente novamente."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            schedule = schedules_found[0] if schedules_found else None
            if schedule:
                expected_members = get_expected_attendance_member_keys(report.agenda, schedule)
                checked = set(schedule.checked_members.keys())
                if not expected_members.issubset(checked):
                    return response.Response({"detail": "Confira a frequência de todos os integrantes antes de enviar o relatório."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = report.status
            report.status = EducationReport.ReportStatus.PENDING_REVIEW
            report.submitted_for_review_at = timezone.now()
            report.submitted_for_review_by = request.user
            report.save(update_fields=["status", "submitted_for_review_at", "submitted_for_review_by", "updated_at"])

            ReportStatusHistory.objects.create(
                report=report,
                old_status=old_status,
                new_status=report.status,
                changed_by=request.user
            )

            # Marcar frequência como reportada no ShiftSchedule
            if schedule and not schedule.attendance_reported:
                schedule.attendance_reported = True
                schedule.attendance_reported_at = timezone.now()
                schedule.attendance_approved = False
                schedule.attendance_approved_at = None
                schedule.save(update_fields=[
                    "attendance_reported",
                    "attendance_reported_at",
                    "attendance_approved",
                    "attendance_approved_at",
                ])

        return response.Response({"detail": "Enviado para conferência."})

    @decorators.action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        self._block_visitor_write()
        if not request.user.is_admin_role:
            raise PermissionDenied("Apenas gestores ou administradores podem aprovar relatórios.")

        report = self.get_object()
        if report.status != EducationReport.ReportStatus.PENDING_REVIEW:
            return response.Response({"detail": "Apenas relatórios aguardando conferência podem ser aprovados."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            old_status = report.status
            report.status = EducationReport.ReportStatus.APPROVED
            report.reviewed_at = timezone.now()
            report.reviewed_by = request.user
            report.save(update_fields=["status", "reviewed_at", "reviewed_by", "updated_at"])

            ReportStatusHistory.objects.create(
                report=report,
                old_status=old_status,
                new_status=report.status,
                changed_by=request.user
            )

            from apps.statistics.services import generate_statistics_for_report
            generate_statistics_for_report(report, processed_by=request.user)

        self._register_accessibility_block(report)
        transaction.on_commit(lambda: send_satisfaction_survey_email(report))
        transaction.on_commit(lambda: send_report_confirmation_email(report))

        return response.Response({"detail": "Relatório aprovado com sucesso."})

    @decorators.action(detail=True, methods=["post"], url_path="return-for-correction")
    def return_for_correction(self, request, pk=None):
        self._block_visitor_write()
        if not request.user.is_admin_role:
            raise PermissionDenied("Apenas gestores ou administradores podem devolver relatórios.")

        notes = request.data.get("notes", "").strip()
        if not notes:
            return response.Response({"detail": "A justificativa Ã© obrigatÃ³ria."}, status=status.HTTP_400_BAD_REQUEST)

        report = self.get_object()
        if report.status != EducationReport.ReportStatus.PENDING_REVIEW:
            return response.Response({"detail": "Apenas relatórios aguardando conferência podem ser devolvidos."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            old_status = report.status
            report.status = EducationReport.ReportStatus.RETURNED
            report.review_notes = notes
            report.reviewed_at = timezone.now()
            report.reviewed_by = request.user

            update_fields = ["status", "review_notes", "reviewed_at", "reviewed_by", "updated_at"]
            report.save(update_fields=update_fields)

            if report.statistics_processed:
                from apps.statistics.services import invalidate_statistics
                invalidate_statistics(report, request.user)

            ReportStatusHistory.objects.create(
                report=report,
                old_status=old_status,
                new_status=report.status,
                changed_by=request.user,
                notes=notes
            )

        return response.Response({"detail": "Relatório devolvido para correÃ§Ã£o."})

    def _validate_agenda_access(self, agenda):
        user = self.request.user
        if user.is_admin_role:
            return
        if user.is_agent_role:
            self._log_permission_denied("USER_NOT_CHIEF", "Somente o chefe responsÃ¡vel pela escala pode preencher ou enviar este relatório.", agenda.pk)
        allowed = Agenda.objects.filter(pk=agenda.pk).filter(chief_agenda_filter(user)).exists()
        if not allowed:
            self._log_permission_denied("USER_NOT_LINKED_TO_TEAM", "VocÃª nÃ£o possui vÃ­nculo com esta equipe.", agenda.pk)

    def _register_accessibility_block(self, report):
        if report.accessibility_conditions_met != "NO" or not report.agenda_id:
            return
        agenda = report.agenda
        address_parts = [p for p in [agenda.address, agenda.neighborhood, agenda.city, agenda.state] if p]
        full_address = ", ".join(address_parts) if address_parts else (agenda.location or "")

        AccessibilityBlocklist.objects.update_or_create(
            source_report=report,
            defaults={
                "institution_location": agenda.institution_location or agenda.location or "",
                "address": full_address[:220],
                "external_responsible": agenda.external_responsible or "",
                "external_responsible_phone": agenda.external_responsible_phone or "",
                "external_email": agenda.external_email or agenda.contact_email or "",
                "source_agenda": agenda,
                "reason": "Local nÃ£o atendeu Ã s condiÃ§Ãµes de acessibilidade para cadeirantes no relatório técnico.",
                "is_active": True,
            },
        )

    @decorators.action(detail=False, methods=["get"])
    def statistics(self, request):
        try:
            return self._statistics(request)
        except (OperationalError, ProgrammingError) as exc:
            return self._schema_error_response(exc)

    def _statistics(self, request):
        allowed_visitors = ["OLS/CooAdm", "Subsecretaria"]
        is_allowed_visitor = request.user.role == User.Role.VISITOR and request.user.sector and request.user.sector.name in allowed_visitors
        if not (request.user.is_admin_role or request.user.role == User.Role.SUPERVISOR or is_allowed_visitor):
            raise PermissionDenied("Acesso restrito.")

        from django.core.cache import cache
        import hashlib

        query_string = request.META.get('QUERY_STRING', '')
        user_id = request.user.id if request.user.is_authenticated else 0
        cache_key = f"report_stats_{user_id}_{query_string}"
        cache_key = hashlib.md5(cache_key.encode('utf-8')).hexdigest()

        cached_data = cache.get(cache_key)
        if cached_data:
            return response.Response(cached_data)

        params = request.query_params
        reports = self.get_queryset()
        if not params.get("status"):
            reports = reports.filter(status=EducationReport.ReportStatus.APPROVED)

        actions = EducationAction.objects.filter(report_id__in=reports.values("id"))

        yearly_reports = self._statistics_yearly_queryset()
        if not params.get("status"):
            yearly_reports = yearly_reports.filter(status=EducationReport.ReportStatus.APPROVED)
        reference_date = timezone.localdate()
        if params.get("date_to"):
            try:
                reference_date = date.fromisoformat(params["date_to"])
            except ValueError:
                reference_date = timezone.localdate()
        first_year = 2011
        yearly_actions = EducationAction.objects.filter(
            report_id__in=yearly_reports.filter(
                operation_date__year__gte=first_year,
                operation_date__year__lte=reference_date.year,
            ).values("id")
        )

        def total_for(field):
            return actions.aggregate(total=Sum(field))["total"] or 0

        totals = [
            {"key": field, "label": label, "value": total_for(field)}
            for field, label in self.statistics_fields
        ]

        by_team = []
        for row in (
            actions.values("report__team")
            .annotate(
                reports=Count("report", distinct=True),
                actions=Count("id"),
                approach=Sum("approach"),
                tests=Sum("tests"),
                used_caps=Sum("used_caps"),
                distributed_certificates=Sum("distributed_certificates"),
            )
            .order_by("-approach")[:10]
        ):
            by_team.append(
                {
                    "label": row["report__team"] or "Sem equipe",
                    "reports": row["reports"],
                    "actions": row["actions"],
                    "approach": row["approach"] or 0,
                    "tests": row["tests"] or 0,
                    "used_caps": row["used_caps"] or 0,
                    "distributed_certificates": row["distributed_certificates"] or 0,
                }
            )

        by_action_type = [
            {
                "label": row["type_action"] or "Sem tipo",
                "value": row["approach"] or 0,
                "actions": row["actions"],
            }
            for row in (
                actions.values("type_action")
                .annotate(approach=Sum("approach"), actions=Count("id"))
                .order_by("-approach")[:10]
            )
        ]

        by_audience = [
            {
                "label": row["type_audience"] or "Sem pÃºblico",
                "value": row["approach"] or 0,
                "actions": row["actions"],
            }
            for row in (
                actions.values("type_audience")
                .annotate(approach=Sum("approach"), actions=Count("id"))
                .order_by("-approach")[:10]
            )
        ]

        by_day = [
            {
                "date": row["report__operation_date"].isoformat(),
                "label": row["report__operation_date"].strftime("%d/%m"),
                "value": row["approach"] or 0,
                "approached_lectures": row["approached_lectures"] or 0,
                "approached_actions": row["approached_actions"] or 0,
                "tests": row["tests"] or 0,
                "actions": row["actions"],
            }
            for row in (
                actions.values("report__operation_date")
                .annotate(
                    approach=Sum("approach"),
                    approached_lectures=Sum("approached_lectures"),
                    approached_actions=Sum("approached_actions"),
                    tests=Sum("tests"),
                    actions=Count("id"),
                )
                .order_by("report__operation_date")
            )
        ]

        by_status = [
            {"label": row["status"], "value": row["total"]}
            for row in reports.values("status").annotate(total=Count("id")).order_by("status")
        ]

        by_month_year = [
            {
                "year": row["year"],
                "month": row["month"],
                "label": date(2000, row["month"], 1).strftime("%b").title(),
                "approached_lectures": row["approached_lectures"] or 0,
                "approached_actions": row["approached_actions"] or 0,
            }
            for row in (
                yearly_actions.annotate(
                    year=ExtractYear("report__operation_date"),
                    month=ExtractMonth("report__operation_date"),
                )
                .values("year", "month")
                .annotate(
                    approached_lectures=Sum("approached_lectures"),
                    approached_actions=Sum("approached_actions"),
                )
                .order_by("year", "month")
            )
        ]

        # Previous Year Comparison for 4 indicators
        # Usa o ano de referÃªncia (date_to) para determinar o ano atual e o anterior completo
        date_to_str = params.get("date_to")
        try:
            ref_date = date.fromisoformat(date_to_str) if date_to_str else timezone.localdate()
        except ValueError:
            ref_date = timezone.localdate()

        ref_year = ref_date.year
        prev_year = ref_year - 1

        # PerÃ­odo atual: todo o ano de referÃªncia atÃ© a data selecionada
        current_date_from = date(ref_year, 1, 1)
        current_date_to = ref_date

        # PerÃ­odo anterior: ano inteiro anterior (01/01 a 31/12)
        prev_date_from = date(prev_year, 1, 1)
        prev_date_to = date(prev_year, 12, 31)

        def get_scoped_reports():
            user = request.user
            qs = EducationReport.objects.select_related("agenda", "created_by").prefetch_related(
                "actions",
                "actions__agenda",
            )
            if user.is_agent_role:
                qs = qs.none()
            elif not user.is_admin_role:
                qs = qs.filter(chief_agenda_filter(user, prefix="agenda__")).distinct()

            if params.get("protocol"):
                qs = qs.filter(agenda_id=params["protocol"])
            if params.get("team"):
                qs = qs.filter(team__icontains=params["team"].strip())
            if params.get("source"):
                qs = qs.filter(source=params["source"])
            if params.get("status"):
                qs = qs.filter(status=params["status"])
            else:
                qs = qs.filter(status=EducationReport.ReportStatus.APPROVED)
            if params.get("q"):
                term = params["q"].strip()
                search_filter = (
                    Q(team__icontains=term)
                    | Q(agenda__source_id__icontains=term)
                    | Q(agenda__title__icontains=term)
                    | Q(management_name__icontains=term)
                    | Q(contact_received__icontains=term)
                    | Q(occurrence_observation__icontains=term)
                    | Q(actions__place_action__icontains=term)
                    | Q(actions__type_action__icontains=term)
                    | Q(actions__institution_name__icontains=term)
                )
                if term.isdigit():
                    search_filter |= Q(agenda_id=int(term)) | Q(agenda__service_order_number=int(term))
                qs = qs.filter(search_filter)
            return qs

        cur_reports  = get_scoped_reports().filter(operation_date__gte=current_date_from, operation_date__lte=current_date_to)
        prev_reports = get_scoped_reports().filter(operation_date__gte=prev_date_from,    operation_date__lte=prev_date_to)

        cur_actions  = EducationAction.objects.filter(report_id__in=cur_reports.values("id"))
        prev_actions = EducationAction.objects.filter(report_id__in=prev_reports.values("id"))

        comparison_fields = [
            ("approach",           "Abordagens"),
            ("approached_actions", "Abordados em aÃ§Ãµes"),
            ("publicity_materials","Materiais de divulgaÃ§Ã£o"),
            ("approached_lectures","Abordados em palestras"),
        ]

        comparison_list = []
        cur_agg = cur_actions.aggregate(**{key: Sum(key) for key, _ in comparison_fields})
        prev_agg = prev_actions.aggregate(**{key: Sum(key) for key, _ in comparison_fields})

        for key, label in comparison_fields:
            current_val = cur_agg.get(key) or 0
            prev_val = prev_agg.get(key) or 0
            diff = current_val - prev_val
            if prev_val > 0:
                pct_change = round((diff / prev_val) * 100, 1)
            elif current_val > 0:
                pct_change = 100.0
            else:
                pct_change = 0.0

            comparison_list.append({
                "key":        key,
                "label":      label,
                "current":    current_val,
                "previous":   prev_val,
                "difference": diff,
                "percentage": pct_change,
                "prev_year":  prev_year,
                "ref_year":   ref_year,
            })

        by_entity_type = [
            {"label": row["agenda__requester_entity_type"], "value": row["total"]}
            for row in (
                reports.exclude(agenda__requester_entity_type="")
                .values("agenda__requester_entity_type")
                .annotate(total=Count("id"))
                .order_by("-total")
            )
        ]

        by_modality = [
            {"label": row["agenda__action_type"], "value": row["total"]}
            for row in (
                reports.exclude(agenda__action_type="")
                .values("agenda__action_type")
                .annotate(total=Count("id"))
                .order_by("-total")
            )
        ]

        by_age_range = [
            {"label": row["agenda__age_ranges"], "value": row["total"]}
            for row in (
                reports.exclude(agenda__age_ranges="")
                .values("agenda__age_ranges")
                .annotate(total=Count("id"))
                .order_by("-total")
            )
        ]

        historical_totals = [
            {
                "year": row["year"],
                **{
                    field: row.get(field) or 0
                    for field, _ in self.statistics_fields
                }
            }
            for row in (
                yearly_actions.annotate(
                    year=ExtractYear("report__operation_date"),
                )
                .values("year")
                .annotate(
                    **{field: Sum(field) for field, _ in self.statistics_fields}
                )
                .order_by("year")
            )
        ]

        data = {
            "reports_count": reports.count(),
            "actions_count": actions.count(),
            "totals": totals,
            "by_team": by_team,
            "by_action_type": by_action_type,
            "by_audience": by_audience,
            "by_day": by_day,
            "by_status": by_status,
            "by_month_year": by_month_year,
            "comparison": comparison_list,
            "by_entity_type": by_entity_type,
            "by_modality": by_modality,
            "by_age_range": by_age_range,
            "historical_totals": historical_totals,
        }

        cache.set(cache_key, data, 60 * 15)
        return response.Response(data)

    @decorators.action(detail=False, methods=["get"], url_path="export-statistics")
    def export_statistics(self, request):
        allowed_visitors = ["OLS/CooAdm", "Subsecretaria"]
        is_allowed_visitor = request.user.role == User.Role.VISITOR and request.user.sector and request.user.sector.name in allowed_visitors
        if not (request.user.is_admin_role or request.user.role == User.Role.SUPERVISOR or is_allowed_visitor):
            raise PermissionDenied("Apenas Chefes, Gestores e Administração podem exportar estatísticas.")
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from io import BytesIO

        reports = self.get_queryset()
        actions = EducationAction.objects.filter(report_id__in=reports.values("id"))
        today = timezone.localdate()
        reference_date = today
        if request.query_params.get("date_to"):
            try:
                reference_date = date.fromisoformat(request.query_params["date_to"])
            except ValueError:
                reference_date = today
        reference_year = reference_date.year
        elapsed_months = max(reference_date.month, 1)

        totals_agg = actions.aggregate(**{field: Sum(field) for field, _ in self.statistics_fields})
        totals = {
            field: totals_agg.get(field) or 0
            for field, _label in self.statistics_fields
        }
        goals = {
            goal.key: goal
            for goal in EducationGoal.objects.filter(year=reference_year, is_active=True)
        }

        goal_structure = [
            {
                "key": "approach", "label": "1 - ABORDADOS", "section": True,
                "children": [
                    {"key": "approached_lectures", "label": "1.1 - ABORDADOS PALESTRAS"},
                    {"key": "approached_actions", "label": "1.2 - ABORDADOS AÃ‡Ã•ES"},
                ],
            },
            {
                "key": "lectures", "label": "2 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“ PALESTRAS", "section": True,
                "children": [
                    {"key": "schools", "label": "2.1 - ESCOLAS"},
                    {"key": "universities", "label": "2.2 - UNIVERSIDADES"},
                    {"key": "companies", "label": "2.3 - EMPRESAS"},
                ],
            },
            {
                "key": "educational_actions", "label": "3 - AÃ‡Ã•ES", "section": True,
                "children": [
                    {"key": "bars", "label": "3.1 - BAR/RESTAURANTE"},
                    {"key": "tolls", "label": "3.2 - PEDÃGIO"},
                    {"key": "sports", "label": "3.3 - PRAÃ‡A ESPORTIVA"},
                    {"key": "beach", "label": "3.4 - PRAIA"},
                    {"key": "events", "label": "3.5 - EVENTO"},
                    {"key": "shopping", "label": "3.6 - SHOPPING/CENTRO COMERCIAL"},
                    {"key": "parks", "label": "3.7 - PRAÃ‡AS/PARQUES PÃšBLICOS"},
                    {"key": "tourist_spots", "label": "3.8 - PONTOS TURÃSTICOS"},
                    {"key": "social_actions", "label": "3.9 - AÃ‡ÃƒO SOCIAL"},
                    {"key": "joint_inspections", "label": "3.10 - AÃ‡ÃƒO CONJUNTA COM A FISCALIZAÃ‡ÃƒO"},
                    {"key": "other_actions", "label": "3.11 - OUTROS"},
                ],
            },
            {
                "key": "publicity_materials", "label": "4 - MATERIAIS DE DIVULGAÃ‡ÃƒO", "section": True,
                "children": [
                    {"key": "distributed_certificates", "label": "4.1 - CERTIFICADOS ENTREGUES"},
                    {"key": "gibis", "label": '4.2 - KIT "Escolinha Nota 10"'},
                ],
            },
        ]

        def build_goal_rows():
            rows = []
            for group in goal_structure:
                goal = goals.get(group["key"])
                accumulated = totals.get(group["key"], 0)
                rows.append({
                    "label": goal.label if goal else group["label"],
                    "accumulated": accumulated,
                    "projection": round((accumulated / elapsed_months) * 12),
                    "average": goal.average if goal else 0,
                    "target": goal.target if goal else 0,
                    "section": True,
                })
                for child in group.get("children", []):
                    child_goal = goals.get(child["key"])
                    child_accumulated = totals.get(child["key"], 0)
                    rows.append({
                        "label": child_goal.label if child_goal else child["label"],
                        "accumulated": child_accumulated,
                        "projection": round((child_accumulated / elapsed_months) * 12),
                        "average": child_goal.average if child_goal else 0,
                        "target": child_goal.target if child_goal else 0,
                        "section": False,
                    })
            return rows

        goal_rows = build_goal_rows()

        yearly_reports = self._statistics_yearly_queryset().filter(
            operation_date__year__gte=2019,
            operation_date__year__lte=reference_year,
        )
        yearly_rows = list(
            EducationAction.objects.filter(report_id__in=yearly_reports.values("id"))
            .annotate(year=ExtractYear("report__operation_date"))
            .values("year")
            .annotate(
                approached_lectures=Sum("approached_lectures"),
                approached_actions=Sum("approached_actions"),
            )
            .order_by("year")
        )

        def fmt(value):
            return f"{int(value or 0):,}".replace(",", ".")

        # --- Colors ---
        GREEN_SECTION = colors.HexColor("#d5f5d5")
        RED_SECTION = colors.HexColor("#f5d5d5")
        HEADER_BG = colors.HexColor("#1a5c2a")
        HEADER_FG = colors.white
        ZEBRA_EVEN = colors.HexColor("#f4f4f4")
        ZEBRA_ODD = colors.white
        BORDER_COLOR = colors.HexColor("#cccccc")
        DARK_TEXT = colors.HexColor("#1a1a1a")

        section_colors = {
            "1": GREEN_SECTION,
            "2": GREEN_SECTION,
            "3": RED_SECTION,
            "4": GREEN_SECTION,
        }

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("ReportTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=4, textColor=DARK_TEXT, fontName="Helvetica-Bold")
        subtitle_style = ParagraphStyle("ReportSubtitle", parent=styles["Normal"], fontSize=9, spaceAfter=2, textColor=colors.HexColor("#555555"))
        section_title_style = ParagraphStyle("SectionTitle", parent=styles["Heading2"], fontSize=12, spaceBefore=18, spaceAfter=6, textColor=DARK_TEXT, fontName="Helvetica-Bold")
        cell_style = ParagraphStyle("CellStyle", parent=styles["Normal"], fontSize=8, leading=10, textColor=DARK_TEXT)
        cell_bold = ParagraphStyle("CellBold", parent=cell_style, fontName="Helvetica-Bold")
        cell_center = ParagraphStyle("CellCenter", parent=cell_style, alignment=TA_CENTER)
        cell_center_bold = ParagraphStyle("CellCenterBold", parent=cell_bold, alignment=TA_CENTER)
        header_cell = ParagraphStyle("HeaderCell", parent=cell_bold, textColor=HEADER_FG, fontSize=8, alignment=TA_CENTER)
        header_left = ParagraphStyle("HeaderLeft", parent=header_cell, alignment=TA_LEFT)
        note_style = ParagraphStyle("NoteStyle", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#666666"), spaceBefore=2)
        footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#999999"), alignment=TA_CENTER)

        period_from = request.query_params.get("date_from") or "inÃ­cio"
        period_to = request.query_params.get("date_to") or today.isoformat()
        month_label = reference_date.strftime("%m")

        elements = []

        # --- Header ---
        elements.append(Paragraph("OperaÃ§Ã£o Lei Seca", title_style))
        elements.append(Paragraph("Relatório TÃ©cnico de EstatÃ­sticas", ParagraphStyle("Sub", parent=subtitle_style, fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#333333"))))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"PerÃ­odo analisado: {period_from} a {period_to}", subtitle_style))
        elements.append(Paragraph(f"Emitido em: {today.strftime('%d/%m/%Y')} &nbsp;|&nbsp; Relatórios: {reports.count()} &nbsp;|&nbsp; AÃ§Ãµes registradas: {actions.count()}", subtitle_style))
        elements.append(Spacer(1, 6))

        # --- Section 1: Quadro de metas ---
        elements.append(Paragraph(f"1. Quadro de metas {reference_year}", section_title_style))
        data_2 = [[
            Paragraph("Indicador", header_left),
            Paragraph(f"{reference_year} atÃ© {month_label}", header_cell),
            Paragraph(f"ProjeÃ§Ã£o {reference_year}", header_cell),
            Paragraph("MÃ©dia*", header_cell),
            Paragraph(f"Meta {reference_year}", header_cell),
        ]]
        goal_section_indices = []
        for row in goal_rows:
            is_section = row.get("section", False)
            row_index = len(data_2)
            s = cell_bold if is_section else cell_style
            sc = cell_center_bold if is_section else cell_center
            data_2.append([
                Paragraph(row["label"], s),
                Paragraph(fmt(row["accumulated"]), sc),
                Paragraph(fmt(row["projection"]), sc),
                Paragraph(fmt(row["average"]), sc),
                Paragraph(fmt(row["target"]), sc),
            ])
            if is_section:
                goal_section_indices.append(row_index)

        t2 = Table(data_2, colWidths=[200, 80, 80, 80, 80], repeatRows=1)
        style_2 = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
            ("TOPPADDING", (0, 1), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
        for i in range(1, len(data_2)):
            if i in goal_section_indices:
                label_text = data_2[i][0].text if hasattr(data_2[i][0], "text") else ""
                section_num = label_text.strip()[:1] if label_text else ""
                bg = section_colors.get(section_num, GREEN_SECTION)
                style_2.add("BACKGROUND", (0, i), (-1, i), bg)
            else:
                bg = ZEBRA_EVEN if i % 2 == 0 else ZEBRA_ODD
                style_2.add("BACKGROUND", (0, i), (-1, i), bg)
        t2.setStyle(style_2)
        elements.append(t2)

        elements.append(Spacer(1, 12))

        # --- Section 2: EvoluÃ§Ã£o anual ---
        elements.append(Paragraph("2. EvoluÃ§Ã£o anual desde 2019", section_title_style))
        data_3 = [[
            Paragraph("Ano", header_left),
            Paragraph("Abordados em palestras", header_cell),
            Paragraph("Abordados em aÃ§Ãµes", header_cell),
        ]]
        for row in yearly_rows:
            data_3.append([
                Paragraph(str(row["year"]), cell_bold),
                Paragraph(fmt(row["approached_lectures"]), cell_center),
                Paragraph(fmt(row["approached_actions"]), cell_center),
            ])

        if len(data_3) > 1:
            t3 = Table(data_3, colWidths=[100, 200, 200], repeatRows=1)
            style_3 = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
            for i in range(1, len(data_3)):
                bg = ZEBRA_EVEN if i % 2 == 0 else ZEBRA_ODD
                style_3.add("BACKGROUND", (0, i), (-1, i), bg)
            t3.setStyle(style_3)
            elements.append(t3)

        elements.append(Spacer(1, 12))

        # --- Section 3: Indicadores Consolidados ---
        elements.append(Paragraph("3. Indicadores consolidados", section_title_style))
        data_1 = [[Paragraph("Indicador", header_left), Paragraph("Valor", header_cell)]]
        sorted_fields = sorted(self.statistics_fields, key=lambda item: totals.get(item[0], 0), reverse=True)
        for field, label in sorted_fields:
            value = totals.get(field, 0)
            if value:
                data_1.append([Paragraph(label, cell_style), Paragraph(fmt(value), cell_center)])

        if len(data_1) > 1:
            t1 = Table(data_1, colWidths=[320, 100], repeatRows=1)
            style_1 = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
            for i in range(1, len(data_1)):
                bg = ZEBRA_EVEN if i % 2 == 0 else ZEBRA_ODD
                style_1.add("BACKGROUND", (0, i), (-1, i), bg)
            t1.setStyle(style_1)
            elements.append(t1)

        elements.append(Spacer(1, 16))

        # --- Section 4: ComparaÃ§Ã£o Ano a Ano ---
        params = request.query_params
        date_to_str = params.get("date_to")
        try:
            ref_date_cmp = date.fromisoformat(date_to_str) if date_to_str else today
        except ValueError:
            ref_date_cmp = today
        cmp_ref_year = ref_date_cmp.year
        cmp_prev_year = cmp_ref_year - 1

        cmp_current_from = date(cmp_ref_year, 1, 1)
        cmp_current_to = ref_date_cmp
        cmp_prev_from = date(cmp_prev_year, 1, 1)
        cmp_prev_to = date(cmp_prev_year, 12, 31)

        cmp_cur_reports = reports.filter(operation_date__gte=cmp_current_from, operation_date__lte=cmp_current_to)
        cmp_prev_reports = self._statistics_yearly_queryset().filter(operation_date__gte=cmp_prev_from, operation_date__lte=cmp_prev_to)

        cmp_cur_actions = EducationAction.objects.filter(report_id__in=cmp_cur_reports.values("id"))
        cmp_prev_actions = EducationAction.objects.filter(report_id__in=cmp_prev_reports.values("id"))

        comparison_fields = [
            ("approach", "Abordagens"),
            ("approached_actions", "Abordados em aÃ§Ãµes"),
            ("publicity_materials", "Materiais de divulgaÃ§Ã£o"),
            ("approached_lectures", "Abordados em palestras"),
        ]

        BLUE_HEADER = colors.HexColor("#003299")

        elements.append(Paragraph("4. ComparaÃ§Ã£o Ano a Ano", section_title_style))
        elements.append(Paragraph(f"Indicadores do ano de referÃªncia ({cmp_ref_year}) versus o ano anterior ({cmp_prev_year}) completo.", note_style))
        elements.append(Spacer(1, 4))

        data_cmp = [[
            Paragraph("Indicador", header_left),
            Paragraph(f"{cmp_ref_year} (acumulado)", header_cell),
            Paragraph(f"{cmp_prev_year} (total)", header_cell),
            Paragraph("DiferenÃ§a", header_cell),
            Paragraph("VariaÃ§Ã£o %", header_cell),
        ]]
        cmp_cur_agg = cmp_cur_actions.aggregate(**{key: Sum(key) for key, _ in comparison_fields})
        cmp_prev_agg = cmp_prev_actions.aggregate(**{key: Sum(key) for key, _ in comparison_fields})

        for key, label in comparison_fields:
            cur_val = cmp_cur_agg.get(key) or 0
            prev_val = cmp_prev_agg.get(key) or 0
            diff = cur_val - prev_val
            if prev_val > 0:
                pct = round((diff / prev_val) * 100, 1)
            elif cur_val > 0:
                pct = 100.0
            else:
                pct = 0.0
            pct_str = f"+{pct}%" if pct > 0 else f"{pct}%"
            data_cmp.append([
                Paragraph(label, cell_bold),
                Paragraph(fmt(cur_val), cell_center),
                Paragraph(fmt(prev_val), cell_center),
                Paragraph(fmt(diff), cell_center),
                Paragraph(pct_str, cell_center_bold),
            ])

        t_cmp = Table(data_cmp, colWidths=[160, 90, 90, 80, 80], repeatRows=1)
        style_cmp = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
            ("TOPPADDING", (0, 1), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
        for i in range(1, len(data_cmp)):
            bg = ZEBRA_EVEN if i % 2 == 0 else ZEBRA_ODD
            style_cmp.add("BACKGROUND", (0, i), (-1, i), bg)
        t_cmp.setStyle(style_cmp)
        elements.append(t_cmp)

        elements.append(Spacer(1, 16))

        # --- Section 5: Nota tÃ©cnica ---
        elements.append(Paragraph("5. Nota tÃ©cnica", section_title_style))
        notes = [
            "Os dados deste relatório sÃ£o calculados a partir dos relatórios técnicos cadastrados no sistema.",
            "A projeÃ§Ã£o anual considera o acumulado do ano dividido pela quantidade de meses transcorridos e multiplicado por 12.",
            "As metas e mÃ©dias histÃ³ricas sÃ£o obtidas do cadastro anual de metas da aplicaÃ§Ã£o.",
            "* MÃ©dia refere-se Ã  mÃ©dia histÃ³rica dos anos anteriores registrados no sistema.",
        ]
        for note in notes:
            elements.append(Paragraph(f"ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢ {note}", note_style))

        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"OperaÃ§Ã£o Lei Seca ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Relatório gerado automaticamente em {today.strftime('%d/%m/%Y')}", footer_style))

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=30,
            title=f"Relatório de EstatÃ­sticas {reference_year}",
            author="Agenda OLS",
        )
        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()

        response_file = HttpResponse(pdf_content, content_type="application/pdf")
        response_file["Content-Disposition"] = f'attachment; filename="relatorio-estatisticas-{reference_year}.pdf"'
        return response_file

    def _statistics_yearly_queryset(self):
        user = self.request.user
        queryset = EducationReport.objects.select_related("agenda", "created_by").prefetch_related(
            "actions",
            "actions__agenda",
        )
        if user.is_agent_role:
            scoped = queryset.none()
        elif user.is_admin_role:
            scoped = queryset
        else:
            scoped = queryset.filter(chief_agenda_filter(user, prefix="agenda__")).distinct()

        params = self.request.query_params
        if params.get("protocol"):
            scoped = scoped.filter(agenda_id=params["protocol"])
        if params.get("team"):
            scoped = scoped.filter(team__icontains=params["team"].strip())
        if params.get("source"):
            scoped = scoped.filter(source=params["source"])
        if params.get("status"):
            scoped = scoped.filter(status=params["status"])
        if params.get("q"):
            term = params["q"].strip()
            search_filter = (
                Q(team__icontains=term)
                | Q(agenda__source_id__icontains=term)
                | Q(agenda__title__icontains=term)
                | Q(management_name__icontains=term)
                | Q(contact_received__icontains=term)
                | Q(occurrence_observation__icontains=term)
                | Q(actions__place_action__icontains=term)
                | Q(actions__type_action__icontains=term)
                | Q(actions__institution_name__icontains=term)
            )
            if term.isdigit():
                search_filter |= Q(agenda_id=int(term)) | Q(agenda__service_order_number=int(term))
            scoped = scoped.filter(search_filter)
        return scoped.distinct()


class EducationGoalViewSet(viewsets.ModelViewSet):
    serializer_class = EducationGoalSerializer
    permission_classes = [IsAuthenticated, AdminOrReadSectorPermission]

    def get_queryset(self):
        queryset = EducationGoal.objects.all()
        year = self.request.query_params.get("year")
        if year:
            queryset = queryset.filter(year=year)
        if self.request.query_params.get("include_inactive") != "true":
            queryset = queryset.filter(is_active=True)
        return queryset.order_by("year", "order", "label")


class AccessibilityBlocklistViewSet(viewsets.ModelViewSet):
    serializer_class = AccessibilityBlocklistSerializer
    permission_classes = [IsAuthenticated, VisitorReadOnly]

    def get_queryset(self):
        user = self.request.user
        if not (user.is_admin_role or user.role == User.Role.SUPERVISOR):
            raise PermissionDenied("Sem permissÃ£o para gerenciar a lista de restriÃ§Ãµes de acessibilidade.")

        queryset = AccessibilityBlocklist.objects.all()
        term = self.request.query_params.get("search")
        if term:
            queryset = queryset.filter(
                Q(institution_location__icontains=term)
                | Q(address__icontains=term)
                | Q(external_responsible__icontains=term)
                | Q(external_email__icontains=term)
            )

        include_inactive = self.request.query_params.get("include_inactive")
        if include_inactive != "true":
            queryset = queryset.filter(is_active=True)

        return queryset.order_by("-created_at")


class PublicCepLookupView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "anon"

    def get(self, request):
        cep = re.sub(r"\D", "", request.query_params.get("cep", ""))
        if len(cep) != 8:
            return response.Response({"detail": "Informe um CEP com 8 digitos."}, status=status.HTTP_400_BAD_REQUEST)

        req = Request(
            f"https://viacep.com.br/ws/{cep}/json/",
            headers={"User-Agent": "agenda-educacao/1.0"},
        )
        try:
            with urlopen(req, timeout=8) as remote_response:
                payload = json.loads(remote_response.read().decode("utf-8"))
        except HTTPError:
            return response.Response({"detail": "Nao foi possivel consultar o CEP agora."}, status=status.HTTP_502_BAD_GATEWAY)
        except URLError:
            return response.Response({"detail": "Nao foi possivel consultar o CEP agora."}, status=status.HTTP_502_BAD_GATEWAY)

        if payload.get("erro"):
            return response.Response({"detail": "CEP nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        return response.Response(
            {
                "cep": payload.get("cep", ""),
                "address": payload.get("logradouro", ""),
                "neighborhood": payload.get("bairro", ""),
                "city": payload.get("localidade", ""),
                "state": payload.get("uf", ""),
                "complement": payload.get("complemento", ""),
            }
        )


class PublicAgendaRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "anon"

    def get(self, request):
        date_str = request.query_params.get("date")
        if not date_str:
            return response.Response({"detail": "Informe a data."}, status=400)

        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return response.Response({"detail": "Formato de data invÃ¡lido."}, status=400)

        agenda_id = request.query_params.get("agenda_id")
        qs = Agenda.objects.filter(
            date=date_obj,
            status__in=[Agenda.Status.PENDING, Agenda.Status.APPROVED]
        )
        if agenda_id and agenda_id.isdigit():
            qs = qs.exclude(id=int(agenda_id))

        return response.Response({"available": True})

    def post(self, request):
        serializer = PublicAgendaRequestSerializer(data=request.data, context={"is_internal_request": False})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        public_sector, _ = Sector.objects.get_or_create(
            name="SolicitaÃ§Ãµes externas",
            defaults={"description": "SolicitaÃ§Ãµes recebidas por formulÃ¡rio pÃºblico"},
        )
        system_user, created = User.objects.get_or_create(
            email="solicitacao.publica@agenda.local",
            defaults={
                "username": "solicitacao.publica@agenda.local",
                "full_name": "SolicitaÃ§Ã£o PÃºblica",
                "role": User.Role.USER,
                "is_active": False,
                "sector": public_sector,
            },
        )
        if system_user.role != User.Role.USER or system_user.is_active:
            system_user.role = User.Role.USER
            system_user.is_active = False
            system_user.save(update_fields=["role", "is_active"])
        if created:
            system_user.set_unusable_password()
            system_user.save()
        agenda = Agenda.objects.create(
            source_id=f"internal-request:{request.user.id}:{timezone.now().strftime('%Y%m%d%H%M%S%f')}",
            title=data["title"],
            description=data["description"],
            date=data["date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            time_2=data.get("time_2"),
            time_3=data.get("time_3"),
            location=data["address"] if data["requester_entity_type"].startswith("AÃ§Ã£o de Rua") else data["institution_location"],
            action_type=data["action_type"],
            institution_location=data["institution_location"],
            actions_count=data.get("actions_count"),
            address=data["address"],
            neighborhood=data.get("neighborhood", ""),
            city=data["city"],
            state=data.get("state", ""),
            external_responsible=data["external_responsible"],
            external_responsible_phone=data["external_responsible_phone"],
            external_email=data["external_email"],
            contact_email=data.get("contact_email", ""),
            requester_cpf=data.get("requester_cpf", ""),
            requester_role=data.get("requester_role", ""),
            requester_entity_type=data["requester_entity_type"],
            administrative_demand_type=data.get("administrative_demand_type", ""),
            audience=data.get("audience", ""),
            participant_range=data.get("participant_range", ""),
            age_ranges=data.get("age_ranges", ""),
            accessibility_access=data.get("accessibility_access", ""),
            has_ramps=data.get("has_ramps", ""),
            has_elevators=data.get("has_elevators", ""),
            has_accessible_bathrooms=data.get("has_accessible_bathrooms", ""),
            media_equipment=data.get("media_equipment", ""),
            image_authorization=data.get("image_authorization", ""),
            quantity=data.get("quantity"),
            notes=data.get("notes", ""),
            status=Agenda.Status.PENDING,
            origin=Agenda.Origin.PUBLIC_FORM,
            responsible=system_user,
            created_by=system_user,
            sector=public_sector,
        )
        AgendaHistory.objects.create(
            agenda=agenda,
            changed_by=system_user,
            action="SOLICITACAO_PUBLICA",
            snapshot=snapshot_for(agenda),
        )
        from apps.schedules.serializers import find_accessibility_block
        from apps.schedules.accessibility import schedule_accessibility_rejection
        block = find_accessibility_block(data)
        if block:
            schedule_accessibility_rejection(agenda, block)

        transaction.on_commit(lambda: send_agenda_status_email(agenda, Agenda.Status.PENDING))
        return response.Response(
            {
                "detail": "SolicitaÃ§Ã£o enviada com sucesso. Acompanhe o retorno pelo contato informado.",
                "protocol": agenda.id,
            },
            status=201,
        )


class PublicAgendaRequestUpdateView(APIView):
    permission_classes = [AllowAny]

    def get_agenda(self, token):
        try:
            payload = signing.loads(token, salt=PUBLIC_REQUEST_SALT)
            return Agenda.objects.get(pk=payload["agenda"])
        except (signing.BadSignature, KeyError, Agenda.DoesNotExist):
            raise PermissionDenied("Link de alteraÃ§Ã£o invÃ¡lido.")

    def get(self, request, token):
        agenda = self.get_agenda(token)
        return response.Response(
            {
                "protocol": agenda.id,
                "title": agenda.title,
                "institution_location": agenda.institution_location,
                "external_responsible": agenda.external_responsible,
                "external_email": agenda.external_email,
                "date": agenda.date,
                "start_time": agenda.start_time,
                "end_time": agenda.end_time,
                "actions_count": agenda.actions_count,
                "time_2": agenda.time_2,
                "time_3": agenda.time_3,
                "status": agenda.status,
            }
        )

    def patch(self, request, token):
        agenda = self.get_agenda(token)
        serializer = PublicAgendaRequestRescheduleSerializer(data=request.data, context={"agenda_id": agenda.id})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        agenda.date = data["date"]
        agenda.start_time = data["start_time"]
        agenda.end_time = data["end_time"]
        agenda.actions_count = data.get("actions_count")
        agenda.time_2 = data.get("time_2")
        agenda.time_3 = data.get("time_3")
        agenda.status = Agenda.Status.PENDING
        agenda.cancel_reason = ""
        agenda.save(
            update_fields=[
                "date",
                "start_time",
                "end_time",
                "actions_count",
                "time_2",
                "time_3",
                "status",
                "cancel_reason",
                "updated_at",
            ]
        )
        AgendaHistory.objects.create(
            agenda=agenda,
            changed_by=agenda.created_by,
            action="REENVIO_PUBLICO_DATA",
            snapshot=snapshot_for(agenda),
        )
        return response.Response(
            {
                "detail": "Data atualizada e formulÃ¡rio reenviado para avaliaÃ§Ã£o.",
                "protocol": agenda.id,
            }
        )


class SatisfactionSurveyPublicView(APIView):
    permission_classes = [AllowAny]

    def get_survey(self, token):
        try:
            return SatisfactionSurvey.objects.select_related("agenda", "report").get(token=token)
        except SatisfactionSurvey.DoesNotExist:
            raise PermissionDenied("Link da pesquisa invÃ¡lido.")

    def get(self, request, token):
        survey = self.get_survey(token)
        return response.Response(SatisfactionSurveySerializer(survey).data)

    def post(self, request, token):
        survey = self.get_survey(token)
        if survey.answered_at:
            return response.Response({"detail": "Esta pesquisa jÃ¡ foi respondida."}, status=400)
        serializer = SatisfactionSurveySerializer(survey, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        suggestion = request.data.get("suggestion", "").strip()
        moderation_status = (
            SatisfactionSurvey.ModerationStatus.PENDING
            if suggestion
            else SatisfactionSurvey.ModerationStatus.APPROVED
        )
        serializer.save(
            answered_at=timezone.now(),
            is_approved=moderation_status == SatisfactionSurvey.ModerationStatus.APPROVED,
            moderation_status=moderation_status,
        )
        return response.Response({"detail": "Pesquisa enviada com sucesso. Obrigado pela avaliaÃ§Ã£o."})


class InternalAgendaRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role == User.Role.VISITOR:
            raise PermissionDenied("O perfil Visitante não possui acesso ao módulo Solicitações.")
        if not (request.user.is_admin_role or request.user.role == User.Role.SUPERVISOR):
            raise PermissionDenied("Apenas Chefes, Gestores e Administração podem criar solicitações internas.")
        serializer = PublicAgendaRequestSerializer(data=request.data, context={"is_internal_request": True})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        internal_sector, _ = Sector.objects.get_or_create(
            name="SolicitaÃ§Ãµes internas",
            defaults={"description": "SolicitaÃ§Ãµes cadastradas internamente pela equipe"},
        )
        agenda = Agenda.objects.create(
            title=data["title"],
            description=data["description"],
            date=data["date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            time_2=data.get("time_2"),
            time_3=data.get("time_3"),
            location=data["institution_location"],
            action_type=data["action_type"],
            institution_location=data["institution_location"],
            actions_count=data.get("actions_count"),
            address=data["address"],
            neighborhood=data.get("neighborhood", ""),
            city=data["city"],
            state=data.get("state", ""),
            external_responsible=data["external_responsible"],
            external_responsible_phone=data["external_responsible_phone"],
            external_email=data["external_email"],
            contact_email=data.get("contact_email", ""),
            requester_cpf=data.get("requester_cpf", ""),
            requester_role=data.get("requester_role", ""),
            requester_entity_type=data["requester_entity_type"],
            administrative_demand_type=data.get("administrative_demand_type", ""),
            audience=data.get("audience", ""),
            participant_range=data.get("participant_range", ""),
            age_ranges=data.get("age_ranges", ""),
            accessibility_access=data.get("accessibility_access", ""),
            has_ramps=data.get("has_ramps", ""),
            has_elevators=data.get("has_elevators", ""),
            has_accessible_bathrooms=data.get("has_accessible_bathrooms", ""),
            media_equipment=data.get("media_equipment", ""),
            image_authorization=data.get("image_authorization", ""),
            quantity=data.get("quantity"),
            notes=data.get("notes", ""),
            status=Agenda.Status.PENDING,
            origin=Agenda.Origin.INTERNAL,
            responsible=request.user,
            created_by=request.user,
            sector=internal_sector,
        )
        AgendaHistory.objects.create(
            agenda=agenda,
            changed_by=request.user,
            action="SOLICITACAO_INTERNA",
            snapshot=snapshot_for(agenda),
        )
        log_audit(
            request,
            AuditLog.Action.CREATE,
            "Agendas",
            f"Solicitacao interna criada: protocolo {agenda.id}.",
            {"agenda_id": agenda.id, "title": agenda.title, "status": agenda.status},
        )
        from apps.schedules.serializers import find_accessibility_block
        from apps.schedules.accessibility import schedule_accessibility_rejection
        block = find_accessibility_block(data)
        if block:
            schedule_accessibility_rejection(agenda, block)
        transaction.on_commit(lambda: send_agenda_status_email(agenda, Agenda.Status.PENDING))
        return response.Response(
            {
                "detail": "SolicitaÃ§Ã£o interna registrada com sucesso.",
                "protocol": agenda.id,
            },
            status=201,
        )


class ReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _check_access(self, request):
        if not request.user.is_admin_role:
            raise PermissionDenied("Apenas Gestores e Administração podem acessar relatórios.")

    def _queryset(self, request, *, check_access=True, unscoped=False):
        if check_access:
            self._check_access(request)
        user = request.user
        scoped = Agenda.objects.select_related("responsible", "sector", "created_by")
        if unscoped or user.is_admin_role:
            pass
        elif user.role == User.Role.SUPERVISOR:
            scoped = scoped.filter(
                Q(sector_id=user.sector_id)
                | chief_agenda_filter(user)
            )
        else:
            scoped = scoped.filter(Q(created_by=user) | Q(responsible=user))

        params = request.query_params
        if params.get("date"):
            scoped = scoped.filter(date=params["date"])
        if params.get("date_from"):
            scoped = scoped.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            scoped = scoped.filter(date__lte=params["date_to"])
        if params.get("status"):
            scoped = scoped.filter(status=params["status"])
        if params.get("municipality"):
            scoped = scoped.filter(municipality_ref_id=params["municipality"])
        if params.get("region"):
            scoped = scoped.filter(municipality_ref__region_id=params["region"])
        if params.get("q"):
            term = params["q"].strip()
            search_filter = (
                Q(source_id__icontains=term)
                | Q(title__icontains=term)
                | Q(institution_location__icontains=term)
                | Q(location__icontains=term)
                | Q(address__icontains=term)
                | Q(neighborhood__icontains=term)
                | Q(city__icontains=term)
                | Q(external_responsible__icontains=term)
                | Q(agents__icontains=term)
            )
            if term.isdigit():
                search_filter |= Q(id=int(term)) | Q(service_order_number=int(term))
            scoped = scoped.filter(search_filter)
        return scoped.distinct().order_by("date", "start_time")

    def list(self, request):
        qs = self._queryset(request)
        return response.Response(
            {
                "total": qs.count(),
                "by_status": list(qs.values("status").annotate(total=Count("id")).order_by("status")),
                "by_sector": list(qs.values("sector__name").annotate(total=Count("id")).order_by("sector__name")),
                "by_user": list(qs.values("created_by__full_name").annotate(total=Count("id")).order_by("created_by__full_name")),
            }
        )

    @decorators.action(detail=False, methods=["get"])
    def export_excel(self, request):
        qs = self._queryset(request)
        log_audit(
            request,
            AuditLog.Action.REPORT_EXPORT,
            "Relatorios",
            "Relatorio de agendas exportado em Excel.",
            {"format": "xlsx", "total": qs.count()},
        )
        wb = Workbook()
        ws = wb.active
        ws.title = "Agendas"
        ws.append(["TÃ­tulo", "Data", "InÃ­cio", "Fim", "Status", "Equipe", "ResponsÃ¡vel", "Local"])
        for agenda in qs:
            ws.append([
                agenda.title,
                agenda.date.isoformat(),
                agenda.start_time.isoformat(timespec="minutes") if agenda.start_time else "",
                agenda.end_time.isoformat(timespec="minutes") if agenda.end_time else "",
                agenda.get_status_display(),
                agenda.sector.name if agenda.sector else "-",
                agenda.responsible.full_name if agenda.responsible else "-",
                agenda.location or agenda.institution_location or "-",
            ])
        response_file = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response_file["Content-Disposition"] = 'attachment; filename="relatorio-agendas.xlsx"'
        wb.save(response_file)
        return response_file

    @decorators.action(detail=False, methods=["get"])
    def export_pdf(self, request):
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from io import BytesIO

        # 1. Fetch dashboard-specific queryset
        request_source_filter = (
            Q(origin=Agenda.Origin.PUBLIC_FORM)
            | Q(source_id__startswith="internal-request:")
            | Q(source_id__startswith="appsheet:")
            | Q(sector__name__in=["SolicitaÃ§Ãµes externas", "SolicitaÃ§Ãµes internas"])
            | Q(created_by__email="solicitacao.publica@agenda.local")
            | Q(responsible__email="solicitacao.publica@agenda.local")
        )
        qs = self._queryset(request, check_access=False, unscoped=True)
        log_audit(
            request,
            AuditLog.Action.REPORT_EXPORT,
            "Relatorios",
            "Relatorio operacional exportado em PDF.",
            {"format": "pdf"},
        )
        today = timezone.localdate()
        now = timezone.localtime().time()
        aggs = qs.aggregate(
            total=Count('id'),
            approved=Count('id', filter=Q(status=Agenda.Status.APPROVED)),
            pending=Count('id', filter=Q(status=Agenda.Status.PENDING)),
            completed=Count('id', filter=Q(status=Agenda.Status.COMPLETED)),
            cancelled=Count('id', filter=Q(status=Agenda.Status.CANCELLED)),
            today_count=Count('id', filter=Q(date=today)),
            upcoming_count=Count('id', filter=Q(date__gte=today)),
            in_progress=Count('id', filter=Q(date=today, start_time__lte=now, end_time__gte=now) & ~Q(status__in=[Agenda.Status.CANCELLED, Agenda.Status.COMPLETED]))
        )
        total = aggs['total']
        approved = aggs['approved']
        pending = aggs['pending']
        completed = aggs['completed']
        cancelled = aggs['cancelled']
        today_count = aggs['today_count']
        upcoming_count = aggs['upcoming_count']
        in_progress = aggs['in_progress']

        today_agents = set()
        for agenda in qs.filter(date=today).prefetch_related("agents_ref"):
            today_agents.update(agenda.agents_ref.values_list("id", flat=True))
            if not agenda.agents_ref.exists() and agenda.agents:
                today_agents.update(
                    name.strip().casefold()
                    for name in agenda.agents.replace(",", " - ").split(" - ")
                    if name.strip()
                )
        today_agents_count = len(today_agents)

        status_total = max(total, 1)
        completion_rate = round((approved / status_total) * 100, 1)
        cancellation_rate = round((cancelled / status_total) * 100, 1)
        avg_per_user = round(total / max(qs.values("responsible_id").distinct().count(), 1), 1)

        # 3. Compute Top categories lists
        by_municipality_counter = Counter(
            normalize_name(row.get("municipality_ref__name") or row.get("city") or "Sem municÃ­pio")
            for row in qs.values("municipality_ref__name", "city")
        )
        by_municipality = by_municipality_counter.most_common(8)

        by_neighborhood_counter = Counter(
            normalize_name(row.get("neighborhood_ref__name") or row.get("neighborhood") or "Sem bairro")
            for row in qs.values("neighborhood_ref__name", "neighborhood")
        )
        by_neighborhood = by_neighborhood_counter.most_common(8)

        by_team_counter = Counter(
            (
                row.get("team_ref__name")
                or row.get("team_name")
                or "Sem equipe"
            ).strip()
            for row in qs.filter(status__in=[Agenda.Status.APPROVED, Agenda.Status.COMPLETED])
            .values("team_ref__name", "team_name")
        )
        by_team_actions = [
            {"team_ref__name": label, "team_name": "", "total": value}
            for label, value in by_team_counter.most_common(8)
        ]

        # 4. Set up ReportLab document styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("ReportTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=4, textColor=colors.HexColor("#002766"), fontName="Helvetica-Bold")
        subtitle_style = ParagraphStyle("ReportSubtitle", parent=styles["Normal"], fontSize=9, spaceAfter=2, textColor=colors.HexColor("#555555"))
        section_title_style = ParagraphStyle("SectionTitle", parent=styles["Heading2"], fontSize=11, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#002766"), fontName="Helvetica-Bold")
        cell_style = ParagraphStyle("CellStyle", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#1a1a1a"))
        cell_bold = ParagraphStyle("CellBold", parent=cell_style, fontName="Helvetica-Bold")
        cell_center = ParagraphStyle("CellCenter", parent=cell_style, alignment=TA_CENTER)

        HEADER_BG = colors.HexColor("#002766")
        HEADER_FG = colors.white
        ZEBRA_EVEN = colors.HexColor("#f4f6fb")
        ZEBRA_ODD = colors.white
        BORDER_COLOR = colors.HexColor("#dddddd")

        header_cell = ParagraphStyle("HeaderCell", parent=cell_bold, textColor=colors.white, fontSize=8, alignment=TA_CENTER)
        header_left = ParagraphStyle("HeaderLeft", parent=header_cell, alignment=TA_LEFT)
        footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#999999"), alignment=TA_CENTER)

        def make_table(headers, rows, widths):
            data = [[Paragraph(h, header_left if i == 0 else header_cell) for i, h in enumerate(headers)]]
            for r in rows:
                data.append([
                    Paragraph(str(r[0]), cell_style),
                    Paragraph(str(r[1]), cell_center)
                ])
            t = Table(data, colWidths=widths, repeatRows=1)
            t_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("TOPPADDING", (0, 0), (-1, 0), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
            for idx in range(1, len(data)):
                bg = ZEBRA_EVEN if idx % 2 == 0 else ZEBRA_ODD
                t_style.add("BACKGROUND", (0, idx), (-1, idx), bg)
            t.setStyle(t_style)
            return t

        date_from = request.query_params.get("date_from") or "InÃ­cio"
        date_to = request.query_params.get("date_to") or today.strftime("%d/%m/%Y")

        elements = []

        # --- Header ---
        elements.append(Paragraph("OperaÃ§Ã£o Lei Seca", title_style))
        elements.append(Paragraph("Relatório Consolidado de Atividades - Dashboard", ParagraphStyle("Sub", parent=subtitle_style, fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#333333"))))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"PerÃ­odo analisado: {date_from} a {date_to}", subtitle_style))
        elements.append(Paragraph(f"Emitido em: {today.strftime('%d/%m/%Y')} &nbsp;|&nbsp; Total de agendas no perÃ­odo: {total}", subtitle_style))
        elements.append(Spacer(1, 8))

        # --- Section 1: Resumo Operacional ---
        elements.append(Paragraph("1. Resumo Operacional", section_title_style))
        operacionais_rows = [
            ("Agendas Aprovadas", approved),
            ("Agendas Pendentes", pending),
            ("Agendas Canceladas", cancelled),
            ("Agendas de Hoje", today_count),
            ("Agentes Escalados Hoje", today_agents_count),
            ("Agendas em Andamento", in_progress),
            ("PrÃ³ximas Agendas", upcoming_count),
        ]
        elements.append(make_table(["MÃ©trica Operacional", "Quantidade"], operacionais_rows, [350, 150]))
        elements.append(Spacer(1, 6))

        # --- Section 2: Indicadores AvanÃ§ados ---
        elements.append(Paragraph("2. Indicadores AvanÃ§ados", section_title_style))
        avancados_rows = [
            ("Taxa de aprovaÃ§Ã£o", f"{completion_rate}%"),
            ("Taxa de cancelamento", f"{cancellation_rate}%"),
            ("Tempo mÃ©dio de aprovaÃ§Ã£o", "24h"),
            ("MÃ©dia por usuÃ¡rio", avg_per_user),
        ]
        elements.append(make_table(["Indicador AvanÃ§ado", "Valor"], avancados_rows, [350, 150]))
        elements.append(Spacer(1, 6))

        # --- Section 3: Agendas por MunicÃ­pio ---
        if by_municipality:
            elements.append(Paragraph("3. Agendas por MunicÃ­pio (Top 8)", section_title_style))
            elements.append(make_table(["MunicÃ­pio", "Agendas"], by_municipality, [350, 150]))
            elements.append(Spacer(1, 6))

        # --- Section 4: Agendas por Bairro ---
        if by_neighborhood:
            elements.append(Paragraph("4. Agendas por Bairro (Top 8)", section_title_style))
            elements.append(make_table(["Bairro", "Agendas"], by_neighborhood, [350, 150]))
            elements.append(Spacer(1, 6))

        # --- Section 5: Agendas por Equipe ---
        if by_team_actions:
            elements.append(Paragraph("5. Agendas por Equipe (Top 8)", section_title_style))
            team_rows = [(t["team_ref__name"] or t["team_name"] or "Sem equipe", t["total"]) for t in by_team_actions]
            elements.append(make_table(["Equipe", "Agendas ConcluÃ­das"], team_rows, [350, 150]))
            elements.append(Spacer(1, 6))

        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"OperaÃ§Ã£o Lei Seca ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Relatório gerado automaticamente em {today.strftime('%d/%m/%Y')}", footer_style))

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=25,
            bottomMargin=25,
            title="Relatório Operacional de Agendas - Dashboard",
            author="Agenda OLS",
        )
        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()

        response_file = HttpResponse(pdf_content, content_type="application/pdf")
        response_file["Content-Disposition"] = 'attachment; filename="relatorio-operacional-dashboard.pdf"'
        return response_file


class SatisfactionSurveyViewSet(viewsets.ModelViewSet):
    queryset = SatisfactionSurvey.objects.all()
    serializer_class = SatisfactionSurveySerializer
    permission_classes = [IsAuthenticated, VisitorReadOnly]

    def get_queryset(self):
        user = self.request.user
        if self.can_moderate(user):
            return SatisfactionSurvey.objects.all()
        return SatisfactionSurvey.objects.filter(moderation_status=SatisfactionSurvey.ModerationStatus.APPROVED)

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ["PUT", "PATCH", "DELETE"]:
            user = request.user
            if not self.can_moderate(user):
                self.permission_denied(request, message="Apenas gestores podem moderar avaliacoes.")

    def can_moderate(self, user):
        return bool(user and user.is_authenticated and (user.is_superuser or user.role in ["ADMIN", "MANAGER"]))

    def filtered_moderation_queryset(self, request):
        qs = SatisfactionSurvey.objects.filter(answered_at__isnull=False).exclude(suggestion="").select_related(
            "agenda",
            "agenda__municipality_ref",
            "moderated_by",
        ).prefetch_related("moderation_history")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        team = request.query_params.get("team")
        municipality = request.query_params.get("municipality")
        institution = request.query_params.get("institution")
        status_param = request.query_params.get("status")
        q = request.query_params.get("q")
        if date_from:
            qs = qs.filter(answered_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(answered_at__date__lte=date_to)
        if team:
            qs = qs.filter(team__iexact=team)
        if municipality:
            qs = qs.filter(agenda__municipality_ref_id=municipality)
        if institution:
            qs = qs.filter(agenda__location__icontains=institution)
        if status_param:
            qs = qs.filter(moderation_status=status_param)
        else:
            qs = qs.filter(moderation_status=SatisfactionSurvey.ModerationStatus.PENDING)
        if q:
            qs = qs.filter(
                Q(suggestion__icontains=q)
                | Q(moderated_comment__icontains=q)
                | Q(team__icontains=q)
                | Q(agenda__location__icontains=q)
                | Q(agenda__title__icontains=q)
            )
        return qs.order_by("-answered_at", "-id")

    @decorators.action(detail=False, methods=["get"])
    def moderation(self, request):
        if not self.can_moderate(request.user):
            raise PermissionDenied("Apenas gestores podem visualizar comentarios pendentes.")
        serializer = self.get_serializer(self.filtered_moderation_queryset(request), many=True)
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post"])
    def moderate(self, request, pk=None):
        if not self.can_moderate(request.user):
            raise PermissionDenied("Apenas gestores podem moderar avaliacoes.")
        survey = self.get_object()
        new_status = request.data.get("status")
        valid_statuses = {choice[0] for choice in SatisfactionSurvey.ModerationStatus.choices}
        if new_status not in valid_statuses or new_status == SatisfactionSurvey.ModerationStatus.PENDING:
            return response.Response({"detail": "Informe um status de moderacao valido."}, status=400)
        previous_status = survey.moderation_status
        moderated_comment = request.data.get("moderated_comment", survey.moderated_comment)
        if moderated_comment is None:
            moderated_comment = ""
        survey.moderation_status = new_status
        survey.is_approved = new_status == SatisfactionSurvey.ModerationStatus.APPROVED
        survey.moderated_comment = str(moderated_comment).strip()
        survey.moderated_at = timezone.now()
        survey.moderated_by = request.user
        survey.save(update_fields=["moderation_status", "is_approved", "moderated_comment", "moderated_at", "moderated_by", "updated_at"])
        SatisfactionSurveyModerationHistory.objects.create(
            survey=survey,
            previous_status=previous_status,
            new_status=new_status,
            comment_snapshot=survey.moderated_comment or survey.suggestion,
            decided_by=request.user,
        )
        return response.Response(self.get_serializer(survey).data)

    @decorators.action(detail=False, methods=["get"])
    def analytics(self, request):
        qs = SatisfactionSurvey.objects.filter(answered_at__isnull=False)

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        state_param = request.query_params.get("state")
        municipality = request.query_params.get("municipality")
        region = request.query_params.get("region")
        status_param = request.query_params.get("status")
        team = request.query_params.get("team") or request.query_params.get("speaker")

        if date_from:
            qs = qs.filter(agenda__date__gte=date_from)
        if date_to:
            qs = qs.filter(agenda__date__lte=date_to)
        state_options_qs = qs
        if state_param:
            qs = qs.filter(agenda__state__iexact=state_param)
        if municipality:
            qs = qs.filter(agenda__municipality_ref_id=municipality)
        if region:
            qs = qs.filter(agenda__municipality_ref__region_id=region)
        if status_param:
            qs = qs.filter(agenda__status=status_param)
        if team:
            qs = qs.filter(team__iexact=team)

        CRITERIA_FIELDS = [
            ("audiovisual_resources", "Recursos \u00e1udio-visuais"),
            ("speaker_knowledge", "Palestrante"),
            ("wheelchair_testimony", "Depoimento dos cadeirantes"),
            ("workshops", "Din\u00e2micas"),
            ("support_material", "Material de apoio"),
            ("punctuality", "Pontualidade"),
            ("team_enthusiasm", "Entusiasmo"),
        ]

        ALL_CRITERIA = CRITERIA_FIELDS + [("overall_rating", "Nota geral")]

        states = [
            value for value in state_options_qs.exclude(agenda__state="")
            .values_list("agenda__state", flat=True)
            .distinct()
            .order_by("agenda__state")
        ]
        regions = [
            {"id": item["agenda__municipality_ref__region_id"], "name": item["agenda__municipality_ref__region__name"]}
            for item in state_options_qs.exclude(agenda__municipality_ref__region_id__isnull=True)
            .values("agenda__municipality_ref__region_id", "agenda__municipality_ref__region__name")
            .distinct()
            .order_by("agenda__municipality_ref__region__name")
        ]
        municipalities = [
            {"id": item["agenda__municipality_ref_id"], "name": item["agenda__municipality_ref__name"]}
            for item in qs.exclude(agenda__municipality_ref_id__isnull=True)
            .values("agenda__municipality_ref_id", "agenda__municipality_ref__name")
            .distinct()
            .order_by("agenda__municipality_ref__name")
        ]
        teams = [
            value for value in state_options_qs.exclude(team="")
            .values_list("team", flat=True)
            .distinct()
            .order_by("team")
        ]

        total_surveys = qs.count()

        if total_surveys == 0:
            empty_distribution = {label: {str(score): 0 for score in range(1, 11)} for _, label in ALL_CRITERIA}
            return response.Response({
                "cards": {
                    "total_surveys": 0,
                    "satisfaction_index": 0,
                    "speaker_avg": 0,
                    "resources_avg": 0,
                    "punctuality_avg": 0,
                    "enthusiasm_avg": 0,
                    "workshops_avg": 0,
                    "support_material_avg": 0,
                    "wheelchair_avg": 0,
                    "best_criteria": None,
                    "worst_criteria": None,
                    "most_improved": None,
                },
                "radar": [],
                "ranking": [],
                "distribution": empty_distribution,
                "monthly_evolution": [],
                "heatmap": [],
                "comments": [],
                "states": states,
                "regions": regions,
                "municipalities": municipalities,
                "teams": teams,
                "satisfaction_panel": {
                    "overall_rating": 0,
                    "total_responses": 0,
                    "team_ratings": [],
                    "messages": [],
                },
                "intelligence": {
                    "excellence_index": 0,
                    "best_criteria": None,
                    "most_improved": None,
                    "most_declined": None,
                    "trend": None,
                    "trend_delta": 0,
                },
                "executive_summary": "",
            })

        # -- Aggregates ----------------------------------------------
        agg_kwargs = {}
        for field, _ in ALL_CRITERIA:
            agg_kwargs[f"{field}_avg"] = Avg(field)
        aggregates = qs.aggregate(
            **agg_kwargs,
            satisfaction_count=Sum(
                Case(When(overall_rating__gte=4, then=1), default=0, output_field=IntegerField())
            ),
        )

        overall_avg = round(aggregates["overall_rating_avg"] or 0, 2)
        satisfaction_index = round((aggregates["satisfaction_count"] or 0) / total_surveys * 100, 1)
        speaker_avg = round(aggregates["speaker_knowledge_avg"] or 0, 2)
        resources_avg = round(aggregates["audiovisual_resources_avg"] or 0, 2)
        punctuality_avg = round(aggregates["punctuality_avg"] or 0, 2)
        enthusiasm_avg = round(aggregates["team_enthusiasm_avg"] or 0, 2)
        workshops_avg = round(aggregates["workshops_avg"] or 0, 2)
        support_material_avg = round(aggregates["support_material_avg"] or 0, 2)
        wheelchair_avg = round(aggregates["wheelchair_testimony_avg"] or 0, 2)

        criteria_averages = {}
        for field, label in CRITERIA_FIELDS:
            criteria_averages[label] = round(aggregates[f"{field}_avg"] or 0, 2)

        best_criteria = max(criteria_averages, key=criteria_averages.get)
        worst_criteria = min(criteria_averages, key=criteria_averages.get)

        cards = {
            "total_surveys": total_surveys,
            "satisfaction_index": satisfaction_index,
            "speaker_avg": speaker_avg,
            "resources_avg": resources_avg,
            "punctuality_avg": punctuality_avg,
            "enthusiasm_avg": enthusiasm_avg,
            "workshops_avg": workshops_avg,
            "support_material_avg": support_material_avg,
            "wheelchair_avg": wheelchair_avg,
            "best_criteria": best_criteria,
            "worst_criteria": worst_criteria,
            "most_improved": best_criteria,
        }

        panel_qs = qs.filter(Q(moderation_status=SatisfactionSurvey.ModerationStatus.APPROVED) | Q(suggestion=""))
        panel_overall_avg = panel_qs.aggregate(avg=Avg("overall_rating"))["avg"] or 0.0
        panel_team_ratings = list(
            panel_qs.values("team")
            .annotate(avg=Avg("overall_rating"), count=Count("id"))
            .exclude(team="")
            .order_by("-avg", "-count")[:10]
        )
        panel_messages_qs = qs.filter(suggestion__gt="")
        if not self.can_moderate(request.user):
            panel_messages_qs = panel_messages_qs.filter(moderation_status=SatisfactionSurvey.ModerationStatus.APPROVED)
        panel_messages = list(
            panel_messages_qs.annotate(
                moderation_rank=Case(
                    When(moderation_status=SatisfactionSurvey.ModerationStatus.PENDING, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("moderation_rank", "-answered_at")
            .values("id", "team", "suggestion", "moderated_comment", "answered_at", "overall_rating", "is_approved", "moderation_status", "agenda__id", "agenda__institution_location")[:15]
        )
        satisfaction_panel = {
            "overall_rating": round(overall_avg, 1) if overall_avg is not None else 0.0,
            "total_responses": total_surveys,
            "team_ratings": [
                {"team": item["team"], "avg": round(item["avg"], 1), "count": item["count"]}
                for item in panel_team_ratings if item["avg"] is not None
            ],
            "messages": panel_messages,
        }

        # -- Radar ----------------------------------------------------
        radar = []
        for field, label in ALL_CRITERIA:
            radar.append({
                "criteria": label,
                "value": round(aggregates[f"{field}_avg"] or 0, 2),
            })

        # -- Ranking (Teams) ------------------------------------------
        teams_avg = list(panel_qs.values("team").annotate(value=Avg("overall_rating")).order_by("-value"))
        ranking = []
        for i, item in enumerate(teams_avg, 1):
            if item["team"]:
                ranking.append({
                    "criteria": item["team"], # Keep the key 'criteria' so frontend doesn't break, or change to 'team'
                    "value": round(item["value"] or 0, 2),
                    "position": len(ranking) + 1
                })

        # -- Distribution ---------------------------------------------
        distribution = {}
        dist_agg = {}
        for field, label in ALL_CRITERIA:
            for score in range(1, 11):
                dist_agg[f"{field}_{score}"] = Sum(
                    Case(When(**{field: score}, then=1), default=0, output_field=IntegerField())
                )
        dist_result = qs.aggregate(**dist_agg)
        for field, label in ALL_CRITERIA:
            distribution[label] = {
                str(score): dist_result.get(f"{field}_{score}", 0) or 0
                for score in range(1, 11)
            }

        # -- Monthly Evolution ----------------------------------------
        monthly_qs = (
            qs.annotate(month=TruncMonth("agenda__date"))
            .values("month")
            .annotate(avg_rating=Avg("overall_rating"))
            .order_by("month")
        )
        monthly_evolution = []
        for entry in monthly_qs:
            m = entry["month"]
            if m:
                month_labels = [
                    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
                ]
                monthly_evolution.append({
                    "month": m.strftime("%Y-%m"),
                    "label": f"{month_labels[m.month - 1]}/{m.strftime('%y')}",
                    "value": round(entry["avg_rating"] or 0, 2),
                })

        # -- Heatmap --------------------------------------------------
        heatmap_agg = {}
        for field, _ in CRITERIA_FIELDS:
            heatmap_agg[f"{field}_avg"] = Avg(field)
        heatmap_qs = (
            qs.annotate(month=TruncMonth("agenda__date"))
            .values("month")
            .annotate(**heatmap_agg)
            .order_by("month")
        )
        heatmap = []
        for entry in heatmap_qs:
            m = entry["month"]
            if m:
                for field, label in CRITERIA_FIELDS:
                    heatmap.append({
                        "criteria": label,
                        "month": m.strftime("%Y-%m"),
                        "value": round(entry[f"{field}_avg"] or 0, 2),
                    })

        # -- Comments -------------------------------------------------
        comments_qs = (
            qs.filter(suggestion__gt="", moderation_status=SatisfactionSurvey.ModerationStatus.APPROVED)
            .select_related("agenda", "agenda__municipality_ref")
            .order_by("-answered_at")[:20]
        )
        comments = []
        for s in comments_qs:
            agenda = s.agenda
            municipality_name = agenda.city or ""
            if agenda.municipality_ref_id:
                try:
                    municipality = agenda.municipality_ref
                except Municipality.DoesNotExist:
                    municipality = None
                if municipality:
                    municipality_name = municipality.name
            comments.append({
                "school": agenda.location or "",
                "municipality": municipality_name,
                "date": agenda.date.strftime("%d/%m/%Y") if agenda.date else "",
                "overall_rating": s.overall_rating,
                "comment": s.moderated_comment or s.suggestion,
            })

        # -- Intelligence ---------------------------------------------
        most_improved = None
        most_declined = None
        trend = None
        trend_delta = 0

        if date_from and date_to:
            from datetime import datetime as _dt
            try:
                d_from = _dt.strptime(date_from, "%Y-%m-%d").date()
                d_to = _dt.strptime(date_to, "%Y-%m-%d").date()
                period_days = (d_to - d_from).days
                prev_to = d_from - timedelta(days=1)
                prev_from = prev_to - timedelta(days=period_days)

                prev_qs = SatisfactionSurvey.objects.filter(
                    answered_at__isnull=False,
                    agenda__date__gte=prev_from,
                    agenda__date__lte=prev_to,
                )
                if state_param:
                    prev_qs = prev_qs.filter(agenda__state__iexact=state_param)
                if municipality:
                    prev_qs = prev_qs.filter(agenda__municipality_ref_id=municipality)
                if status_param:
                    prev_qs = prev_qs.filter(agenda__status=status_param)
                if team:
                    prev_qs = prev_qs.filter(team__iexact=team)

                prev_agg_kwargs = {}
                for field, _ in CRITERIA_FIELDS:
                    prev_agg_kwargs[f"{field}_avg"] = Avg(field)
                prev_agg_kwargs["overall_rating_avg"] = Avg("overall_rating")
                prev_aggregates = prev_qs.aggregate(**prev_agg_kwargs)

                prev_overall = prev_aggregates.get("overall_rating_avg")
                if prev_overall is not None:
                    trend = "up" if overall_avg >= prev_overall else "down"
                    trend_delta = round(abs(overall_avg - prev_overall), 2)

                    deltas = {}
                    for field, label in CRITERIA_FIELDS:
                        cur = aggregates.get(f"{field}_avg") or 0
                        prev = prev_aggregates.get(f"{field}_avg") or 0
                        deltas[label] = cur - prev

                    if deltas:
                        best_delta_label = max(deltas, key=deltas.get)
                        worst_delta_label = min(deltas, key=deltas.get)
                        if deltas[best_delta_label] > 0:
                            most_improved = best_delta_label
                        if deltas[worst_delta_label] < 0:
                            most_declined = worst_delta_label
            except (ValueError, TypeError):
                pass

        intelligence = {
            "excellence_index": satisfaction_index,
            "best_criteria": best_criteria,
            "most_improved": most_improved,
            "most_declined": most_declined,
            "trend": trend,
            "trend_delta": trend_delta,
        }

        # -- Executive Summary ----------------------------------------
        sorted_criteria = sorted(criteria_averages.items(), key=lambda x: x[1], reverse=True)
        best1 = sorted_criteria[0][0] if len(sorted_criteria) > 0 else ""
        best2 = sorted_criteria[1][0] if len(sorted_criteria) > 1 else ""
        executive_summary = (
            f"Foram recebidas {total_surveys} avalia\u00e7\u00f5es no per\u00edodo selecionado. "
            f"A nota m\u00e9dia geral foi {overall_avg:.2f}. "
            f"O \u00edndice de excel\u00eancia atingiu {satisfaction_index:.1f}%. "
            f"Os crit\u00e9rios mais bem avaliados foram {best1} e {best2}. "
            f"O crit\u00e9rio com menor m\u00e9dia foi {worst_criteria}, indicando oportunidade de melhoria."
        )

        return response.Response({
            "cards": cards,
            "radar": radar,
            "ranking": ranking,
            "distribution": distribution,
            "monthly_evolution": monthly_evolution,
            "heatmap": heatmap,
            "regions": regions,
            "municipalities": municipalities,
            "teams": teams,
            "comments": comments,
            "satisfaction_panel": satisfaction_panel,
            "intelligence": intelligence,
            "executive_summary": executive_summary,
        })


class GoogleFormsWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Recebe o payload via POST do Google Apps Script (onFormSubmit)
        O payload esperado Ã© {"namedValues": {"Carimbo de data/hora": ["valor"], ...}}
        """
        import logging as _logging
        _wh_logger = _logging.getLogger(__name__)

        webhook_secret = getattr(settings, "WEBHOOK_SECRET", "") or ""
        incoming_secret = request.headers.get("X-Webhook-Secret", "")
        if not webhook_secret or incoming_secret != webhook_secret:
            return response.Response({"detail": "Nao autorizado."}, status=403)

        named_values = request.data.get("namedValues")

        # Fallback caso o script envie diretamente o objeto
        if not named_values and request.data:
            named_values = request.data

        if not named_values or not isinstance(named_values, dict):
            return response.Response({"detail": "Payload invÃ¡lido. Esperado 'namedValues'."}, status=400)

        # Converte dicionÃ¡rio de listas para dicionÃ¡rio simples
        row = {}
        for k, v in named_values.items():
            if isinstance(v, list) and len(v) > 0:
                row[k] = v[0]
            else:
                row[k] = v

        from apps.accounts.models import User
        from apps.schedules.models import Sector
        from apps.schedules.management.commands.import_google_sheet_requests import Command as ImportGoogleSheetCommand

        admin = User.objects.filter(role__in=["ADMIN", "MANAGER"]).first()
        if not admin:
            return response.Response({"detail": "Nenhum administrador encontrado."}, status=500)

        sector, _ = Sector.objects.get_or_create(
            name="SolicitaÃ§Ãµes externas",
            defaults={"description": "SolicitaÃ§Ãµes importadas do Google Forms/Sheets."},
        )

        cmd = ImportGoogleSheetCommand()
        try:
            # O Ã­ndice 0 Ã© usado apenas para log na descriÃ§Ã£o
            result = cmd.import_row(row, index=0, admin=admin, sector=sector, dry_run=False)
            return response.Response({"status": "success", "result": result})
        except Exception as e:
            _wh_logger.exception("Erro ao processar webhook do Google Forms")
            return response.Response({"detail": "Erro interno ao processar a solicitacao."}, status=500)




