# Design Decisions & Rationale

- JWT everywhere: SimpleJWT for stateless auth; frontend stores tokens in `localStorage` for simplicity.
- SQLite dev DB: Zero-config local dev; swap to Postgres/MySQL in `DATABASES` as needed.
- Open CORS in dev: `CORS_ALLOW_ALL_ORIGINS=True` for ease; tighten in production.
- Polling (30s): Lightweight near-real-time feel without websockets; adjustable per view.
- Per-sensor models: Separate Isolation Forests per sensor type to keep feature distributions stable.
- In-memory context: Rolling stats kept in-process for feature engineering; avoids extra DB reads per prediction.
- Rule-based agent: Transparent, deterministic actions/explanations; easy to extend; complements ML detector.
