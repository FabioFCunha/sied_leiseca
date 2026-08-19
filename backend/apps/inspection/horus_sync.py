import json
import os
import socket
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

import psycopg2

from apps.inspection.serializers import InspectionReportIngestionSerializer


CUT_OFF_DATE = date(2026, 8, 10)
SAFETY_WINDOW = timedelta(minutes=5)
DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_STATE_FILE = Path(__file__).resolve().parents[2] / ".inspection_horus_sync_state.json"
ZERO_UUID = "00000000-0000-0000-0000-000000000000"
SUCCESS_RESULTS = {
    "created",
    "updated",
    "ignored_equal",
    "ignored_stale",
    "flagged_source_update_after_statistics_review",
    "ignored_source_update_after_statistics_review",
}

SECTION_FIELDS = [
    "id",
    "user_id",
    "management_id",
    "militaryChief",
    "team",
    "operation_date",
    "segovTeamCivil",
    "segovTeamMilitar",
    "change_ols",
    "agent_detran",
    "number_trailers",
    "change_support",
    "cars",
    "changes_general",
    "created_at",
    "updated_at",
    "candidate_updated_at",
]

OPERATION_FIELDS = [
    "id",
    "rcols_section_id",
    "addressOperation",
    "locality",
    "another_not_listed",
    "departure_meeting_point",
    "operation_assembly",
    "first_approach",
    "closing",
    "approach",
    "reconductor",
    "refusal",
    "celebrities_authorities",
    "four_ml",
    "thirtythree_ml",
    "thirtyfour_ml",
    "passive_tests_performed",
    "changes_material",
    "cnh_collected",
    "fined",
    "towed",
    "removal_resolutions",
    "arrests_means_evidence",
    "art307",
    "criminal_occurrences",
    "driving_canceled_license",
    "vehicle_resolutions",
    "administrative_tests",
    "created_at",
    "updated_at",
    "cep",
    "street",
    "city",
    "district",
    "number",
]

FINE_FIELDS = [
    "id",
    "rcols_section_twos_id",
    "art",
    "quant",
    "created_at",
    "updated_at",
]

INITIAL_SECTION_SQL = """
WITH candidate_sections AS (
    SELECT
        s.id,
        COALESCE(
            GREATEST(
                s.updated_at,
                COALESCE(
                    (
                        SELECT MAX(GREATEST(st.created_at, st.updated_at))
                        FROM rcols_section_twos st
                        WHERE st.rcols_section_id = s.id
                    ),
                    s.updated_at
                ),
                COALESCE(
                    (
                        SELECT MAX(GREATEST(f.created_at, f.updated_at))
                        FROM rcols_fineds f
                        INNER JOIN rcols_section_twos st2 ON st2.id = f.rcols_section_twos_id
                        WHERE st2.rcols_section_id = s.id
                    ),
                    s.updated_at
                )
            ),
            s.updated_at
        ) AS candidate_updated_at
    FROM rcols_sections s
    WHERE s.operation_date >= %s
)
SELECT
    s.id,
    s.user_id,
    s.management_id,
    s."militaryChief",
    s.team,
    s.operation_date,
    s."segovTeamCivil",
    s."segovTeamMilitar",
    s.change_ols,
    s.agent_detran,
    s.number_trailers,
    s.change_support,
    s.cars,
    s.changes_general,
    s.created_at,
    s.updated_at,
    c.candidate_updated_at
FROM rcols_sections s
INNER JOIN candidate_sections c ON c.id = s.id
WHERE s.operation_date >= %s
  AND (s.operation_date, c.candidate_updated_at, s.id) > (%s, %s, %s)
ORDER BY s.operation_date, c.candidate_updated_at, s.id
LIMIT %s
"""

INCREMENTAL_SECTION_SQL = """
WITH candidate_sections AS (
    SELECT
        s.id,
        COALESCE(
            GREATEST(
                s.updated_at,
                COALESCE(
                    (
                        SELECT MAX(GREATEST(st.created_at, st.updated_at))
                        FROM rcols_section_twos st
                        WHERE st.rcols_section_id = s.id
                    ),
                    s.updated_at
                ),
                COALESCE(
                    (
                        SELECT MAX(GREATEST(f.created_at, f.updated_at))
                        FROM rcols_fineds f
                        INNER JOIN rcols_section_twos st2 ON st2.id = f.rcols_section_twos_id
                        WHERE st2.rcols_section_id = s.id
                    ),
                    s.updated_at
                )
            ),
            s.updated_at
        ) AS candidate_updated_at
    FROM rcols_sections s
    WHERE s.operation_date >= %s
      AND (
        GREATEST(s.created_at, s.updated_at) >= %s
        OR EXISTS (
            SELECT 1
            FROM rcols_section_twos st
            WHERE st.rcols_section_id = s.id
              AND GREATEST(st.created_at, st.updated_at) >= %s
        )
        OR EXISTS (
            SELECT 1
            FROM rcols_fineds f
            INNER JOIN rcols_section_twos st2 ON st2.id = f.rcols_section_twos_id
            WHERE st2.rcols_section_id = s.id
              AND GREATEST(f.created_at, f.updated_at) >= %s
        )
      )
)
SELECT
    s.id,
    s.user_id,
    s.management_id,
    s."militaryChief",
    s.team,
    s.operation_date,
    s."segovTeamCivil",
    s."segovTeamMilitar",
    s.change_ols,
    s.agent_detran,
    s.number_trailers,
    s.change_support,
    s.cars,
    s.changes_general,
    s.created_at,
    s.updated_at,
    c.candidate_updated_at
FROM rcols_sections s
INNER JOIN candidate_sections c ON c.id = s.id
WHERE s.operation_date >= %s
  AND (c.candidate_updated_at, s.id) > (%s, %s)
ORDER BY c.candidate_updated_at, s.id
LIMIT %s
"""

OPERATIONS_SQL = """
SELECT
    id,
    rcols_section_id,
    "addressOperation",
    locality,
    another_not_listed,
    departure_meeting_point,
    operation_assembly,
    first_approach,
    closing,
    approach,
    reconductor,
    refusal,
    celebrities_authorities,
    four_ml,
    thirtythree_ml,
    thirtyfour_ml,
    passive_tests_performed,
    changes_material,
    cnh_collected,
    fined,
    towed,
    removal_resolutions,
    arrests_means_evidence,
    art307,
    criminal_occurrences,
    driving_canceled_license,
    vehicle_resolutions,
    administrative_tests,
    created_at,
    updated_at,
    cep,
    street,
    city,
    district,
    number
FROM rcols_section_twos
WHERE rcols_section_id = ANY(%s::uuid[])
ORDER BY rcols_section_id, updated_at, id
"""

FINES_SQL = """
SELECT
    id,
    rcols_section_twos_id,
    art,
    quant,
    created_at,
    updated_at
FROM rcols_fineds
WHERE rcols_section_twos_id = ANY(%s::uuid[])
ORDER BY rcols_section_twos_id, updated_at, id
"""


class HorusSyncError(Exception):
    pass


@dataclass
class SyncSummary:
    reports_found: int = 0
    operations_found: int = 0
    fines_found: int = 0
    reports_sent: int = 0
    dry_run_reports: int = 0
    created: int = 0
    updated: int = 0
    ignored_equal: int = 0
    ignored_stale: int = 0
    flagged_source_update_after_statistics_review: int = 0
    ignored_source_update_after_statistics_review: int = 0
    errors: int = 0
    warnings: int = 0


def ensure_cutoff_date(value: date) -> date:
    if value < CUT_OFF_DATE:
        raise HorusSyncError(
            f"date_from anterior ao corte operacional nao e permitido nesta versao: {value.isoformat()}"
        )
    return value


def parse_date_from_option(raw_value: str | None) -> date | None:
    if not raw_value:
        return None
    return ensure_cutoff_date(date.fromisoformat(raw_value))


def empty_state() -> dict:
    return {
        "initial_load_completed": False,
        "initial_cursor": {
            "operation_date": CUT_OFF_DATE.isoformat(),
            "candidate_updated_at": "1970-01-01T00:00:00+00:00",
            "source_id": ZERO_UUID,
        },
        "initial_max_candidate_updated_at": None,
        "incremental_cursor": {
            "candidate_updated_at": None,
        },
    }


def load_state_file(state_file: Path) -> dict:
    state = empty_state()
    if not state_file.exists():
        return state
    loaded = json.loads(state_file.read_text(encoding="utf-8"))
    state.update({key: value for key, value in loaded.items() if key in state})
    if "initial_cursor" in loaded:
        state["initial_cursor"].update(loaded["initial_cursor"] or {})
    if "incremental_cursor" in loaded:
        state["incremental_cursor"].update(loaded["incremental_cursor"] or {})
    return state


def save_state_file(state_file: Path, payload: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=f"{state_file.name}.", suffix=".tmp", dir=state_file.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, state_file)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def to_iso_datetime(value: datetime | None) -> str | None:
    normalized = normalize_datetime(value)
    return normalized.isoformat() if normalized else None


def rows_to_dicts(rows, fields: list[str]) -> list[dict]:
    return [dict(zip(fields, row)) for row in rows]


def map_fine_payload(fine: dict) -> dict:
    return {
        "source_id": fine["id"],
        "art": fine.get("art") or "",
        "quant": fine.get("quant"),
        "source_created_at": to_iso_datetime(fine.get("created_at")),
        "source_updated_at": to_iso_datetime(fine.get("updated_at")),
    }


def map_operation_payload(operation: dict, fines: list[dict]) -> dict:
    return {
        "source_id": str(operation["id"]),
        "source_created_at": to_iso_datetime(operation.get("created_at")),
        "source_updated_at": to_iso_datetime(operation.get("updated_at")),
        "address_operation": operation.get("addressOperation") or "",
        "locality": operation.get("locality") or "",
        "another_not_listed": operation.get("another_not_listed") or "",
        "departure_meeting_point": operation.get("departure_meeting_point") or "",
        "operation_assembly": operation.get("operation_assembly") or "",
        "first_approach": operation.get("first_approach") or "",
        "closing": operation.get("closing") or "",
        "approach": operation.get("approach"),
        "reconductor": operation.get("reconductor"),
        "refusal": operation.get("refusal"),
        "celebrities_authorities": operation.get("celebrities_authorities"),
        "four_ml": operation.get("four_ml"),
        "thirtythree_ml": operation.get("thirtythree_ml"),
        "thirtyfour_ml": operation.get("thirtyfour_ml"),
        "passive_tests_performed": operation.get("passive_tests_performed"),
        "changes_material": operation.get("changes_material") or "",
        "cnh_collected": operation.get("cnh_collected"),
        "fined": operation.get("fined"),
        "towed": operation.get("towed"),
        "removal_resolutions": operation.get("removal_resolutions"),
        "arrests_means_evidence": operation.get("arrests_means_evidence"),
        "art307": operation.get("art307"),
        "criminal_occurrences": operation.get("criminal_occurrences"),
        "driving_canceled_license": operation.get("driving_canceled_license"),
        "vehicle_resolutions": operation.get("vehicle_resolutions") or "",
        "administrative_tests": operation.get("administrative_tests") or "",
        "cep": operation.get("cep") or "",
        "street": operation.get("street") or "",
        "city": operation.get("city") or "",
        "district": operation.get("district") or "",
        "number": operation.get("number") or "",
        "fines": fines,
    }


def map_section_payload(section: dict, operations: list[dict]) -> dict:
    return {
        "source_id": str(section["id"]),
        "source_created_at": to_iso_datetime(section.get("created_at")),
        "source_updated_at": to_iso_datetime(section.get("updated_at")),
        "operation_date": section["operation_date"].isoformat() if section.get("operation_date") else None,
        "team": section.get("team") or "",
        "management_id": section.get("management_id"),
        "military_chief_source_id": str(section["militaryChief"]) if section.get("militaryChief") else None,
        "segov_team_civil": section.get("segovTeamCivil") or "",
        "segov_team_military": section.get("segovTeamMilitar") or "",
        "change_ols": section.get("change_ols") or "",
        "agent_detran": section.get("agent_detran"),
        "number_trailers": section.get("number_trailers"),
        "change_support": section.get("change_support") or "",
        "cars": section.get("cars") or "",
        "changes_general": section.get("changes_general") or "",
        "operations": operations,
    }


class HorusInspectionSyncer:
    def __init__(
        self,
        *,
        env=None,
        state_file: Path | None = None,
        safety_window: timedelta = SAFETY_WINDOW,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        opener=urllib_request.urlopen,
        connect_func=psycopg2.connect,
    ):
        self.env = env or os.environ
        self.state_file = state_file or DEFAULT_STATE_FILE
        self.safety_window = safety_window
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.batch_size = batch_size
        self.opener = opener
        self.connect_func = connect_func

    def _required_env(self, key: str) -> str:
        value = str(self.env.get(key, "") or "").strip()
        if not value:
            raise HorusSyncError(f"Variavel de ambiente obrigatoria ausente: {key}")
        return value

    def build_horus_connection_kwargs(self) -> dict:
        return {
            "host": self._required_env("HORUS_DB_HOST"),
            "port": int(self.env.get("HORUS_DB_PORT") or 5432),
            "dbname": self._required_env("HORUS_DB_NAME"),
            "user": self._required_env("HORUS_DB_USER"),
            "password": self._required_env("HORUS_DB_PASSWORD"),
            "connect_timeout": self.timeout_seconds,
        }

    def build_api_target(self) -> tuple[str, str]:
        return (
            self._required_env("SIED_INSPECTION_SYNC_URL"),
            self._required_env("SIED_INSPECTION_SYNC_TOKEN"),
        )

    def determine_mode(self, *, date_from: date | None, state: dict) -> tuple[str, date, datetime | None]:
        effective_date_from = ensure_cutoff_date(date_from) if date_from is not None else CUT_OFF_DATE
        if not state.get("initial_load_completed"):
            return "initial", effective_date_from, None
        cursor_value = state.get("incremental_cursor", {}).get("candidate_updated_at")
        if not cursor_value:
            return "incremental", effective_date_from, None
        return "incremental", effective_date_from, normalize_datetime(datetime.fromisoformat(cursor_value)) - self.safety_window

    def connect_horus(self):
        conn = self.connect_func(**self.build_horus_connection_kwargs())
        if hasattr(conn, "set_session"):
            conn.set_session(readonly=True, autocommit=False)
        return conn

    def fetch_initial_section_batch(
        self,
        conn,
        *,
        date_from: date,
        last_key: tuple[date, datetime, str],
        batch_limit: int,
    ) -> tuple[list[dict], bool]:
        params = [date_from, date_from, *last_key, batch_limit + 1]
        with conn.cursor() as cursor:
            cursor.execute(INITIAL_SECTION_SQL, params)
            rows = rows_to_dicts(cursor.fetchall(), SECTION_FIELDS)
        has_more = len(rows) > batch_limit
        return rows[:batch_limit], has_more

    def fetch_incremental_section_batch(
        self,
        conn,
        *,
        date_from: date,
        updated_from: datetime | None,
        batch_limit: int,
    ) -> tuple[list[dict], bool]:
        start_updated_from = updated_from or normalize_datetime(datetime(1970, 1, 1, tzinfo=timezone.utc))
        params = [date_from, start_updated_from, start_updated_from, start_updated_from, date_from, start_updated_from, ZERO_UUID, batch_limit + 1]
        with conn.cursor() as cursor:
            cursor.execute(INCREMENTAL_SECTION_SQL, params)
            rows = rows_to_dicts(cursor.fetchall(), SECTION_FIELDS)
        has_more = len(rows) > batch_limit
        return rows[:batch_limit], has_more

    def fetch_operations(self, conn, *, section_ids: list[str]) -> list[dict]:
        if not section_ids:
            return []
        with conn.cursor() as cursor:
            cursor.execute(OPERATIONS_SQL, (section_ids,))
            return rows_to_dicts(cursor.fetchall(), OPERATION_FIELDS)

    def fetch_fines(self, conn, *, operation_ids: list[str]) -> list[dict]:
        if not operation_ids:
            return []
        with conn.cursor() as cursor:
            cursor.execute(FINES_SQL, (operation_ids,))
            return rows_to_dicts(cursor.fetchall(), FINE_FIELDS)

    def build_payloads(self, sections: list[dict], operations: list[dict], fines: list[dict]) -> tuple[list[dict], list[str]]:
        warnings: list[str] = []
        valid_section_ids = {section["id"] for section in sections}
        operations_by_section: dict[str, list[dict]] = {}
        operation_index: dict[str, dict] = {}

        for operation in operations:
            operation_index[operation["id"]] = operation
            section_id = operation["rcols_section_id"]
            if section_id not in valid_section_ids:
                warnings.append(f"Operacao orfa ignorada: operation_id={operation['id']} section_id={section_id}")
                continue
            operations_by_section.setdefault(section_id, []).append(operation)

        fines_by_operation: dict[str, list[dict]] = {}
        for fine in fines:
            operation_id = fine["rcols_section_twos_id"]
            if operation_id not in operation_index:
                warnings.append(f"Fine orfa ignorada: fine_id={fine['id']} operation_id={operation_id}")
                continue
            fines_by_operation.setdefault(operation_id, []).append(fine)

        payloads: list[dict] = []
        for section in sections:
            mapped_operations = []
            for operation in operations_by_section.get(section["id"], []):
                mapped_fines = [map_fine_payload(fine) for fine in fines_by_operation.get(operation["id"], [])]
                mapped_operations.append(map_operation_payload(operation, mapped_fines))
            payloads.append(map_section_payload(section, mapped_operations))
        return payloads, warnings

    def validate_payload(self, payload: dict) -> None:
        serializer = InspectionReportIngestionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

    def post_payload(self, payload: dict) -> dict:
        url, token = self.build_api_target()
        request = urllib_request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        last_error = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                with self.opener(request, timeout=self.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib_error.HTTPError as exc:
                if exc.code in {429, 502, 503, 504} and attempt < self.retry_attempts:
                    last_error = exc
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    try:
                        wait_seconds = (
                            max(1.0, float(retry_after))
                            if retry_after
                            else float(2 ** (attempt - 1))
                        )
                    except (TypeError, ValueError):
                        wait_seconds = float(2 ** (attempt - 1))
                    time.sleep(wait_seconds)
                    continue
                body_text = exc.read().decode("utf-8", "ignore")
                raise HorusSyncError(f"HTTP {exc.code}: {body_text[:300]}") from exc
            except (urllib_error.URLError, socket.timeout, TimeoutError) as exc:
                if attempt < self.retry_attempts:
                    last_error = exc
                    time.sleep(float(2 ** (attempt - 1)))
                    continue
                raise HorusSyncError(f"Timeout ou erro de conexao com a API SIED: {exc}") from exc
        raise HorusSyncError(f"Falha apos retries limitados: {last_error}")

    def _classify_result(self, response: dict) -> str:
        result = response.get("result", "unknown")
        if result not in SUCCESS_RESULTS:
            raise HorusSyncError(f"Resultado inesperado da API SIED: {result}")
        return result

    def _build_saved_state(
        self,
        *,
        previous_state: dict,
        mode: str,
        effective_date_from: date,
        processed_sections: list[dict],
        has_more: bool,
        max_candidate_updated_at_seen: datetime | None,
    ) -> dict:
        state = load_state_file(self.state_file) if self.state_file.exists() else empty_state()
        if previous_state:
            state = previous_state

        if mode == "initial":
            if processed_sections:
                last_section = processed_sections[-1]
                state["initial_cursor"] = {
                    "operation_date": last_section["operation_date"].isoformat(),
                    "candidate_updated_at": normalize_datetime(last_section["candidate_updated_at"]).isoformat(),
                    "source_id": str(last_section["id"]),
                }
            state["initial_max_candidate_updated_at"] = (
                max_candidate_updated_at_seen.isoformat() if max_candidate_updated_at_seen else state.get("initial_max_candidate_updated_at")
            )
            state["initial_load_completed"] = not has_more
            if not has_more:
                state["incremental_cursor"] = {
                    "candidate_updated_at": state.get("initial_max_candidate_updated_at"),
                }
        else:
            state["initial_load_completed"] = True
            if max_candidate_updated_at_seen:
                state["incremental_cursor"] = {
                    "candidate_updated_at": max_candidate_updated_at_seen.isoformat(),
                }
        return state

    def run(self, *, date_from: date | None, limit: int | None, dry_run: bool) -> dict:
        state = load_state_file(self.state_file)
        mode, effective_date_from, updated_from = self.determine_mode(date_from=date_from, state=state)
        batch_limit = limit or self.batch_size
        summary = SyncSummary()
        warnings: list[str] = []
        report_logs: list[dict] = []
        had_errors = False
        max_candidate_updated_at_seen = None
        persisted_state = None

        conn = self.connect_horus()
        try:
            if mode == "initial":
                initial_cursor = state["initial_cursor"]
                last_key = (
                    ensure_cutoff_date(date.fromisoformat(initial_cursor["operation_date"])),
                    normalize_datetime(datetime.fromisoformat(initial_cursor["candidate_updated_at"])),
                    initial_cursor["source_id"],
                )
                sections, has_more = self.fetch_initial_section_batch(
                    conn,
                    date_from=effective_date_from,
                    last_key=last_key,
                    batch_limit=batch_limit,
                )
            else:
                sections, has_more = self.fetch_incremental_section_batch(
                    conn,
                    date_from=effective_date_from,
                    updated_from=updated_from,
                    batch_limit=batch_limit,
                )

            section_ids = [section["id"] for section in sections]
            operations = self.fetch_operations(conn, section_ids=section_ids)
            operation_ids = [operation["id"] for operation in operations]
            fines = self.fetch_fines(conn, operation_ids=operation_ids)
            payloads, payload_warnings = self.build_payloads(sections, operations, fines)

            summary.reports_found = len(sections)
            summary.operations_found = len(operations)
            summary.fines_found = len(fines)
            summary.warnings = len(payload_warnings)
            warnings.extend(payload_warnings)

            for section, payload in zip(sections, payloads):
                candidate_updated_at = normalize_datetime(section.get("candidate_updated_at"))
                if candidate_updated_at and (
                    max_candidate_updated_at_seen is None or candidate_updated_at > max_candidate_updated_at_seen
                ):
                    max_candidate_updated_at_seen = candidate_updated_at
                try:
                    self.validate_payload(payload)
                    if dry_run:
                        summary.dry_run_reports += 1
                        result = "dry_run"
                    else:
                        response = self.post_payload(payload)
                        result = self._classify_result(response)
                        summary.reports_sent += 1
                        setattr(summary, result, getattr(summary, result) + 1)
                    report_logs.append(
                        {
                            "source_id": payload["source_id"],
                            "date": payload["operation_date"],
                            "team": payload.get("team") or "",
                            "result": result,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    had_errors = True
                    summary.errors += 1
                    report_logs.append(
                        {
                            "source_id": payload["source_id"],
                            "date": payload["operation_date"],
                            "team": payload.get("team") or "",
                            "result": "error",
                            "error": str(exc)[:300],
                        }
                    )

            if not dry_run and not had_errors:
                persisted_state = self._build_saved_state(
                    previous_state=state,
                    mode=mode,
                    effective_date_from=effective_date_from,
                    processed_sections=sections,
                    has_more=has_more,
                    max_candidate_updated_at_seen=max_candidate_updated_at_seen,
                )
                save_state_file(self.state_file, persisted_state)

            return {
                "summary": asdict(summary),
                "warnings": warnings,
                "report_logs": report_logs,
                "mode": mode,
                "effective_date_from": effective_date_from.isoformat(),
                "updated_from": updated_from.isoformat() if updated_from else None,
                "state_file": str(self.state_file),
                "cursor_saved": not dry_run and not had_errors,
                "initial_load_completed": (
                    persisted_state.get("initial_load_completed")
                    if persisted_state is not None
                    else state.get("initial_load_completed")
                ),
                "has_more": has_more,
                "success_results": sorted(SUCCESS_RESULTS),
                "candidate_sql_initial": INITIAL_SECTION_SQL.strip(),
                "candidate_sql_incremental": INCREMENTAL_SECTION_SQL.strip(),
                "operations_sql": OPERATIONS_SQL.strip(),
                "fines_sql": FINES_SQL.strip(),
                "state_preview": persisted_state or state,
            }
        finally:
            conn.close()
