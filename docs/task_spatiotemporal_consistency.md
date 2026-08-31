# Spatiotemporal Consistency Check — Stage 2: بررسی و اعتبارسنجی پیوستگی زمانی و مکانی داده‌ها

**Date:** 2026-08-31
**Owner:** AmirAli
**Status:** Done
**ClickUp Task:** بررسی و اعتبارسنجی پیوستگی زمانی و مکانی داده‌ها (Stage 2, step 2)
**Priority:** Normal
**Deadline:** 28 Mordad 1405, 17:00 Iran Time

> **Note:** This file previously contained a pre-implementation placeholder
> sketching a broader design (grid coverage, Moran's I, ACF/PACF). That sketch
> did not match the actual ClickUp task scope (gap detection, neighbor
> consistency, thresholds, gap-fix strategy, report, sample code/docs), so it
> is replaced here with the as-built documentation. The more advanced spatial/
> temporal autocorrelation ideas are kept under Future Improvements below.

---

## Implementation Summary

This task validates that the preprocessed wind dataset is continuous in time
(no unexpected sampling gaps within a station) and consistent in space (no
implausible disagreement between geographically neighboring stations at the
same timestamp). It adds a dedicated `SpatiotemporalConsistencyChecker` that
detects and classifies time gaps, flags spatial disagreement beyond
data-calibrated thresholds, proposes a linear-interpolation fix for short
gaps, and produces a single JSON-serializable continuity report consumed by
downstream preprocessing/pathfinding steps.

---

## Task Checklist (Items to Check)

| Item | Status | Details |
|------|--------|---------|
| **1.** Detect temporal gaps | ✅ Done | `check_temporal_gaps()` — per-station, based on `expected_interval_hours` |
| **2.** Check spatial inconsistency between neighboring stations | ✅ Done | `check_spatial_consistency()` — haversine-based neighbor pairing + speed/direction diff |
| **3.** Define acceptable thresholds | ✅ Done | `ConsistencyConfig` — calibrated against the reference Khorasan dataset (see below) |
| **4.** Provide a gap-fix / interpolation strategy | ✅ Done | `fill_fixable_gaps()` — linear interpolation on speed, circular interpolation on direction, bounded by `max_fixable_gap_steps` |
| **5.** Produce a continuity report | ✅ Done | `generate_report()` |
| **6.** Sample code | ✅ Done | See Usage Example below |
| **7.** Documentation | ✅ Done | This file |

---

## Produced Outputs

### 1. Implementation Code
- File: `src/preprocessing/consistency.py`
- Main class: `SpatiotemporalConsistencyChecker`
- Supporting: `ConsistencyConfig`, `haversine_km()`, `circular_diff_deg()`
- Capabilities:
  - Per-station temporal gap detection with fixable/unfixable classification
  - Linear/circular interpolation fill for short gaps (`missing_steps <= max_fixable_gap_steps`)
  - Distance-limited neighbor pairing (haversine) and speed/direction disagreement check
  - Single combined JSON-ready report (`generate_report`)

### 2. Tests
- File: `tests/preprocessing/test_consistency.py` (12 cases)
- Coverage: haversine distance sanity check, circular-difference wraparound,
  no-gap on clean data, fixable-gap detection, unfixable-gap detection,
  interpolation correctness, spatial consistency on matching neighbors,
  spatial violation detection, distance-cutoff exclusion, report structure,
  missing-column validation.

### 3. Design Documentation
- This file.

---

## Usage Example

```python
import pandas as pd
from preprocessing.consistency import SpatiotemporalConsistencyChecker

df = pd.read_csv("data/khorasan_wind_qc_cleaned.csv")

checker = SpatiotemporalConsistencyChecker()
report = checker.generate_report(df)

print(report["temporal"]["total_gaps"], "time gaps found")
print(report["spatial"]["violations"], "spatial disagreements found")

# Optionally materialize the interpolated records for fixable gaps:
filled_df = checker.fill_fixable_gaps(df)
```

---

## Dependencies

- **Prerequisite:** Wind QC task (`src/qc/wind_qc.py`, Mehdi) — this task
  consumes its cleaned output (`data/khorasan_wind_qc_cleaned.csv`) and is no
  longer blocked once QC produced clean data.
- **Depends on:** Data prep for pathfinding (`pathfinding_preparation.py`) can
  use `fill_fixable_gaps()` output as an optional pre-step once a gapped
  dataset appears; not required for the current gap-free reference dataset.

---

## Technical Notes

- **Architecture:** Two independent checks (temporal, spatial) composed into
  one report; both operate on the same tidy `timestamp, station, lat, lon,
  speed, direction` schema already used by `WindQualityControl`, so the
  checker can run directly on QC output with no reshaping.
- **Threshold calibration:** Run against the reference Khorasan dataset
  (Mashhad–Neyshabur 73 km, Neyshabur–Sabzevar 100 km, Mashhad–Sabzevar
  173 km, 144 hourly records):
  - `max_speed_diff = 15.0 m/s` — close to the 90th percentile (16.3 m/s) of
    observed pairwise speed differences.
  - `max_direction_diff_deg = 150.0°` — close to the 90th percentile (151°)
    of observed pairwise direction differences. Raw direction disagreement
    between stations 70–170 km apart is naturally wide because of local
    topography, so a strict threshold (e.g. 90°) produced a ~53% false-flag
    rate on the reference data; 150° only flags near-total direction
    reversals.
  - `max_neighbor_distance_km = 250.0` — comfortably covers all three
    Khorasan station pairs while excluding stations far enough apart that
    comparing them directly is not meaningful.
  - `max_fixable_gap_steps = 2` — gaps of one or two missing hourly steps are
    filled by interpolation; anything longer is only reported, not guessed.
- **On the reference dataset:** 0 temporal gaps (data is fully hourly and
  complete), 144 spatial comparisons across 3 neighbor pairs, 33 flagged as
  disagreements above threshold (worth a manual look, not necessarily
  errors — see calibration note above).
- **Parameters:** All thresholds are configurable via `ConsistencyConfig`;
  defaults above are a starting point, not a hard physical law, and should be
  revisited as more stations/seasons are added.

---

## Future Improvements

1. Replace the fixed absolute direction/speed thresholds with a
   distance-scaled or z-score-based criterion (similar to
   `WindQualityControl`'s spatial z-score check) once more station pairs at
   varied distances are available.
2. Add spatial autocorrelation (Moran's I) and temporal autocorrelation
   (ACF/PACF) diagnostics as a follow-up analytical task once the station
   network is denser — the current dataset (3 stations, 2 days) is too small
   for these to be statistically meaningful.
3. Feed `fill_fixable_gaps()` output directly into
   `pathfinding_preparation.py` once a real gapped dataset is available for
   integration testing.

---

## Conclusion

All checklist items are implemented, tested (12/12 passing), and validated
against the real Khorasan reference dataset. The module is ready for use by
downstream preprocessing/pathfinding steps and does not modify the raw QC
output files.
