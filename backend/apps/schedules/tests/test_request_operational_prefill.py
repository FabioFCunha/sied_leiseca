from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.models import ActionType, Agenda
from apps.schedules.views import _resolve_requested_operational_action_type


class RequestedOperationalActionTypeTests(TestCase):
    def setUp(self):
        for name, category in (
            ("Palestra Escola Pública", ActionType.Category.LECTURE),
            ("Palestra Escola Privada", ActionType.Category.LECTURE),
            ("Palestra Empresa", ActionType.Category.LECTURE),
            ("Ação Educativa", ActionType.Category.EDUCATIONAL_ACTION),
        ):
            ActionType.objects.update_or_create(
                name=name,
                defaults={"category": category, "is_active": True},
            )

    def assert_resolution(self, requester_type, expected_name):
        name, reference = _resolve_requested_operational_action_type("Palestra", requester_type)

        self.assertEqual(name, expected_name)
        self.assertIsNotNone(reference)
        self.assertEqual(reference.name, expected_name)

    def test_public_school_request_becomes_public_school_lecture(self):
        self.assert_resolution("Instituição de Ensino Público", "Palestra Escola Pública")

    def test_private_school_request_becomes_private_school_lecture(self):
        self.assert_resolution("Instituição de Ensino Privado", "Palestra Escola Privada")

    def test_business_request_becomes_business_lecture(self):
        self.assert_resolution("Empresa/Órgão Privado", "Palestra Empresa")

    def test_educational_action_uses_active_operational_type(self):
        name, reference = _resolve_requested_operational_action_type(
            "Ação de educação/conscientização",
            "Instituição de Ensino Público",
        )

        self.assertEqual(name, "Ação Educativa")
        self.assertEqual(reference.name, "Ação Educativa")

    def test_generic_lecture_is_preserved_when_nature_is_missing(self):
        name, reference = _resolve_requested_operational_action_type(
            "Palestra",
            "Instituição de Ensino",
        )

        self.assertEqual(name, "Palestra")
        self.assertIsNone(reference)


class InternalRequestOperationalPrefillTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="request-prefill@test.local",
            password="pwd",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(self.user)
        self.action_type, _ = ActionType.objects.update_or_create(
            name="Palestra Escola Pública",
            defaults={
                "category": ActionType.Category.LECTURE,
                "is_active": True,
            },
        )

    def test_internal_request_persists_classification_and_operational_type(self):
        response = self.client.post(reverse("internal_agenda_request"), {
            "title": "Palestra - Escola Teste",
            "description": "Solicitação interna",
            "date": "2026-09-10",
            "start_time": "10:00",
            "end_time": "11:00",
            "action_type": "Palestra",
            "institution_location": "Escola Teste",
            "address": "Rua Teste, 10",
            "city": "Rio de Janeiro",
            "external_responsible": "Responsável Teste",
            "external_responsible_phone": "21999999999",
            "external_email": "responsavel@test.local",
            "requester_entity_type": "Instituição de Ensino Público",
            "participant_range": "30 a 50",
            "age_ranges": "05 - 10 anos (ensino fundamental - anos iniciais)",
            "accessibility_access": "Sim",
            "has_accessible_bathrooms": "Sim",
            "image_authorization": "Autorizado",
            "quantity": 50,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        agenda = Agenda.objects.get(pk=response.data["protocol"])
        self.assertEqual(agenda.requester_entity_type, "Instituição de Ensino Público")
        self.assertEqual(agenda.action_type, "Palestra Escola Pública")
        self.assertEqual(agenda.action_type_ref, self.action_type)
