from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inspection.views import InspectionReportSyncView, InspectionReportViewSet


router = DefaultRouter()
router.register("reports", InspectionReportViewSet, basename="inspection-reports")


urlpatterns = [
    path("sync/reports/", InspectionReportSyncView.as_view(), name="inspection_sync_reports"),
    path("", include(router.urls)),
]
