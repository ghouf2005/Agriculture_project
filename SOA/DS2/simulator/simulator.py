# simulator.py
import time
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import os
from dotenv import load_dotenv
import config
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
def refresh_token():
    global ACCESS_TOKEN
    if not REFRESH_TOKEN:
        print("⚠ No refresh token in .env — cannot refresh.")
        return False

    payload = {"refresh": REFRESH_TOKEN}
    try:
        response = requests.post(TOKEN_REFRESH_ENDPOINT, json=payload)
        response.raise_for_status()
        data = response.json()
        ACCESS_TOKEN = data.get('access', '')
        print("✅ Refreshed access token. Update .env with new ACCESS_TOKEN if needed.")
        return True
    except Exception as e:
        print(f"❌ Refresh error: {e}. Update tokens in .env manually.")
        return False

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
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            if refresh_token():
                headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                response = requests.post(SENSOR_ENDPOINT, json=payload, headers=headers)
                response.raise_for_status()
                print(f"✅ Retried after refresh: Sent {sensor_type} for Plot {plot_id} → {response.status_code}")
            else:
                print(f"❌ Refresh failed for {sensor_type} — update .env and rerun.")
        else:
            print(f"❌ API error for Plot {plot_id} {sensor_type}: {e}")

# ------------------------------------------------------------
# Main simulation loop
# ------------------------------------------------------------
def run_simulator():
    anomaly_engine = AnomalyEngine()

    # Initialize data trackers
    temperature_data = {p: [] for p in config.PLOT_IDS}
    humidity_data = {p: [] for p in config.PLOT_IDS}
    moisture_data = {p: [] for p in config.PLOT_IDS}
    moisture_levels = {p: np.random.uniform(*config.BASE_MOISTURE_RANGE) for p in config.PLOT_IDS}
    device_ids = {p: fake.uuid4() if config.USE_FAKE_DEVICE_IDS else None for p in config.PLOT_IDS}

    # Time tracking
    current_time = datetime.fromisoformat(config.START_DATE)  # Start at configured datetime
    time_points = []  # List of datetimes for plotting

    # Simulate until total minutes reached (now in hourly steps)
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

        current_time += timedelta(minutes=config.MINUTES_PER_STEP)
        time.sleep(config.READING_INTERVAL_SEC)
    
    # ✨ Rapport final
    print(f"\n\n{'='*60}")
    print(f"📊 SIMULATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total anomalies injected: {len(anomaly_engine.log)}")
    print(f"Anomaly scenarios used:")
    if anomaly_engine.scenarios_used:
        for scenario in sorted(anomaly_engine.scenarios_used):
            print(f"  - {scenario}")
    else:
        print("  - None triggered")
    
    # ------------------------------------------------------------
    # Plot graphs after simulation ends
    # ------------------------------------------------------------
    colors = {p: c for p, c in zip(config.PLOT_IDS, ["tab:blue", "tab:orange", "tab:green", "tab:red"])}

    # Temperature
    plt.figure(figsize=(12, 5))
    for plot in config.PLOT_IDS:
        plt.plot(time_points, temperature_data[plot], label=f"Plot {plot}", color=colors[plot])
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
        plt.plot(time_points, humidity_data[plot], label=f"Plot {plot}", color=colors[plot])
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
        plt.plot(time_points, moisture_data[plot], label=f"Plot {plot}", color=colors[plot])
    plt.xlabel("Simulated Hours")
    plt.ylabel("Moisture (%)")
    plt.title("Moisture per Plot")
    plt.legend()
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.gcf().autofmt_xdate()
    plt.savefig("moisture_simulation_per_plot.png")

    plt.show()


if __name__ == "__main__":
    run_simulator()