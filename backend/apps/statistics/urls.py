from django.urls import path
from apps.statistics.views import (
    StatisticsSummaryView, StatisticsComparisonView, StatisticsHistoricalSeriesView,
    StatisticsDashboardView, StatisticsDashboardFiltersView, StatisticsDashboardCsvView,
)

app_name = 'statistics'

urlpatterns = [
    path('summary/', StatisticsSummaryView.as_view(), name='summary'),
    path('comparison/', StatisticsComparisonView.as_view(), name='comparison'),
    path('historical-series/', StatisticsHistoricalSeriesView.as_view(), name='historical_series'),
    path('dashboard/', StatisticsDashboardView.as_view(), name='dashboard'),
    path('dashboard/filters/', StatisticsDashboardFiltersView.as_view(), name='dashboard_filters'),
    path('dashboard/export.csv', StatisticsDashboardCsvView.as_view(), name='dashboard_export_csv'),
]
