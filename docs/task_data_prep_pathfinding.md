# Data Preparation for Pathfinding (آماده‌سازی داده ورودی مسیریابی) — Stage 2

**Date:** 2026-08-31
**Owner:** Mehdi
**Status:** Done (see "Known Gaps" below — two upstream dependencies are not fully finished)
**ClickUp Task:** provided as pasted task text, no URL/ID given
**Priority:** Normal
**Deadline:** 1405-05-29, 17:00 Iran Time (already past as of this PR)

---

## Implementation Summary

Converts preprocessed wind data (from QC / IDW / Kriging) into the standard
input format the pathfinding algorithm consumes: a regular lat/lon grid, one
record per altitude level between 500-2000 m, unified units (m/s, degrees),
and normalized wind vector components. This replaces an earlier, unrelated
draft of this doc that described a `networkx` graph-building deliverable —
that design was never implemented and did not match this task's checklist;
see "Note on prior documentation" below.

---

## Task Checklist (Items to Check)

| Item | Status | Details |
|------|--------|---------|
| **1.** Convert data to a regular grid | ✅ Done | `prepare_for_pathfinding` builds a full `timestamp × altitude × lat × lon` grid via `pd.MultiIndex.from_product` and left-merges observed data onto it, so every grid cell exists even where no observation was recorded. |
| **2.** Unify units (m/s and degrees) | ✅ Done | New `normalize_units()` accepts `speed`/`wind_speed` and `direction`/`wind_direction` column aliases, converts speed to m/s (`m/s`, `km/h`, `kt` supported via `speed_unit=`), rejects negative speeds, and wraps direction into `[0, 360)`. |
| **3.** Build wind vectors across altitudes (500-2000 m) | ✅ Done | `DEFAULT_ALTITUDES = (500.0, 1000.0, 1500.0, 2000.0)`; `speed_direction_to_uv` / `uv_to_speed_direction` convert between the two representations so either can be supplied. |
| **4.** Normalize values | ✅ Done | `normalize_components()` produces unit-length `u_normalized`/`v_normalized` vectors (zero-magnitude rows safely map to 0, not NaN or divide-by-zero). |
| **5.** Define a standard output format | ✅ Done | See `docs/PATHFINDING_DATA_FORMAT.md` (updated in this PR with the units section). |
| **6.** Sample code and docs | ✅ Done | Usage example below; tests in `tests/test_pathfinding_preparation.py`. |

---

## Produced Outputs

### 1. Implementation Code
- File: `src/preprocessing/pathfinding_preparation.py`
- Functions:
  - `normalize_units(data, speed_unit="m/s")` — column-alias + unit unification (new in this PR)
  - `speed_direction_to_uv(wind_speed, wind_direction)` / `uv_to_speed_direction(u, v)`
  - `normalize_components(u, v)`
  - `prepare_for_pathfinding(data, lat_step, lon_step, altitude_levels=DEFAULT_ALTITUDES, normalize=True, speed_unit="m/s")`
- Exported from `preprocessing.__init__` for convenience.

### 2. Tests
- File: `tests/test_pathfinding_preparation.py`
- Coverage: base grid construction, full 500-2000 m altitude range, `speed`/`direction` alias handling, km/h → m/s conversion, negative-speed rejection, unsupported-unit rejection, `prepare_for_pathfinding` with non-canonical units end-to-end.

### 3. Design Documentation
- This file, plus `docs/PATHFINDING_DATA_FORMAT.md` for the output schema.

---

## Usage Example

```python
import pandas as pd
from preprocessing import prepare_for_pathfinding

df = pd.DataFrame({
    "timestamp": ["2026-08-29T00:00:00"] * 2,
    "lat": [36.297, 36.297],
    "lon": [59.606, 59.606],
    "altitude": [500.0, 1000.0],
    "speed": [18.7, 24.1],       # km/h, aliased to wind_speed
    "direction": [286.0, 297.0],
})

prepped = prepare_for_pathfinding(
    df, lat_step=0.25, lon_step=0.25, speed_unit="km/h",
)
# prepped now has canonical wind_speed (m/s), wind_direction (deg),
# u, v, u_normalized, v_normalized, on a regular lat/lon/altitude/timestamp grid.
```

---

## Dependencies

- **Prerequisite:** IDW Interpolation (done, PR #1) and Kriging Interpolation (done, PR #2) — merged.
- **Prerequisite:** Wind Data Quality Control — status is ambiguous. `docs/PROJECT_PROGRESS.md` records it as incomplete ("no tests, no real Open-Meteo data, pushed directly to main"), but `src/qc/wind_qc.py` now has 32 passing tests on `main`. Its actual completion state should be confirmed by whoever owns that task.
- **Prerequisite:** Spatiotemporal Consistency — **not started**. `src/preprocessing/consistency.py` does not exist.
- **Blocks:** Preprocessing Report & Docs.

### Known Gaps

Per direction from the task owner, this PR proceeds despite the two prerequisite
gaps above rather than waiting on them. Concretely, this means:
- `prepare_for_pathfinding` has not been validated against real QC or
  consistency-checked output, only against the existing sample data and
  synthetic test fixtures.
- If the eventual QC/Consistency modules change their output column names or
  units, this module's alias list in `normalize_units()` may need updating.

### Note on prior documentation

This file previously described an unimplemented, unrelated design (a
`networkx`-based `build_wind_graph` / `export_graph` API in a file called
`data_prep.py`, with every checklist box left unchecked and placeholders like
`[Task ID/URL]` never filled in). That never matched the actual code in
`pathfinding_preparation.py` and appears to have been a stub introduced
alongside unrelated documentation work (PR #8) rather than a completed task.
It has been replaced with this document, which describes what is actually
implemented and tested.

The sample file `data/khorasan_pathfinding_ready.csv` uses `speed`/`direction`
column names rather than `wind_speed`/`wind_direction`; `normalize_units()`
now handles both, but this is called out here since it was a real, silent
mismatch between that sample data and the code that predates this PR.

---

## Technical Notes

- **Architecture:** grid-first approach — build the full coordinate grid, then
  left-merge available observations onto it, so downstream pathfinding code
  can rely on a dense, regular structure (missing cells become `NaN` wind
  values rather than absent rows).
- **Parameters:** `speed_unit` defaults to `"m/s"`; pass `"km/h"` or `"kt"` if
  the upstream source uses those units instead.
- **Units:** canonical output is always m/s and degrees `[0, 360)`, regardless
  of input unit/column naming.

---

## Future Improvements

1. Once Spatiotemporal Consistency lands, wire its output directly into this
   module's expected schema (or extend `normalize_units()` if it introduces
   new column names).
2. Confirm QC's real status with its owner and, if genuinely incomplete,
   re-run this module against corrected QC output.
3. Consider interpolating missing grid cells (currently left as `NaN`) rather
   than leaving gaps, once IDW/Kriging are wired in upstream of this step.

---

## Conclusion

The checklist items for this task (grid conversion, unit unification, wind
vectors across the 500-2000 m altitude range, normalization, standard output
format, sample code/docs) are implemented and covered by passing tests. The
two upstream prerequisites (QC, Consistency) are not confirmed complete; this
was flagged to the task owner, who chose to proceed now rather than wait.
