import json
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from apps.inspection.models import InspectionHistoricalTerritorialStatistic
from apps.inspection.horus_sync import HorusInspectionSyncer
from apps.inspection.territorial import resolve_territory

HISTORICAL_DATE_FROM = date(2022, 10, 3)
HISTORICAL_DATE_TO = date(2026, 8, 9)

HORUS_HISTORICAL_TERRITORIAL_SQL = """
SELECT
    s.operation_date,
    COALESCE(
        NULLIF(UPPER(TRIM(s.team)), ''),
        'SEM EQUIPE'
    ) AS team,
    COALESCE(
        st.city,
        ''
    ) AS source_city,

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
    SUM(st.passive_tests_performed) AS passive_tests_performed,
    SUM(st.removal_resolutions) AS removal_resolutions,
    SUM(st.arrests_means_evidence) AS arrests_means_evidence,
    SUM(st.art307) AS art307,
    SUM(st.criminal_occurrences) AS criminal_occurrences,
    SUM(st.driving_canceled_license) AS driving_canceled_license

FROM rcols_sections s
LEFT JOIN rcols_section_twos st ON st.rcols_section_id = s.id

WHERE s.operation_date >= %s
  AND s.operation_date <= %s

GROUP BY
    s.operation_date,
    COALESCE(
        NULLIF(UPPER(TRIM(s.team)), ''),
        'SEM EQUIPE'
    ),
    COALESCE(
        st.city,
        ''
    )

ORDER BY
    s.operation_date,
    team,
    source_city
"""

class Command(BaseCommand):
    help = "Importa dados territoriais historicos do Horus."

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

            self.stdout.write(f"Encontradas {len(raw_rows)} linhas. Inserindo no banco local...")
            
            InspectionHistoricalTerritorialStatistic.objects.all().delete()
            
            batch = []
            for row in raw_rows:
                operation_date, team, source_city, reports_count, operations_count, rain, \
                approach, reconductor, refusal, fined, towed, cnh_collected, four_ml, \
                thirtythree_ml, thirtyfour_ml, passive_tests_performed, removal_resolutions, \
                arrests_means_evidence, art307, criminal_occurrences, driving_canceled_license = row
                
                territory = resolve_territory(source_city)
                
                batch.append(InspectionHistoricalTerritorialStatistic(
                    reference_date=operation_date,
                    team=team,
                    source_city=source_city,
                    normalized_city=territory["normalized_city"],
                    municipality_id=territory["municipality_id"],
                    region_id=territory["region_id"],
                    reports_count=reports_count or 0,
                    operations_count=operations_count or 0,
                    rain=rain or 0,
                    approach=approach or 0,
                    reconductor=reconductor or 0,
                    refusal=refusal or 0,
                    fined=fined or 0,
                    towed=towed or 0,
                    cnh_collected=cnh_collected or 0,
                    four_ml=four_ml or 0,
                    thirtythree_ml=thirtythree_ml or 0,
                    thirtyfour_ml=thirtyfour_ml or 0,
                    passive_tests_performed=passive_tests_performed or 0,
                    removal_resolutions=removal_resolutions or 0,
                    arrests_means_evidence=arrests_means_evidence or 0,
                    art307=art307 or 0,
                    criminal_occurrences=criminal_occurrences or 0,
                    driving_canceled_license=driving_canceled_license or 0,
                ))
            
            InspectionHistoricalTerritorialStatistic.objects.bulk_create(batch)
            self.stdout.write(self.style.SUCCESS("Importacao territorial historica concluida."))

        finally:
            conn.close()
