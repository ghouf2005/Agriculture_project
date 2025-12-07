import time
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import requests
import os
from dotenv import load_dotenv
import config
from anomaly_injector import AnomalyInjector  # ← your anomaly injector

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
    drift = np.random.uniform(-0.2, -0.05)
    noise = np.random.uniform(-config.MOISTURE_NOISE_MAX, config.MOISTURE_NOISE_MAX)
    new_value = current + drift + noise
    return np.clip(new_value, config.BASE_MOISTURE_RANGE[0], config.BASE_MOISTURE_RANGE[1])


# ------------------------------------------------------------
# Refresh access token 
# ------------------------------------------------------------
def refresh_access_token():
    if not REFRESH_TOKEN:
        print("⚠️  No REFRESH_TOKEN in .env, cannot refresh.")
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

def send_to_api(plot_id, sensor_type, value, timestamp):
    global current_access

    if not SENSOR_ENDPOINT:
        print("⚠️  No SENSOR_ENDPOINT found in .env — skipping API send.")
        return

    normalized_type = sensor_type.upper()
    if normalized_type not in VALID_SENSOR_TYPES:
        print(f"⚠️  Unknown sensor_type '{sensor_type}', skipping API send.")
        return

    payload = {
        "plot": plot_id,
        "sensor_type": normalized_type,
        "value": round(value, 2),
        "timestamp": timestamp.isoformat(),  # Add timestamp in ISO format
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

        print(
            f"[API] Plot {plot_id} {sensor_type}={value:.2f} @ {timestamp.strftime('%Y-%m-%d %H:%M')} → {r.status_code}"
        )
    except Exception as e:
        print(f"❌ API error: {e}")


# ------------------------------------------------------------
# Main simulator with anomaly injection
# ------------------------------------------------------------
def run_simulator():
    print("Sensor Simulator – Farm-shared Temperature/Humidity + Realistic Anomalies")

    # Farm-wide weather offsets (same weather per farm)
    farms = set(config.PLOT_FARM_MAP.values())
    farm_temp_offset = {f: np.random.uniform(-0.6, 0.6) for f in farms}
    farm_hum_offset  = {f: np.random.uniform(-2.0, 2.0) for f in farms}

    injector = AnomalyInjector()
    injector.configure_for_plots(config.PLOT_IDS, config.PLOT_FARM_MAP)

    moisture_levels = {p: np.random.uniform(*config.BASE_MOISTURE_RANGE) for p in config.PLOT_IDS}
    device_ids = {p: fake.uuid4() for p in config.PLOT_IDS}

    temperature_data = {p: [] for p in config.PLOT_IDS}
    humidity_data    = {p: [] for p in config.PLOT_IDS}
    moisture_data    = {p: [] for p in config.PLOT_IDS}
    time_points = []
    anomalies_log = []

    simulated_minutes = 0
    start_time = config.SIMULATION_START_DATETIME

    while simulated_minutes < config.TOTAL_SIM_MINUTES:
        current_time = start_time + timedelta(minutes=simulated_minutes)
        time_points.append(current_time)

        for plot in config.PLOT_IDS:
            farm_id = config.PLOT_FARM_MAP.get(plot, f"farm_{plot}")

            # === Baseline with farm-shared base ===
            temp = generate_temperature(simulated_minutes) + farm_temp_offset.get(farm_id, 0)
            hum  = generate_humidity(simulated_minutes)  + farm_hum_offset.get(farm_id, 0)

            # tiny per-reading noise
            temp += np.random.uniform(-0.3, 0.3)
            hum  += np.random.uniform(-1.0, 1.0)

            moisture_levels[plot] = generate_moisture(moisture_levels[plot])

            # === Inject anomalies ===
            temp, temp_anom = injector.modify_sensor_value("TEMPERATURE", temp, simulated_minutes, plot)
            hum,  hum_anom  = injector.modify_sensor_value("HUMIDITY",   hum,  simulated_minutes, plot)
            moisture_levels[plot], moist_anom = injector.modify_sensor_value("MOISTURE", moisture_levels[plot], simulated_minutes, plot)

            if any([temp_anom, hum_anom, moist_anom]):
                anomalies_log.append({
                    "minute": simulated_minutes,
                    "plot": plot,
                    "temp_anomaly": temp_anom,
                    "hum_anomaly": hum_anom,
                    "moist_anomaly": moist_anom,
                })

            # Store & send
            temperature_data[plot].append(temp)
            humidity_data[plot].append(hum)
            moisture_data[plot].append(moisture_levels[plot])

            for stype, val in [("temperature", temp), ("humidity", hum), ("moisture", moisture_levels[plot])]:
                send_to_api(plot, stype, val, current_time)

            print(f"Plot {plot} | Farm {farm_id} → T:{temp:5.2f}°C  H:{hum:5.2f}%  M:{moisture_levels[plot]:5.2f}%")

        simulated_minutes += config.MINUTES_PER_STEP
        time.sleep(config.READING_INTERVAL_SEC)

    injector.save_ground_truth()

    # ------------------------------------------------------------
    # Final report
    # ------------------------------------------------------------
    print(f"\n\n{'='*60}")
    print(f"📊 SIMULATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total anomalies injected: {len(anomalies_log)}")
    print(f"Anomaly scenarios used:")
    for scenario in injector.anomaly_scenarios:
        print(f"  - {scenario}")

    # ------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    for plot in config.PLOT_IDS:
        # Temperature
        axes[0].plot(time_points, temperature_data[plot], label=f"Plot {plot}", alpha=0.7)
        axes[0].set_ylabel("Temperature (°C)")
        axes[0].set_title("Temperature Over Time")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Humidity
        axes[1].plot(time_points, humidity_data[plot], label=f"Plot {plot}", alpha=0.7)
        axes[1].set_ylabel("Humidity (%)")
        axes[1].set_title("Humidity Over Time")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        # Moisture
        axes[2].plot(time_points, moisture_data[plot], label=f"Plot {plot}", alpha=0.7)
        axes[2].set_ylabel("Soil Moisture (%)")
        axes[2].set_title("Soil Moisture Over Time")
        axes[2].set_xlabel("Time")
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

    # Highlight anomaly windows (use the randomized base windows for this run)
    for scenario_name, windows in injector.base_windows.items():
        for window in windows:
            for ax in axes:
                ax.axvspan(
                    start_time + timedelta(minutes=window['start']),
                    start_time + timedelta(minutes=window['end']),
                    alpha=0.2, color='red',
                    label=f'{scenario_name}' if ax == axes[0] else ''
                )

    # Format X-axis with HH:MM
    for ax in axes:
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    run_simulator()
