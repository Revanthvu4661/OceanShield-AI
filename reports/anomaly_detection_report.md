# Phase 3 Anomaly Detection Report

## What was built

- Added a background anomaly watcher on top of the autonomous snapshot worker.
- The watcher compares each new station sample against that station’s recent baseline.
- It flags two proactive anomaly classes:
  - `pressure_drop` when pressure falls at least 4 hPa below the recent station baseline.
  - `wave_severity_spike` when the current wave severity jumps by at least 0.65 above baseline.
- Anomalies are persisted to SQLite immediately with severity, baseline, delta, and rule metadata.
- Added API access to the latest anomaly feed through the background status endpoint and a dedicated anomalies route.

## Files created or updated

- [backend/storage.py](D:/ocean/backend/storage.py)
- [backend/background_jobs.py](D:/ocean/backend/background_jobs.py)
- [backend/routes/background.py](D:/ocean/backend/routes/background.py)
- [backend/schemas.py](D:/ocean/backend/schemas.py)
- [reports/anomaly_detection_report.md](D:/ocean/reports/anomaly_detection_report.md)

## Key findings

- The watcher uses the same engineered feature logic as the prediction pipeline, so anomaly detection stays aligned with the model inputs.
- Pressure anomalies are based on the background stream’s recent local baseline rather than a static global threshold.
- Wave severity spikes are computed from the current sample’s sigheight, swellheight, period, and wind gust behavior.
- The anomaly store now gives the system a durable audit trail for proactive states.

## Recommended next step

- Proceed to Phase 4 and make the route advisor proactively recommend safer alternatives when a high-risk route is detected.
