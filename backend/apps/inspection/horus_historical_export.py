import hashlib
import json
from datetime import date
from pathlib import Path

from apps.inspection.horus_sync import HorusInspectionSyncer


HISTORICAL_DATE_FROM = date(2022, 10, 3)
HISTORICAL_DATE_TO = date(2026, 8, 9)

SOURCE_TYPE = "DAILY"
TAXONOMY_ERA = "ERA_C"


HORUS_HISTORICAL_SQL = """
SELECT
    s.operation_date,
    COALESCE(
        NULLIF(UPPER(TRIM(s.team)), ''),
        'SEM EQUIPE'
    ) AS team,

    COUNT(DISTINCT s.id) AS reports_count,
    COUNT(st.id) AS operations_count,

    COUNT(
        DISTINCT CASE
            WHEN (
                LOWER(
                    COALESCE(
                        s.changes_general,
                        ''
                    )
                ) LIKE '%%chuv%%'
                OR LOWER(
                    COALESCE(
                        s.changes_general,
                        ''
                    )
                ) LIKE '%%chove%%'
            )
            THEN s.id
            ELSE NULL
        END
    ) AS rain,

    SUM(st.approach) AS approach,
    SUM(st.reconductor) AS reconductor,
    SUM(st.refusal) AS refusal,

    SUM(st.fined) AS fined,
    SUM(st.towed) AS towed,

    SUM(st.cnh_collected) AS cnh_collected,

    SUM(st.four_ml) AS four_ml,
    SUM(st.thirtythree_ml) AS thirtythree_ml,
    SUM(st.thirtyfour_ml) AS thirtyfour_ml,

    SUM(
        st.passive_tests_performed
    ) AS passive_tests_performed,

    SUM(
        st.removal_resolutions
    ) AS removal_resolutions,

    SUM(
        st.arrests_means_evidence
    ) AS arrests_means_evidence,

    SUM(st.art307) AS art307,

    SUM(
        st.criminal_occurrences
    ) AS criminal_occurrences,

    SUM(
        st.driving_canceled_license
    ) AS driving_canceled_license

FROM rcols_sections s

LEFT JOIN rcols_section_twos st
    ON st.rcols_section_id = s.id

WHERE s.operation_date >= %s
  AND s.operation_date <= %s

GROUP BY
    s.operation_date,
    COALESCE(
        NULLIF(UPPER(TRIM(s.team)), ''),
        'SEM EQUIPE'
    )

ORDER BY
    s.operation_date,
    team
"""


FIELDS = [
    "reference_date",
    "team",
    "reports_count",
    "operations_count",
    "rain",
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
]


def _sum_nullable(rows, field):
    values = [
        row.get(field)
        for row in rows
        if row.get(field) is not None
    ]

    if not values:
        return None

    return sum(values)


def _build_annual_controls(rows):
    years = {}

    for year in range(
        HISTORICAL_DATE_FROM.year,
        HISTORICAL_DATE_TO.year + 1,
    ):
        year_rows = [
            row
            for row in rows
            if row["reference_year"] == year
        ]

        years[str(year)] = {
            "rows": len(year_rows),

            "reports": sum(
                row["reports_count"]
                for row in year_rows
            ),

            "operations": sum(
                row["operations_count"]
                for row in year_rows
            ),

            "rain": _sum_nullable(
                year_rows,
                "rain",
            ),

            "approach": _sum_nullable(
                year_rows,
                "approach",
            ),

            "reconductor": _sum_nullable(
                year_rows,
                "reconductor",
            ),

            "refusal": _sum_nullable(
                year_rows,
                "refusal",
            ),

            "fined": _sum_nullable(
                year_rows,
                "fined",
            ),

            "towed": _sum_nullable(
                year_rows,
                "towed",
            ),

            "cnh_collected": _sum_nullable(
                year_rows,
                "cnh_collected",
            ),

            "four_ml": _sum_nullable(
                year_rows,
                "four_ml",
            ),

            "thirtythree_ml": _sum_nullable(
                year_rows,
                "thirtythree_ml",
            ),

            "thirtyfour_ml": _sum_nullable(
                year_rows,
                "thirtyfour_ml",
            ),

            "passive_tests_performed": _sum_nullable(
                year_rows,
                "passive_tests_performed",
            ),

            "removal_resolutions": _sum_nullable(
                year_rows,
                "removal_resolutions",
            ),

            "arrests_means_evidence": _sum_nullable(
                year_rows,
                "arrests_means_evidence",
            ),

            "art307": _sum_nullable(
                year_rows,
                "art307",
            ),

            "criminal_occurrences": _sum_nullable(
                year_rows,
                "criminal_occurrences",
            ),

            "driving_canceled_license": _sum_nullable(
                year_rows,
                "driving_canceled_license",
            ),
        }

    return years


def _compute_sha256(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


class HorusHistoricalExporter:
    def __init__(self, syncer=None):
        self.syncer = (
            syncer
            or HorusInspectionSyncer()
        )

    def fetch_rows(self):
        conn = self.syncer.connect_horus()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    HORUS_HISTORICAL_SQL,
                    (
                        HISTORICAL_DATE_FROM,
                        HISTORICAL_DATE_TO,
                    ),
                )

                raw_rows = cursor.fetchall()

            rows = []

            for source_row, values in enumerate(
                raw_rows,
                start=1,
            ):
                item = dict(
                    zip(
                        FIELDS,
                        values,
                    )
                )

                reference_date = item[
                    "reference_date"
                ]

                item[
                    "reference_date"
                ] = reference_date.isoformat()

                item[
                    "reference_year"
                ] = reference_date.year

                item[
                    "reference_month"
                ] = reference_date.month

                item[
                    "source_type"
                ] = SOURCE_TYPE

                item[
                    "taxonomy_era"
                ] = TAXONOMY_ERA

                item[
                    "source_sheet"
                ] = "HORUS"

                item[
                    "source_row"
                ] = source_row

                item[
                    "source_team_label"
                ] = item["team"]

                rows.append(item)

            return rows

        finally:
            try:
                conn.rollback()
            finally:
                conn.close()

    def build_payload(self):
        rows = self.fetch_rows()

        date_values = [
            row["reference_date"]
            for row in rows
        ]

        teams = sorted(
            {
                row["team"]
                for row in rows
            }
        )

        annual_controls = (
            _build_annual_controls(rows)
        )

        return {
            "metadata": {
                "source": "HORUS",
                "source_type": SOURCE_TYPE,
                "taxonomy_era": TAXONOMY_ERA,

                "date_from": (
                    HISTORICAL_DATE_FROM
                    .isoformat()
                ),

                "date_to": (
                    HISTORICAL_DATE_TO
                    .isoformat()
                ),

                "read_only_source": True,

                "granularity": (
                    "reference_date+team"
                ),

                "rain_methodology": (
                    "COUNT DISTINCT report id "
                    "quando changes_general "
                    "contem 'chuv' ou 'chove'"
                ),
            },

            "summary": {
                "rows": len(rows),

                "reports": sum(
                    row["reports_count"]
                    for row in rows
                ),

                "operations": sum(
                    row["operations_count"]
                    for row in rows
                ),

                "rain": _sum_nullable(
                    rows,
                    "rain",
                ),

                "teams": len(teams),

                "date_start": (
                    min(date_values)
                    if date_values
                    else None
                ),

                "date_end": (
                    max(date_values)
                    if date_values
                    else None
                ),
            },

            "annual_controls": annual_controls,

            "teams": teams,

            "rows": rows,
        }

    def export(self, output_path):
        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = self.build_payload()

        output_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        return {
            "output": str(
                output_path.resolve()
            ),

            "sha256": _compute_sha256(
                output_path
            ),

            "summary": payload[
                "summary"
            ],

            "annual_controls": payload[
                "annual_controls"
            ],
        }