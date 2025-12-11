import os
import django
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, classification_report

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agriculture_sys_project.settings")
django.setup()

from agriculture_app.ml_model import get_detector

print("📥 Loading dataset...")
df = pd.read_csv("synthetic_dataset_with_labels.csv")

FEATURE_WINDOW = 5  # Must match training script


def engineer_features(values):
    """
    Engineer features matching the training script:
    - value: current sensor reading
    - roll_mean: rolling mean over window
    - roll_std: rolling standard deviation
    - diff: difference from previous value
    - derivative: rolling mean of differences
    """
    df_features = pd.DataFrame({"value": values})

    # Rolling statistics
    df_features["roll_mean"] = df_features["value"].rolling(FEATURE_WINDOW, min_periods=1).mean()
    df_features["roll_std"] = df_features["value"].rolling(FEATURE_WINDOW, min_periods=1).std().fillna(0)
    
    # Difference from previous value
    df_features["diff"] = df_features["value"].diff().fillna(0)
    
    # Derivative (rolling mean of differences)
    df_features["derivative"] = df_features["diff"].rolling(FEATURE_WINDOW, min_periods=1).mean().fillna(0)

    # Fill any remaining NaN values
    df_features = df_features.bfill().ffill().fillna(0)
    
    # Return feature matrix: [value, roll_mean, roll_std, diff, derivative]
    feature_matrix = df_features[["value", "roll_mean", "roll_std", "diff", "derivative"]].values
    
    return feature_matrix


def evaluate_sensor(sensor_type):
    print(f"\n{'='*60}")
    print(f"=== Evaluating {sensor_type} ===")
    print(f"{'='*60}")

    # Get detector
    detector = get_detector(sensor_type)
    if detector is None:
        print(f"❌ No detector found for {sensor_type}")
        return

    # Filter data for this sensor type
    sub = df[df["sensor_type"] == sensor_type].copy()
    if len(sub) == 0:
        print(f"⚠ No data found for {sensor_type}")
        return

    print(f"📊 Evaluating on {len(sub)} samples")
    
    # Get values and ground truth
    values = sub["value"].values
    y_true = sub["is_anomaly"].values
    
    # Engineer features (same as training)
    X = engineer_features(values)
    
    if X.shape[1] != 5:
        print(f"❌ Error: Expected 5 features, got {X.shape[1]}")
        return
    
    # Scale features using the detector's scaler
    X_scaled = detector.scaler.transform(X)
    
    # Predict using the model
    predictions = detector.model.predict(X_scaled)  # -1 = anomaly, 1 = normal
    y_pred = np.where(predictions == -1, 1, 0)  # Convert to 0/1
    
    # Calculate metrics
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    
    print(f"\n📈 Results:")
    print(f"   True Positives (TP):  {tp}")
    print(f"   True Negatives (TN):  {tn}")
    print(f"   False Positives (FP): {fp}")
    print(f"   False Negatives (FN): {fn}")
    
    print(f"\n📊 Metrics:")
    print(f"   Precision: {precision:.4f} ({precision*100:.2f}%)")
    print(f"   Recall:    {recall:.4f} ({recall*100:.2f}%)")
    print(f"   F1-score:  {f1:.4f} ({f1*100:.2f}%)")
    
    # Calculate false positive rate
    if (fp + tn) > 0:
        fpr = fp / (fp + tn)
        print(f"   FPR:       {fpr:.4f} ({fpr*100:.2f}%)")
    
    # Accuracy
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    
    print(f"\n📋 Classification Report:")
    print(classification_report(y_true, y_pred, target_names=['Normal', 'Anomaly'], zero_division=0))
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("🔍 Starting Isolation Forest Evaluation")
    print("=" * 60)
    
    evaluate_sensor("TEMPERATURE")
    evaluate_sensor("HUMIDITY")
    evaluate_sensor("MOISTURE")
    
    print("✅ Evaluation complete!")
