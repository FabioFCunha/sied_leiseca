from collections import defaultdict
from datetime import date

from apps.inspection.models import (
    HISTORICAL_CUTOFF_DATE,
    INSPECTION_STATISTICS_CUTOFF_DATE,
    InspectionHistoricalTerritorialStatistic,
    InspectionMunicipality,
    InspectionReport,
    InspectionReportOperation,
)
from apps.inspection.territorial import (
    normalize_municipality_name,
    resolve_territory,
)


class InspectionTerritorialStatisticsService:
    """
    Estatistica territorial da Fiscalizacao.

    Camada independente da Estatistica Oficial.

    Fonte territorial historica:
    InspectionHistoricalTerritorialStatistic
    de 2022-10-03 ate 2026-08-09.

    Fonte territorial operacional:
    InspectionReportOperation.city
    a partir de 2026-08-10.
    """

    METROPOLITAN_REGION_CODE = "METROPOLITANA"
    HISTORICAL_TERRITORIAL_FROM = date(2022, 10, 3)
    HISTORICAL_TERRITORIAL_TO = HISTORICAL_CUTOFF_DATE
    TERRITORIAL_AREA_ALL = "all"
    TERRITORIAL_AREA_METROPOLITAN = "metropolitan"
    TERRITORIAL_AREA_INTERIOR = "interior"
    RAIN_STRUCTURED_CLASSIFICATION_FROM = date(
        2026,
        8,
        17,
    )

    def __init__(self, filters=None):
        self.filters = filters or {}

        self.date_from = self._parse_date(
            self.filters.get("date_from")
        )
        self.date_to = self._parse_date(
            self.filters.get("date_to")
        )

        self.team = (
            str(self.filters.get("team") or "").strip()
            or None
        )
        self.region = (
            str(self.filters.get("region") or "").strip()
            or None
        )
        self.municipality = (
            str(
                self.filters.get("municipality") or ""
            ).strip()
            or None
        )
        self.territorial_area = (
            self._normalize_territorial_area(
                self.filters.get(
                    "territorial_area"
                )
            )
        )

    @staticmethod
    def _parse_date(value):
        if not value:
            return None

        if isinstance(value, date):
            return value

        return date.fromisoformat(str(value))

    @staticmethod
    def _number(value):
        return value or 0

    @classmethod
    def _normalize_territorial_area(
        cls,
        value,
    ):
        normalized = str(
            value or cls.TERRITORIAL_AREA_ALL
        ).strip().lower()

        if normalized not in {
            cls.TERRITORIAL_AREA_ALL,
            cls.TERRITORIAL_AREA_METROPOLITAN,
            cls.TERRITORIAL_AREA_INTERIOR,
        }:
            return cls.TERRITORIAL_AREA_ALL

        return normalized

    @classmethod
    def _territorial_group_for_region_code(
        cls,
        region_code,
    ):
        return (
            cls.TERRITORIAL_AREA_METROPOLITAN
            if region_code
            == cls.METROPOLITAN_REGION_CODE
            else cls.TERRITORIAL_AREA_INTERIOR
        )

    @staticmethod
    def _empty_metrics():
        return {
            "operations": 0,
            "approach": 0,
            "reconductor": 0,
            "refusal": 0,
            "thirtythree_ml": 0,
            "thirtyfour_ml": 0,
            "arrests_means_evidence": 0,
            "alcohol_cases": 0,
            "alcohol_percentage": None,
            "fined": 0,
            "towed": 0,
            "cnh_collected": 0,
            "removal_resolutions": 0,
            "art307": 0,
            "criminal_occurrences": 0,
            "driving_canceled_license": 0,
        }

    @classmethod
    def _build_metrics(
        cls,
        *,
        operations,
        approach,
        reconductor=0,
        refusal=0,
        thirtythree_ml=0,
        thirtyfour_ml=0,
        arrests_means_evidence=0,
        fined=0,
        towed=0,
        cnh_collected=0,
        removal_resolutions=0,
        art307=0,
        criminal_occurrences=0,
        driving_canceled_license=0,
    ):
        alcohol_cases = (
            refusal
            + thirtythree_ml
            + thirtyfour_ml
            + arrests_means_evidence
        )
        alcohol_percentage = (
            alcohol_cases / approach * 100
            if approach > 0
            else None
        )

        return {
            "operations": operations,
            "approach": approach,
            "reconductor": reconductor,
            "refusal": refusal,
            "thirtythree_ml": thirtythree_ml,
            "thirtyfour_ml": thirtyfour_ml,
            "arrests_means_evidence": (
                arrests_means_evidence
            ),
            "alcohol_cases": alcohol_cases,
            "alcohol_percentage": (
                alcohol_percentage
            ),
            "fined": fined,
            "towed": towed,
            "cnh_collected": cnh_collected,
            "removal_resolutions": (
                removal_resolutions
            ),
            "art307": art307,
            "criminal_occurrences": (
                criminal_occurrences
            ),
            "driving_canceled_license": (
                driving_canceled_license
            ),
        }

    @classmethod
    def _operation_metrics(cls, operation):
        return cls._build_metrics(
            operations=1,
            approach=cls._number(
                operation.approach
            ),
            reconductor=cls._number(
                operation.reconductor
            ),
            refusal=cls._number(
                operation.refusal
            ),
            thirtythree_ml=cls._number(
                operation.thirtythree_ml
            ),
            thirtyfour_ml=cls._number(
                operation.thirtyfour_ml
            ),
            arrests_means_evidence=cls._number(
                operation.arrests_means_evidence
            ),
            fined=cls._number(
                operation.fined
            ),
            towed=cls._number(
                operation.towed
            ),
            cnh_collected=cls._number(
                operation.cnh_collected
            ),
            removal_resolutions=cls._number(
                operation.removal_resolutions
            ),
            art307=cls._number(
                operation.art307
            ),
            criminal_occurrences=cls._number(
                operation.criminal_occurrences
            ),
            driving_canceled_license=cls._number(
                operation.driving_canceled_license
            ),
        )

    @classmethod
    def _historical_metrics(cls, row):
        return cls._build_metrics(
            operations=cls._number(
                row.operations_count
            ),
            approach=cls._number(
                row.approach
            ),
            reconductor=cls._number(
                row.reconductor
            ),
            refusal=cls._number(
                row.refusal
            ),
            thirtythree_ml=cls._number(
                row.thirtythree_ml
            ),
            thirtyfour_ml=cls._number(
                row.thirtyfour_ml
            ),
            arrests_means_evidence=cls._number(
                row.arrests_means_evidence
            ),
            fined=cls._number(
                row.fined
            ),
            towed=cls._number(
                row.towed
            ),
            cnh_collected=cls._number(
                row.cnh_collected
            ),
            removal_resolutions=cls._number(
                row.removal_resolutions
            ),
            art307=cls._number(
                row.art307
            ),
            criminal_occurrences=cls._number(
                row.criminal_occurrences
            ),
            driving_canceled_license=cls._number(
                row.driving_canceled_license
            ),
        )

    @classmethod
    def _add_metrics(cls, target, source):
        fields = (
            "operations",
            "approach",
            "reconductor",
            "refusal",
            "thirtythree_ml",
            "thirtyfour_ml",
            "arrests_means_evidence",
            "alcohol_cases",
            "fined",
            "towed",
            "cnh_collected",
            "removal_resolutions",
            "art307",
            "criminal_occurrences",
            "driving_canceled_license",
        )

        for field in fields:
            target[field] += (
                source.get(field) or 0
            )

        target["alcohol_percentage"] = (
            target["alcohol_cases"]
            / target["approach"]
            * 100
            if target["approach"] > 0
            else None
        )

    def _effective_historical_range(self):
        start = max(
            self.date_from or self.HISTORICAL_TERRITORIAL_FROM,
            self.HISTORICAL_TERRITORIAL_FROM,
        )
        end = min(
            self.date_to or self.HISTORICAL_TERRITORIAL_TO,
            self.HISTORICAL_TERRITORIAL_TO,
        )

        if start > end:
            return None, None

        return start, end

    def _effective_operational_range(self):
        start = max(
            self.date_from or INSPECTION_STATISTICS_CUTOFF_DATE,
            INSPECTION_STATISTICS_CUTOFF_DATE,
        )
        end = self.date_to

        if end and start > end:
            return None, None

        return start, end

    def _get_historical_queryset(self):
        start, end = (
            self._effective_historical_range()
        )

        if not start:
            return (
                InspectionHistoricalTerritorialStatistic
                .objects.none()
            )

        queryset = (
            InspectionHistoricalTerritorialStatistic
            .objects
            .select_related(
                "municipality",
                "region",
            )
            .filter(
                reference_date__gte=start,
                reference_date__lte=end,
            )
            .order_by(
                "reference_date",
                "id",
            )
        )

        if self.team:
            queryset = queryset.filter(
                team__iexact=self.team
            )

        return queryset

    def _get_operational_queryset(self):
        start, end = (
            self._effective_operational_range()
        )

        if not start:
            return (
                InspectionReportOperation.objects.none()
            )

        queryset = (
            InspectionReportOperation.objects
            .select_related("report")
            .filter(
                report__operation_date__gte=start,
                report__statistics_status=(
                    InspectionReport
                    .StatisticsStatus
                    .INCLUDED
                ),
            )
            .order_by(
                "report__operation_date",
                "id",
            )
        )

        if end:
            queryset = queryset.filter(
                report__operation_date__lte=end
            )

        if self.team:
            queryset = queryset.filter(
                report__team__iexact=self.team
            )

        return queryset

    def _historical_territory(self, row):
        municipality_name = (
            row.municipality.name
            if row.municipality_id
            else None
        )
        normalized_city = (
            row.municipality.normalized_name
            if row.municipality_id
            else (
                row.normalized_city
                or normalize_municipality_name(
                    row.source_city
                )
            )
        )

        return {
            "matched": bool(
                row.region_id
                and row.municipality_id
            ),
            "region_id": row.region_id,
            "region_code": (
                row.region.code
                if row.region_id
                else None
            ),
            "region": (
                row.region.name
                if row.region_id
                else None
            ),
            "municipality_id": (
                row.municipality_id
            ),
            "municipality": municipality_name,
            "normalized_city": normalized_city,
        }

    def _matches_territorial_filters(
        self,
        territory,
        *,
        include_municipality=True,
    ):
        if not territory["matched"]:
            return (
                self.territorial_area
                == self.TERRITORIAL_AREA_ALL
                and
                self.region is None
                and (
                    self.municipality is None
                    or not include_municipality
                )
            )

        territorial_group = (
            self._territorial_group_for_region_code(
                territory["region_code"]
            )
        )

        if (
            self.territorial_area
            != self.TERRITORIAL_AREA_ALL
            and territorial_group
            != self.territorial_area
        ):
            return False

        if self.region:
            region_filter = (
                self.region.strip().upper()
            )

            if (
                territory["region_code"].upper()
                != region_filter
                and territory["region"].upper()
                != region_filter
            ):
                return False

        if (
            include_municipality
            and self.municipality
        ):
            municipality_filter = (
                normalize_municipality_name(
                    self.municipality
                )
            )

            if (
                territory["normalized_city"]
                != municipality_filter
            ):
                return False

        return True

    @staticmethod
    def _serialize_region_rows(regions):
        region_rows = []

        for region_item in regions.values():
            municipality_rows = list(
                region_item[
                    "municipalities"
                ].values()
            )

            for municipality_item in municipality_rows:
                municipality_item.pop(
                    "_rain_report_ids",
                    None,
                )
                municipality_item["dates"] = sorted(
                    municipality_item["dates"]
                )

            municipality_rows.sort(
                key=lambda item: (
                    item["municipality"]
                )
            )

            region_item[
                "municipalities"
            ] = municipality_rows
            region_rows.append(region_item)

        return region_rows

    def _build_sources_used(
        self,
        historical_queryset,
        operational_queryset,
    ):
        sources_used = []

        if historical_queryset.exists():
            sources_used.append("historical")

        if operational_queryset.exists():
            sources_used.append("operational")

        return sources_used

    def _build_meta(
        self,
        *,
        sources_used,
    ):
        return {
            "source": "unified",
            "sources_used": sources_used,
            "territorial_source": (
                "InspectionHistoricalTerritorialStatistic + "
                "InspectionReportOperation.city"
            ),
            "historical_from": (
                self.HISTORICAL_TERRITORIAL_FROM
                .isoformat()
            ),
            "historical_to": (
                self.HISTORICAL_TERRITORIAL_TO
                .isoformat()
            ),
            "operational_from": (
                INSPECTION_STATISTICS_CUTOFF_DATE
                .isoformat()
            ),
            "territorial_coverage_from": (
                self.HISTORICAL_TERRITORIAL_FROM
                .isoformat()
            ),
            "highlighted_operations_source": (
                "operational_only"
            ),
            "historical_highlighted_supported": False,
            "date_from": (
                self.date_from.isoformat()
                if self.date_from
                else None
            ),
            "date_to": (
                self.date_to.isoformat()
                if self.date_to
                else None
            ),
            "team": self.team,
            "territorial_area": (
                self.territorial_area
            ),
            "region": self.region,
            "municipality": (
                self.municipality
            ),
        }

    def _aggregate_data(
        self,
        *,
        include_municipality_filter=True,
    ):
        historical_queryset = (
            self._get_historical_queryset()
        )
        operational_queryset = (
            self._get_operational_queryset()
        )

        sources_used = self._build_sources_used(
            historical_queryset,
            operational_queryset,
        )

        regions = {}
        unclassified = defaultdict(
            lambda: {
                "source_city": "",
                "normalized_city": "",
                "operations": 0,
                "approach": 0,
            }
        )

        total = self._empty_metrics()
        metropolitan_total = (
            self._empty_metrics()
        )
        interior_total = (
            self._empty_metrics()
        )

        classified_operations = 0
        unclassified_operations = 0
        highlighted_operations = []

        for row in historical_queryset:
            territory = self._historical_territory(
                row
            )

            if not self._matches_territorial_filters(
                territory,
                include_municipality=(
                    include_municipality_filter
                ),
            ):
                continue

            metrics = self._historical_metrics(
                row
            )

            self._add_metrics(total, metrics)

            if not territory["matched"]:
                unclassified_operations += (
                    metrics["operations"]
                )
                self._accumulate_unclassified(
                    unclassified=unclassified,
                    source_city=row.source_city,
                    normalized_city=(
                        row.normalized_city
                    ),
                    metrics=metrics,
                )
                continue

            classified_operations += (
                metrics["operations"]
            )
            self._accumulate_classified(
                territory=territory,
                metrics=metrics,
                reference_date=(
                    row.reference_date
                ),
                rain_count=self._number(
                    row.rain
                ),
                rain_report_id=None,
                regions=regions,
                metropolitan_total=(
                    metropolitan_total
                ),
                interior_total=(
                    interior_total
                ),
            )

        for operation in operational_queryset:
            territory = resolve_territory(
                operation.city
            )

            if not self._matches_territorial_filters(
                territory,
                include_municipality=(
                    include_municipality_filter
                ),
            ):
                continue

            metrics = self._operation_metrics(
                operation
            )

            self._add_metrics(total, metrics)

            if not territory["matched"]:
                unclassified_operations += 1
                self._accumulate_unclassified(
                    unclassified=unclassified,
                    source_city=operation.city,
                    normalized_city=(
                        territory[
                            "normalized_city"
                        ]
                    ),
                    metrics=metrics,
                )
                continue

            classified_operations += 1
            self._accumulate_classified(
                territory=territory,
                metrics=metrics,
                reference_date=(
                    operation.report
                    .operation_date
                ),
                rain_count=(
                    1
                    if self._operation_has_rain(
                        operation
                    )
                    else 0
                ),
                rain_report_id=(
                    operation.report_id
                ),
                regions=regions,
                metropolitan_total=(
                    metropolitan_total
                ),
                interior_total=(
                    interior_total
                ),
            )

            if (
                metrics["alcohol_percentage"]
                is not None
                and metrics[
                    "alcohol_percentage"
                ] >= 25
            ):
                highlighted_operations.append(
                    self._build_highlighted_operation(
                        operation,
                        territory,
                        metrics,
                    )
                )

        region_rows = self._serialize_region_rows(
            regions
        )
        region_rows.sort(
            key=lambda item: (
                0
                if item["region_code"]
                == self.METROPOLITAN_REGION_CODE
                else 1,
                item["region"],
            )
        )

        highlighted_operations.sort(
            key=lambda item: (
                -item[
                    "alcohol_percentage"
                ],
                item["date"],
                item["municipality"],
            )
        )

        unclassified_rows = list(
            unclassified.values()
        )
        unclassified_rows.sort(
            key=lambda item: (
                item["source_city"]
            )
        )

        return {
            "meta": self._build_meta(
                sources_used=sources_used
            ),
            "summary": {
                "operations": (
                    total["operations"]
                ),
                "classified_operations": (
                    classified_operations
                ),
                "unclassified_operations": (
                    unclassified_operations
                ),
                "approach": (
                    total["approach"]
                ),
                "reconductor": (
                    total["reconductor"]
                ),
                "refusal": (
                    total["refusal"]
                ),
                "administrative_art_165": (
                    total["thirtythree_ml"]
                ),
                "criminal_art_306": (
                    total["thirtyfour_ml"]
                ),
                "criminal_art_306_other_evidence": (
                    total[
                        "arrests_means_evidence"
                    ]
                ),
                "alcohol_cases": (
                    total["alcohol_cases"]
                ),
                "alcohol_percentage": (
                    total[
                        "alcohol_percentage"
                    ]
                ),
                "fined": (
                    total["fined"]
                ),
                "towed": (
                    total["towed"]
                ),
                "cnh_collected": (
                    total[
                        "cnh_collected"
                    ]
                ),
                "art307": (
                    total["art307"]
                ),
                "criminal_occurrences": (
                    total[
                        "criminal_occurrences"
                    ]
                ),
                "driving_canceled_license": (
                    total[
                        "driving_canceled_license"
                    ]
                ),
            },
            "metropolitan": (
                metropolitan_total
            ),
            "interior": (
                interior_total
            ),
            "regions": region_rows,
            "highlighted_operations": (
                highlighted_operations
            ),
            "unclassified": (
                unclassified_rows
            ),
        }

    def _ensure_region(
        self,
        regions,
        territory,
    ):
        region_code = territory["region_code"]

        if region_code not in regions:
            regions[region_code] = {
                "region_id": (
                    territory["region_id"]
                ),
                "region_code": region_code,
                "region": territory["region"],
                "territorial_group": (
                    self._territorial_group_for_region_code(
                        region_code
                    ).upper()
                ),
                "metrics": (
                    self._empty_metrics()
                ),
                "municipalities": {},
            }

        return regions[region_code]

    def _ensure_municipality(
        self,
        region_item,
        territory,
    ):
        municipality_key = (
            territory["normalized_city"]
        )

        municipalities = region_item[
            "municipalities"
        ]

        if municipality_key not in municipalities:
            municipalities[municipality_key] = {
                "municipality_id": (
                    territory[
                        "municipality_id"
                    ]
                ),
                "municipality": (
                    territory[
                        "municipality"
                    ]
                ),
                "normalized_name": (
                    municipality_key
                ),
                "rain": 0,
                "_rain_report_ids": set(),
                "dates": set(),
                "metrics": (
                    self._empty_metrics()
                ),
            }

        return municipalities[municipality_key]

    def _accumulate_classified(
        self,
        *,
        territory,
        metrics,
        reference_date,
        rain_count,
        rain_report_id,
        regions,
        metropolitan_total,
        interior_total,
    ):
        region_item = self._ensure_region(
            regions,
            territory,
        )

        self._add_metrics(
            region_item["metrics"],
            metrics,
        )

        municipality_item = (
            self._ensure_municipality(
                region_item,
                territory,
            )
        )
        municipality_item["dates"].add(
            reference_date.isoformat()
        )
        self._accumulate_municipality_rain(
            municipality_item,
            rain_count=rain_count,
            rain_report_id=rain_report_id,
        )

        self._add_metrics(
            municipality_item["metrics"],
            metrics,
        )

        if (
            territory["region_code"]
            == self.METROPOLITAN_REGION_CODE
        ):
            self._add_metrics(
                metropolitan_total,
                metrics,
            )
        else:
            self._add_metrics(
                interior_total,
                metrics,
            )

    @staticmethod
    def _accumulate_municipality_rain(
        municipality_item,
        *,
        rain_count,
        rain_report_id,
    ):
        if rain_report_id is not None:
            if (
                rain_count > 0
                and rain_report_id
                not in municipality_item[
                    "_rain_report_ids"
                ]
            ):
                municipality_item["rain"] += 1
                municipality_item[
                    "_rain_report_ids"
                ].add(rain_report_id)
            return

        municipality_item["rain"] += (
            rain_count or 0
        )

    def _operation_has_rain(self, operation):
        report = operation.report
        classification = (
            report.statistics_classification
            or {}
        )

        if (
            report.operation_date
            < self
            .RAIN_STRUCTURED_CLASSIFICATION_FROM
        ):
            observation = str(
                report.changes_general or ""
            ).lower()
            return (
                "chuv" in observation
                or "chove" in observation
            )

        return (
            classification.get("rain")
            is True
        )

    def _accumulate_unclassified(
        self,
        *,
        unclassified,
        source_city,
        normalized_city,
        metrics,
    ):
        key = normalized_city or "__EMPTY__"
        item = unclassified[key]

        item["source_city"] = source_city or ""
        item["normalized_city"] = (
            normalized_city or ""
        )
        item["operations"] += (
            metrics["operations"]
        )
        item["approach"] += (
            metrics["approach"]
        )

    def _build_highlighted_operation(
        self,
        operation,
        territory,
        metrics,
    ):
        return {
            "operation_id": operation.id,
            "report_id": operation.report_id,
            "date": (
                operation.report
                .operation_date
                .isoformat()
            ),
            "team": operation.report.team,
            "source_city": operation.city,
            "municipality": (
                territory["municipality"]
            ),
            "region": territory["region"],
            "region_code": (
                territory["region_code"]
            ),
            "territorial_group": (
                self._territorial_group_for_region_code(
                    territory["region_code"]
                ).upper()
            ),
            "approach": metrics["approach"],
            "alcohol_cases": (
                metrics["alcohol_cases"]
            ),
            "alcohol_percentage": round(
                metrics["alcohol_percentage"],
                2,
            ),
        }

    def get_data(self):
        return self._aggregate_data()


class InspectionTerritorialRankingService(
    InspectionTerritorialStatisticsService
):
    FIXED_INDICATOR_KEYS = (
        "operations",
        "approach",
        "alcohol_cases",
        "alcohol_percentage",
    )
    ADDITIONAL_INDICATOR_DEFINITIONS = {
        "fined": {
            "label": "Multados",
            "value_key": "fined",
        },
        "cnh_collected": {
            "label": "CNH recolhidas",
            "value_key": "cnh_collected",
        },
        "towed": {
            "label": "Veículos rebocados",
            "value_key": "towed",
        },
        "refusal": {
            "label": "Recusas",
            "value_key": "refusal",
        },
        "reconductor": {
            "label": "Reconduções",
            "value_key": "reconductor",
        },
        "removal_resolutions": {
            "label": "Resoluções de remoção",
            "value_key": "removal_resolutions",
        },
        "criminal_occurrences": {
            "label": "Ocorrências criminais",
            "value_key": "criminal_occurrences",
        },
        "arrests_means_evidence": {
            "label": "Prisões / meios de prova",
            "value_key": "arrests_means_evidence",
        },
        "fined_per_100_approaches": {
            "label": "Multados por 100 abordagens",
            "value_key": "fined_per_100_approaches",
        },
        "art307": {
            "label": "Art. 307",
            "value_key": "art307",
        },
    }
    FIXED_INDICATOR_DEFINITIONS = {
        "operations": {
            "label": "Ações",
        },
        "approach": {
            "label": "Abordados",
        },
        "alcohol_cases": {
            "label": "Alcoolemia",
        },
        "alcohol_percentage": {
            "label": "% Alcoolemia",
        },
    }
    DEFAULT_LIMIT = 10
    MIN_LIMIT = 1
    MAX_LIMIT = 50

    def __init__(self, filters=None):
        super().__init__(filters=filters)

        requested_limit = self.filters.get("limit")
        self.limit = self._normalize_limit(
            requested_limit
        )
        self.selected_indicators = (
            self._normalize_selected_indicators(
                self.filters.get("indicators"),
                self.filters.get("indicator"),
            )
        )

    @classmethod
    def _normalize_limit(cls, value):
        try:
            normalized = int(value)
        except (
            TypeError,
            ValueError,
        ):
            normalized = cls.DEFAULT_LIMIT

        return max(
            cls.MIN_LIMIT,
            min(cls.MAX_LIMIT, normalized),
        )

    @classmethod
    def _normalize_selected_indicators(
        cls,
        indicators,
        legacy_indicator=None,
    ):
        values = []

        if isinstance(indicators, str):
            values.extend(
                item.strip()
                for item in indicators.split(",")
                if item.strip()
            )
        elif indicators:
            for item in indicators:
                item = str(item).strip()
                if not item:
                    continue

                values.extend(
                    piece.strip()
                    for piece in item.split(",")
                    if piece.strip()
                )

        if legacy_indicator:
            legacy_value = str(
                legacy_indicator
            ).strip()
            if legacy_value:
                values.append(legacy_value)

        normalized = []
        seen = set()

        for item in values:
            if (
                item in cls.FIXED_INDICATOR_KEYS
                or item
                not in cls.ADDITIONAL_INDICATOR_DEFINITIONS
                or item in seen
            ):
                continue

            seen.add(item)
            normalized.append(item)

        return normalized

    @staticmethod
    def _safe_rate(
        numerator,
        denominator,
    ):
        if not denominator:
            return 0.0

        return numerator / denominator * 100

    def _build_ranking_row(
        self,
        municipality_item,
    ):
        metrics = municipality_item["metrics"]
        alcohol_percentage = self._safe_rate(
            metrics["alcohol_cases"],
            metrics["approach"],
        )
        fined_per_100 = self._safe_rate(
            metrics["fined"],
            metrics["approach"],
        )

        return {
            "municipality_id": (
                municipality_item[
                    "municipality_id"
                ]
            ),
            "municipality": (
                municipality_item[
                    "municipality"
                ]
            ),
            "normalized_name": (
                municipality_item[
                    "normalized_name"
                ]
            ),
            "region": municipality_item[
                "region"
            ],
            "region_code": municipality_item[
                "region_code"
            ],
            "operations": metrics["operations"],
            "approach": metrics["approach"],
            "alcohol_cases": (
                metrics["alcohol_cases"]
            ),
            "fined": metrics["fined"],
            "cnh_collected": (
                metrics["cnh_collected"]
            ),
            "towed": metrics["towed"],
            "refusal": metrics["refusal"],
            "reconductor": (
                metrics["reconductor"]
            ),
            "removal_resolutions": (
                metrics[
                    "removal_resolutions"
                ]
            ),
            "criminal_occurrences": (
                metrics[
                    "criminal_occurrences"
                ]
            ),
            "arrests_means_evidence": (
                metrics[
                    "arrests_means_evidence"
                ]
            ),
            "alcohol_percentage": (
                alcohol_percentage
            ),
            "fined_per_100_approaches": (
                fined_per_100
            ),
            "art307": metrics["art307"],
            "rain": municipality_item["rain"],
        }

    def _flatten_rankable_municipalities(
        self,
        aggregated,
    ):
        rows = []

        for region_item in aggregated["regions"]:
            for municipality_item in region_item[
                "municipalities"
            ]:
                rows.append(
                    {
                        **municipality_item,
                        "region": region_item[
                            "region"
                        ],
                        "region_code": (
                            region_item[
                                "region_code"
                            ]
                        ),
                    }
                )

        return rows

    @classmethod
    def _matches_area_group(
        cls,
        territorial_group,
        territorial_area,
    ):
        return (
            territorial_area
            == cls.TERRITORIAL_AREA_ALL
            or territorial_group
            == territorial_area
        )

    def _official_territorial_options(self):
        queryset = (
            InspectionMunicipality.objects
            .select_related("region")
            .filter(
                is_active=True,
                region__is_active=True,
            )
            .order_by(
                "name"
            )
        )
        municipalities = []
        regions = []
        seen_ids = set()
        seen_region_codes = set()

        for municipality in queryset:
            territorial_group = (
                self._territorial_group_for_region_code(
                    municipality.region.code
                )
            )

            if municipality.id in seen_ids:
                continue

            seen_ids.add(
                municipality.id
            )

            if (
                municipality.region.code
                not in seen_region_codes
            ):
                seen_region_codes.add(
                    municipality.region.code
                )
                regions.append(
                    {
                        "region_id": (
                            municipality.region.id
                        ),
                        "region": (
                            municipality.region.name
                        ),
                        "region_code": (
                            municipality.region.code
                        ),
                        "territorial_group": (
                            territorial_group
                        ),
                    }
                )

            municipalities.append(
                {
                    "municipality_id": (
                        municipality.id
                    ),
                    "municipality": (
                        municipality.name
                    ),
                    "region": (
                        municipality.region.name
                    ),
                    "region_code": (
                        municipality.region.code
                    ),
                    "territorial_group": (
                        territorial_group
                    ),
                }
            )

        regions.sort(
            key=lambda item: (
                0
                if item["region_code"]
                == self.METROPOLITAN_REGION_CODE
                else 1,
                item["region"],
            )
        )

        return {
            "regions": regions,
            "municipalities": municipalities,
        }

    def get_data(self):
        aggregated = self._aggregate_data(
            include_municipality_filter=False
        )
        base_rows = (
            self._flatten_rankable_municipalities(
                aggregated
            )
        )
        ranking_rows = [
            self._build_ranking_row(item)
            for item in base_rows
        ]

        ranking_rows.sort(
            key=lambda item: (
                -item["alcohol_percentage"],
                -item["alcohol_cases"],
                -item["approach"],
                item["municipality"],
            )
        )

        total_municipalities = len(
            ranking_rows
        )

        for position, item in enumerate(
            ranking_rows,
            start=1,
        ):
            item["position"] = position
            item[
                "total_municipalities"
            ] = total_municipalities
            item.pop(
                "normalized_name",
                None,
            )

        if self.municipality:
            municipality_filter = (
                normalize_municipality_name(
                    self.municipality
                )
            )
            ranking = [
                item
                for item in ranking_rows
                if normalize_municipality_name(
                    item["municipality"]
                )
                == municipality_filter
            ][:1]
        else:
            ranking = ranking_rows[
                : self.limit
            ]
        official_options = (
            self._official_territorial_options()
        )

        return {
            "summary": {
                "municipalities_considered": (
                    total_municipalities
                ),
            },
            "ranking": ranking,
            "meta": {
                **aggregated["meta"],
                "ranking_criterion": (
                    "alcohol_percentage"
                ),
                "ranking_criterion_label": (
                    "% Alcoolemia"
                ),
                "limit": self.limit,
                "selected_indicators": (
                    self.selected_indicators
                ),
                "fixed_indicators": list(
                    self.FIXED_INDICATOR_KEYS
                ),
                "available_regions": (
                    official_options["regions"]
                ),
                "available_municipalities": (
                    official_options[
                        "municipalities"
                    ]
                ),
            },
        }
