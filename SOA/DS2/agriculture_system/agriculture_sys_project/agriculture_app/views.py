from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import (
    FarmProfile,
    FieldPlot,
    SensorReading,
    AnomalyEvent,
    AgentRecommendation
)
from .serializers import (
    FarmProfileSerializer,
    FieldPlotSerializer,
    SensorReadingSerializer,
    AnomalyEventSerializer,
    AgentRecommendationSerializer
)


class FarmProfileListCreateView(generics.ListCreateAPIView):
    queryset = FarmProfile.objects.all()
    serializer_class = FarmProfileSerializer


class FieldPlotListCreateView(generics.ListCreateAPIView):
    queryset = FieldPlot.objects.all()
    serializer_class = FieldPlotSerializer


class SensorReadingListCreateView(generics.ListCreateAPIView):
    serializer_class = SensorReadingSerializer

    def get_queryset(self):
        queryset = SensorReading.objects.all()
        plot_id = self.request.query_params.get("plot")

        if plot_id:
            queryset = queryset.filter(plot_id=plot_id)

        return queryset


class AnomalyEventListView(generics.ListAPIView):
    queryset = AnomalyEvent.objects.all()
    serializer_class = AnomalyEventSerializer


class AgentRecommendationListView(generics.ListAPIView):
    queryset = AgentRecommendation.objects.all()
    serializer_class = AgentRecommendationSerializer
