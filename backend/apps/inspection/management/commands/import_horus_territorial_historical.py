import re
from collections import defaultdict
from datetime import date

from django.core.management.base import BaseCommand

from apps.inspection.horus_sync import HorusInspectionSyncer
from apps.inspection.models import (
    InspectionHistoricalTerritorialStatistic,
    InspectionMunicipality,
)
from apps.inspection.territorial import (
    normalize_municipality_name,
    resolve_municipality,
)


HISTORICAL_DATE_FROM = date(2022, 10, 3)
HISTORICAL_DATE_TO = date(2026, 8, 9)

PREFIX_PATTERN = re.compile(r"(?<!\d)(\d{1,2}\.\d{2})(?!\d)")
UNKNOWN_PREFIXES = {"11.16"}

PREFIX_TO_MUNICIPALITY_NAME = {
    "4.01": "Duque de Caxias",
    "4.02": "Nilópolis",
    "4.03": "Nova Iguaçu",
    "4.04": "Queimados",
    "4.05": "São João de Meriti",
    "4.06": "Belford Roxo",
    "4.07": "Magé",
    "4.09": "Japeri",
    "4.10": "Mesquita",
    "4.11": "Itaguaí",
    "4.12": "Guapimirim",
    "4.13": "Seropédica",
    "4.14": "Paracambi",
    "5.01": "Niterói",
    "5.02": "São Gonçalo",
    "5.03": "Itaboraí",
    "5.04": "Rio Bonito",
    "5.05": "Maricá",
    "5.06": "Tanguá",
    "6.01": "Itaperuna",
    "6.03": "Miracema",
    "6.04": "Itaocara",
    "6.05": "Cardoso Moreira",
    "6.06": "Bom Jesus do Itabapoana",
    "6.07": "Santo Antônio de Pádua",
    "7.01": "Campos dos Goytacazes",
    "7.02": "São João da Barra",
    "7.03": "Macaé",
    "7.04": "Conceição de Macabu",
    "7.05": "Quissamã",
    "8.01": "Nova Friburgo",
    "8.02": "Petrópolis",
    "8.03": "Teresópolis",
    "8.04": "Santa Maria Madalena",
    "8.05": "Cachoeiras de Macacu",
    "8.06": "Cordeiro",
    "8.07": "Macuco",
    "8.08": "São José do Vale do Rio Preto",
    "9.01": "Cabo Frio",
    "9.02": "Armação dos Búzios",
    "9.04": "Araruama",
    "9.05": "Saquarema",
    "9.06": "Rio das Ostras",
    "9.07": "São Pedro da Aldeia",
    "9.08": "Arraial do Cabo",
    "9.09": "Iguaba Grande",
    "9.11": "Casimiro de Abreu",
    "10.01": "Volta Redonda",
    "10.02": "Resende",
    "10.04": "Itatiaia",
    "11.01": "Barra Mansa",
    "11.02": "Vassouras",
    "11.04": "Miguel Pereira",
    "11.05": "Três Rios",
    "11.07": "Angra dos Reis",
    "11.08": "Barra do Piraí",
    "11.09": "Paraty",
    "11.10": "Paraíba do Sul",
    "11.11": "Mangaratiba",
    "11.12": "Valença",
    "11.13": "Paty do Alferes",
    "11.17": "Porciúncula",
    "11.19": "Piraí",
    "11.20": "Itatiaia",
    "11.21": "Bom Jardim",
    "11.22": "Varre-Sai",
}

METRIC_FIELDS = (
    "approach",
    "reconductor",
    "refusal",
    "fined",
    "towed",
    "cnh_collected",
    "four_ml",
    "thirtythree_ml",
    "thirtyfour_ml",
    "passive_tests_performed",
    "removal_resolutions",
    "arrests_means_evidence",
    "art307",
    "criminal_occurrences",
    "driving_canceled_license",
)

HORUS_HISTORICAL_TERRITORIAL_SQL = """
SELECT
    s.id AS section_id,
    st.id AS operation_id,
    s.operation_date,
    COALESCE(
        NULLIF(UPPER(TRIM(s.team)), ''),
        'SEM EQUIPE'
    ) AS team,
    COALESCE(st.city, '') AS source_city,
    COALESCE(st."addressOperation", '') AS address_operation,
    CASE
        WHEN (
            LOWER(COALESCE(s.changes_general, '')) LIKE '%%chuv%%'
            OR LOWER(COALESCE(s.changes_general, '')) LIKE '%%chove%%'
        )
        THEN 1
        ELSE 0
    END AS has_rain,
    COALESCE(st.approach, 0) AS approach,
    COALESCE(st.reconductor, 0) AS reconductor,
    COALESCE(st.refusal, 0) AS refusal,
    COALESCE(st.fined, 0) AS fined,
    COALESCE(st.towed, 0) AS towed,
    COALESCE(st.cnh_collected, 0) AS cnh_collected,
    COALESCE(st.four_ml, 0) AS four_ml,
    COALESCE(st.thirtythree_ml, 0) AS thirtythree_ml,
    COALESCE(st.thirtyfour_ml, 0) AS thirtyfour_ml,
    COALESCE(st.passive_tests_performed, 0) AS passive_tests_performed,
    COALESCE(st.removal_resolutions, 0) AS removal_resolutions,
    COALESCE(st.arrests_means_evidence, 0) AS arrests_means_evidence,
    COALESCE(st.art307, 0) AS art307,
    COALESCE(st.criminal_occurrences, 0) AS criminal_occurrences,
    COALESCE(st.driving_canceled_license, 0) AS driving_canceled_license
FROM rcols_sections s
LEFT JOIN rcols_section_twos st ON st.rcols_section_id = s.id
WHERE s.operation_date >= %s
  AND s.operation_date <= %s
ORDER BY
    s.operation_date,
    team,
    s.id,
    st.id
"""


def extract_territorial_prefix(address_operation):
    if not address_operation:
        return None

    match = PREFIX_PATTERN.search(str(address_operation))
    if not match:
        return None

    return match.group(1)


def municipality_name_for_prefix(prefix):
    if not prefix or prefix in UNKNOWN_PREFIXES:
        return None

    if re.match(r"^[0-3]\.\d{2}$", prefix):
        return "Rio de Janeiro"

    return PREFIX_TO_MUNICIPALITY_NAME.get(prefix)


def load_municipalities_by_prefix():
    municipality_names = {
        "Rio de Janeiro",
        *PREFIX_TO_MUNICIPALITY_NAME.values(),
    }
    normalized_names = {
        normalize_municipality_name(name)
        for name in municipality_names
    }

    municipalities = (
        InspectionMunicipality.objects.select_related("region")
        .filter(
            normalized_name__in=normalized_names,
            is_active=True,
            region__is_active=True,
        )
    )

    return {
        municipality.normalized_name: municipality
        for municipality in municipalities
    }


def resolve_municipality_from_city(source_city):
    if not source_city:
        return None

    return resolve_municipality(source_city)


def resolve_municipality_from_prefix(prefix, municipalities_by_name):
    municipality_name = municipality_name_for_prefix(prefix)
    if not municipality_name:
        return None

    return municipalities_by_name.get(
        normalize_municipality_name(municipality_name)
    )


class Command(BaseCommand):
    help = "Importa dados territoriais historicos do Horus."

    def _build_statistics(self, raw_rows):
        municipalities_by_name = load_municipalities_by_prefix()
        operation_rows = []
        valid_prefixes_by_section = defaultdict(set)

        for row in raw_rows:
            (
                section_id,
                operation_id,
                operation_date,
                team,
                source_city,
                address_operation,
                has_rain,
                approach,
                reconductor,
                refusal,
                fined,
                towed,
                cnh_collected,
                four_ml,
                thirtythree_ml,
                thirtyfour_ml,
                passive_tests_performed,
                removal_resolutions,
                arrests_means_evidence,
                art307,
                criminal_occurrences,
                driving_canceled_license,
            ) = row

            if operation_id is None:
                continue

            own_prefix = extract_territorial_prefix(address_operation)
            own_prefix_is_valid = (
                municipality_name_for_prefix(own_prefix) is not None
            )

            if own_prefix_is_valid:
                valid_prefixes_by_section[section_id].add(own_prefix)

            operation_rows.append(
                {
                    "section_id": section_id,
                    "operation_date": operation_date,
                    "team": team,
                    "source_city": source_city or "",
                    "normalized_city": normalize_municipality_name(
                        source_city or ""
                    ),
                    "has_rain": bool(has_rain),
                    "own_prefix": own_prefix,
                    "own_prefix_is_valid": own_prefix_is_valid,
                    "metrics": {
                        "approach": approach or 0,
                        "reconductor": reconductor or 0,
                        "refusal": refusal or 0,
                        "fined": fined or 0,
                        "towed": towed or 0,
                        "cnh_collected": cnh_collected or 0,
                        "four_ml": four_ml or 0,
                        "thirtythree_ml": thirtythree_ml or 0,
                        "thirtyfour_ml": thirtyfour_ml or 0,
                        "passive_tests_performed": (
                            passive_tests_performed or 0
                        ),
                        "removal_resolutions": (
                            removal_resolutions or 0
                        ),
                        "arrests_means_evidence": (
                            arrests_means_evidence or 0
                        ),
                        "art307": art307 or 0,
                        "criminal_occurrences": (
                            criminal_occurrences or 0
                        ),
                        "driving_canceled_license": (
                            driving_canceled_license or 0
                        ),
                    },
                }
            )

        aggregated = {}

        for operation in operation_rows:
            section_prefixes = valid_prefixes_by_section.get(
                operation["section_id"],
                set(),
            )

            effective_prefix = None
            municipality = None

            # Resolution order is intentionally strict for auditability:
            # 1. own valid prefix
            # 2. exactly one valid prefix elsewhere in the same report
            # 3. exact municipality match by source_city only when there is
            #    no valid territorial prefix evidence in the report
            if operation["own_prefix"] is not None:
                if operation["own_prefix_is_valid"]:
                    effective_prefix = operation["own_prefix"]
            elif len(section_prefixes) == 1:
                effective_prefix = next(iter(section_prefixes))

            if effective_prefix is not None:
                municipality = resolve_municipality_from_prefix(
                    effective_prefix,
                    municipalities_by_name,
                )
            elif len(section_prefixes) == 0:
                municipality = resolve_municipality_from_city(
                    operation["source_city"]
                )

            region = municipality.region if municipality else None

            key = (
                operation["operation_date"],
                operation["team"],
                operation["source_city"],
                operation["normalized_city"],
                municipality.id if municipality else None,
                region.id if region else None,
            )

            if key not in aggregated:
                aggregated[key] = {
                    "reference_date": operation["operation_date"],
                    "team": operation["team"],
                    "source_city": operation["source_city"],
                    "normalized_city": operation["normalized_city"],
                    "municipality": municipality,
                    "region": region,
                    "reports": set(),
                    "rain_reports": set(),
                    "operations_count": 0,
                    "metrics": {field: 0 for field in METRIC_FIELDS},
                }

            item = aggregated[key]
            item["reports"].add(operation["section_id"])
            if operation["has_rain"]:
                item["rain_reports"].add(operation["section_id"])
            item["operations_count"] += 1

            for field, value in operation["metrics"].items():
                item["metrics"][field] += value

        statistics = []
        for item in aggregated.values():
            statistics.append(
                InspectionHistoricalTerritorialStatistic(
                    reference_date=item["reference_date"],
                    team=item["team"],
                    source_city=item["source_city"],
                    normalized_city=item["normalized_city"],
                    municipality=item["municipality"],
                    region=item["region"],
                    reports_count=len(item["reports"]),
                    operations_count=item["operations_count"],
                    rain=len(item["rain_reports"]),
                    **item["metrics"],
                )
            )

        return statistics

    def handle(self, *args, **options):
        self.stdout.write("Conectando ao Horus...")
        syncer = HorusInspectionSyncer()
        conn = syncer.connect_horus()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    HORUS_HISTORICAL_TERRITORIAL_SQL,
                    (HISTORICAL_DATE_FROM, HISTORICAL_DATE_TO),
                )
                raw_rows = cursor.fetchall()

            self.stdout.write(
                f"Encontradas {len(raw_rows)} operacoes brutas. Inserindo no banco local..."
            )

            statistics = self._build_statistics(raw_rows)

            InspectionHistoricalTerritorialStatistic.objects.all().delete()
            InspectionHistoricalTerritorialStatistic.objects.bulk_create(
                statistics
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Importacao territorial historica concluida."
                )
            )
        finally:
            conn.close()
