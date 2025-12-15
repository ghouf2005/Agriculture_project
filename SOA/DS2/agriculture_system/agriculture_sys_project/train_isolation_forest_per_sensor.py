import os
from dotenv import load_dotenv
import django
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
import joblib

load_dotenv()  # This loads .env from the current directory (or searches up the dir tree)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agriculture_sys_project.settings")
django.setup()

from agriculture_app.models import SensorReading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "agriculture_app")

FEATURE_WINDOW = 10  # Increased for better drift detection  # rolling window for trend features


def engineer_features(values):
    """
    Engineer features for Isolation Forest:
    - value: current sensor reading
    - roll_mean: rolling mean over window
    - roll_std: rolling standard deviation
    - diff: difference from previous value
    - derivative: rolling mean of differences
    """
    df = pd.DataFrame({"value": values})

    # Rolling statistics
    df["roll_mean"] = df["value"].rolling(FEATURE_WINDOW, min_periods=1).mean()
    df["roll_std"] = df["value"].rolling(FEATURE_WINDOW, min_periods=1).std().fillna(0)
    
    # Difference from previous value
    df["diff"] = df["value"].diff().fillna(0)
    
    # Derivative (rolling mean of differences)
    df["derivative"] = df["diff"].rolling(FEATURE_WINDOW, min_periods=1).mean().fillna(0)

    # Fill any remaining NaN values (backward fill, then forward fill, then zero)
    df = df.bfill().ffill().fillna(0)
    
    # Return feature matrix: [value, roll_mean, roll_std, diff, derivative]
    feature_matrix = df[["value", "roll_mean", "roll_std", "diff", "derivative"]].values
    
    return feature_matrix


def train_model(sensor_type, filename):
    print(f"\n{'='*60}")
    print(f"📥 Training Isolation Forest for {sensor_type}...")
    print(f"{'='*60}")

    # Instead of fetching everything sorted by timestamp (which interleaves plots),
    # we must fetch by plot to preserve time-series continuity for rolling features.
    
    # Get all unique plot IDs that have this sensor type
    plot_ids = SensorReading.objects.filter(sensor_type=sensor_type).values_list('plot_id', flat=True).distinct()
    
    all_features = []
    
    print(f"   Processing {len(plot_ids)} plots...")
    
    for pid in plot_ids:
        # Get readings for this plot, sorted by time
        qs_plot = SensorReading.objects.filter(sensor_type=sensor_type, plot_id=pid).order_by("timestamp")
        
        if qs_plot.count() < FEATURE_WINDOW * 2:
            continue
            
        values = np.array([x.value for x in qs_plot])
        
        # Engineer features for this plot's series
        X_plot = engineer_features(values)
        all_features.append(X_plot)
        
    if not all_features:
        print(f"⚠ No sufficient data per plot for {sensor_type}.")
        return

    # Stack all plot features into one big matrix
    X = np.vstack(all_features)
    
    if X.shape[1] != 5:
        print(f"❌ Error: Expected 5 features, got {X.shape[1]}")
        return
    
    print(f"   Combined Feature matrix shape: {X.shape}")
    print(f"   Features: [value, roll_mean, roll_std, diff, derivative]")

    # Scale features
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)
    print(f"   Scaled features - Mean: {X_scaled.mean(axis=0)}, Std: {X_scaled.std(axis=0)}")

    # Train Isolation Forest with improved parameters
    # Per-sensor contamination to balance precision/recall
    # Auto-contamination: Estimate from data using a preliminary fit
    prelim_model = IsolationForest(n_estimators=50, max_samples=256, random_state=42)
    prelim_model.fit(X_scaled)
    prelim_preds = prelim_model.predict(X_scaled)
    # Estimate fraction of anomalies (clamped between 1% and 10%)
    estimated_contamination = max(0.01, min(0.1, (prelim_preds == -1).mean()))
    # Per-sensor tuning for better balance: higher for Temp/Hum (less FN), lower for Moisture (less FP)
    if sensor_type == "TEMPERATURE":
        contamination = 0.05  # Slightly higher → better recall
    elif sensor_type == "HUMIDITY":
        contamination = 0.05   # Same — Humidity behaves well
    elif sensor_type == "MOISTURE":
        contamination = 0.025  # Lower than others → cuts FP significantly
    else:
        contamination = 0.04

    print(f"   Estimated contamination from data: {estimated_contamination:.4f}")
    print(f"   Using tuned contamination: {contamination:.4f}")

    print(f"   Training Isolation Forest (contamination={contamination})...")
    model = IsolationForest(
        n_estimators=200,          # Reduced for faster training, still effective
        contamination=contamination,     # Dynamic per sensor
        max_samples=256,           # Sample size for each tree (balance speed/accuracy)
        max_features=1.0,          # Use all features
        bootstrap=False,           # No bootstrap for Isolation Forest
        random_state=42,           # Reproducibility
        n_jobs=-1                 # Use all CPU cores
    )

    model.fit(X_scaled)
    
    # Quick validation: check predictions
    predictions = model.predict(X_scaled)
    anomaly_count = (predictions == -1).sum()
    anomaly_rate = anomaly_count / len(predictions) * 100
    print(f"   Training results: {anomaly_count}/{len(predictions)} ({anomaly_rate:.1f}%) flagged as anomalies")

    # Save model
    save_path = os.path.join(APP_DIR, filename)
    joblib.dump({
        "model": model,
        "scaler": scaler,
        "feature_window": FEATURE_WINDOW
    }, save_path)

    print(f"🎉 Saved model → {save_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    train_model("TEMPERATURE", "model_temperature.pkl")
    train_model("HUMIDITY", "model_humidity.pkl")
    train_model("MOISTURE", "model_moisture.pkl")