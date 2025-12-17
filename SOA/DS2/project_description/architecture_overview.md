# Architecture Overview

- **Backend API (Django + DRF + SimpleJWT):** Core app `agriculture_app` exposes plots, readings, anomalies, recommendations. Located in `SOA/DS2/agriculture_system/agriculture_sys_project`.
- **Frontend (Vue 3 + Vite):** Dashboard for plots, charts, alerts, auth. Located in `SOA/DS2/agriculture_system/frontend`.
- **Simulator:** Generates synthetic sensor readings/anomalies for demos. Located in `SOA/DS2/simulator`.

Data flow:
1) Simulator or devices POST sensor readings to `/api/sensor-readings/`.
2) Backend runs Isolation Forest + thresholds; anomalous readings create `AnomalyEvent` and trigger `AgentRecommendation`.
3) Frontend polls `/api/plots/`, `/api/sensor-readings/?plot=`, `/api/anomalies/`, `/api/recommendations/` for dashboards/charts/alerts.

Auth: JWT via SimpleJWT; tokens stored in frontend `localStorage`; Axios interceptor adds `Authorization: Bearer <token>`.
