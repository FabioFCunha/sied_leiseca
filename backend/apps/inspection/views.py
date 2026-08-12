from django.db.models import Count, Prefetch, Sum
from rest_framework import decorators, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inspection.models import InspectionReport, InspectionReportOperation, InspectionStatistic
from apps.inspection.permissions import (
    CanReviewInspectionStatistics,
    CanViewInspectionStatisticsDashboard,
    HasInspectionSyncToken,
)
from apps.inspection.serializers import (
    InspectionExcludeStatisticsSerializer,
    InspectionStatisticsDashboardQuerySerializer,
    InspectionReportDetailSerializer,
    InspectionReportIngestionSerializer,
    InspectionReportListSerializer,
)
from apps.inspection.services import InspectionStatisticsService, InspectionSyncService


SUMMARY_FIELDS = (
    "approach",
    "reconductor",
    "refusal",
    "fined",
    "towed",
    "cnh_collected",
    "passive_tests_performed",
    "four_ml",
    "thirtythree_ml",
    "thirtyfour_ml",
    "removal_resolutions",
    "criminal_occurrences",
    "art307",
    "driving_canceled_license",
    "arrests_means_evidence",
    "celebrities_authorities",
)


def _empty_dashboard(filters):
    return {
        "filters": filters,
        "summary": {
            "homologated_reports": 0,
            "operations": 0,
            **{field: None for field in SUMMARY_FIELDS},
        },
        "alcohol_results": {
            "four_ml": None,
            "thirtythree_ml": None,
            "thirtyfour_ml": None,
            "refusal": None,
        },
        "administrative_measures": {
            "fined": None,
            "towed": None,
            "cnh_collected": None,
            "removal_resolutions": None,
        },
        "occurrences": {
            "criminal_occurrences": None,
            "art307": None,
            "driving_canceled_license": None,
            "arrests_means_evidence": None,
        },
        "team_production": [],
        "time_series": [],
        "meta": {
            "has_data": False,
            "cutoff_date": "2026-08-10",
            "null_aggregation_rule": (
                "Sem registros homologados no filtro, os indicadores retornam null. "
                "Com registros homologados, a API consolida SUM ignorando NULL e expõe 0 quando a soma agregada ficar vazia."
            ),
        },
    }


class InspectionReportSyncView(APIView):
    authentication_classes = []
    permission_classes = [HasInspectionSyncToken]

    def post(self, request):
        serializer = InspectionReportIngestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = InspectionSyncService().sync_report(serializer.validated_data)
        status_code = status.HTTP_201_CREATED if result.outcome == "created" else status.HTTP_200_OK
        return Response(
            {
                "result": result.outcome,
                "detail": result.detail,
                "report_id": result.report.id,
                "source_id": str(result.report.source_id),
                "status": result.report.status,
                "statistics_status": result.report.statistics_status,
            },
            status=status_code,
        )


class InspectionReportViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    ordering_fields = [
        "operation_date",
        "synced_at",
        "status",
        "statistics_status",
        "statistics_reviewed_at",
        "team",
        "created_at",
        "updated_at",
    ]

    def get_permissions(self):
        if self.action in {"include_in_statistics", "exclude_from_statistics"}:
            return [CanReviewInspectionStatistics()]
        return [permission() for permission in self.permission_classes]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return InspectionReportDetailSerializer
        return InspectionReportListSerializer

    def get_queryset(self):
        queryset = InspectionReport.objects.select_related("statistics_reviewed_by")

        if self.action == "retrieve":
            return queryset.prefetch_related(
                Prefetch(
                    "operations",
                    queryset=InspectionReportOperation.objects.prefetch_related("fines").order_by("id"),
                ),
                "statistics_history__changed_by",
            )

        queryset = queryset.annotate(
            operation_count=Count("operations", distinct=True),
            total_approach=Sum("operations__approach"),
            total_refusal=Sum("operations__refusal"),
            total_fined=Sum("operations__fined"),
        )

        params = self.request.query_params
        if params.get("date_from"):
            queryset = queryset.filter(operation_date__gte=params["date_from"])
        if params.get("date_to"):
            queryset = queryset.filter(operation_date__lte=params["date_to"])
        if params.get("team"):
            queryset = queryset.filter(team__iexact=params["team"].strip())
        if params.get("status"):
            queryset = queryset.filter(status=params["status"].strip())
        if params.get("statistics_status"):
            queryset = queryset.filter(statistics_status=params["statistics_status"].strip())
        if params.get("q"):
            queryset = queryset.filter(team__icontains=params["q"].strip())

        ordering = params.get("ordering", "").strip()
        allowed = set(self.ordering_fields + [f"-{field}" for field in self.ordering_fields])
        if ordering and ordering in allowed:
            return queryset.order_by(ordering, "-created_at")

        return queryset.order_by("-operation_date", "-created_at")

    @decorators.action(detail=True, methods=["post"], url_path="include-in-statistics")
    def include_in_statistics(self, request, pk=None):
        report = self.get_object()
        result = InspectionStatisticsService().include_report(report.id, user=request.user)
        serializer = InspectionReportDetailSerializer(result.report, context={"request": request})
        return Response(
            {
                "result": result.outcome,
                "detail": result.detail,
                "report": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @decorators.action(detail=True, methods=["post"], url_path="exclude-from-statistics")
    def exclude_from_statistics(self, request, pk=None):
        serializer = InspectionExcludeStatisticsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = self.get_object()
        result = InspectionStatisticsService().exclude_report(
            report.id,
            user=request.user,
            reason=serializer.validated_data["reason"],
        )
        report_serializer = InspectionReportDetailSerializer(result.report, context={"request": request})
        return Response(
            {
                "result": result.outcome,
                "detail": result.detail,
                "report": report_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class InspectionStatisticsDashboardView(APIView):
    permission_classes = [CanViewInspectionStatisticsDashboard]

    def get(self, request):
        serializer = InspectionStatisticsDashboardQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        queryset = InspectionStatistic.objects.all()
        if filters.get("date_from"):
            queryset = queryset.filter(operation_date__gte=filters["date_from"])
        if filters.get("date_to"):
            queryset = queryset.filter(operation_date__lte=filters["date_to"])
        if filters.get("team"):
            queryset = queryset.filter(team__iexact=filters["team"])

        normalized_filters = {
            "date_from": filters.get("date_from").isoformat() if filters.get("date_from") else None,
            "date_to": filters.get("date_to").isoformat() if filters.get("date_to") else None,
            "team": filters.get("team") or None,
        }

        if not queryset.exists():
            return Response(_empty_dashboard(normalized_filters))

        aggregate_data = queryset.aggregate(
            homologated_reports=Count("id"),
            operations=Sum("operations_count"),
            **{field: Sum(field) for field in SUMMARY_FIELDS},
        )

        team_production = list(
            queryset.values("team")
            .annotate(
                reports=Count("id"),
                operations=Sum("operations_count"),
                approach=Sum("approach"),
                refusal=Sum("refusal"),
                fined=Sum("fined"),
                towed=Sum("towed"),
            )
            .order_by("-approach", "team")
        )

        time_series = list(
            queryset.values("operation_date")
            .annotate(
                reports=Count("id"),
                operations=Sum("operations_count"),
                approach=Sum("approach"),
                refusal=Sum("refusal"),
                fined=Sum("fined"),
            )
            .order_by("operation_date")
        )
        for row in time_series:
            row["operation_date"] = row["operation_date"].isoformat()

        return Response(
            {
                "filters": normalized_filters,
                "summary": aggregate_data,
                "alcohol_results": {
                    "four_ml": aggregate_data["four_ml"],
                    "thirtythree_ml": aggregate_data["thirtythree_ml"],
                    "thirtyfour_ml": aggregate_data["thirtyfour_ml"],
                    "refusal": aggregate_data["refusal"],
                },
                "administrative_measures": {
                    "fined": aggregate_data["fined"],
                    "towed": aggregate_data["towed"],
                    "cnh_collected": aggregate_data["cnh_collected"],
                    "removal_resolutions": aggregate_data["removal_resolutions"],
                },
                "occurrences": {
                    "criminal_occurrences": aggregate_data["criminal_occurrences"],
                    "art307": aggregate_data["art307"],
                    "driving_canceled_license": aggregate_data["driving_canceled_license"],
                    "arrests_means_evidence": aggregate_data["arrests_means_evidence"],
                },
                "team_production": team_production,
                "time_series": time_series,
                "meta": {
                    "has_data": True,
                    "cutoff_date": "2026-08-10",
                    "null_aggregation_rule": (
                        "Com registros homologados, a API consolida SUM ignorando NULL. "
                        "Se todos os valores do indicador forem NULL, o resultado permanece null."
                    ),
                },
            }
        )
