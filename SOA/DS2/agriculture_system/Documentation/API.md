# API Documentation
Base URL defaults to `http://localhost:8000/api`. All endpoints use JSON and require a Bearer JWT unless marked public.

## Authentication
- `POST /auth/token/` — obtain access and refresh tokens.
- `POST /auth/token/refresh/` — refresh access token.

Headers for authenticated calls:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Farms and plots
- `GET /farms/` — list farms for the current user (admins see all).
- `GET /plots/` — list plots; optional query `?id=<plot_id>` to filter.
- `GET /plots/<id>/` — retrieve a single plot.
- `GET /farms/<farm_id>/plots/` — list plots belonging to a farm.

Response fields:
```
FieldPlot: { id, farm, name, crop_variety, farm_name }
FarmProfile: { id, owner, location, size, crop_type }
```

## Sensor readings
- `POST /sensor-readings/create/` — create a reading. Body:
```
{ "plot": 1, "sensor_type": "TEMPERATURE|HUMIDITY|MOISTURE", "value": 23.4, "simulated_time": "2025-01-01T06:00:00Z" }
```
- `GET /sensor-readings/?plot=<plot_id>` — list readings (filtered by plot when provided).

On create, the backend will run anomaly detection for the corresponding sensor type and may emit an `AnomalyEvent` plus an `AgentRecommendation`.

## Anomalies
- `GET /anomalies/?plot=<plot_id>` — list anomalies visible to the user (filter optional).

`AnomalyEvent` fields: `{ id, plot, anomaly_type, severity, model_confidence, simulated_time, timestamp }`.

## Recommendations
- `GET /recommendations/?anomaly=<id>` — list recommendations; optional filter by anomaly id.

`AgentRecommendation` fields:
```
{
  id,
  anomaly_event,            // FK
  anomaly_id,               // convenience alias
  anomaly: { ...AnomalyEvent },
  action,                   // recommended_action
  explanation,              // explanation_text
  confidence,               // LOW|MEDIUM|HIGH
  simulated_time,
  created_at,               // timestamp
  timestamp
}
```

## Error handling
- JWT errors: HTTP 401.
- Permission errors: HTTP 403 when accessing another user's farm/plot.
- Validation errors: HTTP 400 with field-level messages from DRF serializers.

## Development notes
- All routes live in `agriculture_app.urls` and use DRF generic views.
- Default permissions enforce authentication globally; adjust in `settings.py` if exposing public endpoints.
