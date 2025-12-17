# Agriculture Monitoring System Documentation

This folder contains project-level documentation for the DS2 Agriculture monitoring platform (Django REST backend, Vue 3 frontend, Isolation Forest anomaly detection, and a rule-based recommendation agent).

## Contents
- Architecture overview: see `Architecture.md`
- API reference: see `API.md`
- Modeling and design decisions: see `Modeling.md`
- Evaluation results summary: see `Evaluation.md`

## Prerequisites
- Docker Desktop (recommended path) or Python 3.11+, Node 18+
- PostgreSQL 15 (if running services locally without Docker)
- pipenv for backend virtualenv management; npm or pnpm for frontend

### Environment variables
Create a `.env` in `SOA/DS2/agriculture_system` for Docker, and another in `SOA/DS2/agriculture_system/agriculture_sys_project` when running locally. Minimum keys:
```
DB_NAME=agri_db
DB_USER=agri_user
DB_PASSWORD=agri_pass
DB_HOST=postgres_db
DB_PORT=5432
SECRET_KEY=change-me
JWT_SECRET=change-me
DJANGO_SETTINGS_MODULE=agriculture_sys_project.settings
VITE_API_BASE_URL=http://localhost:8000/api
```
Adjust `DB_HOST=localhost` when not using Docker.

## Quick start (Docker)
1) From `SOA/DS2/agriculture_system`, build and start:
```
docker compose up --build
```
2) Backend is exposed on http://localhost:8000, frontend on http://localhost:3000.
3) Create a superuser for login:
```
docker compose exec backend python manage.py createsuperuser
```

## Local development (without Docker)
Backend:
```
cd SOA/DS2/agriculture_system/agriculture_sys_project
pipenv install --dev
pipenv run python manage.py migrate
pipenv run python manage.py createsuperuser
pipenv run python manage.py runserver 0.0.0.0:8000
```

Frontend:
```
cd SOA/DS2/agriculture_system/frontend
npm install
npm run dev -- --host --port 3000
```

## Data and models
- Models are trained per sensor type via `train_isolation_forest_per_sensor.py` and saved as `model_*.pkl` in `agriculture_app/`.
- To evaluate production logic on labeled CSVs, run `evaluate_isolation_forest.py` (see `Evaluation.md`).

## Useful paths
- Backend service: `agriculture_sys_project/`
- Core app: `agriculture_sys_project/agriculture_app/`
- Frontend: `frontend/`
- Simulator and data generation: `SOA/DS2/simulator/`

See the other documents in this folder for details on API usage, architecture, modeling decisions, and evaluation steps.
