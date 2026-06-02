from rest_framework import serializers

from .models import (
    ActionType,
    Agent,
    Agenda,
    AgendaHistory,
    AgendaMaterial,
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


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "name", "description", "is_active"]


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
    military_team_names = {
        "ALFA",
        "BRAVO",
        "CHARLIE",
        "DELTA",
        "ECHO",
        "FOX",
        "GOLF",
        "HOTEL",
    }

    class Meta(LookupSerializer.Meta):
        model = Team

    def validate_name(self, value):
        normalized = value.strip().upper()
        allowed = {name.casefold(): name for name in self.military_team_names}
        if normalized.casefold() not in allowed:
            raise serializers.ValidationError("Use uma equipe padronizada: ALFA, BRAVO, CHARLIE, DELTA, ECHO, FOX, GOLF ou HOTEL.")
        return allowed[normalized.casefold()]


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


class MaterialSerializer(LookupSerializer):
    class Meta(LookupSerializer.Meta):
        model = Material


class ChiefSerializer(LookupSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta(LookupSerializer.Meta):
        model = Chief
        fields = ["id", "source_id", "name", "cpf", "team", "team_name", "role", "address", "phone", "is_active"]


class AgendaHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True)

    class Meta:
        model = AgendaHistory
        fields = ["id", "agenda", "changed_by_name", "action", "snapshot", "created_at"]


class AgendaMaterialSerializer(serializers.ModelSerializer):
    kit_name = serializers.CharField(source="kit.name", read_only=True)
    material_name = serializers.CharField(source="material.name", read_only=True)

    class Meta:
        model = AgendaMaterial
        fields = ["id", "position", "kit", "kit_name", "material", "material_name", "quantity"]


class AgendaSerializer(serializers.ModelSerializer):
    responsible_name = serializers.CharField(source="responsible.full_name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    history = AgendaHistorySerializer(many=True, read_only=True)
    materials = AgendaMaterialSerializer(many=True, read_only=True)
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
        read_only_fields = ["created_by", "created_at", "updated_at", "history", "materials"]

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
            if candidate.overlaps_queryset().exists():
                raise serializers.ValidationError(
                    "Existe conflito de horário para o mesmo responsável ou local."
                )
        return attrs

    def get_satisfaction_survey_token(self, obj):
        survey = obj.satisfaction_surveys.order_by("-created_at").first()
        return survey.token if survey else ""

    def get_satisfaction_survey_answered_at(self, obj):
        survey = obj.satisfaction_surveys.order_by("-created_at").first()
        return survey.answered_at if survey else None


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
            "breathalyzers",
            "cars",
            "changes_general",
            "contact_received",
            "occurrence_observation",
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
        ]

    def validate_source_id(self, value):
        return value or None

    def get_actions_count(self, obj):
        return obj.actions.count()

    def validate(self, attrs):
        instance = self.instance
        agenda = attrs.get("agenda", getattr(instance, "agenda", None))
        if not agenda:
            raise serializers.ValidationError("Informe o protocolo da solicitação.")
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
            "Ação educativa (Espaço interno)",
            "Palestra Virtual",
            "Palestra Presencial",
            "Campanha educativa/conscientização",
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
    age_ranges = serializers.CharField(max_length=220, required=False, allow_blank=True)
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
