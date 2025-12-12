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
        self.active = {}  # {plot_id: {"type": ..., "duration": ..., "params": {}}}

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
                "params": {}  # Per-sensor parameters
            }
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
        params = anomaly["params"]
        anomaly_type = anomaly["type"]

        # -------------------------------
        # Amplitude-tuned anomalies (STRONGER)
        # -------------------------------
        if anomaly_type == "HIGH_TEMPERATURE" and sensor_type == "temperature":
            value += np.random.uniform(5, 10)

        elif anomaly_type == "LOW_TEMPERATURE" and sensor_type == "temperature":
            value -= np.random.uniform(5, 10)

        elif anomaly_type == "HIGH_HUMIDITY" and sensor_type == "humidity":
            value += np.random.uniform(8, 15)

        elif anomaly_type == "LOW_HUMIDITY" and sensor_type == "humidity":
            value -= np.random.uniform(8, 15)

        elif anomaly_type == "HIGH_MOISTURE" and sensor_type == "moisture":
            value += np.random.uniform(10, 20)

        elif anomaly_type == "LOW_MOISTURE" and sensor_type == "moisture":
            value -= np.random.uniform(10, 20)

        elif anomaly_type == "SENSOR_FREEZE":
            if sensor_type not in params:
                params[sensor_type] = {"freeze_value": value}
            value = params[sensor_type]["freeze_value"]

        elif anomaly_type == "NOISE_INJECTION":
            value += np.random.normal(0, 15)

        elif anomaly_type == "SENSOR_DRIFT":
            if sensor_type not in params:
                # Bidirectional drift (up or down), avoiding tiny drifts
                drift = np.random.uniform(-1.0, 1.0)
                while abs(drift) < 0.5:
                    drift = np.random.uniform(-1.0, 1.0)
                params[sensor_type] = {"drift": drift}
            value += params[sensor_type]["drift"]

        return float(value)

    # ----------------------------------------------------------
    # End step (decrement duration after all sensors processed)
    # ----------------------------------------------------------
    def end_step(self, plot_id):
        if plot_id in self.active:
            anomaly_type = self.active[plot_id]["type"]
            self.active[plot_id]["duration"] -= 1
            if self.active[plot_id]["duration"] <= 0:
                print(f"✔ [ANOMALY END] Plot {plot_id}: {anomaly_type}")
                del self.active[plot_id]