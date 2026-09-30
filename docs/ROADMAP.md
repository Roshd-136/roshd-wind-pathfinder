# ROADMAP — Correctness, Verification Scene, Infrastructure

Status legend: `[x]` done and verified · `[~]` partially done · `[ ]` not started.
This file is the plan of record for the current hardening pass. Each item lands as
its own PR; the project owner merges (see `CONTRIBUTING.md`).

> **Read the newest status addendum at the bottom first.** The plan sections below
> keep their original wording (including the problems as they were found), but
> several of their tables and numbers were written against an earlier state of the
> scene: the flight levels were AGL 500/1000/1500/2000 m and they are now **MSL
> 1500/2200/2900/3600 m** with a 300 m terrain-clearance rule. Where a number below
> disagrees with the newest addendum, the addendum is what the code does.

## Why this ordering

Two things are true at once:

1. Stage 3 routing ships **wrong-answer bugs** that the task docs currently
   certify as correct, and part of the documentation describes code that is not
   in the repository.
2. There is **no way to see whether the routing actually works** — the existing
   artifacts are static PNGs produced by scripts that fly a different aircraft
   speed than the cost model.

So the 3D scene is not decoration; it is the verification harness that makes the
bugs visible, and the bugs must be fixed before a four-route comparison means
anything. Order: make the repo runnable → build the minimal scene so routes are
visible → fix the wrong answers the scene exposes → build the full four-route
scene → tidy tests and docs.

**Demo corridor:** Mashhad (36.297, 59.606) → Sabzevar (36.215, 57.678), 173.1 km.
The existing bounding box (36.05–36.45, 57.45–59.85) already contains it, so no
grid rebuild is needed. The scene takes the pair as a parameter, so a >200 km
corridor (Bojnurd 241 km, Gonabad 232 km, Birjand 383 km) needs new **data**, not
new code.

**Known data caveat:** the layer winds are **not measured**. `LAYERS = [(500, 1.15,
0), (1000, 0.95, 10), (1500, 0.90, 25), (2000, 1.30, 40)]` are hand-picked Ekman
scale/rotation factors applied to the 10 m surface wind, and they are
non-monotonic — which is why "1500 m is optimal" keeps winning. Every arrow drawn
from them must be labelled synthetic. The fetch script only requests
`wind_speed_10m` / `wind_direction_10m`; real multi-level winds would come from
Open-Meteo's pressure-level endpoint (~925/850/700 hPa ≈ 800/1500/3000 m).

**Out of scope:** Stage 4+, new data sources beyond the demo corridor, and the
Moran's I / ACF-PACF sketch in `docs/task_spatiotemporal_consistency.md`.

---

## Phase 0 — A repository that can prove things

- [x] **0.1** This roadmap, as `docs/ROADMAP.md`.
- [x] **0.2** Reproducible imports. Modules import each other as top-level
      packages (`from pathfinding.graph import ...`), which only resolved because
      `src/` happened to be on `sys.path`; `addopts = "-q --import-mode=append"`
      hid that. `pyproject.toml` now sets `pythonpath = ["src"]`.
- [x] **0.3** Dependency hygiene. `pytest-cov` added to `dev`; `matplotlib` moved
      out of core dependencies into a `viz` extra alongside `plotly`, so the
      pipeline and CI do not need a plotting stack.
- [x] **0.4** `.gitignore` (none existed): venv, caches, `*.db`, generated scenes.
- [x] **0.5** `.github/workflows/ci.yml` (did not exist): ruff job plus a 3.10 /
      3.11 / 3.12 test matrix with a coverage floor.
- [x] **0.6** `AGENTS.md` §6: exact install/test/lint commands, the `pythonpath`
      explanation, and an **evidence rule** — no "verified" or coverage claim
      without pasted output from a run against this repository.
- [~] **0.7** One canonical aircraft speed. The scene's `VIZ_AIRCRAFT` and the two
      visualisation scripts now agree on 20 m/s (the scripts' `AIRSPEED_MPS = 20.0`
      is no longer contradicted by a 50 m/s `CostModelConfig` default) — but the
      number is still written out in three places instead of imported once.

**Acceptance:** clean clone → `pip install -e ".[dev,viz]"` → `ruff check .` and
`pytest` green locally and in CI.

---

## Phase 1 — Wrong answers

- [x] **1.1 A\* heuristic is inadmissible → suboptimal routes.** Reproduced: 33%
      worse than the true optimum on a 3-node graph built with the project's own
      `compute_edge_cost`; `h(Z)` overestimated the true remaining cost by 1.60×.
      `ground_speed_mps` returns `√(airspeed² − cross²) + along_track`, so any
      tailwind pushes ground speed above airspeed and `haversine / (airspeed·3.6)`
      overestimates. Fix: bound the heuristic by the **maximum possible ground
      speed derived from the winds the graph was built from**; thread the real
      airspeed instead of the hardcoded 50 m/s; make admissibility hold **in the
      objective's units** (per-criterion lower bound) and route non-time criteria
      through Dijkstra; add the tailwind regression case, a seeded property test
      that `a_star` never costs more than `dijkstra`, and a direct test that
      `h(n) ≤` true remaining cost for every node.
- [x] **1.2 Kriging stops being exact once the fitted nugget > 0.** Reproduced:
      error equals the nugget fraction — nugget 0 / 0.5 / 1.0 → error 0.000000 /
      1.000000 / 2.000000. `fit()` adds `nugget·I` while `predict()` builds the
      cross-covariance through `_build_covariance`, which already subtracted the
      nugget at h=0, so the two sides of the kriging system disagree.
      `test_predict_exact_at_source` passes only because that seed fits a nugget
      ≈ 0 — it is latent-flaky. Fix: make the covariance self-consistent
      (`cov(0) = sill`, `sill − nugget − model(h)` otherwise), drop the ad-hoc
      `+= nugget * eye`, and parameterize the exactness test over the nugget.
- [x] **1.3 The router ignores its own configuration.** `WindRouter` stores
      `config`, `criterion` and `time_weight`, but routing always calls A\* on
      build-time weights; `criterion` is only stamped into the result string, and
      `estimated_time_hours = total_cost` unconditionally — so under
      `energy`/`balanced` it reports a number that is not hours.
- [x] **1.4 IDW `max_points` picks the wrong points.** `source[:n_use]` takes the
      *first* N sources in input row order, so results depend on row order and the
      nearest stations can be dropped.
- [x] **1.5 Missing wind is silently treated as calm.** `normalize_components`
      does `.fillna(0.0)`, turning "unknown" into a valid-looking zero-wind
      vector. Same defect as `data/khorasan_pathfinding_ready.csv`, whose wind
      columns are 100% NaN.
- [x] **1.6 QC configuration that does nothing.** `outlier_method` only
      implements `"zscore"`, so any other value silently disables outlier
      detection. `spatial_neighbor_radius_deg`, `spatial_z_threshold` and
      `min_spatial_neighbors` are declared and advertised in `docs/wind_qc.md` but
      referenced nowhere. `EmpiricalVariogram.compute` has identical `if`/`else`
      branches.

---

## Phase 2 — The 3D verification scene (Plotly, self-contained HTML)

One self-contained HTML — no map tiles, no API key, works offline — that opens in
the preview pane and regenerates with one command.

- [x] **2.1** Renderer foundation on the real pipeline (`MultiLayerWindGraph`,
      `WindRouter`), not a re-derivation: ground surface, station markers,
      origin/destination markers, altitude axis with a **stated vertical
      exaggeration** (500–2000 m across 173 km is invisible at 1:1). With no DEM
      available, the honest and useful surface is one coloured by **best-per-cell
      layer** and labelled as such — not fake elevation.
- [x] **2.2** Wind arrows with hover, one trace per layer, driven by **the same
      wind field the router consumes**. Hover shows speed (m/s and km/h),
      direction (° and compass), altitude, coordinates and a synthetic flag.
      Downsampled for interactivity, with the stride stated in the legend, and one
      toggle per layer so hovering is never ambiguous.
- [~] **2.3** The bug-revealing view: A\* and Dijkstra routes on the same layer for
      the same pair. They diverge today on tailwind-heavy legs; after 1.1 they must
      coincide.
- [x] **2.4** Cost-model extensions: a `distance` criterion (pure geometric) so
      "shortest path" is a real objective, and an explicit configurable along-track
      wind term so the wind-following route genuinely rewards moving along the wind.
- [x] **2.5** Single-layer routing entry point; `_route_on_layer` is private and
      layer choice is implicit inside `compare_layers`.
- [x] **2.6** The four routes. R1 most optimized (minimum energy + fewest heading
      changes, favouring along-wind legs — this is where `smooth_dijkstra`'s turn
      penalty, currently dead code with zero callers, becomes the engine);
      R2 fastest; R3 shortest distance; R4 R1's objective locked to one layer.
      Emit the comparison table: distance, time, energy index, node count,
      heading changes.
- [x] **2.7** Routes as splines (Catmull-Rom / `scipy.interpolate`), four colours,
      legend toggles, hover per spline. Keep the routed nodes visible and label the
      spline as cosmetic smoothing: a spline that cuts a grid corner is different
      geometry from the path that was costed.
- [x] **2.8** Honesty in the scene itself: arrows labelled synthetic, "energy"
      labelled a **relative index**, not kWh.
- [x] **2.9** Smoke test on the HTML (four route traces, four layer traces,
      expected labels, non-trivial size) plus one-command regeneration, so the
      artifact cannot silently become empty. This is the acceptance evidence for
      the whole roadmap.

---

## Phase 3 — Hygiene, and the tests that should have caught Phase 1

- [~] **3.1** Consolidate the duplicated cache tests, replace `tempfile.mktemp`
      with `tmp_path`, close SQLite connections, keep exactly one pandas-dependent
      test. Add regression tests for every Phase 1 bug.
- [x] **3.2** Per-package coverage floor with reproducible numbers. Measured
      baseline for this pass: 86% overall, with `src/pathfinding/algorithms.py` at
      **53%** — the task docs' "95% branch coverage on `src/pathfinding`" claim
      cannot be reproduced.
- [~] **3.3** De-duplicate `LAYERS`, `_bearing`, `ground_speed` and
      `build_multi_layer` across the two visualisation scripts; fix the mangled
      `kriging.py` docstring.
- [ ] **3.4** Cache TTL semantics: `timestamp` doubles as observation time and
      staleness anchor (`WHERE (timestamp + ttl) < now`), so backfilled history is
      born expired and a fresh fetch of an old observation reads as stale. Add
      `stored_at`, anchor TTL to it, keep `timestamp` as observation time, and
      provide a migration path for existing `.db` files.

---

## Phase 4 — Make existing artifacts honest, then guard the docs

- [ ] **4.1** `path_vis_02_path_layers.png` advertises mid-route layer switching
      that the engine cannot do (one layer per route). Relabel, or make it true.
- [~] **4.2** One sweep: `docs/task_routing_benchmark.md` ("this confirms A\*
      correctness"), `docs/PROJECT_PROGRESS.md` ("admissible, optimal"),
      `docs/wind_qc.md`'s spatial config example, `docs/task_idw_interpolation.md`'s
      `max_points` claim, `pathfinding_best_layer_map.png`'s synthetic-wind caption,
      and docstrings referencing non-existent symbols.
- [x] **4.3** Drift guard: a test asserting doc-referenced symbols and parameters
      exist, wired into CI.
- [x] **4.4** Verify the enforcement claims. `PROJECT_PROGRESS.md` describes
      rulesets and CODEOWNERS, and `README.md`/`AGENTS.md` reference
      `.github/PROMPT.md` and `pull_request_template.md`; none of those files exist
      in this checkout. Confirm against the canonical remote before re-adding, or
      correct the docs.
- [~] **4.5** The 12-route "A\* == Dijkstra" table holds only because Khorasan
      winds are weak against the assumed airspeed; after 1.1 it needs a case that
      actually distinguishes the algorithms, plus a larger-graph timing run if the
      A\* performance claim is to survive.

---

## Sequencing

`0 → 2.1–2.3 (see the routes, see the bug) → 1.1–1.6 (fix what you can now see) →
2.4–2.9 (four-route scene) → 3 → 4.`

**Done when:** a clean checkout installs, lints and tests green in CI; the
A\*/Kriging property tests pass; A\* and Dijkstra visibly coincide in the scene;
the four routes render with per-layer hoverable arrows and differ for the reasons
the legend claims; the reported travel time is genuinely time under every
criterion; and no doc or asset claims more than the code does.

## Risks

- **1.2** changes fitted interpolants → regenerate `docs/preprocessing_report.md`
  numbers and its assets in the same change.
- **1.5**'s NaN policy may make some routes infeasible until real wind replaces the
  all-NaN `khorasan_pathfinding_ready.csv`.
- Scene file size: a 41×81 grid × 4 layers is ~13k arrows; full density makes hover
  sluggish, hence the documented stride and per-layer toggles.
- Plotly hover over thousands of cones is the one interaction that may need real
  tuning; the fallback is fewer arrows plus a click-to-inspect probe.
- CI requires a GitHub remote; this checkout has no `.git` at all, so confirming
  the canonical remote and default branch is step one before any PR.

---

## Status addendum — 2026-09-21

Landed in this pass, and what it changed:

- **Wind unit bug (new, not in the original plan).** `scripts/fetch_khorasan_data.py`
  never set `wind_speed_unit`, so `data/khorasan_wind_qc_cleaned.csv` stored
  Open-Meteo's default **km/h** while every consumer (`wind_qc`,
  `prepare_for_pathfinding`, `viz.wind_field`) read it as **m/s** — wind 3.6× too
  strong, and the QC thresholds (z-score, 30 m/s temporal jump) effectively inert.
  Verified against the API: CSV `5.2` == the API's km/h value, m/s is `1.46`. The
  fetch script now requests `wind_speed_unit=ms` (and raises if the response is not
  m/s), supports `--start/--end` so the committed window is reproducible, and the
  dataset was regenerated: speeds are now 0.45–7.72 m/s and QC removes 2 of 144
  records.
- **Layer profile made physical.** `LAYER_PROFILES` was hand-picked and
  non-monotone (1000/1500 m modelled *slower* than 500 m), which is why "the best
  layer" was a constant artifact. It is now a monotone power-law + Ekman-veer
  profile, so the 3D router's answer depends on the wind field rather than on the
  constants.
- **`smooth_dijkstra`'s turn penalty was inert on the merged graph.** Every 3D route
  has two vertical (climb/descent) transitions whose bearing is undefined; the
  penalty charged them anyway, adding the same constant to every candidate, so the
  penalty could not change the chosen route (a 50.0 penalty produced the same path
  as 0.0). Vertical transitions are now exempt in both the search and
  `heading_changes`.
- **Constrained routes are now comparable.** `to_stacked_graph(layers=...)` and
  `WindRouter.find_optimal_path(..., layers=...)` restrict the merged graph to a
  subset of altitudes, so the single-altitude route (R4) also starts and ends on
  the ground and pays for its climb/descent. Previously it was routed on the layer
  alone, omitted the vertical cost entirely and looked *cheaper* than the free
  route.
- **Terrain.** `src/viz/terrain.py` + `scripts/fetch_terrain_data.py` add a real
  DEM (`data/khorasan_terrain.csv`, Copernicus GLO-90 via Open-Meteo). The scene's
  ground surface, the AGL reference for every layer, station markers and the
  origin/destination markers all sit on it.

### Still open (docs are now knowingly stale)

The unit fix changed the dataset, so these numbers must be regenerated rather than
trusted:

- `docs/preprocessing_report.md` — IDW/Kriging RMSE, the 90th-percentile
  calibration figures, "144 of 144 valid, 0 removed", and its PNG assets. A warning
  banner was added; the numbers themselves still need a regeneration pass.
- `docs/wind_cost_validation_report.md` — "wind speeds in this dataset range
  roughly 4–15 m/s" is the km/h range read as m/s.
- `docs/task_wind_cost_model.md` — its worked Mashhad 08:00 example uses a reading
  that is really km/h.
- `docs/PROJECT_PROGRESS.md` — historical and append-only; do not rewrite, but its
  A\*/admissibility and coverage claims predate the fixes above.
- `docs/assets/path_vis/*.png` and the other PNG reports were rendered from the
  mis-scaled wind field.
- A scene-level follow-up: with the corrected winds, climbing 1500 m costs ≈0.3 h
  while the shear gains far less, so no free route switches altitude on this
  corridor. The capability is proved in
  `tests/pathfinding/test_routing.py::test_multilayer_route_climbs_when_the_upper_layer_pays`;
  a longer corridor or a real multi-level wind source would make it visible.

---

## Status addendum — 2026-09-22 (scene legibility, effort/fuel model, focus mode)

Follow-up to the 2026-09-21 addendum, answering four review questions about the
scene (`docs/assets/routing_scene.html`).

### Wind arrows: length is now strictly proportional to wind speed

Before, the shaft was proportional to speed but scaled at only `0.7 km/(m/s)`,
and the cone head was drawn at the arrow's *tail* with a fixed 3.5 km diameter —
so the head covered the shaft and every arrow read as the same size. Now:

- `ARROW_KM_PER_MS = 1.6`, `ARROW_MAX_LENGTH_KM = 18`. In this hour's field the
  graph node speeds are 5.2–10.2 m/s, so arrows are 8.3–16.3 km and **nothing is
  capped** — proportionality is exact. `tests/test_routing_scene.py::test_wind_arrow_length_is_proportional_to_wind_speed`
  recomputes every expected length from the graph nodes the arrows are drawn on.
- The head sits at the shaft tip and is drawn with `sizemode="absolute"`, for
  which Plotly normalises cone size against the largest vector in the trace, so
  the head grows with the wind too.
- Within one layer this dataset's arrows differ by ≈1.6× — that is the real
  spatial spread of the hour, not a chosen visual factor. The honesty limit is
  stated in the code and in the scene's chips.

### Why R1 and R2 report identical numbers (and R3 differs by only 0.3 km)

Not a bug, and now stated in the page instead of left to guess:

- The wind direction at the three stations spans 68°–125° and speeds 4.4–6.9 m/s,
  and IDW (power 2) smooths the field *between* stations. There is no
  "preferred-wind region" for a route to detour into, so distance-, time- and
  energy-optimal paths converge.
- The energy criterion differs from the time criterion by
  `1 + 0.3·(cross/20 m/s)²`, i.e. at most ~4% of edge weight, so both optima land
  on the same discrete path.
- Result (R1/R2 node-for-node identical; R3 shorter by 0.27 km) is therefore a
  property of the data, not the algorithm. The scene now prints the distance
  range and the station wind spread, and a regression test asserts that a route
  drawn as a different line can never claim R1's numbers.

### Why the picture disagreed with the table

The drawn line is not the flight distance. The scene exaggerates altitude ×20
and the route follows the *real terrain* (AGL), so:

| route | horizontal (km) | table 3D (km) | drawn on screen (km) |
|---|---|---|---|
| R1/R2 | 174.2 | 175.2 | 215.5 |
| R3 | 174.0 | 175.0 | 213.9 |
| R4 | 174.2 | 178.2 | 275.5 |

R4 shares R1's horizontal path yet its line is 60 km longer on screen, purely
because of the ×20 vertical exaggeration. A new column «طول خط روی صفحه (km)»
reports the drawn length (`drawn_polyline_km`), so the image and the table can be
checked against each other; `test_drawn_geometry_matches_the_reported_distance`
and `test_drawn_line_is_longer_than_the_real_distance` pin both halves.

### New: motor effort, power and fuel per route

`src/pathfinding/effort.py` (new) turns a route's legs into:

- **how many times the aircraft must re-steer** (air-heading change above a
  threshold, computed from the navigation triangle, not from the ground track),
- **with what power** (extra shaft power while banked: induced drag × `n²−1`),
- **and how much fuel** (`shaft energy / (η_thermal · LHV)`), split into cruise,
  turn and climb/descent.

Every one of those is a *model* number: mass (25 kg), L/D (12), bank (25°),
η_prop 0.60, η_thermal 0.28, LHV 43 MJ/kg are declared assumptions, printed in
the page's «فرضهای مدل سوخت» table next to the fuel column. For this corridor:
R1/R2 0.41 kg (0.23 kg/100 km, 10 course corrections, 4.9 s of turning at 74 W
extra), R4 0.51 kg.

### Focus mode (double-click) and reset

Double-clicking a route used to do nothing: the Plotly legend was switched off
and the page never handled the gesture. The HTML legend is now **grouped** (one
chip per layer/route, controlling both its traces) and supports:

- **click** — toggle that group,
- **double-click** — isolate it: every other group is hidden, while the terrain
  and the origin/destination markers stay (`meta["always"]`), so the focused
  route is not floating in space,
- **«نمایش همه» button / `Esc`** — restore every group's default visibility.

`Plotly config doubleClick` is disabled so Plotly's own zoom-reset cannot fight
the gesture. Verified interactively in the live preview: isolating R3 left
traces `[0, 14, 15, 19, 20]`, and the reset restored all defaults.

### New: the wind-riding route (R5) — one heading, zero corrections

The four graph routes all *hold a ground track*, so every heading change is a motor
correction. This corridor has an east-to-west wind, which means a fifth strategy is
available that the graph cannot express: **climb, hold one air heading, let the wind
carry the aircraft, and descend into the destination**. The route is not planned on
the graph at all — it integrates the continuous wind field
(`src/pathfinding/wind_riding.py`, new) and is then reported as an ordinary
`RouteResult` so it lands in the same table and the same legend.

The planner is a one-parameter search: a coarse heading sweep (4°), then staged
refinement (1°, then 0.1°), each layer integrated separately, and the layer/heading
with the least arrival time among those that land within 2 km wins (~7 s per search
with the simulation cache).

**Measured on the shipped dataset** (same aircraft, same 174 km corridor):

| route | layer (m) | km | hours | energy idx | motor corrections | fuel (kg) | kg/100 km |
|---|---|---|---|---|---|---|---|
| R1 (energy-optimal, graph) | 500 | 174.24 | 1.940 | 1.994 | 10 | 0.408 | 0.234 |
| R2 (time-optimal, graph) | 500 | 174.24 | 1.940 | 1.994 | 10 | 0.408 | 0.234 |
| R3 (distance-optimal, graph) | 500 | 173.98 | 1.963 | 2.020 | 5 | 0.413 | 0.237 |
| R4 (layer-locked, graph) | 2000 | 174.24 | 2.224 | 2.450 | 9 | 0.506 | 0.290 |
| **R5 (wind-riding)** | 500 | **173.62** | **1.900** | **1.933** | **0** | **0.393** | **0.226** |

**The honest part of that table.** The two models do not bill the descent the same
way, and this changes the verdict, so the scene now says so in the same paragraph
that quotes the numbers: graph routes charge an *extra vertical phase* for the
descent (no forward motion), while wind riding descends **in motion** on a glideslope
and therefore covers ground while it loses height. Re-scoring R5 under the graph's
convention adds ~2.8 minutes and the descent's potential energy, which puts it at
1.946 h and 0.410 kg — i.e. **level with R1, not ahead of it**. R5's time/fuel
advantage in the table is a *modelling* artefact; what survives any convention is
that it reaches the destination with **zero motor corrections** (a single constant
heading) and a marginally shorter path.

**Four defects found and fixed while building it** (each one would have quietly
turned the claim into a lie):

1. **The descent trigger used the cruise layer's ground speed**, so the aircraft
   touched down hundreds of metres short or long and needed a closing leg — exactly
   the path change the strategy exists to avoid. The lead distance now comes from the
   *descent* layer, and the descent itself is a **glideslope** driven by the
   remaining distance, so it lands on the destination (verified: `final_leg_km == 0`
   in a uniform field).
2. **One 0.25° refinement stage was not enough** to arrive within the tolerance —
   the planner returned no route at all for a config that "looked" fine. Refinement
   is now staged (4° → 1° → 0.1°), with a simulation cache.
3. **The ride/descent boundary was mis-billed**: the sampling window open when the
   descent started (up to 2 minutes of cruise) was attributed to the descent phase,
   inflating its distance and implying an impossible ground speed. The boundary is
   now closed exactly at the trigger.
4. **A continuous profile was reported as dozens of "layers"**: `altitudes_used`
   derives layers from `node_altitudes`, so a sloping descent produced ~17 distinct
   altitudes and the route looked multi-layer. `RouteResult.layers_used` (new,
   optional) lets a route declare its cruise layers explicitly; R5 reports one.

**Verified:** 11 new unit tests on synthetic uniform fields
(`tests/pathfinding/test_wind_riding.py`) and 7 new scene tests
(`tests/test_routing_scene.py`) — including "the graph routes must need corrections
or the comparison is empty", "the route lands *on* the destination", and the
altitude-profile/`layers_used` pair. Whole suite: 248 passed, `ruff` clean.

---

## Phase 6 — Gravity was missing, and it was why nothing ever climbed

**The user's suspicion was right, and it was two defects, not one.**

### 6.1 Every single-layer route began in the sky

`WindRouter._route_on_layer` routed directly on the *layer* graph — and in that graph
every node sits at the layer's own altitude; there are no ground nodes. So a
"500 m route" and a "2000 m route" both started and ended at cruise altitude, with
`total_climb_m == total_descent_m == 0`. The climb to the layer was never billed.

`MultiLayerWindGraph.to_stacked_graph(layers=(altitude,))` already existed and does
exactly the right thing (ground nodes, charged climb, charged descent) — the
docstring of `find_optimal_path` even *claimed* single-layer routes did this. They did
not. `_route_on_layer` now goes through the stacked graph, so every route is
ground-to-ground and the layer comparison is apples-to-apples.

### 6.2 A descent cost more per second than level flight

`compute_vertical_cost` billed **both** directions with `energy_multiplier` (1.5×
cruise), so descending was the most expensive phase in the model. Nothing in physics
supports that: in a descent gravity supplies part of the thrust and the motor comes
back to idle. Meanwhile `compute_route_effort` billed the climb at the full `mgh/η`
and credited the descent with **nothing** — the stored potential energy was never
returned. Every multi-layer route therefore paid a penalty that does not exist.

Fixes, in the two models that own the physics:

| where | before | after |
|---|---|---|
| `VerticalCostConfig` | one `energy_multiplier` for both directions | `energy_multiplier` (climb) + `descent_energy_factor = 0.15` |
| `compute_route_effort` | descent = `mgh/η`, no credit | descent = idle power; glide range and fuel saved reported |
| `LegSample` | no per-leg power | `power_fraction` (1.0 = cruise, idle = glide) |

**The identity that closes the loop:** the climb costs `mgh/η` of shaft energy, and the
descent returns exactly that much as engine-idle range, because

```
D · (L/D) · h / η  =  m · g · h / η
```

A route that starts and ends on the ground has zero *net* potential-energy change, so
its net altitude fuel is only the remnant of the idle descent. That is asserted to
1e-9 in `test_gravity_settlement_cancels_the_climb_energy_exactly`.

### 6.3 The wind-riding descent is now a real glide

Previously the descent started when `remaining <= ground_speed × descent_seconds` — a
*time*-based lead, which fixed the glide slope after the fact and gave gravity no share
of the distance. It now starts when the remaining distance equals the glide range of
the cruise altitude (`h · L/D`), and those legs carry
`power_fraction = descent_idle_power_fraction`. The planner and the fuel model read the
glide ratio and the idle fraction from the *same* `MotorEffortConfig`, so the geometry
and the accounting cannot drift apart.

### 6.4 The answer the table now gives

Same corridor, same aircraft, same dataset — every route climbs out of Mashhad and
descends into Sabzevar:

```
route   layer(m)  dist(km)  time(h)  energy  fuel(kg)  climb/descent
R1           500     174.2    1.940   1.931    0.3760  500 / 500
R2           500     174.2    1.940   1.931    0.3760  500 / 500
R3           500     174.0    1.963   1.957      —     500 / 500
R4          2000     174.2    2.224   2.200    0.3768  2000 / 2000
R5           500     173.6    1.900   1.933    0.3803  500 / 500 (glide)
```

and the per-layer breakdown of *"climb, ride the wind, glide down"*, which the scene now
prints as its own table:

```
layer  wind(m/s)  offset from corridor  climb(min)  ride(min)  glide(min)  glide(km)  turns  total(h)  fuel(kg)
  500       8.0              1°               3.3       106.7        4.0        5.7       1     1.900    0.3803
 1000       8.8              9°               6.7       101.0        8.3       11.7       1     1.933    0.3795
 1500       9.4             16°              10.0        96.3       12.7       17.5       0     1.983    0.3821
 2000      10.0             23°              13.3        92.3       18.0       24.1       1     2.061    0.3873
```

**Reading it honestly.** The user's intuition — spend motor up front, then let the wind
carry you, then glide down — is *mechanically correct*, and after 6.1–6.3 the model can
finally express it. What the data then says is narrower:

* The wind **does** get stronger with height (8.0 → 10.0 m/s), and the ride phase
  **does** get shorter (106.7 → 92.3 min).
* But it also **rotates away from the corridor**: 1° off at 500 m, 23° off at 2000 m.
  The usable along-track component grows far more slowly than the total speed.
* Gravity makes the extra altitude nearly **fuel-free** (0.3803 → 0.3873 kg across a 4×
  height change) — but the climb costs **10 extra minutes**, and that is what the time
  criterion bills.
* So the layer is genuinely a **criterion-dependent choice**: 500 m is fastest, 1000 m
  is cheapest, and 1500 m is the only layer where the aircraft drifts the whole way
  with **zero ground-track bends**.

This also **supersedes** the previous phase's honesty note. That note said R5's
time/fuel edge over the graph routes was a *modelling artefact* of different descent
conventions. The conventions have been unified, so the note is gone from the scene; the
numbers above are on one convention.

---

## Status addendum — 2026-09-22 (MSL flight levels, terrain clearance, and the wind-riding contract)

This supersedes the numbers in the Phase 6 and "scene legibility" addenda. Those were
written while the four flight levels were **AGL 500/1000/1500/2000 m**; the levels are
now **MSL 1500/2200/2900/3600 m** with a 300 m terrain-clearance rule, and that change
is what makes the multi-layer optimisation finally do something.

### What the four levels are now, and why it matters

| item | value |
|---|---|
| flight levels (MSL) | 1500 / 2200 / 2900 / 3600 m |
| minimum clearance | `MIN_TERRAIN_CLEARANCE_M = 300` m |
| corridor DEM | 872 – 3175 m (relief 2303 m) |
| ground at Mashhad / Sabzevar | 983.24 m / 983.90 m |

Nodes whose clearance would be negative are **not built into the graph at all**, so a
"route on level X" cannot mean "a route through the mountain". That turned the
layer table from a wind comparison into a feasibility comparison: a level that cannot
clear the range simply has no path, and the evidence table now says so instead of
printing a number.

### The routes (regenerated scene, one hour, one aircraft, 20 m/s)

```
route  criterion  algo    level(m)  dist(km)  time(h)  energy  climb/descent(m)  fuel(kg)
R1     energy     smooth      2900     176.6    2.213   2.176     1917 / 1916     0.378
R2     time       astar       2900     176.6    2.212   2.177     1917 / 1916     0.378
R3     distance   astar       3600     174.0    2.389   2.349     2617 / 2616     0.387
R4     energy     smooth      2200     192.8    2.292   2.275     1217 / 1216     0.420
R6     energy     smooth      3600     174.3    2.351   2.310     2617 / 2616     0.379
R5     time       wind-ride   3600     173.7    2.130   2.311     2617 / 2616     0.393
```

### The four review questions, answered with geometry rather than prose

1. **"Terrain isn't visualised."** The ground surface is the Copernicus DEM
   (`data/khorasan_terrain.csv`), drawn at its real elevations ×20, hoverable per cell
   (`ارتفاع زمین: … متر`). Range on the z axis: 17.44–63.50 km of axis = 872–3175 m real.
2. **"All the splines are in one layer."** They are not, any more. The routed node
   altitudes per route (deduplicated, in order, `0` = on the ground) are:
   `R1/R2: 0 → 1500 → 2200 → 2900 → 2200 → 1500 → 0` (4 level changes),
   `R3: 0 → 1500 → 2200 → 2900 → 3600 → 2900 → 2200 → 1500 → 0` (6),
   `R4: 0 → 2200 → 0`, `R6: 0 → 3600 → 0`, `R5: 0 → 3600 → …glideslope… → 0`.
3. **"Why not move along multiple layers?"** Now it does, wherever that pays: the free
   routes climb through 1500 and 2200 to cruise at **2900** and descend through them
   again, and the 2200/3600 locks (R4/R6) exist to show what giving that freedom up
   costs. The free route wins the energy objective (2.176) against both locks
   (2.275 / 2.310).
4. **"Wind arrows aren't visible / start and end points are in the sky."** Arrows are
   on by default — one shaft trace plus one cone trace per level, drawn on the very
   nodes the router uses (52 / 101 / 111 / 40 arrows at 1500 / 2200 / 2900 / 3600 m),
   hovering to speed, direction, level, local ground and coordinates. Every route's
   first and last drawn node is at the **ground** (983 m at Mashhad, 984 m at
   Sabzevar) and the start/end markers sit on the same DEM elevations.

### A contract bug this pass found in the wind-riding route

`RouteResult.node_altitudes` documents that ground nodes report **0** ("اینجا یعنی روی
زمین، نه سطح دریا"), and `WindRouter` honours it. `wind_riding_route_result` passed the
planner's MSL profile through untouched, so R5 reported **983.24 m** for a node that is
sitting on the ground — two routes on one corridor with two different zero points, which
made "ground to ground" true for only one of them. Fixed by anchoring the endpoints to
0, and while there, `total_descent_m` is now measured to the **destination's** ground
rather than the origin's (2616.10 m instead of 2616.76 m).

### Test-suite repairs

- `write_scene` now takes `ground_n_lat` / `ground_n_lon`. The "best layer per cell"
  overlay is the most expensive part of building the scene and touches none of the
  HTML assertions, so the artifact tests build it at 5×7 and share one generated file
  (a module fixture) instead of regenerating the whole pipeline five times. The scene
  test file previously could not finish a run — it was killed at 240 s — and now
  completes.
- Eleven scene tests were re-pinned to the current design rather than left asserting the
  old one: route column indices are looked up **by name** (the table grew columns three
  times), the arrow layers iterate `FLIGHT_LEVELS_MSL` instead of a hardcoded
  500/1000/1500/2000, the layer group key is `level-1500` (the test looked up
  `layer-1500` and could never have passed), the climb assertions now use
  `level − ground elevation` instead of `level` (Mashhad is not at sea level), the
  locked-route pair is R4/R6 instead of the old low/high pair, and the drawn-length
  assertion is the exact breakdown `horizontal + 20 × vertical` instead of two routes
  that used to share a path.
- The old layer-evidence test asserted that *every* layer's net time gain was negative —
  i.e. that climbing never pays. In this wind field climbing **does** pay, so that
  assertion was both false and an obstacle to the fix. It now asserts conformance with
  `WindRouter.compare_layers`: one row per level, engine numbers for the routable ones,
  and an explicit "no path" reason for the blocked ones.

### New: the doc-drift guard (`tests/test_docs_consistency.py`)

Every backticked dotted reference in `docs/*.md`, `README.md`, `AGENTS.md` and
`CONTRIBUTING.md` whose first segment is one of this project's packages
(`data`, `preprocessing`, `pathfinding`, `qc`, `viz`) must resolve — as a module or as
an attribute of one. Demonstrated to work by injecting a bogus reference
(the dotted form of a class that does not exist, under `pathfinding.routing`) into a
scratch doc — the guard failed with `_scratch_drift.md:3`, and passed once the file was
removed. The CI workflow's comment claimed this test existed; before this pass it did
not.

### Docs corrected in the same pass

`AGENTS.md`'s repository tree (it put the QC module under `preprocessing/`, listed
`pathfinding/` as a directory of "(future)" files, and omitted `src/qc/`, `src/viz/`
and `scripts/`),
`README.md` and `CONTRIBUTING.md` (they pointed readers at `.github/PROMPT.md` and
`.github/pull_request_template.md`, neither of which has ever been in this checkout —
`.github/` contains only `workflows/ci.yml`).

### Still open, stated plainly

- **3.3** is half done: the mangled `kriging.py` docstring and the `if`/`else` copy in
  `EmpiricalVariogram.compute` are fixed, but `LAYERS`, `_bearing`, `ground_speed` and
  `build_multi_layer` are still duplicated between `path_visualizer.py` and
  `generate_pathfinding_visualizations.py`.
- **3.4** (`stored_at` in the cache) is not started: TTL is still anchored to the
  observation timestamp.
- **4.1** is not started: `path_vis_02_path_layers.png` is still captioned as "route
  coloured by its current layer", which the layer-per-route engine never did.
- **0.7** is half done: the airspeed is 20 m/s everywhere in practice, but the constant
  is written out in three places instead of imported once.
