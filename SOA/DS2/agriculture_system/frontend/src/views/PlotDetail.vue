<template>
  <div class="container py-3">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h2 class="mb-0">{{ plotName }}</h2>
        <small class="text-muted">Live trends and detected anomalies.</small>
      </div>
      <button class="btn btn-outline-success btn-sm" @click="loadData" :disabled="loading">
        Refresh
      </button>
    </div>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <div class="row g-3 mb-3">
      <div class="col-12 col-lg-4">
        <div class="card shadow-sm h-100">
          <div class="card-body">
            <h5 class="card-title">Latest snapshot</h5>
            <p v-if="!lastReading" class="text-muted">No readings yet.</p>
            <ul v-else class="list-group list-group-flush">
              <li class="list-group-item d-flex justify-content-between">
                <span>Moisture</span><strong>{{ fmt(lastReading.moisture) }} %</strong>
              </li>
              <li class="list-group-item d-flex justify-content-between">
                <span>Temperature</span><strong>{{ fmt(lastReading.temperature) }} °C</strong>
              </li>
              <li class="list-group-item d-flex justify-content-between">
                <span>Humidity</span><strong>{{ fmt(lastReading.humidity) }} %</strong>
              </li>
              <li class="list-group-item d-flex justify-content-between">
                <span>Status</span>
                <span class="badge" :class="hasAnomaly ? 'bg-danger' : 'bg-success'">
                  {{ hasAnomaly ? 'Anomaly detected' : 'Normal' }}
                </span>
              </li>
              <li v-if="plotInfo?.crop_variety" class="list-group-item d-flex justify-content-between">
                <span>Crop</span><strong>{{ plotInfo.crop_variety }}</strong>
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div class="col-12 col-lg-8">
        <SensorChart :readings="readings" :anomalies="anomalies" />
      </div>
    </div>

    <div class="card shadow-sm">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h5 class="card-title mb-0">Anomalies</h5>
          <small class="text-muted">Sorted by time, newest first.</small>
        </div>
        <div v-if="!anomalies.length" class="text-muted">No anomalies reported for this plot.</div>
        <ul v-else class="list-group list-group-flush">
          <li v-for="a in anomalies" :key="a.id" class="list-group-item">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <strong>{{ a.anomaly_type || a.type || 'Anomaly' }}</strong>
                <p class="mb-1">
                  {{ a.description || a.severity || 'No description provided.' }}
                </p>
                <small class="text-muted">{{ formatDate(a.timestamp) }}</small>
              </div>
              <span class="badge bg-danger">{{ a.severity || a.anomaly_type || 'Alert' }}</span>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/api/client';
import SensorChart from '@/components/SensorChart.vue';

// Raw shape from backend: one row per sensor_type
interface RawSensorReading {
  timestamp: string;
  plot: number;
  sensor_type: string;
  value: number;
}

// Combined shape for the chart: one row per timestamp with all metrics
interface SensorReading {
  timestamp: string;
  moisture: number | null;
  temperature: number | null;
  humidity: number | null;
}

interface AnomalyEvent {
  id: number;
  plot: number;
  timestamp: string;
  description?: string;
  type?: string;
  severity?: string;
}

interface PlotInfo {
  id: number;
  name?: string;
  crop_variety?: string;
}

const route = useRoute();
const plotId = Number(route.params.id);
const readings = ref<SensorReading[]>([]);
const anomalies = ref<AnomalyEvent[]>([]);
const loading = ref(false);
const error = ref('');
const plotInfo = ref<PlotInfo | null>(null);
const latestSnapshot = ref<{ moisture: number | null; temperature: number | null; humidity: number | null } | null>(null);
let timer: number | undefined;

const lastReading = computed(() => latestSnapshot.value);
const hasAnomaly = computed(() => anomalies.value.length > 0);
const plotName = computed(() => plotInfo.value?.name || `Plot #${plotId}`);

const formatDate = (ts: string) => new Date(ts).toLocaleString();
const fmt = (val: number | null) => (val === null || val === undefined ? '–' : val.toFixed(1));

const loadData = async () => {
  loading.value = true;
  error.value = '';
  try {
    const [plotRes, readRes, anomalyRes] = await Promise.all([
      api
        .get<PlotInfo>(`/plots/${plotId}/`)
        .catch(() => api.get<PlotInfo[]>(`/plots/`, { params: { id: plotId } })),
      api.get<RawSensorReading[]>('/sensor-readings/', { params: { plot: plotId } }),
      api.get<AnomalyEvent[]>('/anomalies/', { params: { plot: plotId } }),
    ]);

    const plotData = Array.isArray(plotRes.data) ? plotRes.data[0] : plotRes.data;
    plotInfo.value = plotData || null;

    // Track latest per metric for snapshot
    const latestByType: Record<string, { ts: number; value: number }> = {};

    // Group raw readings (one per sensor_type) into combined rows per timestamp
    const grouped = new Map<string, SensorReading>();
    readRes.data.forEach((r) => {
      const key = new Date(r.timestamp).toISOString();
      if (!grouped.has(key)) {
        grouped.set(key, {
          timestamp: r.timestamp,
          moisture: null,
          temperature: null,
          humidity: null,
        });
      }
      const row = grouped.get(key)!;
      const sensor = r.sensor_type.toLowerCase();
      const tsNum = new Date(r.timestamp).getTime();
      if (sensor.includes('moisture')) {
        row.moisture = r.value;
        if (!latestByType.moisture || tsNum > latestByType.moisture.ts) {
          latestByType.moisture = { ts: tsNum, value: r.value };
        }
      }
      if (sensor.includes('temp')) {
        row.temperature = r.value;
        if (!latestByType.temperature || tsNum > latestByType.temperature.ts) {
          latestByType.temperature = { ts: tsNum, value: r.value };
        }
      }
      if (sensor.includes('humid')) {
        row.humidity = r.value;
        if (!latestByType.humidity || tsNum > latestByType.humidity.ts) {
          latestByType.humidity = { ts: tsNum, value: r.value };
        }
      }
    });

    readings.value = Array.from(grouped.values()).sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    latestSnapshot.value = {
      moisture: latestByType.moisture?.value ?? null,
      temperature: latestByType.temperature?.value ?? null,
      humidity: latestByType.humidity?.value ?? null,
    };
    anomalies.value = anomalyRes.data.sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  } catch (err) {
    console.error(err);
    error.value = 'Failed to load plot data.';
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadData();
  timer = window.setInterval(loadData, 30000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>
