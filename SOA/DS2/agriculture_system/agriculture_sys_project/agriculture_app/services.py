"""
Services pour l'analyse des capteurs et la gestion des anomalies
"""
from django.db.models import Avg
from .models import SensorReading, AnomalyEvent, AgentRecommendation
from .ml_module import anomaly_detector
from .agent_module import generate_recommendation


def process_sensor_reading(reading):
    """
    Traite une nouvelle lecture de capteur :
    1. Analyse avec le modèle ML
    2. Crée un AnomalyEvent si nécessaire
    3. Retourne les résultats
    
    Args:
        reading: Instance de SensorReading
    
    Returns:
        dict: Résultats avec anomaly_created, anomaly_event, etc.
    """
    results = {
        'reading_id': reading.id,
        'anomaly_created': False,
        'anomaly_event': None,
        'analysis': None
    }
    
    # Analyse avec le détecteur
    analysis = anomaly_detector.analyze_reading(reading)
    results['analysis'] = analysis
    
    # Si anomalie détectée, créer l'événement
    if analysis['has_anomaly']:
        anomaly_event = AnomalyEvent.objects.create(
            plot=reading.plot,
            timestamp=reading.timestamp,  # Pass the timestamp from the reading
            anomaly_type=analysis['anomaly_type'],
            severity=analysis['severity'],
            model_confidence=analysis['confidence']
        )
        
        results['anomaly_created'] = True
        results['anomaly_event'] = anomaly_event
        
        # Générer une recommandation
        generate_recommendation(anomaly_event)
        
        print(f"🚨 Anomalie détectée : {anomaly_event.anomaly_type} "
              f"(sévérité: {anomaly_event.severity}, "
              f"confiance: {anomaly_event.model_confidence:.2f})")
    
    return results


def train_model_for_plot(plot_id, min_samples=100):
    """
    Entraîne le modèle ML pour un plot spécifique
    
    Returns:
        bool: True si succès
    """
    return anomaly_detector.train_on_historical_data(plot_id, min_samples)


def get_anomaly_statistics(plot_id=None):
    """
    Retourne des statistiques sur les anomalies détectées
    """
    queryset = AnomalyEvent.objects.all()
    
    if plot_id:
        queryset = queryset.filter(plot_id=plot_id)
    
    total = queryset.count()
    by_severity = {}
    by_type = {}
    
    for anomaly in queryset:
        # Par sévérité
        severity = anomaly.severity
        by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Par type
        anom_type = anomaly.anomaly_type
        by_type[anom_type] = by_type.get(anom_type, 0) + 1
    
    avg_confidence = queryset.aggregate(avg=Avg('model_confidence'))['avg'] or 0.0
    
    return {
        'total_anomalies': total,
        'by_severity': by_severity,
        'by_type': by_type,
        'avg_confidence': round(avg_confidence, 3)
    }