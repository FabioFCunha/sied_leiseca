from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import logging

from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.schedules.models import Agent, Chief, Sector, Support, Team

logger = logging.getLogger(__name__)


def only_digits(value):
    return "".join(char for char in str(value or "") if char.isdigit())


def sector_for_team(team):
    if not team:
        return None
    candidates = [team.name, team.name.title()]
    if team.name.upper() == "FOX":
        candidates.append("Foxtrot")
    for name in candidates:
        sector = Sector.objects.filter(name__iexact=name).first()
        if sector:
            return sector
    return Sector.objects.create(
        name=team.name,
        description="Equipe para vinculo de usuarios",
        is_active=True,
    )


def find_lookup(model, user):
    cpf = only_digits(user.cpf)
    if cpf:
        found = model.objects.filter(cpf=cpf).first()
        if found:
            return found
    return model.objects.filter(name__iexact=user.full_name).first()

from .models import AuditLog, User


USER_LOOKUP_SOURCE_PREFIX = "user:"
USER_LOOKUP_MODELS = (Agent, Chief, Support)


def user_lookup_source_id(user):
    return f"{USER_LOOKUP_SOURCE_PREFIX}{user.id}"


def get_safe_lookup_query(user):
    source_id = user_lookup_source_id(user)
    cpf = only_digits(getattr(user, "cpf", ""))

    q = Q(source_id=source_id)
    if cpf:
        q |= Q(cpf=cpf)
    if user.full_name:
        # Usa nome apenas se o registro alvo não tiver CPF (para não conflitar com homônimos que já possuem outro CPF)
        q |= Q(name__iexact=user.full_name, cpf__isnull=True) | Q(name__iexact=user.full_name, cpf="")
    return q

def deactivate_other_user_lookups(user, active_model=None):
    q = get_safe_lookup_query(user)
    for model in USER_LOOKUP_MODELS:
        if active_model is not None and model is active_model:
            continue
        model.objects.filter(q).update(is_active=False)


def find_unlinked_legacy_candidate(model, cpf, name):
    # 1. Procurar por CPF legado livre (source_id vazio/nulo)
    cpf_digits = only_digits(cpf)
    if cpf_digits:
        legacy = model.objects.filter(
            Q(cpf=cpf_digits) & (Q(source_id="") | Q(source_id__isnull=True))
        ).first()
        if legacy:
            return legacy

    # 2. Procurar por nome legado livre e único, sem CPF
    if name:
        candidates = model.objects.filter(
            Q(name__iexact=name) & (Q(source_id="") | Q(source_id__isnull=True))
        )
        if candidates.count() == 1:
            candidate = candidates.first()
            if not candidate.cpf:
                return candidate

    return None


def find_bound_conflict(model, cpf, name, excluding_source_id, excluding_id=None):
    cpf_digits = only_digits(cpf)
    q_base = Q()
    if excluding_id:
        q_base &= ~Q(id=excluding_id)

    # 1. Conflito por CPF com outro usuário (Somente o CPF bloqueia - Cenário C)
    if cpf_digits:
        conflict = model.objects.filter(
            q_base & Q(cpf=cpf_digits)
        ).exclude(source_id=excluding_source_id).exclude(source_id="").exclude(source_id__isnull=True).first()
        if conflict:
            return conflict, "CPF vinculado a outro usuário"

    # 2. Coincidência por Nome (Cenário D - Não bloqueia, apenas alerta)
    if name:
        # Vinculado a outro usuário
        conflict_name = model.objects.filter(
            q_base & Q(name__iexact=name)
        ).exclude(source_id=excluding_source_id).first()
        
        if conflict_name:
            logger.warning(
                "SYNC_WARNING_DUPLICATE_NAME",
                extra={
                    "nome": name,
                    "cpf_existente": getattr(conflict_name, "cpf", ""),
                    "lookup_id": conflict_name.id,
                    "model": model.__name__,
                },
            )

    return None, None


def safe_save_lookup(lookup, *, user, model_name):
    try:
        with transaction.atomic():
            lookup.save()
        return lookup
    except IntegrityError:
        logger.exception(
            "Falha ao sincronizar lookup operacional devido a erro de integridade",
            extra={
                "user_id": user.id,
                "email": user.email,
                "lookup_model": model_name,
                "lookup_id": getattr(lookup, "id", None),
            },
        )
        raise serializers.ValidationError(
            {"full_name": f"O nome exato '{lookup.name}' já está registrado. O banco de dados exige nomes únicos para o histórico de escalas. Por favor, adicione um diferencial (ex: sobrenome adicional)."}
        )


def upsert_user_lookup(model, user, role_label, extra_defaults=None):
    expected_source_id = user_lookup_source_id(user)

    # 1. Procurar por source_id
    lookup = model.objects.filter(source_id=expected_source_id).first()

    defaults = {
        "source_id": expected_source_id,
        "name": user.full_name,
        "cpf": only_digits(user.cpf) or None,
        "role": role_label,
        "is_active": user.is_active,
        "vacation_start": user.vacation_start,
        "vacation_end": user.vacation_end,
    }
    if extra_defaults:
        defaults.update(extra_defaults)

    if lookup is None:
        # Se não existe lookup para este usuário, procuramos candidato legado (sem vínculo)
        legacy_candidate = find_unlinked_legacy_candidate(
            model=model,
            cpf=user.cpf,
            name=user.full_name,
        )
        if legacy_candidate:
            lookup = legacy_candidate
        else:
            # Não há candidato legado. Verificamos se há conflito com outro usuário ou ambiguidade
            conflict, reason = find_bound_conflict(
                model=model,
                cpf=user.cpf,
                name=user.full_name,
                excluding_source_id=expected_source_id,
            )
            if conflict:
                raise serializers.ValidationError(
                    {"cpf": f"Não foi possível sincronizar o perfil operacional. O CPF informado já se encontra vinculado a outro usuário ativo no sistema."}
                )

            # Sem conflitos, criamos um novo
            lookup = model()
    else:
        # Se o lookup existe, mas o nome ou CPF mudou, verificamos se há conflito com outro registro
        # 1. Verificamos se há conflito com outro usuário ou ambiguidade
        conflict, reason = find_bound_conflict(
            model=model,
            cpf=user.cpf,
            name=user.full_name,
            excluding_source_id=expected_source_id,
            excluding_id=lookup.id,
        )
        if conflict:
            raise serializers.ValidationError(
                {"cpf": f"Não foi possível sincronizar o perfil operacional. O CPF informado já se encontra vinculado a outro usuário ativo no sistema."}
            )

        # 2. Verificamos se há um registro legado (sem vínculo) com o novo CPF/nome
        legacy_candidate = find_unlinked_legacy_candidate(
            model=model,
            cpf=user.cpf,
            name=user.full_name,
        )
        if legacy_candidate and legacy_candidate.id != lookup.id:
            # Desvincula o lookup antigo
            lookup.source_id = ""
            lookup.is_active = False
            safe_save_lookup(lookup, user=user, model_name=model.__name__)
            # Reutiliza o legado candidate
            lookup = legacy_candidate

    for field, value in defaults.items():
        setattr(lookup, field, value)

    return safe_save_lookup(lookup, user=user, model_name=model.__name__)


def lookup_for_user(user):
    model = {
        User.Role.SUPERVISOR: Chief,
        User.Role.USER: Agent,
        User.Role.SUPPORT: Support,
    }.get(user.role)
    if not model:
        return None
    return model.objects.filter(source_id=user_lookup_source_id(user)).first() or find_lookup(model, user)


def team_for_user(user):
    lookup = lookup_for_user(user)
    return lookup.team if lookup and lookup.team_id else None


def fallback_team_for_user(user):
    sector_name = str(getattr(getattr(user, "sector", None), "name", "") or "").strip()
    if not sector_name:
        return None
    return Team.objects.filter(name__iexact=sector_name).first()


def sync_user_lookup(user, team=None, clear_team=False):
    if not user.full_name:
        deactivate_other_user_lookups(user)
        return

    if user.role == User.Role.SUPERVISOR:
        existing = Chief.objects.filter(source_id=user_lookup_source_id(user)).first() or find_lookup(Chief, user)
        phone = user.phone or (existing.phone if existing else "")
        selected_team = None if clear_team else (team or (existing.team if existing and existing.team_id else None) or fallback_team_for_user(user))
        lookup = upsert_user_lookup(
            Chief,
            user,
            "CHEFE",
            {"phone": phone, "team": selected_team},
        )
        if not lookup:
            return
        deactivate_other_user_lookups(user, Chief)
        sector = sector_for_team(lookup.team)
        sector_id = sector.id if sector else None
        changed_fields = []
        if phone and user.phone != phone:
            user.phone = phone
            changed_fields.append("phone")
        if user.sector_id != sector_id:
            user.sector = sector
            changed_fields.append("sector")
        if changed_fields:
            user.save(update_fields=changed_fields)
        return

    if user.role == User.Role.USER:
        existing = Agent.objects.filter(source_id=user_lookup_source_id(user)).first() or find_lookup(Agent, user)
        selected_team = None if clear_team else (team or (existing.team if existing and existing.team_id else None) or fallback_team_for_user(user))
        lookup = upsert_user_lookup(Agent, user, "AGENTE", {"team": selected_team})
        if not lookup:
            return
        deactivate_other_user_lookups(user, Agent)
        sector = sector_for_team(lookup.team)
        sector_id = sector.id if sector else None
        if user.sector_id != sector_id:
            user.sector = sector
            user.save(update_fields=["sector"])
        return

    if user.role == User.Role.SUPPORT:
        existing = Support.objects.filter(source_id=user_lookup_source_id(user)).first() or find_lookup(Support, user)
        selected_team = None if clear_team else (team or (existing.team if existing and existing.team_id else None) or fallback_team_for_user(user))
        lookup = upsert_user_lookup(Support, user, "APOIO", {"team": selected_team})
        if not lookup:
            return
        deactivate_other_user_lookups(user, Support)
        sector = sector_for_team(lookup.team)
        sector_id = sector.id if sector else None
        if user.sector_id != sector_id:
            user.sector = sector
            user.save(update_fields=["sector"])
        return

    deactivate_other_user_lookups(user)


def sync_active_users_for_role(role):
    users = User.objects.filter(is_active=True, role=role).select_related("sector")
    for user in users:
        try:
            with transaction.atomic():
                sync_user_lookup(user)
        except Exception as e:
            logger.exception(
                "Falha ao sincronizar lookup operacional para o usuário %s (%s) na função %s: %s",
                user.id,
                user.email,
                role,
                str(e),
            )


def sync_all_user_lookups():
    total = 0
    for user in User.objects.exclude(role__in=[User.Role.ADMIN, User.Role.MANAGER, User.Role.VISITOR]):
        try:
            with transaction.atomic():
                sync_user_lookup(user)
                total += 1
        except Exception as e:
            logger.exception("Falha ao sincronizar lookup operacional geral para o usuario %s: %s", user.id, str(e))
    return total


class LoginSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all(), required=False, allow_null=True, write_only=True)
    team_id = serializers.SerializerMethodField()
    team_name = serializers.SerializerMethodField()
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    occupation = serializers.CharField(source="role", read_only=True)
    password_setup_link = serializers.SerializerMethodField()
    cpf = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "cpf",
            "phone",
            "role",
            "occupation",
            "team",
            "team_id",
            "team_name",
            "sector",
            "sector_name",
            "is_active",
            "is_on_vacation",
            "vacation_start",
            "vacation_end",
            "password",
            "password_setup_link",
            "lgpd_consent_at",
        ]
        read_only_fields = ["id", "password_setup_link", "lgpd_consent_at"]
        extra_kwargs = {
            "full_name": {"required": False, "allow_blank": True},
            "cpf": {"required": False, "allow_blank": True},
        }

    def get_cpf(self, obj):
        raw = only_digits(obj.cpf)
        if not raw:
            return None
        request = self.context.get("request")
        if request and hasattr(request, "user") and (request.user.is_superuser or getattr(request.user, "is_admin_role", False)):
            return raw
        return f"***.***.{raw[-5:-2]}-{raw[-2:]}" if len(raw) >= 5 else raw

    def get_password_setup_link(self, obj):
        uid = urlsafe_base64_encode(force_bytes(obj.pk))
        token = default_token_generator.make_token(obj)
        return f"{settings.FRONTEND_URL}/definir-senha?uid={uid}&token={token}"

    def get_team_id(self, obj):
        team = team_for_user(obj)
        return team.id if team else None

    def get_team_name(self, obj):
        team = team_for_user(obj)
        return team.name if team else ""

    def validate_email(self, value):
        email = (value or "").strip().lower()
        try:
            validate_email(email)
        except DjangoValidationError:
            raise serializers.ValidationError("Informe um e-mail valido.")
        return email

    def validate_phone(self, value):
        digits = only_digits(value)
        if not digits:
            return ""
        if len(digits) not in {10, 11}:
            raise serializers.ValidationError("Informe um telefone valido com DDD.")
        return digits

    def validate_cpf(self, value):
        digits = only_digits(value)
        if not digits:
            return None
        if len(digits) != 11:
            raise serializers.ValidationError("Informe um CPF valido com 11 digitos.")
        return digits

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", User.Role.USER))
        if role in {User.Role.USER, User.Role.SUPPORT}:
            team = attrs.get("team") if "team" in attrs else getattr(self.instance, "team", None) if self.instance else None
            if not team:
                raise serializers.ValidationError({"team": "Este campo é obrigatório para usuários operacionais."})
            if team and not team.is_active:
                raise serializers.ValidationError({"team": "Selecione uma equipe ativa."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        team = validated_data.pop("team", None)
        if validated_data.get("role") == User.Role.VISITOR and not validated_data.get("full_name"):
            sector = validated_data.get("sector")
            label = sector.name if sector else validated_data.get("email", "")
            validated_data["full_name"] = f"Visitante - {label}".strip()
        user = User(**validated_data)
        user.username = user.email
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        sync_user_lookup(user, team=team, clear_team=not team)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        team_provided = "team" in validated_data
        team = validated_data.pop("team", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.username = instance.email
        instance.save()
        sync_user_lookup(instance, team=team, clear_team=(team_provided and not team))
        return instance


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "created_at",
            "user",
            "user_name",
            "user_email",
            "action",
            "action_label",
            "module",
            "description",
            "metadata",
            "ip_address",
            "user_agent",
        ]
