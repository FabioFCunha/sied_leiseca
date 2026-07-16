from datetime import time

from django.test import TestCase

from apps.accounts.models import User
from apps.schedules.models import Sector
from apps.schedules.serializers import AgendaSerializer


class AgendaTimeValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="test@example.com", cpf="11111111111")
        self.sector = Sector.objects.create(name="Test Sector")

    def build_serializer(self, **overrides):
        data = {
            "title": "Ação",
            "date": "2026-08-01",
            "start_time": "08:00:00",
            "end_time": "10:00:00",
            "requester_entity_type": "Outro",
            "description": "Test",
            "location": "Local",
            "responsible": self.user.id,
            "sector": self.sector.id,
        }
        data.update(overrides)
        return AgendaSerializer(data=data)

    def test_acao_de_rua_preserves_manual_end_time(self):
        serializer = self.build_serializer(
            requester_entity_type="6",
            end_time="10:00:00",
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["end_time"], time(10, 0))

    def test_acao_de_rua_allows_cross_midnight(self):
        serializer = self.build_serializer(
            requester_entity_type="6",
            start_time="22:00:00",
            end_time="00:00:00",
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["end_time"], time(0, 0))

    def test_acao_de_rua_allows_2345_to_midnight(self):
        serializer = self.build_serializer(
            requester_entity_type="6",
            start_time="23:45:00",
            end_time="00:00:00",
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["end_time"], time(0, 0))

    def test_normal_agenda_rejects_same_time(self):
        serializer = self.build_serializer(end_time="08:00:00")

        self.assertFalse(serializer.is_valid())
        self.assertIn("end_time", serializer.errors)

    def test_invalid_time_format_handled_by_drf(self):
        serializer = self.build_serializer(start_time="18:30 PM")

        self.assertFalse(serializer.is_valid())
        self.assertIn("start_time", serializer.errors)
