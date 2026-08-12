from django.db.models import Count, Prefetch, Sum
from django.db.models.functions import Coalesce
from rest_framework import decorators, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inspection.models import InspectionReport, InspectionReportOperation
from apps.inspection.permissions import CanReviewInspectionStatistics, HasInspectionSyncToken
from apps.inspection.serializers import (
    InspectionExcludeStatisticsSerializer,
    InspectionReportDetailSerializer,
    InspectionReportIngestionSerializer,
    InspectionReportListSerializer,
)
from apps.inspection.services import InspectionStatisticsService, InspectionSyncService


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
            total_approach=Coalesce(Sum("operations__approach"), 0),
            total_refusal=Coalesce(Sum("operations__refusal"), 0),
            total_fined=Coalesce(Sum("operations__fined"), 0),
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
