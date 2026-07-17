from django.conf import settings
from django.db import models
from django.db import transaction
from django.db.models import Max, Q
from django.contrib.postgres.indexes import GinIndex


class Sector(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class NamedLookup(models.Model):
    source_id = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=180, unique=True)
    is_active = models.BooleanField(default=True)
    vacation_start = models.DateField(null=True, blank=True)
    vacation_end = models.DateField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vehicle(NamedLookup):
    pass


class Team(NamedLookup):
    pass


class UserTeamTransfer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_transfers")
    old_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="transfers_out")
    new_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="transfers_in")
    effective_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_team_transfers")

    class Meta:
        ordering = ["-effective_date", "-created_at"]

    def __str__(self):
        return f"{self.user} from {self.old_team} to {self.new_team} on {self.effective_date}"


class Support(NamedLookup):
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="supports")
    role = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=220, blank=True)


class Agent(NamedLookup):
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="agents")
    role = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=220, blank=True)


class ActionType(NamedLookup):
    pass


class Region(NamedLookup):
    pass


class Municipality(NamedLookup):
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name="municipalities")


class Neighborhood(NamedLookup):
    pass


class Kit(NamedLookup):
    class Meta(NamedLookup.Meta):
        verbose_name = "Kit"
        verbose_name_plural = "Kits"


class Dynamic(NamedLookup):
    materials = models.TextField(blank=True, default="")

    class Meta(NamedLookup.Meta):
        verbose_name = "Dinâmica"
        verbose_name_plural = "Dinâmicas"


class Material(NamedLookup):
    pass


class Chief(NamedLookup):
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="chiefs")
    role = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=220, blank=True)
    phone = models.CharField(max_length=160, blank=True)


class ShiftSchedule(models.Model):
    date = models.DateField()
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="shift_schedules")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_shift_schedules",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="updated_shift_schedules",
    )
    extra_chiefs = models.ManyToManyField(Chief, blank=True, related_name="extra_shift_schedules")
    extra_agents = models.ManyToManyField(Agent, blank=True, related_name="extra_shift_schedules")
    extra_supports = models.ManyToManyField(Support, blank=True, related_name="extra_shift_schedules")
    removed_chiefs = models.ManyToManyField(Chief, blank=True, related_name="removed_shift_schedules")
    removed_agents = models.ManyToManyField(Agent, blank=True, related_name="removed_shift_schedules")
    removed_supports = models.ManyToManyField(Support, blank=True, related_name="removed_shift_schedules")
    absent_chiefs = models.ManyToManyField(Chief, blank=True, related_name="absent_shift_schedules")
    absent_agents = models.ManyToManyField(Agent, blank=True, related_name="absent_shift_schedules")
    absent_supports = models.ManyToManyField(Support, blank=True, related_name="absent_shift_schedules")
    
    attendance_reported = models.BooleanField(default=False)
    attendance_reported_at = models.DateTimeField(null=True, blank=True)
    attendance_approved = models.BooleanField(default=False)
    attendance_approved_at = models.DateTimeField(null=True, blank=True)
    checked_members = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "team__name"]
        constraints = [
            models.UniqueConstraint(fields=["date", "team"], name="unique_shift_schedule_date_team"),
        ]
        indexes = [
            models.Index(fields=["date", "team"], name="schedules_sh_date_team_idx"),
        ]

    def __str__(self):
        return f"{self.date} - {self.team}"


class ShiftAbsence(models.Model):
    class MemberType(models.TextChoices):
        CHIEF = "CHIEF", "Chefe"
        AGENT = "AGENT", "Agente"
        SUPPORT = "SUPPORT", "Apoio"

    schedule = models.ForeignKey(ShiftSchedule, on_delete=models.CASCADE, related_name="absence_records")
    member_type = models.CharField(max_length=16, choices=MemberType.choices)
    member_id = models.PositiveIntegerField()
    member_name = models.CharField(max_length=180)
    reason = models.TextField()
    attachment = models.FileField(upload_to="shift_absences/", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_shift_absences",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["member_name"]
        constraints = [
            models.UniqueConstraint(fields=["schedule", "member_type", "member_id"], name="unique_shift_absence_member"),
        ]
        indexes = [
            models.Index(fields=["schedule", "member_type"], name="shift_abs_sched_type_idx"),
        ]

    def __str__(self):
        return f"{self.member_name} - {self.schedule}"


class ShiftManualInclusion(models.Model):
    class MemberType(models.TextChoices):
        CHIEF = "CHIEF", "Chefe"
        AGENT = "AGENT", "Agente"
        SUPPORT = "SUPPORT", "Apoio"

    schedule = models.ForeignKey(ShiftSchedule, on_delete=models.CASCADE, related_name="manual_inclusions")
    member_type = models.CharField(max_length=16, choices=MemberType.choices)
    member_id = models.PositiveIntegerField()
    member_name = models.CharField(max_length=180)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="added_manual_inclusions",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["member_name"]
        constraints = [
            models.UniqueConstraint(fields=["schedule", "member_type", "member_id"], name="unique_shift_inclusion_member"),
        ]

    def __str__(self):
        return f"Incluido: {self.member_name} - {self.schedule}"


class ShiftSwapRequest(models.Model):
    class MemberType(models.TextChoices):
        CHIEF = "CHIEF", "Chefe"
        AGENT = "AGENT", "Agente"
        SUPPORT = "SUPPORT", "Apoio"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        APPROVED = "APPROVED", "Aprovada"
        REJECTED = "REJECTED", "Rejeitada"

    schedule = models.ForeignKey(ShiftSchedule, on_delete=models.CASCADE, related_name="swap_requests")
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shift_swap_requests",
    )
    member_type = models.CharField(max_length=16, choices=MemberType.choices)
    from_member_id = models.PositiveIntegerField()
    from_member_name = models.CharField(max_length=180)
    target_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="target_shift_swap_requests")
    to_member_id = models.PositiveIntegerField()
    to_member_name = models.CharField(max_length=180)
    reason = models.TextField(blank=True)
    attachment = models.FileField(upload_to="shift_swaps/", null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="decided_shift_swap_requests",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="shift_sw_status_idx"),
            models.Index(fields=["schedule", "member_type"], name="shift_sw_sched_type_idx"),
        ]

    def __str__(self):
        return f"{self.get_member_type_display()} - {self.from_member_name} por {self.to_member_name}"


class Agenda(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        APPROVED = "APPROVED", "Aprovada"
        CANCELLED = "CANCELLED", "Cancelada"
        COMPLETED = "COMPLETED", "Concluída"

    class ServiceOrderMode(models.TextChoices):
        TEAM = "TEAM", "Equipe operacional"
        DESIGNATED = "DESIGNATED", "Participantes selecionados"

    class Origin(models.TextChoices):
        INTERNAL = "INTERNAL", "Interna"
        PUBLIC_FORM = "PUBLIC_FORM", "Formulario publico"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        PHONE = "PHONE", "Telefone"
        EMAIL = "EMAIL", "E-mail"
        DOCUMENT = "DOCUMENT", "Oficio"
        OTHER = "OTHER", "Outra"

    title = models.CharField(max_length=180)
    source_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    service_order_number = models.PositiveIntegerField(unique=True, db_index=True, editable=False, null=True, blank=True)
    linked_action = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_requests",
    )
    description = models.TextField()
    date = models.DateField(db_index=True)
    start_time = models.TimeField(db_index=True)
    end_time = models.TimeField()
    location = models.CharField(max_length=180)
    vehicle = models.CharField(max_length=120, blank=True)
    vehicle_ref = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    service_order_mode = models.CharField(
        max_length=20,
        choices=ServiceOrderMode.choices,
        default=ServiceOrderMode.TEAM,
        db_index=True,
    )
    designated_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="designated_service_orders",
    )
    team_name = models.CharField(max_length=160, blank=True)
    team_ref = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    chief_name = models.CharField(max_length=160, blank=True)
    chief_ref = models.ForeignKey(Chief, on_delete=models.SET_NULL, null=True, blank=True)
    team_phone = models.CharField(max_length=160, blank=True)
    agents = models.TextField(blank=True)
    agents_ref = models.ManyToManyField(Agent, blank=True, related_name="agendas")
    support_1 = models.CharField(max_length=160, blank=True)
    support_1_ref = models.ForeignKey(
        Support, on_delete=models.SET_NULL, null=True, blank=True, related_name="support_1_agendas"
    )
    support_2 = models.CharField(max_length=160, blank=True)
    support_2_ref = models.ForeignKey(
        Support, on_delete=models.SET_NULL, null=True, blank=True, related_name="support_2_agendas"
    )
    action_type = models.CharField(max_length=160, blank=True)
    action_type_ref = models.ForeignKey(ActionType, on_delete=models.SET_NULL, null=True, blank=True)
    institution_location = models.CharField(max_length=220, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    participant_range = models.CharField(max_length=40, blank=True)
    street_action_details = models.JSONField(default=list, blank=True)
    actions_count = models.PositiveSmallIntegerField(null=True, blank=True)
    schedule_text = models.CharField(max_length=120, blank=True)
    time_2 = models.TimeField(null=True, blank=True)
    time_3 = models.TimeField(null=True, blank=True)
    address = models.CharField(max_length=220, blank=True)
    neighborhood = models.CharField(max_length=120, blank=True)
    neighborhood_ref = models.ForeignKey(Neighborhood, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=40, blank=True)
    municipality_ref = models.ForeignKey(Municipality, on_delete=models.SET_NULL, null=True, blank=True)
    external_responsible = models.CharField(max_length=160, blank=True)
    external_responsible_phone = models.CharField(max_length=160, blank=True)
    external_email = models.EmailField(blank=True)
    contact_email = models.EmailField(blank=True)
    requester_cpf = models.CharField(max_length=20, blank=True)
    requester_role = models.CharField(max_length=160, blank=True)
    audience = models.CharField(max_length=160, blank=True)
    requester_entity_type = models.CharField(max_length=160, blank=True)
    age_ranges = models.CharField(max_length=220, blank=True)
    accessibility_access = models.CharField(max_length=80, blank=True)
    accessibility_block = models.ForeignKey(
        "AccessibilityBlocklist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocked_agendas",
    )
    accessibility_rejection_due_at = models.DateTimeField(null=True, blank=True)
    accessibility_rejection_sent_at = models.DateTimeField(null=True, blank=True)
    has_ramps = models.CharField(max_length=3, blank=True)
    has_elevators = models.CharField(max_length=3, blank=True)
    has_accessible_bathrooms = models.CharField(max_length=3, blank=True)
    media_equipment = models.TextField(blank=True)
    image_authorization = models.TextField(blank=True)
    activity_type = models.CharField(max_length=160, blank=True)
    kit_1 = models.CharField(max_length=160, blank=True)
    kit_1_quantity = models.PositiveIntegerField(null=True, blank=True)
    material_1 = models.CharField(max_length=220, blank=True)
    kit_2 = models.CharField(max_length=160, blank=True)
    kit_2_quantity = models.PositiveIntegerField(null=True, blank=True)
    material_2 = models.CharField(max_length=220, blank=True)
    kit_3 = models.CharField(max_length=160, blank=True)
    kit_3_quantity = models.PositiveIntegerField(null=True, blank=True)
    material_3 = models.CharField(max_length=220, blank=True)
    kit_4 = models.CharField(max_length=160, blank=True)
    kit_4_quantity = models.PositiveIntegerField(null=True, blank=True)
    material_4 = models.CharField(max_length=220, blank=True)
    kit_5 = models.CharField(max_length=160, blank=True)
    kit_5_quantity = models.PositiveIntegerField(null=True, blank=True)
    material_5 = models.CharField(max_length=220, blank=True)
    kit_6 = models.CharField(max_length=160, blank=True)
    kit_6_quantity = models.PositiveIntegerField(null=True, blank=True)
    material_6 = models.CharField(max_length=220, blank=True)
    kit_7 = models.CharField(max_length=160, blank=True)
    kit_7_quantity = models.PositiveIntegerField(null=True, blank=True)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="responsible_agendas",
    )
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="agendas")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.INTERNAL, db_index=True)
    cancel_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_agendas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["date", "status"]),
            models.Index(fields=["sector", "date"]),
            models.Index(fields=["responsible", "date"]),
            models.Index(fields=["accessibility_rejection_due_at", "accessibility_rejection_sent_at"]),
            GinIndex(name='action_type_gin_idx', fields=['action_type'], opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return f"{self.title} - {self.date}"

    def should_have_service_order(self):
        return self.status in [Agenda.Status.APPROVED, Agenda.Status.COMPLETED]

    def save(self, *args, **kwargs):
        if self.should_have_service_order() and not self.service_order_number:
            with transaction.atomic():
                last_number = Agenda.objects.select_for_update().aggregate(
                    max_number=Max("service_order_number")
                )["max_number"] or 0
                self.service_order_number = last_number + 1
                update_fields = kwargs.get("update_fields")
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {"service_order_number"}
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def overlaps_queryset(self):
        qs = Agenda.objects.filter(
            date=self.date,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk).exclude(status__in=[Agenda.Status.CANCELLED])

        filters = Q()
        if self.responsible and not getattr(self.responsible, 'email', '') == 'solicitacao.publica@agenda.local':
            filters |= Q(responsible=self.responsible)
        if self.location:
            filters |= Q(location__iexact=self.location)

        if not filters:
            return Agenda.objects.none()

        return qs.filter(filters)


class AgendaHistory(models.Model):
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name="history")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.agenda_id} - {self.action}"


class AgendaMaterial(models.Model):
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name="materials")
    kit = models.ForeignKey(Kit, on_delete=models.SET_NULL, null=True, blank=True)
    dynamic = models.ForeignKey(Dynamic, on_delete=models.SET_NULL, null=True, blank=True)
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.agenda_id} - {self.kit or self.material}"


class EventReport(models.Model):
    class ObjectiveStatus(models.TextChoices):
        FULL = "FULL", "Totalmente atingido"
        PARTIAL = "PARTIAL", "Parcialmente atingido"
        NOT_REACHED = "NOT_REACHED", "Não atingido"

    class ReportStatus(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        SUBMITTED = "SUBMITTED", "Enviado"

    class ExecutionQuality(models.TextChoices):
        AS_PLANNED = "AS_PLANNED", "Executada conforme planejado"
        PARTIAL_CHANGE = "PARTIAL_CHANGE", "Executada com ajustes"
        NOT_EXECUTED = "NOT_EXECUTED", "Não executada"

    class ReceptivityLevel(models.TextChoices):
        HIGH = "HIGH", "Alta receptividade"
        MEDIUM = "MEDIUM", "Receptividade moderada"
        LOW = "LOW", "Baixa receptividade"

    class IncidentStatus(models.TextChoices):
        NONE = "NONE", "Sem ocorrências"
        MINOR = "MINOR", "Ocorrências sem impacto"
        RELEVANT = "RELEVANT", "Ocorrências relevantes"

    class MaterialStatus(models.TextChoices):
        ADEQUATE = "ADEQUATE", "Materiais suficientes"
        PARTIAL = "PARTIAL", "Materiais parcialmente suficientes"
        INSUFFICIENT = "INSUFFICIENT", "Materiais insuficientes"

    class TeamPerformance(models.TextChoices):
        EXCELLENT = "EXCELLENT", "Excelente"
        ADEQUATE = "ADEQUATE", "Adequada"
        NEEDS_SUPPORT = "NEEDS_SUPPORT", "Necessita apoio"

    agenda = models.OneToOneField(Agenda, on_delete=models.CASCADE, related_name="event_report")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.DRAFT)
    objective_status = models.CharField(max_length=20, choices=ObjectiveStatus.choices, default=ObjectiveStatus.FULL)
    execution_quality = models.CharField(max_length=20, choices=ExecutionQuality.choices, default=ExecutionQuality.AS_PLANNED)
    receptivity_level = models.CharField(max_length=20, choices=ReceptivityLevel.choices, default=ReceptivityLevel.HIGH)
    incident_status = models.CharField(max_length=20, choices=IncidentStatus.choices, default=IncidentStatus.NONE)
    material_status = models.CharField(max_length=20, choices=MaterialStatus.choices, default=MaterialStatus.ADEQUATE)
    team_performance_status = models.CharField(max_length=20, choices=TeamPerformance.choices, default=TeamPerformance.ADEQUATE)
    participants_count = models.PositiveIntegerField(null=True, blank=True)
    audience_profile = models.CharField(max_length=220, blank=True)
    execution_summary = models.TextField()
    public_receptivity = models.TextField(blank=True)
    incidents = models.TextField(blank=True)
    materials_used = models.TextField(blank=True)
    team_performance = models.TextField(blank=True)
    positive_points = models.TextField(blank=True)
    improvement_points = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    final_considerations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Relatorio - {self.agenda}"


class EducationReport(models.Model):
    class Source(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        IMPORTED = "IMPORTED", "Importado"

    class ReportStatus(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        PENDING_REVIEW = "PENDING_REVIEW", "Aguardando conferência"
        APPROVED = "APPROVED", "Aprovado"
        RETURNED = "RETURNED", "Devolvido para correção"
        SUBMITTED = "SUBMITTED", "Enviado"

    source = models.CharField(max_length=20, choices=Source.choices, default=Source.LOCAL)
    source_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    agenda = models.ForeignKey(
        Agenda,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="technical_reports",
    )
    operation_date = models.DateField()
    team = models.CharField(max_length=160)
    management_id = models.IntegerField(null=True, blank=True)
    management_name = models.CharField(max_length=180, blank=True)
    education_pcd = models.TextField(blank=True)
    education_agents = models.TextField(blank=True)
    changes_staff = models.TextField(blank=True)
    approximate_public = models.PositiveIntegerField(null=True, blank=True)
    street_action_details = models.JSONField(default=list, blank=True)
    accessibility_conditions_met = models.CharField(
        max_length=3,
        choices=[("YES", "Sim"), ("NO", "Não")],
        blank=True,
    )
    materials_removed = models.TextField(blank=True)
    materials_spent = models.TextField(blank=True)
    equipment_materials_removed = models.TextField(blank=True)
    equipment_materials_distributed = models.TextField(blank=True)
    distribution_materials_removed = models.TextField(blank=True)
    distribution_materials_distributed = models.TextField(blank=True)
    breathalyzers = models.TextField(blank=True)
    cars = models.CharField(max_length=220, blank=True)
    changes_general = models.TextField(blank=True)
    contact_received = models.CharField(max_length=220, blank=True)
    occurrence_observation = models.TextField(blank=True)
    general_observations = models.TextField(blank=True)
    photo_1 = models.FileField(upload_to="education_reports/", null=True, blank=True)
    photo_2 = models.FileField(upload_to="education_reports/", null=True, blank=True)
    no_photo_reason = models.TextField(blank=True)
    lat = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    lng = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.DRAFT)
    horus_created_at = models.DateTimeField(null=True, blank=True)
    horus_updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="education_reports",
    )
    submitted_for_review_at = models.DateTimeField(null=True, blank=True)
    submitted_for_review_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_reports",
    )
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-operation_date", "-created_at"]
        indexes = [
            models.Index(fields=["operation_date", "team"]),
            models.Index(fields=["source", "operation_date"]),
        ]

    def __str__(self):
        protocol = f"#{self.agenda_id} - " if self.agenda_id else ""
        return f"{protocol}Relatorio - {self.team}"


class ReportStatusHistory(models.Model):
    report = models.ForeignKey(EducationReport, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20, choices=EducationReport.ReportStatus.choices, null=True, blank=True)
    new_status = models.CharField(max_length=20, choices=EducationReport.ReportStatus.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.report} ({self.old_status} -> {self.new_status})"


class AccessibilityBlocklist(models.Model):
    institution_location = models.CharField(max_length=220, blank=True)
    address = models.CharField(max_length=220, blank=True)
    external_responsible = models.CharField(max_length=160, blank=True)
    external_responsible_phone = models.CharField(max_length=160, blank=True)
    external_email = models.EmailField(blank=True)
    requester_cpf = models.CharField(max_length=20, blank=True)
    reason = models.TextField(blank=True)
    source_agenda = models.ForeignKey(Agenda, on_delete=models.SET_NULL, null=True, blank=True, related_name="accessibility_blocks")
    source_report = models.ForeignKey(EducationReport, on_delete=models.SET_NULL, null=True, blank=True, related_name="accessibility_blocks")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "institution_location"]),
            models.Index(fields=["is_active", "address"]),
            models.Index(fields=["is_active", "external_email"]),
            models.Index(fields=["is_active", "requester_cpf"]),
        ]

    def __str__(self):
        return self.institution_location or self.external_responsible or self.external_email or "Restrição de acessibilidade"


class EducationAction(models.Model):
    report = models.ForeignKey(EducationReport, on_delete=models.CASCADE, related_name="actions")
    agenda = models.ForeignKey(Agenda, on_delete=models.SET_NULL, null=True, blank=True, related_name="education_actions")
    source_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    place_action = models.CharField(max_length=260, blank=True)
    type_action = models.CharField(max_length=160, blank=True)
    type_audience = models.CharField(max_length=160, blank=True)
    institution_name = models.CharField(max_length=220, blank=True)
    start_time = models.CharField(max_length=30, blank=True)
    final_hour = models.CharField(max_length=30, blank=True)
    approach = models.PositiveIntegerField(default=0)
    equipment_materials_removed = models.TextField(blank=True)
    equipment_materials_distributed = models.TextField(blank=True)
    distribution_materials_removed = models.TextField(blank=True)
    distribution_materials_distributed = models.TextField(blank=True)
    approached_lectures = models.PositiveIntegerField(default=0)
    approached_actions = models.PositiveIntegerField(default=0)
    tests = models.PositiveIntegerField(default=0)
    used_caps = models.PositiveIntegerField(default=0)
    available_caps = models.PositiveIntegerField(default=0)
    distributed_folders = models.PositiveIntegerField(default=0)
    cricris = models.PositiveIntegerField(default=0)
    vetarolas = models.PositiveIntegerField(default=0)
    used_adhesives = models.PositiveIntegerField(default=0)
    sequence_certificates = models.PositiveIntegerField(default=0)
    gibis = models.PositiveIntegerField(default=0)
    distributed_certificates = models.PositiveIntegerField(default=0)
    lectures = models.PositiveIntegerField(default=0)
    schools = models.PositiveIntegerField(default=0)
    universities = models.PositiveIntegerField(default=0)
    companies = models.PositiveIntegerField(default=0)
    educational_actions = models.PositiveIntegerField(default=0)
    bars = models.PositiveIntegerField(default=0)
    tolls = models.PositiveIntegerField(default=0)
    sports = models.PositiveIntegerField(default=0)
    beach = models.PositiveIntegerField(default=0)
    events = models.PositiveIntegerField(default=0)
    shopping = models.PositiveIntegerField(default=0)
    social_actions = models.PositiveIntegerField(default=0)
    joint_inspections = models.PositiveIntegerField(default=0)
    other_actions = models.PositiveIntegerField(default=0)
    publicity_materials = models.PositiveIntegerField(default=0)
    horus_created_at = models.DateTimeField(null=True, blank=True)
    horus_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time", "id"]

    def __str__(self):
        return f"{self.type_action} - {self.institution_name}"


class SatisfactionSurvey(models.Model):
    class ModerationStatus(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        APPROVED = "APPROVED", "Aprovado"
        REJECTED = "REJECTED", "Reprovado"
        HIDDEN = "HIDDEN", "Oculto"

    agenda = models.ForeignKey(Agenda, on_delete=models.PROTECT, related_name="satisfaction_surveys")
    report = models.ForeignKey(
        EducationReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="satisfaction_surveys",
    )
    token = models.CharField(max_length=180, unique=True)
    requester_email = models.EmailField(blank=True)
    team = models.CharField(max_length=160, blank=True)
    chief_name = models.CharField(max_length=160, blank=True)
    audiovisual_resources = models.PositiveSmallIntegerField(null=True, blank=True)
    speaker_knowledge = models.PositiveSmallIntegerField(null=True, blank=True)
    wheelchair_testimony = models.PositiveSmallIntegerField(null=True, blank=True)
    workshops = models.PositiveSmallIntegerField(null=True, blank=True)
    support_material = models.PositiveSmallIntegerField(null=True, blank=True)
    punctuality = models.PositiveSmallIntegerField(null=True, blank=True)
    team_enthusiasm = models.PositiveSmallIntegerField(null=True, blank=True)
    overall_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    suggestion = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_approved = models.BooleanField(default=False, db_index=True)
    moderation_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
    )
    moderated_comment = models.TextField(blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_satisfaction_surveys",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["moderation_status", "answered_at"], name="survey_status_answered_idx"),
            models.Index(fields=["team", "answered_at"], name="survey_team_answered_idx"),
        ]

    def __str__(self):
        return f"Pesquisa #{self.agenda_id}"


class SatisfactionSurveyModerationHistory(models.Model):
    survey = models.ForeignKey(
        SatisfactionSurvey,
        on_delete=models.CASCADE,
        related_name="moderation_history",
    )
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=SatisfactionSurvey.ModerationStatus.choices)
    comment_snapshot = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="satisfaction_moderation_decisions",
    )
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decided_at", "-id"]

    def __str__(self):
        return f"Moderação #{self.survey_id}: {self.new_status}"


class EducationGoal(models.Model):
    year = models.PositiveIntegerField()
    key = models.CharField(max_length=80)
    label = models.CharField(max_length=160)
    average = models.PositiveIntegerField(default=0)
    target = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["year", "order", "label"]
        constraints = [
            models.UniqueConstraint(fields=["year", "key"], name="unique_education_goal_year_key"),
        ]

    def __str__(self):
        return f"{self.year} - {self.label}"

