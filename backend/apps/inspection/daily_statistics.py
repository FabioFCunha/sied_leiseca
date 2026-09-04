from calendar import monthrange
from datetime import date

from django.db.models import Max

from apps.inspection.models import InspectionStatistic
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
        approach = cls._number(summary.get("approach"))
        refusal = cls._number(summary.get("refusal"))
        administrative = cls._number(alcohol.get("thirtythree_ml"))
        criminal = cls._number(alcohol.get("thirtyfour_ml"))
        total_alcohol = refusal + administrative + criminal

        return {
            "operations": cls._number(summary.get("operations")),
            "approach": approach,
            "fined": cls._number(summary.get("fined")),
            "refusal": refusal,
            "administrative_alcohol": administrative,
            "criminal_alcohol": criminal,
            "total_alcohol": total_alcohol,
            "alcohol_percentage": (
                total_alcohol / approach * 100 if approach > 0 else None
            ),
            "towed": cls._number(summary.get("towed")),
        }

    @staticmethod
    def _operation_days(dashboard):
        return len(
            {
                row.get("operation_date")
                for row in dashboard.get("time_series") or []
                if row.get("operation_date") and (row.get("operations") or 0) > 0
            }
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
        current_days = self._operation_days(current_dashboard)
        previous_days = self._operation_days(previous_dashboard)

        return {
            "daily": {
                "date": selected_date.isoformat(),
                "metrics": self._metrics(daily_dashboard),
                "teams": daily_dashboard.get("team_production") or [],
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
