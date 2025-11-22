from django.shortcuts import render
from rest_framework import viewsets
from .models import FieldPlot,FarmProfile,SensorReading,AnomalyEvent,AgentRecommendation
from .serializers import FieldPlotSerializer,FarmProfileSerializer,SensorReadingSerializer,AnomalyEventSerializer,AgentRecommendationSerializer
from rest_framework.decorators import action

class FarmProfileViewSet(viewsets.ModelViewSet):
    queryset = FarmProfile.objects.all()
    serializer_class = FarmProfileSerializer

class FieldPlotViewSet(viewsets.ModelViewSet):
    queryset = FieldPlot.objects.all()
    serializer_class = FieldPlotSerializer

class SensorReadingViewSet(viewsets.ModelViewSet):
    queryset = SensorReading.objects.all()
    serializer_class = SensorReadingSerializer

class AnomalyEventViewSet(viewsets.ModelViewSet):
    queryset = AnomalyEvent.objects.all()
    serializer_class = AnomalyEventSerializer

class AgentRecommendationViewSet(viewsets.ModelViewSet):
    queryset = AgentRecommendation.objects.all()
    serializer_class = AgentRecommendationSerializer
