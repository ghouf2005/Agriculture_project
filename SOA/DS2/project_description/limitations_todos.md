# Limitations / TODOs

- Model files (`model_*.pkl`) must exist on the server; missing models skip detection for that sensor type.
- In-memory context resets on process restart; for long-running prod, persist recent windows (cache/DB) or rewarm from history.
- Polling may miss instant updates; websockets/Server-Sent Events would improve latency.
- CORS and DEBUG are dev-friendly defaults; harden for production.
- SQLite not ideal for scale; migrate to a managed DB for production.
- Thresholds/severity buckets are heuristic; tune per crop/region.
- No rate limiting on ingest endpoints; add if exposed publicly.
