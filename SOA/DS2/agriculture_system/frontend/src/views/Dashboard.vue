<template>
  <div class="container-xxl py-3">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h2 class="mb-0">Plots overview</h2>
        <small class="text-muted">Status is red when recent anomalies exist.</small>
      </div>
      <button class="btn btn-outline-success btn-sm" @click="fetchData" :disabled="loading">
        Refresh
      </button>
    </div>

    <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
    <div v-if="loading" class="alert alert-info">Loading...</div>
    <div v-else class="row g-3">
      <div v-for="plot in plots" :key="plot.id" class="col-12 col-sm-6 col-lg-4 col-xl-3">
        <div class="card shadow-sm h-100">
          <div class="card-body d-flex flex-column p-3">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div>
                <h5 class="card-title mb-1">{{ plot.name || `Plot #${plot.id}` }}</h5>
                <small class="text-muted">{{ plot.farm_name || plot.location || 'Farm not set' }}</small>
              </div>
              <span class="badge" :class="statusClass(plot.id)">
                {{ statusLabel(plot.id) }}
              </span>
            </div>
            <p class="card-text flex-grow-1 small mb-3">{{ plot.description || 'Monitoring soil moisture, temperature, and humidity.' }}</p>
            <RouterLink :to="`/plots/${plot.id}`" class="btn btn-success btn-sm mt-auto">View details</RouterLink>
          </div>
        </div>
      </div>
      <p v-if="!plots.length && !loading" class="text-muted">No plots available yet.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import api from '@/api/client';

interface Plot {
  id: number;
  name?: string;
  location?: string;
  description?: string;
  farm_name?: string;
}

interface AnomalyEvent {
  id: number;
  plot: number;
  timestamp: string;
  description?: string;
}

const plots = ref<Plot[]>([]);
const anomaliesByPlot = ref<Record<number, number>>({});
const loading = ref(false);
const error = ref('');
let timer: number | undefined;

const fetchData = async () => {
  loading.value = true;
  error.value = '';
  try {
    const [plotsRes, anomaliesRes] = await Promise.all([
      api.get<Plot[]>('/plots/'),
      api.get<AnomalyEvent[]>('/anomalies/'),
    ]);
    plots.value = plotsRes.data;
    const grouped: Record<number, number> = {};
    anomaliesRes.data.forEach((a) => {
      grouped[a.plot] = (grouped[a.plot] || 0) + 1;
    });
    anomaliesByPlot.value = grouped;
  } catch (err) {
    console.error(err);
    error.value = 'Failed to load plots or anomalies.';
  } finally {
    loading.value = false;
  }
};

const statusLabel = (plotId: number) =>
  anomaliesByPlot.value[plotId] ? 'Anomaly' : 'Normal';

const statusClass = (plotId: number) =>
  anomaliesByPlot.value[plotId] ? 'bg-danger' : 'bg-success';

onMounted(() => {
  fetchData();
  timer = window.setInterval(fetchData, 30000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>
