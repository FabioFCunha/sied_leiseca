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


DATE_FROM = date(2023, 1, 1)
DATE_TO = date(2026, 8, 9)

EXPECTED_ROWS = 11225
EXPECTED_RAIN = 1780

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

    period_rows = []

    for row in rows:
        try:
            reference_date = (
                date.fromisoformat(
                    str(
                        row.get(
                            "reference_date"
                        )
                    )
                )
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise CommandError(
                "reference_date inválida "
                f"no JSON: "
                f"{row.get('reference_date')}"
            ) from exc

        if (
            DATE_FROM
            <= reference_date
            <= DATE_TO
        ):
            period_rows.append(
                row
            )

    total_rain = sum(
        int(
            row.get("rain")
            or 0
        )
        for row in period_rows
    )

    if len(period_rows) != EXPECTED_ROWS:
        raise CommandError(
            "Quantidade de linhas divergente: "
            f"{len(period_rows)} "
            f"!= {EXPECTED_ROWS}."
        )

    if total_rain != EXPECTED_RAIN:
        raise CommandError(
            "Total de chuva divergente: "
            f"{total_rain} "
            f"!= {EXPECTED_RAIN}."
        )

    positive_rows = [
        row
        for row in period_rows
        if int(
            row.get("rain")
            or 0
        ) > 0
    ]

    return (
        payload,
        period_rows,
        positive_rows,
        total_rain,
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
                    "push_horus_historical_rain/1.0"
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
        "somente os valores positivos de rain "
        "do histórico Horus DAILY / ERA_C "
        "entre 01/01/2023 e 09/08/2026."
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
            period_rows,
            positive_rows,
            total_rain,
        ) = _load(path)

        file_sha256 = _sha256(
            path
        )

        self.stdout.write(
            "=" * 80
        )
        self.stdout.write(
            "PUSH HORUS — CHUVA HISTÓRICA"
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
            f"Linhas do período: "
            f"{len(period_rows)}"
        )
        self.stdout.write(
            f"Linhas positivas a enviar: "
            f"{len(positive_rows)}"
        )
        self.stdout.write(
            f"Total chuva: {total_rain}"
        )
        self.stdout.write(
            "Observação: linhas com rain=0 "
            "não precisam ser gravadas; "
            "permanecer NULL equivale a zero "
            "na agregação histórica."
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
            positive_rows[:limit]
            if limit is not None
            else positive_rows
        )

        counters = {
            "sent": 0,
            "updated": 0,
            "unchanged": 0,
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
                    "UPDATE_RAIN"
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
                "rain": int(
                    row.get("rain")
                    or 0
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
                status_code == 200
                and outcome == "updated"
            ):
                counters[
                    "updated"
                ] += 1

            elif (
                status_code == 200
                and outcome == "unchanged"
            ):
                counters[
                    "unchanged"
                ] += 1

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

        if counters["errors"]:
            raise CommandError(
                "Envio de chuva terminou "
                "com erros."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Chuva histórica enviada "
                "com sucesso."
            )
        )
