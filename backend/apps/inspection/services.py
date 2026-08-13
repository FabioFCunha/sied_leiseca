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



from django.db.models import Count, Sum, Value, F
from django.db.models.functions import Coalesce

from apps.inspection.models import (
    HistoricalSourceType,
    HistoricalTaxonomyEra,
    InspectionHistoricalStatistic,
    INSPECTION_STATISTICS_CUTOFF_DATE,
)


class InspectionStatisticsUnifiedService:
    def __init__(self, filters):
        self.filters = filters

        self.date_from = (
            date.fromisoformat(filters["date_from"])
            if filters.get("date_from")
            else None
        )

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
        hist_agg, hist_ts, hist_tp = (
            self._get_historical_data()
            if self.use_historical
            else ({}, [], {})
        )

        oper_agg, oper_ts, oper_tp = (
            self._get_operational_data()
            if self.use_operational
            else ({}, [], {})
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

            "team_production": team_production,

            "time_series": time_series,

            "meta": {
                "has_data": has_data,

                "cutoff_date": (
                    INSPECTION_STATISTICS_CUTOFF_DATE
                    .isoformat()
                ),

                "sources_used": sources_used,
            },

            "coverage": coverage,
        }

    def _get_historical_data(self):
        #
        # HISTÓRICO COM DUAS GRANULARIDADES
        #
        # 1) DAILY / ERA_C:
        #    dados diários oficiais do Horus, com data e equipe.
        #
        # 2) LEGACY / ERA_A:
        #    consolidado anual anterior a 2023, sem data diária
        #    e sem equipe.
        #

        daily_qs = (
            InspectionHistoricalStatistic
            .objects
            .filter(
                reference_date__isnull=False,
                source_type=HistoricalSourceType.DAILY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_C,
            )
        )

        if self.date_from:
            daily_qs = daily_qs.filter(
                reference_date__gte=self.date_from
            )

        if self.date_to:
            daily_qs = daily_qs.filter(
                reference_date__lte=self.date_to
            )

        if self.team:
            daily_qs = daily_qs.filter(
                team__iexact=self.team
            )

        #
        # CONSOLIDADO ANUAL LEGACY / ERA_A
        #
        annual_qs = (
            InspectionHistoricalStatistic
            .objects
            .filter(
                source_type=HistoricalSourceType.LEGACY,
                taxonomy_era=HistoricalTaxonomyEra.ERA_A,
                reference_date__isnull=True,
                reference_month__isnull=True,
            )
        )

        #
        # O consolidado anual não possui equipe.
        #
        if self.team:
            annual_qs = annual_qs.none()

        else:
            first_full_year = 1
            last_full_year = 9999

            #
            # Um ano inicial só entra se o filtro começar
            # exatamente em 01/01.
            #
            if self.date_from:
                first_full_year = self.date_from.year

                if (
                    self.date_from.month != 1
                    or self.date_from.day != 1
                ):
                    first_full_year += 1

            #
            # Um ano final só entra se o filtro terminar
            # exatamente em 31/12.
            #
            if self.date_to:
                last_full_year = self.date_to.year

                if (
                    self.date_to.month != 12
                    or self.date_to.day != 31
                ):
                    last_full_year -= 1

            if first_full_year <= last_full_year:
                annual_qs = annual_qs.filter(
                    reference_year__gte=first_full_year,
                    reference_year__lte=last_full_year,
                )

            else:
                annual_qs = annual_qs.none()

        #
        # ==========================================================
        # HISTÓRICO DIÁRIO HORUS / ERA_C
        # ==========================================================
        #
        # Aqui os indicadores possuem equivalência direta com
        # os campos extraídos do Horus.
        #
        daily_agg = daily_qs.aggregate(
            approach=Sum(
                "historical_approached"
            ),

            reconductor=Sum(
                "reconductor"
            ),

            #
            # ATENÇÃO: approach_plus_reconductor NÃO é calculado
            # aqui no aggregate porque o Django 5.x resolve
            # Coalesce('reconductor') dentro de Sum() como o alias
            # do agregado 'reconductor', causando FieldError.
            # É calculado via Python logo abaixo.
            #

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

            criminal_occurrences=Sum(
                "criminal_occurrences"
            ),

            art307=Sum(
                "historical_art_307"
            ),

            driving_canceled_license=Sum(
                "driving_canceled_license"
            ),

            operations=Sum(
                "historical_operations"
            ),

            #
            # Campos existentes somente em outras fontes históricas.
            #
            taxi_approached=Sum(
                "taxi_approached"
            ),

            taxi_illegal=Sum(
                "taxi_illegal"
            ),

            rain=Sum(
                "rain"
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
        )

        #
        # approach_plus_reconductor calculado via Python para evitar
        # conflito de nomes no aggregate do Django 5.x.
        #
        daily_approach = daily_agg.get("approach")
        daily_reconductor = daily_agg.get("reconductor")
        daily_agg["approach_plus_reconductor"] = self._sum_nullable(
            daily_approach, daily_reconductor
        )

        #
        # ==========================================================
        # CONSOLIDADO ANUAL LEGACY / ERA_A
        # ==========================================================
        #
        annual_agg = annual_qs.aggregate(
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

            cnh_collected=Sum(
                "cnh_collected"
            ),

            passive_tests_performed=Sum(
                "passive_tests_performed"
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

            rain=Sum(
                "rain"
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
        # No legado, ocorrência criminal é derivada dos dois
        # indicadores disponíveis na fonte antiga.
        #
        criminal_art_306 = annual_agg.pop(
            "criminal_art_306",
            None,
        )

        criminal_other = annual_agg.pop(
            "criminal_art_306_other_evidence",
            None,
        )

        annual_agg[
            "criminal_occurrences"
        ] = self._sum_nullable(
            criminal_art_306,
            criminal_other,
        )

        #
        # O LEGACY anual não possui recondutor equivalente.
        #
        annual_agg["reconductor"] = None

        #
        # Também não existe equivalência segura para
        # "Abordados + Recondutor" no LEGACY.
        #
        annual_agg[
            "approach_plus_reconductor"
        ] = None

        #
        # ==========================================================
        # UNIFICAÇÃO DOS DOIS HISTÓRICOS
        # ==========================================================
        #
        agg = {}

        aggregate_keys = (
            set(daily_agg.keys())
            | set(annual_agg.keys())
        )

        for key in aggregate_keys:
            agg[key] = self._sum_nullable(
                daily_agg.get(key),
                annual_agg.get(key),
            )

        #
        # Se o período selecionado mistura DAILY/Horus e
        # LEGACY anual, não mostramos Abordados + Recondutor,
        # porque uma parte da série não possui recondutor
        # equivalente.
        #
        has_daily = daily_qs.exists()
        has_annual = annual_qs.exists()

        if has_daily and has_annual:
            agg[
                "approach_plus_reconductor"
            ] = None

        #
        # ==========================================================
        # SÉRIE TEMPORAL
        # ==========================================================
        #
        # Apenas o histórico diário possui granularidade legítima
        # para compor uma série por data.
        #
        hist_ts = list(
            daily_qs
            .values(
                "reference_date"
            )
            .annotate(
                operation_date=F(
                    "reference_date"
                ),

                approach=Sum(
                    "historical_approached"
                ),

                reconductor=Sum(
                    "reconductor"
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
                "reference_date"
            )
        )

        for row in hist_ts:
            del row[
                "reference_date"
            ]

        #
        # ==========================================================
        # PRODUÇÃO POR EQUIPE
        # ==========================================================
        #
        # Também somente DAILY / ERA_C, pois o LEGACY anual
        # não possui equipe.
        #
        hist_tp_qs = list(
            daily_qs
            .values(
                "team"
            )
            .annotate(
                approach=Sum(
                    "historical_approached"
                ),

                reconductor=Sum(
                    "reconductor"
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

                operations=Sum(
                    "historical_operations"
                ),
            )
        )

        hist_tp = {
            row["team"]: row
            for row in hist_tp_qs
        }

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