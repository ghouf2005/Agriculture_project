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
    farm_name = serializers.CharField(source="farm.location", read_only=True)

    class Meta:
        model = FieldPlot
        fields = '__all__'

class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = ['id', 'plot', 'sensor_type', 'value', 'simulated_time'] 


class AnomalyEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyEvent
        fields = ['id', 'plot', 'anomaly_type', 'severity', 'description', 'model_confidence', 'simulated_time']
        

class AgentRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRecommendation
        fields = ['id', 'anomaly_event', 'recommended_action', 'explanation_text', 'confidence', 'simulated_time']  # Exclude timestamp