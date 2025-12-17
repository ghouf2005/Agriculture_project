from django.db import models

class SensorType(models.TextChoices):
    MOISTURE = "MOISTURE", "Moisture"
    TEMPERATURE = "TEMPERATURE", "Temperature"
    HUMIDITY = "HUMIDITY", "Humidity"


class AnomalyType(models.TextChoices):
    HIGH_MOISTURE = "HIGH_MOISTURE", "High Moisture"
    LOW_MOISTURE = "LOW_MOISTURE", "Low Moisture"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE", "High Temperature"
    LOW_TEMPERATURE = "LOW_TEMPERATURE", "Low Temperature"
    HIGH_HUMIDITY = "HIGH_HUMIDITY", "High Humidity"
    LOW_HUMIDITY = "LOW_HUMIDITY", "Low Humidity"


class SeverityLevel(models.TextChoices):
    HIGH = "HIGH", "High"
    MEDIUM = "MEDIUM", "Medium"
    LOW = "LOW", "Low"


class AgentConfidence(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
