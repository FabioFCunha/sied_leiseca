import io
import json
import socket
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError

from django.core.management import call_command
from django.test import SimpleTestCase

from apps.inspection.horus_sync import (
    CUT_OFF_DATE,
    FINE_FIELDS,
    FINES_SQL,
    INITIAL_SECTION_SQL,
    INCREMENTAL_SECTION_SQL,
    OPERATION_FIELDS,
    OPERATIONS_SQL,
    SECTION_FIELDS,
    HorusInspectionSyncer,
    HorusSyncError,
    empty_state,
    ensure_cutoff_date,
    load_state_file,
)


def make_uuid(index: int) -> str:
    return f"00000000-0000-4000-8000-{index:012d}"


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized_sql = " ".join(sql.split())
        self.connection.executed_sql.append((normalized_sql, params))
        if "FROM rcols_sections s INNER JOIN candidate_sections c ON c.id = s.id" in normalized_sql:
            self._rows = self.connection.next_section_batch()
        elif "FROM rcols_section_twos WHERE rcols_section_id = ANY(%s::uuid[])" in normalized_sql:
            requested = set((params or [()])[0])
            self._rows = [row for row in self.connection.operation_rows if row[1] in requested]
        elif "FROM rcols_fineds WHERE rcols_section_twos_id = ANY(%s::uuid[])" in normalized_sql:
            requested = set((params or [()])[0])
            self._rows = [row for row in self.connection.fine_rows if row[1] in requested]
        else:
            raise AssertionError(f"SQL inesperado: {normalized_sql}")

    def fetchall(self):
        return list(self._rows)


class FakeConnection:
    def __init__(self, *, section_batches, operation_rows, fine_rows):
        self.section_batches = [list(batch) for batch in section_batches]
        self.operation_rows = list(operation_rows)
        self.fine_rows = list(fine_rows)
        self.executed_sql = []
        self.closed = False
        self.set_session_calls = []

    def cursor(self):
        return FakeCursor(self)

    def set_session(self, **kwargs):
        self.set_session_calls.append(kwargs)

    def close(self):
        self.closed = True

    def next_section_batch(self):
        if not self.section_batches:
            return []
        return self.section_batches.pop(0)


class FakeHttpResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def build_http_error(status_code, body):
    return HTTPError(
        url="https://sied.local/api/inspection/sync/reports/",
        code=status_code,
        msg="error",
        hdrs=None,
        fp=io.BytesIO(json.dumps(body).encode("utf-8")),
    )


class HorusSyncFixturesMixin:
    def setUp(self):
        super().setUp()
        self.base_env = {
            "HORUS_DB_HOST": "10.0.0.5",
            "HORUS_DB_PORT": "5432",
            "HORUS_DB_NAME": "horus",
            "HORUS_DB_USER": "readonly",
            "HORUS_DB_PASSWORD": "secret-password",
            "SIED_INSPECTION_SYNC_URL": "https://sied.local/api/inspection/sync/reports/",
            "SIED_INSPECTION_SYNC_TOKEN": "super-secret-token",
        }
        self.section_1_id = make_uuid(1)
        self.section_2_id = make_uuid(2)
        self.section_3_id = make_uuid(3)
        self.operation_1_id = make_uuid(101)
        self.operation_2_id = make_uuid(102)
        self.operation_3_id = make_uuid(103)
        self.operation_orphan_id = make_uuid(999)
        self.section_1 = self.make_section(
            section_id=self.section_1_id,
            operation_date=date(2026, 8, 10),
            section_updated_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
            candidate_updated_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
            team="A3",
        )
        self.section_2 = self.make_section(
            section_id=self.section_2_id,
            operation_date=date(2026, 8, 11),
            section_updated_at=datetime(2026, 8, 11, 9, 10, tzinfo=timezone.utc),
            candidate_updated_at=datetime(2026, 8, 11, 9, 10, tzinfo=timezone.utc),
            team="B4",
            management_id=15,
            military_chief_id=make_uuid(202),
        )
        self.section_3 = self.make_section(
            section_id=self.section_3_id,
            operation_date=date(2026, 8, 12),
            section_updated_at=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
            candidate_updated_at=datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
            team="C5",
        )
        self.section_1_operation_changed = self.make_section(
            section_id=self.section_1_id,
            operation_date=date(2026, 8, 10),
            section_updated_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
            candidate_updated_at=datetime(2026, 8, 12, 13, 10, tzinfo=timezone.utc),
            team="A3",
        )
        self.section_1_fine_changed = self.make_section(
            section_id=self.section_1_id,
            operation_date=date(2026, 8, 10),
            section_updated_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
            candidate_updated_at=datetime(2026, 8, 12, 13, 20, tzinfo=timezone.utc),
            team="A3",
        )
        self.operation_1 = self.make_operation(
            operation_id=self.operation_1_id,
            section_id=self.section_1_id,
            updated_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
        )
        self.operation_1_updated = self.make_operation(
            operation_id=self.operation_1_id,
            section_id=self.section_1_id,
            updated_at=datetime(2026, 8, 12, 13, 10, tzinfo=timezone.utc),
        )
        self.operation_2 = self.make_operation(
            operation_id=self.operation_2_id,
            section_id=self.section_1_id,
            updated_at=datetime(2026, 8, 10, 8, 36, tzinfo=timezone.utc),
            approach=None,
            reconductor=0,
            refusal=None,
            cnh_collected=None,
            fined=0,
            vehicle_resolutions="",
            administrative_tests="",
        )
        self.operation_3 = self.make_operation(
            operation_id=self.operation_3_id,
            section_id=self.section_2_id,
            updated_at=datetime(2026, 8, 11, 9, 10, tzinfo=timezone.utc),
        )
        self.operation_orphan = self.make_operation(
            operation_id=self.operation_orphan_id,
            section_id=make_uuid(404),
            updated_at=datetime(2026, 8, 10, 8, 37, tzinfo=timezone.utc),
        )
        self.fine_1 = self.make_fine(
            fine_id=123,
            operation_id=self.operation_1_id,
            updated_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
            quant=2,
        )
        self.fine_1_updated = self.make_fine(
            fine_id=123,
            operation_id=self.operation_1_id,
            updated_at=datetime(2026, 8, 12, 13, 20, tzinfo=timezone.utc),
            quant=2,
        )
        self.fine_2 = self.make_fine(
            fine_id=124,
            operation_id=self.operation_2_id,
            updated_at=datetime(2026, 8, 10, 8, 36, 30, tzinfo=timezone.utc),
            quant=None,
        )
        self.fine_orphan = self.make_fine(
            fine_id=9999,
            operation_id=make_uuid(4040),
            updated_at=datetime(2026, 8, 10, 8, 38, tzinfo=timezone.utc),
            quant=1,
        )

    def make_section(
        self,
        *,
        section_id: str,
        operation_date: date,
        section_updated_at: datetime,
        candidate_updated_at: datetime,
        team: str,
        management_id=None,
        military_chief_id=None,
    ):
        return (
            section_id,
            999,
            management_id,
            military_chief_id,
            f"Chefe civil {team}",
            f"Chefe militar {team}",
            team,
            operation_date,
            f"Equipe civil {team}",
            f"Equipe militar {team}",
            "Sem alteracoes",
            2,
            0,
            "",
            f"VTR-{team}",
            "Sem alteracoes",
            "Sem alteracao de material",
            section_updated_at,
            "38 BPM",
            "54-0934\nSubten exemplo",
            "54-0934",
            "Baixa abordagem justificada",
            "AI-123",
            "AI-123 detalhado",
            "Alteracoes diversas",
            datetime.combine(operation_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=8),
            section_updated_at,
            candidate_updated_at,
        )

    def make_operation(
        self,
        *,
        operation_id: str,
        section_id: str,
        updated_at: datetime,
        approach=93,
        reconductor=10,
        refusal=5,
        cnh_collected=0,
        fined=44,
        vehicle_resolutions="003 contran",
        administrative_tests="Sem Alteracoes",
    ):
        return (
            operation_id,
            section_id,
            "Rua Ficticia, 100",
            "Vista Alegre",
            "",
            "20:00",
            "20:45",
            "21:40",
            "02:00",
            approach,
            reconductor,
            refusal,
            0,
            88,
            0,
            0,
            0,
            "",
            cnh_collected,
            fined,
            0,
            270,
            0,
            0,
            0,
            1,
            vehicle_resolutions,
            administrative_tests,
            updated_at - timedelta(minutes=1),
            updated_at,
            "21250-392",
            "Rua Ficticia",
            "Rio de Janeiro",
            "Vista Alegre",
            "",
        )

    def make_fine(self, *, fine_id: int, operation_id: str, updated_at: datetime, quant):
        return (
            fine_id,
            operation_id,
            "Cod.659-92",
            quant,
            updated_at - timedelta(minutes=1),
            updated_at,
        )

    def make_initial_sections(self, count: int):
        sections = []
        for index in range(1, count + 1):
            section_id = make_uuid(1000 + index)
            operation_date = date(2026, 8, 10) + timedelta(days=(index - 1) // 3)
            candidate_updated_at = datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc) + timedelta(minutes=index)
            sections.append(
                self.make_section(
                    section_id=section_id,
                    operation_date=operation_date,
                    section_updated_at=candidate_updated_at,
                    candidate_updated_at=candidate_updated_at,
                    team=f"T{index:02d}",
                )
            )
        return sections

    def build_connection(self, *, section_batches=None, operation_rows=None, fine_rows=None):
        return FakeConnection(
            section_batches=section_batches or [[self.section_1]],
            operation_rows=operation_rows or [self.operation_1],
            fine_rows=fine_rows or [self.fine_1],
        )

    def build_syncer(self, *, connection, opener, state_file):
        return HorusInspectionSyncer(
            env=self.base_env,
            connect_func=lambda **kwargs: connection,
            opener=opener,
            state_file=state_file,
            batch_size=100,
        )


class HorusSyncUnitTests(HorusSyncFixturesMixin, SimpleTestCase):
    def test_cutoff_blocks_dates_before_2026_08_10(self):
        with self.assertRaises(HorusSyncError):
            ensure_cutoff_date(date(2026, 8, 9))

    def test_report_and_operation_ids_are_preserved_exactly(self):
        syncer = HorusInspectionSyncer(env=self.base_env, connect_func=lambda **kwargs: None, opener=lambda *a, **k: None)
        sections = [dict(zip(SECTION_FIELDS, self.section_1))]
        operations = [dict(zip(OPERATION_FIELDS, self.operation_1))]
        fines = [dict(zip(FINE_FIELDS, self.fine_1))]

        payloads, warnings = syncer.build_payloads(sections, operations, fines)

        self.assertEqual(warnings, [])
        payload = payloads[0]
        self.assertEqual(payload["source_id"], self.section_1_id)
        self.assertEqual(payload["operations"][0]["source_id"], self.operation_1_id)
        self.assertEqual(payload["operations"][0]["fines"][0]["source_id"], 123)

    def test_build_payloads_preserve_zero_null_and_270(self):
        syncer = HorusInspectionSyncer(env=self.base_env, connect_func=lambda **kwargs: None, opener=lambda *a, **k: None)
        sections = [dict(zip(SECTION_FIELDS, self.section_1))]
        operations = [dict(zip(OPERATION_FIELDS, self.operation_1)), dict(zip(OPERATION_FIELDS, self.operation_2))]
        fines = [dict(zip(FINE_FIELDS, self.fine_1)), dict(zip(FINE_FIELDS, self.fine_2))]

        payloads, _ = syncer.build_payloads(sections, operations, fines)

        payload = payloads[0]
        self.assertIsNone(payload["management_id"])
        self.assertEqual(payload["agent_detran"], 2)
        self.assertEqual(payload["number_trailers"], 0)
        self.assertEqual(payload["civil_chief_name"], "Chefe civil A3")
        self.assertEqual(payload["support_opm"], "38 BPM")
        self.assertEqual(payload["support_pmerj_staff"], "54-0934\nSubten exemplo")
        self.assertEqual(payload["support_vehicles"], "54-0934")
        self.assertEqual(payload["low_approach_reasons"], "Baixa abordagem justificada")
        self.assertEqual(payload["team_violation_notices"], "AI-123")
        self.assertEqual(payload["specified_violation_notices"], "AI-123 detalhado")
        self.assertEqual(payload["miscellaneous_changes"], "Alteracoes diversas")
        self.assertEqual(payload["operations"][0]["removal_resolutions"], 270)
        self.assertIsNone(payload["operations"][1]["approach"])
        self.assertEqual(payload["operations"][1]["fined"], 0)
        self.assertIsNone(payload["operations"][1]["fines"][0]["quant"])

    def test_build_payloads_warn_for_orphan_operation_and_fine(self):
        syncer = HorusInspectionSyncer(env=self.base_env, connect_func=lambda **kwargs: None, opener=lambda *a, **k: None)
        sections = [dict(zip(SECTION_FIELDS, self.section_1))]
        operations = [dict(zip(OPERATION_FIELDS, self.operation_1)), dict(zip(OPERATION_FIELDS, self.operation_orphan))]
        fines = [dict(zip(FINE_FIELDS, self.fine_1)), dict(zip(FINE_FIELDS, self.fine_orphan))]

        payloads, warnings = syncer.build_payloads(sections, operations, fines)

        self.assertEqual(len(payloads), 1)
        self.assertEqual(len(payloads[0]["operations"]), 1)
        self.assertTrue(any("Operacao orfa ignorada" in warning for warning in warnings))
        self.assertTrue(any("Fine orfa ignorada" in warning for warning in warnings))

    def test_sql_quotes_case_sensitive_horus_columns(self):
        combined_sql = "\n".join([INITIAL_SECTION_SQL, INCREMENTAL_SECTION_SQL, OPERATIONS_SQL])

        self.assertIn('s."militaryChief"', combined_sql)
        self.assertIn('s."segovTeamCivil"', combined_sql)
        self.assertIn('s."segovTeamMilitar"', combined_sql)
        self.assertIn('"addressOperation"', combined_sql)

        self.assertNotIn("s.militaryChief", combined_sql)
        self.assertNotIn("s.segovTeamCivil", combined_sql)
        self.assertNotIn("s.segovTeamMilitar", combined_sql)
        self.assertNotIn("st.addressOperation", combined_sql)

    def test_uuid_array_queries_are_explicitly_typed(self):
        self.assertIn("ANY(%s::uuid[])", OPERATIONS_SQL)
        self.assertIn("ANY(%s::uuid[])", FINES_SQL)

    def test_uuid_lists_remain_bound_parameters_without_sql_interpolation(self):
        connection = self.build_connection(
            section_batches=[[self.section_1]],
            operation_rows=[self.operation_1, self.operation_2],
            fine_rows=[self.fine_1, self.fine_2],
        )

        def opener(request, timeout):
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer = self.build_syncer(connection=connection, opener=opener, state_file=state_file)
            syncer.run(date_from=CUT_OFF_DATE, limit=1, dry_run=True)

        operations_sql, operations_params = connection.executed_sql[1]
        fines_sql, fines_params = connection.executed_sql[2]

        self.assertIn("ANY(%s::uuid[])", operations_sql)
        self.assertEqual(list(operations_params[0]), [self.section_1_id])
        self.assertNotIn(self.section_1_id, operations_sql)

        self.assertIn("ANY(%s::uuid[])", fines_sql)
        self.assertEqual(list(fines_params[0]), [self.operation_1_id, self.operation_2_id])
        self.assertNotIn(self.operation_1_id, fines_sql)

    def test_dry_run_does_not_write_state(self):
        connection = self.build_connection(
            section_batches=[[self.section_1, self.section_2]],
            operation_rows=[self.operation_1, self.operation_3],
            fine_rows=[self.fine_1],
        )

        def opener(request, timeout):
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer = self.build_syncer(connection=connection, opener=opener, state_file=state_file)
            result = syncer.run(date_from=CUT_OFF_DATE, limit=1, dry_run=True)

        self.assertEqual(result["mode"], "initial")
        self.assertEqual(result["summary"]["reports_found"], 1)
        self.assertFalse(result["cursor_saved"])
        self.assertFalse(state_file.exists())

    def test_initial_load_limit_1_then_limit_5_keeps_other_records_available(self):
        initial_sections = self.make_initial_sections(10)
        first_batch = initial_sections[:2]
        second_batch = initial_sections[1:7]
        first_connection = self.build_connection(section_batches=[first_batch], operation_rows=[], fine_rows=[])
        second_connection = self.build_connection(section_batches=[second_batch], operation_rows=[], fine_rows=[])
        processed_ids = []

        def opener(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            processed_ids.append(payload["source_id"])
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer1 = self.build_syncer(connection=first_connection, opener=opener, state_file=state_file)
            result1 = syncer1.run(date_from=CUT_OFF_DATE, limit=1, dry_run=False)
            state_after_first = load_state_file(state_file)

            syncer2 = self.build_syncer(connection=second_connection, opener=opener, state_file=state_file)
            result2 = syncer2.run(date_from=CUT_OFF_DATE, limit=5, dry_run=False)

        self.assertEqual(result1["summary"]["reports_found"], 1)
        self.assertFalse(result1["initial_load_completed"])
        self.assertEqual(result2["summary"]["reports_found"], 5)
        self.assertEqual(len(set(processed_ids)), 6)
        self.assertFalse(state_after_first["initial_load_completed"])

    def test_initial_load_completion_switches_to_incremental(self):
        initial_sections = self.make_initial_sections(2)
        connection = self.build_connection(section_batches=[initial_sections], operation_rows=[], fine_rows=[])

        def opener(request, timeout):
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer = self.build_syncer(connection=connection, opener=opener, state_file=state_file)
            result = syncer.run(date_from=CUT_OFF_DATE, limit=5, dry_run=False)
            state = load_state_file(state_file)

        self.assertTrue(result["initial_load_completed"])
        self.assertTrue(state["initial_load_completed"])
        self.assertEqual(state["incremental_cursor"]["candidate_updated_at"], state["initial_max_candidate_updated_at"])

    def test_incremental_query_captures_old_report_modified_after_cursor(self):
        connection = self.build_connection(
            section_batches=[[self.section_1_operation_changed, self.section_2, self.section_3]],
            operation_rows=[self.operation_1_updated, self.operation_3],
            fine_rows=[self.fine_1],
        )

        def opener(request, timeout):
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            state = empty_state()
            state["initial_load_completed"] = True
            state["incremental_cursor"]["candidate_updated_at"] = "2026-08-12T13:00:00+00:00"
            state_file.write_text(json.dumps(state), encoding="utf-8")
            syncer = self.build_syncer(connection=connection, opener=opener, state_file=state_file)
            result = syncer.run(date_from=None, limit=1, dry_run=True)

        self.assertEqual(result["mode"], "incremental")
        self.assertEqual(result["updated_from"], "2026-08-12T12:55:00+00:00")
        candidate_sql = connection.executed_sql[0][0]
        self.assertIn("ORDER BY c.candidate_updated_at, s.id", candidate_sql)
        self.assertIn("AND (c.candidate_updated_at, s.id) > (%s, %s)", candidate_sql)

    def test_incremental_query_captures_new_fine_in_old_report(self):
        connection = self.build_connection(
            section_batches=[[self.section_1_fine_changed]],
            operation_rows=[self.operation_1],
            fine_rows=[self.fine_1_updated],
        )

        def opener(request, timeout):
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            state = empty_state()
            state["initial_load_completed"] = True
            state["incremental_cursor"]["candidate_updated_at"] = "2026-08-12T13:00:00+00:00"
            state_file.write_text(json.dumps(state), encoding="utf-8")
            syncer = self.build_syncer(connection=connection, opener=opener, state_file=state_file)
            result = syncer.run(date_from=None, limit=1, dry_run=True)

        self.assertEqual(result["summary"]["reports_found"], 1)
        candidate_sql = connection.executed_sql[0][0]
        self.assertIn("FROM rcols_fineds f INNER JOIN rcols_section_twos st2", candidate_sql)

    def test_failure_mid_page_does_not_lose_remaining_records(self):
        initial_sections = self.make_initial_sections(4)
        first_connection = self.build_connection(section_batches=[initial_sections], operation_rows=[], fine_rows=[])
        second_connection = self.build_connection(section_batches=[initial_sections], operation_rows=[], fine_rows=[])
        processed_first = []
        processed_second = []

        def opener_with_error(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            processed_first.append(payload["source_id"])
            if len(processed_first) == 3:
                raise build_http_error(400, {"detail": "payload invalido"})
            return FakeHttpResponse({"result": "created"})

        def opener_success(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            processed_second.append(payload["source_id"])
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer1 = self.build_syncer(connection=first_connection, opener=opener_with_error, state_file=state_file)
            result1 = syncer1.run(date_from=CUT_OFF_DATE, limit=4, dry_run=False)

            syncer2 = self.build_syncer(connection=second_connection, opener=opener_success, state_file=state_file)
            result2 = syncer2.run(date_from=CUT_OFF_DATE, limit=4, dry_run=False)

        self.assertFalse(result1["cursor_saved"])
        self.assertFalse(state_file.exists())
        self.assertEqual(len(processed_first), 4)
        self.assertEqual(result2["summary"]["reports_found"], 4)
        self.assertEqual(len(processed_second), 4)

    def test_state_matches_initial_sql_cursor_shape(self):
        initial_sections = self.make_initial_sections(1)
        connection = self.build_connection(section_batches=[initial_sections], operation_rows=[], fine_rows=[])

        def opener(request, timeout):
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer = self.build_syncer(connection=connection, opener=opener, state_file=state_file)
            syncer.run(date_from=CUT_OFF_DATE, limit=1, dry_run=False)
            state = load_state_file(state_file)

        self.assertIn("operation_date", state["initial_cursor"])
        self.assertIn("candidate_updated_at", state["initial_cursor"])
        self.assertIn("source_id", state["initial_cursor"])

    def test_transition_from_initial_to_incremental(self):
        initial_sections = self.make_initial_sections(1)
        initial_connection = self.build_connection(section_batches=[initial_sections], operation_rows=[], fine_rows=[])
        incremental_connection = self.build_connection(section_batches=[[self.section_1_operation_changed]], operation_rows=[self.operation_1_updated], fine_rows=[self.fine_1])

        def opener(request, timeout):
            return FakeHttpResponse({"result": "created"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer1 = self.build_syncer(connection=initial_connection, opener=opener, state_file=state_file)
            result1 = syncer1.run(date_from=CUT_OFF_DATE, limit=5, dry_run=False)

            syncer2 = self.build_syncer(connection=incremental_connection, opener=opener, state_file=state_file)
            result2 = syncer2.run(date_from=None, limit=1, dry_run=True)

        self.assertTrue(result1["initial_load_completed"])
        self.assertEqual(result2["mode"], "incremental")

    def test_retry_happens_for_503_then_succeeds(self):
        connection = self.build_connection()
        attempts = {"count": 0}

        def opener(request, timeout):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise build_http_error(503, {"detail": "temporarily unavailable"})
            return FakeHttpResponse({"result": "updated"})

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer = self.build_syncer(connection=connection, opener=opener, state_file=state_file)
            result = syncer.run(date_from=CUT_OFF_DATE, limit=1, dry_run=False)

        self.assertEqual(attempts["count"], 2)
        self.assertEqual(result["summary"]["updated"], 1)

    def test_timeout_retry_is_limited(self):
        connection = self.build_connection()
        attempts = {"count": 0}

        def opener(request, timeout):
            attempts["count"] += 1
            raise socket.timeout("timed out")

        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            syncer = self.build_syncer(connection=connection, opener=opener, state_file=state_file)
            result = syncer.run(date_from=CUT_OFF_DATE, limit=1, dry_run=False)

        self.assertEqual(attempts["count"], 3)
        self.assertEqual(result["summary"]["errors"], 1)
        self.assertFalse(result["cursor_saved"])

    def test_command_dry_run_outputs_json_summary(self):
        with TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            from unittest.mock import patch

            with patch("apps.inspection.management.commands.sync_horus_inspection.HorusInspectionSyncer") as syncer_cls:
                syncer = syncer_cls.return_value
                syncer.run.return_value = {
                    "summary": {"reports_found": 0, "operations_found": 0, "fines_found": 0, "dry_run_reports": 0},
                    "warnings": [],
                    "report_logs": [],
                    "mode": "initial",
                    "effective_date_from": "2026-08-10",
                    "updated_from": None,
                    "state_file": str(state_file),
                    "cursor_saved": False,
                    "initial_load_completed": False,
                    "has_more": False,
                    "state_preview": empty_state(),
                }
                out = io.StringIO()
                call_command("sync_horus_inspection", "--dry-run", "--date-from", "2026-08-10", stdout=out)

        self.assertIn("Sincronizacao concluida.", out.getvalue())
        self.assertIn('"reports_found": 0', out.getvalue())
