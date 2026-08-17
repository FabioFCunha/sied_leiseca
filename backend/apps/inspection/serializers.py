from rest_framework import serializers

from apps.inspection.models import (
    InspectionFine,
    InspectionReport,
    InspectionReportOperation,
    InspectionStatisticsDecisionHistory,
)


class InspectionFineIngestionSerializer(serializers.Serializer):
    source_id = serializers.IntegerField()
    art = serializers.CharField(required=False, allow_blank=True, default="")
    quant = serializers.IntegerField(required=False, allow_null=True, default=None)
    source_created_at = serializers.DateTimeField()
    source_updated_at = serializers.DateTimeField()


class InspectionOperationIngestionSerializer(serializers.Serializer):
    source_id = serializers.UUIDField()
    source_created_at = serializers.DateTimeField()
    source_updated_at = serializers.DateTimeField()

    address_operation = serializers.CharField(required=False, allow_blank=True, default="")
    locality = serializers.CharField(required=False, allow_blank=True, default="")
    another_not_listed = serializers.CharField(required=False, allow_blank=True, default="")
    departure_meeting_point = serializers.CharField(required=False, allow_blank=True, default="")
    operation_assembly = serializers.CharField(required=False, allow_blank=True, default="")
    first_approach = serializers.CharField(required=False, allow_blank=True, default="")
    closing = serializers.CharField(required=False, allow_blank=True, default="")

    approach = serializers.IntegerField(required=False, allow_null=True, default=None)
    reconductor = serializers.IntegerField(required=False, allow_null=True, default=None)
    refusal = serializers.IntegerField(required=False, allow_null=True, default=None)
    celebrities_authorities = serializers.IntegerField(required=False, allow_null=True, default=None)
    four_ml = serializers.IntegerField(required=False, allow_null=True, default=None)
    thirtythree_ml = serializers.IntegerField(required=False, allow_null=True, default=None)
    thirtyfour_ml = serializers.IntegerField(required=False, allow_null=True, default=None)
    passive_tests_performed = serializers.IntegerField(required=False, allow_null=True, default=None)
    changes_material = serializers.CharField(required=False, allow_blank=True, default="")
    cnh_collected = serializers.IntegerField(required=False, allow_null=True, default=None)
    fined = serializers.IntegerField(required=False, allow_null=True, default=None)
    towed = serializers.IntegerField(required=False, allow_null=True, default=None)
    removal_resolutions = serializers.IntegerField(required=False, allow_null=True, default=None)
    arrests_means_evidence = serializers.IntegerField(required=False, allow_null=True, default=None)
    art307 = serializers.IntegerField(required=False, allow_null=True, default=None)
    criminal_occurrences = serializers.IntegerField(required=False, allow_null=True, default=None)
    driving_canceled_license = serializers.IntegerField(required=False, allow_null=True, default=None)
    vehicle_resolutions = serializers.CharField(required=False, allow_blank=True, default="")
    administrative_tests = serializers.CharField(required=False, allow_blank=True, default="")
    cep = serializers.CharField(required=False, allow_blank=True, default="")
    street = serializers.CharField(required=False, allow_blank=True, default="")
    city = serializers.CharField(required=False, allow_blank=True, default="")
    district = serializers.CharField(required=False, allow_blank=True, default="")
    number = serializers.CharField(required=False, allow_blank=True, default="")

    fines = InspectionFineIngestionSerializer(many=True, required=False, default=list)


class InspectionReportIngestionSerializer(serializers.Serializer):
    source_id = serializers.UUIDField()
    source_created_at = serializers.DateTimeField()
    source_updated_at = serializers.DateTimeField()
    operation_date = serializers.DateField()
    team = serializers.CharField(required=False, allow_blank=True, default="")
    management_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    military_chief_source_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    segov_team_civil = serializers.CharField(required=False, allow_blank=True, default="")
    segov_team_military = serializers.CharField(required=False, allow_blank=True, default="")
    change_ols = serializers.CharField(required=False, allow_blank=True, default="")
    agent_detran = serializers.IntegerField(required=False, allow_null=True, default=None)
    number_trailers = serializers.IntegerField(required=False, allow_null=True, default=None)
    change_support = serializers.CharField(required=False, allow_blank=True, default="")
    cars = serializers.CharField(required=False, allow_blank=True, default="")
    changes_general = serializers.CharField(required=False, allow_blank=True, default="")
    operations = InspectionOperationIngestionSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        if "status" in self.initial_data:
            raise serializers.ValidationError(
                {"status": "O status humano do relatorio nao pode ser definido pela ingestao externa."}
            )
        if "statistics_status" in self.initial_data:
            raise serializers.ValidationError(
                {"statistics_status": "A decisao estatistica nao pode ser definida pela ingestao externa."}
            )
        return attrs


class InspectionStatisticsClassificationSerializer(serializers.Serializer):
    fugitives = serializers.BooleanField(default=False)
    flagrante = serializers.BooleanField(default=False)
    simulacrum = serializers.BooleanField(default=False)
    weapons = serializers.BooleanField(default=False)
    recovered_vehicles = serializers.BooleanField(default=False)
    stolen_vehicles = serializers.BooleanField(default=False)
    robbed_vehicles = serializers.BooleanField(default=False)
    narcotics = serializers.BooleanField(default=False)
    bribery = serializers.BooleanField(default=False)
    art311 = serializers.BooleanField(default=False)
    art306 = serializers.BooleanField(default=False)
    rain = serializers.BooleanField(default=False)


class InspectionIncludeStatisticsSerializer(serializers.Serializer):
    classification = InspectionStatisticsClassificationSerializer()


class InspectionExcludeStatisticsSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)


class InspectionStatisticsDashboardQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    team = serializers.CharField(required=False, allow_blank=False, trim_whitespace=True)

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError({"date_to": "date_to deve ser maior ou igual a date_from."})
        return attrs


class InspectionReviewerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()


class InspectionFineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionFine
        fields = [
            "source_id",
            "art",
            "quant",
            "source_created_at",
            "source_updated_at",
        ]


class InspectionReportOperationSerializer(serializers.ModelSerializer):
    fines = InspectionFineSerializer(many=True, read_only=True)

    class Meta:
        model = InspectionReportOperation
        fields = [
            "source_id",
            "address_operation",
            "locality",
            "another_not_listed",
            "departure_meeting_point",
            "operation_assembly",
            "first_approach",
            "closing",
            "approach",
            "reconductor",
            "refusal",
            "celebrities_authorities",
            "four_ml",
            "thirtythree_ml",
            "thirtyfour_ml",
            "passive_tests_performed",
            "changes_material",
            "cnh_collected",
            "fined",
            "towed",
            "removal_resolutions",
            "arrests_means_evidence",
            "art307",
            "criminal_occurrences",
            "driving_canceled_license",
            "vehicle_resolutions",
            "administrative_tests",
            "cep",
            "street",
            "city",
            "district",
            "number",
            "source_created_at",
            "source_updated_at",
            "fines",
        ]


class InspectionStatisticsDecisionHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True)

    class Meta:
        model = InspectionStatisticsDecisionHistory
        fields = [
            "id",
            "old_status",
            "new_status",
            "changed_by",
            "changed_by_name",
            "changed_at",
            "notes",
        ]


class InspectionReportListSerializer(serializers.ModelSerializer):
    operation_count = serializers.IntegerField(read_only=True)
    total_approach = serializers.IntegerField(read_only=True)
    total_refusal = serializers.IntegerField(read_only=True)
    total_fined = serializers.IntegerField(read_only=True)
    statistics_reviewed_by_name = serializers.CharField(source="statistics_reviewed_by.full_name", read_only=True)

    class Meta:
        model = InspectionReport
        fields = [
            "id",
            "source_id",
            "operation_date",
            "team",
            "status",
            "statistics_status",
            "statistics_reviewed_at",
            "statistics_reviewed_by_name",
            "has_source_update_after_statistics_review",
            "synced_at",
            "source_updated_at",
            "operation_count",
            "total_approach",
            "total_refusal",
            "total_fined",
            "created_at",
            "updated_at",
        ]


class InspectionHistoricalPushSerializer(serializers.Serializer):
    """
    Serializer para o endpoint POST /api/inspection/sync/historical/push/

    Recebe um único registro do array ``rows`` do JSON exportado do Horus,
    mais o SHA-256 do arquivo de extração para rastreabilidade do lote.
    """

    # Identificação do lote (rastreabilidade)
    file_sha256 = serializers.CharField(
        min_length=64,
        max_length=64,
        help_text=(
            "SHA-256 do arquivo JSON exportado do Horus. "
            "Identifica o lote de origem para rastreabilidade."
        ),
    )

    # Metadados de controle obrigatórios
    source_type = serializers.ChoiceField(choices=["DAILY"])
    taxonomy_era = serializers.ChoiceField(choices=["ERA_C"])
    reference_date = serializers.DateField()
    team = serializers.CharField(allow_blank=False, trim_whitespace=True)

    # Rastreabilidade interna
    source_row = serializers.IntegerField(required=False, allow_null=True, default=0)

    # Contadores de relatórios/operações
    reports_count = serializers.IntegerField(required=False, allow_null=True, default=None)
    operations_count = serializers.IntegerField(required=False, allow_null=True, default=None)

    # Campos de abordagem (regra ERA_C)
    approach = serializers.IntegerField(required=False, allow_null=True, default=None)
    reconductor = serializers.IntegerField(required=False, allow_null=True, default=None)

    # Demais campos numéricos
    refusal = serializers.IntegerField(required=False, allow_null=True, default=None)
    fined = serializers.IntegerField(required=False, allow_null=True, default=None)
    towed = serializers.IntegerField(required=False, allow_null=True, default=None)
    cnh_collected = serializers.IntegerField(required=False, allow_null=True, default=None)
    four_ml = serializers.IntegerField(required=False, allow_null=True, default=None)
    thirtythree_ml = serializers.IntegerField(required=False, allow_null=True, default=None)
    thirtyfour_ml = serializers.IntegerField(required=False, allow_null=True, default=None)
    passive_tests_performed = serializers.IntegerField(required=False, allow_null=True, default=None)
    removal_resolutions = serializers.IntegerField(required=False, allow_null=True, default=None)
    arrests_means_evidence = serializers.IntegerField(required=False, allow_null=True, default=None)
    art307 = serializers.IntegerField(required=False, allow_null=True, default=None)
    criminal_occurrences = serializers.IntegerField(required=False, allow_null=True, default=None)
    driving_canceled_license = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_team(self, value):
        normalized = str(value or "").strip().upper()
        if not normalized:
            raise serializers.ValidationError("team não pode ser vazio.")
        return normalized

    def validate_file_sha256(self, value):
        import re
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise serializers.ValidationError(
                "file_sha256 deve ser um hexadecimal de 64 caracteres (SHA-256)."
            )
        return value.lower()


class InspectionReportDetailSerializer(serializers.ModelSerializer):
    operations = InspectionReportOperationSerializer(many=True, read_only=True)
    statistics_reviewed_by_name = serializers.CharField(source="statistics_reviewed_by.full_name", read_only=True)
    statistics_history = InspectionStatisticsDecisionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = InspectionReport
        fields = [
            "id",
            "source_id",
            "operation_date",
            "team",
            "management_id",
            "military_chief_source_id",
            "segov_team_civil",
            "segov_team_military",
            "change_ols",
            "agent_detran",
            "number_trailers",
            "change_support",
            "cars",
            "changes_general",
            "status",
            "statistics_status",
            "statistics_reviewed_by",
            "statistics_reviewed_by_name",
            "statistics_reviewed_at",
            "statistics_exclusion_reason",
            "statistics_snapshot",
            "has_source_update_after_statistics_review",
            "source_update_after_statistics_review_at",
            "source_created_at",
            "source_updated_at",
            "synced_at",
            "created_at",
            "updated_at",
            "operations",
            "statistics_history",
        ]
