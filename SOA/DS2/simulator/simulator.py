import time
import numpy as np
from faker import Faker
from datetime import datetime
import matplotlib.pyplot as plt
import config

fake = Faker()

# ------------------------------------------------------------
# Temperature cycle
# ------------------------------------------------------------
def generate_temperature(minutes):
    angle = 2 * np.pi * (minutes % config.DAY_LENGTH_MINUTES) / config.DAY_LENGTH_MINUTES
    mid = (config.TEMP_DAY_PEAK + config.TEMP_NIGHT_LOW) / 2
    amp = (config.TEMP_DAY_PEAK - config.TEMP_NIGHT_LOW) / 2
    noise = np.random.uniform(-config.TEMP_NOISE_MAX, config.TEMP_NOISE_MAX)
    return mid + amp * np.sin(angle) + noise

# ------------------------------------------------------------
# Humidity inverse cycle
# ------------------------------------------------------------
def generate_humidity(minutes):
    angle = 2 * np.pi * ((minutes + config.DAY_LENGTH_MINUTES / 2) % config.DAY_LENGTH_MINUTES) / config.DAY_LENGTH_MINUTES
    mid = (config.HUM_DAY_LOW + config.HUM_NIGHT_HIGH) / 2
    amp = (config.HUM_NIGHT_HIGH - config.HUM_DAY_LOW) / 2
    noise = np.random.uniform(-config.HUM_NOISE_MAX, config.HUM_NOISE_MAX)
    return mid + amp * np.sin(angle) + noise

# ------------------------------------------------------------
# Moisture drift
# ------------------------------------------------------------
def generate_moisture(current):
    drift = np.random.uniform(-0.2, -0.05)
    noise = np.random.uniform(-config.MOISTURE_NOISE_MAX, config.MOISTURE_NOISE_MAX)
    new_value = current + drift + noise
    return np.clip(new_value, config.BASE_MOISTURE_RANGE[0], config.BASE_MOISTURE_RANGE[1])

# ------------------------------------------------------------
# Device metadata
# ------------------------------------------------------------
def fake_device_id():
    return fake.uuid4() if config.USE_FAKE_DEVICE_IDS else "device-1"

# ------------------------------------------------------------
# Simulation and data collection
# ------------------------------------------------------------
def run_simulator():
    print("🌱 Running simulator with visualization...")

    # Initialize moisture per plot
    moisture_levels = {plot: np.random.uniform(*config.BASE_MOISTURE_RANGE) for plot in config.PLOT_IDS}

    # Data storage
    timestamps = []
    temperature_data = {plot: [] for plot in config.PLOT_IDS}
    humidity_data = {plot: [] for plot in config.PLOT_IDS}
    moisture_data = {plot: [] for plot in config.PLOT_IDS}

    simulated_minutes = 0

    while simulated_minutes < config.TOTAL_SIM_MINUTES:
        timestamps.append(simulated_minutes)

        for plot in config.PLOT_IDS:
            temp = generate_temperature(simulated_minutes)
            hum = generate_humidity(simulated_minutes)
            moisture_levels[plot] = generate_moisture(moisture_levels[plot])

            temperature_data[plot].append(temp)
            humidity_data[plot].append(hum)
            moisture_data[plot].append(moisture_levels[plot])

        simulated_minutes += config.MINUTES_PER_STEP
        # time.sleep(config.READING_INTERVAL_SEC)  # skip for fast plotting

    # ------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------
    fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    for plot in config.PLOT_IDS:
        axs[0].plot(timestamps, temperature_data[plot], label=f"Plot {plot}")
        axs[1].plot(timestamps, humidity_data[plot], label=f"Plot {plot}")
        axs[2].plot(timestamps, moisture_data[plot], label=f"Plot {plot}")

    axs[0].set_ylabel("Temperature (°C)")
    axs[0].set_title("Temperature over Simulated Day")
    axs[0].legend()

    axs[1].set_ylabel("Humidity (%)")
    axs[1].set_title("Humidity over Simulated Day")
    axs[1].legend()

    axs[2].set_ylabel("Moisture (%)")
    axs[2].set_xlabel("Simulated Minutes")
    axs[2].set_title("Moisture over Simulated Day")
    axs[2].legend()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    run_simulator()
