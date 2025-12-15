import os
import joblib
import numpy as np
import pandas as pd
from scipy.special import expit

# App directory (where this file lives)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# One window size everywhere (must match training/eval)
FEATURE_WINDOW = 10

# Global detector instances (lazy load)
_detectors = {}

MODEL_FILES = {
    "TEMPERATURE": "model_temperature.pkl",
    "HUMIDITY": "model_humidity.pkl",
    "MOISTURE": "model_moisture.pkl",
}


def engineer_features_matrix(values, window=FEATURE_WINDOW):
    """
    SINGLE SOURCE OF TRUTH for feature engineering (PDF workflow).
    Builds a feature matrix for a full time series:
      [value, roll_mean, roll_std, diff, derivative]
    """
    df = pd.DataFrame({"value": values.astype(float)})

    df["roll_mean"] = df["value"].rolling(window, min_periods=1).mean()
    df["roll_std"] = df["value"].rolling(window, min_periods=1).std().fillna(0.0)
    df["diff"] = df["value"].diff().fillna(0.0)
    df["derivative"] = df["diff"].rolling(window, min_periods=1).mean().fillna(0.0)

    df = df.bfill().ffill().fillna(0.0)
    return df[["value", "roll_mean", "roll_std", "diff", "derivative"]].values


def engineer_features_last(context_values, window=FEATURE_WINDOW):
    """
    Fast version for live inference: compute ONLY the last row features
    using the rolling-window context (equivalent to the last row of
    engineer_features_matrix()).
    """
    # Keep last window points only
    ctx = np.array(context_values[-window:], dtype=float)
    value = float(ctx[-1])

    roll_mean = float(ctx.mean())
    roll_std = float(ctx.std()) if len(ctx) > 1 else 0.0

    diff = float(value - ctx[-2]) if len(ctx) > 1 else 0.0

    if len(ctx) > 1:
        diffs = np.diff(ctx)
        derivative = float(diffs.mean()) if len(diffs) > 0 else 0.0
    else:
        derivative = 0.0

    return np.array([[value, roll_mean, roll_std, diff, derivative]], dtype=float)


class MLAnomalyDetector:
    """
    Isolation Forest detector with consistent feature engineering.
    Maintains rolling context per plot per sensor.
    """

    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        data = joblib.load(model_path)
        self.model = data["model"]
        self.scaler = data["scaler"]

        # Ensure window comes from file or fallback to constant
        self.window = int(data.get("feature_window", FEATURE_WINDOW))

        # {plot_id: {sensor_type: [values...]}}
        self.plot_contexts = {}

    def _get_context(self, plot_id, sensor_type):
        self.plot_contexts.setdefault(plot_id, {})
        self.plot_contexts[plot_id].setdefault(sensor_type, [])
        return self.plot_contexts[plot_id][sensor_type]

    def predict(self, plot_id, sensor_type, value):
        """
        Returns:
          (is_anomaly: bool, confidence_score: float in [0,1], higher = more anomalous)
        """
        ctx = self._get_context(plot_id, sensor_type)

        ctx.append(float(value))
        # keep a bit more than window so diffs/derivative stay stable
        if len(ctx) > self.window * 3:
            del ctx[:-self.window * 3]

        # Need minimum context to avoid random early flags
        if len(ctx) < 5:
            return False, 0.0

        X = engineer_features_last(ctx, window=self.window)
        Xs = self.scaler.transform(X)

        pred = self.model.predict(Xs)[0]            # 1 normal, -1 anomaly
        raw = self.model.decision_function(Xs)[0]   # negative => more anomalous

        # Normalize to 0..1 (higher => more anomalous)
        confidence = float(expit(-raw * 10))

        return (pred == -1), confidence


def get_detector(sensor_type: str):
    """
    Load detector for a sensor type (TEMPERATURE / HUMIDITY / MOISTURE).
    """
    if sensor_type not in MODEL_FILES:
        return None

    if sensor_type in _detectors:
        return _detectors[sensor_type]

    model_path = os.path.join(BASE_DIR, MODEL_FILES[sensor_type])
    if not os.path.exists(model_path):
        print(f"⚠ Warning: Model file not found: {model_path}")
        return None

    try:
        _detectors[sensor_type] = MLAnomalyDetector(model_path)
        return _detectors[sensor_type]
    except Exception as e:
        print(f"⚠ Error loading model for {sensor_type}: {e}")
        return None
