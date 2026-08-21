from rest_framework import serializers
from django.db.models import Q
import re
import unicodedata

from apps.accounts.models import User

from .models import (
    ActionType,
    Agent,
    Agenda,
    AgendaHistory,
    AgendaMaterial,
    AccessibilityBlocklist,
    ExternalRequestDateBlock,
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
    Region,
    Sector,
    SatisfactionSurvey,
    SatisfactionSurveyModerationHistory,
    ShiftAbsence,
    ShiftSchedule,
    ShiftScheduleChange,
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


class ExternalRequestDateBlockSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    updated_by_name = serializers.CharField(source="updated_by.full_name", read_only=True)

    class Meta:
        model = ExternalRequestDateBlock
        fields = ["id", "start_date", "end_date", "reason", "is_active", "created_by", "created_by_name", "updated_by", "updated_by_name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_by_name", "updated_by", "updated_by_name", "created_at", "updated_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        is_active = attrs.get("is_active", getattr(self.instance, "is_active", True))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "A data final não pode ser anterior à data inicial."})
        if is_active and start_date and end_date:
            conflicts = ExternalRequestDateBlock.objects.filter(is_active=True, start_date__lte=end_date, end_date__gte=start_date)
            if self.instance:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            if conflicts.exists():
                raise serializers.ValidationError({"start_date": "O período informado se sobrepõe a uma indisponibilidade ativa."})
        return attrs


class PublicExternalRequestDateBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalRequestDateBlock
        fields = ["start_date", "end_date"]


def external_request_date_block_message(block):
    start_date = block.start_date.strftime("%d/%m/%Y")
    end_date = block.end_date.strftime("%d/%m/%Y")
    if block.start_date == block.end_date:
        return f"A data {start_date} está indisponível para solicitações externas. Por favor, escolha outra data."
    return f"O período de {start_date} a {end_date} está indisponível para solicitações externas. Por favor, escolha uma data fora desse período."


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
        fields = ["id", "source_id", "name", "cpf", "team", "team_name", "role", "address", "is_active", "vacation_start", "vacation_end"]

    def validate_name(self, value):
        return value.strip().upper()


class AgentSerializer(LookupSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta(LookupSerializer.Meta):
        model = Agent
        fields = ["id", "source_id", "name", "cpf", "team", "team_name", "role", "address", "is_active", "vacation_start", "vacation_end"]


class ActionTypeSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = ActionType
        fields = ["id", "source_id", "name", "category", "is_active"]


class RegionSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Region

class MunicipalitySerializer(LookupSerializer):
    region_id = serializers.IntegerField(source="region.id", read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta(LookupSerializer.Meta):
        model = Municipality
        fields = LookupSerializer.Meta.fields + ["region_id", "region_name"]


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
        fields = ["id", "source_id", "name", "cpf", "team", "team_name", "role", "address", "phone", "is_active", "vacation_start", "vacation_end"]


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


def build_schedule_members(obj, agenda=None):
    from apps.schedules.services import get_effective_members
    return get_effective_members(obj, agenda)


class ShiftScheduleChangeSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = ShiftScheduleChange
        fields = [
            "id",
            "action",
            "member_type",
            "member_id",
            "member_name",
            "reason",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields


class ShiftScheduleSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    members = serializers.SerializerMethodField()
    swap_requests = serializers.SerializerMethodField()
    member_changes = ShiftScheduleChangeSerializer(many=True, read_only=True)

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
            "member_changes",
            "extra_chiefs",
            "extra_agents",
            "extra_supports",
            "removed_chiefs",
            "removed_agents",
            "removed_supports",
            "absent_chiefs",
            "absent_agents",
            "absent_supports",
            "attendance_reported",
            "attendance_reported_at",
            "attendance_approved",
            "attendance_approved_at",
            "checked_members",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_by_name", "created_at", "updated_at", "members", "swap_requests", "attendance_reported_at", "attendance_approved_at"]

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
        return build_schedule_members(
            obj,
            self.context.get("context_agenda"),
        )


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
    support_1_ref_name = serializers.CharField(source="support_1_ref.name", read_only=True)
    support_2_ref_name = serializers.CharField(source="support_2_ref.name", read_only=True)
    action_type_ref_name = serializers.CharField(source="action_type_ref.name", read_only=True)
    municipality_ref_name = serializers.CharField(source="municipality_ref.name", read_only=True)
    neighborhood_ref_name = serializers.CharField(source="neighborhood_ref.name", read_only=True)
    linked_action_title = serializers.CharField(source="linked_action.title", read_only=True)
    linked_requests_count = serializers.SerializerMethodField()
    satisfaction_survey_token = serializers.SerializerMethodField()
    satisfaction_survey_answered_at = serializers.SerializerMethodField()
    satisfaction_rating = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    delete_block_reason = serializers.SerializerMethodField()
    designated_users = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), many=True, required=False)
    absent_designated_users = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), many=True, required=False)
    designated_users_details = serializers.SerializerMethodField()
    predicted_agreement_indicator = serializers.SerializerMethodField()
    predicted_agreement_indicator_label = serializers.SerializerMethodField()

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
            "satisfaction_rating",
            "can_delete",
            "delete_block_reason",
            "title",
            "description",
            "date",
            "start_time",
            "end_time",
            "location",
            "vehicle",
            "vehicle_ref",
            "vehicle_name",
            "service_order_mode",
            "designated_users",
            "absent_designated_users",
            "designated_users_details",
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
            "support_1_ref_name",
            "support_2",
            "support_2_ref",
            "support_2_ref_name",
            "action_type",
            "action_type_ref",
            "action_type_ref_name",
            "institution_location",
            "quantity",
            "participant_range",
            "street_action_details",
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
            "predicted_agreement_indicator",
            "predicted_agreement_indicator_label",
            "administrative_demand_type",
            "travel_displacement",
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
        read_only_fields = [
            "created_by",
            "service_order_number",
            "created_at",
            "updated_at",
            "history",
            "predicted_agreement_indicator",
            "predicted_agreement_indicator_label",
        ]

    def validate(self, attrs):
        instance = self.instance
        start_time = attrs.get("start_time", getattr(instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(instance, "end_time", None))

        STREET_ACTION_ID = "6"
        action_type_ref = getattr(instance, "action_type_ref_id", None)
        if "action_type_ref" in attrs:
            action_ref = attrs["action_type_ref"]
            if action_ref:
                if not action_ref.is_active or action_ref.category == ActionType.Category.PROGRAM_INDICATOR or action_ref.name.lower() == "palestra escola":
                    raise serializers.ValidationError({"action_type_ref": f"O tipo de ação '{action_ref.name}' não está ativo para novas seleções."})
            action_type_ref = getattr(attrs["action_type_ref"], "id", None) if attrs["action_type_ref"] else None
        requester_entity_type = str(attrs.get("requester_entity_type", getattr(instance, "requester_entity_type", "")))
        administrative_demand_type = str(attrs.get("administrative_demand_type", getattr(instance, "administrative_demand_type", "")) or "")
        is_street_action = (str(action_type_ref) == STREET_ACTION_ID) or (requester_entity_type == STREET_ACTION_ID)

        current_origin = attrs.get("origin", getattr(instance, "origin", ""))
        if current_origin == Agenda.Origin.INTERNAL:
            if requester_entity_type == "Demanda Administrativa":
                valid_subtypes = {choice for choice, _label in Agenda.AdministrativeDemandType.choices}
                if not administrative_demand_type:
                    raise serializers.ValidationError({"administrative_demand_type": "Informe o tipo de demanda administrativa."})
                if administrative_demand_type not in valid_subtypes:
                    raise serializers.ValidationError({"administrative_demand_type": "Informe um tipo de demanda administrativa v?lido."})
            else:
                attrs["administrative_demand_type"] = ""
        else:
            attrs["administrative_demand_type"] = ""

        if start_time and end_time and start_time == end_time:
            raise serializers.ValidationError({"end_time": "A hora final nÃ£o pode ser igual Ã  hora inicial."})

        status_field = attrs.get("status", getattr(instance, "status", None))
        cancel_reason = attrs.get("cancel_reason", getattr(instance, "cancel_reason", ""))

        if instance and instance.status == Agenda.Status.CANCELLED and status_field != Agenda.Status.CANCELLED:
            raise serializers.ValidationError({"status": "N?o ? poss?vel alterar o status de uma solicita??o cancelada via edi??o normal. Utilize a a??o de reabertura."})

        if status_field == Agenda.Status.CANCELLED and not str(cancel_reason or "").strip():
            raise serializers.ValidationError({"cancel_reason": "Informe o motivo do cancelamento."})

        service_order_mode = attrs.get(
            "service_order_mode",
            getattr(instance, "service_order_mode", Agenda.ServiceOrderMode.TEAM),
        ) or Agenda.ServiceOrderMode.TEAM

        designated_users_present = "designated_users" in attrs
        if designated_users_present:
            designated_users = list(attrs.get("designated_users") or [])
        elif instance:
            designated_users = list(instance.designated_users.all())
        else:
            designated_users = []

        inactive_designated = [member.full_name for member in designated_users if not member.is_active]
        if inactive_designated:
            raise serializers.ValidationError({
                "designated_users": f"Selecione apenas usu?rios ativos. Inativos: {', '.join(inactive_designated)}.",
            })

        current_team_ref = attrs.get("team_ref", getattr(instance, "team_ref", None))
        current_team_name = attrs.get("team_name", getattr(instance, "team_name", ""))
        current_chief_ref = attrs.get("chief_ref", getattr(instance, "chief_ref", None))
        current_chief_name = attrs.get("chief_name", getattr(instance, "chief_name", ""))
        current_team_phone = attrs.get("team_phone", getattr(instance, "team_phone", ""))
        current_support_1_ref = attrs.get("support_1_ref", getattr(instance, "support_1_ref", None))
        current_support_1 = attrs.get("support_1", getattr(instance, "support_1", ""))
        current_support_2_ref = attrs.get("support_2_ref", getattr(instance, "support_2_ref", None))
        current_support_2 = attrs.get("support_2", getattr(instance, "support_2", ""))
        current_agents_ref = list(attrs.get("agents_ref", [])) if "agents_ref" in attrs else list(instance.agents_ref.all()) if instance else []
        current_agents = attrs.get("agents", getattr(instance, "agents", ""))

        has_operational_team_data = any([
            current_team_ref,
            str(current_team_name or "").strip(),
            current_chief_ref,
            str(current_chief_name or "").strip(),
            str(current_team_phone or "").strip(),
            current_support_1_ref,
            str(current_support_1 or "").strip(),
            current_support_2_ref,
            str(current_support_2 or "").strip(),
            bool(current_agents_ref),
            str(current_agents or "").strip(),
        ])

        if service_order_mode == Agenda.ServiceOrderMode.DESIGNATED:
            if not designated_users:
                raise serializers.ValidationError({"designated_users": "Selecione ao menos um participante para a Ordem de Servi?o."})
            if has_operational_team_data:
                raise serializers.ValidationError({
                    "service_order_mode": "Para usar participantes selecionados, remova a composi??o da equipe operacional antes de salvar.",
                })
        else:
            if designated_users:
                raise serializers.ValidationError({
                    "designated_users": "Limpe os participantes selecionados para voltar ao modo de equipe operacional.",
                })
        return attrs

    def get_predicted_agreement_indicator(self, obj):
        from .agreement_indicators import derive_from_agenda
        return derive_from_agenda(obj)

    def get_predicted_agreement_indicator_label(self, obj):
        from .agreement_indicators import derive_from_agenda, EducationAgreementIndicator
        val = derive_from_agenda(obj)
        if val == EducationAgreementIndicator.ESCOLINHA_NOTA_10:
            return "Escolinha Nota 10"
        elif val == EducationAgreementIndicator.ESCOLA_NOTA_10:
            return "Escola Nota 10"
        return None

    def get_linked_requests_count(self, obj):
        if hasattr(obj, 'linked_requests_count_annotated'):
            return obj.linked_requests_count_annotated
        return obj.linked_requests.count()

    def get_satisfaction_survey_token(self, obj):
        surveys = list(obj.satisfaction_surveys.all())
        if not surveys:
            return ""
        survey = sorted(surveys, key=lambda s: s.created_at, reverse=True)[0]
        return survey.token

    def get_satisfaction_survey_answered_at(self, obj):
        surveys = list(obj.satisfaction_surveys.all())
        if not surveys:
            return None
        survey = sorted(surveys, key=lambda s: s.created_at, reverse=True)[0]
        return survey.answered_at

    def get_satisfaction_rating(self, obj):
        answered_surveys = [s for s in obj.satisfaction_surveys.all() if s.answered_at]
        if not answered_surveys:
            return None
        return sum(s.overall_rating for s in answered_surveys if s.overall_rating) / len(answered_surveys)

    def get_can_delete(self, obj):
        return not bool(self.get_delete_block_reason(obj))

    def get_designated_users_details(self, obj):
        from apps.accounts.serializers import team_for_user

        details = []
        for member in obj.designated_users.filter(is_active=True).order_by("full_name"):
            team = team_for_user(member)
            details.append({
                "id": member.id,
                "full_name": member.full_name,
                "role": member.get_role_display() if hasattr(member, "get_role_display") else member.role,
                "team_name": team.name if team else "",
            })
        return details

    def get_delete_block_reason(self, obj):
        blockers = []
        if obj.technical_reports.exists():
            blockers.append("relatório técnico")
        if hasattr(obj, "event_report"):
            blockers.append("relatório de evento")
        if obj.satisfaction_surveys.exists():
            blockers.append("avaliação de satisfação")
        if not blockers:
            return ""
        if len(blockers) == 1:
            joined = blockers[0]
        elif len(blockers) == 2:
            joined = " e ".join(blockers)
        else:
            joined = ", ".join(blockers[:-1]) + f" e {blockers[-1]}"
        return f"Esta solicitação não pode ser excluída porque já possui {joined} vinculado."

    def create(self, validated_data):
        materials_data = validated_data.pop("materials", [])
        designated_users = validated_data.pop("designated_users", [])
        agenda = super().create(validated_data)
        if designated_users:
            agenda.designated_users.set(designated_users)
        self._save_materials(agenda, materials_data)
        return agenda

    def update(self, instance, validated_data):
        materials_data = validated_data.pop("materials", None)
        designated_users = validated_data.pop("designated_users", None)
        request = self.context.get("request")
        next_status = validated_data.get("status")
        is_decision_transition = (
            next_status in {Agenda.Status.APPROVED, Agenda.Status.CANCELLED}
            and next_status != instance.status
            and getattr(getattr(request, "user", None), "is_authenticated", False)
        )
        if is_decision_transition:
            validated_data["responsible"] = request.user
        elif instance.origin == Agenda.Origin.INTERNAL:
            validated_data.pop("responsible", None)
        agenda = super().update(instance, validated_data)
        if designated_users is not None:
            agenda.designated_users.set(designated_users)
        if materials_data is not None:
            agenda.materials.all().delete()
            self._save_materials(agenda, materials_data)
        return agenda

    def _save_materials(self, agenda, materials_data):
        for position, material_data in enumerate(materials_data, start=1):
            material_data.pop("id", None)
            material_data.pop("position", None)
            if not material_data.get("kit") and not material_data.get("material") and not material_data.get("dynamic"):
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
                "support_1_ref_name",
                "support_2",
                "support_2_ref",
                "support_2_ref_name",
                "responsible",
                "responsible_name",
                "created_by",
                "created_by_name",
                "history",
                "designated_users",
                "designated_users_details",
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


ACTION_COUNTER_FIELDS = {
    "bares": "bars",
    "pedagio": "tolls",
    "esportes": "sports",
    "praia": "beach",
    "eventos": "events",
    "shopping": "shopping",
    "shopping/centro comercial": "shopping",
    "pracas/parques publicos": "parks",
    "pontos turisticos": "tourist_spots",
    "acao social": "social_actions",
    "ao social": "social_actions",
    "acao conjunta com a fiscalizacao": "joint_inspections",
    "ao conjunta com a fiscalizao": "joint_inspections",
    "outros": "other_actions",
}


class EducationActionListSerializer(serializers.ListSerializer):
    """Keeps historical action-type exceptions scoped to their original row."""

    def to_internal_value(self, data):
        if not isinstance(data, list):
            self.fail("not_a_list", input_type=type(data).__name__)

        validated_data = []
        errors = []
        legacy_action_types_by_id = getattr(self, "legacy_action_types_by_id", {})
        for item in data:
            action_id = item.get("id") if isinstance(item, dict) else None
            submitted_type = str(item.get("type_action") or "").strip() if isinstance(item, dict) else ""
            previous_type = legacy_action_types_by_id.get(str(action_id), "").strip()
            self.child._allow_historical_action_type = (
                bool(previous_type)
                and bool(submitted_type)
                and previous_type.lower() == submitted_type.lower()
            )
            try:
                validated_data.append(self.child.run_validation(item))
                errors.append({})
            except serializers.ValidationError as exc:
                validated_data.append({})
                errors.append(exc.detail)
            finally:
                self.child._allow_historical_action_type = False

        if any(errors):
            raise serializers.ValidationError(errors)
        return validated_data


class EducationActionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    agenda_title = serializers.CharField(source="agenda.title", read_only=True)

    @staticmethod
    def _is_selectable_action_type(action_type):
        if not action_type:
            return False
        if not action_type.is_active:
            return False
        if not action_type.category:
            return False
        if action_type.category == ActionType.Category.PROGRAM_INDICATOR:
            return False
        if str(action_type.name or "").strip().lower() == "palestra escola":
            return False
        return action_type.category in {
            ActionType.Category.LECTURE,
            ActionType.Category.EDUCATIONAL_ACTION,
        }

    class Meta:
        model = EducationAction
        list_serializer_class = EducationActionListSerializer
        fields = [
            "id",
            "agenda",
            "agenda_title",
            "source_id",
            "place_action",
            "type_action",
            "type_audience",
            "requester_entity_kind",
            "requester_entity_nature",
            "age_range",
            "agreement_indicator",
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
            "parks",
            "tourist_spots",
            "social_actions",
            "joint_inspections",
            "other_actions",
            "publicity_materials",
            "horus_created_at",
            "horus_updated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "agenda_title", "agreement_indicator"]
        extra_kwargs = {"source_id": {"validators": []}}

    def validate_source_id(self, value):
        return value or None

    def validate_distribution_materials_distributed(self, value):
        if not value:
            return value

        import re
        from apps.schedules.models import Kit

        for line in value.splitlines():
            text = line.strip()
            if not text:
                continue
            text = re.sub(r"\[\s*\]", "| 0", text)
            if "|" in text:
                name_part, quantity_part = [part.strip() for part in text.rsplit("|", 1)]
                name = name_part
                quantity = quantity_part
            else:
                match = re.match(r"^(?P<name>.+?)\s+-\s*(?P<quantity>\d+)\s*$", text)
                if not match:
                    continue
                name = match.group("name").strip()
                quantity = match.group("quantity")
            
            quantity_match = re.search(r"\d+", str(quantity))
            if not name or not quantity_match:
                continue

            if int(quantity_match.group(0)) == 0:
                continue

            if not Kit.objects.filter(name__iexact=name).exists():
                raise serializers.ValidationError(
                    f"O material '{name}' não pertence à categoria Material para Distribuição."
                )
        return value

    def validate(self, attrs):
        action_type = str(attrs.get("type_action", getattr(self.instance, "type_action", "")) or "").strip()
        incoming_action_type = attrs.get("type_action", serializers.empty)
        current_action_type = str(getattr(self.instance, "type_action", "") or "").strip()
        action_type_changed = incoming_action_type is not serializers.empty and action_type != current_action_type

        if action_type:
            matched_action = ActionType.objects.filter(name__iexact=action_type).order_by("id").first()
            if not matched_action:
                raise serializers.ValidationError({"type_action": "Selecione um tipo operacional válido cadastrado no catálogo."})
            allows_historical_action_type = bool(getattr(self, "_allow_historical_action_type", False))
            if not self._is_selectable_action_type(matched_action) and not allows_historical_action_type:
                if not self.instance or action_type_changed:
                    if matched_action.name.lower() == "palestra escola":
                        raise serializers.ValidationError({"type_action": "O tipo de ação 'Palestra Escola' foi desativado e não pode ser selecionado."})
                    raise serializers.ValidationError({"type_action": f"O tipo de ação '{matched_action.name}' não está disponível para novas seleções."})
            attrs["type_action"] = matched_action.name

        counter_fields = [
            "educational_actions",
            "bars",
            "tolls",
            "sports",
            "beach",
            "events",
            "shopping",
            "parks",
            "tourist_spots",
            "social_actions",
            "joint_inspections",
            "other_actions",
        ]
        for field in counter_fields:
            attrs[field] = 0
        mapped_field = ACTION_COUNTER_FIELDS.get(normalize_action_choice(action_type))
        if mapped_field:
            attrs["educational_actions"] = 1
            attrs[mapped_field] = 1

        from .agreement_indicators import derive_education_agreement_indicator
        kind = attrs.get("requester_entity_kind", getattr(self.instance, "requester_entity_kind", None))
        nature = attrs.get("requester_entity_nature", getattr(self.instance, "requester_entity_nature", None))
        age = attrs.get("age_range", getattr(self.instance, "age_range", None))
        attrs["agreement_indicator"] = derive_education_agreement_indicator(kind, nature, age)

        return attrs


class EducationReportSerializer(serializers.ModelSerializer):
    agenda_title = serializers.CharField(source="agenda.title", read_only=True)
    agenda_date = serializers.DateField(source="agenda.date", read_only=True)
    agenda_location = serializers.CharField(source="agenda.institution_location", read_only=True)
    agenda_service_order_number = serializers.IntegerField(source="agenda.service_order_number", read_only=True)
    agenda_service_order_mode = serializers.CharField(source="agenda.service_order_mode", read_only=True)
    agenda_phone = serializers.CharField(source="agenda.external_responsible_phone", read_only=True)
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
            "agenda_service_order_number",
            "agenda_service_order_mode",
            "agenda_phone",
            "operation_date",
            "team",
            "management_id",
            "management_name",
            "education_pcd",
            "education_agents",
            "changes_staff",
            "approximate_public",
            "street_action_details",
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
            "has_exceptional_occurrence",
            "exceptional_occurrence_type",
            "exceptional_occurrence_description",
            "exceptional_occurrence_actions_taken",
            "exceptional_occurrence_impact",
            "photo_1",
            "photo_2",
            "no_photo_reason",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, "pk", None):
            self.fields["actions"].legacy_action_types_by_id = {
                str(action.pk): action.type_action or ""
                for action in self.instance.actions.all().only("id", "type_action")
            }

    def get_actions_count(self, obj):
        if hasattr(obj, 'actions_count_annotated'):
            return obj.actions_count_annotated
        return obj.actions.count()

    def get_satisfaction_survey(self, obj):
        survey = obj.satisfaction_surveys.first()
        if not survey and obj.agenda_id:
            survey = SatisfactionSurvey.objects.filter(agenda_id=obj.agenda_id).first()
        if survey and survey.answered_at:
            return SatisfactionSurveySerializer(survey).data
        return None

    def validate(self, attrs):
        instance = self.instance
        agenda = attrs.get("agenda", getattr(instance, "agenda", None))
        if not agenda:
            raise serializers.ValidationError("Informe o protocolo da solicita\u00e7\u00e3o.")
        status = attrs.get("status", getattr(instance, "status", None))
        accessibility = attrs.get("accessibility_conditions_met", getattr(instance, "accessibility_conditions_met", ""))
        if status == EducationReport.ReportStatus.APPROVED and accessibility not in {"YES", "NO"}:
            raise serializers.ValidationError({
                "accessibility_conditions_met": "Informe se o local atendeu \u00e0s condi\u00e7\u00f5es de acessibilidade para cadeirantes."
            })

        has_exceptional_occurrence = attrs.get(
            "has_exceptional_occurrence",
            getattr(instance, "has_exceptional_occurrence", False),
        )
        exceptional_occurrence_type = (
            attrs.get(
                "exceptional_occurrence_type",
                getattr(instance, "exceptional_occurrence_type", ""),
            )
            or ""
        )
        exceptional_occurrence_description = (
            attrs.get(
                "exceptional_occurrence_description",
                getattr(instance, "exceptional_occurrence_description", ""),
            )
            or ""
        )
        exceptional_occurrence_actions_taken = (
            attrs.get(
                "exceptional_occurrence_actions_taken",
                getattr(instance, "exceptional_occurrence_actions_taken", ""),
            )
            or ""
        )
        exceptional_occurrence_impact = (
            attrs.get(
                "exceptional_occurrence_impact",
                getattr(instance, "exceptional_occurrence_impact", ""),
            )
            or ""
        )

        if has_exceptional_occurrence:
            valid_types = {choice for choice, _label in EducationReport.ExceptionalOccurrenceType.choices}
            valid_impacts = {choice for choice, _label in EducationReport.ExceptionalOccurrenceImpact.choices}
            errors = {}

            if not exceptional_occurrence_type:
                errors["exceptional_occurrence_type"] = "Informe o tipo da ocorr\u00eancia excepcional."
            elif exceptional_occurrence_type not in valid_types:
                errors["exceptional_occurrence_type"] = "Informe um tipo de ocorr\u00eancia excepcional v\u00e1lido."

            if not exceptional_occurrence_description:
                errors["exceptional_occurrence_description"] = "Informe a descri\u00e7\u00e3o da ocorr\u00eancia excepcional."

            if not exceptional_occurrence_actions_taken:
                errors["exceptional_occurrence_actions_taken"] = "Informe as provid\u00eancias adotadas."

            if not exceptional_occurrence_impact:
                errors["exceptional_occurrence_impact"] = "Informe o impacto da ocorr\u00eancia excepcional."
            elif exceptional_occurrence_impact not in valid_impacts:
                errors["exceptional_occurrence_impact"] = "Informe um impacto de ocorr\u00eancia excepcional v\u00e1lido."

            if errors:
                raise serializers.ValidationError(errors)

            attrs["exceptional_occurrence_type"] = exceptional_occurrence_type
            attrs["exceptional_occurrence_description"] = exceptional_occurrence_description
            attrs["exceptional_occurrence_actions_taken"] = exceptional_occurrence_actions_taken
            attrs["exceptional_occurrence_impact"] = exceptional_occurrence_impact
        else:
            attrs["exceptional_occurrence_type"] = ""
            attrs["exceptional_occurrence_description"] = ""
            attrs["exceptional_occurrence_actions_taken"] = ""
            attrs["exceptional_occurrence_impact"] = ""

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
            legacy_action_types_by_id = {
                str(action.pk): action.type_action or ""
                for action in instance.actions.all().only("id", "type_action")
            }
            instance.actions.all().delete()
            self._save_actions(instance, actions_data, legacy_action_types_by_id)
        return instance

    @staticmethod
    def _is_meaningful_action_data(action_data):
        if not isinstance(action_data, dict):
            return False
        meaningful_fields = (
            "type_action",
            "place_action",
            "type_audience",
            "institution_name",
            "start_time",
            "final_hour",
            "source_id",
        )
        for field in meaningful_fields:
            value = action_data.get(field)
            if value is None:
                continue
            if isinstance(value, str):
                if value.strip():
                    return True
                continue
            if value:
                return True
        return False

    def _save_actions(self, report, actions_data, legacy_action_types_by_id=None):
        from .agreement_indicators import normalize_age_range, normalize_entity_type

        agenda = report.agenda
        first_saved_action = True
        for action_data in actions_data:
            if not self._is_meaningful_action_data(action_data):
                continue
            action_data = action_data.copy()
            source_action_id = action_data.pop("id", None)
            action_data.pop("source_id", None)
            action_data.setdefault("agenda", getattr(agenda, "pk", agenda))
            submitted_action_type = str(action_data.get("type_action") or "").strip()
            historical_agenda_action_name = ""

            if first_saved_action and agenda:
                if not action_data.get("requester_entity_kind") and not action_data.get("requester_entity_nature"):
                    inherited_kind, inherited_nature = normalize_entity_type(agenda.requester_entity_type)
                    if not action_data.get("requester_entity_kind") and inherited_kind:
                        action_data["requester_entity_kind"] = inherited_kind
                    if not action_data.get("requester_entity_nature") and inherited_nature:
                        action_data["requester_entity_nature"] = inherited_nature
                if not action_data.get("age_range"):
                    inherited_age = normalize_age_range(agenda.age_ranges)
                    if inherited_age:
                        action_data["age_range"] = inherited_age
                agenda_action_type = getattr(agenda, "action_type_ref", None)
                if agenda_action_type and str(agenda_action_type.name or "").strip():
                    historical_agenda_action_name = str(agenda_action_type.name).strip()
                else:
                    agenda_action_name = str(getattr(agenda, "action_type", "") or "").strip()
                    if agenda_action_name:
                        matched_action = ActionType.objects.filter(name__iexact=agenda_action_name).order_by("id").first()
                        historical_agenda_action_name = matched_action.name if matched_action else agenda_action_name
                if not submitted_action_type and historical_agenda_action_name:
                    action_data["type_action"] = historical_agenda_action_name

            current_action_type = str(action_data.get("type_action") or "").strip()
            allows_historical_action_type = (
                (legacy_action_types_by_id or {}).get(str(source_action_id), "").strip().lower()
                == current_action_type.lower()
            )
            if not allows_historical_action_type and first_saved_action and historical_agenda_action_name and current_action_type:
                allows_historical_action_type = historical_agenda_action_name.lower() == current_action_type.lower()
            serializer = EducationActionSerializer(data=action_data, context=self.context)
            serializer._allow_historical_action_type = allows_historical_action_type
            serializer.is_valid(raise_exception=True)
            serializer.save(report=report)
            first_saved_action = False


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
    from django.db.models import Count
    available_dates = []
    end_date = start_date + timedelta(days=40)  # buffer para os finais de semana

    # Busca as contagens de todos os dias futuros em uma unica query
    busy_dates_query = Agenda.objects.filter(
        date__gt=start_date,
        date__lte=end_date,
        status__in=[Agenda.Status.PENDING, Agenda.Status.APPROVED]
    ).values('date').annotate(count=Count('id'))
    
    busy_dates = {item['date']: item['count'] for item in busy_dates_query}
    
    current_date = start_date + timedelta(days=1)
    
    while len(available_dates) < limit and current_date <= end_date:
        if current_date.weekday() < 5:
            count = busy_dates.get(current_date, 0)
            if count < 4:
                available_dates.append(current_date)
        current_date += timedelta(days=1)
        
    return available_dates


def normalize_block_value(value):
    return " ".join(str(value or "").strip().casefold().split())


def normalize_action_choice(value):
    normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace("?", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized.casefold())
    return " ".join(normalized.split())


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


PUBLIC_ACTION_TYPE_CHOICES = [
    "Palestra",
    "Ação de educação/conscientização",
    "Palestra Empresa",
    "Palestra Escola",
    "Palestra Virtual",
    "Ação educativa (Espaço interno)",
    "Palestra bilíngue (Inglês)",
]

STREET_ACTION_TYPE_CHOICES = [
    "Bares",
    "Pedágio",
    "Esportes",
    "Praia",
    "Eventos",
    "Shopping/Centro Comercial",
    "Praças/Parques públicos",
    "Pontos turísticos",
    "Ação Social",
    "Ação conjunta com a fiscalização",
    "Outros",
]


class PublicAgendaRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    description = serializers.CharField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    time_2 = serializers.TimeField(required=False, allow_null=True)
    time_3 = serializers.TimeField(required=False, allow_null=True)
    action_type = serializers.CharField(max_length=160)
    def validate_action_type(self, value):
        cleaned = str(value or "").strip()
        normalized = normalize_action_choice(cleaned)
        allowed = {
            normalize_action_choice(option)
            for option in [
                "Palestra",
                "Acao de educacao conscientizacao",
                "Palestra Empresa",
                "Palestra Escola",
                "Palestra Virtual",
                "Acao educativa espaco interno",
                "Palestra bilingue ingles",
                "Bares",
                "Pedagio",
                "Esportes",
                "Praia",
                "Eventos",
                "Shopping centro comercial",
                "Pracas parques publicos",
                "Pontos turisticos",
                "Acao Social",
                "Acao conjunta com a fiscalizacao",
                "Outros",
                "Praças Esportivas",
                "Shopping/Centro Comerciais",
                "Praças/Parques Públicos",
            ]
        }
        if normalized not in allowed:
            raise serializers.ValidationError("Informe um tipo de ação válido.")
        return cleaned

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
    administrative_demand_type = serializers.ChoiceField(choices=[choice for choice, _label in Agenda.AdministrativeDemandType.choices], required=False, allow_blank=True)
    audience = serializers.CharField(max_length=160, required=False, allow_blank=True)
    participant_range = serializers.ChoiceField(
        choices=["30 a 50", "51 a 100", "100 a 200"], required=False, allow_blank=True
    )
    age_ranges = serializers.ChoiceField(
        choices=PUBLIC_AGE_RANGE_CHOICES + LEGACY_PUBLIC_AGE_RANGE_CHOICES, required=False, allow_blank=True
    )
    accessibility_access = serializers.ChoiceField(
        choices=["Sim", "Não", "Não se aplica, pois será realizado no térreo"], required=False, allow_blank=True
    )
    has_ramps = serializers.ChoiceField(choices=["Sim", "Não"], required=False, allow_blank=True)
    has_elevators = serializers.ChoiceField(choices=["Sim", "Não"], required=False, allow_blank=True)
    has_accessible_bathrooms = serializers.ChoiceField(choices=["Sim", "Não"], required=False, allow_blank=True)
    media_equipment = serializers.CharField(required=False, allow_blank=True)
    image_authorization = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["start_time"] == attrs["end_time"]:
            raise serializers.ValidationError("A hora final nÃ£o pode ser igual Ã  hora inicial.")

        is_internal_request = bool(self.context.get("is_internal_request"))
        requester_entity_type = str(attrs.get("requester_entity_type", "") or "")
        administrative_demand_type = str(attrs.get("administrative_demand_type", "") or "")
        if is_internal_request:
            valid_subtypes = {choice for choice, _label in Agenda.AdministrativeDemandType.choices}
            if requester_entity_type == "Demanda Administrativa":
                if not administrative_demand_type:
                    raise serializers.ValidationError({"administrative_demand_type": "Informe o tipo de demanda administrativa."})
                if administrative_demand_type not in valid_subtypes:
                    raise serializers.ValidationError({"administrative_demand_type": "Informe o tipo de demanda administrativa vÃ¡lido."})
            else:
                attrs["administrative_demand_type"] = ""
        else:
            attrs["administrative_demand_type"] = ""

        date = attrs.get("date")
        if not is_internal_request and date:
            block = ExternalRequestDateBlock.objects.filter(
                is_active=True, start_date__lte=date, end_date__gte=date
            ).order_by("start_date", "end_date", "id").first()
            if block:
                raise serializers.ValidationError({"date": external_request_date_block_message(block)})
        if date:
            agenda_id = self.context.get("agenda_id")
            qs = Agenda.objects.filter(
                date=date,
                status__in=[Agenda.Status.PENDING, Agenda.Status.APPROVED]
            )
            if agenda_id:
                qs = qs.exclude(id=agenda_id)

        return attrs


class PublicAgendaRequestRescheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    actions_count = serializers.IntegerField(min_value=1, max_value=3, required=False, allow_null=True)
    time_2 = serializers.TimeField(required=False, allow_null=True)
    time_3 = serializers.TimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["start_time"] == attrs["end_time"]:
            raise serializers.ValidationError("A hora final não pode ser igual à hora inicial.")
            
        date = attrs.get("date")
        original_date = self.context.get("original_date")
        if date and date != original_date:
            block = ExternalRequestDateBlock.objects.filter(
                is_active=True, start_date__lte=date, end_date__gte=date
            ).order_by("start_date", "end_date", "id").first()
            if block:
                raise serializers.ValidationError({"date": external_request_date_block_message(block)})
        if date:
            agenda_id = self.context.get("agenda_id")
            qs = Agenda.objects.filter(
                date=date,
                status__in=[Agenda.Status.PENDING, Agenda.Status.APPROVED]
            )
            if agenda_id:
                qs = qs.exclude(id=agenda_id)

        return attrs


class SatisfactionSurveyModerationHistorySerializer(serializers.ModelSerializer):
    decided_by_name = serializers.CharField(source="decided_by.full_name", read_only=True)

    class Meta:
        model = SatisfactionSurveyModerationHistory
        fields = [
            "id",
            "previous_status",
            "new_status",
            "comment_snapshot",
            "decided_at",
            "decided_by",
            "decided_by_name",
        ]


class SatisfactionSurveySerializer(serializers.ModelSerializer):
    protocol = serializers.IntegerField(source="agenda_id", read_only=True)
    agenda_title = serializers.CharField(source="agenda.title", read_only=True)
    agenda_date = serializers.DateField(source="agenda.date", read_only=True)
    institution = serializers.CharField(source="agenda.location", read_only=True)
    municipality = serializers.SerializerMethodField()
    state = serializers.CharField(source="agenda.state", read_only=True)
    moderation_status_label = serializers.CharField(source="get_moderation_status_display", read_only=True)
    moderated_by_name = serializers.CharField(source="moderated_by.full_name", read_only=True)
    display_comment = serializers.SerializerMethodField()
    moderation_history = SatisfactionSurveyModerationHistorySerializer(many=True, read_only=True)

    class Meta:
        model = SatisfactionSurvey
        fields = [
            "id",
            "protocol",
            "agenda_title",
            "agenda_date",
            "institution",
            "municipality",
            "state",
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
            "display_comment",
            "is_approved",
            "moderation_status",
            "moderation_status_label",
            "moderated_comment",
            "moderated_at",
            "moderated_by",
            "moderated_by_name",
            "moderation_history",
            "answered_at",
        ]
        read_only_fields = [
            "id",
            "protocol",
            "agenda_title",
            "agenda_date",
            "institution",
            "municipality",
            "state",
            "team",
            "chief_name",
            "display_comment",
            "is_approved",
            "moderation_status",
            "moderation_status_label",
            "moderated_at",
            "moderated_by",
            "moderated_by_name",
            "moderation_history",
            "answered_at",
        ]

    def get_display_comment(self, obj):
        return obj.moderated_comment or obj.suggestion

    def get_municipality(self, obj):
        agenda = getattr(obj, "agenda", None)
        if not agenda:
            return ""
        try:
            municipality = agenda.municipality_ref
        except Municipality.DoesNotExist:
            municipality = None
        return municipality.name if municipality else (agenda.city or "")


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
            if value is None or value < 1 or value > 10:
                raise serializers.ValidationError({field: "Informe uma nota de 1 a 10."})
        return attrs
