import os
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, classification_report

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agriculture_sys_project.settings")
django.setup()

from agriculture_app.ml_model import get_detector, engineer_features_matrix, FEATURE_WINDOW

CSV_PATH = "ground_truth_anomalies.csv"
SENSORS = ["TEMPERATURE", "HUMIDITY", "MOISTURE"]


def evaluate_sensor(sensor_type: str, df: pd.DataFrame):
    print(f"\n{'='*70}")
    print(f"📊 Evaluating {sensor_type}")
    print(f"{'='*70}")

    detector = get_detector(sensor_type)
    if detector is None:
        print(f"❌ No detector found for {sensor_type}. Train first.")
        return

    sub = df[df["sensor_type"] == sensor_type].copy()
    if sub.empty:
        print("⚠ No rows for this sensor.")
        return

    sub["timestamp"] = pd.to_datetime(sub["timestamp"])
    sub = sub.sort_values(["plot", "timestamp"])

    y_true_all = []
    y_pred_all = []

    for plot_id, g in sub.groupby("plot"):
        if len(g) < FEATURE_WINDOW * 2:
            continue

        values = g["value"].astype(float).values
        y_true = g["is_anomaly"].astype(int).values

        X = engineer_features_matrix(values, window=FEATURE_WINDOW)
        Xs = detector.scaler.transform(X)

        pred = detector.model.predict(Xs)  # -1 anomaly, 1 normal
        y_pred = (pred == -1).astype(int)

        y_true_all.append(y_true)
        y_pred_all.append(y_pred)

    if not y_true_all:
        print("⚠ Not enough plot segments for evaluation.")
        return

    y_true = np.concatenate(y_true_all)
    y_pred = np.concatenate(y_pred_all)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn + 1e-9)

    print(f"TP={tp}  TN={tn}  FP={fp}  FN={fn}")
    print(f"Precision={precision:.4f}  Recall={recall:.4f}  F1={f1:.4f}  FPR={fpr:.4f}")

    print("\nClassification report:")
    print(classification_report(y_true, y_pred, target_names=["Normal", "Anomaly"], zero_division=0))


if __name__ == "__main__":
    if not os.path.exists(CSV_PATH):
        print(f"❌ Missing {CSV_PATH}. Run simulator with anomalies to generate it.")
        raise SystemExit(1)

    df = pd.read_csv(CSV_PATH)
    print("✅ Loaded:", CSV_PATH, "rows=", len(df))

    for s in SENSORS:
        evaluate_sensor(s, df)

    print("\n✅ Evaluation complete.")
