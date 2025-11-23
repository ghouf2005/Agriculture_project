from rest_framework import serializers
from .models import (
    FarmProfile,
    FieldPlot,
    SensorReading,
    AnomalyEvent,
    AgentRecommendation
)


class FarmProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmProfile
        fields = '__all__'

class FieldPlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldPlot
        fields = '__all__'

class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = '__all__'

class AnomalyEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyEvent
        fields = '__all__'

class AgentRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRecommendation
        fields = '__all__'
