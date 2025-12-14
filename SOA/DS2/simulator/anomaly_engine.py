# anomaly_engine.py
import random
import numpy as np
import config


class AnomalyEngine:
    """
    Handles anomaly injection for the simulator.
    Each active anomaly is tracked per plot.
    """

    def __init__(self):
        self.active = {}  # {plot_id: {"type": ..., "duration": ..., ...}}
        self.log = []  # chronological list of triggered anomalies
        self.scenarios_used = set()

    # ----------------------------------------------------------
    # Random anomaly trigger
    # ----------------------------------------------------------
    def maybe_trigger(self, plot_id):
        """
        With a small probability, start a new anomaly on this plot.
        If an anomaly is already active, keep the current one.
        """
        if plot_id in self.active:
            return

        if random.random() < config.ANOMALY_CHANCE:
            anomaly = random.choice(config.ENABLED_ANOMALIES)
            self.active[plot_id] = {
                "type": anomaly,
                "duration": random.randint(3, 8),
            }
            self.log.append({"plot": plot_id, "type": anomaly})
            self.scenarios_used.add(anomaly)
            print(f"🔥 [ANOMALY START] Plot {plot_id}: {anomaly}")

    # ----------------------------------------------------------
    # Apply anomaly to value
    # ----------------------------------------------------------
    def apply(self, plot_id, sensor_type, value):
        """
        Apply anomaly effect (if any) to the given sensor value.
        sensor_type is one of: "temperature", "humidity", "moisture"
        """
        if plot_id not in self.active:
            return value

        anomaly = self.active[plot_id]
        anomaly_type = anomaly["type"]

        # -------------------------------
        # Amplitude-tuned anomalies
        # -------------------------------
        if anomaly_type == "HIGH_TEMPERATURE" and sensor_type == "temperature":
            # moderate but significant heat spike
            value += np.random.uniform(2, 5)

        elif anomaly_type == "LOW_TEMPERATURE" and sensor_type == "temperature":
            value -= np.random.uniform(2, 5)

        elif anomaly_type == "HIGH_HUMIDITY" and sensor_type == "humidity":
            value += np.random.uniform(3, 8)

        elif anomaly_type == "LOW_HUMIDITY" and sensor_type == "humidity":
            value -= np.random.uniform(3, 8)

        elif anomaly_type == "HIGH_MOISTURE" and sensor_type == "moisture":
            value += np.random.uniform(4, 8)

        elif anomaly_type == "LOW_MOISTURE" and sensor_type == "moisture":
            value -= np.random.uniform(4, 8)

        elif anomaly_type == "SENSOR_FREEZE":
            # sensor gets stuck at a constant reading
            if "freeze_value" not in anomaly:
                anomaly["freeze_value"] = value
            value = anomaly["freeze_value"]

        elif anomaly_type == "NOISE_INJECTION":
            # smaller noise than before: still “crazy” but not insane
            value += np.random.normal(0, 10)

        elif anomaly_type == "SENSOR_DRIFT":
            # gradual drift anomaly (calibration issue)
            drift = anomaly.get("drift")
            if drift is None:
                drift = np.random.uniform(0.1, 0.4)
                anomaly["drift"] = drift
            value += drift

        # reduce duration, end anomaly if complete
        anomaly["duration"] -= 1
        if anomaly["duration"] <= 0:
            print(f"✔ [ANOMALY END] Plot {plot_id}: {anomaly_type}")
            del self.active[plot_id]

        return float(value)
