import io
import json
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.schedules.geocoding import GeocodingError, geocode_address, normalize_agenda_address
from apps.schedules.models import Agenda, Sector


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class AgendaGeocodingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="geocoding-admin@example.com",
            password="test-password",
            role="ADMIN",
        )
        self.sector = Sector.objects.create(name="Geocoding")

    def agenda(self, **overrides):
        values = {
            "title": "Ação geocodificada",
            "description": "Teste",
            "date": date.today(),
            "start_time": time(10, 0),
            "end_time": time(11, 0),
            "location": "Local",
            "address": "Rua da Assembleia, 10, Centro",
            "neighborhood": "Centro",
            "city": "Rio de Janeiro",
            "state": "RJ",
            "responsible": self.user,
            "created_by": self.user,
            "sector": self.sector,
            "status": Agenda.Status.APPROVED,
        }
        values.update(overrides)
        return Agenda.objects.create(**values)

    def run_command(self, *args):
        output = io.StringIO()
        call_command("backfill_agenda_coordinates", *args, stdout=output, stderr=output)
        return output.getvalue()

    def test_normalizes_complete_address_without_duplicates(self):
        agenda = self.agenda(address="  Rua da Assembleia, 10,  Centro, Rio de Janeiro - RJ, 20011-901  ")
        normalized = normalize_agenda_address(agenda)
        self.assertEqual(normalized, "Rua da Assembleia, 10, Centro, Rio de Janeiro - RJ, 20011-901, Brasil")
        self.assertEqual(normalized.count("Centro"), 1)
        self.assertIn("20011-901", normalized)

    def test_address_without_street_is_not_geocoded_from_institution_or_city(self):
        agenda = self.agenda(address="", institution_location="Instituição", city="Rio de Janeiro")
        self.assertEqual(normalize_agenda_address(agenda), "")

    def test_geocode_returns_decimal_coordinates(self):
        def opener(request, timeout):
            self.assertEqual(timeout, 5)
            self.assertEqual(request.headers["User-agent"], "SIED-Test/1.0")
            return FakeResponse([{"lat": "-22.90680000", "lon": "-43.17290000"}])

        result = geocode_address("Rua A, 1, Brasil", opener=opener, timeout=5, user_agent="SIED-Test/1.0")
        self.assertEqual(result, (Decimal("-22.90680000"), Decimal("-43.17290000")))

    def test_geocode_returns_none_when_address_is_not_found(self):
        result = geocode_address("Rua inexistente", opener=lambda request, timeout: FakeResponse([]))
        self.assertIsNone(result)

    def test_geocode_handles_connection_failure(self):
        def opener(request, timeout):
            raise URLError("offline")

        with self.assertRaises(GeocodingError):
            geocode_address("Rua A", opener=opener)

    def test_geocode_handles_timeout(self):
        def opener(request, timeout):
            raise TimeoutError("timeout")

        with self.assertRaises(GeocodingError):
            geocode_address("Rua A", opener=opener)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.time.sleep")
    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_dry_run_does_not_write_any_field(self, geocode, sleep):
        agenda = self.agenda()
        geocode.return_value = (Decimal("-22.9"), Decimal("-43.1"))
        before = (agenda.latitude, agenda.longitude, agenda.geocoding_address, agenda.geocoding_status, agenda.geocoding_attempted_at)

        output = self.run_command("--dry-run", "--limit", "1")

        agenda.refresh_from_db()
        after = (agenda.latitude, agenda.longitude, agenda.geocoding_address, agenda.geocoding_status, agenda.geocoding_attempted_at)
        self.assertEqual(after, before)
        self.assertIn("SIMULAÇÃO", output)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_command_persists_found_coordinates(self, geocode):
        agenda = self.agenda()
        geocode.return_value = (Decimal("-22.90000000"), Decimal("-43.10000000"))

        self.run_command("--limit", "1")

        agenda.refresh_from_db()
        self.assertEqual(agenda.geocoding_status, Agenda.GeocodingStatus.FOUND)
        self.assertEqual(agenda.latitude, Decimal("-22.90000000"))
        self.assertIsNotNone(agenda.geocoding_attempted_at)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address", return_value=None)
    def test_command_persists_not_found_without_fake_coordinates(self, geocode):
        agenda = self.agenda()
        self.run_command("--limit", "1")
        agenda.refresh_from_db()
        self.assertEqual(agenda.geocoding_status, Agenda.GeocodingStatus.NOT_FOUND)
        self.assertIsNone(agenda.latitude)
        self.assertIsNone(agenda.longitude)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_command_continues_after_connection_error(self, geocode):
        agenda = self.agenda()
        geocode.side_effect = GeocodingError("offline")
        output = self.run_command("--limit", "1")
        agenda.refresh_from_db()
        self.assertEqual(agenda.geocoding_status, Agenda.GeocodingStatus.PENDING)
        self.assertIn("erros: 1", output)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_does_not_repeat_unchanged_found_address(self, geocode):
        agenda = self.agenda(
            latitude=Decimal("-22.9"),
            longitude=Decimal("-43.1"),
            geocoding_status=Agenda.GeocodingStatus.FOUND,
        )
        agenda.geocoding_address = normalize_agenda_address(agenda)
        agenda.save(update_fields=["geocoding_address"])
        output = self.run_command("--limit", "1")
        geocode.assert_not_called()
        self.assertIn("ignorados: 1", output)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_retries_when_normalized_address_changes(self, geocode):
        agenda = self.agenda(
            latitude=Decimal("-22.9"), longitude=Decimal("-43.1"),
            geocoding_address="Endereço anterior", geocoding_status=Agenda.GeocodingStatus.FOUND,
        )
        geocode.return_value = (Decimal("-22.8"), Decimal("-43.2"))
        self.run_command("--limit", "1")
        agenda.refresh_from_db()
        geocode.assert_called_once()
        self.assertEqual(agenda.latitude, Decimal("-22.80000000"))

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_retry_not_found_is_explicit(self, geocode):
        agenda = self.agenda(geocoding_status=Agenda.GeocodingStatus.NOT_FOUND)
        agenda.geocoding_address = normalize_agenda_address(agenda)
        agenda.save(update_fields=["geocoding_address"])
        self.run_command("--limit", "1")
        geocode.assert_not_called()
        geocode.return_value = (Decimal("-22.8"), Decimal("-43.2"))
        self.run_command("--limit", "1", "--retry-not-found")
        geocode.assert_called_once()

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.time.sleep")
    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_limit_controls_processed_records(self, geocode, sleep):
        self.agenda(title="Primeira")
        self.agenda(title="Segunda", address="Rua B, 2")
        geocode.return_value = (Decimal("-22.9"), Decimal("-43.1"))
        output = self.run_command("--limit", "1")
        self.assertEqual(geocode.call_count, 1)
        self.assertIn("processados: 1", output)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_agenda_id_processes_only_the_found_agenda(self, geocode):
        target = self.agenda(id=5556, title="Protocolo selecionado")
        self.agenda(id=5557, title="Outro protocolo", address="Rua B, 2")
        geocode.return_value = (Decimal("-22.8"), Decimal("-43.2"))

        output = self.run_command("--agenda-id", str(target.id), "--dry-run")

        self.assertEqual(geocode.call_count, 1)
        self.assertIn("processados: 1", output)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_agenda_id_not_found_does_not_process_other_records(self, geocode):
        self.agenda(id=5557)

        output = self.run_command("--agenda-id", "5556", "--dry-run")

        geocode.assert_not_called()
        self.assertIn("Agenda 5556 não encontrada; nenhum registro processado.", output)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_agenda_id_dry_run_never_writes(self, geocode):
        target = self.agenda(id=5556)
        geocode.return_value = (Decimal("-22.8"), Decimal("-43.2"))

        self.run_command("--agenda-id", "5556", "--dry-run")

        target.refresh_from_db()
        self.assertIsNone(target.latitude)
        self.assertIsNone(target.longitude)
        self.assertEqual(target.geocoding_status, Agenda.GeocodingStatus.PENDING)
        self.assertIsNone(target.geocoding_attempted_at)

    @patch("apps.schedules.management.commands.backfill_agenda_coordinates.geocode_address")
    def test_agenda_id_real_run_writes_only_selected_agenda(self, geocode):
        target = self.agenda(id=5556, title="Protocolo selecionado")
        other = self.agenda(id=5557, title="Outro protocolo", address="Rua B, 2")
        geocode.return_value = (Decimal("-22.8"), Decimal("-43.2"))

        self.run_command("--agenda-id", "5556")

        target.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(target.geocoding_status, Agenda.GeocodingStatus.FOUND)
        self.assertEqual(target.latitude, Decimal("-22.80000000"))
        self.assertEqual(other.geocoding_status, Agenda.GeocodingStatus.PENDING)
        self.assertIsNone(other.latitude)
        self.assertEqual(geocode.call_count, 1)
    def test_dashboard_sends_coordinates_and_keeps_missing_agenda(self):
        located = self.agenda(latitude=Decimal("-22.9068"), longitude=Decimal("-43.1729"), geocoding_status=Agenda.GeocodingStatus.FOUND)
        missing = self.agenda(title="Sem coordenadas", address="", geocoding_status=Agenda.GeocodingStatus.NOT_FOUND)
        cache.clear()
        client = APIClient()
        unauthenticated = client.get("/api/agendas/dashboard/", {"date": date.today().isoformat()})
        self.assertIn(unauthenticated.status_code, (401, 403))
        client.force_authenticate(self.user)
        response = client.get("/api/agendas/dashboard/", {"date": date.today().isoformat()})
        self.assertEqual(response.status_code, 200)
        rows = {row["id"]: row for row in response.data["operations"]["field_operations"]}
        self.assertEqual(rows[located.id]["latitude"], float(located.latitude))
        self.assertEqual(rows[located.id]["longitude"], float(located.longitude))
        self.assertEqual(rows[located.id]["geocoding_status"], Agenda.GeocodingStatus.FOUND)
        self.assertIsNone(rows[missing.id]["latitude"])
        self.assertIsNone(rows[missing.id]["longitude"])
        self.assertEqual(rows[missing.id]["geocoding_status"], Agenda.GeocodingStatus.NOT_FOUND)
