from rest_framework import serializers
from django.db.models import Q

from .models import (
    ActionType,
    Agent,
    Agenda,
    AgendaHistory,
    AgendaMaterial,
    AccessibilityBlocklist,
    EducationAction,
    EducationGoal,
    EducationReport,
    EventReport,
    Chief,
    Kit,
    Dynamic,
    Material,
    Municipality,
    Neighborhood,
    Sector,
    SatisfactionSurvey,
    ShiftAbsence,
    ShiftSchedule,
    ShiftSwapRequest,
    Support,
    Team,
    Vehicle,
)


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "name", "description", "is_active"]


class AccessibilityBlocklistSerializer(serializers.ModelSerializer):
    source_agenda_protocol = serializers.IntegerField(source="source_agenda_id", read_only=True)
    source_report_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = AccessibilityBlocklist
        fields = [
            "id",
            "institution_location",
            "address",
            "external_responsible",
            "external_responsible_phone",
            "external_email",
            "requester_cpf",
            "reason",
            "source_agenda",
            "source_agenda_protocol",
            "source_report",
            "source_report_id",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "source_agenda_protocol", "source_report_id"]


class LookupSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["id", "source_id", "name", "is_active"]

    def validate_cpf(self, value):
        digits = "".join(char for char in str(value or "") if char.isdigit())
        if not digits:
            return None
        if len(digits) != 11:
            raise serializers.ValidationError("Informe um CPF valido com 11 digitos.")
        return digits


class VehicleSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Vehicle


class TeamSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Team

    def validate_name(self, value):
        normalized = value.strip().upper()
        if not normalized:
            raise serializers.ValidationError("Informe o nome da equipe.")
        return normalized


class SupportSerializer(LookupSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta(LookupSerializer.Meta):
        model = Support
        fields = ["id", "source_id", "name", "cpf", "team", "team_name", "role", "address", "is_active"]

    def validate_name(self, value):
        return value.strip().upper()


class AgentSerializer(LookupSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta(LookupSerializer.Meta):
        model = Agent
        fields = ["id", "source_id", "name", "cpf", "team", "team_name", "role", "address", "is_active"]


class ActionTypeSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = ActionType


class MunicipalitySerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Municipality


class NeighborhoodSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Neighborhood


class KitSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Kit

    def validate_name(self, value):
        return value.strip().upper()


class DynamicSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Dynamic
        fields = LookupSerializer.Meta.fields + ["materials"]

    def validate_name(self, value):
        return value.strip().upper()


class MaterialSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Material


class ChiefSerializer(LookupSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta(LookupSerializer.Meta):
        model = Chief
        fields = ["id", "source_id", "name", "cpf", "team", "team_name", "role", "address", "phone", "is_active"]


def shift_swap_visibility_filter(user):
    if not user or not user.is_authenticated:
        return Q(pk__isnull=True)
    if getattr(user, "is_admin_role", False):
        return Q()

    sector = getattr(user, "sector", None)
    if getattr(user, "role", "") == "SUPERVISOR" and sector and sector.name:
        return Q(schedule__team__name__iexact=sector.name)

    query = Q(requester=user)
    if user.full_name:
        query |= Q(from_member_name__iexact=user.full_name) | Q(to_member_name__iexact=user.full_name)

    cpf = "".join(char for char in str(user.cpf or "") if char.isdigit())
    member_models = [
        (ShiftSwapRequest.MemberType.CHIEF, Chief),
        (ShiftSwapRequest.MemberType.AGENT, Agent),
        (ShiftSwapRequest.MemberType.SUPPORT, Support),
    ]
    if cpf:
        for member_type, lookup_model in member_models:
            member_ids = list(lookup_model.objects.filter(cpf=cpf).values_list("id", flat=True))
            if member_ids:
                query |= (
                    Q(member_type=member_type, from_member_id__in=member_ids)
                    | Q(member_type=member_type, to_member_id__in=member_ids)
                )
    return query


def _digits(value):
    return "".join(char for char in str(value or "") if char.isdigit())


def _same_text(left, right):
    return str(left or "").strip().casefold() == str(right or "").strip().casefold()


def _member_matches_user(member, user):
    user_cpf = _digits(getattr(user, "cpf", ""))
    member_cpf = _digits(getattr(member, "cpf", ""))
    if user_cpf and member_cpf and user_cpf == member_cpf:
        return True
    return bool(getattr(user, "full_name", "")) and _same_text(member.name, user.full_name)


def _user_team_matches_schedule(user, schedule):
    sector = getattr(user, "sector", None)
    return bool(sector and schedule and _same_text(sector.name, schedule.team.name))


class ShiftSwapRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source="requester.full_name", read_only=True)
    target_team_name = serializers.CharField(source="target_team.name", read_only=True)
    schedule_date = serializers.DateField(source="schedule.date", read_only=True)
    schedule_team_name = serializers.CharField(source="schedule.team.name", read_only=True)
    decided_by_name = serializers.CharField(source="decided_by.full_name", read_only=True)
    attachment_url = serializers.FileField(source="attachment", read_only=True)
    can_decide = serializers.SerializerMethodField()

    class Meta:
        model = ShiftSwapRequest
        fields = [
            "id",
            "schedule",
            "schedule_date",
            "schedule_team_name",
            "requester",
            "requester_name",
            "member_type",
            "from_member_id",
            "from_member_name",
            "target_team",
            "target_team_name",
            "to_member_id",
            "to_member_name",
            "reason",
            "attachment",
            "attachment_url",
            "can_decide",
            "status",
            "decided_by",
            "decided_by_name",
            "decided_at",
            "decision_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "requester",
            "requester_name",
            "from_member_name",
            "to_member_name",
            "status",
            "decided_by",
            "decided_by_name",
            "decided_at",
            "decision_note",
            "created_at",
            "updated_at",
            "schedule_date",
            "schedule_team_name",
            "target_team_name",
            "attachment_url",
            "can_decide",
        ]

    def get_can_decide(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        can_manage = bool(getattr(user, "is_admin_role", False))
        return can_manage and obj.status == ShiftSwapRequest.Status.PENDING and obj.requester_id != user.id

    def _lookup_model(self, member_type):
        return {
            ShiftSwapRequest.MemberType.CHIEF: Chief,
            ShiftSwapRequest.MemberType.AGENT: Agent,
            ShiftSwapRequest.MemberType.SUPPORT: Support,
        }.get(member_type)

    def validate(self, attrs):
        schedule = attrs.get("schedule") or getattr(self.instance, "schedule", None)
        member_type = attrs.get("member_type") or getattr(self.instance, "member_type", None)
        from_member_id = attrs.get("from_member_id") or getattr(self.instance, "from_member_id", None)
        target_team = attrs.get("target_team") or getattr(self.instance, "target_team", None)
        to_member_id = attrs.get("to_member_id") or getattr(self.instance, "to_member_id", None)
        lookup_model = self._lookup_model(member_type)

        if not lookup_model:
            raise serializers.ValidationError("Informe o tipo de integrante da troca.")
        if schedule and target_team and schedule.team_id == target_team.id:
            raise serializers.ValidationError("Selecione uma equipe diferente para a troca.")

        from_member = lookup_model.objects.filter(id=from_member_id, team=schedule.team, is_active=True).first()
        if not from_member:
            raise serializers.ValidationError("O integrante de origem precisa pertencer a equipe escalada.")
        to_member = lookup_model.objects.filter(id=to_member_id, team=target_team, is_active=True).first()
        if not to_member:
            raise serializers.ValidationError("O integrante substituto precisa ser da equipe selecionada e da mesma funcao.")

        request = self.context.get("request")
        user = getattr(request, "user", None)
        user_role = getattr(user, "role", "")
        if user and user.is_authenticated:
            if user_role in {"USER", "SUPPORT"} and not _member_matches_user(from_member, user):
                raise serializers.ValidationError("Agentes so podem solicitar troca para o proprio integrante.")
            if user_role == "SUPERVISOR":
                if not _user_team_matches_schedule(user, schedule):
                    raise serializers.ValidationError("Chefes so podem solicitar troca para integrantes da propria equipe.")
                if member_type != ShiftSwapRequest.MemberType.CHIEF and not _same_text(getattr(from_member.team, "name", ""), user.sector.name if user.sector else ""):
                    raise serializers.ValidationError("Chefes so podem solicitar troca para integrantes da propria equipe.")

        attrs["from_member_name"] = from_member.name
        attrs["to_member_name"] = to_member.name
        return attrs


class ShiftScheduleSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    members = serializers.SerializerMethodField()
    swap_requests = serializers.SerializerMethodField()

    class Meta:
        model = ShiftSchedule
        fields = [
            "id",
            "date",
            "team",
            "team_name",
            "notes",
            "members",
            "swap_requests",
            "extra_chiefs",
            "extra_agents",
            "extra_supports",
            "removed_chiefs",
            "removed_agents",
            "removed_supports",
            "absent_chiefs",
            "absent_agents",
            "absent_supports",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_by_name", "created_at", "updated_at", "members", "swap_requests"]

    def validate(self, attrs):
        date = attrs.get("date") or getattr(self.instance, "date", None)
        team = attrs.get("team") or getattr(self.instance, "team", None)
        if date and team:
            queryset = ShiftSchedule.objects.filter(date=date, team=team)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("Esta equipe ja esta escalada para este dia.")
        return attrs

    def get_members(self, obj):
        absent_chief_ids = set(obj.absent_chiefs.values_list("id", flat=True))
        absent_agent_ids = set(obj.absent_agents.values_list("id", flat=True))
        absent_support_ids = set(obj.absent_supports.values_list("id", flat=True))
        absence_records = {
            (record.member_type, record.member_id): record
            for record in obj.absence_records.all()
        }

        def row(item, is_extra=False, is_absent=False):
            member_type = None
            if isinstance(item, Chief):
                member_type = ShiftAbsence.MemberType.CHIEF
            elif isinstance(item, Support):
                member_type = ShiftAbsence.MemberType.SUPPORT
            else:
                member_type = ShiftAbsence.MemberType.AGENT
            absence = absence_records.get((member_type, item.id))
            return {
                "id": item.id,
                "name": item.name,
                "role": item.role,
                "cpf": item.cpf,
                "team": item.team_id,
                "team_name": item.team.name if item.team else "Sem equipe",
                "is_extra": is_extra,
                "is_absent": is_absent,
                "absence_reason": absence.reason if absence else "",
                "absence_attachment_url": absence.attachment.url if absence and absence.attachment else "",
            }

        removed_chief_ids = set(obj.removed_chiefs.values_list("id", flat=True))
        removed_agent_ids = set(obj.removed_agents.values_list("id", flat=True))
        removed_support_ids = set(obj.removed_supports.values_list("id", flat=True))

        chief_objs = Chief.objects.filter(team=obj.team, is_active=True, source_id__startswith="user:").exclude(id__in=removed_chief_ids).order_by("name")
        agent_objs = Agent.objects.filter(team=obj.team, is_active=True, source_id__startswith="user:").exclude(id__in=removed_agent_ids).order_by("name")
        support_objs = Support.objects.filter(team=obj.team, is_active=True, source_id__startswith="user:").exclude(id__in=removed_support_ids).order_by("name")

        chiefs = [row(item, is_absent=item.id in absent_chief_ids) for item in chief_objs]
        agents = [row(item, is_absent=item.id in absent_agent_ids) for item in agent_objs]
        supports = [row(item, is_absent=item.id in absent_support_ids) for item in support_objs]

        for item in obj.extra_chiefs.filter(is_active=True, source_id__startswith="user:"):
            if not any(m["id"] == item.id for m in chiefs):
                chiefs.append(row(item, is_extra=True, is_absent=item.id in absent_chief_ids))
        for item in obj.extra_agents.filter(is_active=True, source_id__startswith="user:"):
            if not any(m["id"] == item.id for m in agents):
                agents.append(row(item, is_extra=True, is_absent=item.id in absent_agent_ids))
        for item in obj.extra_supports.filter(is_active=True, source_id__startswith="user:"):
            if not any(m["id"] == item.id for m in supports):
                supports.append(row(item, is_extra=True, is_absent=item.id in absent_support_ids))

        members = {
            "chiefs": chiefs,
            "agents": agents,
            "supports": supports,
        }
        for swap in obj.swap_requests.filter(status=ShiftSwapRequest.Status.APPROVED):
            group = {
                ShiftSwapRequest.MemberType.CHIEF: "chiefs",
                ShiftSwapRequest.MemberType.AGENT: "agents",
                ShiftSwapRequest.MemberType.SUPPORT: "supports",
            }.get(swap.member_type, "agents")

            is_swap_absent = False
            if swap.member_type == ShiftSwapRequest.MemberType.CHIEF:
                is_swap_absent = swap.to_member_id in absent_chief_ids
            elif swap.member_type == ShiftSwapRequest.MemberType.SUPPORT:
                is_swap_absent = swap.to_member_id in absent_support_ids
            else:
                is_swap_absent = swap.to_member_id in absent_agent_ids
            swap_absence = absence_records.get((swap.member_type, swap.to_member_id))

            replacement = {
                "id": f"swap-{swap.id}",
                "real_id": swap.to_member_id,
                "name": swap.to_member_name,
                "role": f"Troca aprovada: substitui {swap.from_member_name}",
                "cpf": "",
                "team": swap.target_team_id,
                "team_name": swap.target_team.name,
                "swapped": True,
                "is_absent": is_swap_absent,
                "absence_reason": swap_absence.reason if swap_absence else "",
                "absence_attachment_url": swap_absence.attachment.url if swap_absence and swap_absence.attachment else "",
            }
            for index, member in enumerate(members[group]):
                if int(member["id"]) == int(swap.from_member_id):
                    members[group][index] = replacement
                    break
            else:
                members[group].append(replacement)
        return members

    def get_swap_requests(self, obj):
        request = self.context.get("request")
        queryset = obj.swap_requests.select_related("requester", "target_team", "decided_by")
        if request:
            queryset = queryset.filter(shift_swap_visibility_filter(request.user))
        return ShiftSwapRequestSerializer(queryset, many=True, context=self.context).data


class AgendaHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True)

    class Meta:
        model = AgendaHistory
        fields = ["id", "agenda", "changed_by_name", "action", "snapshot", "created_at"]


class AgendaMaterialSerializer(serializers.ModelSerializer):
    kit_name = serializers.CharField(source="kit.name", read_only=True)
    dynamic_name = serializers.CharField(source="dynamic.name", read_only=True)
    material_name = serializers.CharField(source="material.name", read_only=True)

    class Meta:
        model = AgendaMaterial
        fields = ["id", "position", "kit", "kit_name", "dynamic", "dynamic_name", "material", "material_name", "quantity"]


class AgendaSerializer(serializers.ModelSerializer):
    responsible_name = serializers.CharField(source="responsible.full_name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    history = AgendaHistorySerializer(many=True, read_only=True)
    materials = AgendaMaterialSerializer(many=True, required=False)
    vehicle_name = serializers.CharField(source="vehicle_ref.name", read_only=True)
    team_ref_name = serializers.CharField(source="team_ref.name", read_only=True)
    chief_ref_name = serializers.CharField(source="chief_ref.name", read_only=True)
    action_type_ref_name = serializers.CharField(source="action_type_ref.name", read_only=True)
    municipality_ref_name = serializers.CharField(source="municipality_ref.name", read_only=True)
    neighborhood_ref_name = serializers.CharField(source="neighborhood_ref.name", read_only=True)
    linked_action_title = serializers.CharField(source="linked_action.title", read_only=True)
    linked_requests_count = serializers.IntegerField(source="linked_requests.count", read_only=True)
    satisfaction_survey_token = serializers.SerializerMethodField()
    satisfaction_survey_answered_at = serializers.SerializerMethodField()

    class Meta:
        model = Agenda
        fields = [
            "id",
            "source_id",
            "service_order_number",
            "linked_action",
            "linked_action_title",
            "linked_requests_count",
            "satisfaction_survey_token",
            "satisfaction_survey_answered_at",
            "title",
            "description",
            "date",
            "start_time",
            "end_time",
            "location",
            "vehicle",
            "vehicle_ref",
            "vehicle_name",
            "team_name",
            "team_ref",
            "team_ref_name",
            "chief_name",
            "chief_ref",
            "chief_ref_name",
            "team_phone",
            "agents",
            "agents_ref",
            "support_1",
            "support_1_ref",
            "support_2",
            "support_2_ref",
            "action_type",
            "action_type_ref",
            "action_type_ref_name",
            "institution_location",
            "quantity",
            "participant_range",
            "actions_count",
            "schedule_text",
            "time_2",
            "time_3",
            "address",
            "neighborhood",
            "neighborhood_ref",
            "neighborhood_ref_name",
            "city",
            "state",
            "municipality_ref",
            "municipality_ref_name",
            "external_responsible",
            "external_responsible_phone",
            "external_email",
            "contact_email",
            "requester_cpf",
            "requester_role",
            "audience",
            "requester_entity_type",
            "age_ranges",
            "accessibility_access",
            "has_ramps",
            "has_elevators",
            "has_accessible_bathrooms",
            "media_equipment",
            "image_authorization",
            "activity_type",
            "responsible",
            "responsible_name",
            "sector",
            "sector_name",
            "status",
            "origin",
            "cancel_reason",
            "notes",
            "kit_1",
            "kit_1_quantity",
            "material_1",
            "kit_2",
            "kit_2_quantity",
            "material_2",
            "kit_3",
            "kit_3_quantity",
            "material_3",
            "kit_4",
            "kit_4_quantity",
            "material_4",
            "kit_5",
            "kit_5_quantity",
            "material_5",
            "kit_6",
            "kit_6_quantity",
            "material_6",
            "kit_7",
            "kit_7_quantity",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "history",
            "materials",
        ]
        read_only_fields = ["created_by", "service_order_number", "created_at", "updated_at", "history"]

    def validate(self, attrs):
        instance = self.instance
        date = attrs.get("date", getattr(instance, "date", None))
        start_time = attrs.get("start_time", getattr(instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(instance, "end_time", None))

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("A hora final deve ser maior que a hora inicial.")

        status = attrs.get("status", getattr(instance, "status", None))
        cancel_reason = attrs.get("cancel_reason", getattr(instance, "cancel_reason", ""))
        if status == Agenda.Status.CANCELLED and not str(cancel_reason or "").strip():
            raise serializers.ValidationError("Informe o motivo do cancelamento.")

        candidate = Agenda(
            pk=getattr(instance, "pk", None),
            date=date,
            start_time=start_time,
            end_time=end_time,
            location=attrs.get("location", getattr(instance, "location", "")),
            responsible=attrs.get("responsible", getattr(instance, "responsible", None)),
        )
        if date and start_time and end_time and candidate.responsible and candidate.location:
            conflict = candidate.overlaps_queryset().select_related("responsible").order_by("start_time").first()
            if conflict:
                conflict_time = f"{conflict.start_time:%H:%M} às {conflict.end_time:%H:%M}"
                conflict_label = conflict.location or conflict.institution_location or "local não informado"
                raise serializers.ValidationError(
                    f"Existe conflito de horário com o protocolo #{conflict.id}, das {conflict_time}, em {conflict_label}."
                )
        return attrs

    def get_satisfaction_survey_token(self, obj):
        survey = obj.satisfaction_surveys.order_by("-created_at").first()
        return survey.token if survey else ""

    def get_satisfaction_survey_answered_at(self, obj):
        survey = obj.satisfaction_surveys.order_by("-created_at").first()
        return survey.answered_at if survey else None

    def create(self, validated_data):
        materials_data = validated_data.pop("materials", [])
        agenda = super().create(validated_data)
        self._save_materials(agenda, materials_data)
        return agenda

    def update(self, instance, validated_data):
        materials_data = validated_data.pop("materials", None)
        agenda = super().update(instance, validated_data)
        if materials_data is not None:
            agenda.materials.all().delete()
            self._save_materials(agenda, materials_data)
        return agenda

    def _save_materials(self, agenda, materials_data):
        for position, material_data in enumerate(materials_data, start=1):
            material_data.pop("id", None)
            material_data.pop("position", None)
            if not material_data.get("kit") and not material_data.get("material"):
                continue
            AgendaMaterial.objects.create(agenda=agenda, position=position, **material_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if getattr(getattr(request, "user", None), "role", None) == "VISITOR":
            hidden_fields = [
                "vehicle",
                "vehicle_ref",
                "vehicle_name",
                "team_name",
                "team_ref",
                "team_ref_name",
                "chief_name",
                "chief_ref",
                "chief_ref_name",
                "team_phone",
                "agents",
                "agents_ref",
                "support_1",
                "support_1_ref",
                "support_2",
                "support_2_ref",
                "responsible",
                "responsible_name",
                "created_by",
                "created_by_name",
                "history",
            ]
            for field in hidden_fields:
                if field in data:
                    data[field] = [] if field in {"agents_ref", "history"} else None
        return data


def report_text(report):
    agenda = report.agenda
    participants = report.participants_count or agenda.quantity or "não informado"
    incidents = report.incidents.strip() or report.get_incident_status_display()
    materials = report.materials_used.strip() or report.get_material_status_display()
    receptivity = report.public_receptivity.strip() or report.get_receptivity_level_display()
    team = report.team_performance.strip() or report.get_team_performance_status_display()
    positives = report.positive_points.strip() or "A atividade transcorreu de forma organizada, com participação satisfatória do público envolvido."
    improvements = report.improvement_points.strip() or "Não foram identificados pontos críticos que comprometessem o resultado da ação."
    recommendations = report.recommendations.strip() or "Recomenda-se manter o planejamento prévio e o alinhamento entre equipe, local e responsáveis."
    final = report.final_considerations.strip() or "Diante do exposto, considera-se que a atividade cumpriu sua finalidade institucional."

    return (
        f"RELATÓRIO TÉCNICO DE ATIVIDADE\n\n"
        f"1. Identificação da atividade\n"
        f"Atividade: {agenda.title}\n"
        f"Data: {agenda.date.strftime('%d/%m/%Y')}\n"
        f"Horário: {agenda.start_time.strftime('%H:%M')} às {agenda.end_time.strftime('%H:%M')}\n"
        f"Local: {agenda.institution_location or agenda.location}\n"
        f"Endereço: {agenda.address or 'não informado'}\n"
        f"Município: {agenda.city or 'não informado'}\n"
        f"Equipe: {agenda.team_name or agenda.sector.name}\n"
        f"Chefe responsável: {agenda.chief_name or report.created_by.full_name}\n\n"
        f"2. Público atendido\n"
        f"Quantidade estimada/registrada: {participants}\n"
        f"Perfil do público: {report.audience_profile or agenda.audience or 'não informado'}\n\n"
        f"3. Síntese da execução\n"
        f"{report.execution_summary}\n\n"
        f"4. Avaliação técnica\n"
        f"Objetivo da atividade: {report.get_objective_status_display()}.\n"
        f"Execução: {report.get_execution_quality_display()}.\n"
        f"Receptividade do público: {receptivity}\n"
        f"Atuação da equipe: {team}\n"
        f"Materiais utilizados: {materials}\n"
        f"Ocorrências: {incidents}\n\n"
        f"5. Pontos observados\n"
        f"Pontos positivos: {positives}\n"
        f"Pontos de melhoria: {improvements}\n"
        f"Recomendações: {recommendations}\n\n"
        f"6. Considerações finais\n"
        f"{final}"
    )


class EventReportSerializer(serializers.ModelSerializer):
    agenda_title = serializers.CharField(source="agenda.title", read_only=True)
    agenda_date = serializers.DateField(source="agenda.date", read_only=True)
    agenda_location = serializers.CharField(source="agenda.location", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    technical_report = serializers.SerializerMethodField()

    class Meta:
        model = EventReport
        fields = [
            "id",
            "agenda",
            "agenda_title",
            "agenda_date",
            "agenda_location",
            "created_by",
            "created_by_name",
            "status",
            "objective_status",
            "execution_quality",
            "receptivity_level",
            "incident_status",
            "material_status",
            "team_performance_status",
            "participants_count",
            "audience_profile",
            "execution_summary",
            "public_receptivity",
            "incidents",
            "materials_used",
            "team_performance",
            "positive_points",
            "improvement_points",
            "recommendations",
            "final_considerations",
            "technical_report",
            "created_at",
            "updated_at",
            "submitted_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at", "submitted_at", "technical_report"]

    def get_technical_report(self, obj):
        return report_text(obj)


class EducationActionSerializer(serializers.ModelSerializer):
    agenda_title = serializers.CharField(source="agenda.title", read_only=True)

    class Meta:
        model = EducationAction
        fields = [
            "id",
            "agenda",
            "agenda_title",
            "source_id",
            "place_action",
            "type_action",
            "type_audience",
            "institution_name",
            "start_time",
            "final_hour",
            "approach",
            "equipment_materials_removed",
            "equipment_materials_distributed",
            "distribution_materials_removed",
            "distribution_materials_distributed",
            "approached_lectures",
            "approached_actions",
            "tests",
            "used_caps",
            "available_caps",
            "distributed_folders",
            "cricris",
            "vetarolas",
            "used_adhesives",
            "sequence_certificates",
            "gibis",
            "distributed_certificates",
            "lectures",
            "schools",
            "universities",
            "companies",
            "educational_actions",
            "bars",
            "tolls",
            "sports",
            "beach",
            "events",
            "shopping",
            "social_actions",
            "other_actions",
            "publicity_materials",
            "horus_created_at",
            "horus_updated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "agenda_title"]
        extra_kwargs = {"source_id": {"validators": []}}

    def validate_source_id(self, value):
        return value or None


class EducationReportSerializer(serializers.ModelSerializer):
    agenda_title = serializers.CharField(source="agenda.title", read_only=True)
    agenda_date = serializers.DateField(source="agenda.date", read_only=True)
    agenda_location = serializers.CharField(source="agenda.institution_location", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    actions = EducationActionSerializer(many=True, required=False)
    actions_count = serializers.SerializerMethodField()
    satisfaction_survey = serializers.SerializerMethodField()

    class Meta:
        model = EducationReport
        fields = [
            "id",
            "source",
            "source_id",
            "agenda",
            "agenda_title",
            "agenda_date",
            "agenda_location",
            "operation_date",
            "team",
            "management_id",
            "management_name",
            "education_pcd",
            "education_agents",
            "changes_staff",
            "approximate_public",
            "accessibility_conditions_met",
            "materials_removed",
            "materials_spent",
            "equipment_materials_removed",
            "equipment_materials_distributed",
            "distribution_materials_removed",
            "distribution_materials_distributed",
            "breathalyzers",
            "cars",
            "changes_general",
            "contact_received",
            "occurrence_observation",
            "general_observations",
            "lat",
            "lng",
            "status",
            "horus_created_at",
            "horus_updated_at",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "actions_count",
            "actions",
            "satisfaction_survey",
        ]
        read_only_fields = [
            "agenda_title",
            "agenda_date",
            "agenda_location",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "actions_count",
            "satisfaction_survey",
        ]

    def validate_source_id(self, value):
        return value or None

    def get_actions_count(self, obj):
        return obj.actions.count()

    def get_satisfaction_survey(self, obj):
        survey = obj.satisfaction_surveys.first()
        if survey and survey.answered_at:
            return SatisfactionSurveySerializer(survey).data
        return None

    def validate(self, attrs):
        instance = self.instance
        agenda = attrs.get("agenda", getattr(instance, "agenda", None))
        if not agenda:
            raise serializers.ValidationError("Informe o protocolo da solicitação.")
        status = attrs.get("status", getattr(instance, "status", None))
        accessibility = attrs.get("accessibility_conditions_met", getattr(instance, "accessibility_conditions_met", ""))
        if status == EducationReport.ReportStatus.SUBMITTED and accessibility not in {"YES", "NO"}:
            raise serializers.ValidationError({
                "accessibility_conditions_met": "Informe se o local atendeu às condições de acessibilidade para cadeirantes."
            })
        return attrs

    def create(self, validated_data):
        actions_data = validated_data.pop("actions", [])
        report = EducationReport.objects.create(**validated_data)
        self._save_actions(report, actions_data)
        return report

    def update(self, instance, validated_data):
        actions_data = validated_data.pop("actions", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if actions_data is not None:
            instance.actions.all().delete()
            self._save_actions(instance, actions_data)
        return instance

    def _save_actions(self, report, actions_data):
        for action_data in actions_data:
            action_data.pop("id", None)
            EducationAction.objects.create(report=report, **action_data)


class EducationGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationGoal
        fields = [
            "id",
            "year",
            "key",
            "label",
            "average",
            "target",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


def get_next_available_dates(start_date, limit=3):
    from datetime import timedelta
    available_dates = []
    current_date = start_date + timedelta(days=1)
    
    for _ in range(30):
        if len(available_dates) >= limit:
            break
            
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
            
        agendas_count = Agenda.objects.filter(
            date=current_date,
            status__in=[Agenda.Status.PENDING, Agenda.Status.APPROVED]
        ).count()
        
        if agendas_count < 4:
            available_dates.append(current_date)
            
        current_date += timedelta(days=1)
        
    return available_dates


def normalize_block_value(value):
    return " ".join(str(value or "").strip().casefold().split())


def find_accessibility_block(attrs):
    institution = normalize_block_value(attrs.get("institution_location"))
    address = normalize_block_value(attrs.get("address"))
    responsible = normalize_block_value(attrs.get("external_responsible"))
    phone = normalize_block_value(attrs.get("external_responsible_phone"))
    email = normalize_block_value(attrs.get("external_email"))
    cpf = normalize_block_value(attrs.get("requester_cpf"))

    for block in AccessibilityBlocklist.objects.filter(is_active=True):
        if block.address and normalize_block_value(block.address) == address:
            return block
        if block.institution_location and normalize_block_value(block.institution_location) == institution:
            return block
        if block.external_email and normalize_block_value(block.external_email) == email:
            return block
        if block.requester_cpf and normalize_block_value(block.requester_cpf) == cpf:
            return block
        if block.external_responsible and normalize_block_value(block.external_responsible) == responsible:
            return block
        if block.external_responsible_phone and normalize_block_value(block.external_responsible_phone) == phone:
            return block
    return None


PUBLIC_AGE_RANGE_CHOICES = [
    "05 - 10 anos (ensino fundamental - anos iniciais)",
    "11 - 14 anos (ensino fundamental - anos finais)",
    "15 - 17 anos (ensino médio)",
    "acima de 18 anos - Adultos",
]

LEGACY_PUBLIC_AGE_RANGE_CHOICES = [
    "04 até 8 anos",
    "09 até 13 anos",
    "14 até 17 anos",
    "acima de 18 anos",
]


class PublicAgendaRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    description = serializers.CharField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    time_2 = serializers.TimeField(required=False, allow_null=True)
    time_3 = serializers.TimeField(required=False, allow_null=True)
    action_type = serializers.ChoiceField(
        choices=[
            "Palestra Empresa",
            "Palestra Escola",
            "Palestra Virtual",
            "Ação educativa (Espaço interno)",
            "Palestra bilíngue (Inglês)",
        ]
    )
    institution_location = serializers.CharField(max_length=220)
    actions_count = serializers.IntegerField(min_value=1, max_value=3, required=False, allow_null=True)
    address = serializers.CharField(max_length=220)
    neighborhood = serializers.CharField(max_length=120, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120)
    state = serializers.CharField(max_length=40, required=False, allow_blank=True)
    external_responsible = serializers.CharField(max_length=160)
    external_responsible_phone = serializers.CharField(max_length=160)
    external_email = serializers.EmailField()
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    requester_cpf = serializers.CharField(max_length=20, required=False, allow_blank=True)
    requester_role = serializers.CharField(max_length=160, required=False, allow_blank=True)
    requester_entity_type = serializers.CharField(max_length=160)
    audience = serializers.CharField(max_length=160, required=False, allow_blank=True)
    participant_range = serializers.ChoiceField(
        choices=["30 a 50", "51 a 100", "100 a 200"]
    )
    age_ranges = serializers.ChoiceField(
        choices=PUBLIC_AGE_RANGE_CHOICES + LEGACY_PUBLIC_AGE_RANGE_CHOICES
    )
    accessibility_access = serializers.ChoiceField(
        choices=["Sim", "Não", "Não se aplica, pois será realizado no térreo"]
    )
    has_ramps = serializers.ChoiceField(choices=["Sim", "Não"], required=False, allow_blank=True)
    has_elevators = serializers.ChoiceField(choices=["Sim", "Não"], required=False, allow_blank=True)
    has_accessible_bathrooms = serializers.ChoiceField(choices=["Sim", "Não"], required=False, allow_blank=True)
    media_equipment = serializers.CharField(required=False, allow_blank=True)
    image_authorization = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError("A hora final deve ser maior que a hora inicial.")
            
        date = attrs.get("date")
        if date:
            agenda_id = self.context.get("agenda_id")
            qs = Agenda.objects.filter(
                date=date,
                status__in=[Agenda.Status.PENDING, Agenda.Status.APPROVED]
            )
            if agenda_id:
                qs = qs.exclude(id=agenda_id)
            
            if qs.count() >= 4:
                suggested = get_next_available_dates(date)
                suggested_str = ", ".join(d.strftime("%d/%m/%Y") for d in suggested)
                raise serializers.ValidationError(
                    f"Infelizmente já atingimos o limite de vagas para esta data. Sugerimos os dias úteis disponíveis a seguir: {suggested_str}."
                )
                
        return attrs


class PublicAgendaRequestRescheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    actions_count = serializers.IntegerField(min_value=1, max_value=3, required=False, allow_null=True)
    time_2 = serializers.TimeField(required=False, allow_null=True)
    time_3 = serializers.TimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError("A hora final deve ser maior que a hora inicial.")
            
        date = attrs.get("date")
        if date:
            agenda_id = self.context.get("agenda_id")
            qs = Agenda.objects.filter(
                date=date,
                status__in=[Agenda.Status.PENDING, Agenda.Status.APPROVED]
            )
            if agenda_id:
                qs = qs.exclude(id=agenda_id)
                
            if qs.count() >= 4:
                suggested = get_next_available_dates(date)
                suggested_str = ", ".join(d.strftime("%d/%m/%Y") for d in suggested)
                raise serializers.ValidationError(
                    f"Infelizmente já atingimos o limite de vagas para esta data. Sugerimos os dias úteis disponíveis a seguir: {suggested_str}."
                )
                
        return attrs


class SatisfactionSurveySerializer(serializers.ModelSerializer):
    protocol = serializers.IntegerField(source="agenda_id", read_only=True)
    agenda_title = serializers.CharField(source="agenda.title", read_only=True)

    class Meta:
        model = SatisfactionSurvey
        fields = [
            "id",
            "protocol",
            "agenda_title",
            "team",
            "chief_name",
            "audiovisual_resources",
            "speaker_knowledge",
            "wheelchair_testimony",
            "workshops",
            "support_material",
            "punctuality",
            "team_enthusiasm",
            "overall_rating",
            "suggestion",
            "is_approved",
            "answered_at",
        ]
        read_only_fields = ["id", "protocol", "agenda_title", "team", "chief_name", "answered_at"]


    def validate(self, attrs):
        for field in [
            "audiovisual_resources",
            "speaker_knowledge",
            "wheelchair_testimony",
            "workshops",
            "support_material",
            "punctuality",
            "team_enthusiasm",
            "overall_rating",
        ]:
            value = attrs.get(field)
            if value is None or value < 1 or value > 5:
                raise serializers.ValidationError({field: "Informe uma nota de 1 a 5."})
        return attrs
