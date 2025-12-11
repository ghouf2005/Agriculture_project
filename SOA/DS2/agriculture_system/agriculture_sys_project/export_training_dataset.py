import os
from dotenv import load_dotenv
import django
import pandas as pd
import numpy as np

# Django setup
load_dotenv()  # This loads .env from the current directory (or searches up the dir tree)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agriculture_sys_project.settings")
django.setup()

from agriculture_app.models import SensorReading
from agriculture_app.ml_model import get_detector


def export_dataset():
    """
    Export sensor readings with anomaly labels using proper feature engineering.
    Maintains context per plot-sensor combination for accurate detection.
    """
    print("📥 Loading SensorReadings...")
    
    readings = SensorReading.objects.all().order_by("timestamp", "plot_id", "sensor_type")
    
    # Group by plot and sensor type to maintain context
    plot_sensor_contexts = {}  # {(plot_id, sensor_type): detector}
    
    rows = []
    for r in readings:
        # Get or create detector for this sensor type
        detector = get_detector(r.sensor_type)
        
        if detector is None:
            print(f"⚠ No detector for {r.sensor_type}, skipping anomaly detection")
            is_anomaly = 0
        else:
            # Use detector with proper context per plot
            plot_id = r.plot_id
            is_anomaly_bool, confidence_score = detector.predict(
                plot_id=plot_id,
                sensor_type=r.sensor_type,
                value=r.value
            )
            
            # Apply threshold (same as views.py)
            ANOMALY_THRESHOLD = 0.1
            is_anomaly = 1 if (is_anomaly_bool and confidence_score >= ANOMALY_THRESHOLD) else 0
        
        rows.append({
            "timestamp": r.timestamp,
            "plot": r.plot_id,
            "sensor_type": r.sensor_type,
            "value": r.value,
            "is_anomaly": is_anomaly,
        })

    df = pd.DataFrame(rows)
    df.to_csv("synthetic_dataset_with_labels.csv", index=False)

    print("✅ Exported synthetic_dataset_with_labels.csv")
    print(f"Total samples: {len(df)}")
    print(f"Total anomalies detected: {df['is_anomaly'].sum()} ({df['is_anomaly'].sum()/len(df)*100:.2f}%)")
    
    # Print breakdown by sensor type
    print("\nBreakdown by sensor type:")
    for sensor_type in df["sensor_type"].unique():
        sub = df[df["sensor_type"] == sensor_type]
        anomaly_count = sub["is_anomaly"].sum()
        print(f"  {sensor_type}: {anomaly_count}/{len(sub)} ({anomaly_count/len(sub)*100:.2f}%)")


if __name__ == "__main__":
    export_dataset()
