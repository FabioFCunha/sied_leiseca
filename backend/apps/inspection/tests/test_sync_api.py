from copy import deepcopy

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.inspection.models import InspectionFine, InspectionReport, InspectionReportOperation, InspectionStatisticsDecisionHistory
from apps.inspection.serializers import InspectionReportIngestionSerializer
from apps.inspection.services import InspectionSyncService


class InspectionSyncPayloadMixin:
    def payload(self):
        return {
            "source_id": "11111111-1111-1111-1111-111111111111",
            "source_created_at": "2026-08-10T08:00:00Z",
            "source_updated_at": "2026-08-10T08:30:00Z",
            "operation_date": "2026-08-10",
            "team": "A3",
            "management_id": 1,
            "military_chief_source_id": "22222222-2222-2222-2222-222222222222",
            "civil_chief_name": "Chefe Civil",
            "military_chief_name": "Chefe Militar",
            "segov_team_civil": "Equipe civil ficticia",
            "segov_team_military": "Equipe militar ficticia",
            "change_ols": "Sem alteracoes",
            "agent_detran": 2,
            "number_trailers": 0,
            "change_support": "",
            "cars": "VTR-01",
            "changes_general": "Sem alteracoes",
            "changes_material": "Sem alteracao de material",
            "complement_source_updated_at": "2026-08-10T08:31:00Z",
            "support_opm": "38 BPM",
            "support_pmerj_staff": "54-0934\nSubten exemplo",
            "support_vehicles": "54-0934",
            "low_approach_reasons": "Baixa abordagem justificada",
            "team_violation_notices": "AI-123",
            "specified_violation_notices": "AI-123 detalhado",
            "miscellaneous_changes": "Alteracoes diversas",
            "operations": [
                {
                    "source_id": "33333333-3333-3333-3333-333333333333",
                    "source_created_at": "2026-08-10T08:05:00Z",
                    "source_updated_at": "2026-08-10T08:35:00Z",
                    "address_operation": "Rua Ficticia, 100",
                    "locality": "Vista Alegre",
                    "another_not_listed": "",
                    "departure_meeting_point": "20:00",
                    "operation_assembly": "20:45",
                    "first_approach": "21:40",
                    "closing": "02:00",
                    "approach": 93,
                    "reconductor": 10,
                    "refusal": 5,
                    "celebrities_authorities": 0,
                    "four_ml": 88,
                    "thirtythree_ml": 0,
                    "thirtyfour_ml": 0,
                    "passive_tests_performed": 0,
                    "changes_material": "",
                    "cnh_collected": 0,
                    "fined": 44,
                    "towed": 0,
                    "removal_resolutions": 270,
                    "arrests_means_evidence": 0,
                    "art307": 0,
                    "criminal_occurrences": 0,
                    "driving_canceled_license": 1,
                    "vehicle_resolutions": "003 contran",
                    "administrative_tests": "Sem alteracoes",
                    "cep": "21250-392",
                    "street": "Rua Ficticia",
                    "city": "Rio de Janeiro",
                    "district": "Vista Alegre",
                    "number": "",
                    "fines": [
                        {
                            "source_id": 123,
                            "art": "Cod.659-92",
                            "quant": 2,
                            "source_created_at": "2026-08-10T08:06:00Z",
                            "source_updated_at": "2026-08-10T08:36:00Z",
                        }
                    ],
                }
            ],
        }

    def validated_payload(self):
        serializer = InspectionReportIngestionSerializer(data=self.payload())
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class InspectionSyncServiceTests(InspectionSyncPayloadMixin, TestCase):
    def setUp(self):
        self.service = InspectionSyncService()

    def test_ingests_new_report(self):
        result = self.service.sync_report(self.validated_payload())

        self.assertEqual(result.outcome, "created")
        self.assertEqual(InspectionReport.objects.count(), 1)
        self.assertEqual(InspectionReport.objects.get().statistics_status, InspectionReport.StatisticsStatus.PENDING)

    def test_ingests_confirmed_horus_complement_fields(self):
        self.service.sync_report(self.validated_payload())
        report = InspectionReport.objects.get()

        self.assertEqual(report.civil_chief_name, "Chefe Civil")
        self.assertEqual(report.military_chief_name, "Chefe Militar")
        self.assertEqual(report.support_opm, "38 BPM")
        self.assertEqual(report.support_pmerj_staff, "54-0934\nSubten exemplo")
        self.assertEqual(report.support_vehicles, "54-0934")
        self.assertEqual(report.low_approach_reasons, "Baixa abordagem justificada")
        self.assertEqual(report.team_violation_notices, "AI-123")
        self.assertEqual(report.specified_violation_notices, "AI-123 detalhado")
        self.assertEqual(report.miscellaneous_changes, "Alteracoes diversas")

    def test_newer_complement_updates_existing_report_idempotently(self):
        self.service.sync_report(self.validated_payload())
        updated = self.payload()
        updated["complement_source_updated_at"] = "2026-08-10T08:45:00Z"
        updated["support_vehicles"] = "54-0935"

        serializer = InspectionReportIngestionSerializer(data=updated)
        serializer.is_valid(raise_exception=True)
        result = self.service.sync_report(serializer.validated_data)

        self.assertEqual(result.outcome, "updated")
        self.assertEqual(InspectionReport.objects.get().support_vehicles, "54-0935")

    def test_creates_multiple_operations(self):
        payload = self.payload()
        second = deepcopy(payload["operations"][0])
        second["source_id"] = "44444444-4444-4444-4444-444444444444"
        payload["operations"].append(second)

        serializer = InspectionReportIngestionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.service.sync_report(serializer.validated_data)

        self.assertEqual(InspectionReportOperation.objects.count(), 2)

    def test_creates_multiple_fines(self):
        payload = self.payload()
        payload["operations"][0]["fines"].append(
            {
                "source_id": 124,
                "art": "Cod.777-00",
                "quant": 1,
                "source_created_at": "2026-08-10T08:06:30Z",
                "source_updated_at": "2026-08-10T08:36:30Z",
            }
        )

        serializer = InspectionReportIngestionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.service.sync_report(serializer.validated_data)

        self.assertEqual(InspectionFine.objects.count(), 2)

    def test_repeated_ingestion_does_not_duplicate_report(self):
        validated = self.validated_payload()
        self.service.sync_report(validated)
        result = self.service.sync_report(validated)

        self.assertEqual(result.outcome, "ignored_equal")
        self.assertEqual(InspectionReport.objects.count(), 1)

    def test_repeated_ingestion_does_not_duplicate_operation(self):
        validated = self.validated_payload()
        self.service.sync_report(validated)
        self.service.sync_report(validated)

        self.assertEqual(InspectionReportOperation.objects.count(), 1)

    def test_repeated_ingestion_does_not_duplicate_fine(self):
        validated = self.validated_payload()
        self.service.sync_report(validated)
        self.service.sync_report(validated)

        self.assertEqual(InspectionFine.objects.count(), 1)

    def test_newer_version_updates_pending_report(self):
        self.service.sync_report(self.validated_payload())

        updated = self.payload()
        updated["source_updated_at"] = "2026-08-10T08:40:00Z"
        updated["changes_general"] = "Atualizado"
        updated["operations"][0]["source_updated_at"] = "2026-08-10T08:45:00Z"
        updated["operations"][0]["approach"] = 95
        updated["operations"][0]["fines"][0]["source_updated_at"] = "2026-08-10T08:46:00Z"
        updated["operations"][0]["fines"][0]["quant"] = 4

        serializer = InspectionReportIngestionSerializer(data=updated)
        serializer.is_valid(raise_exception=True)
        result = self.service.sync_report(serializer.validated_data)
        report = InspectionReport.objects.get()
        operation = InspectionReportOperation.objects.get()
        fine = InspectionFine.objects.get()

        self.assertEqual(result.outcome, "updated")
        self.assertEqual(report.changes_general, "Atualizado")
        self.assertEqual(operation.approach, 95)
        self.assertEqual(fine.quant, 4)
        self.assertEqual(report.statistics_status, InspectionReport.StatisticsStatus.PENDING)

    def test_equal_report_version_with_newer_child_updates_children(self):
        initial = self.payload()
        initial["operations"] = []

        serializer = InspectionReportIngestionSerializer(data=initial)
        serializer.is_valid(raise_exception=True)
        first = self.service.sync_report(serializer.validated_data)

        self.assertEqual(first.outcome, "created")
        self.assertEqual(
            InspectionReportOperation.objects.count(),
            0,
        )

        updated = self.payload()

        # O cabecalho permanece com a mesma versao.
        updated["source_updated_at"] = initial["source_updated_at"]

        # A operacao foi gravada posteriormente no Horus.
        updated["operations"][0][
            "source_updated_at"
        ] = "2026-08-10T08:35:00Z"

        serializer = InspectionReportIngestionSerializer(data=updated)
        serializer.is_valid(raise_exception=True)
        second = self.service.sync_report(serializer.validated_data)

        self.assertEqual(second.outcome, "updated")
        self.assertEqual(
            InspectionReport.objects.count(),
            1,
        )
        self.assertEqual(
            InspectionReportOperation.objects.count(),
            1,
        )

        # Uma nova ingestao identica permanece idempotente.
        serializer = InspectionReportIngestionSerializer(data=updated)
        serializer.is_valid(raise_exception=True)
        third = self.service.sync_report(serializer.validated_data)

        self.assertEqual(third.outcome, "ignored_equal")
        self.assertEqual(
            InspectionReport.objects.count(),
            1,
        )
        self.assertEqual(
            InspectionReportOperation.objects.count(),
            1,
        )

    def test_older_version_does_not_overwrite(self):
        self.service.sync_report(self.validated_payload())

        older = self.payload()
        older["source_updated_at"] = "2026-08-10T08:20:00Z"
        older["changes_general"] = "Antigo"

        serializer = InspectionReportIngestionSerializer(data=older)
        serializer.is_valid(raise_exception=True)
        result = self.service.sync_report(serializer.validated_data)
        report = InspectionReport.objects.get()

        self.assertEqual(result.outcome, "ignored_stale")
        self.assertEqual(report.changes_general, "Sem alteracoes")

    def test_equal_version_is_idempotent(self):
        validated = self.validated_payload()
        self.service.sync_report(validated)
        result = self.service.sync_report(validated)

        self.assertEqual(result.outcome, "ignored_equal")

    def test_null_continues_null(self):
        payload = self.payload()
        payload["management_id"] = None
        payload["operations"][0]["approach"] = None

        serializer = InspectionReportIngestionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.service.sync_report(serializer.validated_data)
        report = InspectionReport.objects.get()
        operation = InspectionReportOperation.objects.get()

        self.assertIsNone(report.management_id)
        self.assertIsNone(operation.approach)

    def test_zero_continues_zero(self):
        payload = self.payload()
        payload["agent_detran"] = 0
        payload["operations"][0]["towed"] = 0

        serializer = InspectionReportIngestionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.service.sync_report(serializer.validated_data)
        report = InspectionReport.objects.get()
        operation = InspectionReportOperation.objects.get()

        self.assertEqual(report.agent_detran, 0)
        self.assertEqual(operation.towed, 0)

    def test_removal_resolutions_270_is_accepted(self):
        result = self.service.sync_report(self.validated_payload())

        self.assertEqual(result.outcome, "created")
        self.assertEqual(InspectionReportOperation.objects.get().removal_resolutions, 270)

    def test_fined_is_not_recalculated_from_fines(self):
        payload = self.payload()
        payload["operations"][0]["fines"][0]["quant"] = 2
        serializer = InspectionReportIngestionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.service.sync_report(serializer.validated_data)

        operation = InspectionReportOperation.objects.get()
        self.assertEqual(operation.fined, 44)
        self.assertEqual(sum(item.quant or 0 for item in operation.fines.all()), 2)

    def test_excluded_report_returns_to_pending_after_newer_source_version(self):
        self.service.sync_report(self.validated_payload())
        report = InspectionReport.objects.get()
        report.statistics_status = InspectionReport.StatisticsStatus.EXCLUDED
        report.statistics_exclusion_reason = "Inconsistencia"
        report.save(update_fields=["statistics_status", "statistics_exclusion_reason"])

        updated = self.payload()
        updated["source_updated_at"] = "2026-08-10T08:40:00Z"
        updated["changes_general"] = "Corrigido"
        serializer = InspectionReportIngestionSerializer(data=updated)
        serializer.is_valid(raise_exception=True)
        result = self.service.sync_report(serializer.validated_data)

        report.refresh_from_db()
        self.assertEqual(result.outcome, "updated")
        self.assertEqual(report.statistics_status, InspectionReport.StatisticsStatus.PENDING)
        self.assertEqual(report.statistics_exclusion_reason, "")
        self.assertEqual(report.changes_general, "Corrigido")
        self.assertTrue(
            InspectionStatisticsDecisionHistory.objects.filter(
                report=report,
                old_status=InspectionReport.StatisticsStatus.EXCLUDED,
                new_status=InspectionReport.StatisticsStatus.PENDING,
            ).exists()
        )

    def test_included_report_preserves_homologated_data_and_flags_newer_source(self):
        self.service.sync_report(self.validated_payload())
        report = InspectionReport.objects.get()
        report.statistics_status = InspectionReport.StatisticsStatus.INCLUDED
        report.save(update_fields=["statistics_status"])

        updated = self.payload()
        updated["source_updated_at"] = "2026-08-10T08:40:00Z"
        updated["changes_general"] = "Tentativa de sobrescrita"
        serializer = InspectionReportIngestionSerializer(data=updated)
        serializer.is_valid(raise_exception=True)
        result = self.service.sync_report(serializer.validated_data)

        report.refresh_from_db()
        self.assertEqual(result.outcome, "flagged_source_update_after_statistics_review")
        self.assertEqual(report.changes_general, "Sem alteracoes")
        self.assertTrue(report.has_source_update_after_statistics_review)
        self.assertIsNotNone(report.source_update_after_statistics_review_at)

    def test_report_payload_cannot_control_human_status(self):
        client = APIClient()
        payload = self.payload()
        payload["status"] = "APPROVED"

        with override_settings(INSPECTION_SYNC_TOKEN="secret-token"):
            response = client.post(
                reverse("inspection_sync_reports"),
                payload,
                format="json",
                HTTP_AUTHORIZATION="Bearer secret-token",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_report_payload_cannot_control_statistics_status(self):
        client = APIClient()
        payload = self.payload()
        payload["statistics_status"] = "INCLUDED"

        with override_settings(INSPECTION_SYNC_TOKEN="secret-token"):
            response = client.post(
                reverse("inspection_sync_reports"),
                payload,
                format="json",
                HTTP_AUTHORIZATION="Bearer secret-token",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("statistics_status", response.data)


@override_settings(INSPECTION_SYNC_TOKEN="secret-token")
class InspectionSyncApiTests(InspectionSyncPayloadMixin, APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("inspection_sync_reports")

    def test_endpoint_blocks_request_without_technical_authentication(self):
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_endpoint_accepts_valid_technical_authentication(self):
        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
            HTTP_AUTHORIZATION="Bearer secret-token",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["result"], "created")
        self.assertEqual(response.data["statistics_status"], "PENDING")

    def test_real_ingestion_proof_for_a3_flow(self):
        payload = self.payload()
        payload["management_id"] = None
        payload["military_chief_source_id"] = None
        payload["operations"][0]["another_not_listed"] = ""
        payload["operations"][0]["number"] = ""
        payload["operations"][0]["celebrities_authorities"] = 0
        payload["operations"][0]["passive_tests_performed"] = 0
        payload["operations"][0]["arrests_means_evidence"] = 0
        payload["operations"][0]["art307"] = 0
        payload["operations"][0]["criminal_occurrences"] = 0
        payload["operations"][0]["vehicle_resolutions"] = "003 contran"
        payload["operations"][0]["administrative_tests"] = "Sem Alteracoes"

        first_response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_AUTHORIZATION="Bearer secret-token",
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED, first_response.data)
        self.assertEqual(first_response.data["result"], "created")

        report = InspectionReport.objects.get()
        operation = InspectionReportOperation.objects.get()
        self.assertEqual(InspectionReport.objects.count(), 1)
        self.assertEqual(InspectionReportOperation.objects.count(), 1)
        self.assertEqual(report.team, "A3")
        self.assertEqual(str(report.operation_date), "2026-08-10")
        self.assertEqual(report.status, InspectionReport.ReportStatus.SYNCED)
        self.assertEqual(report.statistics_status, InspectionReport.StatisticsStatus.PENDING)
        self.assertIsNone(report.management_id)
        self.assertIsNone(report.military_chief_source_id)
        self.assertIsNotNone(report.synced_at)
        self.assertEqual(operation.approach, 93)
        self.assertEqual(operation.reconductor, 10)
        self.assertEqual(operation.refusal, 5)
        self.assertEqual(operation.celebrities_authorities, 0)
        self.assertEqual(operation.four_ml, 88)
        self.assertEqual(operation.thirtythree_ml, 0)
        self.assertEqual(operation.thirtyfour_ml, 0)
        self.assertEqual(operation.passive_tests_performed, 0)
        self.assertEqual(operation.cnh_collected, 0)
        self.assertEqual(operation.fined, 44)
        self.assertEqual(operation.towed, 0)
        self.assertEqual(operation.removal_resolutions, 270)
        self.assertEqual(operation.arrests_means_evidence, 0)
        self.assertEqual(operation.art307, 0)
        self.assertEqual(operation.criminal_occurrences, 0)
        self.assertEqual(operation.driving_canceled_license, 1)
        self.assertEqual(operation.departure_meeting_point, "20:00")
        self.assertEqual(operation.operation_assembly, "20:45")
        self.assertEqual(operation.first_approach, "21:40")
        self.assertEqual(operation.closing, "02:00")
        self.assertEqual(operation.city, "Rio de Janeiro")
        self.assertEqual(operation.district, "Vista Alegre")
        self.assertEqual(operation.cep, "21250-392")
        self.assertEqual(operation.vehicle_resolutions, "003 contran")
        self.assertEqual(operation.administrative_tests, "Sem Alteracoes")
        self.assertEqual(operation.number, "")

        second_response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_AUTHORIZATION="Bearer secret-token",
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK, second_response.data)
        self.assertEqual(second_response.data["result"], "ignored_equal")
        self.assertEqual(InspectionReport.objects.count(), 1)
        self.assertEqual(InspectionReportOperation.objects.count(), 1)

        updated_payload = deepcopy(payload)
        updated_payload["source_updated_at"] = "2026-08-10T08:40:00Z"
        updated_payload["cars"] = "VTR-02"
        update_response = self.client.post(
            self.url,
            updated_payload,
            format="json",
            HTTP_AUTHORIZATION="Bearer secret-token",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK, update_response.data)
        self.assertEqual(update_response.data["result"], "updated")
        report.refresh_from_db()
        self.assertEqual(report.cars, "VTR-02")
        self.assertEqual(report.status, InspectionReport.ReportStatus.SYNCED)
        self.assertEqual(report.statistics_status, InspectionReport.StatisticsStatus.PENDING)
        self.assertEqual(InspectionReport.objects.count(), 1)

        report.statistics_status = InspectionReport.StatisticsStatus.INCLUDED
        report.save(update_fields=["statistics_status"])
        approved_payload = deepcopy(updated_payload)
        approved_payload["source_updated_at"] = "2026-08-10T08:50:00Z"
        approved_payload["cars"] = "VTR-03"
        approved_response = self.client.post(
            self.url,
            approved_payload,
            format="json",
            HTTP_AUTHORIZATION="Bearer secret-token",
        )
        self.assertEqual(approved_response.status_code, status.HTTP_200_OK, approved_response.data)
        self.assertEqual(approved_response.data["result"], "flagged_source_update_after_statistics_review")
        report.refresh_from_db()
        self.assertEqual(report.cars, "VTR-02")
        self.assertEqual(report.statistics_status, InspectionReport.StatisticsStatus.INCLUDED)
        self.assertTrue(report.has_source_update_after_statistics_review)
