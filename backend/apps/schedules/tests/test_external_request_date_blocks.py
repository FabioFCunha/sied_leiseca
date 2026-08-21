from django.urls import reverse
from django.core import signing
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.schedules.models import Agenda, ExternalRequestDateBlock, Sector
from apps.schedules.serializers import ExternalRequestDateBlockSerializer, PublicAgendaRequestSerializer
from apps.schedules.emails import PUBLIC_REQUEST_SALT


class ExternalRequestDateBlockTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin-block@test.local", password="pwd", full_name="Admin", role=User.Role.ADMIN)
        self.manager = User.objects.create_user(email="manager-block@test.local", password="pwd", full_name="Manager", role=User.Role.MANAGER)
        self.user = User.objects.create_user(email="user-block@test.local", password="pwd", full_name="User", role=User.Role.USER)
        self.url = reverse("external-request-date-blocks-list")
        self.public_url = reverse("public_external_request_date_blocks")
        self.public_request_url = reverse("public_agenda_request")
        self.internal_request_url = reverse("internal_agenda_request")

    def payload(self, date_value):
        return {"title": "Palestra", "description": "Teste", "date": date_value, "start_time": "09:00", "end_time": "10:00", "action_type": "Palestra", "institution_location": "Escola", "address": "Rua 1", "city": "Rio", "external_responsible": "Ana", "external_responsible_phone": "21999999999", "external_email": "ana@example.com", "requester_entity_type": "Instituição de Ensino"}

    def create_block(self, start_date="2026-08-22", end_date="2026-08-26", **kwargs):
        return ExternalRequestDateBlock.objects.create(start_date=start_date, end_date=end_date, created_by=self.admin, updated_by=self.admin, **kwargs)

    def test_admin_and_manager_can_create_but_other_profiles_cannot(self):
        payload = {"start_date": "2026-08-22", "end_date": "2026-08-26", "is_active": True}
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(self.url, payload, format="json").status_code, 201)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_public_endpoint_hides_reason_and_inactive_blocks(self):
        ExternalRequestDateBlock.objects.create(start_date="2026-08-22", end_date="2026-08-26", reason="Interno", is_active=True, created_by=self.admin, updated_by=self.admin)
        ExternalRequestDateBlock.objects.create(start_date="2026-09-01", end_date="2026-09-02", reason="Não expor", is_active=False, created_by=self.admin, updated_by=self.admin)
        response = self.client.get(self.public_url, {"date_from": "2026-08-01", "date_to": "2026-08-31"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{"start_date": "2026-08-22", "end_date": "2026-08-26"}])

    def test_rejects_overlapping_active_ranges(self):
        ExternalRequestDateBlock.objects.create(start_date="2026-08-22", end_date="2026-08-26", is_active=True, created_by=self.admin, updated_by=self.admin)
        serializer = ExternalRequestDateBlockSerializer(data={"start_date": "2026-08-25", "end_date": "2026-08-27", "is_active": True})
        self.assertFalse(serializer.is_valid())
        self.assertIn("start_date", serializer.errors)

    def test_external_request_is_blocked_but_internal_request_is_not(self):
        ExternalRequestDateBlock.objects.create(start_date="2026-08-22", end_date="2026-08-26", is_active=True, created_by=self.admin, updated_by=self.admin)
        payload = {"title": "Palestra", "description": "Teste", "date": "2026-08-22", "start_time": "09:00", "end_time": "10:00", "action_type": "Palestra", "institution_location": "Escola", "address": "Rua 1", "city": "Rio", "external_responsible": "Ana", "external_responsible_phone": "21999999999", "external_email": "ana@example.com", "requester_entity_type": "Instituição de Ensino"}
        external = PublicAgendaRequestSerializer(data=payload, context={"is_internal_request": False})
        self.assertFalse(external.is_valid())
        self.assertIn("date", external.errors)
        internal = PublicAgendaRequestSerializer(data=payload, context={"is_internal_request": True})
        self.assertTrue(internal.is_valid(), internal.errors)

    def test_each_non_administrative_role_is_forbidden(self):
        for role in [User.Role.SUPERVISOR, User.Role.USER, User.Role.SUPPORT, User.Role.VISITOR]:
            user = User.objects.create_user(email=f"restricted-{role.lower()}-block@test.local", password="pwd", full_name=role, role=role)
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(self.url).status_code, 403, role)

    def test_public_request_boundaries_are_inclusive_and_neighbors_are_allowed(self):
        self.create_block(reason="Motivo interno")
        self.assertEqual(self.client.post(self.public_request_url, self.payload("2026-08-21"), format="json").status_code, 201)
        for blocked_date in ["2026-08-22", "2026-08-24", "2026-08-26"]:
            response = self.client.post(self.public_request_url, self.payload(blocked_date), format="json")
            self.assertEqual(response.status_code, 400, blocked_date)
            self.assertIn("date", response.data)
            self.assertEqual(
                response.data["date"][0],
                "O período de 22/08/2026 a 26/08/2026 está indisponível para solicitações externas. Por favor, escolha uma data fora desse período.",
            )
            self.assertNotIn("Motivo interno", response.data["date"][0])
        self.assertEqual(self.client.post(self.public_request_url, self.payload("2026-08-27"), format="json").status_code, 201)

    def test_single_day_block_uses_single_date_message(self):
        self.create_block("2026-08-22", "2026-08-22", reason="Não expor")
        response = self.client.post(self.public_request_url, self.payload("2026-08-22"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["date"][0],
            "A data 22/08/2026 está indisponível para solicitações externas. Por favor, escolha outra data.",
        )
        self.assertNotIn("Não expor", response.data["date"][0])

    def test_internal_post_and_internal_agenda_update_are_not_blocked(self):
        self.create_block()
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.internal_request_url, self.payload("2026-08-22"), format="json")
        self.assertEqual(response.status_code, 201)
        agenda = Agenda.objects.get(pk=response.data["protocol"])
        self.assertEqual(agenda.origin, Agenda.Origin.INTERNAL)
        response = self.client.patch(reverse("agendas-detail", args=[agenda.id]), {"date": "2026-08-23"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_existing_external_agenda_is_not_changed_by_new_block(self):
        response = self.client.post(self.public_request_url, self.payload("2026-08-22"), format="json")
        agenda = Agenda.objects.get(pk=response.data["protocol"])
        self.create_block()
        agenda.refresh_from_db()
        self.assertEqual(agenda.origin, Agenda.Origin.PUBLIC_FORM)
        self.assertEqual(str(agenda.date), "2026-08-22")

    def test_existing_public_request_can_keep_its_date_but_cannot_move_to_a_blocked_date(self):
        response = self.client.post(self.public_request_url, self.payload("2026-08-22"), format="json")
        agenda = Agenda.objects.get(pk=response.data["protocol"])
        self.create_block("2026-08-22", "2026-08-23")
        token = signing.dumps({"agenda": agenda.id}, salt=PUBLIC_REQUEST_SALT)
        update_url = reverse("public_agenda_request_update", args=[token])
        same_date = self.client.patch(update_url, {"date": "2026-08-22", "start_time": "10:00", "end_time": "11:00"}, format="json")
        self.assertEqual(same_date.status_code, 200)
        blocked_new_date = self.client.patch(update_url, {"date": "2026-08-23", "start_time": "10:00", "end_time": "11:00"}, format="json")
        self.assertEqual(blocked_new_date.status_code, 400)
        self.assertIn("date", blocked_new_date.data)

    def test_overlap_variants_and_invalid_dates_are_rejected(self):
        self.create_block()
        variants = [("2026-08-22", "2026-08-26"), ("2026-08-20", "2026-08-23"), ("2026-08-25", "2026-08-30"), ("2026-08-23", "2026-08-25"), ("2026-08-20", "2026-08-30")]
        for start_date, end_date in variants:
            serializer = ExternalRequestDateBlockSerializer(data={"start_date": start_date, "end_date": end_date, "is_active": True})
            self.assertFalse(serializer.is_valid(), (start_date, end_date))
        invalid = ExternalRequestDateBlockSerializer(data={"start_date": "2026-08-27", "end_date": "2026-08-26", "is_active": True})
        self.assertFalse(invalid.is_valid())
        self.assertIn("end_date", invalid.errors)

    def test_adjacent_and_inactive_ranges_are_allowed(self):
        self.create_block()
        adjacent = ExternalRequestDateBlockSerializer(data={"start_date": "2026-08-27", "end_date": "2026-08-30", "is_active": True})
        self.assertTrue(adjacent.is_valid(), adjacent.errors)
        self.create_block("2026-09-01", "2026-09-05", is_active=False)
        inactive_conflict = ExternalRequestDateBlockSerializer(data={"start_date": "2026-09-01", "end_date": "2026-09-05", "is_active": True})
        self.assertTrue(inactive_conflict.is_valid(), inactive_conflict.errors)

    def test_admin_crud_audit_and_payload_cannot_spoof_users(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, {"start_date": "2026-10-01", "end_date": "2026-10-02", "reason": "Interno", "created_by": self.user.id, "updated_by": self.user.id}, format="json")
        self.assertEqual(response.status_code, 201)
        block = ExternalRequestDateBlock.objects.get(pk=response.data["id"])
        self.assertEqual(block.created_by, self.admin)
        self.client.force_authenticate(self.manager)
        response = self.client.patch(reverse("external-request-date-blocks-detail", args=[block.id]), {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.updated_by, self.manager)
        self.assertFalse(block.is_active)
        self.assertEqual(self.client.delete(reverse("external-request-date-blocks-detail", args=[block.id])).status_code, 204)

    def test_edit_excludes_itself_but_rejects_another_overlap(self):
        first = self.create_block("2026-10-01", "2026-10-02")
        second = self.create_block("2026-10-05", "2026-10-06")
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(reverse("external-request-date-blocks-detail", args=[first.id]), {"reason": "Alterado"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(reverse("external-request-date-blocks-detail", args=[second.id]), {"start_date": "2026-10-02"}, format="json").status_code, 400)

    def test_public_endpoint_is_read_only_and_validates_its_range(self):
        self.create_block()
        self.assertEqual(self.client.get(self.public_url).status_code, 400)
        self.assertEqual(self.client.get(self.public_url, {"date_from": "x", "date_to": "2026-08-30"}).status_code, 400)
        self.assertEqual(self.client.get(self.public_url, {"date_from": "2026-08-30", "date_to": "2026-08-01"}).status_code, 400)
        self.assertEqual(self.client.post(self.public_url, {}, format="json").status_code, 405)
        self.assertEqual(self.client.put(self.public_url, {}, format="json").status_code, 405)
        self.assertEqual(self.client.patch(self.public_url, {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(self.public_url).status_code, 405)
