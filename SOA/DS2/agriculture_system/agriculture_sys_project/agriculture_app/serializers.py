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
        #fields='__all__'
        # 'created_at' is omitted to keep it as an internal, server-side field.
        fields = ['id', 'plot', 'sensor_type', 'value', 'timestamp']

class AnomalyEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyEvent
        fields = ['id', 'plot', 'anomaly_type', 'severity', 'description', 'model_confidence', 'timestamp']


class AgentRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRecommendation
        #fields='__all__'
        fields = ['id', 'anomaly_event', 'recommended_action', 'explanation_text', 'confidence', 'timestamp']
