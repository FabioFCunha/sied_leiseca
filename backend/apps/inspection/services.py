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
        "statistics_classification": dict(
            report.statistics_classification or {}
        ),
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

        incoming_report_updated_at = payload["source_updated_at"]

        # Um cabecalho realmente mais antigo nunca pode sobrescrever
        # a versao do relatorio ja armazenada, mesmo que o payload
        # contenha filhos com timestamps mais recentes.
        if incoming_report_updated_at < report.source_updated_at:
            return InspectionSyncResult(
                report=report,
                outcome="ignored_stale",
                detail="Payload ignorado por possuir versao mais antiga.",
            )

        latest_known_source_updated_at = self._latest_known_source_updated_at(report)
        incoming_updated_at = self._effective_payload_updated_at(payload)

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

    def _effective_payload_updated_at(self, payload):
        """
        Retorna a versao efetiva recebida do Horus.

        O cabecalho do relatorio pode ser gravado antes das operacoes e
        multas relacionadas. Por isso, a versao efetiva precisa considerar
        tambem os timestamps dos registros filhos.
        """
        timestamps = [payload["source_updated_at"]]

        for operation_payload in payload.get("operations", []):
            operation_updated_at = operation_payload.get("source_updated_at")
            if operation_updated_at is not None:
                timestamps.append(operation_updated_at)

            for fine_payload in operation_payload.get("fines", []):
                fine_updated_at = fine_payload.get("source_updated_at")
                if fine_updated_at is not None:
                    timestamps.append(fine_updated_at)

        return max(timestamps)

    def _latest_known_source_updated_at(self, report):
        timestamps = [report.source_updated_at]

        if report.source_update_after_statistics_review_at:
            timestamps.append(
                report.source_update_after_statistics_review_at
            )

        operation_updated_at = (
            InspectionReportOperation.objects
            .filter(report=report)
            .order_by("-source_updated_at")
            .values_list("source_updated_at", flat=True)
            .first()
        )

        if operation_updated_at is not None:
            timestamps.append(operation_updated_at)

        fine_updated_at = (
            InspectionFine.objects
            .filter(operation__report=report)
            .order_by("-source_updated_at")
            .values_list("source_updated_at", flat=True)
            .first()
        )

        if fine_updated_at is not None:
            timestamps.append(fine_updated_at)

        return max(timestamps)

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
    def include_report(self, report_id, *, user, classification):
        report = (
            InspectionReport.objects.select_for_update()
            .prefetch_related("operations__fines")
            .get(pk=report_id)
        )
        if report.statistics_status != InspectionReport.StatisticsStatus.PENDING:
            raise ValidationError({"detail": "Somente relatorios aguardando analise podem ser incluidos na estatistica."})

        reviewed_at = timezone.now()

        report.statistics_classification = dict(classification)
        report.save(
            update_fields=[
                "statistics_classification",
                "updated_at",
            ]
        )

        snapshot = build_statistics_snapshot(
            report,
            reviewed_at=reviewed_at,
            reviewed_by=user,
        )
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



from django.db.models import Count, Sum, Value, F, Q
from django.db.models.functions import Coalesce

from apps.inspection.models import (
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalStatistic,
    InspectionPublicSecurityYearlyStatistic,
    HISTORICAL_CUTOFF_DATE,


    INSPECTION_STATISTICS_CUTOFF_DATE,
)


# Indicadores cuja fonte oficial exibida no dashboard e exclusivamente o Horus.
# O saldo-base corresponde ao acumulado auditado ate 09/08/2026.
HORUS_OPERATIONAL_CUTOFF_DATE = date(2026, 8, 10)
RAIN_STRUCTURED_CLASSIFICATION_FROM = date(2026, 8, 17)

HORUS_CARD_BASELINES = {
    "four_ml": {
        "value": 939914,
        "available_from": "2022-10-03",
    },
    "thirtythree_ml": {
        "value": 3512,
        "available_from": "2022-10-04",
    },
    "thirtyfour_ml": {
        "value": 736,
        "available_from": "2022-10-04",
    },
    "reconductor": {
        "value": 168019,
        "available_from": "2022-10-03",
    },
    "stolen_recovered_vehicles": {
        "value": 466,
        "available_from": "2022-10-03",
        "breakdown": {
            "recovered": 35,
            "stolen": 33,
            "theft": 398,
        },
    },
    "passive_tests_performed": {
        "value": 476969,
        "available_from": "2022-10-03",
    },
    "arrests_means_evidence": {
        "value": 244,
        "available_from": "2022-10-10",
    },
    "removal_resolutions": {
        "value": 143930,
        "available_from": "2022-10-03",
    },
    "art307": {
        "value": 2833,
        "available_from": "2022-10-03",
    },
    "criminal_occurrences": {
        "value": 1198,
        "available_from": "2022-10-03",
    },
    "driving_canceled_license": {
        "value": 618,
        "available_from": "2022-10-04",
    },
    "rain": {
        "value": 1974,
        "available_from": "2022-10-03",
    },
}


class InspectionStatisticsUnifiedService:
    def __init__(self, filters):
        self.filters = filters
        self.date_from = filters.get("date_from")

        self.date_from = (
            date.fromisoformat(filters["date_from"])
            if filters.get("date_from")
            else None
        )

        self.region = filters.get("region")

        self.date_to = (
            date.fromisoformat(filters["date_to"])
            if filters.get("date_to")
            else None
        )

        self.team = filters.get("team")

        self.use_historical = False
        self.use_operational = False

        #
        # Regra oficial:
        #
        # - até 09/08/2026:
        #   histórico consolidado;
        #
        # - a partir de 10/08/2026:
        #   estatística operacional homologada no SIED.
        #
        if not self.date_from and not self.date_to:
            self.use_historical = True
            self.use_operational = True

        else:
            d_from = self.date_from or date.min
            d_to = self.date_to or date.max

            if d_from < INSPECTION_STATISTICS_CUTOFF_DATE:
                self.use_historical = True

            if d_to >= INSPECTION_STATISTICS_CUTOFF_DATE:
                self.use_operational = True

    @staticmethod
    def _sum_nullable(a, b):
        if a is None and b is None:
            return None

        return (a or 0) + (b or 0)

    def get_dashboard_data(self):
        if self.region:
            hist_agg, hist_ts, hist_tp = (
                self._get_territorial_historical_data()
                if self.use_historical
                else ({}, [], {})
            )
        else:
            hist_agg, hist_ts, hist_tp = (
                self._get_historical_data()
                if self.use_historical
                else ({}, [], {})
            )

        if self.region:
            oper_agg, oper_ts, oper_tp = (
                self._get_territorial_operational_data()
                if self.use_operational
                else ({}, [], {})
            )
        else:
            oper_agg, oper_ts, oper_tp = (
                self._get_operational_data()
                if self.use_operational
                else ({}, [], {})
            )

        public_security, driver_extra = (
            self._get_public_security_data()
        )

        sources_used = []

        if self.use_historical:
            sources_used.append("historical")

        if self.use_operational:
            sources_used.append("report")

        #
        # RESUMO EXECUTIVO
        #
        summary = {
            "homologated_reports": (
                oper_agg.get("homologated_reports")
                if self.use_operational
                else None
            ),

            "operations": self._sum_nullable(
                hist_agg.get("operations"),
                oper_agg.get("operations"),
            ),

            "approach_plus_reconductor": None,

            "refusal": self._sum_nullable(
                hist_agg.get("refusal"),
                oper_agg.get("refusal"),
            ),

            "fined": self._sum_nullable(
                hist_agg.get("fined"),
                oper_agg.get("fined"),
            ),

            "towed": self._sum_nullable(
                hist_agg.get("towed"),
                oper_agg.get("towed"),
            ),

            "cnh_collected": self._sum_nullable(
                hist_agg.get("cnh_collected"),
                oper_agg.get("cnh_collected"),
            ),

            "passive_tests_performed": self._sum_nullable(
                hist_agg.get("passive_tests_performed"),
                oper_agg.get("passive_tests_performed"),
            ),

            "removal_resolutions": self._sum_nullable(
                hist_agg.get("removal_resolutions"),
                oper_agg.get("removal_resolutions"),
            ),

            "criminal_occurrences": self._sum_nullable(
                hist_agg.get("criminal_occurrences"),
                oper_agg.get("criminal_occurrences"),
            ),

            "art307": self._sum_nullable(
                hist_agg.get("art307"),
                oper_agg.get("art307"),
            ),

            "driving_canceled_license": self._sum_nullable(
                hist_agg.get("driving_canceled_license"),
                oper_agg.get("driving_canceled_license"),
            ),

            "arrests_means_evidence": self._sum_nullable(
                hist_agg.get("arrests_means_evidence"),
                oper_agg.get("arrests_means_evidence"),
            ),

            "celebrities_authorities": (
                oper_agg.get("celebrities_authorities")
                if self.use_operational
                else None
            ),

            #
            # Abordados pode existir tanto no histórico anual
            # quanto na estatística operacional.
            #
            "approach": self._sum_nullable(
                hist_agg.get("approach"),
                (
                    oper_agg.get("sum_approach")
                    if self.use_operational
                    else None
                ),
            ),

            "reconductor": self._sum_nullable(
                hist_agg.get("reconductor"),
                (
                    oper_agg.get("sum_reconductor")
                    if self.use_operational
                    else None
                ),
            ),
        }

        #
        # ABORDADOS + RECONDUTOR
        #
        # As definições histórica e operacional não são
        # necessariamente equivalentes.
        #
        if self.use_historical and not self.use_operational:
            summary["approach_plus_reconductor"] = (
                hist_agg.get("approach_plus_reconductor")
            )

        elif self.use_operational and not self.use_historical:
            summary["approach_plus_reconductor"] = (
                oper_agg.get("approach_plus_reconductor")
            )

        else:
            summary["approach_plus_reconductor"] = None

        #
        # RESULTADOS DO ETILÔMETRO
        #
        alcohol = {
            "four_ml": self._sum_nullable(
                hist_agg.get("four_ml"),
                oper_agg.get("four_ml"),
            ),

            "thirtythree_ml": self._sum_nullable(
                hist_agg.get("thirtythree_ml"),
                oper_agg.get("thirtythree_ml"),
            ),

            "thirtyfour_ml": self._sum_nullable(
                hist_agg.get("thirtyfour_ml"),
                oper_agg.get("thirtyfour_ml"),
            ),

            "refusal": self._sum_nullable(
                hist_agg.get("refusal"),
                oper_agg.get("refusal"),
            ),

            "arrests_means_evidence": self._sum_nullable(
                hist_agg.get("arrests_means_evidence"),
                oper_agg.get("arrests_means_evidence"),
            ),

            "negative_tests": (
                hist_agg.get("negative_tests")
                if self.use_historical
                else None
            ),

            "historical_alcohol_cases": (
                hist_agg.get("historical_alcohol_cases")
                if self.use_historical
                else None
            ),
        }

        #
        # CASOS DE ALCOOLEMIA
        #
        # Hist?rico:
        # utiliza o total institucional consolidado j? importado.
        #
        # Operacional:
        # Recusa + Art. 165 administrativo + Art. 306 +
        # pris?o por outros meios/sinais.
        #
        operational_alcohol_components = (
            oper_agg.get("refusal"),
            oper_agg.get("thirtythree_ml"),
            oper_agg.get("thirtyfour_ml"),
            oper_agg.get("arrests_means_evidence"),
        )

        operational_alcohol_cases = (
            sum(
                value or 0
                for value in operational_alcohol_components
            )
            if (
                self.use_operational
                and any(
                    value is not None
                    for value in operational_alcohol_components
                )
            )
            else None
        )

        historical_alcohol_cases = (
            hist_agg.get("historical_alcohol_cases")
            if self.use_historical
            else None
        )

        alcohol["alcohol_cases"] = self._sum_nullable(
            historical_alcohol_cases,
            operational_alcohol_cases,
        )

        approached_for_alcohol = (
            summary.get("approach_plus_reconductor")
            if summary.get("approach_plus_reconductor") is not None
            else summary.get("approach")
        )

        alcohol["alcohol_percentage"] = (
            (
                alcohol["alcohol_cases"]
                / approached_for_alcohol
                * 100
            )
            if (
                alcohol["alcohol_cases"] is not None
                and approached_for_alcohol
                and approached_for_alcohol > 0
            )
            else None
        )

        #
        # MEDIDAS ADMINISTRATIVAS
        #
        admin = {
            "fined": summary["fined"],
            "towed": summary["towed"],
            "cnh_collected": summary["cnh_collected"],
            "removal_resolutions": summary[
                "removal_resolutions"
            ],
        }

        #
        # TÁXI
        #
        taxi = {
            "approached": (
                hist_agg.get("taxi_approached")
                if self.use_historical
                else None
            ),

            "illegal": (
                hist_agg.get("taxi_illegal")
                if self.use_historical
                else None
            ),
        }

        #
        # MOTORISTA
        #
        driver = {
            "reconductor": self._sum_nullable(
                hist_agg.get("reconductor"),
                (
                    oper_agg.get("sum_reconductor")
                    if self.use_operational
                    else None
                ),
            ),

            "reconductors_licensed": (
                hist_agg.get(
                    "historical_reconductors_licensed"
                )
                if self.use_historical
                else None
            ),

            "refusal": summary["refusal"],

            "cnh_collected": summary[
                "cnh_collected"
            ],

            "passive_tests_performed": summary[
                "passive_tests_performed"
            ],

            "historical_cnh_retained": (
                hist_agg.get(
                    "historical_cnh_retained"
                )
                if self.use_historical
                else None
            ),

            "historical_passive_tests": (
                hist_agg.get(
                    "historical_passive_tests"
                )
                if self.use_historical
                else None
            ),

            "fake_cnh": driver_extra["fake_cnh"],
            "suspended_cnh": driver_extra["suspended_cnh"],
            "canceled_cnh": driver_extra["canceled_cnh"],
        }

        #
        # ACONTECIMENTOS
        #
        occurrences = {
            "criminal_occurrences": summary[
                "criminal_occurrences"
            ],

            "art307": summary["art307"],

            "driving_canceled_license": summary[
                "driving_canceled_license"
            ],

            "arrests_means_evidence": summary[
                "arrests_means_evidence"
            ],

            "rain": (
                hist_agg.get("rain")
                if self.use_historical
                else None
            ),

            "planned_actions": (
                hist_agg.get("planned_actions")
                if self.use_historical
                else None
            ),

            "external_occurrence": (
                hist_agg.get("external_occurrence")
                if self.use_historical
                else None
            ),

            "public_security_occurrence": (
                hist_agg.get(
                    "public_security_occurrence"
                )
                if self.use_historical
                else None
            ),

            "historical_deliberations": (
                hist_agg.get(
                    "historical_deliberations"
                )
                if self.use_historical
                else None
            ),

            "historical_event_trailers": (
                hist_agg.get(
                    "historical_event_trailers"
                )
                if self.use_historical
                else None
            ),

            "operations": summary["operations"],
        }

        #
        # SÉRIE TEMPORAL
        #
        ts_dict = {}

        for row in hist_ts:
            operation_date = row[
                "operation_date"
            ]

            ts_dict[
                operation_date
            ] = row

        for row in oper_ts:
            operation_date = row[
                "operation_date"
            ]

            if operation_date in ts_dict:
                for key in [
                    "reports",
                    "operations",
                    "approach",
                    "refusal",
                    "fined",
                ]:
                    ts_dict[
                        operation_date
                    ][key] = self._sum_nullable(
                        ts_dict[
                            operation_date
                        ].get(key),
                        row.get(key),
                    )

            else:
                ts_dict[
                    operation_date
                ] = row

        time_series = [
            ts_dict[key]
            for key in sorted(
                ts_dict.keys()
            )
        ]

        for row in time_series:
            if isinstance(
                row["operation_date"],
                date,
            ):
                row[
                    "operation_date"
                ] = row[
                    "operation_date"
                ].isoformat()

        #
        # PRODUÇÃO POR EQUIPE
        #
        tp_dict = {}

        for team, row in hist_tp.items():
            tp_dict[team] = row

        for team, row in oper_tp.items():
            if team in tp_dict:
                for key in [
                    "reports",
                    "operations",
                    "approach",
                    "refusal",
                    "fined",
                    "towed",
                ]:
                    tp_dict[
                        team
                    ][key] = (
                        self._sum_nullable(
                            tp_dict[
                                team
                            ].get(key),
                            row.get(key),
                        )
                    )

            else:
                tp_dict[team] = row

        team_production = list(
            tp_dict.values()
        )

        team_production.sort(
            key=lambda row: (
                -(
                    row.get(
                        "approach"
                    )
                    or 0
                ),
                row.get(
                    "team",
                    "",
                ),
            )
        )

        #
        # COBERTURA
        #
        coverage = {
            "summary.homologated_reports": (
                "CURRENT_ONLY"
            ),

            "summary.operations": "PARTIAL",

            "summary.approach_plus_reconductor": (
                "DIRECT"
                if (
                    self.use_historical
                    ^ self.use_operational
                )
                else "PARTIAL"
            ),

            "alcohol_results.four_ml": "DIRECT",
            "alcohol_results.thirtythree_ml": "DIRECT",
            "alcohol_results.thirtyfour_ml": "DIRECT",

            "taxi.approached": "HISTORICAL_ONLY",
            "taxi.illegal": "HISTORICAL_ONLY",

            "occurrences.rain": "HISTORICAL_ONLY",
            "occurrences.planned_actions": "HISTORICAL_ONLY",
            "occurrences.external_occurrence": "HISTORICAL_ONLY",
            "occurrences.public_security_occurrence": "HISTORICAL_ONLY",
            "occurrences.historical_deliberations": "HISTORICAL_ONLY",
            "occurrences.historical_event_trailers": "HISTORICAL_ONLY",

            "driver.reconductors_licensed": "HISTORICAL_ONLY",
            "driver.historical_cnh_retained": "HISTORICAL_ONLY",
            "driver.historical_passive_tests": "HISTORICAL_ONLY",
        }

        normalized_filters = {
            "date_from": self.filters.get(
                "date_from"
            ),
            "date_to": self.filters.get(
                "date_to"
            ),
            "team": self.filters.get(
                "team"
            ),
        }

        #
        # Um consolidado anual legítimo pode possuir resumo
        # sem possuir série temporal diária.
        #
        has_data = (
            bool(time_series)
            or bool(team_production)
            or (summary.get("homologated_reports") or 0) > 0
            or any(
                value is not None
                for key, value in summary.items()
                if key != "homologated_reports"
            )
        )

        return {
            "filters": normalized_filters,

            "summary": summary,

            "driver": driver,

            "alcohol_results": alcohol,

            "administrative_measures": admin,

            "taxi": taxi,

            "occurrences": occurrences,

            "public_security": public_security,

            "historical_yearly_table": self._get_historical_yearly_table(),

            "team_production": team_production,

            "time_series": time_series,

            "meta": {
                "has_data": has_data,

                "cutoff_date": (
                    INSPECTION_STATISTICS_CUTOFF_DATE
                    .isoformat()
                ),

                "sources_used": sources_used,

                **(
                    {"territorial_coverage": self._calculate_territorial_coverage()}
                    if self.region
                    else {}
                ),
            },

            "coverage": coverage,

            "horus_cards": self._get_horus_card_totals(),
        }


    def _get_horus_card_totals(self):
        operation_qs = InspectionReportOperation.objects.filter(
            report__operation_date__gte=HORUS_OPERATIONAL_CUTOFF_DATE
        )

        operational = operation_qs.aggregate(
            reconductor=Sum("reconductor"),
            four_ml=Sum("four_ml"),
            thirtythree_ml=Sum("thirtythree_ml"),
            thirtyfour_ml=Sum("thirtyfour_ml"),
            passive_tests_performed=Sum("passive_tests_performed"),
            arrests_means_evidence=Sum("arrests_means_evidence"),
            removal_resolutions=Sum("removal_resolutions"),
            art307=Sum("art307"),
            criminal_occurrences=Sum("criminal_occurrences"),
            driving_canceled_license=Sum("driving_canceled_license"),
        )

        result = {}

        for field_name in (
            "reconductor",
            "four_ml",
            "thirtythree_ml",
            "thirtyfour_ml",
            "passive_tests_performed",
            "arrests_means_evidence",
            "removal_resolutions",
            "art307",
            "criminal_occurrences",
            "driving_canceled_license",
        ):
            baseline = HORUS_CARD_BASELINES[field_name]

            result[field_name] = {
                "value": (
                    baseline["value"]
                    + (operational.get(field_name) or 0)
                ),
                "available_from": baseline["available_from"],
                "source": "HORUS",
            }

        stolen_baseline = HORUS_CARD_BASELINES["stolen_recovered_vehicles"]

        result["stolen_recovered_vehicles"] = {
            "value": stolen_baseline["value"],
            "available_from": stolen_baseline.get("available_from"),
            "breakdown": stolen_baseline.get("breakdown", {}),
            "source": "HORUS",
        }

        rain_baseline = HORUS_CARD_BASELINES["rain"]

        result["rain"] = {
            "value": rain_baseline["value"],
            "available_from": rain_baseline["available_from"],
            "source": "HORUS",
        }

        return result

    def _get_public_security_data(self):
        historical_qs = InspectionPublicSecurityYearlyStatistic.objects.all()

        # A serie institucional e anual e nao possui granularidade
        # por equipe ou por dia. Por isso, so utilizamos um ano
        # historico quando todo o periodo consolidado daquele ano
        # estiver coberto pelo filtro.
        if self.team:
            historical_qs = historical_qs.none()
        else:
            covered_years = []

            for year in range(
                2009,
                HISTORICAL_CUTOFF_DATE.year + 1,
            ):
                period_start = date(year, 1, 1)
                period_end = (
                    HISTORICAL_CUTOFF_DATE
                    if year == HISTORICAL_CUTOFF_DATE.year
                    else date(year, 12, 31)
                )

                starts_before_or_on = (
                    self.date_from is None
                    or self.date_from <= period_start
                )

                ends_after_or_on = (
                    self.date_to is None
                    or self.date_to >= period_end
                )

                if starts_before_or_on and ends_after_or_on:
                    covered_years.append(year)

            historical_qs = historical_qs.filter(
                reference_year__in=covered_years
            )

        historical = historical_qs.aggregate(
            fugitives=Sum("fugitives"),
            flagrante=Sum("flagrante"),
            simulacrum=Sum("simulacrum"),
            weapons=Sum("weapons"),
            recovered_vehicles=Sum("recovered_vehicles"),
            narcotics=Sum("narcotics"),
            bribery=Sum("bribery"),
            art311=Sum("art311"),
            art306=Sum("art306"),
            fake_cnh=Sum("fake_cnh"),
            suspended_cnh=Sum("suspended_cnh"),
            canceled_cnh=Sum("canceled_cnh"),
        )

        operational_qs = (
            InspectionStatistic.objects
            .select_related("report")
            .filter(
                operation_date__gte=INSPECTION_STATISTICS_CUTOFF_DATE
            )
        )

        if self.date_from:
            operational_qs = operational_qs.filter(
                operation_date__gte=self.date_from
            )

        if self.date_to:
            operational_qs = operational_qs.filter(
                operation_date__lte=self.date_to
            )

        if self.team:
            operational_qs = operational_qs.filter(
                team__iexact=self.team
            )

        classification_fields = (
            "fugitives",
            "flagrante",
            "simulacrum",
            "weapons",
            "recovered_vehicles",
            "stolen_vehicles",
            "robbed_vehicles",
            "narcotics",
            "bribery",
            "art311",
            "art306",
            "rain",
        )

        operational = {
            field: 0
            for field in classification_fields
        }

        for (
            operation_date,
            classification,
            changes_general,
        ) in operational_qs.values_list(
            "operation_date",
            "report__statistics_classification",
            "report__changes_general",
        ):
            classification = classification or {}

            #
            # As demais classificações continuam utilizando
            # exclusivamente a classificação estruturada registrada
            # na homologação estatística.
            #
            for field in classification_fields:
                if field == "rain":
                    continue

                if classification.get(field) is True:
                    operational[field] += 1

            #
            # CHUVA — regra de transição
            #
            # - 10/08/2026 a 16/08/2026:
            #   identifica chuva nas Observações gerais do relatório,
            #   recuperando a regra anterior do SIED;
            #
            # - a partir de 17/08/2026:
            #   utiliza exclusivamente o campo estruturado "rain"
            #   da Classificação para Estatística.
            #
            if operation_date < RAIN_STRUCTURED_CLASSIFICATION_FROM:
                observation = str(changes_general or "").lower()

                if "chuv" in observation or "chove" in observation:
                    operational["rain"] += 1

            elif classification.get("rain") is True:
                operational["rain"] += 1

        def combined(field):
            historical_value = historical.get(field)
            operational_value = operational.get(field, 0)

            if historical_value is None and operational_value == 0:
                return None

            return (historical_value or 0) + operational_value

        public_security = {
            "fugitives": combined("fugitives"),
            "flagrante": combined("flagrante"),
            "simulacrum": combined("simulacrum"),
            "weapons": combined("weapons"),
            "recovered_vehicles": combined("recovered_vehicles"),
            "stolen_vehicles": (
                HORUS_CARD_BASELINES[
                    "stolen_recovered_vehicles"
                ]["breakdown"]["theft"]
                + operational["stolen_vehicles"]
            ),
            "robbed_vehicles": (
                HORUS_CARD_BASELINES[
                    "stolen_recovered_vehicles"
                ]["breakdown"]["stolen"]
                + operational["robbed_vehicles"]
            ),
            "narcotics": combined("narcotics"),
            "bribery": combined("bribery"),
            "art311": combined("art311"),
            "art306": combined("art306"),
            "rain": operational["rain"],
        }

        public_security["total"] = sum(
            value or 0
            for key, value in public_security.items()
            if key != "rain"
        )

        driver_extra = {
            "fake_cnh": historical.get("fake_cnh"),
            "suspended_cnh": historical.get("suspended_cnh"),
            "canceled_cnh": historical.get("canceled_cnh"),
        }

        return public_security, driver_extra


    def _get_historical_yearly_table(self):
        official_qs = (
            InspectionHistoricalStatistic
            .objects
            .filter(
                reference_date__isnull=True,
                reference_month__isnull=True,
                team="",
            )
            .filter(
                Q(
                    source_type=HistoricalSourceType.LEGACY,
                    taxonomy_era=HistoricalTaxonomyEra.ERA_A,
                )
                | Q(
                    source_type=HistoricalSourceType.ACCUMULATED,
                    taxonomy_era=HistoricalTaxonomyEra.ERA_B,
                )
            )
        )

        historical_rows = list(
            official_qs
            .values("reference_year")
            .annotate(
                operations=Sum("historical_operations"),
                approached=Sum("historical_approached"),
                fined=Sum("fined"),
                towed=Sum("towed"),
                cnh_collected=Sum("historical_cnh_retained"),
                refusal=Sum("refusal"),
                administrative_art_165=Sum("administrative_art_165"),
                criminal_art_306=Sum("criminal_art_306"),
                criminal_art_306_other_evidence=Sum(
                    "criminal_art_306_other_evidence"
                ),
                alcohol_cases=Sum("historical_alcohol_cases"),
                alcohol_percentage=Sum("historical_alcohol_percentage"),
                art307=Sum("historical_art_307"),
            )
            .order_by("reference_year")
        )

        by_year = {}

        for row in historical_rows:
            year = row.pop("reference_year")

            if year is None:
                continue

            row["year"] = year

            approached = row.get("approached") or 0
            alcohol_cases = row.get("alcohol_cases") or 0

            row["alcohol_percentage"] = (
                alcohol_cases / approached * 100
                if approached > 0
                else None
            )

            by_year[year] = row

        operational = (
            InspectionStatistic.objects
            .filter(
                operation_date__gte=INSPECTION_STATISTICS_CUTOFF_DATE,
                operation_date__year=HISTORICAL_CUTOFF_DATE.year,
            )
            .aggregate(
                operations=Sum("operations_count"),
                approached=Sum("approach"),
                fined=Sum("fined"),
                towed=Sum("towed"),
                cnh_collected=Sum("cnh_collected"),
                refusal=Sum("refusal"),
                administrative_art_165=Sum("thirtythree_ml"),
                criminal_art_306=Sum("thirtyfour_ml"),
                criminal_art_306_other_evidence=Sum(
                    "arrests_means_evidence"
                ),
                art307=Sum("art307"),
            )
        )

        operational_alcohol_cases = sum(
            operational.get(field) or 0
            for field in (
                "refusal",
                "administrative_art_165",
                "criminal_art_306",
                "criminal_art_306_other_evidence",
            )
        )

        year_2026 = HISTORICAL_CUTOFF_DATE.year

        base_2026 = by_year.get(
            year_2026,
            {
                "year": year_2026,
                "operations": None,
                "approached": None,
                "fined": None,
                "towed": None,
                "cnh_collected": None,
                "refusal": None,
                "administrative_art_165": None,
                "criminal_art_306": None,
                "criminal_art_306_other_evidence": None,
                "alcohol_cases": None,
                "alcohol_percentage": None,
                "art307": None,
            },
        )

        additive_fields = (
            "operations",
            "approached",
            "fined",
            "towed",
            "cnh_collected",
            "refusal",
            "administrative_art_165",
            "criminal_art_306",
            "criminal_art_306_other_evidence",
            "art307",
        )

        for field in additive_fields:
            historical_value = base_2026.get(field)
            operational_value = operational.get(field)

            if historical_value is None and operational_value is None:
                base_2026[field] = None
            else:
                base_2026[field] = (
                    (historical_value or 0)
                    + (operational_value or 0)
                )

        historical_alcohol_cases = base_2026.get("alcohol_cases")

        if (
            historical_alcohol_cases is None
            and operational_alcohol_cases == 0
        ):
            base_2026["alcohol_cases"] = None
        else:
            base_2026["alcohol_cases"] = (
                (historical_alcohol_cases or 0)
                + operational_alcohol_cases
            )

        approached_2026 = base_2026.get("approached") or 0
        alcohol_cases_2026 = base_2026.get("alcohol_cases") or 0

        if approached_2026 > 0:
            base_2026["alcohol_percentage"] = (
                alcohol_cases_2026
                / approached_2026
                * 100
            )

        by_year[year_2026] = base_2026

        rows = [
            by_year[year]
            for year in sorted(by_year)
            if 2009 <= year <= year_2026
        ]

        total = {
            "operations": 0,
            "approached": 0,
            "fined": 0,
            "towed": 0,
            "cnh_collected": 0,
            "refusal": 0,
            "administrative_art_165": 0,
            "criminal_art_306": 0,
            "criminal_art_306_other_evidence": 0,
            "alcohol_cases": 0,
            "art307": 0,
        }

        for row in rows:
            for field in total:
                total[field] += row.get(field) or 0

        total["alcohol_percentage"] = (
            total["alcohol_cases"] / total["approached"] * 100
            if total["approached"] > 0
            else None
        )

        return {
            "years": [row["year"] for row in rows],
            "rows": rows,
            "total": total,
            "historical_cutoff_date": HISTORICAL_CUTOFF_DATE.isoformat(),
            "operational_start_date": (
                INSPECTION_STATISTICS_CUTOFF_DATE.isoformat()
            ),
        }


    def _get_historical_data(self):
        #
        # ESTATÍSTICA OFICIAL CONSOLIDADA
        # ==========================================================
        #
        # A primeira aba institucional utiliza como fonte oficial:
        #
        # - LEGACY / ERA_A: 2009 a 2022;
        # - ACCUMULATED / ERA_B: 2023 a 09/08/2026.
        #
        # Esses registros são consolidados da planilha institucional,
        # sem equipe e sem granularidade diária.
        #
        # EXCEÇÃO — CHUVA:
        #
        # O indicador de chuva utiliza o histórico diário do Horus
        # (DAILY / ERA_C), disponível de 03/10/2022 a 09/08/2026.
        #
        # Isso permite que chuva acompanhe corretamente os filtros
        # de período e equipe, sem alterar a origem dos demais
        # indicadores oficiais.
        #
        official_qs = (
            InspectionHistoricalStatistic
            .objects
            .filter(
                reference_date__isnull=True,
                reference_month__isnull=True,
                team="",
            )
            .filter(
                Q(
                    source_type=HistoricalSourceType.LEGACY,
                    taxonomy_era=HistoricalTaxonomyEra.ERA_A,
                )
                | Q(
                    source_type=HistoricalSourceType.ACCUMULATED,
                    taxonomy_era=HistoricalTaxonomyEra.ERA_B,
                )
            )
        )

        #
        # A planilha oficial é consolidada por ano.
        #
        # Um ano somente participa do total quando o filtro cobre
        # integralmente o período oficial disponível daquele ano.
        #
        # Não distribuímos artificialmente totais anuais por
        # dias ou meses.
        #
        # Para 2026, o período histórico oficial termina
        # em 09/08/2026.
        #
        if self.team:
            official_qs = official_qs.none()

        else:
            covered_years = []

            for year in range(
                2009,
                HISTORICAL_CUTOFF_DATE.year + 1,
            ):
                period_start = date(
                    year,
                    1,
                    1,
                )

                period_end = (
                    HISTORICAL_CUTOFF_DATE
                    if year == HISTORICAL_CUTOFF_DATE.year
                    else date(
                        year,
                        12,
                        31,
                    )
                )

                starts_before_or_on = (
                    self.date_from is None
                    or self.date_from <= period_start
                )

                ends_after_or_on = (
                    self.date_to is None
                    or self.date_to >= period_end
                )

                if (
                    starts_before_or_on
                    and ends_after_or_on
                ):
                    covered_years.append(
                        year
                    )

            official_qs = official_qs.filter(
                reference_year__in=covered_years
            )

        #
        # CONSOLIDADO OFICIAL
        # ==========================================================
        #
        # Todos os indicadores abaixo continuam vindo
        # exclusivamente da planilha institucional consolidada.
        #
        # Chuva NÃO é agregada aqui.
        #
        agg = official_qs.aggregate(
            approach=Sum(
                "historical_approached"
            ),

            refusal=Sum(
                "refusal"
            ),

            fined=Sum(
                "fined"
            ),

            towed=Sum(
                "towed"
            ),

            #
            # Na planilha histórica, "CNH" corresponde a
            # "CNH Recolhidas" no SIED.
            #
            cnh_collected=Sum(
                "historical_cnh_retained"
            ),

            passive_tests_performed=Sum(
                "historical_passive_tests"
            ),

            removal_resolutions=Sum(
                "removal_resolutions"
            ),

            arrests_means_evidence=Sum(
                "arrests_means_evidence"
            ),

            four_ml=Sum(
                "four_ml"
            ),

            thirtythree_ml=Sum(
                "thirtythree_ml"
            ),

            thirtyfour_ml=Sum(
                "thirtyfour_ml"
            ),

            taxi_approached=Sum(
                "taxi_approached"
            ),

            taxi_illegal=Sum(
                "taxi_illegal"
            ),

            planned_actions=Sum(
                "planned_actions"
            ),

            external_occurrence=Sum(
                "external_occurrence"
            ),

            public_security_occurrence=Sum(
                "public_security_occurrence"
            ),

            historical_reconductors_licensed=Sum(
                "historical_reconductors_licensed"
            ),

            historical_deliberations=Sum(
                "historical_deliberations"
            ),

            historical_cnh_retained=Sum(
                "historical_cnh_retained"
            ),

            historical_passive_tests=Sum(
                "historical_passive_tests"
            ),

            historical_event_trailers=Sum(
                "historical_event_trailers"
            ),

            negative_tests=Sum(
                "negative_tests"
            ),

            historical_alcohol_cases=Sum(
                "historical_alcohol_cases"
            ),

            criminal_art_306=Sum(
                "criminal_art_306"
            ),

            criminal_art_306_other_evidence=Sum(
                "criminal_art_306_other_evidence"
            ),

            operations=Sum(
                "historical_operations"
            ),

            driving_canceled_license=Sum(
                "driving_canceled_license"
            ),

            art307=Sum(
                "historical_art_307"
            ),
        )

        #
        # CHUVA HISTÓRICA — HORUS DAILY / ERA_C
        # ==========================================================
        #
        # Disponibilidade histórica confirmada:
        # 03/10/2022 a 09/08/2026.
        #
        # O filtro é aplicado diretamente na granularidade
        # data + equipe do Horus.
        #
        rain_available_from = date(
            2022,
            10,
            3,
        )

        daily_qs = (
            InspectionHistoricalStatistic
            .objects
            .filter(
                source_type=HistoricalSourceType.DAILY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_C,
                is_validation_only=False,
                reference_date__isnull=False,
                reference_date__gte=rain_available_from,
                reference_date__lte=HISTORICAL_CUTOFF_DATE,
            )
        )

        if self.date_from:
            effective_date_from = max(
                self.date_from,
                rain_available_from,
            )

            daily_qs = daily_qs.filter(
                reference_date__gte=effective_date_from
            )

        if self.date_to:
            effective_date_to = min(
                self.date_to,
                HISTORICAL_CUTOFF_DATE,
            )

            daily_qs = daily_qs.filter(
                reference_date__lte=effective_date_to
            )

        if self.team:
            daily_qs = daily_qs.filter(
                team__iexact=self.team
            )

        rain_aggregate = daily_qs.aggregate(
            total=Sum(
                "rain"
            )
        )

        if 'covered_years' not in locals():
            covered_years = []
        covered_years = locals().get("covered_years", [])

        partial_daily_qs = daily_qs.exclude(reference_date__year__in=covered_years)
        partial_aggregate = partial_daily_qs.aggregate(
            approach=Sum("historical_approached"),
            refusal=Sum("refusal"),
            fined=Sum("fined"),
            towed=Sum("towed"),
            cnh_collected=Sum("historical_cnh_retained"),
            passive_tests_performed=Sum("historical_passive_tests"),
            removal_resolutions=Sum("removal_resolutions"),
            arrests_means_evidence=Sum("arrests_means_evidence"),
            four_ml=Sum("four_ml"),
            thirtythree_ml=Sum("thirtythree_ml"),
            thirtyfour_ml=Sum("thirtyfour_ml"),
            taxi_approached=Sum("taxi_approached"),
            taxi_illegal=Sum("taxi_illegal"),
            planned_actions=Sum("planned_actions"),
            external_occurrence=Sum("external_occurrence"),
            public_security_occurrence=Sum("public_security_occurrence"),
            historical_reconductors_licensed=Sum("historical_reconductors_licensed"),
            historical_deliberations=Sum("historical_deliberations"),
            historical_cnh_retained=Sum("historical_cnh_retained"),
            historical_passive_tests=Sum("historical_passive_tests"),
            historical_event_trailers=Sum("historical_event_trailers"),
            negative_tests=Sum("negative_tests"),
            historical_alcohol_cases=Sum("historical_alcohol_cases"),
            criminal_art_306=Sum("criminal_art_306"),
            criminal_art_306_other_evidence=Sum("criminal_art_306_other_evidence"),
            operations=Sum("historical_operations"),
            driving_canceled_license=Sum("driving_canceled_license"),
            art307=Sum("historical_art_307"),
        )

        has_partial_data = False
        for k, v in partial_aggregate.items():
            if v is not None:
                has_partial_data = True
                agg[k] = (agg.get(k) or 0) + v


        #
        # Fora da cobertura histórica de chuva, retornamos None.
        # Dentro da cobertura, sem ocorrência positiva, retornamos 0.
        #
        rain_period_start = (
            self.date_from
            if self.date_from
            else rain_available_from
        )

        rain_period_end = (
            self.date_to
            if self.date_to
            else HISTORICAL_CUTOFF_DATE
        )

        rain_has_overlap = (
            rain_period_start <= HISTORICAL_CUTOFF_DATE
            and rain_period_end >= rain_available_from
        )

        if rain_has_overlap:
            agg["rain"] = (
                rain_aggregate.get("total")
                if rain_aggregate.get("total") is not None
                else 0
            )
        else:
            agg["rain"] = None

        criminal_art_306 = agg.pop(
            "criminal_art_306",
            None,
        )

        criminal_other = agg.pop(
            "criminal_art_306_other_evidence",
            None,
        )

        agg["criminal_occurrences"] = (
            self._sum_nullable(
                criminal_art_306,
                criminal_other,
            )
        )

        # A série oficial consolidada não possui recondutor equivalente
        # nem permite construir "Abordados + Recondutor" de forma segura.
        agg["reconductor"] = None
        agg["approach_plus_reconductor"] = None

        #
        # SÉRIE TEMPORAL OFICIAL
        # ==========================================================
        #
        # Como a fonte institucional é anual, cada ponto representa
        # o encerramento do período oficial daquele ano.
        # Em 2026, o ponto termina em 09/08/2026.
        #
        hist_ts = []

        yearly_rows = list(
            official_qs
            .values(
                "reference_year"
            )
            .annotate(
                approach=Sum(
                    "historical_approached"
                ),
                refusal=Sum(
                    "refusal"
                ),
                fined=Sum(
                    "fined"
                ),
                operations=Sum(
                    "historical_operations"
                ),
            )
            .order_by(
                "reference_year"
            )
        )

        for row in yearly_rows:
            year = row.pop(
                "reference_year"
            )

            row["operation_date"] = (
                HISTORICAL_CUTOFF_DATE
                if year == HISTORICAL_CUTOFF_DATE.year
                else date(
                    year,
                    12,
                    31,
                )
            )

            hist_ts.append(
                row
            )

        # O consolidado institucional não possui dimensão por equipe.
        # A única exceção nesta função é chuva, consultada diretamente
        # no Horus DAILY / ERA_C. Não alteramos team_production para
        # evitar misturar metodologias diferentes na tabela institucional.
        hist_tp = {}

        return (
            agg,
            hist_ts,
            hist_tp,
        )


    def _get_operational_data(self):
        qs = InspectionStatistic.objects.all()

        if self.date_from:
            qs = qs.filter(
                operation_date__gte=self.date_from
            )

        if self.date_to:
            qs = qs.filter(
                operation_date__lte=self.date_to
            )

        if self.team:
            qs = qs.filter(
                team__iexact=self.team
            )

        agg = qs.aggregate(
            homologated_reports=Count(
                "id"
            ),

            operations=Sum(
                "operations_count"
            ),

            sum_approach=Sum(
                "approach"
            ),

            sum_reconductor=Sum(
                "reconductor"
            ),

            approach_plus_reconductor=Sum(
                Coalesce(
                    "approach",
                    Value(0),
                )
                + Coalesce(
                    "reconductor",
                    Value(0),
                )
            ),

            refusal=Sum(
                "refusal"
            ),

            fined=Sum(
                "fined"
            ),

            towed=Sum(
                "towed"
            ),

            cnh_collected=Sum(
                "cnh_collected"
            ),

            passive_tests_performed=Sum(
                "passive_tests_performed"
            ),

            removal_resolutions=Sum(
                "removal_resolutions"
            ),

            criminal_occurrences=Sum(
                "criminal_occurrences"
            ),

            art307=Sum(
                "art307"
            ),

            driving_canceled_license=Sum(
                "driving_canceled_license"
            ),

            arrests_means_evidence=Sum(
                "arrests_means_evidence"
            ),

            celebrities_authorities=Sum(
                "celebrities_authorities"
            ),

            four_ml=Sum(
                "four_ml"
            ),

            thirtythree_ml=Sum(
                "thirtythree_ml"
            ),

            thirtyfour_ml=Sum(
                "thirtyfour_ml"
            ),
        )

        oper_ts = list(
            qs
            .values(
                "operation_date"
            )
            .annotate(
                reports=Count(
                    "id"
                ),

                operations=Sum(
                    "operations_count"
                ),

                approach=Sum(
                    "approach"
                ),

                refusal=Sum(
                    "refusal"
                ),

                fined=Sum(
                    "fined"
                ),
            )
            .order_by(
                "operation_date"
            )
        )

        oper_tp_qs = list(
            qs
            .values(
                "team"
            )
            .annotate(
                reports=Count(
                    "id"
                ),

                operations=Sum(
                    "operations_count"
                ),

                approach=Sum(
                    "approach"
                ),

                refusal=Sum(
                    "refusal"
                ),

                fined=Sum(
                    "fined"
                ),

                towed=Sum(
                    "towed"
                ),
            )
        )

        oper_tp = {
            row["team"]: row
            for row in oper_tp_qs
        }

        return (
            agg,
            oper_ts,
            oper_tp,
        )
    def _get_territorial_historical_data(self):
        from apps.inspection.models import InspectionHistoricalTerritorialStatistic
        from django.db.models import Sum, Value
        from django.db.models.functions import Coalesce

        hist_agg = {}
        hist_ts = []
        hist_tp = {}

        if self.date_from and self.date_from > HISTORICAL_CUTOFF_DATE:
            return hist_agg, hist_ts, hist_tp

        qs = InspectionHistoricalTerritorialStatistic.objects.all()

        if self.date_from:
            qs = qs.filter(reference_date__gte=self.date_from)

        if self.date_to:
            effective_date_to = min(self.date_to, HISTORICAL_CUTOFF_DATE)
            qs = qs.filter(reference_date__lte=effective_date_to)
        else:
            qs = qs.filter(reference_date__lte=HISTORICAL_CUTOFF_DATE)

        if self.team:
            qs = qs.filter(team__iexact=self.team)

        if self.region:
            qs = qs.filter(region__name__iexact=self.region)

        agg = qs.aggregate(
            operations=Sum("operations_count"),
            approach=Sum("approach"),
            reconductor=Sum("reconductor"),
            refusal=Sum("refusal"),
            fined=Sum("fined"),
            towed=Sum("towed"),
            cnh_collected=Sum("cnh_collected"),
            four_ml=Sum("four_ml"),
            thirtythree_ml=Sum("thirtythree_ml"),
            thirtyfour_ml=Sum("thirtyfour_ml"),
            passive_tests_performed=Sum("passive_tests_performed"),
            removal_resolutions=Sum("removal_resolutions"),
            arrests_means_evidence=Sum("arrests_means_evidence"),
            art307=Sum("art307"),
            criminal_occurrences=Sum("criminal_occurrences"),
            driving_canceled_license=Sum("driving_canceled_license"),

        )

        for key, val in agg.items():
            hist_agg[key] = val

        hist_agg["rain"] = None

        hist_agg["approach_plus_reconductor"] = self._sum_nullable(
            hist_agg.get("approach"), hist_agg.get("reconductor")
        )

        # Yearly aggregation for TS
        yearly_rows = list(
            qs.values("reference_date__year").annotate(
                operations=Sum("operations_count"),
                approach=Sum("approach"),
                refusal=Sum("refusal"),
                fined=Sum("fined")
            ).order_by("reference_date__year")
        )

        for row in yearly_rows:
            year = row.pop("reference_date__year")
            row["operation_date"] = (
                HISTORICAL_CUTOFF_DATE if year == HISTORICAL_CUTOFF_DATE.year else date(year, 12, 31)
            )
            hist_ts.append(row)

        return hist_agg, hist_ts, hist_tp

    def _get_territorial_operational_data(self):
        from apps.inspection.models import InspectionReportOperation
        from apps.inspection.territorial import resolve_territory
        from django.db.models import Sum, Count, Value
        from django.db.models.functions import Coalesce

        oper_agg = {}
        oper_ts = []
        oper_tp = {}

        if self.date_to and self.date_to <= HISTORICAL_CUTOFF_DATE:
            return oper_agg, oper_ts, oper_tp

        qs = InspectionReportOperation.objects.filter(report__official_statistic__isnull=False)

        if self.date_from:
            qs = qs.filter(report__operation_date__gte=self.date_from)
        else:
            qs = qs.filter(report__operation_date__gt=HISTORICAL_CUTOFF_DATE)

        if self.date_to:
            qs = qs.filter(report__operation_date__lte=self.date_to)

        if self.team:
            qs = qs.filter(report__team__iexact=self.team)

        # Need to fetch and filter in Python because city is string
        # To optimize, we can use an exact match on city if we pre-resolve
        operations = list(qs.select_related('report'))

        filtered_operations = []
        for op in operations:
            territory = resolve_territory(op.city)
            if territory["region"] and territory["region"].lower() == self.region.lower():
                filtered_operations.append(op)

        # Aggregate manually
        ops_count = len(filtered_operations)
        reports_set = set()

        for op in filtered_operations:
            reports_set.add(op.report_id)
            for k in ["approach", "reconductor", "refusal", "fined", "towed", "cnh_collected", "four_ml", "thirtythree_ml", "thirtyfour_ml", "passive_tests_performed", "removal_resolutions", "arrests_means_evidence", "art307", "criminal_occurrences", "driving_canceled_license", "celebrities_authorities"]:
                val = getattr(op, k) or 0
                oper_agg[k] = (oper_agg.get(k) or 0) + val

        oper_agg["operations"] = ops_count
        oper_agg["homologated_reports"] = len(reports_set)
        oper_agg["sum_approach"] = oper_agg.get("approach", 0)
        oper_agg["sum_reconductor"] = oper_agg.get("reconductor", 0)
        oper_agg["approach_plus_reconductor"] = (oper_agg.get("approach") or 0) + (oper_agg.get("reconductor") or 0)

        # Build oper_ts
        ts_dict = {}
        tp_dict = {}
        for op in filtered_operations:
            d = op.report.operation_date
            if d not in ts_dict:
                ts_dict[d] = {"operation_date": d, "operations": 0, "approach": 0, "refusal": 0, "fined": 0}
            ts_dict[d]["operations"] += 1
            ts_dict[d]["approach"] += (op.approach or 0)
            ts_dict[d]["refusal"] += (op.refusal or 0)
            ts_dict[d]["fined"] += (op.fined or 0)

            t = op.report.team
            if t not in tp_dict:
                tp_dict[t] = {"team": t, "operations": 0, "approach": 0, "refusal": 0, "fined": 0, "towed": 0}
            tp_dict[t]["operations"] += 1
            tp_dict[t]["approach"] += (op.approach or 0)
            tp_dict[t]["refusal"] += (op.refusal or 0)
            tp_dict[t]["fined"] += (op.fined or 0)
            tp_dict[t]["towed"] += (op.towed or 0)

        oper_ts = sorted(ts_dict.values(), key=lambda x: x["operation_date"])
        oper_tp = tp_dict

        return oper_agg, oper_ts, oper_tp

    def _calculate_territorial_coverage(self):
        from apps.inspection.models import InspectionHistoricalTerritorialStatistic
        from django.db.models import Sum

        qs = InspectionHistoricalTerritorialStatistic.objects.all()

        if self.date_from:
            qs = qs.filter(reference_date__gte=self.date_from)

        if self.date_to:
            effective_date_to = min(self.date_to, HISTORICAL_CUTOFF_DATE)
            qs = qs.filter(reference_date__lte=effective_date_to)
        else:
            qs = qs.filter(reference_date__lte=HISTORICAL_CUTOFF_DATE)

        if self.team:
            qs = qs.filter(team__iexact=self.team)

        total_agg = qs.aggregate(
            operations=Sum("operations_count"),
            approach=Sum("approach")
        )

        classified_qs = qs.filter(region__isnull=False)
        class_agg = classified_qs.aggregate(
            operations=Sum("operations_count"),
            approach=Sum("approach")
        )

        t_ops = total_agg["operations"] or 0
        c_ops = class_agg["operations"] or 0
        u_ops = t_ops - c_ops

        t_app = total_agg["approach"] or 0
        c_app = class_agg["approach"] or 0
        u_app = t_app - c_app

        pct_ops = (c_ops / t_ops * 100) if t_ops > 0 else 0
        pct_app = (c_app / t_app * 100) if t_app > 0 else 0

        return {
            "operations": {
                "classified": c_ops,
                "unclassified": u_ops,
                "total": t_ops,
                "classified_percentage": round(pct_ops, 1)
            },
            "approach": {
                "classified": c_app,
                "unclassified": u_app,
                "total": t_app,
                "classified_percentage": round(pct_app, 1)
            }
        }
