# Architecture Overview

## High-level components
- Backend: Django REST Framework with JWT auth (SimpleJWT), served via Gunicorn in Docker. Core app: `agriculture_app`.
- Persistence: PostgreSQL 15. Models cover farms, plots, sensor readings, anomalies, and agent recommendations.
- ML layer: Isolation Forest per sensor type with calibrated thresholds and persistence logic (`agriculture_app/ml_model.py`). Models are trained offline and loaded in-process.
- Agent layer: Rule-based recommendation engine triggered on confirmed anomalies (`agriculture_app/agent_module.py`).
- Frontend: Vue 3 + Vite + Pinia, Bootstrap styling. Consumes the REST API and stores JWTs in localStorage.
- Simulator: Scripted data generator in `SOA/DS2/simulator` (produces sensor readings and ground-truth CSVs for evaluation).

## Data flow (ingest to insight)
1. Sensor (or simulator) sends a reading to `POST /api/sensor-readings/create/`.
2. DRF view persists the reading, fetches the cached detector for that sensor type, and computes anomaly flags with warmup, rolling features, hysteresis, and magnitude filtering.
3. On confirmed anomaly, an `AnomalyEvent` is created with severity derived from model confidence.
4. The agent module evaluates rules (confidence gating, moisture drop, heat stress, multi-anomaly) and emits an `AgentRecommendation` with an explanation template.
5. Frontend dashboards list plots, anomalies, and recommendations via `/api/plots`, `/api/anomalies`, and `/api/recommendations`.

## Key modules
- URL routing: `agriculture_sys_project/urls.py` delegates `/api/*` to `agriculture_app.urls`.
- Views: DRF generic views with per-user filtering in `agriculture_app/views.py`.
- Domain models: `agriculture_app/models.py` with indexes for owners, simulated time, and sensor fields.
- Serialization: `agriculture_app/serializers.py` exposes convenience aliases expected by the frontend.
- Detection logic: `agriculture_app/ml_model.py` (feature engineering, hysteresis, per-plot context) plus persisted `model_*.pkl` artifacts.
- Rule engine: `agriculture_app/agent_module.py` builds actionable recommendations and explanations.
- Frontend routing/auth: `frontend/src/router/index.ts`, `frontend/src/stores/auth.ts`, API client in `frontend/src/api/client.ts`.

## Deployment topology
- Docker Compose services: `db` (PostgreSQL), `backend` (Gunicorn + Django), `frontend` (static Nginx container).
- Default ports: 5432 (DB), 8000 (API), 3000 (frontend).
- CORS is currently permissive (allow all) for development; tighten for production.

## Observability and ops
- Logs: standard output from Gunicorn/Django; model predictions print to console when anomalies are processed.
- Migrations: managed via `python manage.py migrate` (run automatically in the Docker startup command).
- Static files: `collectstatic` is executed in the container entrypoint.
