import csv
from collections import Counter
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.inspection.models import InspectionHistoricalStatistic


HISTORICAL_RAIN_MAX_DATE = date(2026, 8, 9)
EXPECTED_SOURCE_TYPE = "DAILY"
EXPECTED_TAXONOMY_ERA = "ERA_C"

REQUIRED_COLUMNS = (
    "reference_date",
    "team",
    "rain",
)


class Command(BaseCommand):
    help = (
        "Atualiza SOMENTE o campo rain do histórico Horus DAILY / ERA_C "
        "já existente no SIED. Por padrão executa apenas dry-run. "
        "Use --apply para persistir."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help=(
                "CSV UTF-8 com colunas: reference_date,team,rain. "
                "Ex.: 2026-01-13,BRAVO,1"
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Persiste as alterações. Sem esta opção o comando "
                "é somente dry-run."
            ),
        )
        parser.add_argument(
            "--show-unchanged",
            action="store_true",
            help="Também lista linhas cujo valor de rain já é igual ao CSV.",
        )

    def handle(self, *args, **options):
        input_path = Path(options["file"])
        apply_changes = bool(options["apply"])
        show_unchanged = bool(options["show_unchanged"])

        if not input_path.exists():
            raise CommandError(f"Arquivo não encontrado: {input_path}")

        if not input_path.is_file():
            raise CommandError(f"O caminho informado não é arquivo: {input_path}")

        rows = self._read_csv(input_path)
        self._validate_unique_keys(rows)

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write("=" * 80)
        self.stdout.write("ATUALIZAÇÃO HISTÓRICA DE CHUVA — FISCALIZAÇÃO")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Modo: {mode}")
        self.stdout.write(f"Arquivo: {input_path}")
        self.stdout.write(f"Linhas CSV válidas: {len(rows)}")
        self.stdout.write(
            "Escopo permitido: DAILY / ERA_C / is_validation_only=False "
            f"/ até {HISTORICAL_RAIN_MAX_DATE.isoformat()}"
        )
        self.stdout.write("Campo permitido para alteração: rain")
        self.stdout.write("")

        stats = Counter()

        with transaction.atomic():
            for row_number, item in rows:
                result = self._process_row(
                    row_number=row_number,
                    item=item,
                    apply_changes=apply_changes,
                    show_unchanged=show_unchanged,
                )
                stats[result] += 1

            if not apply_changes:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write("RESUMO")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Atualizariam/atualizadas: {stats['updated']}")
        self.stdout.write(f"Sem alteração: {stats['unchanged']}")
        self.stdout.write(f"Não encontradas: {stats['not_found']}")
        self.stdout.write(f"Ambíguas (>1 registro): {stats['ambiguous']}")
        self.stdout.write("")

        if stats["not_found"] or stats["ambiguous"]:
            raise CommandError(
                "Validação falhou: existem chaves não encontradas ou ambíguas. "
                "Nenhuma alteração deve ser considerada aprovada até corrigir "
                "essas divergências."
            )

        if apply_changes:
            self.stdout.write(
                self.style.SUCCESS(
                    "Concluído. Somente InspectionHistoricalStatistic.rain "
                    "foi atualizado."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN concluído. Nenhuma alteração foi persistida. "
                    "Revise o resultado e só depois use --apply."
                )
            )

    def _read_csv(self, input_path):
        rows = []

        try:
            with input_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                reader = csv.DictReader(handle)

                if not reader.fieldnames:
                    raise CommandError("CSV sem cabeçalho.")

                normalized_headers = {
                    str(name or "").strip()
                    for name in reader.fieldnames
                }

                missing = [
                    column
                    for column in REQUIRED_COLUMNS
                    if column not in normalized_headers
                ]
                if missing:
                    raise CommandError(
                        "CSV sem colunas obrigatórias: "
                        + ", ".join(missing)
                    )

                for row_number, raw in enumerate(reader, start=2):
                    item = self._normalize_row(row_number, raw)
                    rows.append((row_number, item))

        except UnicodeDecodeError as exc:
            raise CommandError(
                "O CSV deve estar em UTF-8."
            ) from exc

        if not rows:
            raise CommandError("CSV não possui linhas de dados.")

        return rows

    def _normalize_row(self, row_number, raw):
        date_raw = str(raw.get("reference_date") or "").strip()
        team = str(raw.get("team") or "").strip()
        rain_raw = str(raw.get("rain") or "").strip()

        if not date_raw:
            raise CommandError(
                f"Linha {row_number}: reference_date vazio."
            )

        try:
            reference_date = date.fromisoformat(date_raw)
        except ValueError as exc:
            raise CommandError(
                f"Linha {row_number}: data inválida '{date_raw}'. "
                "Use YYYY-MM-DD."
            ) from exc

        if reference_date > HISTORICAL_RAIN_MAX_DATE:
            raise CommandError(
                f"Linha {row_number}: {reference_date} ultrapassa "
                f"o limite histórico {HISTORICAL_RAIN_MAX_DATE}."
            )

        if not team:
            raise CommandError(
                f"Linha {row_number}: team vazio."
            )

        try:
            rain = int(rain_raw)
        except ValueError as exc:
            raise CommandError(
                f"Linha {row_number}: rain inválido '{rain_raw}'. "
                "Informe inteiro >= 0."
            ) from exc

        if rain < 0:
            raise CommandError(
                f"Linha {row_number}: rain não pode ser negativo."
            )

        return {
            "reference_date": reference_date,
            "team": team,
            "rain": rain,
        }

    def _validate_unique_keys(self, rows):
        seen = {}

        for row_number, item in rows:
            key = (
                item["reference_date"],
                item["team"].casefold(),
            )

            if key in seen:
                raise CommandError(
                    "CSV possui chave duplicada "
                    f"(reference_date + team): linhas "
                    f"{seen[key]} e {row_number}."
                )

            seen[key] = row_number

    def _process_row(
        self,
        *,
        row_number,
        item,
        apply_changes,
        show_unchanged,
    ):
        qs = (
            InspectionHistoricalStatistic.objects
            .select_for_update()
            .filter(
                reference_date=item["reference_date"],
                team__iexact=item["team"],
                source_type=EXPECTED_SOURCE_TYPE,
                taxonomy_era=EXPECTED_TAXONOMY_ERA,
                is_validation_only=False,
            )
        )

        count = qs.count()

        label = (
            f"linha={row_number} "
            f"data={item['reference_date']} "
            f"equipe={item['team']}"
        )

        if count == 0:
            self.stdout.write(
                self.style.ERROR(
                    f"NOT_FOUND | {label} | rain_csv={item['rain']}"
                )
            )
            return "not_found"

        if count > 1:
            ids = list(
                qs.order_by("id")
                .values_list("id", flat=True)[:10]
            )
            self.stdout.write(
                self.style.ERROR(
                    f"AMBIGUOUS | {label} | "
                    f"registros={count} | ids={ids}"
                )
            )
            return "ambiguous"

        obj = qs.get()
        old_value = obj.rain
        new_value = item["rain"]

        if old_value == new_value:
            if show_unchanged:
                self.stdout.write(
                    f"UNCHANGED | {label} | rain={new_value}"
                )
            return "unchanged"

        self.stdout.write(
            f"{'UPDATE' if apply_changes else 'WOULD_UPDATE'} | "
            f"{label} | id={obj.id} | "
            f"rain: {old_value!r} -> {new_value}"
        )

        if apply_changes:
            # Segurança: update_fields garante que NENHUM outro
            # indicador histórico seja persistido por este comando.
            obj.rain = new_value
            obj.save(update_fields=["rain"])

        return "updated"
