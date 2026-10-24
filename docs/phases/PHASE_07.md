# Phase 07 ? Predictive AI and reliability

Status: Planned; not implemented.

## Prerequisites
Quality-controlled Phase 05 history and Phase 06 outcomes; consent and evaluation plan.

## Implementation tasks
- [ ] Introduce versioned scikit-learn/XGBoost offline feature pipelines
- [ ] Predict ETA ranges, transfer risk and no-show probability without declaring cancellation from missing GPS
- [ ] Use temporal train/validation/test splits, route/operator slices and leakage checks
- [ ] Compare schedule/recent-history baselines; calibrate uncertainty and record model lineage
- [ ] Guard inference with feature flags, drift monitoring, latency bounds and rollback

## Expected deliverables
Reproducible training, model cards, held-out evaluation and guarded inference.

## Edge cases
Sparse route; festival surge; seasonal drift; missing features; unseen operator; inference outage; privacy deletion.

## Automated tests
Temporal leakage checks; reproducibility; calibration/error by route; missing-feature fallback; drift triggers; rollback and load tests.

## Completion criteria
Model improves declared baseline on held-out time windows; calibration/latency gates pass; missing telemetry never becomes a confirmed cancellation claim.

## Safety gate
Missing GPS means uncertainty, never confirmed cancellation. Separate evidence confidence, authorized verification and freshness. Require network impact validation before automatic live rerouting. Keep simulation labels visible.
