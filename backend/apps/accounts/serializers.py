from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from apps.schedules.models import Agent, Chief

from .models import User


def sync_user_lookup(user):
    if not user.full_name:
        return
    if user.role == User.Role.SUPERVISOR:
        Chief.objects.update_or_create(
            name=user.full_name,
            defaults={"phone": user.phone, "is_active": user.is_active},
        )
    elif user.role == User.Role.USER:
        Agent.objects.update_or_create(
            name=user.full_name,
            defaults={"is_active": user.is_active},
        )


class LoginSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
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
            "sector",
            "sector_name",
            "is_active",
            "password",
            "password_setup_link",
        ]
        read_only_fields = ["id", "password_setup_link"]

    def get_password_setup_link(self, obj):
        uid = urlsafe_base64_encode(force_bytes(obj.pk))
        token = default_token_generator.make_token(obj)
        return f"{settings.FRONTEND_URL}/definir-senha?uid={uid}&token={token}"

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        user.username = user.email
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        sync_user_lookup(user)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.username = instance.email
        instance.save()
        sync_user_lookup(instance)
        return instance
