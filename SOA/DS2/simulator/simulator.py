import time
import numpy as np
from faker import Faker
from datetime import datetime
import matplotlib.pyplot as plt
import requests
import os
from dotenv import load_dotenv
import config

# ------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------
load_dotenv()
SENSOR_ENDPOINT = os.getenv("SENSOR_ENDPOINT")
ACCESS_TOKEN = os.getenv("SIMULATOR_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("SIMULATOR_REFRESH_TOKEN")
TOKEN_REFRESH_ENDPOINT = os.getenv(
    "TOKEN_REFRESH_ENDPOINT",
    "http://127.0.0.1:8000/api/auth/token/refresh/",
)

VALID_SENSOR_TYPES = {"TEMPERATURE", "HUMIDITY", "MOISTURE"}

fake = Faker()

# ------------------------------------------------------------
# Temperature cycle using NumPy
# ------------------------------------------------------------
def generate_temperature(minutes):
    angle = 2 * np.pi * (minutes % config.DAY_LENGTH_MINUTES) / config.DAY_LENGTH_MINUTES
    mid = (config.TEMP_DAY_PEAK + config.TEMP_NIGHT_LOW) / 2
    amp = (config.TEMP_DAY_PEAK - config.TEMP_NIGHT_LOW) / 2
    noise = np.random.uniform(-config.TEMP_NOISE_MAX, config.TEMP_NOISE_MAX)
    return mid + amp * np.sin(angle) + noise


# ------------------------------------------------------------
# Humidity inverse cycle using NumPy
# ------------------------------------------------------------
def generate_humidity(minutes):
    angle = 2 * np.pi * ((minutes + config.DAY_LENGTH_MINUTES / 2) % config.DAY_LENGTH_MINUTES) / config.DAY_LENGTH_MINUTES
    mid = (config.HUM_DAY_LOW + config.HUM_NIGHT_HIGH) / 2
    amp = (config.HUM_NIGHT_HIGH - config.HUM_DAY_LOW) / 2
    noise = np.random.uniform(-config.HUM_NOISE_MAX, config.HUM_NOISE_MAX)
    return mid + amp * np.sin(angle) + noise


# ------------------------------------------------------------
# Moisture drift using NumPy
# ------------------------------------------------------------
def generate_moisture(current):
    drift = np.random.uniform(-0.2, -0.05)  # slow natural drying
    noise = np.random.uniform(-config.MOISTURE_NOISE_MAX, config.MOISTURE_NOISE_MAX)
    new_value = current + drift + noise

    return np.clip(new_value, config.BASE_MOISTURE_RANGE[0], config.BASE_MOISTURE_RANGE[1])
# ------------------------------------------------------------
# Refresh access token 
# ------------------------------------------------------------
def refresh_access_token():
    if not REFRESH_TOKEN:
        print("⚠ No REFRESH_TOKEN in .env, cannot refresh.")
        return None

    try:
        resp = requests.post(
            TOKEN_REFRESH_ENDPOINT,
            json={"refresh": REFRESH_TOKEN},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        new_access = data.get("access")
        if new_access:
            print("✅ Got new access token from refresh.")
        return new_access
    except Exception as e:
        print(f"❌ Error refreshing access token: {e}")
        return None

# ------------------------------------------------------------
# API sending function
# ------------------------------------------------------------
current_access = ACCESS_TOKEN

def send_to_api(plot_id, sensor_type, value):
    global current_access

    if not SENSOR_ENDPOINT:
        print("⚠ No SENSOR_ENDPOINT found in .env — skipping API send.")
        return

    normalized_type = sensor_type.upper()
    if normalized_type not in VALID_SENSOR_TYPES:
        print(f"⚠ Unknown sensor_type '{sensor_type}', skipping API send.")
        return

    payload = {
        "plot": plot_id,
        "sensor_type": normalized_type,
        "value": round(value, 2),
    }

    headers = {"Content-Type": "application/json"}
    if current_access:
        headers["Authorization"] = f"Bearer {current_access}"

    try:
        r = requests.post(
            SENSOR_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=5,
        )

        # If token expired, try once to refresh then retry
        if r.status_code == 401:
            new_access = refresh_access_token()
            if new_access:
                current_access = new_access
                headers["Authorization"] = f"Bearer {current_access}"
                r = requests.post(
                    SENSOR_ENDPOINT,
                    json=payload,
                    headers=headers,
                    timeout=5,
                )

        print(f"[API] Plot {plot_id} {sensor_type}={value:.2f} → {r.status_code}")
    except Exception as e:
        print(f"❌ API error: {e}")



# ------------------------------------------------------------
# Main simulator
# ------------------------------------------------------------
def run_simulator():
    print("🌱 NumPy + Faker Sensor Simulator with API Integration (Day 1–2)...")

    # Stable moisture & device IDs
    moisture_levels = {plot: np.random.uniform(*config.BASE_MOISTURE_RANGE) for plot in config.PLOT_IDS}
    device_ids = {plot: fake.uuid4() for plot in config.PLOT_IDS}

    # For plotting data after simulation
    temperature_data = {plot: [] for plot in config.PLOT_IDS}
    humidity_data = {plot: [] for plot in config.PLOT_IDS}
    moisture_data = {plot: [] for plot in config.PLOT_IDS}
    time_points = []

    simulated_minutes = 0

    while simulated_minutes < config.TOTAL_SIM_MINUTES:
        print(f"\n⏱ Simulated minute: {simulated_minutes} | Real time: {datetime.now()}")
        time_points.append(simulated_minutes)

        for plot in config.PLOT_IDS:
            temp = generate_temperature(simulated_minutes)
            hum = generate_humidity(simulated_minutes)
            moisture_levels[plot] = generate_moisture(moisture_levels[plot])

            # Save for graph
            temperature_data[plot].append(temp)
            humidity_data[plot].append(hum)
            moisture_data[plot].append(moisture_levels[plot])

            # Console output
            print(
                f"Plot {plot} | Device: {device_ids[plot]} → "
                f"Temp: {temp:.2f}°C | Humidity: {hum:.2f}% | Moisture: {moisture_levels[plot]:.2f}%"
            )

            # Send to API
            send_to_api(plot, "temperature", temp)
            send_to_api(plot, "humidity", hum)
            send_to_api(plot, "moisture", moisture_levels[plot])

        simulated_minutes += config.MINUTES_PER_STEP
        time.sleep(config.READING_INTERVAL_SEC)

    # ------------------------------------------------------------
    # Plot graphs after simulation ends
    # ------------------------------------------------------------
    plt.figure(figsize=(12, 8))

    for plot in config.PLOT_IDS:
        plt.plot(time_points, temperature_data[plot], label=f"Plot {plot} - Temperature")
        plt.plot(time_points, humidity_data[plot], label=f"Plot {plot} - Humidity")
        plt.plot(time_points, moisture_data[plot], label=f"Plot {plot} - Moisture")

    plt.xlabel("Simulated Minutes")
    plt.ylabel("Sensor Value")
    plt.title("Sensor Readings Over Time")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    run_simulator()
