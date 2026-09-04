from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.inspection.daily_statistics import InspectionDailyReportService


def dashboard(*, operations, approach, fined, refusal, administrative, criminal, towed, days, other_evidence=0):
    return {
        "summary": {
            "operations": operations,
            "approach": approach,
            "fined": fined,
            "refusal": refusal,
            "towed": towed,
        },
        "alcohol_results": {
            "thirtythree_ml": administrative,
            "thirtyfour_ml": criminal,
            "arrests_means_evidence": other_evidence,
        },
        "occurrences": {"arrests_means_evidence": other_evidence},
        "time_series": [
            {"operation_date": f"2026-01-{day:02d}", "operations": 1}
            for day in range(1, days + 1)
        ],
        "team_production": [],
    }


class InspectionDailyReportServiceTests(SimpleTestCase):
    @patch.object(InspectionDailyReportService, "_daily_teams", return_value=[])
    @patch.object(InspectionDailyReportService, "_operation_days", side_effect=[10, 8])
    @patch("apps.inspection.daily_statistics.InspectionStatistic.objects.aggregate")
    @patch.object(InspectionDailyReportService, "_dashboard")
    def test_daily_filter_does_not_change_comparison_periods(
        self, dashboard_mock, aggregate_mock, operation_days_mock, daily_teams_mock
    ):
        aggregate_mock.return_value = {"value": date(2026, 9, 3)}
        dashboard_mock.side_effect = [
            dashboard(operations=2, approach=100, fined=20, refusal=5, administrative=2, criminal=1, towed=3, days=1),
            dashboard(operations=30, approach=1000, fined=200, refusal=50, administrative=20, criminal=10, towed=30, days=10),
            dashboard(operations=20, approach=800, fined=150, refusal=40, administrative=10, criminal=5, towed=20, days=8),
        ]

        result = InspectionDailyReportService("2026-08-15").get_data()

        self.assertEqual(result["daily"]["date"], "2026-08-15")
        self.assertEqual(
            result["comparison"]["current_period"],
            {"date_from": "2026-01-01", "date_to": "2026-09-03", "operation_days": 10},
        )
        self.assertEqual(
            result["comparison"]["previous_period"],
            {"date_from": "2025-01-01", "date_to": "2025-09-03", "operation_days": 8},
        )
        self.assertEqual(
            dashboard_mock.call_args_list[0].args,
            (date(2026, 8, 15), date(2026, 8, 15)),
        )

    def test_total_alcohol_uses_only_agreed_three_categories(self):
        metrics = InspectionDailyReportService._metrics(
            {
                "summary": {"approach": 100, "refusal": 4},
                "alcohol_results": {
                    "thirtythree_ml": 3,
                    "thirtyfour_ml": 2,
                },
                "occurrences": {"arrests_means_evidence": 99},
            }
        )

        self.assertEqual(metrics["total_alcohol"], 9)
        self.assertEqual(metrics["alcohol_percentage"], 9)
        self.assertEqual(metrics["other_evidence"], 99)

    def test_comparison_calculates_difference_variation_and_daily_average(self):
        rows = InspectionDailyReportService._comparison_rows(
            {"operations": 10, "alcohol_percentage": 10},
            {"operations": 15, "alcohol_percentage": 12.5},
            previous_days=5,
            current_days=6,
        )
        operations = next(row for row in rows if row["key"] == "operations")
        alcohol_percentage = next(
            row for row in rows if row["key"] == "alcohol_percentage"
        )

        self.assertEqual(operations["difference"], 5)
        self.assertEqual(operations["variation_percentage"], 50)
        self.assertEqual(operations["previous_daily_average"], 2)
        self.assertEqual(operations["current_daily_average"], 2.5)
        self.assertEqual(alcohol_percentage["difference"], 2.5)
        self.assertEqual(
            alcohol_percentage["difference_unit"], "percentage_points"
        )
        self.assertIsNone(alcohol_percentage["previous_daily_average"])

    def test_previous_period_handles_leap_day(self):
        self.assertEqual(
            InspectionDailyReportService._matching_previous_date(
                date(2024, 2, 29)
            ),
            date(2023, 2, 28),
        )


class InspectionDailyReportEndpointTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create(
            email="daily-report@example.com",
            password="secret123",
            role=user_model.Role.ADMIN,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("inspection-daily-report")

    def test_endpoint_without_statistics_returns_empty_contract(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["meta"]["has_data"])
        self.assertIsNone(response.data["daily"])
        self.assertIsNone(response.data["comparison"])

    def test_endpoint_rejects_invalid_date(self):
        response = self.client.get(self.url, {"date": "03/09/2026"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.data)
