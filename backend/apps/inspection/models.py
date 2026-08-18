from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class InspectionRegion(models.Model):
    code = models.CharField(max_length=40, unique=True, db_index=True)
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Regiao da Fiscalizacao"
        verbose_name_plural = "Regioes da Fiscalizacao"

    def __str__(self):
        return self.name


class InspectionMunicipality(models.Model):
    region = models.ForeignKey(
        InspectionRegion,
        on_delete=models.PROTECT,
        related_name="municipalities",
    )
    name = models.CharField(max_length=120, unique=True, db_index=True)
    normalized_name = models.CharField(max_length=120, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Municipio da Fiscalizacao"
        verbose_name_plural = "Municipios da Fiscalizacao"
        indexes = [
            models.Index(fields=["region", "name"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.region.name}"


class InspectionReport(models.Model):
    class ReportStatus(models.TextChoices):
        SYNCED = "SYNCED", "Sincronizado"
        PENDING_REVIEW = "PENDING_REVIEW", "Aguardando revisao"
        APPROVED = "APPROVED", "Aprovado"
        RETURNED = "RETURNED", "Devolvido"

    class StatisticsStatus(models.TextChoices):
        PENDING = "PENDING", "Aguardando analise"
        INCLUDED = "INCLUDED", "Incluido na estatistica"
        EXCLUDED = "EXCLUDED", "Nao incluido na estatistica"

    source_id = models.UUIDField(unique=True, db_index=True)
    source_created_at = models.DateTimeField()
    source_updated_at = models.DateTimeField()
    synced_at = models.DateTimeField()

    operation_date = models.DateField()
    team = models.CharField(max_length=120, blank=True)
    management_id = models.IntegerField(null=True, blank=True)
    military_chief_source_id = models.UUIDField(null=True, blank=True)
    segov_team_civil = models.CharField(max_length=255, blank=True)
    segov_team_military = models.CharField(max_length=255, blank=True)
    change_ols = models.TextField(blank=True)
    agent_detran = models.IntegerField(null=True, blank=True)
    number_trailers = models.IntegerField(null=True, blank=True)
    change_support = models.TextField(blank=True)
    cars = models.CharField(max_length=255, blank=True)
    changes_general = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.SYNCED,
        db_index=True,
    )
    statistics_status = models.CharField(
        max_length=16,
        choices=StatisticsStatus.choices,
        default=StatisticsStatus.PENDING,
        db_index=True,
    )
    statistics_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspection_statistics_reviews",
    )
    statistics_reviewed_at = models.DateTimeField(null=True, blank=True)
    statistics_exclusion_reason = models.TextField(blank=True)
    statistics_snapshot = models.JSONField(null=True, blank=True)
    statistics_classification = models.JSONField(default=dict, blank=True)
    has_source_update_after_statistics_review = models.BooleanField(default=False)
    source_update_after_statistics_review_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-operation_date", "-created_at"]
        indexes = [
            models.Index(fields=["operation_date", "team"]),
            models.Index(fields=["status", "operation_date"]),
            models.Index(fields=["statistics_status", "operation_date"]),
        ]

    def __str__(self):
        return f"{self.team} - {self.operation_date}"


class InspectionReportOperation(models.Model):
    report = models.ForeignKey(
        InspectionReport,
        on_delete=models.CASCADE,
        related_name="operations",
    )
    source_id = models.UUIDField(unique=True, db_index=True)
    source_created_at = models.DateTimeField()
    source_updated_at = models.DateTimeField()

    address_operation = models.CharField(max_length=255, blank=True)
    locality = models.CharField(max_length=255, blank=True)
    another_not_listed = models.CharField(max_length=255, blank=True)
    departure_meeting_point = models.CharField(max_length=255, blank=True)
    operation_assembly = models.CharField(max_length=255, blank=True)
    first_approach = models.CharField(max_length=255, blank=True)
    closing = models.CharField(max_length=255, blank=True)
    approach = models.IntegerField(null=True, blank=True)
    reconductor = models.IntegerField(null=True, blank=True)
    refusal = models.IntegerField(null=True, blank=True)
    celebrities_authorities = models.IntegerField(null=True, blank=True)
    four_ml = models.IntegerField(null=True, blank=True)
    thirtythree_ml = models.IntegerField(null=True, blank=True)
    thirtyfour_ml = models.IntegerField(null=True, blank=True)
    passive_tests_performed = models.IntegerField(null=True, blank=True)
    changes_material = models.TextField(blank=True)
    cnh_collected = models.IntegerField(null=True, blank=True)
    fined = models.IntegerField(null=True, blank=True)
    towed = models.IntegerField(null=True, blank=True)
    removal_resolutions = models.IntegerField(null=True, blank=True)
    arrests_means_evidence = models.IntegerField(null=True, blank=True)
    art307 = models.IntegerField(null=True, blank=True)
    criminal_occurrences = models.IntegerField(null=True, blank=True)
    driving_canceled_license = models.IntegerField(null=True, blank=True)
    vehicle_resolutions = models.TextField(blank=True)
    administrative_tests = models.TextField(blank=True)
    cep = models.CharField(max_length=32, blank=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.address_operation or str(self.source_id)


class InspectionFine(models.Model):
    operation = models.ForeignKey(
        InspectionReportOperation,
        on_delete=models.CASCADE,
        related_name="fines",
    )
    source_id = models.IntegerField(unique=True, db_index=True)
    art = models.CharField(max_length=120, blank=True)
    quant = models.IntegerField(null=True, blank=True)
    source_created_at = models.DateTimeField()
    source_updated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.art or 'Infracao'} ({self.source_id})"


class InspectionReportStatusHistory(models.Model):
    report = models.ForeignKey(
        InspectionReport,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    old_status = models.CharField(
        max_length=20,
        choices=InspectionReport.ReportStatus.choices,
        null=True,
        blank=True,
    )
    new_status = models.CharField(
        max_length=20,
        choices=InspectionReport.ReportStatus.choices,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspection_report_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.report_id}: {self.old_status} -> {self.new_status}"


class InspectionStatisticsDecisionHistory(models.Model):
    report = models.ForeignKey(
        InspectionReport,
        on_delete=models.CASCADE,
        related_name="statistics_history",
    )
    old_status = models.CharField(
        max_length=16,
        choices=InspectionReport.StatisticsStatus.choices,
        null=True,
        blank=True,
    )
    new_status = models.CharField(
        max_length=16,
        choices=InspectionReport.StatisticsStatus.choices,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspection_statistics_decision_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.report_id}: {self.old_status} -> {self.new_status}"


class InspectionStatistic(models.Model):
    class StatisticSource(models.TextChoices):
        REPORT = "REPORT", "Relatorio"

    report = models.OneToOneField(
        InspectionReport,
        on_delete=models.CASCADE,
        related_name="official_statistic",
    )
    source_report_id = models.UUIDField(db_index=True)
    operation_date = models.DateField(db_index=True)
    team = models.CharField(max_length=120, blank=True, db_index=True)
    snapshot_source_updated_at = models.DateTimeField()
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_inspection_statistics",
    )
    source = models.CharField(
        max_length=16,
        choices=StatisticSource.choices,
        default=StatisticSource.REPORT,
        db_index=True,
    )

    operations_count = models.IntegerField()
    approach = models.IntegerField(null=True, blank=True)
    reconductor = models.IntegerField(null=True, blank=True)
    refusal = models.IntegerField(null=True, blank=True)
    celebrities_authorities = models.IntegerField(null=True, blank=True)
    four_ml = models.IntegerField(null=True, blank=True)
    thirtythree_ml = models.IntegerField(null=True, blank=True)
    thirtyfour_ml = models.IntegerField(null=True, blank=True)
    passive_tests_performed = models.IntegerField(null=True, blank=True)
    cnh_collected = models.IntegerField(null=True, blank=True)
    fined = models.IntegerField(null=True, blank=True)
    towed = models.IntegerField(null=True, blank=True)
    removal_resolutions = models.IntegerField(null=True, blank=True)
    arrests_means_evidence = models.IntegerField(null=True, blank=True)
    art307 = models.IntegerField(null=True, blank=True)
    criminal_occurrences = models.IntegerField(null=True, blank=True)
    driving_canceled_license = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-operation_date", "-generated_at"]
        indexes = [
            models.Index(fields=["operation_date", "team"]),
            models.Index(fields=["source", "operation_date"]),
        ]

    def __str__(self):
        return f"Estatistica oficial {self.team} - {self.operation_date}"


class InspectionPublicSecurityYearlyStatistic(models.Model):
    reference_year = models.PositiveSmallIntegerField(
        unique=True,
        db_index=True,
    )

    # Seguranca Publica / Criminal
    fugitives = models.IntegerField(null=True, blank=True)
    flagrante = models.IntegerField(null=True, blank=True)
    simulacrum = models.IntegerField(null=True, blank=True)
    weapons = models.IntegerField(null=True, blank=True)
    recovered_vehicles = models.IntegerField(null=True, blank=True)
    narcotics = models.IntegerField(null=True, blank=True)
    bribery = models.IntegerField(null=True, blank=True)
    art311 = models.IntegerField(null=True, blank=True)
    art306 = models.IntegerField(null=True, blank=True)

    # Motorista / CNH
    fake_cnh = models.IntegerField(null=True, blank=True)
    suspended_cnh = models.IntegerField(null=True, blank=True)
    canceled_cnh = models.IntegerField(null=True, blank=True)

    source_label = models.CharField(
        max_length=255,
        blank=True,
        default="Serie historica de ocorrencias",
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["reference_year"]
        verbose_name = "Estatistica anual de seguranca publica"
        verbose_name_plural = "Estatisticas anuais de seguranca publica"

    def __str__(self):
        return f"Seguranca Publica - {self.reference_year}"


HISTORICAL_CUTOFF_DATE = date(2026, 8, 9)
INSPECTION_STATISTICS_CUTOFF_DATE = HISTORICAL_CUTOFF_DATE + timedelta(days=1)


class HistoricalSourceType(models.TextChoices):
    DAILY = "DAILY", "Diario"
    ACCUMULATED = "ACCUMULATED", "Acumulado"
    LEGACY = "LEGACY", "Legado"


class HistoricalTaxonomyEra(models.TextChoices):
    ERA_A = "ERA_A", "Era A"
    ERA_B = "ERA_B", "Era B"
    ERA_C = "ERA_C", "Era C"


class InspectionHistoricalImportBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        COMPLETED = "COMPLETED", "Concluido"
        FAILED = "FAILED", "Falhou"
        PARTIAL = "PARTIAL", "Parcial"

    source_file_name = models.CharField(max_length=255)
    source_file_sha256 = models.CharField(max_length=64, db_index=True)
    source_type = models.CharField(
        max_length=16,
        choices=HistoricalSourceType.choices,
        null=True,
        blank=True,
    )
    taxonomy_era = models.CharField(
        max_length=16,
        choices=HistoricalTaxonomyEra.choices,
        null=True,
        blank=True,
    )
    source_file_size = models.BigIntegerField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspection_historical_import_batches",
    )
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    rows_found = models.IntegerField(default=0)
    rows_valid = models.IntegerField(default=0)
    rows_imported = models.IntegerField(default=0)
    rows_ignored = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)
    warnings_count = models.IntegerField(default=0)
    report_json = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_file_sha256", "source_type", "taxonomy_era"],
                name="uniq_inspection_historical_batch_file_phase",
            )
        ]

    def __str__(self):
        return f"Lote historico {self.source_file_name} ({self.status})"


class InspectionHistoricalStatistic(models.Model):
    reference_date = models.DateField(null=True, blank=True, db_index=True)
    reference_year = models.PositiveSmallIntegerField(null=True, blank=True)
    reference_month = models.PositiveSmallIntegerField(null=True, blank=True)
    team = models.CharField(max_length=120, blank=True, db_index=True)
    source_team_label = models.CharField(max_length=160, blank=True)
    source_type = models.CharField(
        max_length=16,
        choices=HistoricalSourceType.choices,
        db_index=True,
    )
    source_sheet = models.CharField(max_length=120)
    source_row = models.PositiveIntegerField()
    taxonomy_era = models.CharField(
        max_length=16,
        choices=HistoricalTaxonomyEra.choices,
        db_index=True,
    )
    import_batch = models.ForeignKey(
        InspectionHistoricalImportBatch,
        on_delete=models.CASCADE,
        related_name="statistics",
    )

    source_workbook_label = models.CharField(max_length=255, blank=True)
    is_validation_only = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    fined = models.IntegerField(null=True, blank=True)
    towed = models.IntegerField(null=True, blank=True)
    refusal = models.IntegerField(null=True, blank=True)
    cnh_collected = models.IntegerField(null=True, blank=True)
    four_ml = models.IntegerField(null=True, blank=True)
    thirtythree_ml = models.IntegerField(null=True, blank=True)
    thirtyfour_ml = models.IntegerField(null=True, blank=True)
    arrests_means_evidence = models.IntegerField(null=True, blank=True)
    passive_tests_performed = models.IntegerField(null=True, blank=True)
    reconductor = models.IntegerField(null=True, blank=True)
    operations_count = models.IntegerField(null=True, blank=True)
    removal_resolutions = models.IntegerField(null=True, blank=True)
    driving_canceled_license = models.IntegerField(null=True, blank=True)
    criminal_occurrences = models.IntegerField(null=True, blank=True)

    taxi_approached = models.IntegerField(null=True, blank=True)
    taxi_illegal = models.IntegerField(null=True, blank=True)
    planned_actions = models.IntegerField(null=True, blank=True)
    rain = models.IntegerField(null=True, blank=True)
    external_occurrence = models.IntegerField(null=True, blank=True)
    public_security_occurrence = models.IntegerField(null=True, blank=True)
    license_suspension = models.IntegerField(null=True, blank=True)
    negative_tests = models.IntegerField(null=True, blank=True)
    administrative_art_165 = models.IntegerField(null=True, blank=True)
    criminal_art_306 = models.IntegerField(null=True, blank=True)
    criminal_art_306_other_evidence = models.IntegerField(null=True, blank=True)
    historical_alcohol_cases = models.IntegerField(null=True, blank=True)
    historical_alcohol_percentage = models.DecimalField(
        max_digits=12,
        decimal_places=10,
        null=True,
        blank=True,
    )
    historical_event_trailers = models.IntegerField(null=True, blank=True)

    historical_reconductors_licensed = models.IntegerField(null=True, blank=True)
    historical_deliberations = models.IntegerField(null=True, blank=True)
    historical_operations = models.IntegerField(null=True, blank=True)
    historical_cnh_retained = models.IntegerField(null=True, blank=True)
    historical_passive_tests = models.IntegerField(null=True, blank=True)

    historical_approached = models.IntegerField(null=True, blank=True)
    historical_art_307 = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "-reference_date",
            "-reference_year",
            "-reference_month",
            "team",
            "source_sheet",
            "source_row",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["import_batch", "source_sheet", "source_row"],
                name="uniq_inspection_historical_batch_sheet_row",
            ),
            models.CheckConstraint(
                check=models.Q(reference_date__isnull=True)
                | models.Q(reference_date__lte=HISTORICAL_CUTOFF_DATE),
                name="inspection_historical_reference_date_cutoff",
            ),
        ]
        indexes = [
            models.Index(fields=["reference_date", "team"]),
            models.Index(fields=["reference_year", "reference_month"]),
            models.Index(fields=["source_type", "taxonomy_era"]),
            models.Index(fields=["import_batch"]),
        ]

    def clean(self):
        if self.reference_date and self.reference_date > HISTORICAL_CUTOFF_DATE:
            raise ValidationError(
                {
                    "reference_date": (
                        "Dados historicos de Fiscalizacao nao podem ultrapassar "
                        "2026-08-09."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        reference = (
            self.reference_date.isoformat()
            if self.reference_date
            else f"{self.reference_year}-{self.reference_month}"
        )
        return f"Historico {self.team or self.source_team_label} - {reference}"