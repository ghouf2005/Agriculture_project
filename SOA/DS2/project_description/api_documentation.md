# API Documentation (summary)

Live docs once the server runs:
- Swagger UI: http://localhost:8000/api/docs
- Redoc: http://localhost:8000/api/redoc

Core models: farms, plots, sensor readings, anomalies, agent recommendations (see `agriculture_app/models.py`); enums in `agriculture_app/enumerations.py`.

Key endpoints (JWT required unless noted):
- POST `/api/auth/token/` → access/refresh
- GET `/api/plots/` (filter `?id=`), GET `/api/plots/<id>/`
- GET `/api/farms/<farm_id>/plots/`
- GET|POST `/api/sensor-readings/` (list/create); POST `/api/sensor-readings/create/`
- GET `/api/anomalies/` (filter `?plot=`)
- GET `/api/recommendations/` (filter `?anomaly=`)

Auth default: DRF global permission is authenticated; dev CORS is open in settings.
