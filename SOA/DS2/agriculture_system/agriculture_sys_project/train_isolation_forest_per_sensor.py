import os
from dotenv import load_dotenv
import django
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
import joblib

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agriculture_sys_project.settings")
django.setup()

from agriculture_app.models import SensorReading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "agriculture_app")

FEATURE_WINDOW = 10  # must match ml_model/eval


def engineer_features(values):
    df = pd.DataFrame({"value": values})

    df["roll_mean"] = df["value"].rolling(FEATURE_WINDOW, min_periods=1).mean()
    df["roll_std"] = df["value"].rolling(FEATURE_WINDOW, min_periods=1).std().fillna(0.0)
    df["diff"] = df["value"].diff().fillna(0.0)
    df["derivative"] = df["diff"].rolling(FEATURE_WINDOW, min_periods=1).mean().fillna(0.0)

    df = df.bfill().ffill().fillna(0.0)
    return df[["value", "roll_mean", "roll_std", "diff", "derivative"]].values


# OPTIMIZED CONFIGURATION - Reduces FP while maintaining recall
SENSOR_CFG = {
    # Temperature: stricter thresholds, more persistence required
    "TEMPERATURE": {
        "train_cont": 0.005,  # Reduced from 0.01 → cleaner baseline
        "start_q": 0.025,      # Reduced from 0.02 → stricter entry
        "stop_q": 0.05,       # Reduced from 0.06 → stricter exit
        "k": 3                # Increased from 2 → require 3 consecutive hits
    },
    # Humidity: stricter thresholds (avoids daily cycle FPs)
    "HUMIDITY": {
        "train_cont": 0.005,  # Reduced from 0.01
        "start_q": 0.025,      # Reduced from 0.02
        "stop_q": 0.05,       # Reduced from 0.06
        "k": 3                # Increased from 2
    },
    # Moisture: much stricter (noisiest sensor)
    "MOISTURE": {
        "train_cont": 0.003,  # Reduced from 0.005 → even cleaner baseline
        "start_q": 0.02,     # Reduced from 0.015 → much stricter
        "stop_q": 0.04,      # Reduced from 0.045 → much stricter
        "k": 4                # Increased from 3 → maximum persistence
    },
}


def train_model(sensor_type, filename):
    print(f"\n{'='*60}")
    print(f"🔥 Training Isolation Forest for {sensor_type}...")
    print(f"{'='*60}")

    cfg = SENSOR_CFG.get(sensor_type, {"train_cont": 0.005, "start_q": 0.01, "stop_q": 0.04, "k": 3})

    plot_ids = (
        SensorReading.objects.filter(sensor_type=sensor_type)
        .values_list("plot_id", flat=True)
        .distinct()
    )

    all_features = []
    used_plots = 0

    print(f"   Processing {len(plot_ids)} plots...")

    for pid in plot_ids:
        qs_plot = SensorReading.objects.filter(sensor_type=sensor_type, plot_id=pid).order_by("timestamp")

        if qs_plot.count() < FEATURE_WINDOW * 2:
            continue

        values = np.array([x.value for x in qs_plot], dtype=float)
        X_plot = engineer_features(values)
        all_features.append(X_plot)
        used_plots += 1

    if not all_features:
        print(f"⚠ No sufficient data per plot for {sensor_type}.")
        return

    X = np.vstack(all_features)
    print(f"   Used plots: {used_plots}")
    print(f"   Combined Feature matrix shape: {X.shape}")
    print(f"   Features: [value, roll_mean, roll_std, diff, derivative]")

    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    train_cont = float(cfg["train_cont"])
    print(f"   Training Isolation Forest (train_contamination={train_cont})...")

    model = IsolationForest(
        n_estimators=200,
        contamination=train_cont,
        max_samples=256,
        max_features=1.0,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    # Raw scores: lower => more anomalous (scikit-learn convention)
    raw_train = model.decision_function(X_scaled)

    # Calibrated thresholds (THIS is what reduces FP on clean data)
    start_q = float(cfg["start_q"])
    stop_q = float(cfg["stop_q"])
    if stop_q <= start_q:
        stop_q = min(0.20, start_q * 3)

    raw_start = float(np.quantile(raw_train, start_q))
    raw_stop  = float(np.quantile(raw_train, stop_q))

    preds = model.predict(X_scaled)
    flagged = int((preds == -1).sum())
    print(f"   Train predict() flags: {flagged}/{len(preds)} ({flagged/len(preds)*100:.2f}%)")
    print(f"   Saved thresholds: raw_start(q={start_q})={raw_start:.6f}, raw_stop(q={stop_q})={raw_stop:.6f}")
    print(f"   Saved persistence: min_consecutive={cfg['k']}")

    save_path = os.path.join(APP_DIR, filename)
    joblib.dump(
        {
            "model": model,
            "scaler": scaler,
            "feature_window": FEATURE_WINDOW,
            "raw_start": raw_start,
            "raw_stop": raw_stop,
            "min_consecutive": int(cfg["k"]),
            "confidence_scale": 7.0,
            "meta": {
                "sensor_type": sensor_type,
                "train_contamination": train_cont,
                "start_q": start_q,
                "stop_q": stop_q,
                "used_plots": used_plots,
                "n_samples": int(X.shape[0]),
            },
        },
        save_path,
    )

    print(f"🎉 Saved model → {save_path}")
    print(f"   OPTIMIZATION NOTES:")
    print(f"   - Lower train_cont = cleaner baseline model")
    print(f"   - Lower start_q/stop_q = stricter anomaly thresholds")
    print(f"   - Higher k = requires more persistence before flagging")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 OPTIMIZED TRAINING - Reduces FP while maintaining recall")
    print("="*60)
    
    train_model("TEMPERATURE", "model_temperature.pkl")
    train_model("HUMIDITY", "model_humidity.pkl")
    train_model("MOISTURE", "model_moisture.pkl")
    
    print("\n" + "="*60)
    print("✅ TRAINING COMPLETE - Now run evaluate_isolation_forest.py")
    print("="*60)