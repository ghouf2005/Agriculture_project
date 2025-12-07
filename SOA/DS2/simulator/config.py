from datetime import datetime

# ======================================================
# Plot configuration
# ======================================================
PLOT_IDS = [1, 2, 3, 4]

PLOT_FARM_MAP = {
    1: "farmA",
    2: "farmA",
    3: "farmB",
    4: "farmB",
}

# ======================================================
# Simulation time
# ======================================================
SIMULATION_START_DATETIME = datetime(2025, 1, 9, 6, 0, 0)

READING_INTERVAL_SEC = 1
MINUTES_PER_STEP = 5
TOTAL_SIM_MINUTES = 24 * 60

# ======================================================
# Normal ranges
# ======================================================
BASE_MOISTURE_RANGE = (45, 75)
TEMP_DAY_PEAK, TEMP_NIGHT_LOW = 28, 18
HUM_DAY_LOW, HUM_NIGHT_HIGH = 45, 75
DAY_LENGTH_MINUTES = 24 * 60

# Reduced noise because we now have farm offsets
TEMP_NOISE_MAX = 0.3
HUM_NOISE_MAX = 1.5
MOISTURE_NOISE_MAX = 1.0

# ======================================================
# Anomaly multiplicity — keep sparse to favor normal data
# ======================================================
MIN_ANOMALIES_PER_TYPE = 0
MAX_ANOMALIES_PER_TYPE = 1