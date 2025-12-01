from django.urls import path
from .views import (
    FarmListView,
    PlotByFarmView,
    SensorReadingCreateView,
    SensorReadingListView,
    AnomalyListView,
    RecommendationListView,
    TrainModelView,           
    AnomalyStatsView          
)

urlpatterns = [
    # Farms
    path("farms/", FarmListView.as_view(), name="farm-list"),
    path("farms/<int:farm_id>/plots/", PlotByFarmView.as_view(), name="plots-by-farm"),

    # Sensor Readings
    path("sensor-readings/", SensorReadingListView.as_view(), name="sensor-reading-list"),
    path("sensor-readings/create/", SensorReadingCreateView.as_view(), name="sensor-reading-create"),

    # Anomalies
    path("anomalies/", AnomalyListView.as_view(), name="anomaly-list"),

    # Agent Recommendations
    path("recommendations/", RecommendationListView.as_view(), name="recommendation-list"),

    # ✨ NOUVEAU : ML Endpoints
    path("ml/train/", TrainModelView.as_view(), name="ml-train"),
    path("anomalies/stats/", AnomalyStatsView.as_view(), name="anomaly-stats"),
]