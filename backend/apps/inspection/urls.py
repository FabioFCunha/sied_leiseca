from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inspection.views import (
    InspectionDailyReportView,
    InspectionHistoricalPushView,
    InspectionReportSyncView,
    InspectionTerritorialRankingView,
    InspectionReportViewSet,
    InspectionStatisticsDashboardView,
    InspectionTerritorialStatisticsView,
)


router = DefaultRouter()

router.register(
    "reports",
    InspectionReportViewSet,
    basename="inspection-reports",
)


urlpatterns = [
    path(
        "statistics/daily-report/",
        InspectionDailyReportView.as_view(),
        name="inspection-daily-report",
    ),
    path(
        "sync/reports/",
        InspectionReportSyncView.as_view(),
        name="inspection_sync_reports",
    ),
    path(
        "sync/historical/push/",
        InspectionHistoricalPushView.as_view(),
        name="inspection_sync_historical_push",
    ),
    path(
        "statistics/dashboard/",
        InspectionStatisticsDashboardView.as_view(),
        name="inspection-statistics-dashboard",
    ),
    path(
        "statistics/territorial/",
        InspectionTerritorialStatisticsView.as_view(),
        name="inspection-territorial-statistics",
    ),
    path(
        "statistics/territorial-ranking/",
        InspectionTerritorialRankingView.as_view(),
        name="inspection-territorial-ranking",
    ),
    path(
        "",
        include(router.urls),
    ),
]
