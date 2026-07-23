from django.contrib import admin
from .models import StatisticCategoryMapping, ConsolidatedStatistic

@admin.register(StatisticCategoryMapping)
class StatisticCategoryMappingAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'indicator_type', 'sied_action_type', 'is_active', 'updated_at')
    list_filter = ('indicator_type', 'is_active', 'sied_action_type')
    search_fields = ('original_name', 'sied_requester_entity', 'description')

@admin.register(ConsolidatedStatistic)
class ConsolidatedStatisticAdmin(admin.ModelAdmin):
    list_display = ('reference_year', 'reference_month', 'indicator_type', 'methodology', 'value', 'traceability_id')
    list_filter = ('methodology', 'indicator_type', 'reference_year', 'reference_month')
    search_fields = ('traceability_id', 'category_entity_type')
    readonly_fields = ('created_at', 'updated_at')
    
    # Optional: protect historical records from manual editing
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.methodology == 'HISTORICAL_LEGACY':
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields
