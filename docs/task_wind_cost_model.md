# Wind Cost Model & Validation — Stage 3: مدل کامل هزینه بادی و اعتبارسنجی

**Date:** 2026-09-09
**Owner:** Mehdi (محمد مهدی دستگیر)
**Status:** Done (edge cost library) / Blocked-upstream (graph integration — see Dependencies)
**ClickUp Task:** Complete Wind Cost Model & Validation (مدل کامل هزینه بادی و اعتبارسنجی)
**Priority:** High
**Deadline:** 20 Shahrivar 1405, 20:00 Iran Time

---

## Implementation Summary

This task implements `compute_edge_cost()` in `src/pathfinding/cost.py`: a
dynamic edge-cost function for the (future) pathfinding graph that decomposes
real measured wind into an along-track component (tailwind help / headwind
resistance) and a cross-track component (crosswind), and prices an edge under
three selectable optimality criteria — minimum time, minimum energy, and a
user-weighted balance of the two. No placeholder or mock values are used;
every cost is computed from the two edge endpoints' real coordinates and a
real (speed, direction) wind reading.

---

## Task Checklist (Items to Check)

| Item | Status | Details |
|------|--------|---------|
| **1.** Along-track and cross-track components both feed the edge cost | ✅ Done | `decompose_wind()`; both components used in ground speed (§Model) and in the energy penalty. |
| **2.** Three optimality criteria with adjustable weight | ✅ Done | `criterion="time"/"energy"/"balanced"`, `time_weight` adjustable per call or via `CostModelConfig`. |
| **3.** Validation script on ≥3 real origin/destination pairs, numeric results documented | ✅ Done | `scripts/validate_wind_cost_model.py`, 3 Khorasan station pairs × 48 real hourly readings each. See `docs/wind_cost_validation_report.md`. |
| **4.** ≥8 unit tests, all green | ✅ Done | `tests/pathfinding/test_cost.py` — 19 tests, all passing. |
| **5.** Cost model doc with real numeric tables | ✅ Done | This file, §Worked Examples. |
| **6.** Separate validation report with numeric results | ✅ Done | `docs/wind_cost_validation_report.md`. |
| **7.** Full test/validation-script output attached to PR | ✅ Done | See PR body. |

---

## Model

### 1. Wind decomposition (`decompose_wind`)

Given the edge's initial great-circle bearing `θ_path` (`initial_bearing_deg`,
computed from the real endpoint coordinates — not assumed) and a wind reading
`(speed, direction_from)` in standard meteorological convention:

```
direction_to  = (direction_from + 180) mod 360        # where the wind blows toward
Δ             = θ_path − direction_to
along_track   = speed · cos(Δ)   # signed: + tailwind, − headwind
cross_track   = |speed · sin(Δ)| # unsigned crosswind magnitude
```

### 2. Ground speed (`ground_speed_mps`)

Classic wind-triangle navigation: the pilot corrects heading to null out the
crosswind drift, which costs some of the airspeed budget:

```
ground_speed = √(airspeed² − cross_track²) + along_track
```

If `cross_track > airspeed`, the heading cannot be held at all
(`InfeasibleEdgeError`). If the resulting `ground_speed ≤ 0` (headwind
overwhelms airspeed), the edge is also flagged infeasible rather than
silently producing a negative/undefined travel time.

### 3. Time criterion

```
time_hours = distance_km / (ground_speed_mps · 3.6)
```

### 4. Energy criterion

Crosswind requires extra bank/angle-of-attack to hold heading, which adds
induced drag independent of head/tailwind. This is modeled as a multiplicative
penalty on the time already spent in the air:

```
energy_hours = time_hours · (1 + k · (cross_track / airspeed)²)
```

`k` is `CostModelConfig.induced_drag_coeff` (default `0.3`, a tunable
assumption — not a measured aerodynamic constant; documented here rather than
buried in code). Headwind/tailwind still affects energy through `time_hours`
(flying longer at constant power burns more fuel), which is physically
consistent even though it isn't a second free parameter.

### 5. Balanced criterion (user-adjustable weight)

```
balanced_hours = w · time_hours + (1 − w) · energy_hours
```

`w = time_weight ∈ [0, 1]`, overridable per call without rebuilding
`CostModelConfig`.

### Assumptions (explicit, not hidden)

| Parameter | Default | Meaning |
|---|---|---|
| `airspeed_mps` | 50.0 m/s (≈180 km/h) | Assumed constant true airspeed of the vehicle. Must be overridden per vehicle type once one is specified. |
| `induced_drag_coeff` | 0.3 | Crosswind → energy penalty strength. Tunable; not derived from a real aircraft polar. |
| `time_weight` | 0.5 | Default balance point for the "balanced" criterion. |

---

## Worked Examples (real Khorasan station data)

Coordinates are the real station coordinates from
`data/khorasan_wind_qc_cleaned.csv`. Wind is one real hourly reading per
station (2026-08-29 08:00, chosen arbitrarily as a single illustrative row —
the full 48-hour series per edge is in the validation report).

| Station | Lat | Lon | Wind speed (m/s) | Wind dir (° from) |
|---|---|---|---|---|
| Mashhad | 36.297 | 59.606 | 14.7 | 68 |
| Neyshabur | 36.213 | 58.795 | — | — |
| Sabzevar | 36.215 | 57.678 | — | — |

Edge **Mashhad → Neyshabur** (bearing ≈ 262.92°, distance ≈ 73.32 km) with the
Mashhad 08:00 reading above (14.7 m/s from 68°, config defaults):

| Quantity | Value |
|---|---|
| along_track | +14.20 m/s (tailwind component — wind from 68° blows toward ≈248°, close to this edge's 263° bearing) |
| cross_track | 3.78 m/s |
| ground_speed | 64.06 m/s |
| time_hours | 0.318 h |
| energy_hours | 0.318 h |
| balanced_hours (w=0.5) | 0.318 h |

(Reproduced by actually running
`python -c "from pathfinding.cost import compute_edge_cost; print(compute_edge_cost(36.297, 59.606, 36.213, 58.795, 14.7, 68.0))"`
— not hand-estimated.)

Full 48-hour-per-edge summary statistics for all three required
origin/destination pairs (mean/min/max per criterion, computed — not
fabricated — from the real dataset) are in
`docs/wind_cost_validation_report.md` and
`docs/assets/wind_cost_validation_results.json`.

---

## Produced Outputs

- **Code:** `src/pathfinding/cost.py` — `CostModelConfig`, `EdgeCostResult`,
  `initial_bearing_deg`, `decompose_wind`, `ground_speed_mps`,
  `compute_edge_cost`.
- **Tests:** `tests/pathfinding/test_cost.py` — 19 tests, 97% line coverage
  on `cost.py`.
- **Validation:** `scripts/validate_wind_cost_model.py`,
  `docs/wind_cost_validation_report.md`,
  `docs/assets/wind_cost_validation_results.json`.

---

## Dependencies (flagged, not silently worked around)

The ClickUp task lists a dependency on the "multi-layer wind graph +
final pathfinding integration" task. Per `docs/AGENT_ROUTING.md` and
`docs/PROJECT_PROGRESS.md`, `src/pathfinding/graph.py`,
`algorithms.py`, and `routing.py` are all still **future / not started** —
there is no graph or orchestration layer yet for this cost function to be
wired into. Per `AGENTS.md` §2.4 ("check dependencies... make sure those
tasks are merged first") this task is technically blocked on that
dependency.

Rather than blocking entirely or fabricating a graph module outside this
task's scope (`AGENTS.md` §3.6: "do not modify files outside your task's
scope without announcing it" / §4.3: "implement only the checklist items"),
this PR delivers the edge-cost library as a standalone, independently
testable and directly callable unit
(`compute_edge_cost(...).cost`) so the future graph-construction task can
import and use it as its edge-weight function without redesign. **This gap
is flagged for the owner rather than silently resolved** — same pattern as
the QC/consistency dependency gaps noted in PR #16.

A second, unrelated data gap was found during validation: earlier progress
notes (`docs/PROJECT_PROGRESS.md`, 2026-09-02) already flag that
`data/khorasan_pathfinding_ready.csv` is 100% NaN. This task does not depend
on that file — validation instead uses the real, non-NaN
`data/khorasan_wind_qc_cleaned.csv` — but the NaN issue remains open and
unrelated to this PR.

## Future Improvements

- Once `src/pathfinding/graph.py` exists, wire `compute_edge_cost` in as the
  edge-weight function and re-validate end-to-end (this task only validates
  the cost function in isolation on station-pair "edges").
- `airspeed_mps` and `induced_drag_coeff` should be replaced with
  vehicle-specific values once a concrete aircraft/UAV type is specified.
- Wind is currently sampled at the edge's origin station only; once
  interpolated wind fields exist along the route (blocked on the NaN data
  gap above), the cost function could accept a wind sample per sub-segment
  instead of a single value per edge.
