import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { public: true },
    },
    {
      path: '/plots/:id',
      name: 'plot-detail',
      component: () => import('@/views/PlotDetail.vue'),
      props: true,
      meta: { public: true },
    },
    {
      path: '/alerts',
      name: 'alerts',
      component: () => import('@/views/Alerts.vue'),
      meta: { public: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/dashboard',
    },
  ],
});

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore();
  if (!auth.isHydrated) {
    auth.hydrateFromStorage();
  }
  if (to.meta.public) {
    next();
    return;
  }
  if (auth.isAuthenticated) {
    next();
  } else {
    next({ name: 'login', query: { redirect: to.fullPath } });
  }
});

export default router;
