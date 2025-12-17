# simulator.py
import time
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import os
from dotenv import load_dotenv
import SOA.DS2.simulator.config as config
from anomaly_engine import AnomalyEngine

# Force load .env located in the same folder as simulator.py
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=ENV_PATH)
print("=== RAW .env FILE CONTENT (binary)===")
with open(ENV_PATH, "rb") as f:
    print(f.read())
print("====================================")

print("DEBUG .env loaded from:", ENV_PATH)
print("DEBUG SENSOR_ENDPOINT =", os.getenv("SENSOR_ENDPOINT"))

# ------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------
SENSOR_ENDPOINT = os.getenv("SENSOR_ENDPOINT", "").strip()
SIMULATOR_ACCESS_TOKEN = os.getenv("SIMULATOR_ACCESS_TOKEN", "").strip()
SIMULATOR_REFRESH_TOKEN = os.getenv("SIMULATOR_REFRESH_TOKEN", "").strip()
TOKEN_REFRESH_ENDPOINT = os.getenv("TOKEN_REFRESH_ENDPOINT", "").strip()

# Global tokens (loaded from .env, updated on refresh)
ACCESS_TOKEN = SIMULATOR_ACCESS_TOKEN
REFRESH_TOKEN = SIMULATOR_REFRESH_TOKEN

print("DEBUG SENSOR_ENDPOINT repr:", repr(SENSOR_ENDPOINT))

VALID_SENSOR_TYPES = {"TEMPERATURE", "HUMIDITY", "MOISTURE"}

fake = Faker()

# ------------------------------------------------------------
# Temperature cycle using NumPy
# ------------------------------------------------------------
def generate_temperature(current_time):
    hour = current_time.hour
    angle = 2 * np.pi * hour / 24 
    mid = (config.TEMP_DAY_PEAK + config.TEMP_NIGHT_LOW) / 2
    amp = (config.TEMP_DAY_PEAK - config.TEMP_NIGHT_LOW) / 2
    noise = np.random.uniform(-config.TEMP_NOISE_MAX, config.TEMP_NOISE_MAX)
    return mid + amp * np.sin(angle) + noise

# ------------------------------------------------------------
# Humidity inverse cycle using NumPy
# ------------------------------------------------------------
def generate_humidity(current_time):
    hour = (current_time.hour + 12) % 24  # Inverse cycle
    angle = 2 * np.pi * hour / 24
    mid = (config.HUM_DAY_LOW + config.HUM_NIGHT_HIGH) / 2
    amp = (config.HUM_NIGHT_HIGH - config.HUM_DAY_LOW) / 2
    noise = np.random.uniform(-config.HUM_NOISE_MAX, config.HUM_NOISE_MAX)
    return mid + amp * np.sin(angle) + noise

# ------------------------------------------------------------
# Moisture drift using NumPy
# ------------------------------------------------------------
def generate_moisture(current):
    # slow natural drying
    drift = np.random.uniform(-0.2, -0.05)
    noise = np.random.uniform(-config.MOISTURE_NOISE_MAX, config.MOISTURE_NOISE_MAX)
    new_value = current + drift + noise
    return np.clip(new_value, config.BASE_MOISTURE_RANGE[0], config.BASE_MOISTURE_RANGE[1])

# ------------------------------------------------------------
# Simple smoothing to avoid unrealistic jumps
# ------------------------------------------------------------
def smooth(prev, new, alpha=0.2):
    """
    Exponential smoothing: alpha small => very smooth, alpha large => more reactive.
    """
    if prev is None:
        return new
    return alpha * new + (1 - alpha) * prev

# ------------------------------------------------------------
# Refresh token function
# ------------------------------------------------------------
# Add near the top with other functions
def login_and_get_tokens():
    global ACCESS_TOKEN, REFRESH_TOKEN
    login_url = "http://127.0.0.1:8000/api/auth/token/"
    payload = {
        "username": os.getenv("SIMULATOR_USERNAME", "admin"),
        "password": os.getenv("SIMULATOR_PASSWORD", "lolo2020")
    }
    try:
        response = requests.post(login_url, json=payload)
        response.raise_for_status()
        data = response.json()
        ACCESS_TOKEN = data["access"]
        REFRESH_TOKEN = data["refresh"]
        print("✅ Fresh tokens obtained via login")
        return True
    except Exception as e:
        print(f"❌ Failed to login for tokens: {e}")
        return False

# Improve refresh_token() to fallback to login
def refresh_token():
    global ACCESS_TOKEN
    if not REFRESH_TOKEN:
        print("⚠ No refresh token — attempting direct login")
        return login_and_get_tokens()

    payload = {"refresh": REFRESH_TOKEN}
    try:
        response = requests.post(TOKEN_REFRESH_ENDPOINT, json=payload)
        response.raise_for_status()
        data = response.json()
        ACCESS_TOKEN = data.get('access', '')
        print("✅ Access token refreshed")
        return True
    except Exception as e:
        print(f"❌ Refresh failed ({e}) — falling back to login")
        return login_and_get_tokens()
# ------------------------------------------------------------
# Send to API with refresh on 401
# ------------------------------------------------------------
def send_to_api(plot_id, sensor_type, value, current_time):
    if not SENSOR_ENDPOINT:
        print("⚠ SENSOR_ENDPOINT not set in .env — skipping API send.")
        return

    payload = {
        "plot": plot_id,
        "sensor_type": sensor_type,
        "value": value,
        "simulated_time": current_time.isoformat()
    }

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    try:
        response = requests.post(SENSOR_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        print(f"✅ Sent {sensor_type} for Plot {plot_id} → {response.status_code}")
    except requests.exceptions.RequestException as e:
        # Catch ConnectionError, Timeout, HTTPError, etc.
        if isinstance(e, requests.exceptions.HTTPError) and hasattr(e, 'response') and e.response.status_code == 401:
            if refresh_token():
                headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                try:
                    response = requests.post(SENSOR_ENDPOINT, json=payload, headers=headers)
                    response.raise_for_status()
                    print(f"✅ Retried after refresh: Sent {sensor_type} for Plot {plot_id} → {response.status_code}")
                except requests.exceptions.RequestException as retry_e:
                     print(f"❌ Retry failed for {sensor_type}: {retry_e}")
            else:
                print(f"❌ Refresh failed for {sensor_type} — update .env and rerun.")
        else:
            # Just print error and continue (don't crash simulation)
            print(f"⚠ API Error (Plot {plot_id} {sensor_type}): {e}")

# ------------------------------------------------------------
# Main simulation loop
# ------------------------------------------------------------
def run_simulator():
    anomaly_engine = AnomalyEngine()

    # Initialize data trackers
    ground_truth = []  # <--- NEW: Track ground truth for evaluation
    temperature_data = {p: [] for p in config.PLOT_IDS}
    humidity_data = {p: [] for p in config.PLOT_IDS}
    moisture_data = {p: [] for p in config.PLOT_IDS}
    moisture_levels = {p: np.random.uniform(*config.BASE_MOISTURE_RANGE) for p in config.PLOT_IDS}
    device_ids = {p: fake.uuid4() if config.USE_FAKE_DEVICE_IDS else None for p in config.PLOT_IDS}

    # Time tracking
    current_time = datetime.fromisoformat(config.START_DATE)  # Start at configured datetime
    time_points = []  # List of datetimes for plotting

    # Simulate until total minutes reached (now in hourly steps)
    try:
        while (current_time - datetime.fromisoformat(config.START_DATE)).total_seconds() / 60 < config.TOTAL_SIM_MINUTES:
            print(f"\n⏱ Simulated time: {current_time}")
            time_points.append(current_time)

            for plot in config.PLOT_IDS:
                # Generate base values (pass current_time)
                raw_temp = generate_temperature(current_time)
                prev_temp = temperature_data[plot][-1] if temperature_data[plot] else None
                base_temp = smooth(prev_temp, raw_temp, alpha=0.1)

                raw_hum = generate_humidity(current_time)
                prev_hum = humidity_data[plot][-1] if humidity_data[plot] else None
                base_hum = smooth(prev_hum, raw_hum, alpha=0.1)

                raw_moisture = generate_moisture(moisture_levels[plot])
                base_moisture = smooth(moisture_levels[plot], raw_moisture, alpha=0.1)
                moisture_levels[plot] = base_moisture

                # Try to start an anomaly
                anomaly_engine.maybe_trigger(plot)

                # Apply anomalies (if any)
                temp = anomaly_engine.apply(plot, "temperature", base_temp)
                hum = anomaly_engine.apply(plot, "humidity", base_hum)
                moisture_levels[plot] = anomaly_engine.apply(plot, "moisture", moisture_levels[plot])

                # Save for graph
                temperature_data[plot].append(temp)
                humidity_data[plot].append(hum)
                moisture_data[plot].append(moisture_levels[plot])

                # Console output
                print(
                    f"Plot {plot} | Device: {device_ids[plot]} → "
                    f"Temp: {temp:.2f}°C | Humidity: {hum:.2f}% | Moisture: {moisture_levels[plot]:.2f}%"
                )

                # Send to API with current_time
                send_to_api(plot, "TEMPERATURE", temp, current_time)
                send_to_api(plot, "HUMIDITY", hum, current_time)
                send_to_api(plot, "MOISTURE", moisture_levels[plot], current_time)

                # End anomaly step after all sensors processed
                anomaly_engine.end_step(plot)

                # --------------------------------------------------------
                # Capture Ground Truth
                # --------------------------------------------------------
                # Check if there is an active anomaly for this plot
                active_anomaly = anomaly_engine.active.get(plot)
                anomaly_type = active_anomaly["type"] if active_anomaly else "NONE"
                
                # Determine if specific sensors are anomalous based on the type
                # (Logic matches anomaly_engine.apply)
                is_temp_anom = 1 if anomaly_type in ["HIGH_TEMPERATURE", "LOW_TEMPERATURE", "SENSOR_FREEZE", "NOISE_INJECTION", "SENSOR_DRIFT"] else 0
                is_hum_anom = 1 if anomaly_type in ["HIGH_HUMIDITY", "LOW_HUMIDITY", "SENSOR_FREEZE", "NOISE_INJECTION", "SENSOR_DRIFT"] else 0
                is_moist_anom = 1 if anomaly_type in ["HIGH_MOISTURE", "LOW_MOISTURE", "SENSOR_FREEZE", "NOISE_INJECTION", "SENSOR_DRIFT"] else 0
                
                # Append rows (one per sensor type per timestamp)
                ground_truth.append({
                    "timestamp": current_time,
                    "plot": plot,
                    "sensor_type": "TEMPERATURE",
                    "value": temp,
                    "is_anomaly": is_temp_anom,
                    "anomaly_type": anomaly_type if is_temp_anom else "NONE"
                })
                ground_truth.append({
                    "timestamp": current_time,
                    "plot": plot,
                    "sensor_type": "HUMIDITY",
                    "value": hum,
                    "is_anomaly": is_hum_anom,
                    "anomaly_type": anomaly_type if is_hum_anom else "NONE"
                })
                ground_truth.append({
                    "timestamp": current_time,
                    "plot": plot,
                    "sensor_type": "MOISTURE",
                    "value": moisture_levels[plot],
                    "is_anomaly": is_moist_anom,
                    "anomaly_type": anomaly_type if is_moist_anom else "NONE"
                })

            current_time += timedelta(minutes=config.MINUTES_PER_STEP)
            time.sleep(config.READING_INTERVAL_SEC)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped by user. Saving data...")
        
    finally:
        # ------------------------------------------------------------
        # Export Ground Truth CSV
        # ------------------------------------------------------------
        if ground_truth:
            df_gt = pd.DataFrame(ground_truth)
            df_gt.to_csv("ground_truth_anomalies.csv", index=False)
            print("✅ Exported ground_truth_anomalies.csv with true injected anomalies")
        else:
            print("⚠ No ground truth data collected.")

        # ------------------------------------------------------------
        # Plot graphs after simulation ends
        # ------------------------------------------------------------
        try:
            colors = {p: c for p, c in zip(config.PLOT_IDS, ["tab:blue", "tab:orange", "tab:green", "tab:red"])}

            # Temperature
            plt.figure(figsize=(12, 5))
            for plot in config.PLOT_IDS:
                if temperature_data[plot]:
                    plt.plot(time_points[:len(temperature_data[plot])], temperature_data[plot], label=f"Plot {plot}", color=colors[plot])
            plt.xlabel("Simulated Hours")
            plt.ylabel("Temperature (°C)")
            plt.title("Temperature per Plot")
            plt.legend()
            plt.grid(True)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Format as hours:minutes
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))  # Tick every hour
            plt.gcf().autofmt_xdate()  # Rotate dates for readability
            plt.savefig("temperature_simulation_per_plot.png")

            # Humidity
            plt.figure(figsize=(12, 5))
            for plot in config.PLOT_IDS:
                if humidity_data[plot]:
                    plt.plot(time_points[:len(humidity_data[plot])], humidity_data[plot], label=f"Plot {plot}", color=colors[plot])
            plt.xlabel("Simulated Hours")
            plt.ylabel("Humidity (%)")
            plt.title("Humidity per Plot")
            plt.legend()
            plt.grid(True)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
            plt.gcf().autofmt_xdate()
            plt.savefig("humidity_simulation_per_plot.png")

            # Moisture
            plt.figure(figsize=(12, 5))
            for plot in config.PLOT_IDS:
                if moisture_data[plot]:
                    plt.plot(time_points[:len(moisture_data[plot])], moisture_data[plot], label=f"Plot {plot}", color=colors[plot])
            plt.xlabel("Simulated Hours")
            plt.ylabel("Moisture (%)")
            plt.title("Moisture per Plot")
            plt.legend()
            plt.grid(True)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
            plt.gcf().autofmt_xdate()
            plt.savefig("moisture_simulation_per_plot.png")
            
            print("✅ Plots saved.")
        except Exception as e:
            print(f"⚠ Could not save plots: {e}")


if __name__ == "__main__":
    run_simulator()