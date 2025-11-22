from django.db import models

class SensorType(models.TextChoices):
    MOISTURE = "moisture", "Soil Moisture"
    TEMPERATURE = "temperature", "Air Temperature"
    HUMIDITY = "humidity", "Humidity"

class AnomalyType(models.TextChoices):
    LOW_MOISTURE = "low_moisture", "Low Moisture"
    HIGH_TEMPERATURE = "high_temperature", "High Temperature"
    HUMIDITY_DAMAGE = "humidity_damage", "Abnormal Humidity"
    GENERAL_ANOMALY = "general_anomaly", "General Anomaly"


class SeverityLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"