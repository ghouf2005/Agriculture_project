"""
ML Module pour la détection d'anomalies dans les données de capteurs
Implémente : Isolation Forest + Threshold-based detection
"""
import numpy as np
from sklearn.ensemble import IsolationForest
from django.utils import timezone
from datetime import timedelta
from .models import SensorReading, AnomalyEvent
from .enumerations import SensorType, AnomalyType, SeverityLevel


class AnomalyDetector:
    """
    Détecteur d'anomalies hybride :
    - Threshold-based (règles simples)
    - Isolation Forest (ML pour patterns complexes)
    """
    
    # Seuils normaux pour chaque type de capteur
    THRESHOLDS = {
        SensorType.MOISTURE: {'min': 35, 'max': 80, 'critical_min': 30, 'critical_max': 85},
        SensorType.TEMPERATURE: {'min': 10, 'max': 32, 'critical_min': 5, 'critical_max': 38},
        SensorType.HUMIDITY: {'min': 30, 'max': 85, 'critical_min': 20, 'critical_max': 95},
    }
    
    def __init__(self):
        """Initialise le modèle Isolation Forest"""
        self.isolation_forest = IsolationForest(
            contamination=0.1,  # 10% des données sont considérées comme anomalies
            random_state=42,
            n_estimators=100
        )
        self.is_trained = False
    
    def train_on_historical_data(self, plot_id, min_samples=100):
        """
        Entraîne le modèle sur les données historiques normales
        
        Args:
            plot_id: ID du plot à analyser
            min_samples: Nombre minimum d'échantillons requis
        
        Returns:
            bool: True si entraînement réussi
        """
        # Récupérer les dernières lectures (dernières 24h simulées)
        recent_readings = SensorReading.objects.filter(
            plot_id=plot_id
        ).order_by('-timestamp')[:min_samples * 3]  # 3 types de capteurs
        
        if recent_readings.count() < min_samples:
            print(f"⚠️ Pas assez de données pour entraîner (besoin: {min_samples}, disponible: {recent_readings.count()})")
            return False
        
        # Préparer les features : [moisture, temperature, humidity]
        features = []
        
        # Grouper par timestamp pour avoir les 3 valeurs ensemble
        readings_by_time = {}
        for reading in recent_readings:
            ts_key = reading.timestamp.replace(microsecond=0, second=0)
            if ts_key not in readings_by_time:
                readings_by_time[ts_key] = {}
            readings_by_time[ts_key][reading.sensor_type] = reading.value
        
        # Créer les vecteurs de features
        for ts, values in readings_by_time.items():
            if len(values) == 3:  # Avoir les 3 types de capteurs
                feature_vector = [
                    values.get(SensorType.MOISTURE, 0),
                    values.get(SensorType.TEMPERATURE, 0),
                    values.get(SensorType.HUMIDITY, 0)
                ]
                features.append(feature_vector)
        
        if len(features) < min_samples:
            print(f"⚠️ Pas assez de vecteurs complets : {len(features)}")
            return False
        
        # Entraîner le modèle
        X = np.array(features)
        self.isolation_forest.fit(X)
        self.is_trained = True
        
        print(f"✅ Modèle entraîné avec {len(features)} échantillons")
        return True
    
    def detect_threshold_anomaly(self, sensor_type, value):
        """
        Détection par seuils (règles simples)
        
        Returns:
            tuple: (is_anomaly, anomaly_type, severity, confidence)
        """
        if sensor_type not in self.THRESHOLDS:
            return False, None, None, 0.0
        
        thresholds = self.THRESHOLDS[sensor_type]
        
        # Anomalie critique
        if value < thresholds['critical_min']:
            anomaly_type = self._get_low_anomaly_type(sensor_type)
            return True, anomaly_type, SeverityLevel.HIGH, 0.95
        
        if value > thresholds['critical_max']:
            anomaly_type = self._get_high_anomaly_type(sensor_type)
            return True, anomaly_type, SeverityLevel.HIGH, 0.95
        
        # Anomalie moyenne
        if value < thresholds['min']:
            anomaly_type = self._get_low_anomaly_type(sensor_type)
            return True, anomaly_type, SeverityLevel.MEDIUM, 0.75
        
        if value > thresholds['max']:
            anomaly_type = self._get_high_anomaly_type(sensor_type)
            return True, anomaly_type, SeverityLevel.MEDIUM, 0.75
        
        return False, None, None, 0.0
    
    def detect_ml_anomaly(self, plot_id, window_size=10):
        """
        Détection ML avec Isolation Forest
        Analyse les dernières lectures en fenêtre glissante
        
        Returns:
            tuple: (is_anomaly, severity, confidence)
        """
        if not self.is_trained:
            print("⚠️ Modèle non entraîné, entraînement automatique...")
            if not self.train_on_historical_data(plot_id):
                return False, None, 0.0
        
        # Récupérer les dernières lectures
        recent = SensorReading.objects.filter(
            plot_id=plot_id
        ).order_by('-timestamp')[:window_size * 3]
        
        if recent.count() < 3:
            return False, None, 0.0
        
        # Préparer les features
        readings_by_time = {}
        for reading in recent:
            ts_key = reading.timestamp.replace(microsecond=0, second=0)
            if ts_key not in readings_by_time:
                readings_by_time[ts_key] = {}
            readings_by_time[ts_key][reading.sensor_type] = reading.value
        
        # Analyser la fenêtre la plus récente
        latest_vectors = []
        for ts in sorted(readings_by_time.keys(), reverse=True)[:window_size]:
            values = readings_by_time[ts]
            if len(values) == 3:
                vector = [
                    values.get(SensorType.MOISTURE, 0),
                    values.get(SensorType.TEMPERATURE, 0),
                    values.get(SensorType.HUMIDITY, 0)
                ]
                latest_vectors.append(vector)
        
        if not latest_vectors:
            return False, None, 0.0
        
        # Prédiction
        X = np.array(latest_vectors)
        predictions = self.isolation_forest.predict(X)
        scores = self.isolation_forest.score_samples(X)
        
        # -1 = anomalie, 1 = normal
        anomaly_ratio = np.sum(predictions == -1) / len(predictions)
        
        if anomaly_ratio > 0.3:  # Plus de 30% des échantillons sont anormaux
            avg_score = np.mean(scores)
            confidence = abs(avg_score)
            
            if anomaly_ratio > 0.7:
                severity = SeverityLevel.HIGH
            elif anomaly_ratio > 0.5:
                severity = SeverityLevel.MEDIUM
            else:
                severity = SeverityLevel.LOW
            
            return True, severity, min(confidence, 1.0)
        
        return False, None, 0.0
    
    def analyze_reading(self, reading):
        """
        Analyse complète d'une lecture de capteur
        Combine threshold + ML detection
        
        Args:
            reading: Instance de SensorReading
        
        Returns:
            dict: Résultats de l'analyse avec anomalies détectées
        """
        results = {
            'has_anomaly': False,
            'anomaly_type': None,
            'severity': None,
            'confidence': 0.0,
            'detection_method': None
        }
        
        # 1. Détection par seuils (rapide et déterministe)
        is_threshold_anomaly, anomaly_type, severity, confidence = \
            self.detect_threshold_anomaly(reading.sensor_type, reading.value)
        
        if is_threshold_anomaly:
            results['has_anomaly'] = True
            results['anomaly_type'] = anomaly_type
            results['severity'] = severity
            results['confidence'] = confidence
            results['detection_method'] = 'threshold'
            return results
        
        # 2. Détection ML (patterns complexes)
        is_ml_anomaly, ml_severity, ml_confidence = \
            self.detect_ml_anomaly(reading.plot_id)
        
        if is_ml_anomaly:
            results['has_anomaly'] = True
            results['anomaly_type'] = self._infer_anomaly_type_from_context(reading)
            results['severity'] = ml_severity
            results['confidence'] = ml_confidence
            results['detection_method'] = 'isolation_forest'
        
        return results
    
    def _get_low_anomaly_type(self, sensor_type):
        """Retourne le type d'anomalie pour valeur basse"""
        mapping = {
            SensorType.MOISTURE: AnomalyType.LOW_MOISTURE,
            SensorType.TEMPERATURE: AnomalyType.LOW_TEMPERATURE,
            SensorType.HUMIDITY: AnomalyType.LOW_HUMIDITY,
        }
        return mapping.get(sensor_type)
    
    def _get_high_anomaly_type(self, sensor_type):
        """Retourne le type d'anomalie pour valeur haute"""
        mapping = {
            SensorType.MOISTURE: AnomalyType.HIGH_MOISTURE,
            SensorType.TEMPERATURE: AnomalyType.HIGH_TEMPERATURE,
            SensorType.HUMIDITY: AnomalyType.HIGH_HUMIDITY,
        }
        return mapping.get(sensor_type)
    
    def _infer_anomaly_type_from_context(self, reading):
        """
        Infère le type d'anomalie basé sur le contexte des lectures récentes
        """
        recent = SensorReading.objects.filter(
            plot=reading.plot,
            sensor_type=reading.sensor_type
        ).order_by('-timestamp')[:5]
        
        if recent.count() < 2:
            return AnomalyType.LOW_MOISTURE  # Défaut
        
        values = [r.value for r in recent]
        avg = np.mean(values)
        
        thresholds = self.THRESHOLDS.get(reading.sensor_type, {})
        normal_mid = (thresholds.get('min', 0) + thresholds.get('max', 100)) / 2
        
        if avg < normal_mid:
            return self._get_low_anomaly_type(reading.sensor_type)
        else:
            return self._get_high_anomaly_type(reading.sensor_type)


# Instance globale du détecteur
anomaly_detector = AnomalyDetector()