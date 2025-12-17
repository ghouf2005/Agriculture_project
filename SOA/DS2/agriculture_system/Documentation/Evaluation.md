# Evaluation Results Summary

This document tracks anomaly detection performance using the production decision logic (feature engineering, thresholds, persistence, and magnitude filtering).

## How to run evaluation
1) Generate or collect labeled data with `ground_truth_anomalies.csv` (from the simulator or real logs). Expected columns: `timestamp`, `plot`, `sensor_type`, `value`, `is_anomaly` (0/1).
2) From `agriculture_sys_project`, ensure models are trained and present in `agriculture_app/model_*.pkl`.
3) Run:
```
pipenv run python evaluate_isolation_forest.py
```
4) For each sensor type, capture TP/TN/FP/FN plus Precision, Recall, F1, and FPR printed by the script.

## Current results
Fill in after each run (per dataset version). Example structure:

| Sensor type | Dataset version | TP | TN | FP | FN | Precision | Recall | F1 | FPR |
|-------------|-----------------|----|----|----|----|-----------|--------|----|-----|
| TEMPERATURE | YYYY-MM-DD      |    |    |    |    |           |        |    |     |
| HUMIDITY    | YYYY-MM-DD      |    |    |    |    |           |        |    |     |
| MOISTURE    | YYYY-MM-DD      |    |    |    |    |           |        |    |     |

## Notes and observed behavior
- Warmup window discards the first `window` predictions per plot; ensure datasets are long enough.
- Persistence `k` and magnitude filters materially reduce false positives; tune in tandem with contamination during training.
- Re-evaluate after any threshold, feature window, or rule changes.
