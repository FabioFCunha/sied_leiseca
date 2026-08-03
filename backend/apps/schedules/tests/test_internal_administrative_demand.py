from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agenda, Sector
from apps.schedules.serializers import AgendaSerializer, PublicAgendaRequestSerializer


class InternalAdministrativeDemandSerializerTests(TestCase):
    def public_payload(self):
        return {
            "title": "Palestra interna - Escola",
            "description": "Solicitação pública",
            "date": "2026-07-20",
            "start_time": "10:00",
            "end_time": "11:00",
            "action_type": "Palestra",
            "institution_location": "Escola Modelo",
            "address": "Rua Exemplo, 10",
            "city": "Rio de Janeiro",
            "external_responsible": "Maria da Silva",
            "external_responsible_phone": "21999999999",
            "external_email": "maria@example.com",
            "requester_entity_type": "Escola Municipal",
            "participant_range": "51 a 100",
            "age_ranges": "11 - 14 anos (ensino fundamental - anos finais)",
            "accessibility_access": "Não se aplica, pois será realizado no térreo",
            "has_accessible_bathrooms": "Sim",
            "quantity": 100,
        }

    def internal_payload(self, subtype="INTERVIEW"):
        data = self.public_payload()
        data.update({
            "requester_entity_type": "Demanda Administrativa",
            "administrative_demand_type": subtype,
            "institution_location": "Sede Administrativa",
        })
        return data

    def test_public_request_still_accepts_old_payload_without_administrative_type(self):
        serializer = PublicAgendaRequestSerializer(data=self.public_payload(), context={"is_internal_request": False})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data.get("administrative_demand_type", ""), "")

    def test_internal_request_requires_administrative_subtype(self):
        payload = self.internal_payload(subtype="")
        serializer = PublicAgendaRequestSerializer(data=payload, context={"is_internal_request": True})

        self.assertFalse(serializer.is_valid())
        self.assertIn("administrative_demand_type", serializer.errors)

    def test_internal_request_rejects_invalid_administrative_subtype(self):
        payload = self.internal_payload(subtype="INVALID")
        serializer = PublicAgendaRequestSerializer(data=payload, context={"is_internal_request": True})

        self.assertFalse(serializer.is_valid())
        self.assertIn("administrative_demand_type", serializer.errors)

    def test_internal_request_common_type_clears_subtype(self):
        payload = self.public_payload()
        payload["requester_entity_type"] = "Empresa/Órgão"
        payload["administrative_demand_type"] = "INTERVIEW"

        serializer = PublicAgendaRequestSerializer(data=payload, context={"is_internal_request": True})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data.get("administrative_demand_type", ""), "")


class InternalAdministrativeDemandApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-internal@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Admin Interno",
        )
        self.sector = Sector.objects.create(name="Solicitações internas")
        self.url = reverse("internal_agenda_request")
        self.agendas_url = reverse("agendas-list")
        self.client.force_authenticate(self.admin)

    def base_payload(self):
        return {
            "title": "Demanda interna",
            "description": "Descrição da demanda",
            "date": "2026-08-10",
            "start_time": "09:00",
            "end_time": "10:00",
            "action_type": "Palestra",
            "institution_location": "Sede OLS",
            "address": "Rua Exemplo, 10",
            "city": "Rio de Janeiro",
            "state": "RJ",
            "external_responsible": "Maria Gestora",
            "external_responsible_phone": "21999999999",
            "external_email": "maria@example.com",
            "requester_role": "Gestora",
            "requester_entity_type": "Empresa/Órgão",
            "participant_range": "51 a 100",
            "age_ranges": "11 - 14 anos (ensino fundamental - anos finais)",
            "accessibility_access": "Não se aplica, pois será realizado no térreo",
            "has_accessible_bathrooms": "Sim",
            "quantity": 100,
        }

    def test_create_internal_administrative_demand_for_each_subtype(self):
        for subtype in ["TRAVEL", "INTERVIEW", "MEETING"]:
            payload = self.base_payload()
            payload["requester_entity_type"] = "Demanda Administrativa"
            payload["administrative_demand_type"] = subtype
            response = self.client.post(self.url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            agenda = Agenda.objects.latest("id")
            self.assertEqual(agenda.requester_entity_type, "Demanda Administrativa")
            self.assertEqual(agenda.administrative_demand_type, subtype)

    def test_internal_common_type_saves_empty_subtype(self):
        payload = self.base_payload()
        payload["administrative_demand_type"] = "INTERVIEW"
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        agenda = Agenda.objects.latest("id")
        self.assertEqual(agenda.requester_entity_type, "Empresa/Órgão")
        self.assertEqual(agenda.administrative_demand_type, "")

    def test_create_internal_administrative_demand_without_subtype_is_rejected(self):
        payload = self.base_payload()
        payload["requester_entity_type"] = "Demanda Administrativa"
        payload["administrative_demand_type"] = ""
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("administrative_demand_type", response.data)

    def test_edit_internal_request_keeps_saved_subtype(self):
        agenda = Agenda.objects.create(
            title="Entrevista interna",
            description="Descrição",
            date=date(2026, 8, 11),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Sede OLS",
            institution_location="Sede OLS",
            address="Rua Exemplo, 10",
            city="Rio de Janeiro",
            state="RJ",
            external_responsible="Maria Gestora",
            external_responsible_phone="21999999999",
            external_email="maria@example.com",
            requester_role="Gestora",
            requester_entity_type="Demanda Administrativa",
            administrative_demand_type="INTERVIEW",
            action_type="Palestra",
            participant_range="51 a 100",
            age_ranges="11 - 14 anos (ensino fundamental - anos finais)",
            accessibility_access="Não se aplica, pois será realizado no térreo",
            has_accessible_bathrooms="Sim",
            quantity=100,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            origin=Agenda.Origin.INTERNAL,
            status=Agenda.Status.PENDING,
        )

        response = self.client.patch(reverse("agendas-detail", args=[agenda.id]), {
            "requester_entity_type": "Demanda Administrativa",
            "administrative_demand_type": "INTERVIEW",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.administrative_demand_type, "INTERVIEW")

    def test_edit_switching_away_from_administrative_clears_subtype(self):
        agenda = Agenda.objects.create(
            title="Entrevista interna",
            description="Descrição",
            date=date(2026, 8, 11),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Sede OLS",
            institution_location="Sede OLS",
            address="Rua Exemplo, 10",
            city="Rio de Janeiro",
            state="RJ",
            external_responsible="Maria Gestora",
            external_responsible_phone="21999999999",
            external_email="maria@example.com",
            requester_role="Gestora",
            requester_entity_type="Demanda Administrativa",
            administrative_demand_type="INTERVIEW",
            action_type="Palestra",
            participant_range="51 a 100",
            age_ranges="11 - 14 anos (ensino fundamental - anos finais)",
            accessibility_access="Não se aplica, pois será realizado no térreo",
            has_accessible_bathrooms="Sim",
            quantity=100,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            origin=Agenda.Origin.INTERNAL,
            status=Agenda.Status.PENDING,
        )

        response = self.client.patch(reverse("agendas-detail", args=[agenda.id]), {
            "requester_entity_type": "Empresa/Órgão",
            "administrative_demand_type": "INTERVIEW",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.requester_entity_type, "Empresa/Órgão")
        self.assertEqual(agenda.administrative_demand_type, "")

    def test_edit_switching_to_administrative_requires_subtype(self):
        agenda = Agenda.objects.create(
            title="Solicitação comum",
            description="Descrição",
            date=date(2026, 8, 11),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Sede OLS",
            institution_location="Sede OLS",
            address="Rua Exemplo, 10",
            city="Rio de Janeiro",
            state="RJ",
            external_responsible="Maria Gestora",
            external_responsible_phone="21999999999",
            external_email="maria@example.com",
            requester_role="Gestora",
            requester_entity_type="Empresa/Órgão",
            action_type="Palestra",
            participant_range="51 a 100",
            age_ranges="11 - 14 anos (ensino fundamental - anos finais)",
            accessibility_access="Não se aplica, pois será realizado no térreo",
            has_accessible_bathrooms="Sim",
            quantity=100,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            origin=Agenda.Origin.INTERNAL,
            status=Agenda.Status.PENDING,
        )

        response = self.client.patch(reverse("agendas-detail", args=[agenda.id]), {
            "requester_entity_type": "Demanda Administrativa",
            "administrative_demand_type": "",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("administrative_demand_type", response.data)

    def test_agenda_serializer_returns_new_field(self):
        agenda = Agenda.objects.create(
            title="Entrevista interna",
            description="Descrição",
            date=date(2026, 8, 11),
            start_time=time(9, 0),
            end_time=time(10, 0),
            location="Sede OLS",
            institution_location="Sede OLS",
            address="Rua Exemplo, 10",
            city="Rio de Janeiro",
            state="RJ",
            external_responsible="Maria Gestora",
            external_responsible_phone="21999999999",
            external_email="maria@example.com",
            requester_role="Gestora",
            requester_entity_type="Demanda Administrativa",
            administrative_demand_type="INTERVIEW",
            action_type="Palestra",
            participant_range="51 a 100",
            age_ranges="11 - 14 anos (ensino fundamental - anos finais)",
            accessibility_access="Não se aplica, pois será realizado no térreo",
            has_accessible_bathrooms="Sim",
            quantity=100,
            created_by=self.admin,
            responsible=self.admin,
            sector=self.sector,
            origin=Agenda.Origin.INTERNAL,
            status=Agenda.Status.PENDING,
        )

        data = AgendaSerializer(agenda).data

        self.assertEqual(data["administrative_demand_type"], "INTERVIEW")
