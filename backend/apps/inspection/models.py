from django.conf import settings
from django.db import models


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
