from django.db import models
from django.contrib.auth.models import User
from .enumerations import SensorType, AnomalyType, SeverityLevel


# -------------------------------------------------
# 1. FARM PROFILE
# -------------------------------------------------
class FarmProfile(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="farms")
    location = models.CharField(max_length=200)
    size = models.FloatField(help_text="Size of the farm in hectares")
    crop_type = models.CharField(max_length=100)

    class Meta:
        db_table = "farm_profiles"
        ordering = ["owner__username"]
        verbose_name = "Farm Profile"
        verbose_name_plural = "Farm Profiles"
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self):
        return f"{self.owner.username}'s Farm – {self.location}"


# -------------------------------------------------
# 2. FIELD PLOT (belongs to a farm)
# -------------------------------------------------
class FieldPlot(models.Model):
    farm = models.ForeignKey(FarmProfile, on_delete=models.CASCADE, related_name="plots")
    name = models.CharField(max_length=100)
    crop_variety = models.CharField(max_length=100)

    class Meta:
        db_table = "field_plots"
        ordering = ["farm", "name"]
        verbose_name = "Field Plot"
        verbose_name_plural = "Field Plots"
        indexes = [
            models.Index(fields=["farm"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.crop_variety})"


# -------------------------------------------------
# 3. SENSOR READING
# -------------------------------------------------
class SensorReading(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    plot = models.ForeignKey(FieldPlot, on_delete=models.CASCADE, related_name="readings")
    sensor_type = models.CharField(max_length=20, choices=SensorType.choices)
    value = models.FloatField()
    source = models.CharField(max_length=50, default="simulator")

    class Meta:
        db_table = "sensor_readings"
        ordering = ["-timestamp"]
        verbose_name = "Sensor Reading"
        verbose_name_plural = "Sensor Readings"
        indexes = [
            models.Index(fields=["plot"]),
            models.Index(fields=["sensor_type"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.sensor_type} = {self.value} at {self.timestamp}"


# -------------------------------------------------
# 4. ANOMALY EVENT
# -------------------------------------------------
class AnomalyEvent(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    plot = models.ForeignKey(FieldPlot, on_delete=models.CASCADE, related_name="anomalies")
    anomaly_type = models.CharField(max_length=50, choices=AnomalyType.choices)
    severity = models.CharField(max_length=10, choices=SeverityLevel.choices)
    model_confidence = models.FloatField(help_text="AI model confidence (0-1)")

    class Meta:
        db_table = "anomaly_events"
        ordering = ["-timestamp"]
        verbose_name = "Anomaly Event"
        verbose_name_plural = "Anomaly Events"
        indexes = [
            models.Index(fields=["plot"]),
            models.Index(fields=["anomaly_type"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.anomaly_type} ({self.severity})"


# -------------------------------------------------
# 5. AGENT RECOMMENDATION
# -------------------------------------------------
class AgentRecommendation(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    anomaly_event = models.ForeignKey(
        AnomalyEvent, on_delete=models.CASCADE, related_name="recommendations"
    )
    recommended_action = models.CharField(max_length=200)
    explanation_text = models.TextField()
    confidence = models.FloatField(help_text="Recommendation confidence (0-1)")

    class Meta:
        db_table = "agent_recommendations"
        ordering = ["-timestamp"]
        verbose_name = "Agent Recommendation"
        verbose_name_plural = "Agent Recommendations"
        indexes = [
            models.Index(fields=["anomaly_event"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"Recommendation for anomaly {self.anomaly_event_id}"
