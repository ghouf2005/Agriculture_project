# Evaluation Results Summary

- ML detectors: Isolation Forests per sensor type with rolling-feature engineering; thresholds set at 0.55 (temperature), 0.60 (humidity), 0.52 (moisture) to curb false positives. No formal precision/recall benchmark recorded in repo; validated informally with simulator streams.
- Agent rules: Verified to emit recommendations on anomaly creation with context-aware messaging (moisture drop, heat stress, multi-anomaly). Confidence bands are qualitative (LOW/MEDIUM/HIGH) and not calibrated to empirical outcomes.
- Gaps: No offline labeled test evaluation or confusion matrix. Next steps: replay labeled simulator data, log TP/FP/FN, compute precision/recall/F1, and retune thresholds.
