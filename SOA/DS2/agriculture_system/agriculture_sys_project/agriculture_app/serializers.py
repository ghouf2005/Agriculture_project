from rest_framework import serializers
from django.utils import timezone
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
        fields = ['id', 'farm', 'name', 'crop_variety', 'farm_name']

class SensorReadingSerializer(serializers.ModelSerializer):
    simulated_time = serializers.DateTimeField(required=False, default=timezone.now)

    class Meta:
        model = SensorReading
        fields = ['id', 'plot', 'sensor_type', 'value', 'simulated_time'] 


class AnomalyEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyEvent
        fields = ['id', 'plot', 'anomaly_type', 'severity', 'model_confidence', 'simulated_time', 'timestamp']
        

class AgentRecommendationSerializer(serializers.ModelSerializer):
    # Provide aliases expected by the frontend
    anomaly = AnomalyEventSerializer(source='anomaly_event', read_only=True)
    anomaly_id = serializers.IntegerField(source='anomaly_event_id', read_only=True)
    action = serializers.CharField(source='recommended_action')
    explanation = serializers.CharField(source='explanation_text')
    created_at = serializers.DateTimeField(source='timestamp', read_only=True)

    class Meta:
        model = AgentRecommendation
        fields = [
            'id',
            'anomaly_event',
            'anomaly_id',
            'anomaly',
            'action',
            'explanation',
            'recommended_action',
            'explanation_text',
            'confidence',
            'simulated_time',
            'created_at',
            'timestamp',
        ]