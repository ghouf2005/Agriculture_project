from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import FarmProfile, FieldPlot, SensorReading, AnomalyEvent, AgentRecommendation
from .serializers import (
    FarmProfileSerializer,
    FieldPlotSerializer,
    SensorReadingSerializer,
    AnomalyEventSerializer,
    AgentRecommendationSerializer
)

# ---------------------------------------------------
# FARM LIST (ADMIN or FARMER)
# GET /api/farms/
# ---------------------------------------------------
class FarmListView(generics.ListAPIView):
    queryset = FarmProfile.objects.all()
    serializer_class = FarmProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


# ---------------------------------------------------
# LIST PLOTS OF A FARM
# GET /api/farms/<farm_id>/plots/
# ---------------------------------------------------
class PlotByFarmView(generics.ListAPIView):
    serializer_class = FieldPlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        farm_id = self.kwargs["farm_id"]
        return FieldPlot.objects.filter(farm_id=farm_id)


# ---------------------------------------------------
# POST SENSOR DATA (Simulator → Django)
# POST /api/sensor-readings/
# ---------------------------------------------------
class SensorReadingCreateView(generics.CreateAPIView):
    serializer_class = SensorReadingSerializer
    permission_classes = [permissions.AllowAny]  # simulator can send without auth

    def perform_create(self, serializer):
        instance = serializer.save()

        # TODO: call ML module here (later)
        # TODO: generate anomaly & recommendation (later)


# ---------------------------------------------------
# LIST SENSOR READINGS BY PLOT
# GET /api/sensor-readings/?plot=<id>
# ---------------------------------------------------
class SensorReadingListView(generics.ListAPIView):
    serializer_class = SensorReadingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        plot_id = self.request.query_params.get("plot")
        qs = SensorReading.objects.all()
        if plot_id:
            qs = qs.filter(plot_id=plot_id)
        return qs


# ---------------------------------------------------
# LIST ANOMALIES
# GET /api/anomalies/?plot=<id>
# ---------------------------------------------------
class AnomalyListView(generics.ListAPIView):
    serializer_class = AnomalyEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        plot_id = self.request.query_params.get("plot")
        qs = AnomalyEvent.objects.all()
        if plot_id:
            qs = qs.filter(plot_id=plot_id)
        return qs


# ---------------------------------------------------
# LIST RECOMMENDATIONS
# GET /api/recommendations/?anomaly=<id>
# ---------------------------------------------------
class RecommendationListView(generics.ListAPIView):
    serializer_class = AgentRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        anomaly_id = self.request.query_params.get("anomaly")
        qs = AgentRecommendation.objects.all()
        if anomaly_id:
            qs = qs.filter(anomaly_event_id=anomaly_id)
        return qs
