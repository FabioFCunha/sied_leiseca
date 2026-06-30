from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from apps.schedules.models import Agent, Chief, Sector, Support, Team


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


def deactivate_other_user_lookups(user, active_model=None):
    source_id = user_lookup_source_id(user)
    for model in USER_LOOKUP_MODELS:
        if active_model is not None and model is active_model:
            continue
        model.objects.filter(source_id=source_id).update(is_active=False)


def upsert_user_lookup(model, user, role_label, extra_defaults=None):
    lookup = model.objects.filter(source_id=user_lookup_source_id(user)).first() or find_lookup(model, user)
    defaults = {
        "source_id": user_lookup_source_id(user),
        "name": user.full_name,
        "cpf": only_digits(user.cpf) or None,
        "role": role_label,
        "is_active": user.is_active and not user.is_on_vacation,
    }
    if extra_defaults:
        defaults.update(extra_defaults)
    if lookup:
        for field, value in defaults.items():
            setattr(lookup, field, value)
        lookup.save()
    else:
        lookup = model.objects.create(**defaults)
    return lookup


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


def sync_user_lookup(user, team=None, clear_team=False):
    if not user.full_name:
        deactivate_other_user_lookups(user)
        return

    if user.role == User.Role.SUPERVISOR:
        existing = Chief.objects.filter(source_id=user_lookup_source_id(user)).first() or find_lookup(Chief, user)
        phone = user.phone or (existing.phone if existing else "")
        selected_team = None if clear_team else (team or (existing.team if existing and existing.team_id else None))
        lookup = upsert_user_lookup(
            Chief,
            user,
            "CHEFE",
            {"phone": phone, "team": selected_team},
        )
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
        selected_team = None if clear_team else (team or (existing.team if existing and existing.team_id else None))
        lookup = upsert_user_lookup(Agent, user, "AGENTE", {"team": selected_team})
        deactivate_other_user_lookups(user, Agent)
        sector = sector_for_team(lookup.team)
        sector_id = sector.id if sector else None
        if user.sector_id != sector_id:
            user.sector = sector
            user.save(update_fields=["sector"])
        return

    if user.role == User.Role.SUPPORT:
        existing = Support.objects.filter(source_id=user_lookup_source_id(user)).first() or find_lookup(Support, user)
        selected_team = None if clear_team else (team or (existing.team if existing and existing.team_id else None))
        lookup = upsert_user_lookup(Support, user, "APOIO", {"team": selected_team})
        deactivate_other_user_lookups(user, Support)
        sector = sector_for_team(lookup.team)
        sector_id = sector.id if sector else None
        if user.sector_id != sector_id:
            user.sector = sector
            user.save(update_fields=["sector"])
        return

    deactivate_other_user_lookups(user)


def sync_all_user_lookups():
    total = 0
    for user in User.objects.exclude(role__in=[User.Role.ADMIN, User.Role.MANAGER, User.Role.VISITOR]):
        sync_user_lookup(user)
        total += 1
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
            "is_superuser",
            "password",
            "password_setup_link",
        ]
        read_only_fields = ["id", "is_superuser", "password_setup_link"]
        extra_kwargs = {
            "full_name": {"required": False, "allow_blank": True},
            "cpf": {"required": False, "allow_blank": True},
        }

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
        if role in {User.Role.USER, User.Role.SUPPORT, User.Role.SUPERVISOR}:
            team = attrs.get("team") if "team" in attrs else getattr(self.instance, "team", None) if self.instance else None
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
