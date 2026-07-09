import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.db import transaction
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
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.audit import log_audit
from apps.accounts.models import AuditLog, User

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
    ShiftSchedule,
    ShiftSwapRequest,
    Support,
    Team,
    Vehicle,
)
from .permissions import AdminOrReadSectorPermission, AgendaPermission, ShiftSchedulePermission, agent_agenda_filter
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
    field = f"{prefix}chief_name"
    chief_ref_field = f"{prefix}chief_ref__name"
    chief_ref_cpf_field = f"{prefix}chief_ref__cpf"
    chief_ref_team_field = f"{prefix}chief_ref__team__name"
    responsible_field = f"{prefix}responsible"
    query = (
        Q(**{f"{field}__iexact": user.full_name})
        | Q(**{f"{chief_ref_field}__iexact": user.full_name})
        | Q(**{responsible_field: user})
    )
    cpf = "".join(char for char in str(user.cpf or "") if char.isdigit())
    if cpf:
        query |= Q(**{chief_ref_cpf_field: cpf})
    if user.sector_id and user.sector and user.sector.name:
        query |= Q(**{f"{chief_ref_team_field}__iexact": user.sector.name})
    return query


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
        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Chief.objects.all()
        return queryset.select_related("team").order_by("team__name", "name")

    def perform_destroy(self, instance):
        cpf = "".join(char for char in str(instance.cpf or "") if char.isdigit())
        linked_users = User.objects.filter(role=User.Role.SUPERVISOR)
        if cpf:
            linked_users = linked_users.filter(Q(cpf=cpf) | Q(full_name__iexact=instance.name))
        else:
            linked_users = linked_users.filter(full_name__iexact=instance.name)
        linked_users.update(is_active=False)
        super().perform_destroy(instance)


class AgentViewSet(LookupViewSet):
    serializer_class = AgentSerializer

    def get_queryset(self):
        if self.action in ["retrieve", "update", "partial_update", "destroy"] and self.request.user.is_admin_role:
            return Agent.objects.all().select_related("team").order_by("team__name", "name")
        queryset = Agent.objects.filter(is_active=True).exclude(role__icontains="APOIO")
        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Agent.objects.all()
        return queryset.select_related("team").order_by("team__name", "name")


class SupportViewSet(LookupViewSet):
    serializer_class = SupportSerializer

    def get_queryset(self):
        if self.action in ["retrieve", "update", "partial_update", "destroy"] and self.request.user.is_admin_role:
            return Support.objects.all().select_related("team").order_by("team__name", "name")
        queryset = Support.objects.filter(is_active=True)
        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Support.objects.all()
        return queryset.select_related("team").order_by("team__name", "name")


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
        if not user.is_admin_role and user.sector_id:
            queryset = queryset.filter(team_id=user.sector_id)
            
        return queryset.order_by("date", "team__name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

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
            if not reason:
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

    @decorators.action(detail=True, methods=["post"], url_path="report-attendance")
    def report_attendance(self, request, pk=None):
        from django.utils import timezone
        schedule = self.get_object()
        schedule.attendance_reported = True
        schedule.attendance_reported_at = timezone.now()
        schedule.attendance_approved = False
        schedule.attendance_approved_at = None
        schedule.save(update_fields=["attendance_reported", "attendance_reported_at", "attendance_approved", "attendance_approved_at"])
        return response.Response({"detail": "Frequência reportada com sucesso."})

    @decorators.action(detail=True, methods=["post"], url_path="approve-attendance")
    def approve_attendance(self, request, pk=None):
        from django.utils import timezone
        schedule = self.get_object()
        schedule.attendance_approved = True
        schedule.attendance_approved_at = timezone.now()
        schedule.save(update_fields=["attendance_approved", "attendance_approved_at"])
        return response.Response({"detail": "Frequência aprovada."})


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
    serializer_class = AgendaSerializer
    permission_classes = [IsAuthenticated, AgendaPermission]

    def get_scoped_queryset(self):
        user = self.request.user
        queryset = Agenda.objects.select_related("responsible", "sector", "created_by").prefetch_related(
            "history",
            "satisfaction_surveys",
        ).annotate(linked_requests_count_annotated=Count('linked_requests', distinct=True))
        if user.is_admin_role:
            return queryset
        elif user.role == User.Role.VISITOR:
            return queryset
        elif user.role == User.Role.SUPERVISOR:
            if self.request.query_params.get("reportable") == "true":
                return queryset.filter(chief_agenda_filter(user))
            return queryset.filter(
                Q(sector_id=user.sector_id)
                | chief_agenda_filter(user)
            )
        return queryset.filter(agent_agenda_filter(user))

    def get_queryset(self):
        scoped = self.get_scoped_queryset()
        params = self.request.query_params

        # Restrição para que relatórios só fiquem pendentes após as 18h do dia da ação
        if params.get("reportable") == "true":
            from django.utils import timezone
            now = timezone.localtime(timezone.now())
            if now.hour >= 18:
                scoped = scoped.filter(date__lte=now.date()).exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED])
            else:
                scoped = scoped.filter(date__lt=now.date()).exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED])

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
            | Q(sector__name__in=["Solicitações externas", "Solicitações internas"])
            | Q(created_by__email="solicitacao.publica@agenda.local")
            | Q(responsible__email="solicitacao.publica@agenda.local")
        )
        if params.get("source") == "public":
            scoped = scoped.filter(
                Q(origin=Agenda.Origin.PUBLIC_FORM)
                | Q(created_by__email="solicitacao.publica@agenda.local")
                | Q(responsible__email="solicitacao.publica@agenda.local")
            )
        if params.get("source") == "requests":
            scoped = scoped.filter(request_source_filter)
        if params.get("sector"):
            scoped = scoped.filter(sector_id=params["sector"])
        if params.get("user"):
            scoped = scoped.filter(created_by_id=params["user"])
        if params.get("responsible"):
            scoped = scoped.filter(responsible_id=params["responsible"])
        if params.get("vehicle"):
            scoped = scoped.filter(vehicle_ref_id=params["vehicle"])
        if params.get("team"):
            scoped = scoped.filter(team_ref_id=params["team"])
        if params.get("municipality"):
            scoped = scoped.filter(municipality_ref_id=params["municipality"])
        if params.get("region"):
            scoped = scoped.filter(municipality_ref__region_id=params["region"])
        if params.get("action_type"):
            scoped = scoped.filter(action_type_ref_id=params["action_type"])
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
        if params.get("pending_report") == "true":
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
        if previous_status != agenda.status:
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
            days or "nenhuma data disponível nos próximos dias",
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
            | Q(sector__name__in=["Solicitações externas", "Solicitações internas"])
            | Q(created_by__email="solicitacao.publica@agenda.local")
            | Q(responsible__email="solicitacao.publica@agenda.local")
        )
        def unscoped_dashboard_queryset():
            return Agenda.objects.select_related("responsible", "sector", "created_by").prefetch_related(
                "history",
                "satisfaction_surveys",
            )

        def apply_dashboard_filters(scoped):
            params = request.query_params
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
            if params.get("sector"):
                scoped = scoped.filter(sector_id=params["sector"])
            if params.get("user"):
                scoped = scoped.filter(created_by_id=params["user"])
            if params.get("responsible"):
                scoped = scoped.filter(responsible_id=params["responsible"])
            if params.get("vehicle"):
                scoped = scoped.filter(vehicle_ref_id=params["vehicle"])
            if params.get("team"):
                scoped = scoped.filter(team_ref_id=params["team"])
            if params.get("municipality"):
                scoped = scoped.filter(municipality_ref_id=params["municipality"])
            if params.get("action_type"):
                scoped = scoped.filter(action_type_ref_id=params["action_type"])
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
                report__status=EducationReport.ReportStatus.SUBMITTED,
            ).distinct()
            totals = Counter()
            for equipment, distribution in action_scope.values_list(
                "equipment_materials_distributed",
                "distribution_materials_distributed",
            ):
                for name, quantity in parse_material_distribution(equipment):
                    totals[name] += quantity
                for name, quantity in parse_material_distribution(distribution):
                    totals[name] += quantity
            items = [{"label": label, "value": value} for label, value in totals.most_common(8)]
            return {"total": sum(totals.values()), "items": items}

        def action_team_queryset():
            scoped = dashboard_base_queryset().filter(
                status__in=[Agenda.Status.APPROVED, Agenda.Status.COMPLETED]
            )
            return scoped

        previous_start, previous_end, compare_mode = comparison_range()
        comparison_qs = dashboard_base_queryset()
        if previous_start and previous_end:
            comparison_qs = comparison_qs.filter(date__gte=previous_start, date__lte=previous_end)
        else:
            comparison_qs = None
        comparison_label = f"vs {format_period(previous_start, previous_end)}"

        aggs = qs.aggregate(
            today_count=Count('id', filter=Q(date=today)),
            pending=Count('id', filter=Q(status=Agenda.Status.PENDING)),
            approved=Count('id', filter=Q(status=Agenda.Status.APPROVED)),
            completed=Count('id', filter=Q(status=Agenda.Status.COMPLETED)),
            cancelled=Count('id', filter=Q(status=Agenda.Status.CANCELLED)),
            in_progress=Count('id', filter=Q(date=today, start_time__lte=now, end_time__gte=now) & ~Q(status__in=[Agenda.Status.CANCELLED, Agenda.Status.COMPLETED]))
        )
        today_count = aggs['today_count']
        yesterday_count = base_qs.filter(date=yesterday).count()
        pending = aggs['pending']
        approved = aggs['approved']
        completed = aggs['completed']
        cancelled = aggs['cancelled']
        in_progress = aggs['in_progress']
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

        by_team_actions = [
            {
                "label": row["team_ref__name"] or row["team_name"] or "Sem equipe",
                "value": row["total"],
            }
            for row in (
                action_team_queryset()
                .values("team_ref__name", "team_name")
                .annotate(total=Count("id"))
                .order_by("-total", "team_ref__name", "team_name")[:8]
            )
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
            (
                row.get("municipality_ref__name")
                or row.get("city")
                or "Sem município"
            ).strip()
            for row in qs.values("municipality_ref__name", "city")
        )
        by_municipality = [
            {"label": label, "value": value}
            for label, value in by_municipality_counter.most_common(8)
        ]
        by_neighborhood_counter = Counter(
            (
                row.get("neighborhood_ref__name")
                or row.get("neighborhood")
                or "Sem bairro"
            ).strip()
            for row in qs.values("neighborhood_ref__name", "neighborhood")
        )
        by_neighborhood = [
            {"label": label, "value": value}
            for label, value in by_neighborhood_counter.most_common(8)
        ]

        heatmap = defaultdict(int)
        for row in rows:
            day = row["date"].weekday()
            hour = row["start_time"].hour if row["start_time"] else 0
            slot = f"{max(6, min(20, hour)):02d}:00"
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

        status_total = max(total, 1)
        completion_rate = round((approved / status_total) * 100, 1)
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
        if now_dt.hour >= 18:
            reportable_agendas = base_qs.filter(date__lte=now_dt.date())
        else:
            reportable_agendas = base_qs.filter(date__lt=now_dt.date())
        pending_technical_reports_count = reportable_agendas.exclude(status__in=[Agenda.Status.COMPLETED, Agenda.Status.CANCELLED]).filter(technical_reports__isnull=True).count()
        if not (request.user.is_superuser or request.user.role in ["ADMIN", "MANAGER"]):
            messages_qs = messages_qs.filter(is_approved=True)

        recent_messages = list(

            messages_qs.order_by('-answered_at')
            .values('id', 'team', 'suggestion', 'moderated_comment', 'answered_at', 'overall_rating', 'is_approved', 'moderation_status')[:15]
        )

        distributed_materials = distributed_materials_summary(qs)
        chief_reports = EducationReport.objects.filter(
            agenda_id__in=qs.values("id"),
            status=EducationReport.ReportStatus.SUBMITTED,
        ).distinct()
        chief_actions = EducationAction.objects.filter(report_id__in=chief_reports.values("id"))
        chief_reported_agendas = qs.filter(id__in=chief_reports.values("agenda_id")).distinct()
        chief_totals = chief_actions.aggregate(
            approaches=Sum("approach"),
            registered_actions=Count("id"),
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
                    {"label": "Solicitação externa", "value": external_requests},
                    {"label": "Solicitação interna", "value": internal_requests},
                ],
                "by_neighborhood": by_neighborhood,
                "by_user": [{"label": row["responsible__full_name"] or "Sem responsável", "value": row["total"]} for row in by_user],
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = EventReport.objects.select_related("agenda", "agenda__sector", "created_by").order_by("-updated_at")
        if user.is_admin_role:
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
                raise PermissionDenied("Você só pode relatar agendas em que você está vinculado como Chefe.")
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
    statistics_fields = [
        ("approach", "Total de abordagens"),
        ("approached_lectures", "Abordados em palestras"),
        ("approached_actions", "Abordados em ações"),
        ("vetarolas", "Vetarolas"),
        ("used_adhesives", "Adesivos"),
        ("sequence_certificates", "Sequência certificados"),
        ("gibis", "Gibis"),
        ("distributed_certificates", "Certificados"),
        ("lectures", "Palestras realizadas"),
        ("schools", "Escolas"),
        ("universities", "Universidades"),
        ("companies", "Empresas"),
        ("educational_actions", "Ações educativas"),
        ("bars", "Bares"),
        ("tolls", "Pedágio"),
        ("sports", "Esportes"),
        ("beach", "Praia"),
        ("events", "Eventos"),
        ("shopping", "Shopping"),
        ("social_actions", "Ação social"),
        ("other_actions", "Outros"),
        ("publicity_materials", "Materiais de divulgação"),
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = EducationReport.objects.select_related("agenda", "created_by").prefetch_related(
            "actions",
            "actions__agenda",
        ).filter(agenda__date__gte="2026-07-08")
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
            report = serializer.save(created_by=self.request.user)
            SatisfactionSurvey.objects.filter(agenda=report.agenda, report__isnull=True).update(report=report)
            if report.status == EducationReport.ReportStatus.SUBMITTED:
                self._register_accessibility_block(report)
                transaction.on_commit(lambda: send_satisfaction_survey_email(report))
                transaction.on_commit(lambda: send_report_confirmation_email(report))

    def perform_update(self, serializer):
        with transaction.atomic():
            previous_status = serializer.instance.status
            agenda = serializer.validated_data.get("agenda", serializer.instance.agenda)
            self._validate_agenda_access(agenda)
            report = serializer.save()
            SatisfactionSurvey.objects.filter(agenda=report.agenda, report__isnull=True).update(report=report)
            if previous_status != EducationReport.ReportStatus.SUBMITTED and report.status == EducationReport.ReportStatus.SUBMITTED:
                self._register_accessibility_block(report)
                transaction.on_commit(lambda: send_satisfaction_survey_email(report))
                transaction.on_commit(lambda: send_report_confirmation_email(report))
            elif report.status == EducationReport.ReportStatus.SUBMITTED:
                self._register_accessibility_block(report)

    def _validate_agenda_access(self, agenda):
        user = self.request.user
        if user.is_admin_role:
            return
        if user.is_agent_role:
            raise PermissionDenied("Apenas Chefes, Gestores e Administradores podem preencher relatórios.")
        allowed = Agenda.objects.filter(pk=agenda.pk).filter(chief_agenda_filter(user)).exists()
        if not allowed:
            raise PermissionDenied("Você só pode preencher relatórios dos protocolos em que é Chefe responsável.")

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
                "reason": "Local não atendeu às condições de acessibilidade para cadeirantes no relatório técnico.",
                "is_active": True,
            },
        )

    @decorators.action(detail=False, methods=["get"])
    def statistics(self, request):
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

        reports = self.get_queryset()
        actions = EducationAction.objects.filter(report_id__in=reports.values("id"))
        params = request.query_params

        yearly_reports = self._statistics_yearly_queryset()
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
                "label": row["type_audience"] or "Sem público",
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
        # Usa o ano de referência (date_to) para determinar o ano atual e o anterior completo
        date_to_str = params.get("date_to")
        try:
            ref_date = date.fromisoformat(date_to_str) if date_to_str else timezone.localdate()
        except ValueError:
            ref_date = timezone.localdate()

        ref_year = ref_date.year
        prev_year = ref_year - 1

        # Período atual: todo o ano de referência até a data selecionada
        current_date_from = date(ref_year, 1, 1)
        current_date_to = ref_date

        # Período anterior: ano inteiro anterior (01/01 a 31/12)
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
            ("approached_actions", "Abordados em ações"),
            ("publicity_materials","Materiais de divulgação"),
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
        if not (request.user.is_admin_role or request.user.role == User.Role.SUPERVISOR):
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
                    {"key": "approached_actions", "label": "1.2 - ABORDADOS AÃƒâ€¡Ãƒâ€¢ES"},
                ],
            },
            {
                "key": "lectures", "label": "2 Ã¢â‚¬â€œ PALESTRAS", "section": True,
                "children": [
                    {"key": "schools", "label": "2.1 - ESCOLAS"},
                    {"key": "universities", "label": "2.2 - UNIVERSIDADES"},
                    {"key": "companies", "label": "2.3 - EMPRESAS"},
                ],
            },
            {
                "key": "educational_actions", "label": "3 - AÃƒâ€¡Ãƒâ€¢ES", "section": True,
                "children": [
                    {"key": "bars", "label": "3.1 - BAR/RESTAURANTE"},
                    {"key": "tolls", "label": "3.2 - PEDÀGIO"},
                    {"key": "sports", "label": "3.3 - PRAÃƒâ€¡A ESPORTIVA"},
                    {"key": "beach", "label": "3.4 - PRAIA"},
                    {"key": "events", "label": "3.5 - EVENTO"},
                    {"key": "shopping", "label": "3.6 - SHOPPING"},
                    {"key": "social_actions", "label": "3.7 - AÃƒâ€¡ÃƒÆ’O SOCIAL"},
                    {"key": "other_actions", "label": "3.8 - OUTROS"},
                ],
            },
            {
                "key": "publicity_materials", "label": "4 - MATERIAIS DE DIVULGAÃƒâ€¡ÃƒÆ’O", "section": True,
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

        period_from = request.query_params.get("date_from") or "início"
        period_to = request.query_params.get("date_to") or today.isoformat()
        month_label = reference_date.strftime("%m")

        elements = []

        # --- Header ---
        elements.append(Paragraph("Operação Lei Seca", title_style))
        elements.append(Paragraph("Relatório Técnico de Estatísticas", ParagraphStyle("Sub", parent=subtitle_style, fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#333333"))))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"Período analisado: {period_from} a {period_to}", subtitle_style))
        elements.append(Paragraph(f"Emitido em: {today.strftime('%d/%m/%Y')} &nbsp;|&nbsp; Relatórios: {reports.count()} &nbsp;|&nbsp; Ações registradas: {actions.count()}", subtitle_style))
        elements.append(Spacer(1, 6))

        # --- Section 1: Quadro de metas ---
        elements.append(Paragraph(f"1. Quadro de metas {reference_year}", section_title_style))
        data_2 = [[
            Paragraph("Indicador", header_left),
            Paragraph(f"{reference_year} até {month_label}", header_cell),
            Paragraph(f"Projeção {reference_year}", header_cell),
            Paragraph("Média*", header_cell),
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

        # --- Section 2: Evolução anual ---
        elements.append(Paragraph("2. Evolução anual desde 2019", section_title_style))
        data_3 = [[
            Paragraph("Ano", header_left),
            Paragraph("Abordados em palestras", header_cell),
            Paragraph("Abordados em ações", header_cell),
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

        # --- Section 4: Comparação Ano a Ano ---
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
            ("approached_actions", "Abordados em ações"),
            ("publicity_materials", "Materiais de divulgação"),
            ("approached_lectures", "Abordados em palestras"),
        ]

        BLUE_HEADER = colors.HexColor("#003299")

        elements.append(Paragraph("4. Comparação Ano a Ano", section_title_style))
        elements.append(Paragraph(f"Indicadores do ano de referência ({cmp_ref_year}) versus o ano anterior ({cmp_prev_year}) completo.", note_style))
        elements.append(Spacer(1, 4))

        data_cmp = [[
            Paragraph("Indicador", header_left),
            Paragraph(f"{cmp_ref_year} (acumulado)", header_cell),
            Paragraph(f"{cmp_prev_year} (total)", header_cell),
            Paragraph("Diferença", header_cell),
            Paragraph("Variação %", header_cell),
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

        # --- Section 5: Nota técnica ---
        elements.append(Paragraph("5. Nota técnica", section_title_style))
        notes = [
            "Os dados deste relatório são calculados a partir dos relatórios técnicos cadastrados no sistema.",
            "A projeção anual considera o acumulado do ano dividido pela quantidade de meses transcorridos e multiplicado por 12.",
            "As metas e médias históricas são obtidas do cadastro anual de metas da aplicação.",
            "* Média refere-se à média histórica dos anos anteriores registrados no sistema.",
        ]
        for note in notes:
            elements.append(Paragraph(f"Ã¢â‚¬Â¢ {note}", note_style))

        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Operação Lei Seca Ã¢â‚¬â€ Relatório gerado automaticamente em {today.strftime('%d/%m/%Y')}", footer_style))

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=30,
            title=f"Relatório de Estatísticas {reference_year}",
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not (user.is_admin_role or user.role == User.Role.SUPERVISOR):
            raise PermissionDenied("Sem permissão para gerenciar a lista de restrições de acessibilidade.")
        
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


class PublicAgendaRequestView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        date_str = request.query_params.get("date")
        if not date_str:
            return response.Response({"detail": "Informe a data."}, status=400)
            
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return response.Response({"detail": "Formato de data inválido."}, status=400)
            
        agenda_id = request.query_params.get("agenda_id")
        qs = Agenda.objects.filter(
            date=date_obj,
            status__in=[Agenda.Status.PENDING, Agenda.Status.APPROVED]
        )
        if agenda_id and agenda_id.isdigit():
            qs = qs.exclude(id=int(agenda_id))

        return response.Response({"available": True})

    def post(self, request):
        serializer = PublicAgendaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        public_sector, _ = Sector.objects.get_or_create(
            name="Solicitações externas",
            defaults={"description": "Solicitações recebidas por formulário público"},
        )
        system_user, created = User.objects.get_or_create(
            email="solicitacao.publica@agenda.local",
            defaults={
                "username": "solicitacao.publica@agenda.local",
                "full_name": "Solicitação Pública",
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
                "detail": "Solicitação enviada com sucesso. Acompanhe o retorno pelo contato informado.",
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
            raise PermissionDenied("Link de alteração inválido.")

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
                "detail": "Data atualizada e formulário reenviado para avaliação.",
                "protocol": agenda.id,
            }
        )


class SatisfactionSurveyPublicView(APIView):
    permission_classes = [AllowAny]

    def get_survey(self, token):
        try:
            return SatisfactionSurvey.objects.select_related("agenda", "report").get(token=token)
        except SatisfactionSurvey.DoesNotExist:
            raise PermissionDenied("Link da pesquisa inválido.")

    def get(self, request, token):
        survey = self.get_survey(token)
        return response.Response(SatisfactionSurveySerializer(survey).data)

    def post(self, request, token):
        survey = self.get_survey(token)
        if survey.answered_at:
            return response.Response({"detail": "Esta pesquisa já foi respondida."}, status=400)
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
        return response.Response({"detail": "Pesquisa enviada com sucesso. Obrigado pela avaliação."})


class InternalAgendaRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (request.user.is_admin_role or request.user.role == User.Role.SUPERVISOR):
            raise PermissionDenied("Apenas Chefes, Gestores e Administração podem criar solicitações internas.")
        serializer = PublicAgendaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        internal_sector, _ = Sector.objects.get_or_create(
            name="Solicitações internas",
            defaults={"description": "Solicitações cadastradas internamente pela equipe"},
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
                "detail": "Solicitação interna registrada com sucesso.",
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
        ws.append(["Título", "Data", "Início", "Fim", "Status", "Equipe", "Responsável", "Local"])
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
            | Q(sector__name__in=["Solicitações externas", "Solicitações internas"])
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
            (row.get("municipality_ref__name") or row.get("city") or "Sem município").strip()
            for row in qs.values("municipality_ref__name", "city")
        )
        by_municipality = by_municipality_counter.most_common(8)

        by_neighborhood_counter = Counter(
            (row.get("neighborhood_ref__name") or row.get("neighborhood") or "Sem bairro").strip()
            for row in qs.values("neighborhood_ref__name", "neighborhood")
        )
        by_neighborhood = by_neighborhood_counter.most_common(8)

        by_team_actions = list(
            qs.filter(status__in=[Agenda.Status.APPROVED, Agenda.Status.COMPLETED])
            .values("team_ref__name", "team_name")
            .annotate(total=Count("id"))
            .order_by("-total", "team_ref__name", "team_name")[:8]
        )

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

        date_from = request.query_params.get("date_from") or "Início"
        date_to = request.query_params.get("date_to") or today.strftime("%d/%m/%Y")

        elements = []

        # --- Header ---
        elements.append(Paragraph("Operação Lei Seca", title_style))
        elements.append(Paragraph("Relatório Consolidado de Atividades - Dashboard", ParagraphStyle("Sub", parent=subtitle_style, fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#333333"))))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"Período analisado: {date_from} a {date_to}", subtitle_style))
        elements.append(Paragraph(f"Emitido em: {today.strftime('%d/%m/%Y')} &nbsp;|&nbsp; Total de agendas no período: {total}", subtitle_style))
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
            ("Próximas Agendas", upcoming_count),
        ]
        elements.append(make_table(["Métrica Operacional", "Quantidade"], operacionais_rows, [350, 150]))
        elements.append(Spacer(1, 6))

        # --- Section 2: Indicadores Avançados ---
        elements.append(Paragraph("2. Indicadores Avançados", section_title_style))
        avancados_rows = [
            ("Taxa de aprovação", f"{completion_rate}%"),
            ("Taxa de cancelamento", f"{cancellation_rate}%"),
            ("Tempo médio de aprovação", "24h"),
            ("Média por usuário", avg_per_user),
        ]
        elements.append(make_table(["Indicador Avançado", "Valor"], avancados_rows, [350, 150]))
        elements.append(Spacer(1, 6))

        # --- Section 3: Agendas por Município ---
        if by_municipality:
            elements.append(Paragraph("3. Agendas por Município (Top 8)", section_title_style))
            elements.append(make_table(["Município", "Agendas"], by_municipality, [350, 150]))
            elements.append(Spacer(1, 6))

        # --- Section 4: Agendas por Bairro ---
        if by_neighborhood:
            elements.append(Paragraph("4. Agendas por Bairro (Top 8)", section_title_style))
            elements.append(make_table(["Bairro", "Agendas"], by_neighborhood, [350, 150]))
            elements.append(Spacer(1, 6))

        # --- Section 5: Ações por Equipe ---
        if by_team_actions:
            elements.append(Paragraph("5. Ações por Equipe (Top 8)", section_title_style))
            team_rows = [(t["team_ref__name"] or t["team_name"] or "Sem equipe", t["total"]) for t in by_team_actions]
            elements.append(make_table(["Equipe", "Ações Concluídas"], team_rows, [350, 150]))
            elements.append(Spacer(1, 6))

        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"Operação Lei Seca Ã¢â‚¬â€ Relatório gerado automaticamente em {today.strftime('%d/%m/%Y')}", footer_style))

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
    permission_classes = [IsAuthenticated]

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
            ("audiovisual_resources", "Recursos áudio-visuais"),
            ("speaker_knowledge", "Palestrante"),
            ("wheelchair_testimony", "Depoimento dos cadeirantes"),
            ("workshops", "Dinâmicas"),
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
            empty_distribution = {label: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0} for _, label in ALL_CRITERIA}
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
            for score in range(1, 6):
                dist_agg[f"{field}_{score}"] = Sum(
                    Case(When(**{field: score}, then=1), default=0, output_field=IntegerField())
                )
        dist_result = qs.aggregate(**dist_agg)
        for field, label in ALL_CRITERIA:
            distribution[label] = {
                str(score): dist_result.get(f"{field}_{score}", 0) or 0
                for score in range(1, 6)
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
            f"Foram recebidas {total_surveys} avaliações no período selecionado. "
            f"A nota média geral foi {overall_avg:.2f}. "
            f"O índice de excelência atingiu {satisfaction_index:.1f}%. "
            f"Os critérios mais bem avaliados foram {best1} e {best2}. "
            f"O critério com menor média foi {worst_criteria}, indicando oportunidade de melhoria."
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
        O payload esperado é {"namedValues": {"Carimbo de data/hora": ["valor"], ...}}
        """
        named_values = request.data.get("namedValues")
        
        # Fallback caso o script envie diretamente o objeto
        if not named_values and request.data:
            named_values = request.data

        if not named_values or not isinstance(named_values, dict):
            return response.Response({"detail": "Payload inválido. Esperado 'namedValues'."}, status=400)

        # Converte dicionário de listas para dicionário simples
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
            name="Solicitações externas",
            defaults={"description": "Solicitações importadas do Google Forms/Sheets."},
        )

        cmd = ImportGoogleSheetCommand()
        try:
            # O índice 0 é usado apenas para log na descrição
            result = cmd.import_row(row, index=0, admin=admin, sector=sector, dry_run=False)
            return response.Response({"status": "success", "result": result})
        except Exception as e:
            return response.Response({"detail": str(e)}, status=500)
