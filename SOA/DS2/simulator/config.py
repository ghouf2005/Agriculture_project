# ======================================================
# Plot configuration 
# ======================================================
PLOT_IDS = [1, 2 , 3 , 4]  # Must exist in database


# ======================================================
# Time configuration
# ======================================================
READING_INTERVAL_SEC = 1        # every 1 real second
MINUTES_PER_STEP = 5            # equals 5 minutes of simulated time
TOTAL_SIM_MINUTES = 24 * 60     # simulate a full day


# ======================================================
# Normal base ranges
# ======================================================
BASE_MOISTURE_RANGE = (45, 75)      # %
BASE_TEMPERATURE_RANGE = (18, 28)   # °C
BASE_HUMIDITY_RANGE = (45, 75)      # %


# ======================================================
# Diurnal cycle parameters (Day/night)
# ======================================================
DAY_LENGTH_MINUTES = 24 * 60

# Temperature day/night curve
TEMP_DAY_PEAK = 28       # hottest point
TEMP_NIGHT_LOW = 18      # coldest point

# Humidity inverse to temperature
HUM_DAY_LOW = 45
HUM_NIGHT_HIGH = 75


# ======================================================
# Random noise (small variations)
# ======================================================
MOISTURE_NOISE_MAX = 1.0    # %
TEMP_NOISE_MAX = 0.7        # °C
HUM_NOISE_MAX = 3.0         # %


USE_FAKE_DEVICE_IDS = True