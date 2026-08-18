from collections import defaultdict
from datetime import date

from apps.inspection.models import (
    INSPECTION_STATISTICS_CUTOFF_DATE,
    InspectionReport,
    InspectionReportOperation,
)
from apps.inspection.territorial import (
    normalize_municipality_name,
    resolve_territory,
)


class InspectionTerritorialStatisticsService:
    """
    Estatística territorial da Fiscalização.

    Camada independente da Estatística Oficial.

    Fonte territorial:
    InspectionReportOperation.city

    Somente relatórios homologados entram na estatística.
    """

    METROPOLITAN_REGION_CODE = "METROPOLITANA"

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
    def _operation_metrics(cls, operation):
        approach = cls._number(
            operation.approach
        )

        refusal = cls._number(
            operation.refusal
        )

        thirtythree_ml = cls._number(
            operation.thirtythree_ml
        )

        thirtyfour_ml = cls._number(
            operation.thirtyfour_ml
        )

        arrests_means_evidence = cls._number(
            operation.arrests_means_evidence
        )

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
            "operations": 1,
            "approach": approach,
            "reconductor": cls._number(
                operation.reconductor
            ),
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
            "fined": cls._number(
                operation.fined
            ),
            "towed": cls._number(
                operation.towed
            ),
            "cnh_collected": cls._number(
                operation.cnh_collected
            ),
            "removal_resolutions": cls._number(
                operation.removal_resolutions
            ),
            "art307": cls._number(
                operation.art307
            ),
            "criminal_occurrences": cls._number(
                operation.criminal_occurrences
            ),
            "driving_canceled_license": cls._number(
                operation.driving_canceled_license
            ),
        }

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

    def _get_operations_queryset(self):
        queryset = (
            InspectionReportOperation.objects
            .select_related("report")
            .filter(
                report__operation_date__gte=(
                    INSPECTION_STATISTICS_CUTOFF_DATE
                ),
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

        if self.date_from:
            queryset = queryset.filter(
                report__operation_date__gte=(
                    self.date_from
                )
            )

        if self.date_to:
            queryset = queryset.filter(
                report__operation_date__lte=(
                    self.date_to
                )
            )

        if self.team:
            queryset = queryset.filter(
                report__team__iexact=self.team
            )

        return queryset

    def _matches_territorial_filters(
        self,
        territory,
    ):
        if not territory["matched"]:
            return (
                self.region is None
                and self.municipality is None
            )

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

        if self.municipality:
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

    def get_data(self):
        queryset = self._get_operations_queryset()

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

        for operation in queryset:
            territory = resolve_territory(
                operation.city
            )

            if not self._matches_territorial_filters(
                territory
            ):
                continue

            metrics = self._operation_metrics(
                operation
            )

            self._add_metrics(
                total,
                metrics,
            )

            if not territory["matched"]:
                unclassified_operations += 1

                key = (
                    territory["normalized_city"]
                    or "__EMPTY__"
                )

                item = unclassified[key]

                item["source_city"] = (
                    operation.city or ""
                )
                item["normalized_city"] = (
                    territory["normalized_city"]
                )
                item["operations"] += 1
                item["approach"] += (
                    metrics["approach"]
                )

                continue

            classified_operations += 1

            region_code = territory[
                "region_code"
            ]

            if region_code not in regions:
                regions[region_code] = {
                    "region_id": (
                        territory["region_id"]
                    ),
                    "region_code": region_code,
                    "region": territory[
                        "region"
                    ],
                    "territorial_group": (
                        "METROPOLITANA"
                        if region_code
                        == self.METROPOLITAN_REGION_CODE
                        else "INTERIOR"
                    ),
                    "metrics": (
                        self._empty_metrics()
                    ),
                    "municipalities": {},
                }

            region_item = regions[
                region_code
            ]

            self._add_metrics(
                region_item["metrics"],
                metrics,
            )

            municipality_key = (
                territory["normalized_city"]
            )

            if (
                municipality_key
                not in region_item[
                    "municipalities"
                ]
            ):
                region_item[
                    "municipalities"
                ][municipality_key] = {
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
                    "metrics": (
                        self._empty_metrics()
                    ),
                }

            municipality_item = (
                region_item[
                    "municipalities"
                ][municipality_key]
            )

            self._add_metrics(
                municipality_item["metrics"],
                metrics,
            )

            if (
                region_code
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

            if (
                metrics["alcohol_percentage"]
                is not None
                and metrics[
                    "alcohol_percentage"
                ] >= 25
            ):
                highlighted_operations.append(
                    {
                        "operation_id": (
                            operation.id
                        ),
                        "report_id": (
                            operation.report_id
                        ),
                        "date": (
                            operation.report
                            .operation_date
                            .isoformat()
                        ),
                        "team": (
                            operation.report.team
                        ),
                        "source_city": (
                            operation.city
                        ),
                        "municipality": (
                            territory[
                                "municipality"
                            ]
                        ),
                        "region": (
                            territory["region"]
                        ),
                        "region_code": (
                            territory[
                                "region_code"
                            ]
                        ),
                        "territorial_group": (
                            "METROPOLITANA"
                            if region_code
                            == self.METROPOLITAN_REGION_CODE
                            else "INTERIOR"
                        ),
                        "approach": (
                            metrics["approach"]
                        ),
                        "alcohol_cases": (
                            metrics[
                                "alcohol_cases"
                            ]
                        ),
                        "alcohol_percentage": (
                            round(
                                metrics[
                                    "alcohol_percentage"
                                ],
                                2,
                            )
                        ),
                    }
                )

        region_rows = []

        for region_item in regions.values():
            municipality_rows = list(
                region_item[
                    "municipalities"
                ].values()
            )

            municipality_rows.sort(
                key=lambda item: (
                    item["municipality"]
                )
            )

            region_item[
                "municipalities"
            ] = municipality_rows

            region_rows.append(
                region_item
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
                -item["alcohol_percentage"],
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
            "meta": {
                "source": "operational",
                "territorial_source": (
                    "InspectionReportOperation.city"
                ),
                "operational_from": (
                    INSPECTION_STATISTICS_CUTOFF_DATE
                    .isoformat()
                ),
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
                "region": self.region,
                "municipality": (
                    self.municipality
                ),
            },
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