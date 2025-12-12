from django.urls import path
from .views import (
    FarmListView,
    PlotListView,
    PlotDetailView,
    PlotByFarmView,
    SensorReadingCreateView,
    SensorReadingListView,
    AnomalyListView,
    RecommendationListView
)

urlpatterns = [
    # Farms
    path("farms/", FarmListView.as_view(), name="farm-list"),
    path("plots/", PlotListView.as_view(), name="plot-list"),
    path("plots/<int:pk>/", PlotDetailView.as_view(), name="plot-detail"),
    path("farms/<int:farm_id>/plots/", PlotByFarmView.as_view(), name="plots-by-farm"),

    # Sensor Readings
    path("sensor-readings/", SensorReadingListView.as_view(), name="sensor-reading-list"),
    path("sensor-readings/create/", SensorReadingCreateView.as_view(), name="sensor-reading-create"),

    # Anomalies
    path("anomalies/", AnomalyListView.as_view(), name="anomaly-list"),

    # Agent Recommendations
    path("recommendations/", RecommendationListView.as_view(), name="recommendation-list"),
]
