import hashlib
import json
import os
import time
from datetime import date
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.core.management.base import (
    BaseCommand,
    CommandError,
)


DATE_FROM = date(2022, 10, 3)
DATE_TO = date(2022, 12, 31)

EXPECTED_ROWS = 856
EXPECTED_REPORTS = 896
EXPECTED_OPERATIONS = 1051
EXPECTED_RAIN = 207

DEFAULT_TIMEOUT = 30
DEFAULT_RETRY = 3
DEFAULT_DELAY = 0.05


def _sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _load(path):
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise CommandError(
            f"Falha ao ler JSON: {exc}"
        ) from exc

    metadata = (
        payload.get("metadata")
        or {}
    )

    if metadata.get("source") != "HORUS":
        raise CommandError(
            "metadata.source deve ser HORUS."
        )

    if metadata.get("source_type") != "DAILY":
        raise CommandError(
            "metadata.source_type deve ser DAILY."
        )

    if metadata.get("taxonomy_era") != "ERA_C":
        raise CommandError(
            "metadata.taxonomy_era deve ser ERA_C."
        )

    if metadata.get("date_from") != "2022-10-03":
        raise CommandError(
            "metadata.date_from deve ser 2022-10-03."
        )

    if metadata.get("date_to") != "2026-08-09":
        raise CommandError(
            "metadata.date_to deve ser 2026-08-09."
        )

    rows = payload.get("rows")

    if not isinstance(rows, list):
        raise CommandError(
            "Campo rows ausente ou inválido."
        )

    selected = []

    for row in rows:
        raw_date = row.get(
            "reference_date"
        )

        try:
            reference_date = (
                date.fromisoformat(
                    str(raw_date)
                )
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise CommandError(
                "reference_date inválida "
                f"no JSON: {raw_date}"
            ) from exc

        if (
            DATE_FROM
            <= reference_date
            <= DATE_TO
        ):
            selected.append(row)

    reports = sum(
        int(
            row.get(
                "reports_count"
            )
            or 0
        )
        for row in selected
    )

    operations = sum(
        int(
            row.get(
                "operations_count"
            )
            or 0
        )
        for row in selected
    )

    rain = sum(
        int(
            row.get("rain")
            or 0
        )
        for row in selected
    )

    checks = {
        "rows": (
            len(selected),
            EXPECTED_ROWS,
        ),
        "reports": (
            reports,
            EXPECTED_REPORTS,
        ),
        "operations": (
            operations,
            EXPECTED_OPERATIONS,
        ),
        "rain": (
            rain,
            EXPECTED_RAIN,
        ),
    }

    errors = [
        (
            f"{name}: "
            f"{actual} != {expected}"
        )
        for name, (
            actual,
            expected,
        ) in checks.items()
        if actual != expected
    ]

    if errors:
        raise CommandError(
            "Validação de 2022 falhou: "
            + " | ".join(errors)
        )

    return (
        payload,
        selected,
        {
            "rows": len(selected),
            "reports": reports,
            "operations": operations,
            "rain": rain,
        },
    )


def _post(
    *,
    url,
    token,
    payload,
    timeout,
    retry,
):
    body = json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    last_exc = None

    for attempt in range(
        1,
        retry + 1,
    ):
        request = urllib_request.Request(
            url,
            data=body,
            headers={
                "Content-Type": (
                    "application/json"
                ),
                "Authorization": (
                    f"Bearer {token}"
                ),
                "User-Agent": (
                    "push_horus_historical_2022/1.0"
                ),
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(
                request,
                timeout=timeout,
            ) as response:
                raw = response.read()
                data = (
                    json.loads(raw)
                    if raw
                    else {}
                )

                return (
                    response.status,
                    data,
                )

        except urllib_error.HTTPError as exc:
            raw = exc.read()

            try:
                data = (
                    json.loads(raw)
                    if raw
                    else {}
                )
            except Exception:
                data = {
                    "raw": raw.decode(
                        "utf-8",
                        errors="replace",
                    )
                }

            if exc.code in {
                400,
                401,
                403,
                409,
            }:
                return (
                    exc.code,
                    data,
                )

            last_exc = exc

        except (
            urllib_error.URLError,
            OSError,
        ) as exc:
            last_exc = exc

        if attempt < retry:
            time.sleep(
                2 * attempt
            )

    return (
        0,
        {
            "error": str(
                last_exc
            )
        },
    )


class Command(BaseCommand):
    help = (
        "Valida ou envia por HTTPS "
        "exclusivamente a extensão histórica "
        "Horus DAILY / ERA_C de "
        "03/10/2022 a 31/12/2022."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--file",
            required=True,
        )

        parser.add_argument(
            "--url",
            required=True,
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
        )

        parser.add_argument(
            "--send",
            action="store_true",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--token",
            default=None,
        )

        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_TIMEOUT,
        )

        parser.add_argument(
            "--retry",
            type=int,
            default=DEFAULT_RETRY,
        )

        parser.add_argument(
            "--delay",
            type=float,
            default=DEFAULT_DELAY,
        )

    def handle(
        self,
        *args,
        **options,
    ):
        dry_run = bool(
            options["dry_run"]
        )

        send = bool(
            options["send"]
        )

        if dry_run == send:
            raise CommandError(
                "Informe exatamente um: "
                "--dry-run ou --send."
            )

        path = Path(
            options["file"]
        )

        if not path.exists():
            raise CommandError(
                f"Arquivo não encontrado: {path}"
            )

        (
            payload,
            rows,
            summary,
        ) = _load(path)

        file_sha256 = _sha256(
            path
        )

        self.stdout.write(
            "=" * 80
        )
        self.stdout.write(
            "PUSH HORUS — EXTENSÃO 2022"
        )
        self.stdout.write(
            "=" * 80
        )
        self.stdout.write(
            f"Arquivo: {path.resolve()}"
        )
        self.stdout.write(
            f"SHA256: {file_sha256}"
        )
        self.stdout.write(
            f"Linhas: {summary['rows']}"
        )
        self.stdout.write(
            f"Relatórios: {summary['reports']}"
        )
        self.stdout.write(
            f"Operações: {summary['operations']}"
        )
        self.stdout.write(
            f"Chuva: {summary['rain']}"
        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    "DRY-RUN concluído. "
                    "Nenhum dado foi enviado."
                )
            )
            return

        token = (
            options["token"]
            or os.environ.get(
                "SIED_INSPECTION_SYNC_TOKEN"
            )
        )

        if not token:
            raise CommandError(
                "Token ausente. Informe --token "
                "ou SIED_INSPECTION_SYNC_TOKEN."
            )

        limit = options["limit"]

        if (
            limit is not None
            and limit <= 0
        ):
            raise CommandError(
                "--limit deve ser maior que zero."
            )

        rows_to_send = (
            rows[:limit]
            if limit is not None
            else rows
        )

        counters = {
            "sent": 0,
            "created": 0,
            "already_exists": 0,
            "conflicts": 0,
            "errors": 0,
        }

        for index, row in enumerate(
            rows_to_send,
            start=1,
        ):
            request_payload = {
                "file_sha256": (
                    file_sha256
                ),
                "maintenance_action": (
                    "IMPORT_2022"
                ),
                "source_type": "DAILY",
                "taxonomy_era": "ERA_C",
                "reference_date": row[
                    "reference_date"
                ],
                "team": row["team"],
                "source_row": row.get(
                    "source_row",
                    0,
                ),
                "reports_count": row.get(
                    "reports_count"
                ),
                "operations_count": row.get(
                    "operations_count"
                ),
                "rain": row.get(
                    "rain"
                ),
                "approach": row.get(
                    "approach"
                ),
                "reconductor": row.get(
                    "reconductor"
                ),
                "refusal": row.get(
                    "refusal"
                ),
                "fined": row.get(
                    "fined"
                ),
                "towed": row.get(
                    "towed"
                ),
                "cnh_collected": row.get(
                    "cnh_collected"
                ),
                "four_ml": row.get(
                    "four_ml"
                ),
                "thirtythree_ml": row.get(
                    "thirtythree_ml"
                ),
                "thirtyfour_ml": row.get(
                    "thirtyfour_ml"
                ),
                "passive_tests_performed": (
                    row.get(
                        "passive_tests_performed"
                    )
                ),
                "removal_resolutions": (
                    row.get(
                        "removal_resolutions"
                    )
                ),
                "arrests_means_evidence": (
                    row.get(
                        "arrests_means_evidence"
                    )
                ),
                "art307": row.get(
                    "art307"
                ),
                "criminal_occurrences": (
                    row.get(
                        "criminal_occurrences"
                    )
                ),
                "driving_canceled_license": (
                    row.get(
                        "driving_canceled_license"
                    )
                ),
            }

            status_code, result = _post(
                url=options["url"],
                token=token,
                payload=request_payload,
                timeout=options["timeout"],
                retry=options["retry"],
            )

            counters["sent"] += 1

            outcome = result.get(
                "result"
            )

            if (
                status_code == 201
                and outcome == "created"
            ):
                counters[
                    "created"
                ] += 1

            elif (
                status_code == 200
                and outcome
                == "already_exists"
            ):
                counters[
                    "already_exists"
                ] += 1

            elif status_code == 409:
                counters[
                    "conflicts"
                ] += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"CONFLICT {index}: "
                        f"{result}"
                    )
                )

            else:
                counters[
                    "errors"
                ] += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR {index}: "
                        f"HTTP {status_code} "
                        f"{result}"
                    )
                )

            if options["delay"] > 0:
                time.sleep(
                    options["delay"]
                )

        self.stdout.write("")
        self.stdout.write(
            json.dumps(
                counters,
                ensure_ascii=False,
                indent=2,
            )
        )

        if (
            counters["conflicts"]
            or counters["errors"]
        ):
            raise CommandError(
                "Envio terminou com "
                "conflitos ou erros."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Extensão 2022 enviada "
                "com sucesso."
            )
        )
