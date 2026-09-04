from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Max, Q

from apps.inspection.major_occurrence import report_major_occurrence_analysis
from apps.inspection.models import (
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalStatistic,
    InspectionStatistic,
)
from apps.inspection.services import InspectionStatisticsUnifiedService


class InspectionDailyReportService:
    """Relatorio diario e comparativo anual da Fiscalizacao."""

    METRIC_DEFINITIONS = (
        ("operations", "Ações realizadas"),
        ("approach", "Motoristas abordados"),
        ("fined", "Motoristas multados"),
        ("refusal", "Recusas ao teste"),
        ("administrative_alcohol", "Alcoolemia administrativa"),
        ("criminal_alcohol", "Flagrantes de alcoolemia"),
        ("total_alcohol", "Total de alcoolemia"),
        ("alcohol_percentage", "Percentual total de alcoolemia"),
        ("towed", "Veículos removidos"),
    )
    RAIN_STRUCTURED_CLASSIFICATION_FROM = date(2026, 8, 17)

    def __init__(self, selected_date=None):
        self.requested_date = self._parse_date(selected_date)

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
    def _matching_previous_date(value):
        day = min(value.day, monthrange(value.year - 1, value.month)[1])
        return value.replace(year=value.year - 1, day=day)

    @staticmethod
    def _dashboard(date_from, date_to):
        return InspectionStatisticsUnifiedService(
            {
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "team": None,
                "region": None,
            }
        ).get_dashboard_data()

    @classmethod
    def _metrics(cls, dashboard):
        summary = dashboard.get("summary") or {}
        alcohol = dashboard.get("alcohol_results") or {}
        occurrences = dashboard.get("occurrences") or {}
        approach = cls._number(summary.get("approach"))
        refusal = cls._number(summary.get("refusal"))
        administrative = cls._number(alcohol.get("thirtythree_ml"))
        criminal = cls._number(alcohol.get("thirtyfour_ml"))
        other_evidence = cls._number(
            occurrences.get("arrests_means_evidence")
        )
        total_alcohol = refusal + administrative + criminal

        return {
            "operations": cls._number(summary.get("operations")),
            "approach": approach,
            "fined": cls._number(summary.get("fined")),
            "refusal": refusal,
            "administrative_alcohol": administrative,
            "criminal_alcohol": criminal,
            "other_evidence": other_evidence,
            "total_alcohol": total_alcohol,
            "alcohol_percentage": (
                total_alcohol / approach * 100 if approach > 0 else None
            ),
            "towed": cls._number(summary.get("towed")),
        }

    @staticmethod
    def _operation_days(date_from, date_to):
        historical_dates = set(
            InspectionHistoricalStatistic.objects.filter(
                reference_date__range=(date_from, date_to),
                source_type=HistoricalSourceType.DAILY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_C,
                is_validation_only=False,
            )
            .filter(Q(operations_count__gt=0) | Q(historical_operations__gt=0))
            .values_list("reference_date", flat=True)
            .distinct()
        )
        last_historical_date = max(historical_dates, default=None)
        operational_from = (
            max(date_from, last_historical_date + timedelta(days=1))
            if last_historical_date
            else date_from
        )
        operational_dates = set()
        if operational_from <= date_to:
            operational_dates = set(
                InspectionStatistic.objects.filter(
                    operation_date__range=(operational_from, date_to),
                    operations_count__gt=0,
                )
                .values_list("operation_date", flat=True)
                .distinct()
            )
        return len(historical_dates | operational_dates)

    @classmethod
    def _has_rain(cls, report):
        classification = report.statistics_classification or {}
        if report.operation_date < cls.RAIN_STRUCTURED_CLASSIFICATION_FROM:
            observation = str(report.changes_general or "").lower()
            return "chuv" in observation or "chove" in observation
        return classification.get("rain") is True

    @staticmethod
    def _major_occurrence_data(report):
        classification = report.statistics_classification or {}
        if "major_occurrence" not in classification:
            analysis = report_major_occurrence_analysis(report)
            if analysis["suspected"]:
                description = "Indícios identificados: " + "; ".join(
                    analysis["reasons"]
                )
                return True, description
            return False, ""
        confirmed = classification.get("major_occurrence") is True
        description = str(
            classification.get("major_occurrence_description") or ""
        ).strip()
        return confirmed, description if confirmed else ""

    @classmethod
    def _operation_detail(cls, operation):
        return {
            "id": operation.id,
            "address": operation.address_operation or operation.street or "",
            "locality": operation.locality or "",
            "city": operation.city or "",
            "district": operation.district or "",
            "cep": operation.cep or "",
            "number": operation.number or "",
            "departure_meeting_point": operation.departure_meeting_point or "",
            "operation_assembly": operation.operation_assembly or "",
            "first_approach": operation.first_approach or "",
            "closing": operation.closing or "",
            "approach": cls._number(operation.approach),
            "fined": cls._number(operation.fined),
            "refusal": cls._number(operation.refusal),
            "administrative_alcohol": cls._number(operation.thirtythree_ml),
            "criminal_alcohol": cls._number(operation.thirtyfour_ml),
            "other_evidence": cls._number(operation.arrests_means_evidence),
            "towed": cls._number(operation.towed),
            "cnh_collected": cls._number(operation.cnh_collected),
            "reconductor": cls._number(operation.reconductor),
            "removal_resolutions": cls._number(operation.removal_resolutions),
            "vehicle_resolutions": operation.vehicle_resolutions or "",
            "administrative_tests": operation.administrative_tests or "",
            "changes_material": operation.changes_material or "",
            "fines": [
                {"article": fine.art or "", "quantity": cls._number(fine.quant)}
                for fine in operation.fines.all()
            ],
        }

    @classmethod
    def _daily_teams(cls, selected_date):
        statistics = (
            InspectionStatistic.objects.filter(operation_date=selected_date)
            .select_related("report")
            .prefetch_related("report__operations__fines")
            .order_by("team", "report_id")
        )
        teams = defaultdict(
            lambda: {
                "team": "",
                "operations": 0,
                "approach": 0,
                "fined": 0,
                "refusal": 0,
                "administrative_alcohol": 0,
                "criminal_alcohol": 0,
                "other_evidence": 0,
                "total_alcohol": 0,
                "towed": 0,
                "rain": False,
                "major_occurrence": False,
                "major_occurrence_descriptions": [],
                "reports": [],
            }
        )
        for statistic in statistics:
            report = statistic.report
            key = statistic.team or "Não informada"
            item = teams[key]
            item["team"] = key
            for field in (
                "operations", "approach", "fined", "refusal", "towed"
            ):
                source = "operations_count" if field == "operations" else field
                item[field] += cls._number(getattr(statistic, source))
            item["administrative_alcohol"] += cls._number(
                statistic.thirtythree_ml
            )
            item["criminal_alcohol"] += cls._number(statistic.thirtyfour_ml)
            item["other_evidence"] += cls._number(
                statistic.arrests_means_evidence
            )
            item["rain"] = item["rain"] or cls._has_rain(report)
            is_major_occurrence, major_description = (
                cls._major_occurrence_data(report)
            )
            item["major_occurrence"] = (
                item["major_occurrence"] or is_major_occurrence
            )
            if is_major_occurrence and major_description:
                item["major_occurrence_descriptions"].append(major_description)
            item["reports"].append(
                {
                    "id": report.id,
                    "civil_chief": report.civil_chief_name or "",
                    "military_chief": report.military_chief_name or "",
                    "civil_staff": report.segov_team_civil or "",
                    "military_staff": report.segov_team_military or "",
                    "support_opm": report.support_opm or "",
                    "support_staff": report.support_pmerj_staff or "",
                    "support_vehicles": report.support_vehicles or "",
                    "cars": report.cars or "",
                    "changes_general": report.changes_general or "",
                    "changes_material": report.changes_material or "",
                    "low_approach_reasons": report.low_approach_reasons or "",
                    "miscellaneous_changes": report.miscellaneous_changes or "",
                    "rain": cls._has_rain(report),
                    "major_occurrence": is_major_occurrence,
                    "major_occurrence_description": major_description,
                    "operations": [
                        cls._operation_detail(operation)
                        for operation in report.operations.all()
                    ],
                }
            )
        result = list(teams.values())
        for item in result:
            item["total_alcohol"] = (
                item["refusal"]
                + item["administrative_alcohol"]
                + item["criminal_alcohol"]
            )
            item["alcohol_percentage"] = (
                item["total_alcohol"] / item["approach"] * 100
                if item["approach"] > 0
                else None
            )
        return sorted(
            result,
            key=lambda item: (-item["approach"], item["team"]),
        )

    @staticmethod
    def _variation(current, previous):
        if previous in (None, 0):
            return None
        return (current - previous) / previous * 100

    @classmethod
    def _comparison_rows(
        cls,
        previous_metrics,
        current_metrics,
        previous_days,
        current_days,
    ):
        rows = []
        for key, label in cls.METRIC_DEFINITIONS:
            previous = previous_metrics.get(key)
            current = current_metrics.get(key)
            is_percentage = key == "alcohol_percentage"
            difference = (
                None
                if previous is None or current is None
                else current - previous
            )

            rows.append(
                {
                    "key": key,
                    "label": label,
                    "previous": previous,
                    "current": current,
                    "difference": difference,
                    "difference_unit": (
                        "percentage_points" if is_percentage else "absolute"
                    ),
                    "variation_percentage": (
                        None
                        if difference is None
                        else cls._variation(current, previous)
                    ),
                    "previous_daily_average": (
                        None
                        if is_percentage or not previous_days or previous is None
                        else previous / previous_days
                    ),
                    "current_daily_average": (
                        None
                        if is_percentage or not current_days or current is None
                        else current / current_days
                    ),
                }
            )
        return rows

    def get_data(self):
        latest_date = InspectionStatistic.objects.aggregate(
            value=Max("operation_date")
        )["value"]

        if latest_date is None:
            return {
                "daily": None,
                "comparison": None,
                "meta": {"has_data": False, "latest_operation_date": None},
            }

        selected_date = self.requested_date or latest_date
        daily_dashboard = self._dashboard(selected_date, selected_date)
        current_from = date(latest_date.year, 1, 1)
        previous_to = self._matching_previous_date(latest_date)
        previous_from = date(previous_to.year, 1, 1)
        current_dashboard = self._dashboard(current_from, latest_date)
        previous_dashboard = self._dashboard(previous_from, previous_to)
        current_metrics = self._metrics(current_dashboard)
        previous_metrics = self._metrics(previous_dashboard)
        current_days = self._operation_days(current_from, latest_date)
        previous_days = self._operation_days(previous_from, previous_to)

        return {
            "daily": {
                "date": selected_date.isoformat(),
                "metrics": self._metrics(daily_dashboard),
                "teams": self._daily_teams(selected_date),
            },
            "comparison": {
                "previous_period": {
                    "date_from": previous_from.isoformat(),
                    "date_to": previous_to.isoformat(),
                    "operation_days": previous_days,
                },
                "current_period": {
                    "date_from": current_from.isoformat(),
                    "date_to": latest_date.isoformat(),
                    "operation_days": current_days,
                },
                "rows": self._comparison_rows(
                    previous_metrics,
                    current_metrics,
                    previous_days,
                    current_days,
                ),
            },
            "meta": {
                "has_data": True,
                "latest_operation_date": latest_date.isoformat(),
                "comparison_ignores_daily_filter": True,
            },
        }
