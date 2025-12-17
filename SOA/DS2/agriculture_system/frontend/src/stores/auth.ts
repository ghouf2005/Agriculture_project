import { defineStore } from 'pinia';
import axios from 'axios';

interface LoginResponse {
  access: string;
  refresh?: string;
}

const TOKEN_KEY = 'agri_token';
const REFRESH_KEY = 'agri_refresh';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: '' as string,
    refreshToken: '' as string,
    isHydrated: false,
    loading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },
  actions: {
    hydrateFromStorage() {
      if (this.isHydrated) return;
      this.accessToken = localStorage.getItem(TOKEN_KEY) || '';
      this.refreshToken = localStorage.getItem(REFRESH_KEY) || '';
      this.isHydrated = true;
    },
    async login(username: string, password: string) {
      this.loading = true;
      this.error = '';
      try {
        const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
        const { data } = await axios.post<LoginResponse>(`${base}/auth/token/`, {
          username,
          password,
        });
        this.accessToken = data.access;
        this.refreshToken = data.refresh || '';
        localStorage.setItem(TOKEN_KEY, data.access);
        if (data.refresh) {
          localStorage.setItem(REFRESH_KEY, data.refresh);
        }
      } catch (err: any) {
        this.error = err?.response?.data?.detail || 'Login failed';
        throw err;
      } finally {
        this.loading = false;
      }
    },
    logout() {
      this.accessToken = '';
      this.refreshToken = '';
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
    },
  },
});
