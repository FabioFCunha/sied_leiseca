from django.contrib import admin

from .models import (
    ActionType,
    Agent,
    Agenda,
    AgendaHistory,
    AgendaMaterial,
    EducationAction,
    EducationGoal,
    EducationReport,
    EventReport,
    Chief,
    Kit,
    Material,
    Municipality,
    Neighborhood,
    Sector,
    SatisfactionSurvey,
    Support,
    Team,
    Vehicle,
)


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "start_time", "status", "sector", "responsible")
    list_filter = ("status", "sector", "date")
    search_fields = ("title", "location", "responsible__full_name")


@admin.register(AgendaHistory)
class AgendaHistoryAdmin(admin.ModelAdmin):
    list_display = ("agenda", "action", "changed_by", "created_at")
    list_filter = ("action", "created_at")


for lookup_model in [
    Vehicle,
    Team,
    Agent,
    ActionType,
    Municipality,
    Neighborhood,
    Kit,
    Material,
]:
    admin.site.register(lookup_model)


@admin.register(Support)
class SupportAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "role", "address", "source_id", "is_active")
    list_filter = ("team", "is_active")
    search_fields = ("name", "address")


@admin.register(Chief)
class ChiefAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "role", "address", "phone", "source_id", "is_active")
    list_filter = ("team", "is_active")
    search_fields = ("name", "phone", "address")


@admin.register(AgendaMaterial)
class AgendaMaterialAdmin(admin.ModelAdmin):
    list_display = ("agenda", "position", "kit", "material", "quantity")


@admin.register(EventReport)
class EventReportAdmin(admin.ModelAdmin):
    list_display = ("agenda", "status", "objective_status", "participants_count", "created_by", "updated_at")
    list_filter = ("status", "objective_status", "created_at")
    search_fields = ("agenda__title", "created_by__full_name")


class EducationActionInline(admin.TabularInline):
    model = EducationAction
    extra = 0


@admin.register(EducationReport)
class EducationReportAdmin(admin.ModelAdmin):
    list_display = ("agenda", "operation_date", "team", "status", "created_by", "updated_at")
    list_filter = ("source", "status", "operation_date")
    search_fields = ("agenda__id", "agenda__source_id", "agenda__title", "team", "management_name", "contact_received")
    inlines = [EducationActionInline]


@admin.register(SatisfactionSurvey)
class SatisfactionSurveyAdmin(admin.ModelAdmin):
    list_display = ("agenda", "report", "team", "chief_name", "overall_rating", "sent_at", "answered_at")
    list_filter = ("team", "answered_at", "sent_at")
    search_fields = ("agenda__id", "requester_email", "team", "chief_name", "suggestion")


@admin.register(EducationGoal)
class EducationGoalAdmin(admin.ModelAdmin):
    list_display = ("year", "order", "label", "average", "target", "is_active")
    list_filter = ("year", "is_active")
    search_fields = ("label", "key")
