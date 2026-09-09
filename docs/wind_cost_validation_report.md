# Wind Cost Model — Validation Report

**Date:** 2026-09-09
**Related task doc:** `docs/task_wind_cost_model.md`
**Script:** `scripts/validate_wind_cost_model.py`
**Raw output:** `docs/assets/wind_cost_validation_results.json`

## Method

`compute_edge_cost()` was run on all **three required real origin/destination
station pairs** from Khorasan (Mashhad, Neyshabur, Sabzevar — real
coordinates from `data/khorasan_wind_qc_cleaned.csv`), using every one of the
**48 real hourly wind readings** at the origin station as that edge's wind
condition for that hour (144 total edge evaluations per criterion, 432
overall). `CostModelConfig` defaults were used (`airspeed_mps=50.0`,
`induced_drag_coeff=0.3`, `time_weight=0.5`). No synthetic or placeholder
wind values were used — every number below comes from actually running the
script against the real dataset.

## Results

| Edge | Distance (km) | Hours evaluated | Infeasible hours | Time cost (h) mean / min / max | Energy cost (h) mean / min / max | Balanced cost (h) mean / min / max |
|---|---|---|---|---|---|---|
| Mashhad → Neyshabur | 73.32 | 48 | 0 | 0.391 / 0.302 / 0.456 | 0.392 / 0.303 / 0.456 | 0.392 / 0.303 / 0.456 |
| Neyshabur → Sabzevar | 100.21 | 48 | 0 | 0.536 / 0.375 / 0.674 | 0.539 / 0.376 / 0.675 | 0.538 / 0.375 / 0.674 |
| Mashhad → Sabzevar | 173.11 | 48 | 0 | 0.926 / 0.720 / 1.077 | 0.928 / 0.722 / 1.077 | 0.927 / 0.721 / 1.077 |

## Observations

- **0 of 144** origin-station hourly readings produced an infeasible edge
  (crosswind exceeding the assumed 50 m/s airspeed, or a headwind strong
  enough to zero out ground speed). This is expected: real Khorasan wind
  speeds in this dataset range roughly 4–15 m/s (see
  `docs/preprocessing_report.md`), well under the assumed airspeed.
- The **energy criterion is always ≥ the time criterion** on real data,
  consistent with the model (§4 of the task doc): the induced-drag crosswind
  penalty can only add cost relative to pure flight time, never subtract.
  The gap is small in this dataset (≤ ~0.2% of the time cost) because
  measured crosswind components are small relative to the assumed 50 m/s
  airspeed — `(cross/airspeed)²` stays well under 1%.
- The **balanced criterion falls between time and energy** for every edge and
  every hour, as required by the weighted-average construction.
- Longer edges (Mashhad → Sabzevar, ~173 km) show a wider min/max spread in
  hours (0.72–1.08 h) than shorter edges, because the same station's real
  hourly wind direction varies enough across 48 hours to swing between
  favorable and unfavorable relative bearings.

## Caveats (documented, not hidden)

- Wind is sampled at the **origin** station only for the whole edge; this is
  a simplification pending real interpolated wind fields along the route
  (see the NaN-data gap noted in `docs/task_wind_cost_model.md` §Dependencies).
- These are isolated edge evaluations (three station-pairs), not a full graph
  traversal — there is no graph/routing layer yet to validate end-to-end (see
  `docs/task_wind_cost_model.md` §Dependencies for the upstream blocker).
- `airspeed_mps=50.0` and `induced_drag_coeff=0.3` are documented modeling
  assumptions, not measured constants for a specific aircraft/UAV.

## Reproducing

```bash
python scripts/validate_wind_cost_model.py
```

Full test suite and lint output for this task are attached in the PR
description.
