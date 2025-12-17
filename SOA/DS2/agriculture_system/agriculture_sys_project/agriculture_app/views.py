# views.py
# OPTIMIZED: Added magnitude filtering to reduce false positives
from rest_framework import generics, permissions
from .enumerations import AnomalyType, SeverityLevel, AgentConfidence
from .ml_model import get_detector
from .agent_module import generate_recommendation
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

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return FarmProfile.objects.all()
        return FarmProfile.objects.filter(owner=user)


# ---------------------------------------------------
# LIST ALL PLOTS
# GET /api/plots/
# ---------------------------------------------------
class PlotListView(generics.ListAPIView):
    queryset = FieldPlot.objects.all()
    serializer_class = FieldPlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            qs = FieldPlot.objects.all()
        else:
            qs = FieldPlot.objects.filter(farm__owner=user)
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

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return FieldPlot.objects.all()
        return FieldPlot.objects.filter(farm__owner=user)


# ---------------------------------------------------
# LIST PLOTS OF A FARM
# GET /api/farms/<farm_id>/plots/
# ---------------------------------------------------
class PlotByFarmView(generics.ListAPIView):
    serializer_class = FieldPlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        farm_id = self.kwargs["farm_id"]
        user = self.request.user
        qs = FieldPlot.objects.filter(farm_id=farm_id)
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(farm__owner=user)


# ---------------------------------------------------
# POST SENSOR DATA (Simulator → Django)
# POST /api/sensor-readings/
# ---------------------------------------------------
class SensorReadingCreateView(generics.CreateAPIView):
    serializer_class = SensorReadingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save()

        # Get detector for this sensor type
        detector = get_detector(instance.sensor_type)
        
        if detector is None:
            print(f"⚠ ML model missing for {instance.sensor_type}, skipping anomaly detection")
            return

        # Predict anomaly using proper feature engineering
        plot_id = instance.plot.id
        try:
            is_anomaly, confidence_score = detector.predict(
                plot_id=plot_id,
                sensor_type=instance.sensor_type,
                value=instance.value
            )
        except Exception as e:
            print(f"⚠ Prediction failed for {instance.sensor_type}: {e}")
            is_anomaly = False
            confidence_score = 0.0

        # Only proceed if ML model flags it as anomaly
        if not is_anomaly:
            return

        # ============================================================
        # MAGNITUDE FILTER: Reduce false positives on borderline values
        # Only create anomaly event if value is significantly outside
        # normal range (not just slightly unusual)
        # ============================================================
        
        # Define normal operating ranges (center points)
        normal_ranges = {
            "TEMPERATURE": (18, 28),  # Normal: 18-28°C
            "HUMIDITY": (50, 75),     # Normal: 50-75%
            "MOISTURE": (40, 70),     # Normal: 40-70%
        }
        
        # Magnitude thresholds: how far outside normal range to flag
        magnitude_thresholds = {
            "TEMPERATURE": 3.0,  # Must be ±3°C outside range
            "HUMIDITY": 8.0,     # Must be ±8% outside range
            "MOISTURE": 8.0,     # Must be ±8% outside range
        }
        
        min_val, max_val = normal_ranges.get(instance.sensor_type, (0, 100))
        threshold = magnitude_thresholds.get(instance.sensor_type, 5.0)
        
        # Check if value is significantly outside normal range
        is_significantly_low = instance.value < (min_val - threshold)
        is_significantly_high = instance.value > (max_val + threshold)
        
        if not (is_significantly_low or is_significantly_high):
            print(
                f"⚠️ Anomaly dismissed (insufficient magnitude): "
                f"{instance.sensor_type}={instance.value:.2f} "
                f"(normal range: {min_val}-{max_val}, threshold: ±{threshold})"
            )
            return
        
        # ============================================================
        # ANOMALY CONFIRMED - Create event
        # ============================================================
        
        print(
            f"🔥 Anomaly confirmed: {instance.sensor_type} "
            f"value={instance.value:.2f} plot={plot_id} "
            f"confidence={confidence_score:.4f}"
        )

        # Determine anomaly type based on value and sensor type
        anomaly_map = {
            "TEMPERATURE": (
                AnomalyType.HIGH_TEMPERATURE
                if instance.value > max_val
                else AnomalyType.LOW_TEMPERATURE
            ),
            "HUMIDITY": (
                AnomalyType.HIGH_HUMIDITY
                if instance.value > max_val
                else AnomalyType.LOW_HUMIDITY
            ),
            "MOISTURE": (
                AnomalyType.HIGH_MOISTURE
                if instance.value > max_val
                else AnomalyType.LOW_MOISTURE
            ),
        }
        anomaly_type = anomaly_map.get(instance.sensor_type, AnomalyType.HIGH_TEMPERATURE)

        # Determine severity based on confidence score
        if confidence_score < 0.65:
            severity = SeverityLevel.LOW
        elif confidence_score < 0.80:
            severity = SeverityLevel.MEDIUM
        else:
            severity = SeverityLevel.HIGH

        # Create anomaly event
        anomaly_event = AnomalyEvent.objects.create(
            simulated_time=instance.simulated_time,
            plot=instance.plot,
            anomaly_type=anomaly_type,
            severity=severity,
            model_confidence=min(confidence_score, 1.0),
        )
        
        print(f"✅ Created AnomalyEvent #{anomaly_event.id} with severity {severity}")

        # Trigger AI agent recommendation
        generate_recommendation(anomaly_event)


# ---------------------------------------------------
# LIST SENSOR READINGS BY PLOT
# GET /api/sensor-readings/?plot=<id>
# ---------------------------------------------------
class SensorReadingListView(generics.ListCreateAPIView):
    serializer_class = SensorReadingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        plot_id = self.request.query_params.get("plot")
        qs = SensorReading.objects.all()
        if plot_id:
            qs = qs.filter(plot_id=plot_id)
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(plot__farm__owner=user)


# ---------------------------------------------------
# LIST ANOMALIES
# GET /api/anomalies/?plot=<id>
# ---------------------------------------------------
class AnomalyListView(generics.ListAPIView):
    serializer_class = AnomalyEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        plot_id = self.request.query_params.get("plot")
        qs = AnomalyEvent.objects.all()
        if plot_id:
            qs = qs.filter(plot_id=plot_id)
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(plot__farm__owner=user)


# ---------------------------------------------------
# LIST RECOMMENDATIONS
# GET /api/recommendations/?anomaly=<id>
# ---------------------------------------------------
class RecommendationListView(generics.ListAPIView):
    serializer_class = AgentRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        anomaly_id = self.request.query_params.get("anomaly")
        qs = AgentRecommendation.objects.all().select_related("anomaly_event", "anomaly_event__plot", "anomaly_event__plot__farm")
        if anomaly_id:
            qs = qs.filter(anomaly_event_id=anomaly_id)
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(anomaly_event__plot__farm__owner=user)