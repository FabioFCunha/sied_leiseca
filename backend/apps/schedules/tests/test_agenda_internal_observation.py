from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.schedules.emails import PUBLIC_REQUEST_SALT
from apps.schedules.models import Agenda, Sector
from apps.schedules.serializers import AgendaSerializer, PublicAgendaRequestSerializer
from django.core import signing


class AgendaInternalObservationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="internal-observation@example.com",
            password="pass",
            full_name="Gestor de teste",
            role=User.Role.MANAGER,
        )
        self.sector = Sector.objects.create(name="Setor de teste - observação")
        self.agenda = Agenda.objects.create(
            title="OS de teste",
            description="Descrição",
            date=date(2026, 8, 27),
            start_time=time(9),
            end_time=time(10),
            location="Local de teste",
            responsible=self.user,
            created_by=self.user,
            sector=self.sector,
        )

    def test_internal_serializer_reads_updates_and_clears_observation(self):
        serializer = AgendaSerializer(
            self.agenda,
            data={"internal_observation": "Primeira linha\nSegunda linha"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        agenda = serializer.save()
        self.assertEqual(agenda.internal_observation, "Primeira linha\nSegunda linha")
        self.assertEqual(AgendaSerializer(agenda).data["internal_observation"], "Primeira linha\nSegunda linha")

        clear_serializer = AgendaSerializer(agenda, data={"internal_observation": ""}, partial=True)
        self.assertTrue(clear_serializer.is_valid(), clear_serializer.errors)
        self.assertEqual(clear_serializer.save().internal_observation, "")

    def test_old_agenda_serializes_with_empty_observation(self):
        self.assertEqual(AgendaSerializer(self.agenda).data["internal_observation"], "")

    def test_public_serializers_and_token_response_do_not_expose_observation(self):
        public_data = {
            "title": "Solicitação pública",
            "description": "Descrição",
            "date": "2026-08-27",
            "start_time": "09:00",
            "end_time": "10:00",
            "action_type": "Palestra",
            "institution_location": "Escola",
            "address": "Rua Exemplo, 1",
            "city": "Rio de Janeiro",
            "external_responsible": "Solicitante",
            "external_responsible_phone": "21999999999",
            "external_email": "solicitante@example.com",
            "requester_entity_type": "Escola Municipal",
            "internal_observation": "Não deve ser aceito",
        }
        public_serializer = PublicAgendaRequestSerializer(data=public_data)
        self.assertTrue(public_serializer.is_valid(), public_serializer.errors)
        self.assertNotIn("internal_observation", public_serializer.validated_data)

        self.agenda.internal_observation = "Informação interna"
        self.agenda.save(update_fields=["internal_observation"])
        token = signing.dumps({"agenda": self.agenda.id}, salt=PUBLIC_REQUEST_SALT)
        response = APIClient().get(reverse("public_agenda_request_update", args=[token]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("internal_observation", response.data)
