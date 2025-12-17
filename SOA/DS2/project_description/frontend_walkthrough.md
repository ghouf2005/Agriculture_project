# Frontend Walkthrough

- App wiring: `src/main.ts` bootstraps Vue, Pinia, Router, Bootstrap CSS; shell in `src/App.vue`.
- Auth: Pinia store `src/stores/auth.ts`; Axios client with bearer interceptor `src/api/client.ts`.
- Routes: login, dashboard, plot detail, alerts in `src/router/index.ts`; public by default, guard hydrates tokens.
- Views:
  - Dashboard: plots + anomaly badge, polls 30s (`src/views/Dashboard.vue`).
  - Plot Detail: chart + snapshot + anomalies, polls 30s (`src/views/PlotDetail.vue`); chart component in `src/components/SensorChart.vue`.
  - Alerts: recommendations joined to anomalies, polls 30s (`src/views/Alerts.vue`).
  - Login: JWT sign-in (`src/views/Login.vue`).
