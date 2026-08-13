"""
Comando Django: push_horus_inspection_historical

Lê o JSON histórico exportado do Horus e envia registro a registro
por HTTPS autenticado para o endpoint da VPS:

    POST /api/inspection/sync/historical/push/

Uso:
    # Apenas valida o JSON localmente, sem enviar:
    python manage.py push_horus_inspection_historical \\
        --file horus_historical.json \\
        --url https://sied-leiseca.online/api/inspection/sync/historical/push/ \\
        --dry-run

    # Envia 1 registro (teste):
    python manage.py push_horus_inspection_historical \\
        --file horus_historical.json \\
        --url https://sied-leiseca.online/api/inspection/sync/historical/push/ \\
        --send \\
        --limit 1

    # Envia todos (idempotente):
    python manage.py push_horus_inspection_historical \\
        --file horus_historical.json \\
        --url https://sied-leiseca.online/api/inspection/sync/historical/push/ \\
        --send

Variáveis de ambiente necessárias no Windows:
    SIED_INSPECTION_SYNC_TOKEN  → token técnico de autenticação
    (ou passe --token diretamente)

Saída resumida:
    found          : registros encontrados no JSON
    sent           : registros efetivamente enviados ao endpoint
    created        : novos registros criados (HTTP 201)
    already_exists : registros já existentes e idênticos (HTTP 200)
    conflicts      : registros existentes com dados DIFERENTES (HTTP 409)
    errors         : falhas de rede ou resposta inesperada
"""

import hashlib
import json
import os
import time
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.core.management.base import BaseCommand, CommandError


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 2


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_and_validate_json(path: Path) -> tuple[dict, list[dict]]:
    """
    Carrega o JSON e faz validação mínima da estrutura.
    Retorna (payload, rows).
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandError(f"JSON inválido: {exc}") from exc

    if not isinstance(payload, dict):
        raise CommandError("O JSON precisa conter um objeto na raiz.")

    metadata = payload.get("metadata") or {}

    errors = []

    if metadata.get("source") != "HORUS":
        errors.append("metadata.source deve ser HORUS.")

    if metadata.get("source_type") != "DAILY":
        errors.append("metadata.source_type deve ser DAILY.")

    if metadata.get("taxonomy_era") != "ERA_C":
        errors.append("metadata.taxonomy_era deve ser ERA_C.")

    if metadata.get("date_from") != "2023-01-01":
        errors.append("metadata.date_from deve ser 2023-01-01.")

    if metadata.get("date_to") != "2026-08-09":
        errors.append("metadata.date_to deve ser 2026-08-09.")

    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("Campo rows ausente ou vazio.")

    if errors:
        raise CommandError(
            "Arquivo JSON inválido:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return payload, rows


def _post_single(
    *,
    url: str,
    token: str,
    payload: dict,
    timeout: int,
    retry_attempts: int,
    retry_delay: float,
) -> dict:
    """
    Envia um único registro ao endpoint via HTTPS.
    Retorna dict com: status_code, result, body.
    """
    body_bytes = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")

    last_exc = None

    for attempt in range(1, retry_attempts + 1):
        req = urllib_request.Request(
            url,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "push_horus_inspection_historical/1.0",
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                body = json.loads(raw) if raw else {}
                return {
                    "status_code": resp.status,
                    "result": body.get("result", "ok"),
                    "body": body,
                }

        except urllib_error.HTTPError as exc:
            raw = exc.read()
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                body = {"raw": raw.decode("utf-8", errors="replace")}

            # 409 Conflict: não é erro de rede — não faz retry
            if exc.code == 409:
                return {
                    "status_code": exc.code,
                    "result": "conflict",
                    "body": body,
                }

            # 400 Bad Request: erro de dados — não faz retry
            if exc.code == 400:
                return {
                    "status_code": exc.code,
                    "result": "error",
                    "body": body,
                }

            last_exc = exc

        except (urllib_error.URLError, OSError) as exc:
            last_exc = exc

        if attempt < retry_attempts:
            time.sleep(retry_delay)

    return {
        "status_code": 0,
        "result": "error",
        "body": {"error": str(last_exc)},
    }


class Command(BaseCommand):
    help = (
        "Envia o histórico consolidado do Horus (DAILY / ERA_C, "
        "2023-01-01 a 2026-08-09) para a VPS/SIED via HTTPS autenticado. "
        "Idempotente: reenvio do mesmo registro retorna already_exists (200)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Caminho do arquivo JSON exportado do Horus.",
        )

        parser.add_argument(
            "--url",
            required=True,
            help=(
                "URL do endpoint na VPS. "
                "Exemplo: https://sied-leiseca.online/api/inspection/sync/historical/push/"
            ),
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Valida o arquivo JSON localmente e mostra o resumo esperado. "
                "Não envia nenhum dado ao endpoint."
            ),
        )

        parser.add_argument(
            "--send",
            action="store_true",
            help="Envia os registros ao endpoint. Obrigatório para execução real.",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limita a quantidade de registros enviados (útil para teste de 1 registro).",
        )

        parser.add_argument(
            "--token",
            default=None,
            help=(
                "Token técnico de autenticação. "
                "Se omitido, usa a variável de ambiente SIED_INSPECTION_SYNC_TOKEN."
            ),
        )

        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_TIMEOUT_SECONDS,
            help=f"Timeout HTTP em segundos (padrão: {DEFAULT_TIMEOUT_SECONDS}).",
        )

        parser.add_argument(
            "--retry",
            type=int,
            default=DEFAULT_RETRY_ATTEMPTS,
            help=f"Tentativas de reenvio em caso de erro de rede (padrão: {DEFAULT_RETRY_ATTEMPTS}).",
        )

    def handle(self, *args, **options):
        is_dry_run = bool(options.get("dry_run"))
        is_send = bool(options.get("send"))

        if is_dry_run == is_send:
            raise CommandError(
                "Informe exatamente um modo: --dry-run ou --send."
            )

        limit = options.get("limit")
        if limit is not None and limit <= 0:
            raise CommandError("--limit deve ser maior que zero.")

        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"Arquivo não encontrado: {file_path}")

        # Carrega e valida JSON
        payload, all_rows = _load_and_validate_json(file_path)

        sha256 = _compute_sha256(file_path)
        summary_meta = payload.get("summary") or {}
        metadata = payload.get("metadata") or {}

        self.stdout.write(
            self.style.SUCCESS("=== push_horus_inspection_historical ===")
        )
        self.stdout.write(f"  arquivo  : {file_path.resolve()}")
        self.stdout.write(f"  sha256   : {sha256}")
        self.stdout.write(f"  source   : {metadata.get('source')}")
        self.stdout.write(f"  type     : {metadata.get('source_type')}")
        self.stdout.write(f"  era      : {metadata.get('taxonomy_era')}")
        self.stdout.write(f"  periodo  : {metadata.get('date_from')} -> {metadata.get('date_to')}")
        self.stdout.write(f"  rows     : {len(all_rows)}")
        self.stdout.write(f"  reports  : {summary_meta.get('reports')}")
        self.stdout.write(f"  operations: {summary_meta.get('operations')}")
        self.stdout.write("")

        rows_to_send = all_rows[:limit] if limit is not None else all_rows

        counters = {
            "found": len(all_rows),
            "sent": 0,
            "created": 0,
            "already_exists": 0,
            "conflicts": 0,
            "errors": 0,
        }

        if is_dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] {len(rows_to_send)} registro(s) seriam enviados "
                    f"(de {counters['found']} encontrados)."
                )
            )
            self.stdout.write("")
            self._print_summary(counters, dry_run=True, limit=limit)
            return

        # ── modo --send ──────────────────────────────────────────────────────
        url = options["url"].rstrip("/") + "/"

        token = (
            options.get("token")
            or str(os.environ.get("SIED_INSPECTION_SYNC_TOKEN", "") or "").strip()
        )
        if not token:
            raise CommandError(
                "Token ausente. Informe --token ou defina "
                "a variável de ambiente SIED_INSPECTION_SYNC_TOKEN."
            )

        timeout = int(options.get("timeout") or DEFAULT_TIMEOUT_SECONDS)
        retry_attempts = int(options.get("retry") or DEFAULT_RETRY_ATTEMPTS)

        self.stdout.write(
            f"Enviando {len(rows_to_send)} registro(s) para {url} ..."
        )
        self.stdout.write("")

        for idx, row in enumerate(rows_to_send, start=1):
            # Monta payload do endpoint (inclui sha256 do arquivo)
            push_payload = {
                "file_sha256": sha256,
                "source_type": row.get("source_type", "DAILY"),
                "taxonomy_era": row.get("taxonomy_era", "ERA_C"),
                "reference_date": row.get("reference_date"),
                "team": row.get("team"),
                "source_row": row.get("source_row", idx),
                "reports_count": row.get("reports_count"),
                "operations_count": row.get("operations_count"),
                "approach": row.get("approach"),
                "reconductor": row.get("reconductor"),
                "refusal": row.get("refusal"),
                "fined": row.get("fined"),
                "towed": row.get("towed"),
                "cnh_collected": row.get("cnh_collected"),
                "four_ml": row.get("four_ml"),
                "thirtythree_ml": row.get("thirtythree_ml"),
                "thirtyfour_ml": row.get("thirtyfour_ml"),
                "passive_tests_performed": row.get("passive_tests_performed"),
                "removal_resolutions": row.get("removal_resolutions"),
                "arrests_means_evidence": row.get("arrests_means_evidence"),
                "art307": row.get("art307"),
                "criminal_occurrences": row.get("criminal_occurrences"),
                "driving_canceled_license": row.get("driving_canceled_license"),
            }

            response = _post_single(
                url=url,
                token=token,
                payload=push_payload,
                timeout=timeout,
                retry_attempts=retry_attempts,
                retry_delay=DEFAULT_RETRY_DELAY_SECONDS,
            )

            counters["sent"] += 1
            result = response["result"]

            if result == "created":
                counters["created"] += 1
                marker = self.style.SUCCESS("✓ CRIADO")
            elif result == "already_exists":
                counters["already_exists"] += 1
                marker = self.style.WARNING("= EXISTIA")
            elif result == "conflict":
                counters["conflicts"] += 1
                marker = self.style.ERROR("✗ CONFLITO")
                diffs = response["body"].get("differences") or {}
                self.stdout.write(
                    f"  [{idx:>6}] {row.get('reference_date')} / "
                    f"{row.get('team')} → {marker}"
                )
                self.stdout.write(
                    f"           diffs: {json.dumps(diffs, ensure_ascii=False)}"
                )
                continue
            else:
                counters["errors"] += 1
                marker = self.style.ERROR("✗ ERRO")
                self.stdout.write(
                    f"  [{idx:>6}] {row.get('reference_date')} / "
                    f"{row.get('team')} → {marker} "
                    f"(HTTP {response['status_code']}): "
                    f"{json.dumps(response['body'], ensure_ascii=False)[:200]}"
                )
                continue

            # Progresso a cada 100 registros ou para created/already_exists
            if idx % 100 == 0 or result == "created":
                self.stdout.write(
                    f"  [{idx:>6}/{len(rows_to_send)}] "
                    f"{row.get('reference_date')} / {row.get('team')} "
                    f"→ {marker}"
                )

        self.stdout.write("")
        self._print_summary(counters, dry_run=False, limit=limit)

    def _print_summary(
        self,
        counters: dict,
        *,
        dry_run: bool,
        limit: int | None,
    ):
        mode = "DRY-RUN" if dry_run else "RESULTADO"

        self.stdout.write(self.style.SUCCESS(f"=== {mode} ==="))
        self.stdout.write(f"  found          : {counters['found']}")

        if limit is not None:
            self.stdout.write(f"  limit          : {limit}")

        if not dry_run:
            self.stdout.write(f"  sent           : {counters['sent']}")
            self.stdout.write(f"  created        : {counters['created']}")
            self.stdout.write(f"  already_exists : {counters['already_exists']}")
            self.stdout.write(f"  conflicts      : {counters['conflicts']}")
            self.stdout.write(f"  errors         : {counters['errors']}")

            total_ok = counters["created"] + counters["already_exists"]
            self.stdout.write("")

            if counters["conflicts"] == 0 and counters["errors"] == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Concluído com sucesso. "
                        f"{total_ok} registro(s) OK "
                        f"({counters['created']} criados, "
                        f"{counters['already_exists']} já existiam)."
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Concluído com problemas: "
                        f"{counters['conflicts']} conflito(s), "
                        f"{counters['errors']} erro(s)."
                    )
                )
