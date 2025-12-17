import os
import joblib
import numpy as np
import pandas as pd
from collections import deque
from scipy.special import expit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURE_WINDOW = 10

MODEL_FILES = {
    "TEMPERATURE": "model_temperature.pkl",
    "HUMIDITY": "model_humidity.pkl",
    "MOISTURE": "model_moisture.pkl",
}

_detectors = {}  # cache for Django runtime


def engineer_features_matrix(values, window=FEATURE_WINDOW):
    df = pd.DataFrame({"value": values.astype(float)})

    df["roll_mean"] = df["value"].rolling(window, min_periods=1).mean()
    df["roll_std"] = df["value"].rolling(window, min_periods=1).std().fillna(0.0)
    df["diff"] = df["value"].diff().fillna(0.0)
    df["derivative"] = df["diff"].rolling(window, min_periods=1).mean().fillna(0.0)

    df = df.bfill().ffill().fillna(0.0)
    return df[["value", "roll_mean", "roll_std", "diff", "derivative"]].values


def engineer_features_last(context_values, window=FEATURE_WINDOW):
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
    Production decision = calibrated raw thresholds + persistence.
    NOT model.predict().
    """

    def __init__(self, model_path: str):
        data = joblib.load(model_path)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.window = int(data.get("feature_window", FEATURE_WINDOW))

        # thresholds learned at training-time
        self.raw_start = float(data.get("raw_start", -0.05))
        self.raw_stop = float(data.get("raw_stop", -0.02))

        # persistence
        self.k = int(data.get("min_consecutive", 2))

        # confidence shaping (UI only)
        self.conf_scale = float(data.get("confidence_scale", 7.0))

        # per plot context + per plot state
        self.plot_contexts = {}  # {plot_id: {sensor_type: [values...]}}
        self.state = {}          # {(plot_id, sensor_type): {"in": bool, "hits": deque}}

    def reset_all(self):
        self.plot_contexts.clear()
        self.state.clear()

    def reset_plot(self, plot_id, sensor_type):
        self.plot_contexts.pop(plot_id, None)
        self.state.pop((plot_id, sensor_type), None)

    def _get_context(self, plot_id, sensor_type):
        self.plot_contexts.setdefault(plot_id, {})
        self.plot_contexts[plot_id].setdefault(sensor_type, [])
        return self.plot_contexts[plot_id][sensor_type]

    def predict(self, plot_id, sensor_type, value):
        ctx = self._get_context(plot_id, sensor_type)
        ctx.append(float(value))

        # keep some history
        if len(ctx) > self.window * 3:
            del ctx[:-self.window * 3]

        # OPTIMIZATION: Increased warmup period to reduce early false positives
        # Old: max(5, self.window) → New: max(15, int(self.window * 1.5))
        min_context = max(15, int(self.window * 1.5))  # ← THIS IS THE KEY CHANGE
        if len(ctx) < min_context:
            return False, 0.0

        X = engineer_features_last(ctx, window=self.window)
        Xs = self.scaler.transform(X)

        raw = float(self.model.decision_function(Xs)[0])
        confidence = float(expit(-raw * self.conf_scale))

        key = (plot_id, sensor_type)
        st = self.state.setdefault(key, {"in": False, "hits": deque(maxlen=self.k)})

        # hysteresis: harder to ENTER than to STAY
        hit = (raw < self.raw_start) if not st["in"] else (raw < self.raw_stop)

        st["hits"].append(1 if hit else 0)

        # enter anomaly if k consecutive hits
        if not st["in"] and sum(st["hits"]) == self.k:
            st["in"] = True

        # exit anomaly if k consecutive normals
        if st["in"] and sum(st["hits"]) == 0:
            st["in"] = False

        return bool(st["in"]), confidence

def create_detector(sensor_type: str):
    """Fresh detector (no caching) — use in evaluation scripts."""
    if sensor_type not in MODEL_FILES:
        return None
    model_path = os.path.join(BASE_DIR, MODEL_FILES[sensor_type])
    if not os.path.exists(model_path):
        return None
    return MLAnomalyDetector(model_path)


def get_detector(sensor_type: str):
    """Cached detector — use in Django runtime."""
    if sensor_type not in MODEL_FILES:
        return None
    if sensor_type in _detectors:
        return _detectors[sensor_type]
    d = create_detector(sensor_type)
    if d is not None:
        _detectors[sensor_type] = d
    return d
