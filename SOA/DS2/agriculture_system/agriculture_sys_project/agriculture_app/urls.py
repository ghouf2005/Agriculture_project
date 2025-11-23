from django.urls import path
from .views import (
    FarmProfileListCreateView,
    FieldPlotListCreateView,
    SensorReadingListCreateView,
    AnomalyEventListView,
    AgentRecommendationListView,
)

urlpatterns = [

    # Optional (useful for frontend)
    path("api/farms/", FarmProfileListCreateView.as_view(), name="farms"),
    path("api/plots/", FieldPlotListCreateView.as_view(), name="plots"),

    # REQUIRED BY DOCUMENT
    path("api/sensor-readings/", SensorReadingListCreateView.as_view(), name="sensor-readings"),
    path("api/anomalies/", AnomalyEventListView.as_view(), name="anomalies"),
    path("api/recommendations/", AgentRecommendationListView.as_view(), name="recommendations"),
]
