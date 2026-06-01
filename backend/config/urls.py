from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import LoginView, PasswordResetRequestView, SetPasswordView, UserViewSet
from apps.schedules.views import (
    ActionTypeViewSet,
    AgentViewSet,
    AgendaViewSet,
    ChiefViewSet,
    EducationGoalViewSet,
    EducationReportViewSet,
    EventReportViewSet,
    InternalAgendaRequestView,
    KitViewSet,
    MaterialViewSet,
    MunicipalityViewSet,
    NeighborhoodViewSet,
    PublicAgendaRequestView,
    PublicAgendaRequestUpdateView,
    SatisfactionSurveyPublicView,
    ReportViewSet,
    SectorViewSet,
    SupportViewSet,
    TeamViewSet,
    VehicleViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("sectors", SectorViewSet, basename="sectors")
router.register("vehicles", VehicleViewSet, basename="vehicles")
router.register("teams", TeamViewSet, basename="teams")
router.register("chiefs", ChiefViewSet, basename="chiefs")
router.register("agents", AgentViewSet, basename="agents")
router.register("supports", SupportViewSet, basename="supports")
router.register("action-types", ActionTypeViewSet, basename="action-types")
router.register("municipalities", MunicipalityViewSet, basename="municipalities")
router.register("neighborhoods", NeighborhoodViewSet, basename="neighborhoods")
router.register("kits", KitViewSet, basename="kits")
router.register("materials", MaterialViewSet, basename="materials")
router.register("agendas", AgendaViewSet, basename="agendas")
router.register("event-reports", EventReportViewSet, basename="event-reports")
router.register("education-reports", EducationReportViewSet, basename="education-reports")
router.register("education-goals", EducationGoalViewSet, basename="education-goals")
router.register("reports", ReportViewSet, basename="reports")

urlpatterns = [
    path("healthz/", lambda request: HttpResponse("ok"), name="healthz"),
    path("admin/", admin.site.urls),
    path("api/auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/password-reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    path("api/auth/set-password/", SetPasswordView.as_view(), name="set_password"),
    path("api/public/agenda-request/", PublicAgendaRequestView.as_view(), name="public_agenda_request"),
    path("api/public/agenda-request/<str:token>/", PublicAgendaRequestUpdateView.as_view(), name="public_agenda_request_update"),
    path("api/public/satisfaction-survey/<str:token>/", SatisfactionSurveyPublicView.as_view(), name="satisfaction_survey_public"),
    path("api/internal/agenda-request/", InternalAgendaRequestView.as_view(), name="internal_agenda_request"),
    path("api/", include(router.urls)),
]
