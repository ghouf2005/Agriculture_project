<template>
  <div>
    <nav class="navbar navbar-expand-lg navbar-dark bg-success">
      <div class="container-fluid">
        <RouterLink class="navbar-brand fw-bold" to="/dashboard">
          AI Crop Monitoring
        </RouterLink>
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarContent"
          aria-controls="navbarContent"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarContent">
          <ul class="navbar-nav me-auto mb-2 mb-lg-0">
            <li class="nav-item">
              <RouterLink class="nav-link" to="/dashboard">Dashboard</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link" to="/alerts">Alerts</RouterLink>
            </li>
          </ul>
          <div class="d-flex align-items-center">
            <RouterLink v-if="!isAuthenticated" class="btn btn-outline-light btn-sm" to="/login">
              Login
            </RouterLink>
            <button v-else class="btn btn-outline-light btn-sm" @click="handleLogout">
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useAuthStore } from './stores/auth';

const router = useRouter();
const auth = useAuthStore();
const { isAuthenticated } = storeToRefs(auth);

const handleLogout = () => {
  auth.logout();
  router.push('/login');
};
</script>

<style scoped>
.app-main {
  min-height: calc(100vh - 56px);
  background: #f8f9fa;
  padding: 1rem 0;
}
</style>
