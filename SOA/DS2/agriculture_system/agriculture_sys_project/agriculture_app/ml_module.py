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
    
    # ML désactivé pour aligner détection live/évaluation et éviter les rafales de faux positifs
    USE_ML = False

    def __init__(self):
        """Initialise le modèle Isolation Forest"""
        # Modèles par plot pour éviter le spillover inter-parcelle
        self.models = {}

    def _build_model(self):
        return IsolationForest(
            contamination=0.01,
            random_state=42,
            n_estimators=200
        )
    
    def train_on_historical_data(self, plot_id, min_samples=100):
        """
        Entraîne le modèle sur les données historiques normales
        
        Args:
            plot_id: ID du plot à analyser
            min_samples: Nombre minimum d'échantillons requis
        
        Returns:
            bool: True si entraînement réussi
        """
        # Récupérer tout l'historique pour couvrir un cycle complet
        recent_readings = SensorReading.objects.filter(
            plot_id=plot_id
        ).order_by('-timestamp')  # pas de limite
        if recent_readings.count() < min_samples:
            print(f"⚠️ Pas assez de données pour entraîner (besoin: {min_samples}, disponible: {recent_readings.count()})")
            return False
        
        # Préparer les features : [moisture, temperature, humidity]
        features = []
        
        # Grouper par timestamp pour avoir les 3 valeurs ensemble
        readings_by_time = {}
        for reading in recent_readings:
            # Exclure les valeurs déjà hors seuil pour garder un jeu quasi-normal
            is_thresh_anom, _, _, _ = self.detect_threshold_anomaly(reading.sensor_type, reading.value)
            if is_thresh_anom:
                continue

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
        
        # Entraîner le modèle pour ce plot
        X = np.array(features)
        model = self._build_model()
        model.fit(X)
        self.models[plot_id] = {
            'model': model,
            'trained': True
        }

        print(f"✅ Modèle entraîné (plot {plot_id}) avec {len(features)} échantillons")
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
    
    def detect_ml_anomaly(self, plot_id, window_size=30):
        """
        Détection ML avec Isolation Forest
        Analyse les dernières lectures en fenêtre glissante
        
        Returns:
            tuple: (is_anomaly, severity, confidence)
        """
        model_info = self.models.get(plot_id)
        if not model_info or not model_info.get('trained'):
            print("⚠️ Modèle non entraîné, entraînement automatique...")
            if not self.train_on_historical_data(plot_id):
                return False, None, 0.0
            model_info = self.models.get(plot_id)
        
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
        clf = model_info['model']
        predictions = clf.predict(X)
        scores = clf.score_samples(X)

        # -1 = anomalie, 1 = normal
        pred_arr = np.array(predictions)
        anomaly_ratio = np.sum(pred_arr == -1) / len(pred_arr)
        anomaly_count = np.sum(pred_arr == -1)
        avg_score = float(np.mean(scores))

        # Gardes-fous plus stricts pour limiter les faux positifs
        if anomaly_count >= 8 and anomaly_ratio > 0.5 and avg_score < -0.12:
            confidence = min(abs(avg_score), 1.0)

            if anomaly_ratio > 0.7:
                severity = SeverityLevel.HIGH
            elif anomaly_ratio > 0.55:
                severity = SeverityLevel.MEDIUM
            else:
                severity = SeverityLevel.LOW

            return True, severity, confidence

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
        
        if self.USE_ML:
            # 2. Détection ML (patterns complexes) – désactivée par défaut
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

    def get_recommendation(self, anomaly_type):
        """Génère une recommandation basée sur le type d'anomalie"""
        recommendations = {
            AnomalyType.LOW_MOISTURE: "Irrigation requise immédiatement. Vérifier le système d'arrosage.",
            AnomalyType.HIGH_MOISTURE: "Arrêter l'irrigation. Vérifier le drainage du sol.",
            AnomalyType.LOW_TEMPERATURE: "Risque de gel. Couvrir les cultures ou activer le chauffage si disponible.",
            AnomalyType.HIGH_TEMPERATURE: "Risque de stress thermique. Augmenter l'ombrage ou la ventilation.",
            AnomalyType.LOW_HUMIDITY: "Augmenter l'humidification ou la brumisation.",
            AnomalyType.HIGH_HUMIDITY: "Améliorer la ventilation pour réduire l'humidité et prévenir les maladies.",
        }
        return recommendations.get(anomaly_type, "Surveiller la situation et vérifier les capteurs.")


# Instance globale du détecteur
anomaly_detector = AnomalyDetector()