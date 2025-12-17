# ML & Agent Design

- Detector: Isolation Forest per sensor type loaded in `agriculture_app/ml_model.py`; feature window with value, rolling mean/std, diff, derivative; per-plot context maintained in memory.
- Thresholding: After model score, view-level thresholds per sensor (`TEMPERATURE` 0.55, `HUMIDITY` 0.60, `MOISTURE` 0.52; else 0.15) gate anomaly creation.
- Anomaly typing: Maps sensor/value to high/low types; severity derived from confidence score buckets (low/med/high).
- Agent recommendations: Rule-based engine in `agriculture_app/agent_module.py`; checks confidence, moisture drops over 1h, heat stress, multi-anomaly context, fallback default; generates explanation templates and `AgentRecommendation` rows.
- Serialization: Aliases provided in `agriculture_app/serializers.py` to match frontend field expectations (`action`, `explanation`, `anomaly_id`, etc.).
