import os
import joblib
import numpy as np
from datetime import datetime
from django.conf import settings

SEVERITY_LABELS = {1: "low", 2: "medium", 3: "high"}

# Get the app directory path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MLAnomalyDetector:
    """
    Isolation Forest-based anomaly detector with proper feature engineering.
    Maintains context per plot for rolling window features.
    """
    def __init__(self, model_path):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        data = joblib.load(model_path)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.window = data.get("feature_window", 5)

        # Context storage: {plot_id: {sensor_type: [values]}}
        self.plot_contexts = {}

    def _get_context(self, plot_id, sensor_type):
        """Get or create context for a plot-sensor combination."""
        if plot_id not in self.plot_contexts:
            self.plot_contexts[plot_id] = {}
        if sensor_type not in self.plot_contexts[plot_id]:
            self.plot_contexts[plot_id][sensor_type] = []
        return self.plot_contexts[plot_id][sensor_type]

    def _engineer_features(self, value, context):
        """
        Engineer features matching the training script:
        - value: current sensor reading
        - roll_mean: rolling mean over window
        - roll_std: rolling standard deviation
        - diff: difference from previous value
        - derivative: rolling mean of differences
        """
        # Add current value to context
        context.append(value)
        
        # Maintain window size
        if len(context) > self.window:
            context.pop(0)
        
        # Ensure we have at least one value
        if len(context) == 0:
            context.append(value)
        
        arr = np.array(context)
        
        # Compute features (matching training script exactly)
        roll_mean = arr.mean()
        roll_std = arr.std() if len(arr) > 1 else 0.0
        
        # Difference from previous value (single value)
        if len(context) > 1:
            diff = value - context[-2]
        else:
            diff = 0.0
        
        # Derivative: rolling mean of differences over the window
        # This matches: df["derivative"] = df["diff"].rolling(FEATURE_WINDOW).mean()
        if len(context) > 1:
            # Compute all differences in the window
            diffs = np.diff(arr)
            # Take mean of all differences (equivalent to rolling mean when window = full context)
            derivative = diffs.mean() if len(diffs) > 0 else 0.0
        else:
            derivative = 0.0
        
        # Return feature vector: [value, roll_mean, roll_std, diff, derivative]
        return np.array([[value, roll_mean, roll_std, diff, derivative]])

    def predict(self, plot_id, sensor_type, value):
        """
        Predict if a sensor reading is anomalous.
        Returns: (is_anomaly: bool, confidence_score: float)
        """
        # Get context for this plot-sensor combination
        context = self._get_context(plot_id, sensor_type)
        
        # Engineer features
        X = self._engineer_features(value, context)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        prediction = self.model.predict(X_scaled)[0]  # 1 = normal, -1 = anomaly
        score = self.model.decision_function(X_scaled)[0]  # negative = more anomalous
        
        # Convert to anomaly score (higher = more anomalous)
        # Isolation Forest returns negative scores for anomalies
        anomaly_score = abs(score) if prediction == -1 else 0.0
        
        is_anomaly = prediction == -1
        
        return is_anomaly, float(anomaly_score)

    def explain(self, sensor_type, value, timestamp, score, plot_id):
        """Generate explainability report."""
        context = self._get_context(plot_id, sensor_type)
        
        # Determine severity based on score
        if score < 0.15:
            sev = 1
        elif score < 0.35:
            sev = 2
        else:
            sev = 3

        # Classify anomaly shape
        anomaly_type = "Unusual pattern"
        if len(context) > 1:
            mean_val = np.mean(context)
            if abs(value - mean_val) > 10:
                anomaly_type = "Spike"
            elif len(context) > 2 and (context[-2] - value) > 8:
                anomaly_type = "Sudden Drop"
            elif len(context) > 10 and value < np.mean(context[-10:]) - 5:
                anomaly_type = "Drift"

        template = {
            "timestamp": timestamp,
            "sensor": sensor_type,
            "value": value,
            "anomaly_type": anomaly_type,
            "confidence_score": round(score, 2),
            "severity": SEVERITY_LABELS[sev],
            "recommendation": self._recommend(sensor_type, anomaly_type)
        }

        return template

    def _recommend(self, sensor_type, anomaly_type):
        """Generate recommendation based on sensor type and anomaly type."""
        if sensor_type == "MOISTURE":
            if anomaly_type == "Sudden Drop":
                return "Check irrigation system for failure. Soil moisture dropped sharply."
            if anomaly_type == "Spike":
                return "Possible sensor malfunction. Verify moisture probe."
            return "Monitor soil moisture levels closely."
        if sensor_type == "TEMPERATURE":
            if anomaly_type == "Spike":
                return "Heat stress detected. Consider increasing shade or irrigation frequency."
            return "Verify heat conditions. Possible environmental stress."
        if sensor_type == "HUMIDITY":
            return "Check ventilation or sensor calibration."

        return "Investigate sensor behavior."


# Global detector instances (lazy loading)
_detectors = {}


def get_detector(sensor_type):
    """Get or create detector instance for a sensor type."""
    if sensor_type not in _detectors:
        model_files = {
            "TEMPERATURE": "model_temperature.pkl",
            "HUMIDITY": "model_humidity.pkl",
            "MOISTURE": "model_moisture.pkl",
        }
        
        if sensor_type not in model_files:
            return None
        
        model_path = os.path.join(BASE_DIR, model_files[sensor_type])
        
        if not os.path.exists(model_path):
            print(f"⚠ Warning: Model file not found: {model_path}")
            return None
        
        try:
            _detectors[sensor_type] = MLAnomalyDetector(model_path)
        except Exception as e:
            print(f"⚠ Error loading model {sensor_type}: {e}")
            return None
    
    return _detectors[sensor_type]


# Backward compatibility exports (for existing code)
def _load_legacy_models():
    """Legacy function for backward compatibility."""
    return (
        get_detector("TEMPERATURE"),
        get_detector("HUMIDITY"),
        get_detector("MOISTURE")
    )


# Export detector getter function
__all__ = ['MLAnomalyDetector', 'get_detector', 'SEVERITY_LABELS']
