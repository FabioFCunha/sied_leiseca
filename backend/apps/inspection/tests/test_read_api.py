import uuid
from datetime import date, datetime, timezone

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.inspection.models import InspectionFine, InspectionReport, InspectionReportOperation


class InspectionReadApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="reader@example.com",
            password="secret123",
            role=get_user_model().Role.MANAGER,
        )
        self.list_url = reverse("inspection-reports-list")

    def make_report(
        self,
        *,
        team="A3",
        operation_date=date(2026, 8, 10),
        status_value=InspectionReport.ReportStatus.SYNCED,
        statistics_status=InspectionReport.StatisticsStatus.PENDING,
        created_at=None,
        source_suffix="1",
    ):
        report = InspectionReport.objects.create(
            source_id=uuid.UUID(f"00000000-0000-0000-0000-0000000000{source_suffix.zfill(2)}"),
            source_created_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc),
            synced_at=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
            operation_date=operation_date,
            team=team,
            management_id=None,
            military_chief_source_id=None,
            segov_team_civil="Equipe civil ficticia",
            segov_team_military="Equipe militar ficticia",
            change_ols="Sem alteracoes",
            agent_detran=2,
            number_trailers=0,
            change_support="",
            cars="VTR-01",
            changes_general="Sem alteracoes",
            status=status_value,
            statistics_status=statistics_status,
        )
        if created_at is not None:
            InspectionReport.objects.filter(pk=report.pk).update(created_at=created_at, updated_at=created_at)
            report.refresh_from_db()
        return report

    def make_operation(self, report, *, source_suffix="1", approach=93, refusal=5, fined=44, removal_resolutions=270, four_ml=88, thirtythree_ml=0, thirtyfour_ml=0, towed=0):
        return InspectionReportOperation.objects.create(
            report=report,
            source_id=uuid.UUID(f"10000000-0000-0000-0000-0000000000{source_suffix.zfill(2)}"),
            source_created_at=datetime(2026, 8, 10, 8, 5, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 35, tzinfo=timezone.utc),
            address_operation="Rua Ficticia, 100",
            locality="Vista Alegre",
            another_not_listed="",
            departure_meeting_point="20:00",
            operation_assembly="20:45",
            first_approach="21:40",
            closing="02:00",
            approach=approach,
            reconductor=10,
            refusal=refusal,
            celebrities_authorities=0,
            four_ml=four_ml,
            thirtythree_ml=thirtythree_ml,
            thirtyfour_ml=thirtyfour_ml,
            passive_tests_performed=0,
            changes_material="",
            cnh_collected=0,
            fined=fined,
            towed=towed,
            removal_resolutions=removal_resolutions,
            arrests_means_evidence=0,
            art307=0,
            criminal_occurrences=0,
            driving_canceled_license=1,
            vehicle_resolutions="003 contran",
            administrative_tests="Sem Alteracoes",
            cep="21250-392",
            street="Rua Ficticia",
            city="Rio de Janeiro",
            district="Vista Alegre",
            number="",
        )

    def make_fine(self, operation, *, source_id=123, art="Cod.659-92", quant=2):
        return InspectionFine.objects.create(
            operation=operation,
            source_id=source_id,
            art=art,
            quant=quant,
            source_created_at=datetime(2026, 8, 10, 8, 6, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 8, 10, 8, 36, tzinfo=timezone.utc),
        )

    def authenticate(self):
        self.client.force_authenticate(self.user)

    def test_unauthenticated_user_cannot_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_lists_reports(self):
        report = self.make_report()
        self.make_operation(report)
        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["team"], "A3")

    def test_listing_is_paginated(self):
        for index in range(55):
            report = self.make_report(source_suffix=str(index + 1), team=f"T{index}")
            self.make_operation(report, source_suffix=str(index + 1))
        self.authenticate()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 55)
        self.assertEqual(len(response.data["results"]), 50)

    def test_filter_date_from(self):
        old_report = self.make_report(source_suffix="1", operation_date=date(2026, 8, 9))
        new_report = self.make_report(source_suffix="2", operation_date=date(2026, 8, 10))
        self.make_operation(old_report, source_suffix="1")
        self.make_operation(new_report, source_suffix="2")
        self.authenticate()

        response = self.client.get(self.list_url, {"date_from": "2026-08-10"})

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], new_report.id)

    def test_filter_date_to(self):
        old_report = self.make_report(source_suffix="1", operation_date=date(2026, 8, 9))
        new_report = self.make_report(source_suffix="2", operation_date=date(2026, 8, 10))
        self.make_operation(old_report, source_suffix="1")
        self.make_operation(new_report, source_suffix="2")
        self.authenticate()

        response = self.client.get(self.list_url, {"date_to": "2026-08-09"})

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], old_report.id)

    def test_filter_by_team(self):
        report_a3 = self.make_report(source_suffix="1", team="A3")
        report_b4 = self.make_report(source_suffix="2", team="B4")
        self.make_operation(report_a3, source_suffix="1")
        self.make_operation(report_b4, source_suffix="2")
        self.authenticate()

        response = self.client.get(self.list_url, {"team": "A3"})

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["team"], "A3")

    def test_filter_by_statistics_status(self):
        pending = self.make_report(source_suffix="1", statistics_status=InspectionReport.StatisticsStatus.PENDING)
        included = self.make_report(source_suffix="2", statistics_status=InspectionReport.StatisticsStatus.INCLUDED)
        self.make_operation(pending, source_suffix="1")
        self.make_operation(included, source_suffix="2")
        self.authenticate()

        response = self.client.get(self.list_url, {"statistics_status": "INCLUDED"})

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["statistics_status"], "INCLUDED")

    def test_combined_filters(self):
        keep = self.make_report(source_suffix="1", team="A3", operation_date=date(2026, 8, 10), statistics_status=InspectionReport.StatisticsStatus.PENDING)
        other_team = self.make_report(source_suffix="2", team="B4", operation_date=date(2026, 8, 10), statistics_status=InspectionReport.StatisticsStatus.PENDING)
        other_date = self.make_report(source_suffix="3", team="A3", operation_date=date(2026, 8, 9), statistics_status=InspectionReport.StatisticsStatus.PENDING)
        other_status = self.make_report(source_suffix="4", team="A3", operation_date=date(2026, 8, 10), statistics_status=InspectionReport.StatisticsStatus.EXCLUDED)
        for idx, report in enumerate([keep, other_team, other_date, other_status], start=1):
            self.make_operation(report, source_suffix=str(idx))
        self.authenticate()

        response = self.client.get(
            self.list_url,
            {"date_from": "2026-08-10", "date_to": "2026-08-10", "team": "A3", "statistics_status": "PENDING"},
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], keep.id)

    def test_default_ordering(self):
        newer_date = self.make_report(source_suffix="1", operation_date=date(2026, 8, 11), created_at=datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc))
        same_date_older = self.make_report(source_suffix="2", operation_date=date(2026, 8, 10), created_at=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc))
        same_date_newer = self.make_report(source_suffix="3", operation_date=date(2026, 8, 10), created_at=datetime(2026, 8, 10, 11, 0, tzinfo=timezone.utc))
        for idx, report in enumerate([newer_date, same_date_older, same_date_newer], start=1):
            self.make_operation(report, source_suffix=str(idx))
        self.authenticate()

        response = self.client.get(self.list_url)
        ids = [item["id"] for item in response.data["results"]]

        self.assertEqual(ids[:3], [newer_date.id, same_date_newer.id, same_date_older.id])

    def test_report_detail(self):
        report = self.make_report()
        operation = self.make_operation(report)
        self.make_fine(operation)
        self.authenticate()

        response = self.client.get(reverse("inspection-reports-detail", args=[report.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["team"], "A3")
        self.assertEqual(len(response.data["operations"]), 1)
        self.assertEqual(response.data["statistics_status"], "PENDING")

    def test_detail_includes_multiple_operations(self):
        report = self.make_report()
        self.make_operation(report, source_suffix="1")
        self.make_operation(report, source_suffix="2", approach=20)
        self.authenticate()

        response = self.client.get(reverse("inspection-reports-detail", args=[report.id]))

        self.assertEqual(len(response.data["operations"]), 2)

    def test_detail_includes_multiple_fines(self):
        report = self.make_report()
        operation = self.make_operation(report)
        self.make_fine(operation, source_id=123, quant=2)
        self.make_fine(operation, source_id=124, quant=1)
        self.authenticate()

        response = self.client.get(reverse("inspection-reports-detail", args=[report.id]))

        self.assertEqual(len(response.data["operations"][0]["fines"]), 2)

    def test_fined_remains_independent_from_sum_of_fines(self):
        report = self.make_report()
        operation = self.make_operation(report, fined=44)
        self.make_fine(operation, source_id=123, quant=2)
        self.make_fine(operation, source_id=124, quant=1)
        self.authenticate()

        response = self.client.get(reverse("inspection-reports-detail", args=[report.id]))

        self.assertEqual(response.data["operations"][0]["fined"], 44)
        fine_sum = sum(item["quant"] or 0 for item in response.data["operations"][0]["fines"])
        self.assertEqual(fine_sum, 3)

    def test_removal_resolutions_270_appears_unchanged(self):
        report = self.make_report()
        operation = self.make_operation(report, removal_resolutions=270)
        self.make_fine(operation)
        self.authenticate()

        response = self.client.get(reverse("inspection-reports-detail", args=[report.id]))

        self.assertEqual(response.data["operations"][0]["removal_resolutions"], 270)

    def test_null_continues_null(self):
        report = self.make_report()
        operation = self.make_operation(report, approach=None)
        self.make_fine(operation)
        self.authenticate()

        response = self.client.get(reverse("inspection-reports-detail", args=[report.id]))

        self.assertIsNone(response.data["management_id"])
        self.assertIsNone(response.data["operations"][0]["approach"])

    def test_zero_continues_zero(self):
        report = self.make_report()
        operation = self.make_operation(report, four_ml=0, towed=0)
        self.make_fine(operation)
        self.authenticate()

        response = self.client.get(reverse("inspection-reports-detail", args=[report.id]))

        self.assertEqual(response.data["operations"][0]["four_ml"], 0)
        self.assertEqual(response.data["operations"][0]["towed"], 0)

    def test_human_post_is_blocked(self):
        self.authenticate()
        response = self.client.post(self.list_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_human_patch_is_blocked(self):
        report = self.make_report()
        self.make_operation(report)
        self.authenticate()
        response = self.client.patch(reverse("inspection-reports-detail", args=[report.id]), {"team": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_human_delete_is_blocked(self):
        report = self.make_report()
        self.make_operation(report)
        self.authenticate()
        response = self.client.delete(reverse("inspection-reports-detail", args=[report.id]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


@override_settings(INSPECTION_SYNC_TOKEN="secret-token")
class InspectionTechnicalSyncRegressionTests(APITestCase):
    def test_technical_sync_endpoint_still_works(self):
        client = APIClient()
        response = client.post(
            reverse("inspection_sync_reports"),
            {
                "source_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "source_created_at": "2026-08-10T08:00:00Z",
                "source_updated_at": "2026-08-10T08:30:00Z",
                "operation_date": "2026-08-10",
                "team": "A3",
                "operations": [],
            },
            format="json",
            HTTP_AUTHORIZATION="Bearer secret-token",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["result"], "created")
