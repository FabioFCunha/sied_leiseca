from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O e-mail e obrigatorio.")
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        MANAGER = "MANAGER", "Gestor"
        SUPERVISOR = "SUPERVISOR", "Supervisor"
        VISITOR = "VISITOR", "Visitante"
        USER = "USER", "Usuário comum"
        SUPPORT = "SUPPORT", "Apoio"
        ALMOXARIFADO = "ALMOXARIFADO", "Almoxarifado"

    username = models.CharField(max_length=150, unique=False, blank=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=180)
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=160, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    sector = models.ForeignKey(
        "schedules.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    last_activity = models.DateTimeField(null=True, blank=True)
    is_on_vacation = models.BooleanField(default=False)
    vacation_start = models.DateField(null=True, blank=True)
    vacation_end = models.DateField(null=True, blank=True)
    lgpd_consent_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Data de aceite LGPD",
        help_text="Data e hora em que o usuário aceitou a política de privacidade.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return self.full_name or self.email

    @property
    def is_admin_role(self):
        return self.role in {self.Role.ADMIN, self.Role.MANAGER}

    @property
    def is_supervisor_role(self):
        return self.role == self.Role.SUPERVISOR

    @property
    def is_agent_role(self):
        return self.role in {self.Role.USER, self.Role.SUPPORT}


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        CREATE = "CREATE", "Criacao"
        UPDATE = "UPDATE", "Alteracao"
        DELETE = "DELETE", "Exclusao"
        STATUS_CHANGE = "STATUS_CHANGE", "Mudanca de status"
        PASSWORD_LINK = "PASSWORD_LINK", "Link de senha"
        PASSWORD_RESET = "PASSWORD_RESET", "Recuperacao de senha"
        SET_PASSWORD = "SET_PASSWORD", "Definicao de senha"
        EMAIL = "EMAIL", "Envio de e-mail"
        REPORT_EXPORT = "REPORT_EXPORT", "Exportacao de relatorio"

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    module = models.CharField(max_length=80)
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["-created_at"], name="accounts_au_created_25d7e5_idx"),
            models.Index(fields=["action", "module"], name="accounts_au_action_d9594d_idx"),
            models.Index(fields=["user", "-created_at"], name="accounts_au_user_id_728d71_idx"),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.module}"
