<template>
  <div class="card shadow-sm mb-3">
    <div class="card-body">
      <h5 class="card-title mb-3">Sensor Trends</h5>
      <div class="chart-wrapper">
        <Line :data="chartData" :options="chartOptions" />
      </div>
      <p v-if="!readings.length" class="text-muted mt-3 mb-0">No sensor data available yet.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Line } from 'vue-chartjs';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
} from 'chart.js';

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale);

interface SensorReading {
  timestamp: string;
  moisture: number | null;
  temperature: number | null;
  humidity: number | null;
}

interface Anomaly {
  id: number;
  timestamp: string;
  description?: string;
}

const props = defineProps<{
  readings: SensorReading[];
  anomalies?: Anomaly[];
}>();

const anomalyKeys = computed(() => {
  return new Set(
    (props.anomalies || []).map((a) => new Date(a.timestamp).toISOString().slice(0, 19))
  );
});

const labels = computed(() => props.readings.map((r) => new Date(r.timestamp).toLocaleTimeString()));

const chartData = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: 'Moisture (%)',
      data: props.readings.map((r) => r.moisture),
      borderColor: '#0d6efd',
      backgroundColor: '#0d6efd',
      tension: 0.3,
      pointRadius: props.readings.map((r) =>
        anomalyKeys.value.has(new Date(r.timestamp).toISOString().slice(0, 19)) ? 5 : 3
      ),
      pointBackgroundColor: props.readings.map((r) =>
        anomalyKeys.value.has(new Date(r.timestamp).toISOString().slice(0, 19)) ? '#dc3545' : '#0d6efd'
      ),
    },
    {
      label: 'Temperature (°C)',
      data: props.readings.map((r) => r.temperature),
      borderColor: '#fd7e14',
      backgroundColor: '#fd7e14',
      tension: 0.3,
      pointRadius: props.readings.map((r) =>
        anomalyKeys.value.has(new Date(r.timestamp).toISOString().slice(0, 19)) ? 5 : 3
      ),
      pointBackgroundColor: props.readings.map((r) =>
        anomalyKeys.value.has(new Date(r.timestamp).toISOString().slice(0, 19)) ? '#dc3545' : '#fd7e14'
      ),
    },
    {
      label: 'Humidity (%)',
      data: props.readings.map((r) => r.humidity),
      borderColor: '#20c997',
      backgroundColor: '#20c997',
      tension: 0.3,
      pointRadius: props.readings.map((r) =>
        anomalyKeys.value.has(new Date(r.timestamp).toISOString().slice(0, 19)) ? 5 : 3
      ),
      pointBackgroundColor: props.readings.map((r) =>
        anomalyKeys.value.has(new Date(r.timestamp).toISOString().slice(0, 19)) ? '#dc3545' : '#20c997'
      ),
    },
  ],
}));

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  spanGaps: true,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: false,
      text: 'Sensor Trends',
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false,
    },
  },
  scales: {
    y: {
      beginAtZero: false,
      grid: {
        color: '#f1f3f5',
      },
    },
    x: {
      grid: {
        color: '#f8f9fa',
      },
    },
  },
};
</script>

<style scoped>
.chart-wrapper {
  position: relative;
  height: 360px;
  max-height: 50vh;
  min-height: 260px;
}

@media (max-width: 768px) {
  .chart-wrapper {
    height: 260px;
    max-height: 40vh;
  }
}
</style>
