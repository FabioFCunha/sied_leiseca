from collections import Counter, defaultdict
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Avg, Case, Count, F, IntegerField, Q, Sum, Value, When
from django.db.models.functions import ExtractMonth, ExtractYear
from django.core import signing
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from rest_framework import decorators, response, viewsets
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
    Chief,
    Kit,
    Material,
    Municipality,
    Neighborhood,
    Sector,
    SatisfactionSurvey,
    Support,
    Team,
    Vehicle,
)
from .permissions import AdminOrReadSectorPermission, AgendaPermission
from .emails import PUBLIC_REQUEST_SALT, public_update_url, send_agenda_available_dates_email, send_agenda_status_email, send_satisfaction_survey_email
from .serializers import (
    ActionTypeSerializer,
    AgentSerializer,
    AgendaSerializer,
    EducationReportSerializer,
    EducationGoalSerializer,
    EventReportSerializer,
    ChiefSerializer,
    KitSerializer,
    MaterialSerializer,
    MunicipalitySerializer,
    NeighborhoodSerializer,
    PublicAgendaRequestSerializer,
    PublicAgendaRequestRescheduleSerializer,
    SatisfactionSurveySerializer,
    SectorSerializer,
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
        "age_ranges": agenda.age_ranges,
    }


def chief_agenda_filter(user, prefix=""):
    field = f"{prefix}chief_name"
    chief_ref_field = f"{prefix}chief_ref__name"
    responsible_field = f"{prefix}responsible"
    return (
        Q(**{f"{field}__iexact": user.full_name})
        | Q(**{f"{chief_ref_field}__iexact": user.full_name})
        | Q(**{responsible_field: user})
    )


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
        standard_names = ["ALFA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOX", "GOLF", "HOTEL"]
        queryset = Team.objects.filter(name__in=standard_names, is_active=True)
        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Team.objects.filter(name__in=standard_names)
        return queryset.order_by("name")


class ChiefViewSet(LookupViewSet):
    serializer_class = ChiefSerializer

    def get_queryset(self):
        queryset = Chief.objects.filter(is_active=True)
        if self.request.query_params.get("include_inactive") == "true" and self.request.user.is_admin_role:
            queryset = Chief.objects.all()
        return queryset.select_related("team").order_by("team__name", "name")


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


class ActionTypeViewSet(LookupViewSet):
    serializer_class = ActionTypeSerializer
    queryset = ActionType.objects.all()


class MunicipalityViewSet(LookupViewSet):
    serializer_class = MunicipalitySerializer
    queryset = Municipality.objects.all()


class NeighborhoodViewSet(LookupViewSet):
    serializer_class = NeighborhoodSerializer
    queryset = Neighborhood.objects.all()


class KitViewSet(LookupViewSet):
    serializer_class = KitSerializer
    queryset = Kit.objects.all()


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
        )
        if user.is_admin_role:
            return queryset
        elif user.role == User.Role.SUPERVISOR:
            if self.request.query_params.get("reportable") == "true":
                return queryset.filter(chief_agenda_filter(user))
            return queryset.filter(
                Q(sector_id=user.sector_id)
                | chief_agenda_filter(user)
            )
        return queryset.filter(created_by=user) | queryset.filter(responsible=user)

    def get_queryset(self):
        scoped = self.get_scoped_queryset()
        params = self.request.query_params
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
                search_filter |= Q(id=int(term))
            scoped = scoped.filter(search_filter)
        if params.get("order") == "latest":
            return (
                scoped.distinct()
                .annotate(
                    pending_rank=Case(
                        When(status=Agenda.Status.PENDING, then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField(),
                    ),
                    pending_protocol=Case(
                        When(status=Agenda.Status.PENDING, then=F("id")),
                        default=Value(0),
                        output_field=IntegerField(),
                    ),
                )
                .order_by("pending_rank", "-pending_protocol", "date", "start_time")
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
        message = (
            "Prezado(a) solicitante,\n\n"
            "Não temos disponibilidade para atender na data solicitada. "
            f"Temos disponibilidade nas seguintes datas: {days or 'nenhuma data disponível nos próximos dias'}.\n\n"
            "Caso uma das datas informadas atenda sua necessidade, acesse o link abaixo, altere a data da realização da palestra e reenvie o formulário:\n"
            f"{public_update_url(agenda)}\n\n"
            "Atenciosamente,\n"
            "Superintendência da Operação Lei Seca"
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
        today = timezone.localdate()
        request_source_filter = (
            Q(origin=Agenda.Origin.PUBLIC_FORM)
            | Q(source_id__startswith="internal-request:")
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
                    search_filter |= Q(id=int(term))
                scoped = scoped.filter(search_filter)
            return scoped.distinct()

        qs = apply_dashboard_filters(unscoped_dashboard_queryset()).filter(request_source_filter)
        base_qs = unscoped_dashboard_queryset().filter(request_source_filter)
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
            scoped = unscoped_dashboard_queryset().filter(request_source_filter)
            if request.query_params.get("sector"):
                scoped = scoped.filter(sector_id=request.query_params["sector"])
            if request.query_params.get("municipality"):
                scoped = scoped.filter(municipality_ref_id=request.query_params["municipality"])
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
                    search_filter |= Q(id=int(term))
                scoped = scoped.filter(search_filter)
            return scoped

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

        today_count = qs.filter(date=today).count()
        yesterday_count = base_qs.filter(date=yesterday).count()
        pending = qs.filter(status=Agenda.Status.PENDING).count()
        approved = qs.filter(status=Agenda.Status.APPROVED).count()
        cancelled = qs.filter(status=Agenda.Status.CANCELLED).count()
        in_progress = qs.filter(date=today, start_time__lte=now, end_time__gte=now).exclude(
            status__in=[Agenda.Status.CANCELLED, Agenda.Status.COMPLETED]
        ).count()
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
                "time": row["start_time"].isoformat(timespec="minutes"),
                "status": row["status"],
                "sector": row["sector__name"],
                "responsible": row["responsible__full_name"],
                "updated_at": row["updated_at"].isoformat(),
                "location": row["location"],
            }
            for row in sorted(rows, key=lambda item: item["updated_at"], reverse=True)[:12]
        ]
        field_teams = [
            {
                "id": row["id"],
                "team": row["sector__name"] or "Sem equipe",
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
        if not (request.user.is_superuser or request.user.role in ["ADMIN", "MANAGER"]):
            messages_qs = messages_qs.filter(is_approved=True)

        recent_messages = list(

            messages_qs.order_by('-answered_at')
            .values('id', 'team', 'suggestion', 'answered_at', 'overall_rating', 'is_approved')[:15]
        )


        data = {
            "cards": {
                "today_total": {"value": today_count, "change": pct(today_count, comparison_qs.count() if comparison_qs is not None else yesterday_count), "compare_label": comparison_label},
                "pending": {"value": pending, "change": pct(pending, comparison_qs.filter(status=Agenda.Status.PENDING).count() if comparison_qs is not None else None), "compare_label": comparison_label},
                "approved": {"value": approved, "change": pct(approved, comparison_qs.filter(status=Agenda.Status.APPROVED).count() if comparison_qs is not None else None), "compare_label": comparison_label},
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
            "pending_moderation_count": pending_moderation_count,
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
                "abordados_palestras": qs.filter(action_type__icontains="palestra").aggregate(total=Sum("quantity"))["total"] or 0,
                "abordados_acoes": qs.exclude(action_type__icontains="palestra").aggregate(total=Sum("quantity"))["total"] or 0,
            },
        }
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
        if user.role == User.Role.USER:
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

            related_to_chief = (
                agenda.chief_name.lower() == user.full_name.lower()
                or (agenda.chief_ref and agenda.chief_ref.name.lower() == user.full_name.lower())
                or agenda.responsible_id == user.id
            )
            if not related_to_chief:
                raise PermissionDenied("Você só pode relatar agendas em que você está vinculado como Chefe.")
        if user.role == User.Role.USER:
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
        ("approach", "Abordagens"),
        ("approached_lectures", "Abordados em palestras"),
        ("approached_actions", "Abordados em ações"),
        ("tests", "Testes"),
        ("used_caps", "Bocais usados"),
        ("available_caps", "Bocais disponíveis"),
        ("distributed_folders", "Pastas"),
        ("cricris", "Cricris"),
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
        )
        if user.role == User.Role.USER:
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
                search_filter |= Q(agenda_id=int(term))
            scoped = scoped.filter(search_filter)
        return scoped.distinct().order_by("-operation_date", "-created_at")

    def perform_create(self, serializer):
        with transaction.atomic():
            self._validate_agenda_access(serializer.validated_data["agenda"])
            report = serializer.save(created_by=self.request.user)
            if report.status == EducationReport.ReportStatus.SUBMITTED:
                transaction.on_commit(lambda: send_satisfaction_survey_email(report))

    def perform_update(self, serializer):
        with transaction.atomic():
            previous_status = serializer.instance.status
            agenda = serializer.validated_data.get("agenda", serializer.instance.agenda)
            self._validate_agenda_access(agenda)
            report = serializer.save()
            if previous_status != EducationReport.ReportStatus.SUBMITTED and report.status == EducationReport.ReportStatus.SUBMITTED:
                transaction.on_commit(lambda: send_satisfaction_survey_email(report))

    def _validate_agenda_access(self, agenda):
        user = self.request.user
        if user.is_admin_role:
            return
        if user.role == User.Role.USER:
            raise PermissionDenied("Apenas Chefes, Gestores e Administradores podem preencher relatórios.")
        allowed = Agenda.objects.filter(pk=agenda.pk).filter(chief_agenda_filter(user)).exists()
        if not allowed:
            raise PermissionDenied("Você só pode preencher relatórios dos protocolos em que é Chefe responsável.")

    @decorators.action(detail=False, methods=["get"])
    def statistics(self, request):
        if not request.user.is_admin_role:
            raise PermissionDenied("Apenas Gestores e Administração podem acessar estatísticas.")
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
        first_year = 2019
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
            if user.role == User.Role.USER:
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
                    search_filter |= Q(agenda_id=int(term))
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
        for key, label in comparison_fields:
            current_val = cur_actions.aggregate(total=Sum(key))["total"] or 0
            prev_val    = prev_actions.aggregate(total=Sum(key))["total"] or 0
            diff        = current_val - prev_val
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


        return response.Response(
            {
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
            }
        )

    @decorators.action(detail=False, methods=["get"], url_path="export-statistics")
    def export_statistics(self, request):
        if not request.user.is_admin_role:
            raise PermissionDenied("Apenas Gestores e Administração podem exportar estatísticas.")
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

        totals = {
            field: actions.aggregate(total=Sum(field))["total"] or 0
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
                    {"key": "approached_actions", "label": "1.2 - ABORDADOS AÇÕES"},
                ],
            },
            {
                "key": "lectures", "label": "2 – PALESTRAS", "section": True,
                "children": [
                    {"key": "schools", "label": "2.1 - ESCOLAS"},
                    {"key": "universities", "label": "2.2 - UNIVERSIDADES"},
                    {"key": "companies", "label": "2.3 - EMPRESAS"},
                ],
            },
            {
                "key": "educational_actions", "label": "3 - AÇÕES", "section": True,
                "children": [
                    {"key": "bars", "label": "3.1 - BAR/RESTAURANTE"},
                    {"key": "tolls", "label": "3.2 - PEDÁGIO"},
                    {"key": "sports", "label": "3.3 - PRAÇA ESPORTIVA"},
                    {"key": "beach", "label": "3.4 - PRAIA"},
                    {"key": "events", "label": "3.5 - EVENTO"},
                    {"key": "shopping", "label": "3.6 - SHOPPING"},
                    {"key": "social_actions", "label": "3.7 - AÇÃO SOCIAL"},
                    {"key": "other_actions", "label": "3.8 - OUTROS"},
                ],
            },
            {
                "key": "publicity_materials", "label": "4 - MATERIAIS DE DIVULGAÇÃO", "section": True,
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
        for key, label in comparison_fields:
            cur_val = cmp_cur_actions.aggregate(total=Sum(key))["total"] or 0
            prev_val = cmp_prev_actions.aggregate(total=Sum(key))["total"] or 0
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
            elements.append(Paragraph(f"• {note}", note_style))

        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Operação Lei Seca — Relatório gerado automaticamente em {today.strftime('%d/%m/%Y')}", footer_style))

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
        if user.role == User.Role.USER:
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
                search_filter |= Q(agenda_id=int(term))
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
            
        if qs.count() >= 4:
            from apps.schedules.serializers import get_next_available_dates
            suggested = get_next_available_dates(date_obj)
            suggested_str = ", ".join(d.strftime("%d/%m/%Y") for d in suggested)
            return response.Response({
                "available": False,
                "message": f"Infelizmente já atingimos o limite de vagas para esta data. Sugerimos os dias úteis disponíveis a seguir: {suggested_str}."
            })
            
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
            age_ranges=data.get("age_ranges", ""),
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
        is_approved = not bool(suggestion)
        
        serializer.save(answered_at=timezone.now(), is_approved=is_approved)
        return response.Response({"detail": "Pesquisa enviada com sucesso. Obrigado pela avaliação."})


class InternalAgendaRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_admin_role:
            raise PermissionDenied("Apenas Gestores e Administração podem criar solicitações internas.")
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
            age_ranges=data.get("age_ranges", ""),
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
                search_filter |= Q(id=int(term))
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
            | Q(sector__name__in=["Solicitações externas", "Solicitações internas"])
            | Q(created_by__email="solicitacao.publica@agenda.local")
            | Q(responsible__email="solicitacao.publica@agenda.local")
        )
        qs = self._queryset(request, check_access=False, unscoped=True).filter(request_source_filter)
        log_audit(
            request,
            AuditLog.Action.REPORT_EXPORT,
            "Relatorios",
            "Relatorio operacional exportado em PDF.",
            {"format": "pdf", "total": qs.count()},
        )
        today = timezone.localdate()
        total = qs.count()

        # 2. Compute the exact operational metrics shown on the dashboard page
        approved = qs.filter(status=Agenda.Status.APPROVED).count()
        pending = qs.filter(status=Agenda.Status.PENDING).count()
        cancelled = qs.filter(status=Agenda.Status.CANCELLED).count()
        today_count = qs.filter(date=today).count()
        upcoming_count = qs.filter(date__gte=today).count()
        
        now = timezone.localtime().time()
        in_progress = qs.filter(date=today, start_time__lte=now, end_time__gte=now).exclude(
            status__in=[Agenda.Status.CANCELLED, Agenda.Status.COMPLETED]
        ).count()

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
        elements.append(Paragraph(f"Operação Lei Seca — Relatório gerado automaticamente em {today.strftime('%d/%m/%Y')}", footer_style))

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
        if user.is_superuser or user.role in ["ADMIN", "MANAGER"]:
            return SatisfactionSurvey.objects.all()
        return SatisfactionSurvey.objects.filter(is_approved=True)

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ["PUT", "PATCH", "DELETE"]:
            user = request.user
            if not (user.is_superuser or user.role in ["ADMIN", "MANAGER"]):
                self.permission_denied(request, message="Apenas Gestores e Administração podem moderar avaliações.")

