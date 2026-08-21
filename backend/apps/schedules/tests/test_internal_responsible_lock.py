from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agenda, AgendaMaterial, Material, Sector
from apps.schedules.serializers import AgendaSerializer


class InternalResponsibleLockApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.creator = User.objects.create_user(
            email="creator-internal@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Criador Interno",
        )
        self.editor = User.objects.create_user(
            email="editor-internal@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Gestor Editor",
        )
        self.other_responsible = User.objects.create_user(
            email="other-internal@test.com",
            password="pwd",
            role=User.Role.SUPERVISOR,
            full_name="Outro Respons?vel",
        )
        self.manager_with_sector = User.objects.create_user(
            email="manager-with-sector@test.com",
            password="pwd",
            role=User.Role.MANAGER,
            full_name="Gestor Com Setor",
        )
        self.manager_without_sector = User.objects.create_user(
            email="manager-without-sector@test.com",
            password="pwd",
            role=User.Role.MANAGER,
            full_name="Gestor Sem Setor",
        )
        self.regular_user = User.objects.create_user(
            email="regular-user@test.com",
            password="pwd",
            role=User.Role.USER,
            full_name="Usuario Sem Permissao",
        )
        self.internal_url = reverse("internal_agenda_request")
        self.internal_sector, _ = Sector.objects.get_or_create(name="Solicita??es internas")
        self.public_sector = Sector.objects.create(name="Setor Externo")
        self.manager_with_sector.sector = self.public_sector
        self.manager_with_sector.save(update_fields=["sector"])

    def internal_payload(self):
        return {
            "title": "Solicita??o interna",
            "description": "Descri??o da solicita??o",
            "date": "2026-08-12",
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
            "requester_entity_type": "Empresa/??rg??o",
            "participant_range": "51 a 100",
            "age_ranges": "11 - 14 anos (ensino fundamental - anos finais)",
            "accessibility_access": "",
            "has_accessible_bathrooms": "Sim",
            "quantity": 100,
        }

    def create_internal_agenda(self):
        self.client.force_authenticate(self.creator)
        response = self.client.post(self.internal_url, self.internal_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return Agenda.objects.get(id=response.data["protocol"])

    def create_public_agenda(self):
        return Agenda.objects.create(
            title="Agenda publica",
            description="Descri??o",
            date=date(2026, 8, 13),
            start_time=time(10, 0),
            end_time=time(11, 0),
            location="Local externo",
            institution_location="Local externo",
            address="Rua Externa, 20",
            city="Rio de Janeiro",
            state="RJ",
            external_responsible="Jo?o P?blico",
            external_responsible_phone="21988888888",
            external_email="joao@example.com",
            requester_entity_type="Empresa/??rg??o",
            action_type="Palestra",
            created_by=self.creator,
            responsible=self.creator,
            sector=self.public_sector,
            origin=Agenda.Origin.PUBLIC_FORM,
            status=Agenda.Status.PENDING,
        )

    def test_internal_request_starts_with_responsible_equal_to_created_by(self):
        agenda = self.create_internal_agenda()

        self.assertEqual(agenda.origin, Agenda.Origin.INTERNAL)
        self.assertEqual(agenda.responsible_id, agenda.created_by_id)
        self.assertEqual(agenda.responsible_id, self.creator.id)

    def test_patch_internal_agenda_keeps_original_responsible_and_saves_other_fields(self):
        agenda = self.create_internal_agenda()
        self.client.force_authenticate(self.editor)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {
                "title": "Solicita??o interna atualizada",
                "responsible": self.other_responsible.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.title, "Solicita??o interna atualizada")
        self.assertEqual(agenda.responsible_id, self.creator.id)
        self.assertEqual(agenda.created_by_id, self.creator.id)
        self.assertEqual(agenda.last_edited_by_id, self.editor.id)
        self.assertEqual(response.data["last_edited_by_name"], self.editor.full_name)

    def test_non_internal_agenda_still_allows_responsible_change(self):
        agenda = self.create_public_agenda()
        self.client.force_authenticate(self.editor)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {"responsible": self.other_responsible.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.responsible_id, self.other_responsible.id)
        self.assertEqual(agenda.created_by_id, self.creator.id)

    def test_manager_with_sector_approval_persists_authenticated_user_as_responsible(self):
        agenda = self.create_public_agenda()
        self.client.force_authenticate(self.manager_with_sector)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {"status": Agenda.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.status, Agenda.Status.APPROVED)
        self.assertEqual(agenda.responsible_id, self.manager_with_sector.id)

    def test_approval_requires_quantity_for_selected_material(self):
        agenda = self.create_public_agenda()
        material = Material.objects.create(name="Barraca")
        AgendaMaterial.objects.create(agenda=agenda, material=material, quantity=None)
        self.client.force_authenticate(self.manager_with_sector)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {"status": Agenda.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("materials", response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.status, Agenda.Status.PENDING)

    def test_manager_without_sector_approval_persists_authenticated_user_as_responsible(self):
        agenda = self.create_public_agenda()
        self.client.force_authenticate(self.manager_without_sector)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {"status": Agenda.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.responsible_id, self.manager_without_sector.id)

    def test_manager_without_sector_rejection_persists_authenticated_user_as_responsible(self):
        agenda = self.create_public_agenda()
        self.client.force_authenticate(self.manager_without_sector)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {"status": Agenda.Status.CANCELLED, "cancel_reason": "Recusa justificada."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.status, Agenda.Status.CANCELLED)
        self.assertEqual(agenda.responsible_id, self.manager_without_sector.id)

    def test_decision_ignores_spoofed_responsible_and_uses_authenticated_user(self):
        agenda = self.create_public_agenda()
        self.client.force_authenticate(self.manager_with_sector)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {
                "status": Agenda.Status.APPROVED,
                "responsible": self.manager_without_sector.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.responsible_id, self.manager_with_sector.id)

    def test_internal_decision_updates_responsible_to_authenticated_user(self):
        agenda = self.create_internal_agenda()
        self.client.force_authenticate(self.manager_without_sector)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {"status": Agenda.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        agenda.refresh_from_db()
        self.assertEqual(agenda.status, Agenda.Status.APPROVED)
        self.assertEqual(agenda.responsible_id, self.manager_without_sector.id)
        self.assertEqual(agenda.created_by_id, self.creator.id)

    def test_user_without_permission_cannot_approve_or_override_responsible(self):
        agenda = self.create_public_agenda()
        self.client.force_authenticate(self.regular_user)

        response = self.client.patch(
            reverse("agendas-detail", args=[agenda.id]),
            {
                "status": Agenda.Status.APPROVED,
                "responsible": self.manager_with_sector.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        agenda.refresh_from_db()
        self.assertEqual(agenda.status, Agenda.Status.PENDING)
        self.assertEqual(agenda.responsible_id, self.creator.id)


class InternalResponsibleLockSerializerTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            email="serializer-creator@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Criador Serializer",
        )
        self.other_responsible = User.objects.create_user(
            email="serializer-other@test.com",
            password="pwd",
            role=User.Role.ADMIN,
            full_name="Outro Serializer",
        )
        self.sector = Sector.objects.create(name="Setor Serializer")

    def test_serializer_ignores_manual_responsible_change_for_internal_agenda(self):
        agenda = Agenda.objects.create(
            title="Agenda interna",
            description="Descri??o",
            date=date(2026, 8, 14),
            start_time=time(8, 0),
            end_time=time(9, 0),
            location="Sede",
            institution_location="Sede",
            address="Rua Interna, 30",
            city="Rio de Janeiro",
            state="RJ",
            external_responsible="Maria",
            external_responsible_phone="21977777777",
            external_email="maria@example.com",
            requester_entity_type="Empresa/??rg??o",
            action_type="Palestra",
            created_by=self.creator,
            responsible=self.creator,
            sector=self.sector,
            origin=Agenda.Origin.INTERNAL,
            status=Agenda.Status.PENDING,
        )

        serializer = AgendaSerializer(instance=agenda, data={"responsible": self.other_responsible.id}, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        updated.refresh_from_db()
        self.assertEqual(updated.responsible_id, self.creator.id)
        self.assertEqual(updated.created_by_id, self.creator.id)
