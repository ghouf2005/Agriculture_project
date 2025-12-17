<template>
  <div class="container py-3">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h2 class="mb-0">Alerts & Agent Actions</h2>
        <small class="text-muted">Most recent recommendations from the AI agents.</small>
      </div>
      <button class="btn btn-outline-success btn-sm" @click="loadData" :disabled="loading">
        Refresh
      </button>
    </div>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-if="loading" class="alert alert-info">Loading...</div>

    <div class="card shadow-sm">
      <div class="card-body">
        <h5 class="card-title">Recommendations</h5>
        <p v-if="!rows.length && !loading" class="text-muted mb-0">No recommendations yet.</p>
        <div v-else class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th scope="col">Plot</th>
                <th scope="col">Action</th>
                <th scope="col">Explanation</th>
                <th scope="col">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.id">
                <td>Plot #{{ row.plot || row.anomaly?.plot || 'N/A' }}</td>
                <td><span class="badge bg-danger me-1">{{ row.anomaly?.type || 'Alert' }}</span>{{ row.action }}</td>
                <td>{{ row.explanation || 'No explanation provided.' }}</td>
                <td>{{ formatDate(row.created_at || row.timestamp) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import api from '@/api/client';

interface AnomalyEvent {
  id: number;
  plot: number;
  timestamp: string;
  type?: string;
  description?: string;
}

interface AgentRecommendation {
  id: number;
  anomaly?: AnomalyEvent;
  anomaly_id?: number;
  plot?: number;
  action: string;
  explanation?: string;
  created_at?: string;
  timestamp?: string;
}

const anomalies = ref<AnomalyEvent[]>([]);
const recommendations = ref<AgentRecommendation[]>([]);
const loading = ref(false);
const error = ref('');
let timer: number | undefined;

const loadData = async () => {
  loading.value = true;
  error.value = '';
  try {
    const [anomalyRes, recRes] = await Promise.all([
      api.get<AnomalyEvent[]>('/anomalies/'),
      api.get<AgentRecommendation[]>('/recommendations/'),
    ]);
    anomalies.value = anomalyRes.data;
    recommendations.value = recRes.data;
  } catch (err) {
    console.error(err);
    error.value = 'Failed to load alerts.';
  } finally {
    loading.value = false;
  }
};

const rows = computed(() => {
  const anomalyById = new Map<number, AnomalyEvent>();
  anomalies.value.forEach((a) => anomalyById.set(a.id, a));
  return recommendations.value
    .map((r) => ({
      ...r,
      anomaly: r.anomaly || (r.anomaly_id ? anomalyById.get(r.anomaly_id) : undefined),
    }))
    .sort((a, b) =>
      new Date(b.created_at || b.timestamp || '').getTime() -
      new Date(a.created_at || a.timestamp || '').getTime()
    );
});

const formatDate = (ts?: string) => (ts ? new Date(ts).toLocaleString() : 'Unknown');

onMounted(() => {
  loadData();
  timer = window.setInterval(loadData, 30000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>
