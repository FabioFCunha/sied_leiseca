from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.inspection.models import (
    InspectionFine,
    InspectionReport,
    InspectionReportOperation,
    InspectionStatistic,
    InspectionStatisticsDecisionHistory,
)


REPORT_MUTABLE_FIELDS = [
    "source_created_at",
    "source_updated_at",
    "operation_date",
    "team",
    "management_id",
    "military_chief_source_id",
    "segov_team_civil",
    "segov_team_military",
    "change_ols",
    "agent_detran",
    "number_trailers",
    "change_support",
    "cars",
    "changes_general",
]

OPERATION_MUTABLE_FIELDS = [
    "report",
    "source_created_at",
    "source_updated_at",
    "address_operation",
    "locality",
    "another_not_listed",
    "departure_meeting_point",
    "operation_assembly",
    "first_approach",
    "closing",
    "approach",
    "reconductor",
    "refusal",
    "celebrities_authorities",
    "four_ml",
    "thirtythree_ml",
    "thirtyfour_ml",
    "passive_tests_performed",
    "changes_material",
    "cnh_collected",
    "fined",
    "towed",
    "removal_resolutions",
    "arrests_means_evidence",
    "art307",
    "criminal_occurrences",
    "driving_canceled_license",
    "vehicle_resolutions",
    "administrative_tests",
    "cep",
    "street",
    "city",
    "district",
    "number",
]

FINE_MUTABLE_FIELDS = [
    "operation",
    "art",
    "quant",
    "source_created_at",
    "source_updated_at",
]

STATISTIC_SUM_FIELDS = [
    "approach",
    "reconductor",
    "refusal",
    "celebrities_authorities",
    "four_ml",
    "thirtythree_ml",
    "thirtyfour_ml",
    "passive_tests_performed",
    "cnh_collected",
    "fined",
    "towed",
    "removal_resolutions",
    "arrests_means_evidence",
    "art307",
    "criminal_occurrences",
    "driving_canceled_license",
]


@dataclass
class InspectionSyncResult:
    report: InspectionReport
    outcome: str
    detail: str


@dataclass
class InspectionStatisticsDecisionResult:
    report: InspectionReport
    outcome: str
    detail: str


@dataclass
class InspectionStatisticGenerationResult:
    statistic: InspectionStatistic
    outcome: str
    detail: str


def build_statistics_snapshot(report, *, reviewed_at, reviewed_by):
    operations = report.operations.prefetch_related("fines").order_by("id")
    return {
        "report": {
            "source_id": str(report.source_id),
            "source_created_at": report.source_created_at.isoformat(),
            "source_updated_at": report.source_updated_at.isoformat(),
            "operation_date": report.operation_date.isoformat(),
            "team": report.team,
            "management_id": report.management_id,
            "military_chief_source_id": str(report.military_chief_source_id) if report.military_chief_source_id else None,
            "segov_team_civil": report.segov_team_civil,
            "segov_team_military": report.segov_team_military,
            "change_ols": report.change_ols,
            "agent_detran": report.agent_detran,
            "number_trailers": report.number_trailers,
            "change_support": report.change_support,
            "cars": report.cars,
            "changes_general": report.changes_general,
        },
        "operations": [
            {
                "source_id": str(operation.source_id),
                "source_created_at": operation.source_created_at.isoformat(),
                "source_updated_at": operation.source_updated_at.isoformat(),
                "address_operation": operation.address_operation,
                "locality": operation.locality,
                "another_not_listed": operation.another_not_listed,
                "departure_meeting_point": operation.departure_meeting_point,
                "operation_assembly": operation.operation_assembly,
                "first_approach": operation.first_approach,
                "closing": operation.closing,
                "approach": operation.approach,
                "reconductor": operation.reconductor,
                "refusal": operation.refusal,
                "celebrities_authorities": operation.celebrities_authorities,
                "four_ml": operation.four_ml,
                "thirtythree_ml": operation.thirtythree_ml,
                "thirtyfour_ml": operation.thirtyfour_ml,
                "passive_tests_performed": operation.passive_tests_performed,
                "changes_material": operation.changes_material,
                "cnh_collected": operation.cnh_collected,
                "fined": operation.fined,
                "towed": operation.towed,
                "removal_resolutions": operation.removal_resolutions,
                "arrests_means_evidence": operation.arrests_means_evidence,
                "art307": operation.art307,
                "criminal_occurrences": operation.criminal_occurrences,
                "driving_canceled_license": operation.driving_canceled_license,
                "vehicle_resolutions": operation.vehicle_resolutions,
                "administrative_tests": operation.administrative_tests,
                "cep": operation.cep,
                "street": operation.street,
                "city": operation.city,
                "district": operation.district,
                "number": operation.number,
                "fines": [
                    {
                        "source_id": fine.source_id,
                        "art": fine.art,
                        "quant": fine.quant,
                        "source_created_at": fine.source_created_at.isoformat(),
                        "source_updated_at": fine.source_updated_at.isoformat(),
                    }
                    for fine in operation.fines.all()
                ],
            }
            for operation in operations
        ],
        "traceability": {
            "source_updated_at": report.source_updated_at.isoformat(),
            "statistics_reviewed_at": reviewed_at.isoformat(),
            "statistics_reviewed_by": {
                "id": reviewed_by.id,
                "full_name": reviewed_by.full_name,
                "email": reviewed_by.email,
            },
        },
    }


def aggregate_nullable_sum(items, field_name):
    values = [
        item.get(field_name)
        for item in items
        if item.get(field_name) is not None
    ]
    if not values:
        return None
    return sum(values)


def build_official_statistic_fields_from_snapshot(snapshot):
    operations = list(snapshot.get("operations") or [])
    report_payload = snapshot.get("report") or {}
    traceability = snapshot.get("traceability") or {}

    if not operations:
        raise ValidationError({"detail": "O snapshot homologado precisa conter ao menos uma operacao para gerar estatistica oficial."})

    statistic_fields = {
        "source_report_id": UUID(str(report_payload.get("source_id"))),
        "operation_date": date.fromisoformat(report_payload.get("operation_date")),
        "team": report_payload.get("team") or "",
        "snapshot_source_updated_at": datetime.fromisoformat(
            (traceability.get("source_updated_at") or report_payload.get("source_updated_at")).replace("Z", "+00:00")
        ),
        "source": InspectionStatistic.StatisticSource.REPORT,
        "operations_count": len(operations),
    }
    for field_name in STATISTIC_SUM_FIELDS:
        statistic_fields[field_name] = aggregate_nullable_sum(operations, field_name)
    return statistic_fields


class InspectionSyncService:
    @transaction.atomic
    def sync_report(self, payload):
        now = timezone.now()
        report = InspectionReport.objects.select_for_update().filter(source_id=payload["source_id"]).first()

        if report is None:
            report = self._create_report(payload, now)
            self._sync_children(report, payload)
            return InspectionSyncResult(report=report, outcome="created", detail="Relatorio criado.")

        latest_known_source_updated_at = self._latest_known_source_updated_at(report)
        incoming_updated_at = payload["source_updated_at"]

        if incoming_updated_at < latest_known_source_updated_at:
            return InspectionSyncResult(
                report=report,
                outcome="ignored_stale",
                detail="Payload ignorado por possuir versao mais antiga.",
            )

        if incoming_updated_at == latest_known_source_updated_at:
            detail = "Payload ja sincronizado com a mesma versao."
            outcome = "ignored_equal"
            if (
                report.statistics_status == InspectionReport.StatisticsStatus.INCLUDED
                and report.has_source_update_after_statistics_review
                and report.source_update_after_statistics_review_at == incoming_updated_at
            ):
                detail = "Atualizacao da origem ja registrada como divergencia apos homologacao estatistica."
                outcome = "ignored_source_update_after_statistics_review"
            return InspectionSyncResult(report=report, outcome=outcome, detail=detail)

        if report.statistics_status == InspectionReport.StatisticsStatus.INCLUDED:
            self._flag_source_update_after_statistics_review(report, incoming_updated_at)
            return InspectionSyncResult(
                report=report,
                outcome="flagged_source_update_after_statistics_review",
                detail="Existe versao mais nova na origem apos homologacao estatistica; snapshot homologado foi preservado.",
            )

        self._update_report(report, payload, now)
        self._sync_children(report, payload)

        if report.statistics_status == InspectionReport.StatisticsStatus.EXCLUDED:
            self._reset_excluded_report_to_pending(report)

        return InspectionSyncResult(report=report, outcome="updated", detail="Relatorio atualizado.")

    def _latest_known_source_updated_at(self, report):
        if report.source_update_after_statistics_review_at:
            return max(report.source_updated_at, report.source_update_after_statistics_review_at)
        return report.source_updated_at

    def _create_report(self, payload, synced_at):
        create_data = {field: payload.get(field) for field in REPORT_MUTABLE_FIELDS}
        create_data["source_id"] = payload["source_id"]
        create_data["synced_at"] = synced_at
        create_data["status"] = InspectionReport.ReportStatus.SYNCED
        create_data["statistics_status"] = InspectionReport.StatisticsStatus.PENDING
        return InspectionReport.objects.create(**create_data)

    def _update_report(self, report, payload, synced_at):
        for field in REPORT_MUTABLE_FIELDS:
            setattr(report, field, payload.get(field))
        report.synced_at = synced_at
        report.save(update_fields=REPORT_MUTABLE_FIELDS + ["synced_at", "updated_at"])

    def _flag_source_update_after_statistics_review(self, report, incoming_updated_at):
        update_fields = ["has_source_update_after_statistics_review", "source_update_after_statistics_review_at", "updated_at"]
        report.has_source_update_after_statistics_review = True
        if (
            report.source_update_after_statistics_review_at is None
            or incoming_updated_at > report.source_update_after_statistics_review_at
        ):
            report.source_update_after_statistics_review_at = incoming_updated_at
        report.save(update_fields=update_fields)

    def _reset_excluded_report_to_pending(self, report):
        old_status = report.statistics_status
        report.statistics_status = InspectionReport.StatisticsStatus.PENDING
        report.statistics_reviewed_by = None
        report.statistics_reviewed_at = None
        report.statistics_exclusion_reason = ""
        report.statistics_snapshot = None
        report.has_source_update_after_statistics_review = False
        report.source_update_after_statistics_review_at = None
        report.save(
            update_fields=[
                "statistics_status",
                "statistics_reviewed_by",
                "statistics_reviewed_at",
                "statistics_exclusion_reason",
                "statistics_snapshot",
                "has_source_update_after_statistics_review",
                "source_update_after_statistics_review_at",
                "updated_at",
            ]
        )
        InspectionStatisticsDecisionHistory.objects.create(
            report=report,
            old_status=old_status,
            new_status=InspectionReport.StatisticsStatus.PENDING,
            changed_by=None,
            notes="Nova versao recebida da origem; exclusao anterior voltou para analise.",
        )

    def _sync_children(self, report, payload):
        for operation_payload in payload.get("operations", []):
            operation = self._sync_operation(report, operation_payload)
            for fine_payload in operation_payload.get("fines", []):
                self._sync_fine(operation, fine_payload)

    def _sync_operation(self, report, payload):
        operation = InspectionReportOperation.objects.select_for_update().filter(source_id=payload["source_id"]).first()
        if operation is None:
            create_data = {field: payload.get(field) for field in OPERATION_MUTABLE_FIELDS if field != "report"}
            create_data["report"] = report
            create_data["source_id"] = payload["source_id"]
            return InspectionReportOperation.objects.create(**create_data)

        if payload["source_updated_at"] <= operation.source_updated_at:
            return operation

        for field in OPERATION_MUTABLE_FIELDS:
            if field == "report":
                setattr(operation, field, report)
            else:
                setattr(operation, field, payload.get(field))
        operation.save(update_fields=OPERATION_MUTABLE_FIELDS + ["updated_at"])
        return operation

    def _sync_fine(self, operation, payload):
        fine = InspectionFine.objects.select_for_update().filter(source_id=payload["source_id"]).first()
        if fine is None:
            create_data = {field: payload.get(field) for field in FINE_MUTABLE_FIELDS if field != "operation"}
            create_data["operation"] = operation
            create_data["source_id"] = payload["source_id"]
            return InspectionFine.objects.create(**create_data)

        if payload["source_updated_at"] <= fine.source_updated_at:
            return fine

        for field in FINE_MUTABLE_FIELDS:
            if field == "operation":
                setattr(fine, field, operation)
            else:
                setattr(fine, field, payload.get(field))
        fine.save(update_fields=FINE_MUTABLE_FIELDS + ["updated_at"])
        return fine


class InspectionOfficialStatisticService:
    @transaction.atomic
    def generate_for_report(self, report, *, generated_by):
        if not isinstance(report, InspectionReport):
            report = InspectionReport.objects.get(pk=report)

        report = InspectionReport.objects.select_for_update().get(pk=report.pk)
        if report.statistics_status != InspectionReport.StatisticsStatus.INCLUDED:
            raise ValidationError({"detail": "Somente relatorios incluidos podem gerar estatistica oficial."})
        if not report.statistics_snapshot:
            raise ValidationError({"detail": "Nao e possivel gerar estatistica oficial sem snapshot homologado."})

        statistic = InspectionStatistic.objects.filter(report=report).first()
        if statistic is not None:
            return InspectionStatisticGenerationResult(
                statistic=statistic,
                outcome="existing",
                detail="Estatistica oficial ja existente para este relatorio homologado.",
            )

        statistic_fields = build_official_statistic_fields_from_snapshot(report.statistics_snapshot)
        statistic = InspectionStatistic.objects.create(
            report=report,
            generated_by=generated_by,
            **statistic_fields,
        )
        return InspectionStatisticGenerationResult(
            statistic=statistic,
            outcome="created",
            detail="Estatistica oficial gerada a partir do snapshot homologado.",
        )


class InspectionStatisticsService:
    @transaction.atomic
    def include_report(self, report_id, *, user):
        report = (
            InspectionReport.objects.select_for_update()
            .prefetch_related("operations__fines")
            .get(pk=report_id)
        )
        if report.statistics_status != InspectionReport.StatisticsStatus.PENDING:
            raise ValidationError({"detail": "Somente relatorios aguardando analise podem ser incluidos na estatistica."})

        reviewed_at = timezone.now()
        snapshot = build_statistics_snapshot(report, reviewed_at=reviewed_at, reviewed_by=user)
        old_status = report.statistics_status

        report.statistics_status = InspectionReport.StatisticsStatus.INCLUDED
        report.statistics_reviewed_by = user
        report.statistics_reviewed_at = reviewed_at
        report.statistics_exclusion_reason = ""
        report.statistics_snapshot = snapshot
        report.has_source_update_after_statistics_review = False
        report.source_update_after_statistics_review_at = None
        report.save(
            update_fields=[
                "statistics_status",
                "statistics_reviewed_by",
                "statistics_reviewed_at",
                "statistics_exclusion_reason",
                "statistics_snapshot",
                "has_source_update_after_statistics_review",
                "source_update_after_statistics_review_at",
                "updated_at",
            ]
        )
        InspectionStatisticsDecisionHistory.objects.create(
            report=report,
            old_status=old_status,
            new_status=InspectionReport.StatisticsStatus.INCLUDED,
            changed_by=user,
            notes="Relatorio incluido na estatistica com snapshot homologado.",
        )
        InspectionOfficialStatisticService().generate_for_report(report, generated_by=user)
        report.refresh_from_db()
        return InspectionStatisticsDecisionResult(
            report=report,
            outcome="included",
            detail="Relatorio incluido na estatistica com snapshot homologado.",
        )

    @transaction.atomic
    def exclude_report(self, report_id, *, user, reason):
        report = InspectionReport.objects.select_for_update().get(pk=report_id)
        if report.statistics_status != InspectionReport.StatisticsStatus.PENDING:
            raise ValidationError({"detail": "Somente relatorios aguardando analise podem ser excluidos da estatistica."})

        reviewed_at = timezone.now()
        old_status = report.statistics_status

        report.statistics_status = InspectionReport.StatisticsStatus.EXCLUDED
        report.statistics_reviewed_by = user
        report.statistics_reviewed_at = reviewed_at
        report.statistics_exclusion_reason = reason
        report.statistics_snapshot = None
        report.has_source_update_after_statistics_review = False
        report.source_update_after_statistics_review_at = None
        report.save(
            update_fields=[
                "statistics_status",
                "statistics_reviewed_by",
                "statistics_reviewed_at",
                "statistics_exclusion_reason",
                "statistics_snapshot",
                "has_source_update_after_statistics_review",
                "source_update_after_statistics_review_at",
                "updated_at",
            ]
        )
        InspectionStatisticsDecisionHistory.objects.create(
            report=report,
            old_status=old_status,
            new_status=InspectionReport.StatisticsStatus.EXCLUDED,
            changed_by=user,
            notes=reason,
        )
        return InspectionStatisticsDecisionResult(
            report=report,
            outcome="excluded",
            detail="Relatorio marcado como nao incluido na estatistica.",
        )
