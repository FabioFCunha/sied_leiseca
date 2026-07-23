from django.urls import path
from apps.statistics.views import StatisticsSummaryView, StatisticsComparisonView, StatisticsHistoricalSeriesView

app_name = 'statistics'

urlpatterns = [
    path('summary/', StatisticsSummaryView.as_view(), name='summary'),
    path('comparison/', StatisticsComparisonView.as_view(), name='comparison'),
    path('historical-series/', StatisticsHistoricalSeriesView.as_view(), name='historical_series'),
]
