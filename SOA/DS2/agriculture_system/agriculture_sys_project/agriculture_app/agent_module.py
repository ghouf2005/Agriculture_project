"""
AI Agent Module: Rule-based decision making and explanation generation.
"""
from datetime import timedelta
from .models import AnomalyEvent, AgentRecommendation, SensorReading
from .enumerations import AnomalyType, SeverityLevel, AgentConfidence
                         
# --- Rule Engine Constants ---
HEAT_STRESS_THRESHOLD = 5  # °C above normal
MOISTURE_DROP_PERCENTAGE = 10  # % drop
SHORT_TIME_WINDOW = timedelta(hours=1)


def _derive_sensor_type_from_anomaly(anomaly_type: str):
    """Map anomaly types to their originating sensor type."""
    if anomaly_type in [AnomalyType.HIGH_MOISTURE, AnomalyType.LOW_MOISTURE]:
        return 'MOISTURE'
    if anomaly_type in [AnomalyType.HIGH_TEMPERATURE, AnomalyType.LOW_TEMPERATURE]:
        return 'TEMPERATURE'
    if anomaly_type in [AnomalyType.HIGH_HUMIDITY, AnomalyType.LOW_HUMIDITY]:
        return 'HUMIDITY'
    return None

# --- Explanation Templates ---
EXPLANATION_TEMPLATES = {
    "IRRIGATION_CHECK": "At {timestamp}, an irrigation-related anomaly was detected on plot {plot_id} with model confidence {model_confidence:.2f}. "
                        "Soil moisture dropped by {moisture_delta:.1f}% over the last hour. "
                        "Recommended action: {action}. Confidence: {agent_confidence}.",
    "HEAT_STRESS": "At {timestamp}, a heat stress anomaly was detected on plot {plot_id} with model confidence {model_confidence:.2f}. "
                   "Temperature has been sustained {temp_delta:.1f}°C above normal. "
                   "Recommended action: {action}. Confidence: {agent_confidence}.",
    "MULTI_ANOMALY": "At {timestamp}, multiple concurrent anomalies were detected on plot {plot_id}. "
                     "Factors include: {factors}. "
                     "Recommended action: {action}. Confidence: {agent_confidence}.",
    "LOW_CONFIDENCE_MONITOR": "At {timestamp}, a potential anomaly of type '{anomaly_type}' was detected on plot {plot_id} with low model confidence ({model_confidence:.2f}). "
                              "A manual check is advised to confirm the issue. "
                              "Recommended action: {action}. Confidence: {agent_confidence}.",
    "DEFAULT": "At {timestamp}, an anomaly of type '{anomaly_type}' was detected on plot {plot_id} with model confidence {model_confidence:.2f}. "
               "Recommended action: {action}. Confidence: {agent_confidence}."
}

def generate_recommendation(anomaly_event: AnomalyEvent):
    """
    Main function for the AI agent. Takes an anomaly event, applies rules,
    and creates an AgentRecommendation.
    """
    # If one already exists (e.g., called from both service and signal), reuse it
    existing = getattr(anomaly_event, "recommendation", None)
    if existing:
        return existing

    # Rule-based decision making
    decision = apply_rules(anomaly_event)
    
    # Generate explanation text
    explanation = generate_explanation(anomaly_event, decision)
    
    # Create (or get) recommendation safely to avoid unique constraint conflicts
    recommendation, created = AgentRecommendation.objects.get_or_create(
        anomaly_event=anomaly_event,
        defaults={
            "timestamp": anomaly_event.timestamp,
            "simulated_time": anomaly_event.simulated_time,
            "recommended_action": decision["action"],
            "explanation_text": explanation,
            "confidence": decision["confidence"],
        },
    )

    if not created:
        return recommendation

    print(f"✅ Agent created recommendation for anomaly {anomaly_event.id}")

def apply_rules(event: AnomalyEvent):
    """
    The core rule engine. Determines the action and confidence based on the anomaly.
    The order of rules is important: specific rules are checked before general ones.
    """
    sensor_type = _derive_sensor_type_from_anomaly(event.anomaly_type)

    # Rule 1: Handle low model confidence first, as it overrides other rules.
    if event.model_confidence < 0.6:
        return {
            "action": "Monitor closely — verify with manual inspection.",
            "confidence": AgentConfidence.LOW,
            "template": "LOW_CONFIDENCE_MONITOR",
            "context": {}
        }

    # Rule 2: Specific check for significant moisture drop.
    if sensor_type == 'MOISTURE':
        one_hour_ago = event.timestamp - SHORT_TIME_WINDOW
        recent_readings = SensorReading.objects.filter(
            plot=event.plot,
            sensor_type='MOISTURE',
            timestamp__gte=one_hour_ago,
            timestamp__lte=event.timestamp
        ).order_by('timestamp')
        
        if recent_readings.count() > 1:
            first_reading = recent_readings.first()
            last_reading = recent_readings.last()
            if first_reading.value > 0:
                percentage_drop = ((first_reading.value - last_reading.value) / first_reading.value) * 100
                if percentage_drop > MOISTURE_DROP_PERCENTAGE:
                    return {
                        "action": "Irrigation check — possible leak or pump failure.",
                        "confidence": AgentConfidence.HIGH,
                        "template": "IRRIGATION_CHECK",
                        "context": {"moisture_delta": percentage_drop}
                    }

    # Rule 3: Specific check for heat stress.
    if sensor_type == 'TEMPERATURE' and event.severity in [SeverityLevel.HIGH]:
         # This is a simplified check. A real implementation would check sustained high temps.
        return {
            "action": "Heat stress mitigation — increase shade or irrigation frequency.",
            "confidence": AgentConfidence.MEDIUM,
            "template": "HEAT_STRESS",
            "context": {"temp_delta": 5.0} # Placeholder
        }

    # Rule 4: General rule for multiple concurrent anomalies.
    # This runs only if the specific rules above did not match.
    recent_anomalies = AnomalyEvent.objects.filter(
        plot=event.plot,
        timestamp__gte=event.timestamp - SHORT_TIME_WINDOW,
        timestamp__lt=event.timestamp
    )

    if recent_anomalies.exists():
        factors = list(recent_anomalies.values_list('anomaly_type', flat=True))
        factors.append(event.anomaly_type)
        unique_factors = sorted(list(set(factors)))
        return {
            "action": "Comprehensive plot inspection — multiple stress factors detected.",
            "confidence": AgentConfidence.HIGH,
            "template": "MULTI_ANOMALY",
            "context": {"factors": ", ".join(unique_factors)}
        }

    # Rule 5: Default fallback rule if no other rules match.
    return {
        "action": f"Investigate '{event.get_anomaly_type_display()}' on plot {event.plot.id}.",
        "confidence": AgentConfidence.MEDIUM,
        "template": "DEFAULT",
        "context": {}
    }

def generate_explanation(event: AnomalyEvent, decision: dict):
    """
    Builds the explanation string from a template.
    """
    template_name = decision.get("template", "DEFAULT")
    template = EXPLANATION_TEMPLATES[template_name]
    
    context = {
        "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M"),
        "plot_id": event.plot.id,
        "model_confidence": event.model_confidence,
        "anomaly_type": event.get_anomaly_type_display(),
        "action": decision['action'],
        "agent_confidence": decision['confidence'],
        **decision.get("context", {})
    }
    
    return template.format(**context)
