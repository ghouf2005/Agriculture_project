# Modeling, Design Decisions, and Limitations

## Anomaly detection
- Algorithm: Isolation Forest per sensor type; artifacts stored as `model_<sensor>.pkl` under `agriculture_app/`.
- Features: rolling mean/std, first differences, and smoothed derivatives over a sliding window (`FEATURE_WINDOW=10`).
- Calibration: raw decision scores are converted to anomalies using percentile-based thresholds (`raw_start`, `raw_stop`) saved during training and tuned per sensor type.
- Persistence: detections require consecutive hits (`min_consecutive` k) to enter/exit anomaly state, reducing flapping.
- Warmup: minimum context per plot (`max(15, 1.5 * window)`) before any anomaly can be emitted.
- Magnitude filter: after the model flags an anomaly, an additional domain threshold ensures the value is meaningfully outside nominal ranges to cut false positives.
- Caching: detectors are cached per process (`get_detector`) to avoid disk reloads.

## Training workflow
- Script: `train_isolation_forest_per_sensor.py` pulls historical `SensorReading` rows per plot, engineers features, and trains Isolation Forest models with sensor-specific contamination and persistence settings.
- Scaling: robust scaling is fit per sensor type and saved with the model.
- Artifacts: joblib bundle contains model, scaler, feature window, thresholds, persistence k, and metadata for reproducibility.

## Agent and recommendations
- Engine: rule-based in `agent_module.py` with templates for explanations.
- Rules: confidence gate (<0.6 triggers monitor-only), moisture drop over the last hour, high temperature severity, multi-anomaly aggregation, and a default fallback action.
- Outputs: `AgentRecommendation` stores action, explanation, confidence (LOW|MEDIUM|HIGH), and timestamps.

## Limitations and open items
- Data dependency: models need enough per-plot history; warmup drops early points from evaluation and detection.
- Stationarity: percentile thresholds assume relatively stable distributions; sudden concept drift may require retraining.
- Magnitude ranges: hard-coded nominal ranges per sensor; should be configurable per crop/plot.
- Cold-start: new plots have no baseline; consider seeding with regional priors.
- Model lifecycle: no automated retraining scheduler; currently manual via scripts.
- Security: JWT secret defaults to the Django secret key; rotate and store secrets securely for production.

## Future improvements
- Add per-plot or per-crop configurable thresholds and alerting policies.
- Store model version and training metadata on each anomaly for traceability.
- Add evaluation dashboards and drift monitoring.
- Expand rules with weather forecasts or irrigation schedules.
