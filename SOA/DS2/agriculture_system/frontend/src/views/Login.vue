<template>
  <div class="container py-5" style="max-width: 480px;">
    <div class="card shadow-sm">
      <div class="card-body">
        <h3 class="card-title mb-3 text-center">Sign in</h3>
        <p class="text-muted text-center">Use your Django credentials to continue.</p>
        <form @submit.prevent="submit">
          <div class="mb-3">
            <label class="form-label">Username</label>
            <input
              v-model="username"
              class="form-control"
              type="text"
              autocomplete="username"
              required
            />
          </div>
          <div class="mb-3">
            <label class="form-label">Password</label>
            <input
              v-model="password"
              class="form-control"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>
          <button class="btn btn-success w-100" :disabled="auth.loading">
            {{ auth.loading ? 'Signing in...' : 'Login' }}
          </button>
          <p v-if="auth.error" class="text-danger mt-3 mb-0">{{ auth.error }}</p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const username = ref('');
const password = ref('');
const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const submit = async () => {
  try {
    await auth.login(username.value, password.value);
    const redirect = (route.query.redirect as string) || '/dashboard';
    router.push(redirect);
  } catch (err) {
    console.error('Login failed', err);
  }
};
</script>
