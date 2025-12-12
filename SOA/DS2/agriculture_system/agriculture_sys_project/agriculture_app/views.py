# views.py
# Updated to use MLAnomalyDetector with proper feature engineering
from rest_framework import generics, permissions
from .enumerations import AnomalyType, SeverityLevel, AgentConfidence  # Added AgentConfidence
from .ml_model import get_detector
from .agent_module import generate_recommendation  # Import the recommendation generator
from .models import (
    FarmProfile,
    FieldPlot,
    SensorReading,
    AnomalyEvent,
    AgentRecommendation,
)
from .serializers import (
    FarmProfileSerializer,
    FieldPlotSerializer,
    SensorReadingSerializer,
    AnomalyEventSerializer,
    AgentRecommendationSerializer,
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
# LIST ALL PLOTS
# GET /api/plots/
# ---------------------------------------------------
class PlotListView(generics.ListAPIView):
    queryset = FieldPlot.objects.all()
    serializer_class = FieldPlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        plot_id = self.request.query_params.get("id")
        if plot_id:
            qs = qs.filter(id=plot_id)
        return qs


# ---------------------------------------------------
# RETRIEVE SINGLE PLOT
# GET /api/plots/<id>/
# ---------------------------------------------------
class PlotDetailView(generics.RetrieveAPIView):
    queryset = FieldPlot.objects.all()
    serializer_class = FieldPlotSerializer
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
    permission_classes = [permissions.IsAuthenticated]  # simulator must authenticate

    def perform_create(self, serializer):
        instance = serializer.save()

        # -------------------------------
        # Get detector for this sensor type
        # -------------------------------
        detector = get_detector(instance.sensor_type)
        
        if detector is None:
            print(f"⚠ ML model missing for {instance.sensor_type}, skipping anomaly detection")
            return

        # -------------------------------
        # Predict anomaly using proper feature engineering
        # The detector maintains context per plot automatically
        # -------------------------------
        # -------------------------------
        # Predict anomaly using proper feature engineering
        # The detector maintains context per plot automatically
        # -------------------------------
        plot_id = instance.plot.id
        try:
            is_anomaly, confidence_score = detector.predict(
                plot_id=plot_id,
                sensor_type=instance.sensor_type,
                value=instance.value
            )
        except Exception as e:
            # Fallback if model prediction fails (e.g. stale model file)
            print(f"⚠ Prediction failed for {instance.sensor_type}: {e}")
            is_anomaly = False
            confidence_score = 0.0

        # -------------------------------
        # Detect anomaly with improved threshold
        # Using confidence_score (already normalized) with threshold
        # Higher threshold for humidity to avoid false positives from natural daily cycles
        # -------------------------------
        # Threshold: require minimum confidence to reduce false positives
        # Higher threshold for humidity to avoid false positives from natural daily cycles
        if instance.sensor_type == "TEMPERATURE":
             threshold = 0.55
        elif instance.sensor_type == "HUMIDITY":
             threshold = 0.60
        elif instance.sensor_type == "MOISTURE":
             threshold = 0.52
        else:
             threshold = 0.15

        if is_anomaly and confidence_score >= threshold:
            print(
                f"🔥 Anomaly detected: {instance.sensor_type} "
                f"value={instance.value:.2f} plot={plot_id} "
                f"confidence={confidence_score:.4f}"
            )

            # Determine anomaly type based on value and sensor type
            anomaly_map = {
                "TEMPERATURE": (
                    AnomalyType.HIGH_TEMPERATURE
                    if instance.value > 28
                    else AnomalyType.LOW_TEMPERATURE
                ),
                "HUMIDITY": (
                    AnomalyType.HIGH_HUMIDITY
                    if instance.value > 75
                    else AnomalyType.LOW_HUMIDITY
                ),
                "MOISTURE": (
                    AnomalyType.HIGH_MOISTURE
                    if instance.value > 75
                    else AnomalyType.LOW_MOISTURE
                ),
            }
            anomaly_type = anomaly_map[instance.sensor_type]

            # Determine severity based on confidence score
            if confidence_score < 0.2:
                severity = SeverityLevel.LOW
            elif confidence_score < 0.4:
                severity = SeverityLevel.MEDIUM
            else:
                severity = SeverityLevel.HIGH

            # Create anomaly event with simulated_time copied from the reading
            anomaly_event = AnomalyEvent.objects.create(
                simulated_time=instance.simulated_time,  # Direct copy from the reading
                plot=instance.plot,
                anomaly_type=anomaly_type,
                severity=severity,
                model_confidence=min(confidence_score, 1.0),  # Cap at 1.0
            )
            
            print(f"✅ Created AnomalyEvent #{anomaly_event.id} with severity {severity}")

            # Trigger AI agent to create recommendation (from agent_module.py)
            generate_recommendation(anomaly_event)  # This creates and saves AgentRecommendation


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