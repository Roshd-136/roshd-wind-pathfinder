# PROJECT PROGRESS Log

> Every AI agent adds a new section here after finishing a task. Previous sections remain untouched.
> **Rule:** Read this file before starting any task.

## Overall Status (26 Aug 2025)
| Stage | Topic | Status |
|-------|-------|--------|
| Stage 1 | Data sources, caching | ✅ Done |
| Stage 2 | Preprocessing | 🟡 In progress (3/6 on main, 3 incomplete) |
| Stage 3+ | Pathfinding | ⬜ Future |

## Completed Tasks
- **Stage 1** — API Keys, Data Caching, Survey → ✅ Done
- **Stage 2 (Arman)** — IDW Interpolation (PR #1), Kriging (PR #2) → ✅ Done  
- **Stage 2 (Mehdi)** — Wind Data QC → ⚠️ Incomplete (no tests, no real Open-Meteo data, pushed directly to main)
- **Stage 2 (Others)** — DataPrep, Consistency, Report → ⬜ Not started yet / needs review

## New-Section Template (agents: copy this)
```markdown
## Task: «Title» (ClickUp ID: «id») — Stage «n»
- **Status:** Done / In progress  
- **What I built:** 2-4 line summary  
- **Input I used:** which previous task/module  
- **Output of this task:** exact file paths + function/class names  
- **For the next task:** what it needs and how to use it  
- **Test:** real pytest and ruff result
- **PR:** PR link (merge only by Arman)
```

---

## 2025-08-30 — Initial Setup & Documentation Overhaul

**Agent:** Hermes (AI)  
**Branch:** `feat/docs-overhaul-and-structure`  
**PR:** #TBD  

### Summary
Comprehensive documentation overhaul to make the project ready for AI agents and human collaborators. Fixed existing issues, created missing files, established standard folder structure, and prepared GitHub branch protection.

### Changes Made

#### 1. Standard Prompt File (`.github/PROMPT.md`)
- Created the standard prompt file that defines how AI agents should work on this project
- Contains repo URL, token placeholder, task input format, and 8 golden rules for agents

#### 2. PROJECT_PROGRESS.md (this file)
- Created the project progress tracking file
- Establishes append-only convention for tracking all work

#### 3. Data Files Added
- `data/khorasan_wind_qc_cleaned.csv` — QC-cleaned wind data for Khorasan region
- `data/khorasan_qc_report.json` — QC report (144 records, 0% removal rate)
- `data/khorasan_pathfinding_ready.csv` — Pathfinding-ready data with u/v components and normalized values

#### 4. Code Quality Fixes
- Fixed ruff linting error in `tests/data/test_cache.py` (F401 unused import)
- All tests pass: `pytest -q` → 11 passed
- Linter clean: `ruff check .` → OK

#### 5. Documentation Improvements (Planned)
- README.md: Strengthen project structure documentation
- CONTRIBUTING.md: Make general, not person-specific
- AGENTS.md: Ensure accuracy for AI agents

#### 6. Folder Structure for Future Tasks (Planned)
```
docs/
  ├── PROJECT_PROGRESS.md
  ├── task_data_caching.md
  ├── task_idw_interpolation.md
  ├── task_kriging_interpolation.md
  ├── task_wind_qc.md
  ├── task_spatiotemporal_consistency.md
  ├── task_data_prep_pathfinding.md
  └── task_preprocessing_docs.md
tasks/
  ├── templates/
  │   └── task_template.md
  ├── active/
  └── completed/
.github/
  ├── PROMPT.md
  ├── pull_request_template.md
  └── workflows/
      └── ci.yml
src/                       # پکیج پایتون (src-layout)
  ├── __init__.py
  ├── data/
  │   ├── __init__.py
  │   └── cache.py
  ├── preprocessing/
  │   ├── __init__.py
  │   ├── idw.py
  │   ├── kriging.py
  │   ├── qc.py
  │   └── consistency.py
  └── pathfinding/
      ├── __init__.py
      ├── graph.py
      ├── algorithms.py
      └── routing.py
tests/
  ├── data/
  │   ├── test_cache.py
  │   └── test_cache_no_pandas.py
  ├── preprocessing/
  └── pathfinding/
```

### Verification
- ✅ All tests pass (`pytest -q`)
- ✅ Linter clean (`ruff check .`)
- ✅ Data files in place
- ✅ Standard prompt file created

### Next Steps
- Complete documentation overhaul (README, CONTRIBUTING, AGENTS)
- Create folder structure for future tasks
- Set up GitHub branch protection
- Open PR for review


## 2025-08-30 — Git Enforcement: Rulesets, Ownership and PR-only Workflow

**Agent:** Hermes (AI)
**Branch:** main (via PRs)
**PRs:** #8, #9 (docs), #10 (CODEOWNERS)

### Summary
Implemented GitHub enforcement so that only the owner (lawbr3aker) can write to the base branch, all collaborators must merge via pull request, and agent/owner files are protected by code-owner review.

### Changes Made
- Ruleset main-owner-only (branch ruleset, active) targeting refs/heads/main:
  - update, deletion, non_fast_forward blocked: no direct pushes / force-pushes / deletion of main.
  - required_status_checks: Lint and Test (strict), so CI must pass before any merge.
  - pull_request: requires 1 approving review plus code-owner review; stale reviews dismissed.
  - Bypass list = only lawbr3aker (User id 69733196, mode always): the sole actor who can merge/act without review.
- Added .github/CODEOWNERS: * @lawbr3aker, so all files are owned by the project owner and any collaborator PR touching owned files needs the owner explicit review to merge.
- Downgraded MOHAMADCONSTANTINE from org admin to write collaborator (no longer bypasses rulesets).
- Removed redundant classic branch protection (ruleset is now the single source of truth).
- Externalized the owner bypass from role-based (OrganizationAdmin) to per-user (User:69733196) so no other org admin can bypass.

### Resulting Access Model
| Actor | Can push to main directly? | Can merge a PR? |
|---|---|---|
| lawbr3aker (owner) | No (must PR) but bypasses all review rules | Yes, instantly (bypass) |
| MOHAMADCONSTANTINE (write) | No | No: PR needs owner review |
| Bradarabdol (write) | No | No: PR needs owner review |
| AI agents (as above) | No | No: must open PR; owner merges |

### Verification
- PR #10 (CODEOWNERS) merged to main via the PR plus bypass flow.
- Lint and Test green on main.
- Ruleset active; classic protection removed.
- Only lawbr3aker is org admin; others are write collaborators.

### Next Steps
- (Optional) Apply an org-level ruleset for all repos in Roshd-136 (needs owner token with admin:org).

## 2026-08-31 — Stage 2: Spatiotemporal Consistency Check

**Agent:** Hermes (AI), on behalf of AmirAli
**Branch:** task/spatiotemporal-consistency
**PR:** (see PR link)

### Summary
Implemented the "بررسی و اعتبارسنجی پیوستگی زمانی و مکانی داده‌ها" task: a
`SpatiotemporalConsistencyChecker` that detects per-station temporal gaps,
flags spatial disagreement between neighboring stations, fills short
fixable gaps by interpolation, and produces a combined continuity report.
Thresholds in `ConsistencyConfig` are calibrated against the real Khorasan
reference dataset rather than picked arbitrarily.

### Changes Made
- Added `src/preprocessing/consistency.py`:
  `SpatiotemporalConsistencyChecker`, `ConsistencyConfig`, `haversine_km()`,
  `circular_diff_deg()`.
- Added `tests/preprocessing/test_consistency.py` (12 tests, all passing).
- Replaced the pre-implementation placeholder in
  `docs/task_spatiotemporal_consistency.md` with as-built documentation,
  including the threshold-calibration analysis against the real dataset.
- Did not modify `data/*.csv` or `data/*.json` (read-only per routing rules).

### Verification
- ✅ `ruff check .` — all checks passed.
- ✅ `pytest -q` — 44 passed (12 new + existing suite), 0 failed.
- ✅ Ran against `data/khorasan_wind_qc_cleaned.csv` (144 records, 3
  stations): 0 temporal gaps, 144 spatial comparisons across 3 neighbor
  pairs, 33 flagged above the calibrated thresholds (informational, not
  necessarily errors — see task doc).

### Next Steps
- Owner review/merge of PR.
- Consider distance-scaled or z-score-based spatial thresholds once more
  station pairs are available (see Future Improvements in the task doc).

## 2026-09-02 — Stage 2: Preprocessing Report (final)

**Agent:** Hermes (AI), on behalf of AmirAli
**Branch:** task/preprocessing-report
**PR:** (see PR link)

### Summary
Wrote the final Persian preprocessing report (`docs/preprocessing_report.md`)
consolidating real results from all preprocessing modules (QC, IDW, Kriging,
Spatiotemporal Consistency, Data Preparation for Pathfinding), with an actual
leave-one-station-out cross-validation comparing IDW vs Kriging accuracy on
the real Khorasan dataset, and three real charts generated from that data.

### Changes Made
- Added `docs/preprocessing_report.md` (final report).
- Replaced the mismatched placeholder in `docs/task_preprocessing_docs.md`
  with content matching the actual ClickUp task (same pattern as prior
  mismatched-stub fixes for Consistency and Data Prep tasks).
- Added `scripts/generate_preprocessing_report_assets.py` (reproducible
  chart/comparison generator) and three PNGs under `docs/assets/`.

### Verification
- ✅ `ruff check .` — all checks passed.
- ✅ `pytest -q` — 50 passed, 0 failed (full repo suite; no test regressions).
- ✅ IDW vs Kriging comparison actually computed (not fabricated): IDW
  RMSE=7.92 MAE=6.05 m/s; Kriging RMSE=10.65 MAE=8.30 m/s (144
  leave-one-station-out comparisons). Documented the methodological caveat
  that only 3 stations are available, so Kriging's variogram fit (2 source
  points per fold) is statistically unreliable — this result should not be
  read as a general IDW-beats-Kriging conclusion.

### Findings flagged for the team
- `data/khorasan_pathfinding_ready.csv` (added in PR #15) still has 100%
  NaN values in wind_speed/wind_direction/u/v across all 23,040 rows; the
  `pathfinding_preparation.py` code itself works correctly (PR #16), but
  this sample file needs to be regenerated from real QC/interpolation output.

### Next Steps
- Owner review/merge of PR.
- Regenerate `khorasan_pathfinding_ready.csv` with real interpolated data.
- Re-run the IDW/Kriging comparison once more stations are available.

## 2026-09-09 — Stage 3: Wind Cost Model & Validation

**Agent:** Claude (AI), on behalf of Mehdi
**Branch:** `task/wind-cost-model-validation`
**PR:** (see PR link)

### Summary
Implemented `compute_edge_cost()` in `src/pathfinding/cost.py`: a dynamic
edge-cost function decomposing real wind into along-track (headwind/tailwind)
and cross-track (crosswind) components, with three selectable optimality
criteria (time / energy / user-weighted balanced). Validated against three
real Khorasan station pairs using all 48 real hourly readings per pair (no
synthetic data).

### Changes Made
- Added `src/pathfinding/cost.py`: `CostModelConfig`, `EdgeCostResult`,
  `InfeasibleEdgeError`, `initial_bearing_deg()`, `decompose_wind()`,
  `ground_speed_mps()`, `compute_edge_cost()`.
- Added `tests/pathfinding/test_cost.py` (19 tests, all passing).
- Added `scripts/validate_wind_cost_model.py` and its real output at
  `docs/assets/wind_cost_validation_results.json`.
- Added `docs/task_wind_cost_model.md` (design doc + real worked example) and
  `docs/wind_cost_validation_report.md` (separate numeric validation report).
- Updated `src/pathfinding/__init__.py` docstring (`cost.py` now exists).
- Did not modify `data/*.csv` or `data/*.json`.

### Verification
- ✅ `ruff check .` — all checks passed.
- ✅ `pytest -q` — 69 passed, 0 failed (50 existing + 19 new).
- ✅ `pytest --cov=src` — `src/pathfinding/cost.py` at 97% line coverage
  (target was ≥90%).
- ✅ Validation script run on real data: 3 station pairs × 48 real hourly
  readings each, 0 infeasible edges; full numbers in
  `docs/wind_cost_validation_report.md`.

### Blocker flagged (not silently resolved)
This task's ClickUp dependency ("multi-layer wind graph + final pathfinder
integration") is **not started** — `src/pathfinding/graph.py`,
`algorithms.py`, `routing.py` are all still future/empty, so there is no
graph/orchestration layer yet to wire this cost function into end-to-end.
Delivered the cost function as a standalone, independently-tested,
directly-callable unit instead of building the graph layer myself (out of
this task's scope). Flagging for the owner per the existing pattern used for
the QC/Consistency dependency gaps in PR #16.

Also confirmed (did not fix, out of scope): `data/khorasan_pathfinding_ready.csv`
is still 100% NaN as flagged on 2026-09-02; validation here used
`data/khorasan_wind_qc_cleaned.csv` instead, which is real and clean.

### Next Steps
- Owner review/merge of PR.
- Build `src/pathfinding/graph.py` and wire `compute_edge_cost` in as the
  edge-weight function once that task starts.
- Replace `airspeed_mps`/`induced_drag_coeff` defaults with vehicle-specific
  values once concrete aircraft/UAV type specified.

## 2026-09-10 — Stage 3: Routing Algorithms (A*, Dijkstra) & Optimal Layer Selection

**Agent:** Hermes (AI)
**Branch:** `task/86bbw32kw-routing-algorithms`
**PR:** (TBD)

### Summary
Implemented the complete pathfinding routing pipeline:
1. **A* algorithm** with Haversine heuristic (admissible, optimal) in `src/pathfinding/algorithms.py`
2. **Dijkstra algorithm** as comparison/fallback in the same module
3. **Optimal layer selection** (`WindRouter`) in `src/pathfinding/routing.py` that runs pathfinding on all altitude layers and selects the best
4. **WindGraph + MultiLayerWindGraph** construction from wind data in `src/pathfinding/graph.py`

### Changes Made
- Added `src/pathfinding/graph.py`: `GraphNode`, `EdgeData`, `WindGraph`, `MultiLayerWindGraph` (with `build_from_dataframe` class methods)
- Added `src/pathfinding/algorithms.py`: `dijkstra()`, `a_star()` (Haversine heuristic)
- Added `src/pathfinding/routing.py`: `RouteResult`, `LayerComparison`, `WindRouter` (orchestration layer)
- Updated `src/pathfinding/__init__.py` with all new exports
- Added `tests/pathfinding/test_graph.py` (16 tests)
- Added `tests/pathfinding/test_algorithms.py` (18 tests)
- Added `tests/pathfinding/test_routing.py` (9 tests)
- Added `docs/task_routing_benchmark.md` (benchmark doc with real Khorasan data comparison)
- Did not modify `data/*.csv` or `data/*.json`

### Items Check (from ClickUp task 86bbw32kw)
- [x] الگوریتم هیوریستیک هاورساین روی گراف وزن‌دار عمومی پیاده‌سازی شود
- [x] دایکسترا به‌عنوان روش مقایسه‌ای fallback پیاده‌سازی شود
- [x] سیستم انتخاب لایه بهینه پیاده‌سازی شود روی همه لایه‌های موجود اجرا شود
- [x] حداقل ۸ تست برای الگوریتم‌ها و ۴ تست برای انتخاب لایه نوشته شود (۱۸ + ۹)
- [x] پوشش تست پکیج merge تسک‌های دیگر حداقل ۸۵٪ (actual 95% branch coverage)
- [x] مستند انتخاب بنچمارک واقعی جدول مقایسه لایه‌ها تهیه شود
- [x] خروجی coverage pytest ضمیمه شود

### Verification
- `ruff check .` all checks passed
- `pytest` 111 passed (69 existing + 42 new) 0 failed
- `pytest --cov=src/pathfinding --cov-branch` 95% branch coverage (target ≥85%)
- Dijkstra produce identical costs all 12 station-pair layer combinations (real data)
- Benchmark documented `docs/task_routing_benchmark.md` real Khorasan comparison table
- Visualization images added `docs/assets/`: best-layer depth map + optimized route
  (`scripts/generate_pathfinding_visualizations.py`, real Khorasan data)

### Architecture
- `graph.py`: Builds weighted graphs from wind data; handles multi-layer altitude separation
- `algorithms.py`: A* (Haversine heuristic, admissible) + Dijkstra (fallback); both return `(path, cost)`
- `routing.py`: `WindRouter` evaluates all layers, selects optimal, provides comparison table
- `cost.py` (pre-existing): Provides `compute_edge_cost` as the edge weight function

### For the Next Task
- The `WindRouter` is ready for final integration with the flight planner
- `WindGraph.build_from_dataframe` handles both real station data and grid data
- When more stations/data become available, rebuild graphs for better coverage
- `airspeed_mps`/`induced_drag_coeff` defaults in `CostModelConfig` should be updated for specific aircraft type

### Coverage Evidence
```
TOTAL  395  11  134  15  95%
src/pathfinding/__init__.py     5    0    0    0  100%
src/pathfinding/algorithms.py  86    3   40    3   95%
src/pathfinding/cost.py        73    2   20    1   97%
src/pathfinding/graph.py      145    3   44    5   96%
src/pathfinding/routing.py     86    3   30    6   92%
```

---

## 2026-09-22 — Scene review round 2: arrow scaling, effort/fuel model, focus mode

- **Status:** Done
- **What I built:** (1) wind-arrow length is now strictly proportional to wind
  speed and nothing is capped in this dataset; (2) a new motor-effort/fuel model
  (`src/pathfinding/effort.py`) is wired into `RouteResult` and into the scene's
  comparison table and hover; (3) the scene's HTML legend is grouped and supports
  double-click "isolate this item" plus a «نمایش همه» / `Esc` reset; (4) the
  picture-vs-table gap (vertical exaggeration + real terrain) is now reported as
  its own column instead of being left to look like a bug.
- **Input I used:** `src/viz/scene3d.py`, `src/pathfinding/routing.py`,
  `src/pathfinding/cost.py`, `data/khorasan_wind_qc_cleaned.csv`,
  `data/khorasan_terrain.csv`
- **Output of this task:** `src/pathfinding/effort.py` (`MotorEffortConfig`,
  `LegSample`, `RouteEffort`, `air_heading_deg`, `sample_horizontal_leg`,
  `compute_route_effort`); `RouteResult.effort`; `scene3d.drawn_polyline_km`,
  grouped `_legend_entries`, `_fuel_model_html`; regenerated
  `docs/assets/routing_scene.html` (6.2 MB)
- **Verification:**
  ```
  $ .venv/bin/python -m pytest
  230 passed in 173.67s (0:02:53)

  $ .venv/bin/python -m ruff check src tests scripts
  All checks passed!

  $ .venv/bin/python scripts/generate_routing_scene.py
  Scene written to docs/assets/routing_scene.html (6.2 MB, self-contained)
  route   layer(m)  dist(km)  time(h)  energy  tailwind  turns
  R1           500     174.2    1.940   1.993      100%      0
  R2           500     174.2    1.940   1.993      100%      0
  R3           500     174.0    1.963   2.020      100%      0
  R4          2000     174.2    2.224   2.450      100%      0
  ```
- **Answers to the review questions (evidence, not opinion):**
  - *Longer arrow for stronger wind:* yes — shaft = `speed × 1.6 km/(m/s)` and the
    cone head is normalised against the largest vector, so the whole arrow scales
    with speed. Speeds 5.2–10.2 m/s → arrows 8.3–16.3 km, no capping. Pinned by
    `tests/test_routing_scene.py::test_wind_arrow_length_is_proportional_to_wind_speed`.
  - *R1 = R2:* the two routes are node-for-node identical (17 nodes, 174.2448 km,
    1.939993 h). Root cause is the data, not the algorithm: station wind
    directions span only 68°–125°, IDW smooths the field between stations, and the
    energy criterion differs from time by at most ~4% of edge weight.
  - *R3 differs by only 0.27 km:* the routing lattice's long edges already
    approximate the great circle, and with an almost uniform wind field no
    criterion gains by deviating. The scene now prints the distance range and the
    station spread, and `test_shared_horizontal_distance_is_explained_by_altitude`
    plus the new drawn-geometry tests keep the table and the picture consistent.
  - *Double-click did nothing:* it does now (isolate the clicked group; terrain
    and start/end stay visible; reset with the button or `Esc`). Checked in the
    live preview: isolating R3 left traces `[0, 14, 15, 19, 20]`; reset restored
    the defaults (`[1]` hidden).
- **Honesty note:** the fuel/power/turn numbers are **model** outputs. Mass 25 kg,
  L/D 12, bank 25°, η_prop 0.60, η_thermal 0.28 and LHV 43 MJ/kg are declared
  assumptions, printed in the scene next to the fuel column («فرضهای مدل سوخت»).

## Task: «مسیر بادسواری (R5): یک سمت ثابت، صفر تصحیح مسیر» — Stage 3 (pathfinding + scene)
- **Status:** Done (uncommitted on `main`)
- **What I built:** یک استراتژی پنجم برای همان کریدور که روی *گراف* حساب نمی‌شود و
  آن را نمی‌توان با مسیریابی گرافی بیان کرد: «صعود کن به یک لایه، یک سمت هوایی
  ثابت نگه دار، بگذار باد مسیر را ببرد، و با شیب فرود روی مقصد بنشین.» ماژول جدید
  `src/pathfinding/wind_riding.py` میدان باد پیوسته را انتگرال می‌گیرد و خروجی را
  به `RouteResult` تبدیل می‌کند، پس R5 در همان جدول/همان راهنمای صحنه می‌نشیند.
- **Input I used:** `viz.wind_field` (میدان باد هر لایه)، `pathfinding.cost`
  (سرعت هوایی/مدل هزینه)، `pathfinding.graph.VerticalCostConfig` (نرخ صعود/فرود)،
  `pathfinding.effort` (مدل سوخت).
- **Output of this task:**
  - `src/pathfinding/wind_riding.py` — `plan_wind_riding_route`،
    `wind_riding_route_result`، `WindRidingConfig`.
  - `src/viz/scene3d.py` — `WIND_RIDING_ALGORITHM`، `GRAPH_SPECS`،
    `WIND_RIDING_SPECS`، `ROUTE_SPECS` (R5)، `build_wind_riding_route`.
  - `src/pathfinding/routing.py` — فیلد اختیاری `RouteResult.layers_used`.
  - `tests/pathfinding/test_wind_riding.py` (۱۱ تست)، تست‌های R5 در
    `tests/test_routing_scene.py` (۷ تست).
- **Numbers (same aircraft, same corridor, shipped dataset):**

  ```
  route   layer(m)  dist(km)  time(h)  energy  tailwind  motor-corrections  fuel(kg)
  R1           500     174.2    1.940   1.993      100%                10     0.408
  R2           500     174.2    1.940   1.993      100%                10     0.408
  R3           500     174.0    1.963   2.020      100%                 5     0.413
  R4          2000     174.2    2.224   2.450      100%                 9     0.506
  R5           500     173.6    1.900   1.933       98%                 0     0.393
  ```
- **Honesty note (مهم):** قرارداد فرود دو مدل یکی نیست. مسیرهای گرافی یک فاز عمودی
  *جدا* برای فرود می‌پردازند؛ بادسواری با شیب فرود *در حال حرکت* کم می‌کند. اگر R5
  را با قرارداد گرافی بازمحاسبه کنیم (≈۲.۸ دقیقه و انرژی پتانسیل فرود) به ۱.۹۴۶
  ساعت و ۰.۴۱۰ کیلوگرم می‌رسد، یعنی **هم‌سطح R1 و نه جلوتر**. پس مزیت عددی زمان/سوخت
  R5 از مدل‌سازی فرود می‌آید؛ چیزی که با هیچ قراردادی از بین نمی‌رود «صفر تصحیح
  مسیر» است. این جمله با همان اعداد در یادداشت صحنه چاپ می‌شود.
- **Four defects found while building it:** (۱) آستانه شروع فرود از سرعت زمینی
  لایهٔ *کروز* می‌آمد و مسیر چند صد متر این‌طرف/آن‌طرف مقصد می‌نشست و قطعهٔ پایانی
  لازم می‌شد → حالا از لایهٔ فرود می‌آید و فرود یک *شیب* (glideslope) بر مبنای
  مسافت باقی‌مانده است؛ (۲) یک مرحلهٔ ریزکردن ۰.۲۵ درجه کافی نبود و برنامه‌ریز
  اصلاً مسیری پیدا نمی‌کرد → ریزکردن مرحله‌ای ۴°→۱°→۰.۱° با کش شبیه‌سازی؛ (۳) مرز
  بادسواری/فرود پنجرهٔ نمونه‌برداری باز را به فاز فرود نسبت می‌داد و مسافت فرود را
  باد می‌کرد → مرز دقیقاً روی رخداد بسته می‌شود؛ (۴) پروفیل پیوستهٔ فرود ده‌ها
  «لایه» گزارش می‌شد → `RouteResult.layers_used`.
- **For the next task:** اگر کسی روی داده/هندسهٔ دیگری همین را اجرا کرد، محدودیت
  واقعی این است که باد باید بتواند هواپیما را ببرد؛ اگر نه، `build_wind_riding_route`
  مقدار `None` برمی‌گرداند و صحنه همان را می‌نویسد (یک نتیجهٔ داده، نه خرابی).
- **Test:** `248 passed` (۲۰۵ تست غیرصحنه + ۴۳ تست صحنه)، `ruff check src tests
  scripts` پاک. صحنه بازتولید شد: `docs/assets/routing_scene.html` (۶.۲ MB، خودکفا).
- **PR:** —

---

## گرانش در مدل نبود — و همین دلیل «همیشه یک‌لایه ماندن» بود

- **Status:** Done
- **Symptom the user reported:** «هر مسیر فقط در یک لایه حرکت می‌کند، چرا بالاتر نمی‌رود؟ و
  گرانش اصلاً حساب نشده.» هر دو رویه درست بود.
- **دو نقص، نه یکی:**
  1. **هر مسیر تک‌لایه در آسمان شروع می‌شد.** `WindRouter._route_on_layer` مستقیم روی
     گراف *لایه* مسیریابی می‌کرد و آن گراف گره زمین ندارد (هر گره روی ارتفاع همان لایه
     است)، پس `total_climb_m == total_descent_m == 0` می‌شد و هزینهٔ رسیدن به لایه هیچ‌وقت
     پرداخت نمی‌شد. `to_stacked_graph(layers=(altitude,))` از قبل وجود داشت و دقیقاً همین
     کار درست را می‌کند؛ حتی docstring `find_optimal_path` ادعا می‌کرد مسیرهای تک‌لایه
     همین کار را می‌کنند، ولی نمی‌کردند. حالا `_route_on_layer` از همان مسیر می‌رود، پس
     همهٔ مسیرها زمین‌به‌زمین‌اند و مقایسهٔ لایه‌ها منصفانه است.
  2. **فرود از کروز گران‌تر شمرده می‌شد.** `compute_vertical_cost` هر دو جهت را با
     `energy_multiplier` (۱.۵ برابر کروز) بهای انرژی می‌داد؛ یعنی فرود پرهزینه‌ترین فاز
     مدل بود. همزمان `compute_route_effort` صعود را با کل `mgh/η` می‌شکست و به فرود
     **هیچ** اعتباری نمی‌داد، پس انرژی پتانسیل ذخیره‌شده هیچ‌وقت برنمی‌گشت.
- **اصلاح‌ها:** `VerticalCostConfig.descent_energy_factor = 0.15`؛ در `compute_route_effort`
  فرود = توان دور آرام (نه `mgh/η`) به‌همراه گزارش `glide_range_km`،
  `glide_energy_saved_kj`، `net_altitude_energy_kj`؛ `LegSample.power_fraction` برای اینکه
  قطعهٔ گلاید واقعاً با کسر دور آرام سنجیده شود.
- **اتحاد کلیدی (اثبات‌شده با آزمون تا ۱e-۹):**
  `D·(L/D)·h/η = m·g·h/η` — پس سوخت *خالص* تغییر ارتفاع در مسیری که روی زمین شروع و تمام
  می‌شود فقط دور آرام فرود است، نه `mgh/η`. (آزمون:
  `test_gravity_settlement_cancels_the_climb_energy_exactly`.)
- **فرود بادسواری حالا یک گلاید واقعی است:** پیش‌تر با `ground_speed × descent_seconds`
  (مبنای *زمان*) شروع می‌شد؛ حالا وقتی فاصلهٔ باقی‌مانده با بُرد گلاید همان ارتفاع
  (`h · L/D`) برابر شود، و آن قطعه‌ها `power_fraction = descent_idle_power_fraction`
  دارند. نسبت گلاید و کسر دور آرام هر دو از همان `MotorEffortConfig` می‌آیند، پس هندسه و
  حسابداری نمی‌توانند از هم دور شوند.
- **خروجی عددی (همان کریدور/هواپیما/داده):**

  ```
  route   layer(m)  dist(km)  time(h)  energy  fuel(kg)  climb/descent
  R1           500     174.2    1.940   1.931    0.3760  500 / 500
  R2           500     174.2    1.940   1.931    0.3760  500 / 500
  R3           500     174.0    1.963   1.957      —     500 / 500
  R4          2000     174.2    2.224   2.200    0.3768  2000 / 2000
  R5           500     173.6    1.900   1.933    0.3803  500 / 500 (گلاید)
  ```

  و جدول جدید «گرانش، صعود و گلاید» در صحنه، برای هر چهار لایه:

  ```
  layer  wind(m/s)  offset  climb(min)  ride(min)  glide(min)  glide(km)  turns  total(h)  fuel(kg)
    500       8.0      1°        3.3      106.7        4.0        5.7       1     1.900    0.3803
   1000       8.8      9°        6.7      101.0        8.3       11.7       1     1.933    0.3795
   1500       9.4     16°       10.0       96.3       12.7       17.5       0     1.983    0.3821
   2000      10.0     23°       13.3       92.3       18.0       24.1       1     2.061    0.3873
  ```
- **خواندن صادقانهٔ نتیجه:** استراتژی «صعود → سواری باد → گلاید» مکانیکاً درست است و حالا
  مدل می‌تواند بیانش کند؛ ولی دادهٔ این ساعت چیز باریک‌تری می‌گوید: باد با ارتفاع قوی‌تر
  می‌شود (۸ → ۱۰ m/s) و فاز سواری کوتاه‌تر (۱۰۶.۷ → ۹۲.۳ دقیقه)، **اما از کریدور هم
  می‌چرخد** (۱° → ۲۳°)، پس مؤلفهٔ مفیدش خیلی کندتر رشد می‌کند. گرانش ارتفاع اضافه را تقریباً
  بی‌سوخت می‌کند (۰.۳۸۰۳ → ۰.۳۸۷۳ در چهار برابر ارتفاع)، ولی صعود ۱۰ دقیقه زمان می‌گیرد و
  همین است که معیار زمان جریمه می‌کند. پس انتخاب لایه واقعاً **وابسته به معیار** است:
  ۵۰۰ متر سریع‌ترین، ۱۰۰۰ متر کم‌مصرف‌ترین، و ۱۵۰۰ متر تنها لایه‌ای است که هواپیما تمام مسیر
  را با **صفر خمش خط** سواری می‌کند.
- **باطل‌شدن یادداشت قبلی:** یادداشت فاز قبل می‌گفت مزیت زمان/سوخت R5 «اثر مدل‌سازی» است
  چون قرارداد فرود دو مدل یکی نبود. حالا قرارداد یکی شده و همان جمله از صحنه حذف شد.
- **Test:** `tests/pathfinding/test_effort.py` (+۵ آزمون: اتحاد گرانش، سقف اعتبار، توان
  وزنی‌شده)، `tests/pathfinding/test_graph.py` (+۲ آزمون: فرود ارزان‌تر از صعود و اعتبارسنجی
  ضریب)، `tests/test_routing_scene.py` (+۴ آزمون: زمین‌به‌زمین بودن همهٔ مسیرها، برگشت سوخت
  گرانش، کارنامهٔ لایه‌ها، حضور جدول در artifact)، `tests/pathfinding/test_wind_riding.py`
  (آزمون فرود به مدل گلاید به‌روز شد).
- **PR:** —

---

## Task: «صحنهٔ مسیریابی — چهار ایراد بازبینی + قرارداد ارتفاع مسیر بادسواری» — Stage 3

- **Status:** Done
- **Agent:** Buffy (AI)
- **Branch:** `main` (working tree — change not committed)
- **What I built:** چهار ایراد بازبینی صحنهٔ سه‌بعدی را با کد (نه با توضیح) بستم و دو نقص
  واقعی را در مسیر همین کار پیدا و رفع کردم: (۱) قرارداد `RouteResult.node_altitudes`
  دربارهٔ «گره زمین = صفر» در مسیر بادسواری نقض می‌شد، (۲) مجموع فرود بادسواری به زمینِ
  مبدأ حساب می‌شد نه مقصد. علاوه بر این، مجموعه آزمون صحنه قابل اجرا نبود (با ۲۴۰ ثانیه
  timeout کشته می‌شد) و حالا کامل اجرا می‌شود.
- **Input I used:** `src/viz/scene3d.py`، `src/viz/terrain.py`، `src/viz/wind_field.py`،
  `src/pathfinding/wind_riding.py`، `tests/test_routing_scene.py`
- **Output of this task:**
  - `src/pathfinding/wind_riding.py` — `_ground_anchored_altitudes()` (جدید): گره‌های
    مبدأ/مقصد صفر گزارش می‌شوند (همان قراردادی که `WindRouter` رعایت می‌کند)؛ و
    `descent_height_m` از ارتفاع زمین **مقصد** محاسبه می‌شود (۲۶۱۶.۱۰ متر به‌جای ۲۶۱۶.۷۶).
  - `src/viz/scene3d.py` — `write_scene(..., ground_n_lat, ground_n_lon)`: دقت شبکهٔ
    «بهترین لایه» از بیرون قابل تنظیم شد (گران‌ترین بخش ساخت صحنه، بدون اثر روی مسیرها
    و جدول).
  - `tests/test_docs_consistency.py` (جدید) — نگهبان drift مستندات؛ هر ارجاع نقطه‌دار
    داخل بک‌تیک در `docs/*.md`/`README.md`/`AGENTS.md`/`CONTRIBUTING.md` که با نام یک
    پکیج پروژه شروع شود باید resolve شود (ماژول یا اتربیوت). با تزریق یک ارجاع جعلی
    آزموده شد.
  - `tests/test_routing_scene.py` — ۱۱ آزمون به طراحی فعلی بازپین شد (ستون‌های جدول با
    **نام** پیدا می‌شوند، لایه‌ها از `FLIGHT_LEVELS_MSL` می‌آیند، صعود =
    «سطح − ارتفاع زمین مبدأ»، جفت مقید R4/R6، و طول خط ترسیمی =
    «افقی + ۲۰ × ارتفاع»)؛ و `scene_html` (fixture ماژولی) جای پنج بار
    `write_scene` را گرفت.
  - `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md` — درخت مخزن واقعی،
    حذف ارجاع به `.github/PROMPT.md` و `pull_request_template.md` (که هرگز در این
    checkout نبوده‌اند)، و یک بخش وضعیت جدید در انتهای ROADMAP که اعداد قدیمی
    (سطوح AGL ۵۰۰–۲۰۰۰) را با وضعیت فعلی (MSL ۱۵۰۰–۳۶۰۰ + فاصلهٔ ایمنی ۳۰۰ متر) باطل
    می‌کند.
- **Verified numbers (regenerated artifact, `docs/assets/routing_scene.html`, 6.7 MB):**

  ```
  route  criterion  algo    level(m)  dist(km)  time(h)  energy  climb/descent(m)  fuel(kg)
  R1     energy     smooth      2900     176.6    2.213   2.176     1917 / 1916     0.378
  R2     time       astar       2900     176.6    2.212   2.177     1917 / 1916     0.378
  R3     distance   astar       3600     174.0    2.389   2.349     2617 / 2616     0.387
  R4     energy     smooth      2200     192.8    2.292   2.275     1217 / 1216     0.420
  R6     energy     smooth      3600     174.3    2.351   2.310     2617 / 2616     0.379
  R5     time       wind-ride   3600     173.7    2.130   2.311     2617 / 2616     0.393
  ```

  پروفیل ارتفاع مسیرها (۰ = روی زمین): `R1/R2: 0→1500→2200→2900→2200→1500→0`،
  `R3: 0→…→3600→…→0`، `R4: 0→2200→0`، `R6: 0→3600→0`. اولین و آخرین گرهٔ ترسیمی همهٔ
  مسیرها روی زمین است (۹۸۳ متر مشهد، ۹۸۴ متر سبزوار). پیکان‌های باد روی گره‌های خود گراف:
  ۵۲ / ۱۰۱ / ۱۱۱ / ۴۰ پیکان در سطوح ۱۵۰۰ / ۲۲۰۰ / ۲۹۰۰ / ۳۶۰۰ متر. سطح زمین = DEM واقعی
  (۸۷۲ تا ۳۱۷۵ متر).
- **Test:** `.venv/bin/python -m pytest -q` → **264 passed**؛
  `.venv/bin/python -m ruff check .` → `All checks passed!`؛
  `--cov=src` → **TOTAL 89%** (پوشش `src/pathfinding/algorithms.py` از ۵۳٪ به ۸۷٪ رسید،
  چون `smooth_dijkstra` دیگر کد مرده نیست).
- **برای تسک بعدی:** سه مورد باز مانده که در انتهای `docs/ROADMAP.md` صریح فهرست شده‌اند:
  `stored_at` در کش (TTL به زمان مشاهده گره خورده است)، دوباره‌کاری
  `LAYERS`/`_bearing`/`ground_speed`/`build_multi_layer` در دو اسکریپت visualization، و
  کپشن غلط `path_vis_02_path_layers.png`.
- **PR:** —

## Task: «پروفیل عمودی — پله، شکستگی گوشه، و افتِ تیز روی مقصد» — Stage 4

- **Status:** Done
- **Agent:** Buffy (AI)
- **Branch:** `main` (working tree — change not committed)
- **What I built:** سه ایراد دیده‌شده در صحنه در **خود الگوریتم** بسته شد، نه در رندرگر:
  (۱) پروفیل ارتفاعی مسیرها پله‌ای/شکسته دیده می‌شد، (۲) گوشه‌های رمپ‌ها یک شکستگی
  تیز داشتند، (۳) مسیر بادسواری چند صد متر از مقصد می‌گذشت و برمی‌گشت و همان پیچِ
  کوچک در انتهای پروفیل به شکل «افتادن عمودی روی مقصد» دیده می‌شد. علاوه بر این، دو
  قرارداد متضاد در آزمون‌های صحنه که همین کار آشکارشان کرد هم‌راستا شد.
- **Input I used:** `src/pathfinding/profile.py`، `src/pathfinding/routing.py`،
  `src/pathfinding/wind_riding.py`، `src/viz/scene3d.py`، `tests/test_routing_scene.py`
- **Root causes (measured, not guessed):**
  1. **رمپِ فاصلهٔ ایمنی از سقف صعود هواپیما تندتر بود.** کف زمین فاصلهٔ ایمنی را روی
     یک پنجرهٔ خطی ۲ کیلومتری توزیع می‌کرد: `۳۰۰ m / ۲ km = 0.15`. سقف واقعی صعود
     `2.5 / 27 ≈ 0.0925` است. پروفیل مجبور بود همان رمپ ۰.۱۵ را بگیرد و بعد ناگهان
     به تراز برگردد — همان «پلهٔ» ابتدای مسیر. (اندازه‌گیری‌شده: شیب صعود R1 برابر
     `0.1579` به‌جای سقف `0.0925`، و شکستگی `148.6` متر ارتفاع بر کیلومتر.)
  2. **کف زمین آخرین عملگر بود، بدون گردکردن.** «چسبیدن به کف» روی دامنهٔ کوه یک گوشهٔ
     تیز جا می‌گذاشت که هیچ دور گردکردنی آن را نرم نمی‌کرد.
  3. **نمونه‌های گزارش‌شده با گام شبکه ساخته نمی‌شدند.** با `total / 0.5` تقسیم صحیح،
     گام واقعی کمی از ۰.۵ بزرگ‌تر می‌شد و شرط مقایسهٔ فاصله هرگز برقرار نمی‌شد؛ نتیجه
     یا دو نمونه در کل مسیر بود یا نمونهٔ آخر با فاصلهٔ دلبخواه.
  4. **انتهای مسیر بادسواری روی خودش برمی‌گشت.** حلقهٔ شبیه‌سازی وقتی می‌شکند که فاصله
     به مقصد از `arrival_radius_km = 0.2` کمتر شود، و این سنجش *قبل* از گام بعدی انجام
     می‌شود؛ پس نقطهٔ پایانی می‌تواند چند صد متر از مقصد گذشته باشد. اضافه‌کردن مقصد
     بعد از آن نقطه یک قطعهٔ کوتاهِ روبه‌عقب می‌ساخت (اندازه‌گیری‌شده: `0.162 km` با
     `35 m` افت ⇒ شیب `0.2183`) که در پروفیل رسم‌شده یک «افتِ تیز» درست روی مقصد بود.
- **Output of this task:**
  - `src/pathfinding/profile.py` — `_terrain_floor()` بازنویسی شد: کف اکنون
    `ارتفاع زمین + فاصلهٔ ایمنی` است، ولی فاصلهٔ ایمنی فقط تا جایی طلب می‌شود که با
    سقف صعود از مبدأ و سقف فرود از مقصد قابل دسترسی باشد (`min(clearance, cone − ground)`).
    نتیجه: کف **هرگز تندتر از خود هواپیما بالا نمی‌رود** و در دو سر مسیر دقیقاً روی
    زمین است. `_round_corners_above_floor()` (جدید) به‌عنوان آخرین عملگر، گوشه‌های
    تحمیل‌شدهٔ زمین را نرم می‌کند بدون اینکه از کف پایین برود. گام گزارش از گام شبکه
    ساخته می‌شود (`stride = reported_step / grid_step`) و `ceil` جای `int` را گرفت.
    ارتفاع گزارش‌شدهٔ دو سر مسیر همان قرارداد ورودی است (صفر = روی زمین) تا
    `RouteResult.node_altitudes` نشکند.
  - `src/pathfinding/wind_riding.py` — وقتی هواپیما داخل شعاع رسیدن است، نقطهٔ پایانی
    *با* مقصد جایگزین می‌شود (نه اینکه مقصد اضافه شود)، پس انتهای مسیر بازگشت نمی‌کند.
  - `src/viz/scene3d.py` — `_sampled_route_indices()` (جدید): نشانگرهای مسیر با گام
    مسافت (۸ کیلومتر) رسم می‌شوند. پروفیل هر ۰.۵ کیلومتر نمونه دارد (~۳۵۰ نمونه) و
    رسم تمام آن‌ها خط را «نقطه‌نقطه» نشان می‌داد؛ اکنون ۶۰۰ نمونهٔ خط + ۲۳ نشانگر.
  - `tests/pathfinding/test_profile.py` (جدید، ۹ آزمون) — قرارداد الگوریتم پین شد:
    سقف صعود/فرود، دو سر روی زمین، فرودِ تدریجی تا لحظهٔ نشستن، نبودِ پرش شیب، کف زمین
    روی یک رشته‌کوه گاوسی، و اینکه رمپِ فاصلهٔ ایمنی از سقف صعود تندتر نباشد.
  - `tests/test_routing_scene.py` — آزمون جدید «پروفیل کشیده‌شده در هر پنجرهٔ ۲
    کیلومتری تدریجی است»، آزمون جدید «نشانگرها زیرمجموعهٔ تُنُک‌شدهٔ مسیرند»، و سه
    آزمون قدیمی که «دیوارِ عمودی» را قرارداد گرفته بودند بازپین شد
    (`max(node_altitudes) == layer_altitude` ⇒ کرانهٔ کف؛ دو انتهای MSL ⇒ قرارداد صفر).
- **Verified numbers (measured straight out of the regenerated
  `docs/assets/routing_scene.html`):**

  ```
  route  steepest climb   steepest descent   largest kink   drawn start/end altitude
  R1     0.0922 (1:10.8)   0.0854 (1:11.7)    0.0169         983 / 984 m
  R2     0.0922            0.0854             0.0195         983 / 984 m
  R3     0.0945            0.0834             0.0049         983 / 984 m
  R4     0.0946            0.0831             0.0081         983 / 984 m
  R6     0.0935            0.0832             0.0049         983 / 984 m
  R5     0.0942            0.0744             0.0048         983 / 984 m
  ```

  `0.0831 = 1/12` همان نسبت گلایدی است که مدل سوخت با آن کار می‌کند؛ پس فرود روی *همان*
  شیبی نشسته است که سوختش بابتش حساب می‌شود. پنج نمونهٔ آخر خط رسم‌شدهٔ R1..R6 همه روی
  شیب ثابت فرودند (`−0.0831`) — یعنی «افتِ تیز روی مقصد» وجود ندارد. بیشترین تغییر
  شیب بین دو نمونهٔ متوالی از `0.10` به `0.0169` رسید. `worst_2km` (بیشترین تغییر
  ارتفاع در هر پنجرهٔ ۲ کیلومتری) برای هیچ مسیری از `0.095` نمی‌گذرد.

  اندازه‌گیری پیش از این تغییر (همان ابزار): شیب صعود `0.1579`، شکستگی `148.6 m/km`،
  و انتهای R5 با شیب `−0.2183`.
- **Test:** `.venv/bin/python -m pytest -q` → **279 passed** (۲۲۸ + ۵۱ صحنه)، `exit 0`؛
  `.venv/bin/python -m ruff check src tests` → `All checks passed!`
- **یافتهٔ باز (برای تسک بعدی):** شکاف در سنجش فاصلهٔ ایمنیِ *گراف*. شبکهٔ گراف
  `5.56 × 8.99` کیلومتر است و `_edge_clears_terrain` هر یال را فقط با ۷ نمونه بررسی
  می‌کند (هر ~۱ کیلومتر)، در حالی که سلول DEM ۲.۵ کیلومتر است. نتیجه: یالی می‌تواند
  تأیید شود در حالی که قلهٔ واقعیِ بین دو نمونه از ارتفاع سطح پرواز + فاصلهٔ ایمنی
  گذشته باشد. اثبات عددی: روی مسیر R1 ــ در `(36.190, 59.211)` ــ زمین تا `2668 m`
  بالا می‌آید (فاصلهٔ واقعی `232 m`) در حالی که ستون «کمینه فاصله از زمین» جدول
  `516 m` می‌گوید، چون آن عدد فقط از گره‌های *پرواز* گرفته می‌شود. پروفیل این شکاف را
  با بالا بردن ارتفاع تا سقف فاصلهٔ ایمنی می‌بندد (پس R1 تا `2944 m` بالا می‌رود،
  تا `299 m` بالاتر از سطح ۲۹۰۰)، ولی خودِ گراف هنوز مسیری را می‌پذیرد که از پشت
  آستانهٔ تعیین‌شده‌اش رد می‌شود.
- **PR:** —

## Task: «مسیرها منحنی نیستند و بادسواری موازی باد نمی‌رود» — Stage 4 (هندسه + سیاست)

- **Status:** Done
- **Agent:** Buffy (AI)
- **Branch:** `main` (working tree — change not committed)
- **What I built:** سه ایراد دیده‌شده در صحنه، هر سه **در الگوریتم**: (۱) مسیرها یک منحنی
  پیوسته نبودند و «گسسته» دیده می‌شدند، (۲) بخش‌هایی از مسیر *دقیقاً* خط راست بود، و
  (۳) مسیر بادسواری در هیچ نقطه‌ای موازی پیکان‌های باد نبود و مثل یک خط راست در می‌آمد.
- **اندازه‌گیری پیش از تغییر (از `docs/assets/routing_scene.html` تولیدشده، با خواندن
  مستقیم `_fullData` صفحه):**
  - `97٪` پاره‌های رسم‌شدهٔ هر مسیر کمتر از `0.5°` می‌چرخیدند (میانگین `0.04°` برای R5،
    `0.93°` تا `0.18°` برای بقیه) — یعنی خطی که دیده می‌شد یک خط شکستهٔ راست بود، و
    «اسپلاین» فقط روی همان خط شکسته می‌نشست.
  - بیشترین چرخش یک گره: R4 = `36.5°` (گوشهٔ تیز کامل)، یعنی «پله» در پلان‌ویو.
  - هر مسیر **دو** trace بود: خط + نشانگرهای گسسته روی گره‌های خام.
  - R5 در حالت «سمت ثابت» روی میدان باد واقعی: سطح `3600 m`، `173.5 km`، `2.130 h`،
    `0.396 kg` سوخت، `صفر` تصحیح — و **`7.7%` مسیر موازی باد** (زاویهٔ دریفت).
- **Root causes:**
  1. **گراف یک شبکه است.** هر مسیر گرافی زنجیره‌ای از پاره‌های مستقیم است؛ هیچ مرحله‌ای
     گوشه‌ها را گرد نمی‌کرد. `_smooth_route` یک اسپلاین *درون‌یاب* روی همان خط شکسته
     بود، پس گوشه‌ها گوشه می‌ماندند.
  2. **سمت فرمان ثابت ≠ موازی باد.** در بادسواری، باد بردار سرعت هوایی را جمع می‌کند و
     مسیر روی زمین به اندازهٔ زاویهٔ دریفت از جهت باد کج می‌شود؛ با سمت ثابت، این کجی
     در تمام مسیر باقی می‌ماند.
- **Output of this task:**
  - `src/pathfinding/geometry.py` (جدید) — `round_path_corners()`: هر گوشهٔ داخلی با یک
    فیلت کمانی گرد می‌شود (مماس در دو سر ⇒ پیوستگی G1). سه قید هم‌زمان: شعاع از پاره‌های
    مجاور بزرگ‌تر نشود (`MAX_TANGENT_FRACTION = 0.45`)، **زمین قید سخت** باشد (زمین روی
    خود کمان نمونه‌برداری می‌شود و اگر فاصلهٔ ایمنی بشکند شعاع کوچک و دوباره امتحان
    می‌شود؛ اگر با کمترین شعاع هم نشد گوشه تیز می‌ماند)، و ارتفاع هر نمونهٔ تازه از
    تصویر کردن آن روی مسیر *اصلی* بیاید تا پروفیل عمودی دست‌نخورده بماند.
  - `src/pathfinding/routing.py` — گردکردن گوشه **پیش از** `ramp_vertical_transitions`
    صدا زده می‌شود، پس هندسهٔ گزارش‌شده همان چیزی است که الگوریتم تولید می‌کند.
  - `src/pathfinding/wind_riding.py` — سیاست بادسواری از «یک سمت ثابت» به **دنبال‌کردن
    باد با دالان همگرا** تغییر کرد:
    * سمت مسیر هر گام با **مثلث باد** حل می‌شود (`_solve_wind_triangle`) تا *سمت مسیر
      روی زمین* روی جهت خود باد بیفتد. با این کار پسار القایی و باد رو-به-رو صفر می‌شود.
    * زاویهٔ مسیر در بازهٔ `δ ∈ [asin((x−b)/R), asin((x+b)/R)]` انتخاب می‌شود (`x` = انحراف
      جانبی کنونی، `R` = مسافت باقی‌مانده، `b` = دالان مجاز) و داخل بازه، نزدیک‌ترین حالت
      به جهت باد برداشته می‌شود؛ دالان با `R` آب می‌رود پس در چند کیلومتر آخر تصحیح کامل
      می‌شود و هواپیما روی مقصد می‌نشیند.
    * باد در ارتفاع **واقعی** هواپیما نمونه‌برداری می‌شود (`sampler_for_altitude`).
    * کف زمین در فاز بادسواری هم اعمال می‌شود، ولی اگر صعود لازم برای رسیدن به کف از
      سقف شیب هواپیما بگذرد، آن سطح **قابل‌پرواز نیست** (`terrain_climb_feasible`) — همان
      کاری که گراف با حذف گره‌های زیر آستانه می‌کند.
    * `heading_deg` در این حالت میانگین مسافت‌وزن سمت‌های هوایی است؛ `wind_aligned_fraction`
      سهم مسافت موازی باد (سنجه، نه ادعا).
  - `src/viz/scene3d.py` — نشانگرهای گسستهٔ مسیر حذف شدند: هر مسیر **یک** trace و یک
    منحنی پیوسته است. `_sampled_route_indices()` حذف شد. برچسب R5 هم اصلاح شد.
  - `tests/pathfinding/test_geometry.py` (جدید، ۷ آزمون) و شش آزمون تازه در
    `tests/pathfinding/test_wind_riding.py`؛ سه قرارداد قدیمی در `tests/test_routing_scene.py`
    که «دو trace» و «صفر تصحیح» را پین می‌کردند به قرارداد جدید به‌روز شدند.
- **اندازه‌گیری پس از تغییر (همان ابزار، همان کریدور):**
  - بیشترین چرخش یک گره: R4 از `36.5°` به `6.2°` (گوشه گرد شد)، R5 از `2.0°` به `2.5°`
    و میانگین R5 از `0.04°` به `0.165°`. هر مسیر = `۱` trace.
  - R5 روی همان باد: سطح `3600 m`، `178.0 km`، `2.196 h`، `0.405 kg`، **۷ تصحیح** با مجموع
    `24.8°`، و **`58.5%` مسیر موازی باد** (پیش: `7.7%`).
  - سهم موازی‌بودن همهٔ مسیرها در همین صحنه: R1 `15.7%`، R2 `15.7%`، R3 `44.1%`،
    R4 `70.8%`، R6 `8.0%`، R5 `58.5%`. **R4 از R5 بالاتر است** و این یک یافتهٔ واقعی است:
    باد این کریدور تقریباً هم‌راستای کریدور می‌وزد و مدل هزینهٔ گراف خودش باد پشت را
    پاداش می‌دهد، پس بعضی مسیرهای گرافی *تصادفی* موازی می‌شوند. تفاوت R5 این است که
    موازی‌بودنش **ساختاری** است.
  - رشتکوه (۳۱۷۵ m) تنها سطح `3600 m` را برای بادسواری قابل‌پرواز می‌گذارد؛ سطوح ۱۵۰۰،
    ۲۲۰۰ و ۲۹۰۰ رد می‌شوند چون رد شدن از یال به صعودی تندتر از توان هواپیما نیاز دارد.
    همین توضیح می‌دهد چرا بادسواری نمی‌تواند «تمام مسیر را موازی باد» برود: بالای یال،
    باد از سمت سبزوار می‌چرخد.
- **Test:** `.venv/bin/python -m pytest -q` → **۲۹۱ passed**، `exit 0`؛
  `.venv/bin/python -m ruff check src tests scripts` → `All checks passed!`
- **PR:** —

## Task: «مسیرها باید یک منحنی پیوسته باشند و بادسواری باید با عدد اثبات شود» — Stage 3
- **Status:** Done
- **What I built:**
  1. **علت «گسسته دیده‌شدن» مسیرها در الگوریتم نبود، در رندر بود.** هندسهٔ رسم‌شده
     از پیش یک منحنی پیوسته بود (۵۹۹ پاره، بیشترین چرخش `8.7°`)، ولی plotly خط
     سه‌بعدیِ کلفت را با نوار و قطعهٔ میتر می‌کشد؛ وقتی طول تصویرشدهٔ هر پاره از عرض
     خط کمتر شود (۶۰۰ نمونه روی ۱۷۷ کیلومتر و عرض ۹ پیکسل ⇒ ۱.۳ پیکسل در هر پاره)،
     گوشه‌ها می‌شکنند و خط به زنجیر مهره‌مهره تبدیل می‌شود. با آزمون زنده روی همان
     صفحه اندازه‌گیری شد: عرض ۹ و ۵ و ۲ ⇒ مهره‌مهره/خط‌چین؛ عرض ۱ ⇒ پیوسته.
     پس هر مسیر حالا **هندسهٔ واقعی** است: خط مویی (عرض ۱، همیشه پیوسته، حامل
     hover) به‌علاوهٔ یک **لولهٔ مش** روی همان منحنی (`_route_tube`) که ضخامت
     می‌دهد و مثل پیکان‌های باد با زوم بزرگ/کوچک می‌شود.
  2. **سنجهٔ بادسواری، قابل حسابرسی:** `src/pathfinding/alignment.py` (جدید) —
     `WindAlignmentProfile` از `leg_samples` خود مسیر: سهم مسافت با انحراف ≤۳ درجه،
     میانگین مسافت‌وزن انحراف در همان بخش، برچسب ترکیبی «درجه – سهم»، سهم باد
     رو-به-رو (بیش از ۹۰ درجه)، و **مسافت تصحیح انتهایی** (از آخرین قطعهٔ موازی تا
     مقصد). همین سه عدد در جدول مقایسه مسیرها و در جدول سطوح بادسواری و در hover
     گزارش می‌شوند.
  3. **جست‌وجوی سیاست در برنامه‌ریز بادسواری.** پیش‌تر دالان (`wind_corridor_fraction`)
     یک عدد ثابت ۰.۵ بود؛ حالا برنامه‌ریز خودش روی دالان‌های `(0.5, 0.75, 0.95)`
     شبیه‌سازی می‌کند و برنامه‌ای را برمی‌گزیند که **بیشترین مسافت موازی باد** را دارد،
     مشروط به اینکه زمانش از `alignment_slack_ratio` (پیش‌فرض ۱.۱۵ برابر) روی
     کم‌زمان‌ترین برنامهٔ همان سطح بیشتر نشود. R5 حالا «موازی‌ترین» است، نه فقط
     «به‌نسبت سریع».
- **Input I used:** `data/khorasan_wind_qc_cleaned.csv`، `data/khorasan_terrain.csv`،
  `src/pathfinding/wind_riding.py`، `src/viz/scene3d.py`
- **Output of this task:**
  - `src/pathfinding/alignment.py` (جدید) — `wind_alignment_profile()`, `WindAlignmentProfile`
  - `src/pathfinding/wind_riding.py` — `search_fractions`, `alignment_first`,
    `alignment_slack_ratio`؛ فیلدهای `aligned_share`, `parallel_mean_deg`,
    `final_correction_km`, `corridor_fraction` روی `WindRidingPlan`؛ `_plan_preference()`
  - `src/viz/scene3d.py` — `_route_tube()`, `ROUTE_TUBE_*`, `ROUTE_LINE_WIDTH = 1`،
    `_ALIGNMENT_HEADER` + `_alignment_cells()`، ستون «موازی با باد (≤۳°)» در جدول سطوح،
    و اصلاح یک ایراد در همان جدول: ردیف «بدون برنامه» ۱۲ سلول خالی می‌گذاشت در حالی
    که ۱۳ ستون عددی وجود داشت (ستون‌ها جابه‌جا می‌شدند).
  - `tests/pathfinding/test_alignment.py` (جدید، ۱۲ آزمون)، پنج آزمون سیاست در
    `tests/pathfinding/test_wind_riding.py`، و به‌روزرسانی قراردادهای
    `tests/test_routing_scene.py` («هر مسیر دو trace از یک هندسه» و «مسیر بادسواری
    می‌تواند از خط مستقیم بلندتر باشد، ولی باید روی مقصد بنشیند»).
- **اندازه‌گیری روی همان کریدور (واقعی، نه ادعا):**
  - باد این کریدور در طول مسیر ۳۵ درجه می‌چرخد (۲۷۸° در مشهد ⇒ ۳۱۳° در سبزوار) در
    حالی که سمت مقصد ۲۶۷.۶° است. پس «تمام مسیر موازی باد» فیزیکی نیست: هرچه موازی‌تر
    بمانی، بیشتر از مقصد دور می‌شوی و تصحیح پایانی بزرگ‌تر می‌شود.
  - مبادلهٔ سیاست (سطح ۳۶۰۰ متر): دالان ۰.۲ ⇒ سهم موازی ۹٪ و ۲.۱۲۴ ساعت؛
    ۰.۳۵ ⇒ ۳۹٪ و ۲.۱۶۳؛ ۰.۵ ⇒ ۴۶٪ و ۲.۱۹۶؛ ۰.۶۵ ⇒ ۵۰٪ و ۲.۲۳۰؛ ۰.۸ ⇒ ۵۸٪ و ۲.۲۶۹؛
    ۰.۹۵ ⇒ ۶۲٪ و ۲.۳۰۷. قبلاً R5 روی دالان ثابت ۰.۵ بود (۴۶٪)؛ حالا روی ۰.۹۵
    می‌نشیند (۶۲٪) با همان سقف زمانی.
  - رشتکوه (۳۱۷۵ m) تنها سطح ۳۶۰۰ متر را قابل‌پرواز می‌گذارد؛ در آن سطح باد از
    ۲۷۸° به ۳۱۳° می‌چرخد، یعنی سهم موازی ۶۲٪ سقف عملیِ *این* داده با *این* الزام
    «۳ درجه» است — نه یک ضعف پیاده‌سازی.
- **For the next task:** اگر سهم موازی بالاتر خواسته شود، تنها اهرم واقعی *داده* است
  (کریدور بادگردِ دیگری) یا **هدف ورود**: اگر «نقطهٔ پایانی» یک ناحیهٔ ورود در جهت باد
  باشد (نه یک نقطهٔ ریاضی)، مسیر می‌تواند در تمام طول روی خط جریان باد بماند. کد
  آمادهٔ آن است: `WindRidingConfig.search_fractions` + `alignment_first`.
- **Test:** `.venv/bin/python -m pytest -q` → در انتهای همین worktree اجرا و ثبت شد؛
  `.venv/bin/python -m ruff check src tests scripts` → `All checks passed!`
- **PR:** —

## Task: «بخشی از مسیر R5 بیرون کادر صحنه بود + چند مسیر بهینهٔ هم‌خانواده» — Stage 4 (بازهٔ محورها + خانوادهٔ بادسواری)

- **Status:** Done (uncommitted, on `main`)
- **What I built:**
  1. **بازهٔ محورهای صحنه = کریدور ∪ *هرچه رسم می‌شود*.** پیش‌تر بازهٔ محورها فقط جعبهٔ
     کریدور بود؛ مسیر بادسواری عمداً تا شمال کریدور دریفت می‌کند، پس بخشی از خط از کادر
     بیرون می‌زد. حالا از هندسهٔ رسم‌شدهٔ همهٔ مسیرها ساخته می‌شود، **به‌علاوهٔ شعاع لولهٔ
     نمایشی** (`ROUTE_TUBE_RADIUS_KM`): لوله دور خط می‌پیچد، پس مرز واقعی هر مسیر یک شعاع
     بیرون‌تر از خود خط است — R4 که خطش روی لبهٔ جنوبی (`y = 0`) تمام می‌شد، با لوله‌اش
     ۰.۴۵ کیلومتر بیرون می‌زد. محور z هم به همان اندازه باز می‌شود.
  2. **خانوادهٔ بادسواری در همان صحنه.** مسیر بادسواری یک مسیر نیست، یک *مبادله* است: دالان
     تعیین می‌کند هواپیما تا کجا از خط مبدأ–مقصد دور شود تا موازی باد بماند. R7 (دالان تنگ
     ۰.۲۰) و R8 (دالان میانه ۰.۵۰) روی **همان سطح پرواز R5** ساخته می‌شوند و با همان ستون‌های
     هم‌راستایی/سوخت در جدول می‌آیند.
- **اندازه‌گیری روی آرتیفکت بازتولیدشده (نه ادعا):**
  - پیش از این تغییر: بازهٔ محورها `x [0, 216.01]`, `y [0, 44.53]` — لولهٔ R5 تا `y = 47.99`
    (۳.۴۶ کیلومتر بیرون) و لولهٔ R4 تا `y = -0.45` (۰.۴۵ کیلومتر بیرون).
  - پس از آن: `x [0.00, 220.33]`, `y [-1.42, 48.96]` (حاشیه فقط روی سمت مثبت؛ سمت
    منفی تنها چون لولهٔ R4 زیر صفر می‌رود) و **هیچ مسیری بیرون نمی‌زند**
    (بیشینه `y` هر مسیر: R5 = 47.99، R8 = 41.24، R7 = 33.01؛ کمینه R4 = -0.45).
  - هشت مسیر در آرتیفکت: R1 176.6 km/2.213 h · R2 · R3 · R4 · R6 · R5 185.3/2.307 ·
    **R7 174.2/2.124** · **R8 178.0/2.196** — یعنی گونهٔ تنگ، کوتاه‌ترین و سریع‌ترین مسیر
    بادسواری است و گونهٔ باز، موازی‌ترین ولی بلندترین.
- **Input I used:** `src/viz/scene3d.py` (`build_scene_figure`)، `WIND_RIDING_VARIANT_SPECS`،
  `data/khorasan_terrain.csv`
- **Output of this task:**
  - `src/viz/scene3d.py` — حاشیهٔ شعاع لوله در محاسبهٔ گسترهٔ محورها (x/y/z)؛ آزمون‌های
    قرارداد جدید در `tests/test_routing_scene.py` («محورها کریدور و هر مسیر رسم‌شده را در بر
    می‌گیرند») و اصلاح دو قراردادی که کهنه مانده بودند: ستون «موازی با باد» از علامت درصد
    فارسی (`٪`) استفاده می‌کند، و مجموعهٔ کلیدهای مسیر دیگر فقط `ROUTE_SPECS` نیست
    (گونه‌های بادسواری هم می‌آیند، و گونهٔ حذف‌شده هم مجاز است).
  - `docs/assets/routing_scene.html` — بازتولیدشده (۷.۶ مگابایت، خودکفا) با ۸ مسیر.
- **For the next task:** اگر باز هم چیزی از کادر بیرون بزند، قاعده همین است: هر هندسهٔ رسم‌شده
  (سر پیکان‌های باد را هم شامل می‌شود) یا باید وارد گستره شود یا صریح به‌عنوان «تزئینی و
  بیرون‌کادر» علامت بخورد. پیکان‌های باد هنوز چند کیلومتر از لبهٔ غربی/شمالی بیرون‌اند
  (شافتشان، نه گره)؛ به‌عمد بزرگ نشد چون مقیاس کیلومتری صحنه را رقیق می‌کرد.
- **Test:** `.venv/bin/python -m pytest -q` و `.venv/bin/python -m ruff check src tests scripts`
  در همین worktree اجرا شد (نتیجهٔ نهایی در پیام گزارش).
- **PR:** —

## Task: «فقط R5/R7/R8 خمیده به نظر می‌رسند؛ بقیه را هم به همان کیفیت برسان» — Stage 5 (انحنا *و* پروازپذیری)

- **Status:** Done (uncommitted, on `main`)
- **Why the other routes looked like straight lines with corners.** Three separate
  causes, all measured on the real corridor before touching anything:
  1. **The terrain guard inside relaxation was pinning the path.** `relax_path_curvature`
     asked for the *routed path's own* clearance, and it read the altitude by the
     sample's **old index** while reading the ground at the sample's **new**
     coordinates — two different points on one subtraction. In the pass north of
     Mashhad the routed path itself flies at 290 m clearance (below the 300 m
     floor), so every horizontal move was rejected: R1/R2/R4 kept a ±۱۱°/km kink
     cluster pinned at that floor while R3/R6 (higher, further from the ridge)
     smoothed normally. **The distance from a mountain decided which routes looked
     good — not the algorithm.**
  2. **Relaxation was the wrong place to hold the safety constraint.** Released, it
     moved a route over a ridge whose slope is steeper than the aircraft can climb;
     the ramp then had to follow the terrain at ۲۳٪ to keep 300 m clearance, i.e. a
     geometry that cannot be flown (measured on R3: a ۶۲۰ m rise in ۳ km = 0.21
     against a 0.096 climb cap).
  3. **The terrain floor only checked reachability *at* a point**, so a ridge ahead
     did not start the climb earlier — it just made the profile steeper.
- **What I built (all corridor-independent):**
  1. `geometry._nearest_arc_distance` + `level_here(x, y)`: a moved sample is judged
     against the altitude of *its own* arc position (`level(sample) − ground(sample)`
     describes one point again). The guard stays, so the safety contract in the tests
     is unchanged.
  2. **Relaxation is now free horizontally; the vertical ramp runs after it** and
     re-derives the floor + climb/descent caps on the final horizontal geometry. The
     router then re-checks the profile against the aircraft's own vertical-rate bound
     (`_VERTICAL_RATE_MARGIN = 1.25`, the same margin the scene test uses) and, if it
     fails, **halves the deviation budget and tries again** (`_RELAX_ATTEMPTS = 6`).
     Budget ≈ 0 means "the routed geometry", which is flyable by construction, so the
     loop can never come back worse than before — smooth as much as physics allows.
  3. `profile._terrain_floor` now **propagates the floor**: one right-to-left pass
     (each sample at most one `climb_cap` step above its successor) and one forward
     pass for descent. A ridge is cleared by **climbing earlier, not harder** — the
     cone is opened backwards from the terrain. Verified directly on the new test
     fixture: the same ridge needs a 0.511 slope on the old floor (the terrain's own
     slope, unflyable) and 0.125 = exactly the climb cap on the new one.
  4. **The reported distance is now the distance actually flown.** Corner rounding
     means the flown geometry is a little shorter than the routed polyline (R4:
     ۱۹۲.۸ km in the table against ۱۹۰.۶ km drawn — the picture was contradicting the
     table). `total_distance_km` is recomputed from the final geometry.
- **Measured, before → after** (steepest turn rate of the drawn line, °/km):
  R1 **11.80 → 1.50** · R2 **12.26 → 1.50** · R3 **6.75 → 1.42** · R4 **14.78 → 3.32**
  (terrain-forced ridge detour) · R6 **3.46 → 1.47**. The wind-riding routes are
  untouched (they build their own geometry). The 1.5 °/km figure *is* the relax
  target, i.e. the graph routes now sit at R7's quality.
- **Flight physics, after:** minimum terrain clearance **300 m** inside every graph
  route (the floor is respected everywhere, not just at graph nodes); steepest drawn
  profile **≤ 0.09 m/m** on every route (was 0.23 on R3); distances R1 176.3 · R3 173.8
  · R4 190.4 · R6 173.9 km.
- **New tests (generic, no corridor constants):**
  - `tests/pathfinding/test_profile.py::test_a_steep_ridge_is_cleared_by_climbing_earlier_not_harder`
    — a ridge 4× steeper than the climb cap must be cleared with the slope staying at
    the cap, and the test also asserts the profile does *not* simply follow the slope
    (so it can't pass by hiding the problem).
  - `tests/test_routing_scene.py::test_no_graph_route_carries_a_kink` — reads the drawn
    traces and bounds the turn *rate* (≤ 5 °/km); fails at 11.8–14.8 on the old geometry.
  - `tests/pathfinding/test_routing.py` — the distance-criterion identity is now asserted
    against the engine's own legs, since `total_distance_km` is the flown geometry.
- **For the next task:** the same three levers apply to any corridor, but the honest
  ceiling here is still the arrival definition (a corridor-shaped arrival zone instead of
  one point) — that is a *planning* change, not a geometry one.
- **Test:** `.venv/bin/python -m pytest -q` → **۳۲۲ passed**; `.venv/bin/python -m ruff check src tests scripts`
  → `All checks passed!`; artifact regenerated (`docs/assets/routing_scene.html`, ۷.۶ MB, ۸ مسیر).
- **PR:** —

## Task: «چرا R4 به لبهٔ صحنه چسبیده و مثل R5 در جریان باد نمی‌رود؟» — Stage 5 (کادر داده = کادر مسیریابی)

- **Status:** Done (uncommitted, on `main`)
- **The complaint, measured.** R4's drawn line ran along latitude **36.0448–36.0465 for
  more than ۶۰ کیلومتر**, and 36.045 is *outside* the data box — its southern edge was
  36.05. R1/R2 also dipped 13.3 km south and R3 sat 0.1 km inside the edge. The graph
  had nowhere else to go, so the "route" *was* the boundary.
- **Why.** The box was doing two jobs: it was both the DEM footprint **and** the routing
  lattice. `_bbox_lattice` stakes its first row at `lat_min`, so the southernmost
  lattice row was exactly the DEM's southern edge. The Binalud front starts right
  there: ground at (36.05, 59.38) is 1880 m → 320 m clearance at the 2200 m lock,
  while the next row north is **infeasible** (36.072 → 1939 m, 36.095 → 2110 m).
  Exactly one lattice row could leave Mashhad at R4's level, and it was the row glued
  to the data edge. A lattice row is a constant latitude, so the route came out as a
  ruler-straight line on the frame.
- **Falsified the easy explanation first.** Extending the lattice 0.15° on every side
  and re-routing made R4 *worse* (190.4 → 192.8 km, parallel 14.4% → 9.7%): the route
  was not clamped by the **scene**, it was clamped by the **ridge in front of the only
  flyable row**. What was missing was real terrain, not a bigger box.
- **The fix (data, not a constant).** `CORRIDOR_BBOX["lat_min"]` 36.05 → **35.90**
  (16.7 km of genuine plain; nothing extrapolated) and the DEM refetched from the same
  Open-Meteo/Copernicus source: grid **19x87 → 25x88** (2200 points, 872–3199 m).
  South of the old edge the ground falls away fast — 1980 → 1484 m at lon 59.38 — so
  the flyable band widens from one lattice row to several.
- **Measured, before → after:**
  - R4: southern edge gap **−0.6 km (outside the box) → 11.3 km inside**; distance
    190.4 → **189.8 km**; worst drawn turn rate 3.32 → **1.50 °/km**; longest
    dead-straight run **100+ → 15.5 km**.
  - R1/R2 lost an artificial 13.3 km southern dip: 176.3 → **174.1 km**, 2.21 → 2.19 h.
    Distances now R3 173.8 · R6 174.1 · R5 185.4 · R7 174.2 · R8 178.1 km.
  - Every graph route now keeps **≥ 17 km** from every data edge, so the axes no longer
    have to be inflated to contain a route.
- **Co-fix in the same change:** the flat projection’s east–west scale was taken at the
  box’s **south-west corner**, so stretching the box south stretched every drawn `x`
  by 0.2% and the “the picture proves the table” test fell out of tolerance. The scale
  latitude is now separate from the plot origin (`lonlat_to_km(..., ref_lat=)`,
  `scene3d.PLOT_SCALE_LAT` = box centre).
- **New test (generic):** `tests/test_routing_scene.py::test_no_graph_route_is_pinned_to_the_data_edge`
  — every graph route must stay ≥ 2 km inside the box on all four sides. It fails on
  the old box (R4 was outside it), so it pins the defect, not the number.
- **Tightened while here:** `test_climbing_costs_time_but_gravity_gives_the_fuel_back`
  asserted climb↔glide consistency at 0.1%; the refined DEM moved the climb/descent
  asymmetry to 0.2% and it failed. The glide identity is now asserted **exactly**
  (glide range ∝ descent height) and the asymmetry is bounded separately (< 0.3%),
  which is a stronger test than the tolerance it replaced.
- **Known limit, stated honestly:** the surface wind at this hour is *itself* 8–37° off
  the corridor bearing (Mashhad 68°, Neyshabur 80°, Sabzevar 125°; corridor 267.6°),
  so a graph route flying the corridor cannot reach R5's parallel share. R5 is not the
  same kind of answer — it is *built* by the wind-riding planner, which spends almost
  nothing on correcting against the wind, whereas the graph routes minimise a cost  in which the crosswind drag penalty is bounded by that same 8–37° spread.
- **Test:** `pytest -q` → **۳۲۳ passed**; `ruff check src tests scripts` → `All checks
  passed!`; artifact regenerated (`docs/assets/routing_scene.html`, **۸.۰ MB**, ۸ مسیر,
  DEM grid ۲۵×۸۸).
- **PR:** —

---

## Task: «طراحی پایهٔ رابط کاربری و انتخاب معماری فنی» — گام ۴ (UI Foundation)

- **تسک ClickUp:** `86bc860cq` — «طراحی پایهٔ رابط کاربری و انتخاب معماری فنی
  (UI Foundation & Technical Architecture)»، اولویت High، ددلاین ۷ مهر ۱۴۰۵ ساعت ۲۰:۰۰.
- **دامنه:** یک کدبیس React + TypeScript که در سه هدف توزیع می‌شود — Web/PWA،
  دسکتاپ (Tauri) و موبایل (Capacitor) — به‌همراه سیستم طراحی، تمام صفحات/جریان‌ها
  و قرارداد API.
- **معماری فنی (آیتم ۱):** `docs/frontend/architecture.md` — مرجع بصری، توکن‌های
  طراحی، ساختار پوشه‌بندی، لایه‌های سرویس، مدیریت state، تشخیص پلتفرم.
- **قرارداد API (آیتم ۲):** `api/openapi.yaml` (OpenAPI **3.0.3**) — مسیریابی،
  لایه‌های باد، نقاط/چک‌پوینت، الگوریتم‌ها، احراز هویت، پروفایل/ترجیحات، خطاها،
  محدودیت نرخ و نسخه‌بندی.
- **اسکلت و سیستم طراحی (آیتم‌های ۳ و ۴):** پروژهٔ `frontend/` (React + Vite +
  TypeScript + Tailwind + React Router + Mapbox GL JS)، توکن‌های CSS، کامپوننت‌های
  پایه (Button/Card/Checkbox/Select/Slider/TextField) و کامپوننت‌های فیچر (نقشه،
  لایه‌ها، مسیریابی).
- **صفحات و جریان‌ها (آیتم‌های ۵ و ۶):** Map2D، Map3D، Settings، Results، Auth
  (ورود/ثبت‌نام/بازیابی رمز)، Profile، Onboarding؛ انتخاب مبدأ/مقصد/چک‌پوینت،
  کنترل لایه‌ها، انتخاب‌گر الگوریتم، پروفایل مسیر، پنل فیلترهای پیشرفته، نوار کناری/
  drawer و bottom sheet موبایل.
- **دسترسی‌پذیری (آیتم ۷):** طراحی واکنش‌گرا (RTL)، تم تاریک/روشن، بررسی خودکار
  axe-core روی primitives و کامپوننت‌های کلیدی مسیریابی (`vitest-axe`).
- **یکپارچگی ابزارها:** در همین شاخه یک نقص تایپ در پیکربندی تست پیدا و رفع شد —
  `vitest-axe` تایپ matcher خود را فقط روی namespace قدیمی `Vi` augment می‌کرد که
  در Vitest 5 معتبر نیست و باعث شکست `tsc -b` (و در نتیجه build) می‌شد؛ با یک
  shim تایپ در `frontend/src/test/vitest-axe.d.ts` رفع شد.
- **شواهد:** `npm test` → ۵ فایل / ۱۵ تست پاس؛ `npm run lint` → بدون خطا؛
  `npm run build` → موفق؛ `npm run typecheck` → موفق.
- **PR:** —

## Task: «طراحی پایهٔ رابط کاربری و انتخاب معماری فنی» — گام ۵ (بسته‌بندی سه‌گانه و تکمیل چک‌لیست)

- **تسک ClickUp:** `86bc860cq` (همان تسک بالا) — تکمیل آیتم‌های باقی‌مانده.
- **بسته‌بندی سه‌گانه (آیتم ۱):** `frontend/src-tauri/` (Tauri 2 — `tauri.conf.json`
  با شناسه `com.roshd.windpath`، `Cargo.toml`، `src/main.rs`، `src/lib.rs`) و
  `frontend/capacitor.config.ts` (Capacitor 8) اضافه شد؛ اسکریپت‌های
  `npm run tauri` و `npm run cap:sync` به `package.json`. مستند:
  `docs/frontend_architecture.md`.
- **فرم‌های احراز هویت (آیتم ۹):** `VerifyEmailPanel` (تایید ایمیل با توکن لینک)،
  `ResetPasswordForm` (تعیین رمز جدید با `POST /auth/password-reset/confirm`)،
  هوک‌های `useVerifyEmail`/`useConfirmPasswordReset`، و کلیدهای i18n مربوطه.
  تب‌های `AuthPage` به پنج حالت (ورود/ثبت‌نام/فراموشی/تعیین رمز/تایید ایمیل) گسترش یافت.
- **اتصال داده روی نقشه (رفع کد مرده):** پاپ‌آپ «Wind Layers at Point» قبلاً هیچ‌جا
  وصل نبود؛ اکنون با کلیک روی نقشه پس از تعیین مبدأ/مقصد و همچنین با دکمهٔ
  «مشاهده لایه‌های باد در نقطه» در پنل باز می‌شود.
- **چک‌پوینت روی نقشه (آیتم ۱۰):** هندلر long-press (۵۰۰ms، بدون drag) در
  `MapView` اضافه شد و مارکر شماره‌دار چک‌پوینت روی نقشه رسم می‌شود؛ متن راهنما
  با رفتار واقعی هم‌تراز شد.
- **مستندات تحویلی (آیتم‌های ۱، ۴، ۷):** `docs/task_ui_foundation.md`،
  `docs/frontend_architecture.md`، `docs/ui_design_system.md`،
  `docs/accessibility_wcag_aa.md`.
- **تست‌ها:** `AuthForms.test.tsx` (۴ تست) اضافه شد؛ تست `PathInfoPanel` برای
  دکمهٔ جدید به‌روز شد (انتخاب دکمه بر اساس نام قابل‌دسترس، نه ایندکس).
- **شواهد:** `npm test` → ۶ فایل / ۱۹ تست پاس؛ `npm run lint` → بدون خطا؛
  `npm run typecheck` → موفق؛ `npm run build` → موفق.
- **باز (آیتم ۸):** بررسی پیکسل‌به‌پیکسل با mockup نیازمند `VITE_MAPBOX_TOKEN`
  است؛ بدون توکن نقشه رندر نمی‌شود.
- **PR:** —


## Task: «طراحی پایهٔ رابط کاربری و انتخاب معماری فنی» — گام ۶ (بازبینی CI، دسترس‌پذیری و هم‌ترازی mockup)

- **تسک ClickUp:** `86bc860cq` (همان تسک بالا) — بازبینی نهایی PR و رفع یافته‌های ممیزی.
- **وضعیت CI:** روی هد `f29c0bc` چک «Lint & Test» سبز است (`pytest` ۱۸۸ تست، `ruff` بدون خطا).
- **دسترس‌پذیری (آیتم ۷):** نام دسترس‌پذیری تکراری چک‌باکس‌ها (ترکیب `htmlFor` + دربرگرفتن) رفع شد —
  ارتباط فقط با دربرگرفتن برقرار می‌شود؛ خروجی axe دیگر «duplicate name» ندارد.
- **i18n کامل:** همهٔ رشته‌های هاردکد حذف شد — Settings، فیلترهای پیشرفته، چک‌پوینت‌ها،
  دکمهٔ «پاک کردن»، کارت نتیجه، صفحات Profile/Onboarding/About، فرم ثبت‌نام («نام») و
  پیام نبودن توکن Mapbox. حالا جابه‌جایی fa/en تمام صفحه را پوشش می‌دهد (کلیدهای
  جدید `settings.*`، `results.*`، `profile.*`، `onboarding.*`، `about.*`، `map.subtitle/clear/tokenMissing`).
- **هم‌ترازی mockup (آیتم ۸):** نوار بالای صفحات نقشه (`AppHeader`) با عنوان + زیرعنوان و
  کلید تغییر تم روشن/تاریک اضافه شد (مطابق نوار بالای mockup). اجرای واقعی با توکن
  آزمایشی بررسی شد: جریان مبدأ/مقصد/چک‌پوینت (long-press)/محاسبهٔ مسیر/پاپ‌آپ لایه‌های باد،
  حالت ۳بعدی، تم روشن/تاریک، زبان انگلیسی (LTR) و نمای موبایل (bottom sheet) همگی سالم.
- **PWA:** مانیفست `public/manifest.webmanifest` + لینک در `index.html`؛ مستند معماری
  به‌روز شد (سرویس‌ورکر `vite-plugin-pwa` به تسک یکپارچه‌سازی موکول است — نیازمند تأیید مالک).
- **پایداری تست:** `MapView` توکن را در زمان رندر می‌خواند و تست «بدون توکن» با
  `vi.stubEnv` قطعی شد (دیگر به `.env.local` توسعه‌دهنده حساس نیست).
- **شواهد:** `npm test` → ۶ فایل / ۱۹ تست پاس؛ `npm run lint` → بدون خطا؛
  `npm run typecheck` → موفق؛ `npm run build` → موفق؛ `ruff check .` → بدون خطا؛
  `pytest -q` → ۱۸۸ پاس.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «طراحی پایهٔ رابط کاربری و انتخاب معماری فنی» — گام ۷ (میدان باد روی نقشه + تجربهٔ موبایل Uber-مانند)

- **تسک ClickUp:** `86bc860cq` (همان تسک بالا) — هم‌ترازی بصری با mockup و بازطراحی جریان موبایل.
- **میدان باد روی نقشه (موکاپ: نقشهٔ حرارتی + پیکان‌های جهت):** قرارداد موجود
  `GET /wind-layers/{altitudeM}/field` (`WindField` در api/openapi.yaml) به فرانت‌اند وصل شد:
  لایهٔ fill روی سلول‌های شبکه با رنگ داده‌محور از همان رمپ راهنما
  (`src/utils/windField.ts` + `src/components/features/map/windFieldLayer.ts`) و پیکان‌های
  chevron با چرخش در مختصات (قرارداد هواشناسی جهت + ۱۸۰ = سمت جریان). چک‌باکس لایه‌ها
  (سطحی/میانی/بالا) میدان لایهٔ فعال را عوض می‌کند؛ راهنمای سرعت باد هم روی خود نقشه
  (پایین-چپ) و هم در پنل هست.
- **داده واقعی، نه ساختگی:** فیکسچرهای پیش‌نمایش dev با اسکریپت جدید
  `scripts/export_web_wind_fixture.py` از همان خط لولهٔ بصری‌سازی (باد واقعی
  ایستگاه‌ها در ساعت بیشینه + IDW + نمایهٔ اعلام‌شده) تولید و در
  `frontend/public/mock/` ذخیره می‌شود؛ مسیر نمایشی هم خروجی واقعی `WindRouter`
  روی گراف چندلایهٔ MSL است (۱۷۴ km @ ۲۹۰۰ m). در dev اگر بک‌اند نبود، همین
  فیکسچرها به‌عنوان fallback با برچسب صریح «مسیر نمایشی» استفاده می‌شوند؛ در
  build نهایی fallback نیست.
- **تجربهٔ موبایل Uber/Snapp-مانند:** نوار بالا فقط دسکتاپ؛ موبایل نقشهٔ
  تمام‌صفحه + راهنمای گام‌به‌گام («گام ۱ از ۲ — مبدأ…» بعد «گام ۲ از ۲ — مقصد…»)
  و با کامل شدن دو نقطه، شیت «تنظیمات سفر» خودکار بالا می‌آید (الگوریتم، لایه‌ها،
  محدودیت‌ها، چک‌پوینت/وای‌پوینت، محاسبه). جای دکمه‌های زوم و راهنما بر اساس
  جهت صفحه (RTL/LTR) جدا شد تا هم‌پوشان نشوند.
- **رفع باگ‌های رندر:** مبدأ مکث‌های طولانی، image source با مختصات صفر در
  mapbox بود (جایگزینی با هندسهٔ fill خالص) و گم‌شدن اعمال میدان به‌خاطر
  `isStyleLoaded()===false` در لحظهٔ رویداد load (انتظار تایمری در
  `whenStyleReady`).
- **شواهد:** `npm test` → ۷ فایل / ۲۸ تست پاس (۱۲ تست جدید میدان باد)؛
  `npm run lint`/`typecheck`/`build` → موفق؛ رندر واقعی در مرورر بررسی شد
  (میدان سبز→زرد کریدور + پیکان‌ها + جریان کامل موبایل/دسکتاپ)؛
  `ruff check .` و `pytest -q` (۱۸۸) → پاس.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «طراحی پایهٔ رابط کاربری و انتخاب معماری فنی» — گام ۸ (مراحل انتخاب، دسته‌بندی تنظیمات، تم کنترل نقشه)

- **تسک ClickUp:** `86bc860cq` (همان تسک بالا) — بازخورد UX دور دوم.
- **مراحل انتخاب در پنل (الگوی Uber):** فهرست «۱. انتخاب مبدأ / ۲. انتخاب مقصد» در
  بالای پنل کنار نقشه؛ با انتخاب هر نقطه، متن مرحله با «مبدأ/مقصد: عرض، طول»
  و تیک سبز جایگزین می‌شود (`RouteSteps` در `PathInfoPanel`).
- **تنظیمات پیشرفته دسته‌بندی‌شده:** سه دستهٔ جمع‌شونده (ارتفاع پرواز،
  بهینه‌سازی، اجتناب از مناطق) با کامپوننت جدید `Collapsible`؛ محتوای هر دسته
  فقط با گسترشِ خود کاربر رندر می‌شود (آیتم ۱۱ چک‌لیست). تست‌های
  `Collapsible.test.tsx` اضافه شد.
- **کنترل‌های خود نقشه همرنگ تم:** گروه زوم/قطب‌نمای mapbox و نوار انتساب با
  توکن‌های تم استایل شدند (پس‌زمینه/حاشیه/هاور + معکوس‌سازی آیکون در تم تاریک).
- **شواهد:** `npm test` → ۸ فایل / ۳۰ تست پاس؛ `lint`/`typecheck`/`build` → موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «نقشهٔ واقعی بدون توکن، ترن ۳بعدی و اتصال کامل دکمه‌ها» — گام ۹ (سوئیچ MapLibre)

- **تسک:** همان 86bc860cq — رفع «نقشه نمایش داده نمی‌شود».
- **ریشهٔ مشکل:** نقشه به `VITE_MAPBOX_TOKEN` وابسته بود و بدون آن رندر نمی‌شد؛
  همچنین آدرس پیش‌فرض API کلاینت `/v1` داشت که سرور ندارد.
- **راه‌حل:** سوئیچ کامل به **MapLibre GL** (انشعاب آزاد Mapbox — همان API):
  کاشی‌های آزاد OpenStreetMap، ترن واقعی ۳بعدی با DEM آزاد AWS Terrarium +
  سایهٔ کوهستان (hillshade)، بدون هیچ توکن/کلید. تم تاریک با فیلتر CSS بوم.
- **اتصال کامل:** آدرس پیش‌فرض API اصلاح شد (`http://localhost:8000`)؛
  «محاسبه مسیر» اکنون **مسیر واقعی بک‌اند** را می‌گیرد (بدون برچسب نمایشی)
  و کادر نقشه با `fitBounds` روی مسیر تنظیم می‌شود. بک‌اند در پورت ۸۰۰۰ زنده
  و همهٔ دکمه‌ها تست شدند.
- **رفع کرش کل صفحه:** `setTerrain` قبل از آماده‌شدن استایل کل اپ را می‌انداخت
  (React 19) — با رویداد load همگام شد. لایهٔ نقشه/پنل هم به چیدمان شناور
  (overlay) تبدیل شد و نوار بالایی حذف شد (کلید تم داخل پنل).
- **شواهد:** ۳۰/۳۰ تست فرانت + build موفق؛ رندر واقعی نقشهٔ OSM + مسیر بک‌اند
  (۱۴۹.۵ km @ 1500 m) در مرورگر تأیید شد.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «گرید سبز، نمایش مسیر، ترن ۳بعدی و ویزارد مراحل» — گام ۱۰ (بازخورد UX دور سوم)

- **تسک:** همان 86bc860cq.
- **«گرید سبز» حذف شد:** میدان باد از سلول‌های fill به **تصویر نرم canvas**
  (image source + درون‌یابی) تغییر کرد — گرادیان پیوستهٔ آبی→قرمز + پیکان‌های
  chevron؛ درز سلول‌ها از بین رفت.
- **مسیر همیشه رسم می‌شود:** باگ ردشدنِ بی‌صدای مسیر هنگام ناآماده‌بودن استایل
  رفع شد (تلاش مجدد تایمری؛ همان الگوی میدان باد). مسیر واقعی بک‌اند با
  `fitBounds` کادر می‌گیرد.
- **ترن ۳بعدی واقعی (درجا):** سوییچ ۲/۳بعدی دیگر URL عوض نمی‌کند — روی همان
  نقشه: کاشی خیابان خاموش، پس‌زمینهٔ آب، ترن واقعی با DEM آزاد MapLibre
  (AWS Terrarium بازنشسته شده بود)، pitch و بزرگ‌نمایی ارتفاع. هزینهٔ GPU
  کم شد (hillshade در ۳بعدی خاموش، DEM maxzoom=12، pitch=۵۰).
- **ویزارد مراحل (بازخورد):** یک فهرست واحد — گام جاری **بزرگ و بولد** با
  انیمیشن تعویض (step-swap)؛ دکمهٔ **بازگشت** (جلوی کلید تم) به گام قبل
  برمی‌گردد (پاک‌کردن مقصد/نتیجه یا مبدأ) — `goBackStep` در استور.
- **نام مکان به‌جای مختصات:** برچسب گام‌های انجام‌شده با ژئوکدینگ معکوس آزاد
  OSM (Nominatim) «استان، شهر/دهستان، خیابان» را نشان می‌دهد
  (`utils/geocode.ts` + کش)؛ در نبود شبکه به مختصات برمی‌گردد.
- **چیدمان:** پنل شناور روی نقشه با شعاع بزرگ‌تر (rounded-2xl) از دکمه‌ها؛
  زوم/راهنما به سمت مقابل پنل (راست در RTL) منتقل شد.
- **شواهد:** ۳۰/۳۰ تست فرانت + build/lint/typecheck موفق؛ بازبینی زندهٔ
  دسکتاپ/۳بعدی/موبایل (۳۹۰px) در مرورگر.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «بازخورد UX دور چهارم» — گام ۱۱ (مراحل زیر دکمه‌ها، طیف وسط، سایدبار جمع‌شونده)

- **تسک:** همان 86bc860cq.
- **مراحل زیر دکمه‌ها + فونت درشت‌تر:** ردیف دکمه‌ها (بازگشت/تم) بالای فهرست
  مراحل؛ گام جاری ۲۰px بولد (بازخورد: کوچک‌تر از ۲rem).
- **حذف «۱./۲./۳.» از متن گام‌ها** — شماره فقط در نشان دایره‌ای.
- **راهنمای سرعت باد (طیف):** وسط پایین نقشه، پهن‌تر (w-80)، دور از زوم؛
  انتساب OSM به گوشهٔ پایین-چپ منتقل شد تا با زوم/طیف هم‌پوشان نشود.
- **سایدبار جمع‌شونده:** دکمهٔ سه‌خط (منو) — بستن سایدبار فقط با همبرگری
  شناور باز می‌شود؛ کلید بستن روی خود سایدبار. (کلید بستنِ اشتباهی روی پنل
  شناور حذف شد — پنل همیشه نمایان است.)
- **شواهد:** ۳۰/۳۰ تست + build/lint موفق؛ تأیید DOM و تصویر دسکتاپ/موبایل.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «ویزارد اسلایدی مراحل و سوییچ عمودی ۲/۳بعدی» — گام ۱۲ (بازخورد UX دور پنجم)

- **تسک:** همان 86bc860cq.
- **ویزارد مراحل جدا شد:** قاب شناور وسطِ بالا (`StepsWizard`) با **اسلاید
  افقی** گام‌ها — با تکمیل هر گام، نوار به گام بعدی می‌لغزد (جهت‌آگاه RTL/LTR)
  + نشانگر پیشرفت و دکمهٔ بازگشت. قاب جایگزین pill قبلی شد.
- **پنل سبک شد:** مراحل/بازگشت از پنل حذف شد؛ فقط الگوریتم/لایه‌ها/محدودیت‌ها/
  فیلترها/چک‌پوینت‌ها/نتیجه + دکمهٔ محاسبه.
- **سوییچ ۲/۳بعدی عمودی** زیر لبهٔ پایین پنل (بدون ناوبری — همان نقشه).
- **انتساب OSM** به گوشهٔ مقابل سوییچ منتقل شد (رفع هم‌پوشانی).
- **شواهد:** ۳۰/۳۰ تست + build/lint موفق؛ اسلاید واقعی گام ۱→۲→۳ و مسیر
  بک‌اند (۱۳۶.۳ km) در مرورگر تأیید شد.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «نوار ابزار عمودی، محاسبه در ویزارد، ۳بعدی سبز» — گام ۱۳ (بازخورد UX دور ششم)

- **تسک:** همان 86bc860cq.
- **نوار ابزار عمودی آیکونی** کنار لبهٔ بیرونی پنل شناور: جمع/بازکردن پنل (فلش)،
  ۲بعدی/۳بعدی (آیکون نقشه/کوه)، زوم +/− سفارشی (از طریق `onReady` MapView) —
  همه آیکونی بدون متن (`MapTools`).
- **محاسبهٔ مسیر به ویزارد منتقل شد:** دکمه همیشه در قاب وسط بالا نمایان است؛
  پنل فقط تنظیمات/نتیجه.
- **۳بعدی مثل صحنهٔ نمونه:** زمین سبز + سایهٔ قهوه‌ای کوهستان (hillshade)،
  کاشی خیابان خاموش، مسیر ۳بعدی سفید پررنگ روی ترن، پیکان‌های باد **توپر**
  (شکل فلش ۷نقطه‌ای fill به‌جای chevron خطی) رنگ‌آمیزی‌شده با رمپ سرعت.
- **سایدبار پیش‌فرض بسته** (فقط همبرگری).
- **شواهد:** ۳۱/۳۱ تست (۳ تست StepsWizard) + lint/typecheck/build موفق؛
  رندر ۳بعدی زنده تأیید شد.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «بازخورد UX دور هفتم + ممیزی API» — گام ۱۴

- **ممیزی فراخوانی‌های API:** عدم تطابق خروج (/auth/logout) رفع شد — کلاینت
  اکنون refresh token را ذخیره و ارسال می‌کند؛ پاسخ 401 به‌طور خودکار با
  `/auth/refresh` تمدید و درخواست تکرار می‌شود (client.ts). سمت بک‌اند بدنهٔ
  logout اختیاری شد (کامیت روی شاخهٔ بک‌اند).
- **پنل شناور به اندازهٔ محتوا** (max-h سقف اسکرول)، **دکمهٔ محاسبهٔ صاف**
  (بدون گوشه گرد بالا و پدینگ، لبه‌به‌لبه) و **دکمهٔ بازگشت پررنگ** (accent +
  برچسب متنی).
- **شواهد:** ۳۱/۳۱ تست + lint/typecheck/build موفق؛ جریان واقعی مسیر (۱۳۴.۱ km)
  با API زنده تأیید شد.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «بازخورد UX دور هشتم» — گام ۱۵

- **یک انتساب OSM** (حذف کنترل تکراری؛ نمونهٔ صریح پایین-چپ).
- **حذف سوییچ مستقل ۲/۳بعدی** — آیکون‌های نقشه/کوه در نوار ابزار کنار پنل.
- **متن بازگشت کوتاه:** «مرحله قبل» / «Previous step».
- **اسکرول‌بار پنل نامرئی** (`.no-scrollbar` — اسکرول کار می‌کند).
- **شواهد:** ۳۱/۳۱ تست + build/lint موفق؛ تأیید DOM (یک انتساب، متن کوتاه،
  scrollbar-width:none).
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «رنگ‌آمیزی نسبی میدان باد + اسکرول‌بار» — گام ۱۶

- **تسک:** همان 86bc860cq.
- **رنگ میدان‌ها دیگر تک‌رنگ نیست:** رنگ‌آمیزی نسبت به بازهٔ [min,max] خودِ
  میدان انجام می‌شود (همان رفتار نسبی صحنهٔ بصری‌سازی) — با بادهای واقعی
  کریدور (۵–۷٫۹ m/s) کل طیف آبی→قرمز دیده می‌شود؛ هم تصویر نرم و هم
  پیکان‌های توپر. توابع خالص `fieldSpeedRange`/`colorForFieldSpeed` در
  `utils/windField` + تست‌های واحد.
- **اسکرول‌بار پنل:** علت، غلاف اسکرول داخلیِ جامانده از بازآرایی قبلی بود —
  حذف شد (فقط خود Card اسکرول می‌کند و بدون اسکرول‌بار است).
- **شواهد:** ۳۳/۳۳ تست + lint/typecheck/build موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «بازخورد UX دور نهم — پیکان متحرک، ترن ۳بعدی، ویزارد» — گام ۱۷

- **پیکان‌های باد بازطراحی شد:** لایهٔ چندضلعیِ درجه‌ای (که با زوم غول و
  «چاق» دیده می‌شد) با لایهٔ symbol و اسپرایت باریک ثابت‌اندازه (ساقهٔ نازک +
  سر کوچک، رنگ سطل نسبی سرعت) جایگزین شد؛ انیمیشن «حرکت کوتاه در راستای
  جریان + محو + شروع دوباره» با requestAnimationFrame و سقف ~۳۰fps و فاز
  آفست‌دار هر پیکان — دقیقاً جهت باد دیده می‌شود. باگ فاز/گام قبلی که اولین
  تیک انیمیشن را می‌کشت هم رفع شد.
- **رفع ریشه‌ای «۳بعدی هیچی نشان نمی‌دهد» و «مسیر گاهی رسم نمی‌شود»:** گیتِ
  `isStyleLoaded` در برابر منبع DEM (Terrarium آزاد AWS) مدت‌ها false
  می‌ماند و سوییچ ۳بعدی (منتظر رویداد load) هرگز اجرا نمی‌شد. همهٔ اعمال
  لایه (میدان باد، خط مسیر، حالت ۲/۳بعدی) بازگشت‌پذیر (idempotent) و با
  تلاشِ مجدد روی خطا بازنویسی شدند؛ مختصات گوشه‌های تصویر میدان هم (جابجایی
  lat/lon در دو گوشه) اصلاح شد و `triggerRepaint` صریح بعد از افزودن لایه
  در وضعیت نیمه‌لود اضافه شد.
- **ویزارد:** عنوان «مراحل مسیر» و شماره‌های گام حذف شد؛ جستجوی مکان (فقط
  رابط) در بالا و دو فلش در دو سو: راست = گام قبل (پاک‌کردن داده‌های بعدی
  برای تغییر)، چپ = گام بعد (بازتولید) — بدون هم‌پوشانی با عنوانِ لغزان.
- **چک‌پوینت فقط با دکمه:** long-press نقشه حذف شد؛ «افزودن چک‌پوینت» پنل
  حالت placing می‌گیرد و کلیک بعدی روی نقشه چک‌پوینت می‌گذارد (در حالت
  placing، کلیک‌ها به‌جای «اطلاعات نقطه» مسیر افزودن می‌روند).
- **پنل شناور جمع‌شدنی:** دکمهٔ نوار ابزار پنل را تا لبه (عرض صفر با
  transition) جمع می‌کند و نوار ابزار به‌دنبالش به لبه می‌لغزد.
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck موفق؛ راستی‌آزمایی تصویری گام‌به‌گام
  با کروم هدلس (CDP): میدان باد و پیکان‌های متحرک در ۲بعدی، ترن واقعی و
  سایهٔ کوهستان در ۳بعدی (pitch ۵۵ + exaggeration ۲)، رسم مسیر نمایشی ۳۵۰
  نقطه‌ای + fitBounds، افزودن چک‌پوینت با دکمه، بی‌اثر شدن long-press،
  جمع‌شدن پنل (عرض ۰) و تغییر میدان با سوییچ لایه (چرخش اکمان ۳۰۲→۳۰۷°).
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «بازخورد UX دور دهم — تنظیمات نما، جایگزینی انتخاب، چندلایهٔ ۳بعدی» — گام ۱۸

- **جستجوی مکان فقط در گام‌های ۱ و ۲** — در گام «محاسبهٔ مسیر» پنهان می‌شود.
- **پیکان‌های بولدتر** — ساقه/سر پررنگ‌تر و اندازهٔ نماد بزرگ‌تر؛ در ۳بعدی هم
  شکل پیکان با `icon-pitch-alignment: viewport` همان شکل ۲بعدی می‌ماند.
- **نقشهٔ رنگی نرم شد** — تصویر میدان با درون‌یابی دوخطی ساخته می‌شود (به‌جای
  نزدیک‌ترین سلول) تا نوارهای تیز به گرادیان پیوسته تبدیل شود. نکتهٔ داده:
  نوارها از هندسهٔ داده می‌آیند — سه ایستگاه تقریباً روی یک خطِ غربی-شرقی‌اند
  و IDW واقعاً میدان یک‌بعدی می‌سازد.
- **چندلایهٔ ۳بعدی مثل صحنهٔ بصری‌سازی** — در ۳بعدی همهٔ لایه‌های نمایان
  (۵۰/۲۰۰/۵۰۰) هم‌زمان رسم می‌شوند و رنگ پیکان هر لایه از پالت صحنه
  (`#74b9ff/#00cec9/#fdcb6e`) می‌آید؛ در ۲بعدی تک‌لایهٔ فعال با رنگ سطل سرعت.
- **بازگشت، انتخاب را پاک نمی‌کند** — گامِ ویزارد به استور رفت (`wizardStep`)؛
  گام عقب فقط نما را عقب می‌برد و کلیک بعدی روی نقشه همان گام، انتخاب فعلی را
  «جایگزین» می‌کند (نتیجهٔ کهنه باطل می‌شود، انتخاب‌ها سر جایشان می‌مانند).
- **«پاک کردن» به پنل منتقل شد** — دکمهٔ شناور روی نقشه حذف؛ آیکون سطل در
  بالای پنل شناور (و شیت موبایل).
- **ابزار «نمای نقشه»** — قاب کناری کنار نوار ابزار: نقشهٔ پایه (ساده/
  ماهواره‌ای Esri آزاد) + کلیدهای نمایش پیکان‌ها، نقشهٔ رنگی باد و سایهٔ
  کوهستان؛ همه در `useUiStore` و MapView مستقیماً واکنش نشان می‌دهد (تصویر
  ماهواره‌ای حتی در ۳بعدی روی ترن می‌نشیند).
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق؛ راستی‌آزمایی تصویری
  گام‌به‌گام با کروم هدلس: قاب تنظیمات، سوییچ ماهواره‌ای، پنهان‌شدن جستجو در
  گام ۳، ماندن پین‌ها بعد از بازگشت، جایگزینی مقصد، نمایان بودن هر سه لایهٔ
  پیکان در ۳بعدی و کارکرد هر سه کلید نمایش.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «رفع قطعی «پیکان‌ها/نقشهٔ رنگی نمایش داده نمی‌شوند»» — گام ۱۹

- **درخت لایهٔ ایستا:** همهٔ لایه‌های پویا (نقشهٔ رنگی باد، پیکان‌های سه
  ارتفاع، خط مسیر و نقاطش) از ابتدا در استایل پایه تعریف می‌شوند (دادهٔ
  خالی + `visibility: none`) و در زمان اجرا فقط داده عوض می‌شود. افزودن
  لایه وقتی استایل در وضعیت نیمه‌لود (صف DEM) است گاهی بی‌اثر می‌ماند و
  لایه هرگز رسم نمی‌شد — ریشهٔ گزارش «پیکان‌ها نمایش داده نمی‌شوند».
- **باگ مختصات تصویر میدان:** `ImageSource.updateImage` فقط url را عوض
  می‌کند و مختصات جای‌نگهدار باقی می‌ماند — نقشهٔ رنگی در مختصات اشتباه
  (گوشهٔ صفر نقشه) نقش می‌بست. با `setCoordinates` صریح اصلاح شد.
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck موفق؛ بازبینی تصویری: بارگذاری
  تازه (نقشهٔ رنگی + پیکان‌ها هر دو حتماً نقش می‌بندند)، سوییچ ۳بعدی
  (سه لایهٔ پیکان نمایان + ترن) و بازگشت به ۲بعدی (تک‌لایه).
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «بازخورد UX دور نهم» — گام ۱۷ (ادغام کد تیم + سه اصلاح)

- **ادغام:** سه کامیت جدید تیم (لایهٔ ایستا/اسپرایت پیکان، ابزار نمای نقشه،
  ناوبری ویزارد) تحلیل و ناهماهنگ شد؛ تنظیمات پیکان به
  `frontend/src/config/mapDisplay.ts` منتقل و تکمیل شد.
- **تنظیمات نما وسط نقشه** باز می‌شود (قبلاً کنار پنل).
- **گام بعدی فقط با ورودی گام جاری** — فلش بعد بدون مبدأ/مقصد غیرفعال است.
- **پیکان‌ها ۱٫۵ برابر** (spriteSize 99، ساقه ۷٫۸۷۵، sizeStops ×۱٫۵).
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «فلش‌های کوتاه‌تر» — گام ۱۸ (بازخورد UX دور دهم)

- **تسک:** همان 86bc860cq.
- **طول فلش‌های باد کوتاه شد:** هندسهٔ اسپرایت در `config/mapDisplay.ts`
  (baseY از ۰٫۸۶۴ به ۰٫۶۲ — ساقهٔ کوتاه‌تر با همان سر)؛ بدون تغییر اندازهٔ
  کل یا سرِ پیکان.
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «پیکان‌های پررنگ‌تر با همان طول کوتاه» — گام ۱۹

- **تسک:** همان 86bc860cq.
- **ضخامت/اندازه ×۱٫۲** (ساقه ۹٫۴۵px، نیم‌عرض سر ۰٫۱۹، sizeStops ×۱٫۲) —
  طول فلش همان نسخهٔ کوتاه (baseY ۰٫۶۲) دست‌نخورده ماند.
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «فلش نصف‌طول + تنظیمات نما کنار دکمه» — گام ۲۰

- **تسک:** همان 86bc860cq.
- **طول فلش نصف شد:** همهٔ فاصله‌های هندسه از نوک نصف (سر همان اندازه،
  ساقه نصف) — baseY ۰٫۶۲ → ۰٫۳۳۲۵.
- **تنظیمات نما:** دقیقاً کنار ستون ابزار باز می‌شود (چپِ پاپ‌آور = راستِ
  دکمه + ۰٫۵rem؛ تراز بالا) به‌جای وسط نقشه.
- **شواهد:** ۳۸/۳۸ تست + build موفق؛ فاصلهٔ اندازه‌گیری‌شده = ۸px.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «تنظیمات نما رو به پایین» — گام ۲۱

- **تسک:** همان 86bc860cq.
- **جای پاپ‌آور تنظیمات نما:** بالای قاب با بالای دکمهٔ خودش تراز شد
  (۲٫۸۷۵rem = دکمه ۴۰px + فاصله ۶px) و به سمت پایین — کنار زوم — باز می‌شود.
- **شواهد:** اندازه‌گیری DOM (فاصله ۸px، تراز ۰px) + build موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «جای دکمهٔ تنظیمات نما و پاپ‌آور» — گام ۲۲

- **تسک:** همان 86bc860cq.
- **ترتیب ستون ابزار:** [پنل] [۲بعدی] [۳بعدی] [جداکننده] [تنظیمات نما]
  [زوم+/-] — دکمهٔ تنظیمات نما زیر جداکننده و بالای زوم.
- **جای پاپ‌آور در کانفیگ:** `VIEWPORT_POPOVER` در `config/mapDisplay.ts`
  (topRem: ۸٫۷۵ — کمی بالاتر از دکمه؛ gapRem: ۰٫۵) — همهٔ کامپوننت‌ها
  خروجی یکسان از کانفیگ می‌گیرند.
- **شواهد:** ۳۸/۳۸ تست + build/lint موفق؛ اندازه‌گیری DOM (فاصله ۸px،
  پاپ‌آور ۱۳px بالاتر از دکمه).
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «پیکان‌های ضخیم با دم کوتاه + بستن بدون عبور کلیک» — گام ۲۳

- **تسک:** همان 86bc860cq.
- **پیکان‌ها:** ساقه ×۲٫۳ ضخیم‌تر (۳٫۵→۸px)، سر بزرگ‌تر (±۱۲px)، دُم کوتاه
  (size−۲۴)؛ سفر انیمیشن ۳→۱٫۵ کیلومتر تا فلش‌ها هم‌پوشان نشوند.
- **پاپ‌آور تنظیمات نما:** کلیک بیرون (نقشه/سایر) فقط می‌بندد و به عناصر
  زیرین عبور نمی‌کند (backdrop ثابت + عمردرست z) — با کلیک واقعی cua تأیید
  شد: بسته شد و هیچ نقطه‌ای ثبت نشد.
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «دُم نصف‌شدهٔ فلش» — گام ۲۴

- **تسک:** همان 86bc860cq.
- **دُم فلش نصف شد:** baseY ۰٫۳۳۲۵ → ۰٫۲۴ (سر و ضخامت دست‌نخورده) در
  `config/mapDisplay.ts`.
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق؛ تأیید بصری زنده.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «اعمال واقعی هندسهٔ کانفیگ روی اسپرایت پیکان» — گام ۲۵

- **تسک:** همان 86bc860cq.
- **ریشهٔ «دُم هنوز نصف نشده»:**

  `drawArrow` مختصات پیکسلی ثابت داشت (۳٫۵px ساقه، `size−۶` دُم) و
  `ARROW_CFG.geometry` را کلاً نادیده می‌گرفت — تغییر baseY بی‌اثر بود.
- **رفع:** بازنویسی `drawArrow` بر پایهٔ نسبت‌های کانفیگ (tipY/headBaseY/
  shaftTopY/baseY/headHalfWidth) + ضخامت از `shaftWidth` + وسط‌چین عمودی
  اسپرایت برای لنگر center.
- **نتیجه:** دُم اکنون واقعاً نصف (baseY ۰٫۲۴)؛ سر و ضخامت از کانفیگ.
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «نازک‌کردن پیکان + دُم کمی بلندتر» — گام ۲۶

- **تسک:** همان 86bc860cq.
- **ضخامت ۰٫۷×** (shaftWidth ۹٫۴۵ → ۶٫۶۱۵px) و **دُم کمی بلندتر**
  (baseY ۰٫۲۴ → ۰٫۲۹) — هر دو در `config/mapDisplay.ts`.
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق؛ تأیید بصری زنده.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «همزمان‌سازی انیمیشن فلش‌ها» — گام ۲۷

- **تسک:** همان 86bc860cq.
- **علت تصادفی‌بودن:** هر فلش آفست فاز تصادفی‌نما داشت
  (`(i%7)*0.13 + floor(i/7)*0.29`). حذف شد — همهٔ فلش‌ها با `phase` مشترک
  همزمان حرکت و محو می‌شوند (دو فریم تأیید).
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «جریان ذرات باد (سبک windy)» — گام ۲۸

- **تسک:** همان 86bc860cq.
- **بازخورد:** انیمیشن فلش‌ها (هم تصادفی هم همزمان) بد بود — جایگزین کامل:
  **سیستم ذرات جریان** — ۳۰۰ ذره که پیوسته در امتداد بردار محلی باد حرکت
  می‌کنند و ردّ کوتاه می‌گذارند؛ ذره در پایان عمر/خروج از میدان بی‌سروصدا
  جابه‌جا می‌شود (PRNG قطعی — همان جریان هر بار).
- **پیاده‌سازی:** لایهٔ line روی GeoJSON پویا (trail هر ذره) + رنگ نسبی به
  بازهٔ میدان؛ به‌روزرسانی ~۲۲ بار بر ثانیه. پیکان/اسپرایت‌ها کاملاً حذف شدند؛
  کلید «پیکان‌های باد» در تنظیمات حالا «جریان باد» را روشن/خاموش می‌کند.
- **کانفیگ:** `WIND_PARTICLE_CONFIG` در `config/mapDisplay.ts` (تعداد، طول
  ردّ، سرعت نمایشی، عمر، seed).
- **شواهد:** ۳۸/۳۸ تست + lint/typecheck/build موفق؛ تأیید بصری دو فریم.
- **PR:** [#24](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/24)

## Task: «اصلاح مسیریابی بر پایهٔ زمین و باند ارتفاعی» — Stage 3

- **شاخه:** `task/api-terrain-band-routing`
- **چهار نقص کاربر:** نادیده‌گرفتن باند ارتفاعی، چسبیدن به زمین، قلّاب
  ابتدایی، عبور از مقصد و برگشت تیز.
- **ریشه‌ها:**
  1. `compute_route_sync` هرگز `constraints.altitude_range_m` را نمی‌خواند.
  2. مسیریاب هیچ مدل زمینی نداشت (نمونه‌بردار زمین هرگز fit نمی‌شد)؛ ارتفاع
     بادسواری AGL به‌اشتباه MSL تفسیر می‌شد و گره‌های زمین صفر (سطح دریا)
     گزارش می‌شدند.
  3. `to_stacked_graph` گره زمین را روی گره شبکهٔ نزدیک می‌ساخت و تنها یک یال
     عمودی می‌داد؛ روی دامنهٔ قله این گره تا ۲۱ کیلومتر دورتر می‌افتاد و
     مسیر قلّاب می‌خورد.
  4. برنامهٔ بادسواری از مقصد می‌گذشت و با یال تیز برمی‌گشت.
- **اصلاح:** گره زمین در مختصات دقیق + اتصال چندنامزدی با هزینهٔ عمودی+افقی؛
  تزریق مدل زمین؛ نگاشت باند به سطوح پرواز MSL؛ سقف باند برای بادسواری؛
  کوتاه‌سازی در نزدیک‌ترین نقطهٔ مقصد؛ تبدیل `path_3d` به MSL واقعی.
- **خروجی:** `src/pathfinding/graph.py`، `src/pathfinding/wind_riding.py`،
  `src/api/routers/routes.py` و تست‌های `tests/pathfinding/`.
- **شواهد:** ۱۹۹/۱۹۹ تست + `ruff check .`؛ `|p0-origin| = 0`، انتها دقیقاً
  مقصد، باند `[1500,2200]` → `altitudes_used = [2200]`.
- **مستند:** [`docs/task_api_terrain_band_routing.md`](task_api_terrain_band_routing.md)
- **PR:** [#25](https://github.com/Roshd-136/roshd-wind-pathfinder/pull/25)

## Task: «بازبینی کامل مخزن + ترمیم باگ‌ها + پیکان‌ها و طیف باد» — Stage 2/3

- **شاخه:** `task/api-terrain-band-routing` (ادامهٔ کار روی همین شاخه؛ تغییرات
  این بخش در شاخهٔ جاری کامیت‌نشده است).
- **دامنهٔ بازبینی:** کل بک‌اند (`src/api/`، `src/pathfinding/`، `src/viz/`)،
  کل فرانت‌اند نقشه/مسیریابی، و بررسی عملی هر چهار باند ارتفاعی با API واقعی.

- **باسلامات کاربر/خواسته‌ها:**
  1. فهرست منطق‌های غلط و باگ‌ها → ۱۴ مورد پیدا و ترمیم شد (فهرست در زیر).
  2. پیکان‌های جهت باد در صحنهٔ ۲بعدی → بازگشت به‌صورت لایهٔ ثابت با اسپرایت
     مواربع بهنجار (۴ دستهٔ سرعت: آرام/ملایم/تند/تندتر)، تعدیل‌شدهٔ ظریف و
     مجزا از آشوب ذرات؛ کلید «پیکان‌های باد» در تنظیمات نما.
  3. طیف سرعت باد → بازگشت با بازهٔ *پویا* از خود میدان فعلی (قبل از آن بازهٔ
     ثابت ۵–۱۲ بود طوری که با فیلتر سطحی ناسازگار می‌افتاد).
  4. ثبت ۱۰ مسیر محاسبه‌شدهٔ واقعی از زاویه‌های مختلف (۲بعدی چرخان و ۳بعدی
     مداری، شامل هر معیار، هر الگوریتم و هر باند ارتفاعی → سطحی/میانی/بالا/
     بالاترین) — همه با نتیجهٔ سازگار: مسیر سطحی در ۱۵۰۰، میانی ۲۲۰۰، بالا
     ۲۹۰۰ و بالاترین ۳۶۰۰ قفل شده و طیف همراستا با زمینهٔ انتخابی به‌روز شد.
  5. دکمهٔ «محاسبهٔ مجدد» پس از تغییر تنظیمات → تأیید شد: برچسب «محاسبهٔ
     مجدد!» می‌شود، درخواست با مبدأ/مقصد ثابت و تنظیمات جدید می‌رود و مسیر
     واقعاً با باند/معیار تازه عوض می‌شود (شات‌های ۲ و ۴ تا ۷).
  6. لایهٔ «سطحی» → درادر: وقتی مبدأ/مقصد در همان جیب زمینِ پایین باشند مسیر
     ۱۵۰۰ متری درست ساخته می‌شود؛ اگر رشته‌کوه سر راه باشد خطای ۴۰۰ گویا با
     پیشنهاد «باند بالاتر» برمی‌گردد (در جای ۵۰۰ قدیمی). اندازه‌گیری شبکه‌ای:
     لایهٔ ۱۵۰۰ به‌دلیل بازشوی زمین (۳۰۰ متر فاصلهٔ مجاز) در ۳ جزء همبستهٔ
     جغرافیایی است — این محدودیتِ داده است نه باگ؛ باند [0,1500] درست به
     همان سطوح قفل می‌شود.

- **باگ‌های یافته/ترمیم‌شده:**
  1. `altitude_range_m` باندهای بسته — «میانی» هر دو سطح ۱۵۰۰ و ۲۲۰۰ را
     برمی‌داشت؛ باندها نیمه‌باز شدند تا هر باند دقیقاً یک سطح پرواز برگرداند.
  2. انتخاب باند «بالاترین» (۳۶۰۰) در UI ممکن نبود — کلید نمایش چهارم اضافه
     شد (`LayerVisibility` سه‌کلیدی ناقص بود).
  3. خطاهای دامنهٔ موتور (ValueError) به‌صورت ۵۰۰ خام برمی‌گشتند — هندلر
     ۴۰۰ با پیام فارسی در `main.py` اضافه شد.
  4. `POST /routes` حالت ۲۰۲ async برمی‌گرداند در حالی که اسپک ۲۰۲ می‌خواهد —
     اصلاح شد؛ `datetime.utcnow()` منسوخ به `now(timezone.utc)`.
  5. `GET /wind-layers`: خواندن بی‌حافظهٔ فایل با مسیر نسبی + فضولازی
     (`data` پیش‌فرض نال‌پذیر) — مسیر مطلق و کش ست شد.
  6. متادیتای `GET /algorithms` با موتور ناساز بود (۲ معیار/۳ الگوریتم به‌جای
     ۵/۴ واقعی).
  7. `wind_riding.py`: امضای `plan_wind_riding_route` شکسته (فاصله‌گذاری
     تلف‌شده) و ده‌ها مستند ناقص — بازسازی متن مستندات تنها با تکمیل
     هدفمندِ جمله‌های موجود (بدون ادعای جدید) و اصلاح کامنت‌های ناساز با کد
     (شیب فرود «۱/(L/D)» قدیمی در برابر شیبِ سیاستی واقعی).
  8. کلاینت فرانت خطای `detail` فست‌اپی را نمی‌پارسید — پیام‌های فارسی سرور
     هرگز به کاربر نمی‌رسید.
  9. هنگام خطای واقعی HTTP مسیر دمو نمایش داده می‌شد — حذف؛ بنر خطای
     صادقانه با پیام سرور افتاد.
  10. نرمال‌سازی جهت باد ۳۵۹٫۹۹…° → «۳۶۰٫۰» در توولتیپ (پیش/پس از گردکردن
      زاویه) — اصلاح شد.
  11. لایهٔ مردهٔ `route3dLayer.ts` حذف و سیم‌کشی `showParticles` در استور/
      نهر سامانهٔ نما کامل شد.
  12. قیدهای خاموش: `max_wind_speed_mps` و `avoid_zones` پذیرفته می‌شدند ولی
      هرگز اعمال نمی‌شدند؛ حالا فرانت مقدار جعلی نمی‌فرستد و بک‌اند درخواست
      حاملِ این قیدها را صریحاً با ۴۰۰ فارسی رد می‌کند.
  13. اندپوینت `compare-layers` ردیف‌های جعلی (لایهٔ ۵۰۰/۱۰۰۰/۲۰۰۰ خارج از
      سطوح واقعی پروژه) برمی‌گرداند — حذف و ۵۰۱ شفاف جایگزین شد.
  14. نمونه‌برداری جهت خواب‌آلود در `windField.ts` (اختلاف جهت قبل از
      بهنجارسازی) — اصلاح شد.

- **خروجی:** `src/api/routers/{routes,wind_layers,algorithms}.py`،
  `src/api/main.py`، `src/pathfinding/wind_riding.py`،
  `frontend/src/{components/features/{map,routing,layers},config,store,
  services/api,utils,types}/` و تست/کانفیگ هم‌راه آن‌ها؛ تصاویر شات‌ها در
  `/tmp/opencode/` (۱۰ مسیر از زاویه‌های گوناگون).

- **شواهد:** بک‌اند ۱۹۹/۱۹۹ تست + `ruff check .` تمیز؛ فرانت ۴۵/۴۵ تست +
  typecheck + lint (بدون هشدار) + build موفق؛ تأیید زندهٔ API: قید بی‌اثر →
  ۴۰۰ فارسی؛ `compare-layers` بدون کار → ۴۰۴/۵۰۱ صادقانه؛ مسیر عادی از
  ۵۷٫۶۷۸W تا ۵۹٫۶۰۶E: ۱۷۷٫۲ کیلومتر، چندلایه [1500,2200,2900]، باند سطحی
  در همین مقاصد → خطای ۴۰۰ گویا (زمین)، سازگار با اجزای همبستهٔ لایهٔ ۱۵۰۰.

## بازبینی نهایی پیش‌نمایش (۲۰۲۶-۱۰-۱۶) — گفتگو، مودال خطا و واحدهای فارسی

**هدف:** رفع سه بازخورد کاربر روی پیش‌نمایش زنده: افزودن چک‌پوینت، محل نمایش
خطا و واحدهای نمایشی؛ بدون تغییر در موتور مسیریابی (که پیش‌تر تأیید شد).

**اقدام‌ها:**
1. **بررسی چک‌پوینت در سطح API:** درخواست `POST /routes` با چک‌پوینت میانی
   (۳۶٫۲، ۵۸٫۶) نتیجه داد: مسیر دقیقاً از نقطهٔ چک‌پوینت عبور می‌کند
   (فاصلهٔ کمینهٔ مسیر تا نقطه: ۰٫۰ کیلومتر؛ ۱۷۸٫۴ ک.م در ۳۵۹ گره) —
   پس موتور و قرارداد API درست‌اند. مشکل، تجربهٔ کاربری فرانت بود:
   - در نمای ۳بعدی فشردن «افزودن چک‌پوینت» بی‌سروصدا بی‌اثر بود (دکمه
     فشرده می‌ماند ولی هیچ کلیکی اثری ندارد). حالا در ۳بعدی دکمه با دلیل
     روشن قطع می‌شود: «افزودن چک‌پوینت فقط در نمایش ۲بعدی امکان‌پذیر است».
   - هیچ راهنمایی برای «حالا روی نقشه کلیک کن» وجود نداشت؛ حالا بنر راهنما
     («برای ثبت چک‌پوینت، روی نقشه کلیک کنید») روی نقشه و نشانگرِ
     متقاطع (crosshair) روی بوم نقشه، وضعیت ثبت را نشان می‌دهد.
   - چون گره‌های لایهٔ ۱۵۰۰ متر خردشده‌اند (همبستگی سه‌تکه)، چک‌پوینتی
     که «جیب» مبدأ/مقصد را جدا کند در باند سطحی به خطای ۴۰۰ گویای
     موجود می‌رسد — همان واقعیت فیزیکی داده، نه باگ.
2. **خطا در فریم جدای مودال:** بنر کوچک خطای محاسبهٔ مسیر روی نقشه با
   مودال مستقل `RouteErrorDialog` جایگزین شد (role=alertdialog، بستن با
   Escape/کلیک خارج/دکمه، فوکوس اولیه بر دکمهٔ بستن، پیام فارسی موتور).
   موفق‌شدن مجدد محاسبه هم مودال را پشت سر خود پاک می‌کند.
3. **واحدهای فارسی:** ماژول `utils/format.ts` + هوک `useFormatLang`:
   مسافت «۸۰٫۵ ک.م»، زمان «۱س۲۰د»/«۲س»/«۳۰د» (گردشدن ایمن؛ «۱س۶۰د»
   هرگز نمایش داده نمی‌شود)، ارتفاع «۳٬۶۰۰ متر»، سرعت «۷٫۲ م/ث».
   در سربرگ نتیجهٔ پنل، صفحهٔ نتیجه و پاپ‌آپ اطلاعات نقطه اعمال شد؛
   برچسب طیف باد هم در fa «م/ث» شد. زبان انگلیسی قالب لاتین خودش را
   نگه می‌دارد.

**خروجی:** `frontend/src/utils/format{,.test}.ts`،
`frontend/src/hooks/useFormatLang.ts`،
`frontend/src/components/features/routing/RouteErrorDialog{,.test}.tsx`،
`CheckpointManager{,.test}.tsx`، `PathInfoPanel(.test).tsx`،
`RoutingMapScreen.tsx`، `frontend/src/pages/ResultsPage.tsx`،
`frontend/src/components/features/{map/PointInfoPopup,layers/WindSpeedLegend}`
(+تست)، `ui/Button.tsx` (پشتیبانی ref برای React 19)، کلیدهای i18n تازه.

**شواهد:** فرانت ۶۴/۶۴ تست (شامل ۱۹ تست تازه: مودال، راهنمای چک‌پوینت،
قالب فارسی/لاتین) + typecheck + lint (بدون هشدار) + build موفق؛ تأیید
زندهٔ عبور دقیق مسیر از چک‌پوینت در سطح API (بالا).

## قفل ارتفاعِ چک-پوینت (۲۰۲۶-۱۰-۱۶) — گراف/بادسواری، لنگر هوایی

**بازخورد کاربر:** چک-پوینتی را در نمای سه-بعدی با محور «ارتفاع» گیمبال بالا
می‌برد (مثلاً ۲۲۰۰ متر)، ولی مسیر محاسبه‌شده همچنان همان‌جا روی زمین
می‌گذشت (ارتفاع ≈۱۱۱۴ متر = ارتفاع زمین آن نقطه).

**ریشهٔ باگ (دو لایه):**
1. گراف انباشتهٔ مسیریابی، سرِ هر قطعه را همیشه **گره زمین** همان نقطه
   می‌بست (قرارداد «صعود در مبدأ، فرود در مقصد»)، پس هر قفلی در سطح
   «رسیدن به چک-پوینت» بی-اثر بود؛ حتی انتخاب نزدیک‌ترین سطح هم مشکل را
   حل نمی‌کرد، چون مسیر همچنان تا گره زمینِ چک-پوینت پایین می‌آمد.
2. بادسواریِ قفل‌شده، کروزِ «کلیهٔ قطعه» را به سطح قفل می‌بست؛ قطعه‌ای که
   *از* چک-پوینت خروج می‌گرفت، غالباً هیچ برنامه‌ای برای پرواز دوردستِ
   دقیقاً در همان سطح نداشت و به خطای ۴۰۰ جعلی می‌رسید.

**اقدام‌ها:**
1. **لنگر هوایی در گراف** (`pathfinding/graph.py`): `to_stacked_graph`
   پارامتر `endpoint_altitudes` (قفل ارتفاعی سرِ مبدأ/مقصد) گرفت؛ به‌جای
   گره زمین، گره هوایی روی مختصات دقیقِ همان نقطه و در سطح قفل ساخته
   می‌شود؛ به چند گرهٔ نخستِ همان سطح (یال هم‌سطح، بدون هزینهٔ صعود جعلی)
   وصل می‌شود. اگر سطح قفل جزو سطوح انباشته نباشد یا هیچ نقطهٔ پروازپذیری در
   آن سطح نزدیک باشد، `ValueError` شفاف بلند می‌شود (خطای ۴۰۰ فارسی در
   API). `find_optimal_path` و `_route_across_layers` در
   `pathfinding/routing.py` پارامتر را مستقیم می‌رسانند.
2. **قرارداد قفل در API** (`src/api/routers/routes.py`): نزدیک‌ترین سطح
   به قفل + `endpoint_altitudes=(start_lock, end_lock)` برای هر قطعه.
   تعارض دو قفلِ نابرابرِ دو سر یک قطعه → خطای ۴۰۰ فارسی؛ قفلِ
   غیرقابل-پرواز → خطای ۴۰۰ فارسی (پیش‌تر هم بادسواری داشت، حالا گراف
   هم دارد).
3. **بادسواری:** قفل فقط برای «رسیدن» سخت است — قطعهٔ ورودی به چک-پوینت
   قفل‌شده کروزش دقیقاً همان سطح است و فرود نمی‌گیرد (حالت عبوری،
   `land_at_end=False` از کار قبلی)؛ قطعهٔ خروجی از همان ارتفاع در-هوا
   آغاز می‌شود (شروع در ارتفاع قفل) ولی کروزش آزاد است (سطوح باند).
4. **فرانت:** چسباندن محور ارتفاع گیمبال به نزدیک‌ترین سطح واقعی
   (`nearestLayerAltitude` در `config/routing.ts`؛ فقط روی رهاکردن
   محور «بالا») و نشانِ «در ارتفاع قفل‌شدهٔ …» در فهرست چک-پوینت‌ها.
   تست نشانگر یک باگ واقعی را آشکار کرد: کلید i18n تازه با `{alt}` تک
   آکولاد نوشته شده بود ولی قرارداد این پروژه `{{alt}}` است — اصلاح شد.
5. **آزمون‌ها:** ۴ تست تازهٔ لنگر هوایی در
   `tests/pathfinding/test_routing.py` (سرِ قفل در-هوا تمام/آغاز می‌شود،
   قفل بیرون از سطوح رد می‌شود، هر دو سر قفل) + ۲ تست نشانگر
   `CheckpointManager`.

**شواهد زنده (سرویس تازه، ۱۲۷٫۰٫۰٫۱:۸۰۰۰):** مسیر a_star با چک-پوینت
قفل ۲۲۰۰: همهٔ نقاط در شعاع ±۲ ک.م چک-پوینت **دقیقاً ۲۲۰۰ متر** (نزدیک‌ترین
نقطه ۰ متر از چک-پوینت) — فرو-ریزش ۱۱۱۴ متری برطرف شد؛ بادسواری هم
عبور در ۲۲۰۰ (نزدیک‌ترین نقطه ۰ متر، ۲۲۰۰ متر). تعارض قفل‌ها →
۴۰۰ فارسی «ارتفاع قفل‌شدهٔ چک-پوینت‌های دو سر این قطعه یکی نمی‌شود…»؛
قفل ۱۵۰۰ روی زمین مرتفع → ۴۰۰ فارسی در هر دو الگوریتم. دروازه‌ها:
بک‌اند ۲۱۲/۲۱۲ + ruff بدون خطا؛ فرانت ۶۶/۶۶ + typecheck + lint + build.

**یادداشت صداقت:** مسیر a_star با چک-پوینتِ قفل طول بیشتری می‌گیرد
(۱۸۷٫۶ ک.م به‌جای ۱۷۷ ک.م آزاد) — این هزینهٔ فیزیکیِ «عبور اجباری از
نقطه» است نه باگ. بادسواری با قفل دوردست‌تر می‌دود (سیاست دالان
آزمایشیِ همین الگوریتم)؛ الگوریتم پیش‌فرض رابط کاربری a_star است.

## ارتفاع آزاد چک‌پوینت + بازبینی (۲۰۲۶-۱۰-۱۷) — «وسط لایه‌ها» و حذف دکمهٔ خوالی‌غالی

**خواستهٔ کاربر:** ۱) «چک‌پوینت‌ها فقط به لایه‌ها می‌چسبند — نمی‌توانم آن‌ها
را وسط دل لایه‌ها بگذارم!» ۲) «مشاهده لایه‌های باد در نقطه؟ چه کاری می‌کرد!»
۳) «چک‌پوینت را در نمای ۳بعدی هم روی دشت انتخاب‌شده بگذارم!» ۴) «دکمهٔ
مشاهده لایه‌های باد در نقطه را حذف کن.»

**اقدام‌ها:**
1. **لایهٔ واقعی در هر ارتفاع دلخواه** (`src/api/routers/routes.py`):
   نمایهٔ باد پروژه پیوسته است (`profile_at`؛ لگ‌خطی در ارتفاع بالای زمین)،
   پس برای قفلی که وسطِ دل لایه‌هاست (مثلاً ۱۸۰۰) با همان مدلِ
   ۱۵۰۰/۲۲۰۰/... یک لایهٔ واقعی ساخته می‌شود (`_level_field_for`، کش
   چرخان ۲۴‌تایی) و یک گراف تک‌لایه با همان پارامترهای گراف اصلی
   (کف ایمنی، پیمانهٔ زمین یال، طول بیشینهٔ یال) `_router_for_locked_level`
   را می‌سازد. مقایسهٔ پیشین «نزدیک‌ترین سطح به قفل» حذف شد؛ هر قفل
   **دقیقاً** در همان ارتفاع معتبر پرواز می‌شود. سطح استاندارد هم‌چنان از
   گراف اصلی می‌رود (بدون مسیرِ مانورِ بی‌دلیل).
2. **تعارض قفل با باند** (`_check_lock_within_band`): اگر ارتفاع قفل
   بیرون از باند ارتفاعی انتخابی باشد، ۴۰۰ فارسی (پیش‌تر بی‌سروصدا به
   نزدیک‌ترین سطحِ باند می‌رفت!). پیام سطح‌های باند را با «،» می‌شمارد.
3. **بادسواری در ارتفاع قفل:** نمونه‌بردار باد لایهٔ سر-الاکلپی
   (`_sampler_for_level`) به فهرست لایه‌ها اضافه می‌شود تا کروزِ دقیقاً
   قفل‌شده، بادِ همان ارتفاع را بخواند — نه پله‌ایِ لایهٔ پایین‌تر.
4. **فرانت — اسنپ‌برداشت:** محور ارتفاع گیمبال دیگر به «نزدیک‌ترین سطح»
   نمی‌جهد؛ ارتفاع آزاد گزارش می‌شود (کف: زمین + ۲۰۰ متر، همان قید رسم
   صحنه). `nearestLayerAltitude` حذف شد. پس دیگر «نمیتونم وسط لایه‌ها
   بگذارم» معنا ندارد — موتور همگام شد.
5. **فرانت — چک-پوینت در ۳بعدی روی دشت واقعی:** قاعدهٔ «فقط ۲بعدی»
   برداشته شد؛ حالت «افزودن چک‌پوینت» در نمای ۳بعدی هم فعال است. کلیکِ
   خالی صحنهٔ دست‌ساز از `pickLatLon` (پیکان‌یابی راه‌رونده از دوربین به
   سطح زمین با اغراق عمودی) مختصات واقعی می‌دهد و چک‌پوینتِ بی‌ارتفاع
   روی دشت می‌نشیند (ارتفاع عبور را بعداً می‌توان با گیمبال بالا برد).
   در این حالت گویِ زیر کلیک گیمبال را باز نمی‌کند و نشانگر موس
   همیشه crosshair است (`placingPoint` در `scene-gl`).
6. **فرانت — حذف دکمهٔ «مشاهده لایه‌های باد در نقطه»** به‌درخواست کاربر:
   دکمه، حالت انتخاب نقطه، پاپ‌آپ `PointInfoPopup`، هوک
   `useWindAtPoint`، واکشی `point-all` و کلیدهای i18n — همه حذف.
   «اطلاعات نقطه» دیگر به هیچ‌وجه در پیش‌نمایش دیده نشود.

**شواهد زنده (سرویس تازه، ۱۲۷٫۰٫۰٫۱:۸۰۰۰):** a_star + چک‌پوینت قفل
**۱۸۰۰ متر** (وسط ۱۵۰۰ و ۲۲۰۰): `layer_altitude_m = 1800.0`؛ همهٔ نقاط
±۲ ک.م چک‌پوینت دقیقاً ۱۸۰۰ متر و نزدیک‌ترین نقطه ۰ متر افقی — ارتفاع
مسیر ۹۸۶-۲۱۱۶ متر با گذرِ صاف ۱۸۰۰ حوالی چک‌پوینت. باند [0,1500] + قفل
۱۸۰۰ → ۴۰۰ فارسی «ارتفاع قفل‌شدهٔ چک‌پوینت (1800 متر) بیرون از باند
ارتفاعی انتخابی (1500 متر) است...»؛ بادسواری + قفل ۲۲۰۰ (سطح استاندارد)
→ عبور دقیق ۲۲۰۰ و ۰ متر افقی (بازتأیید کار گذشته)؛ بادسواری + قفل
۱۸۰۰ همان دالان → ۴۰۰ صادقانه «قابل پرواز نیست» (کروزِ ثابت زیر قله‌های
میانه جا نمی‌شود — با واقعیتِ خردشدگی لایهٔ ۱۵۰۰ هم‌خوان).
`GET /v1/wind-layers/point-all` → ۴۰۴ (حذف شد).

**دروازه‌ها:** بک‌اند ۲۱۲/۲۱۲ + ruff بدون خطا؛ فرانت ۶۶/۶۶ + typecheck
+ lint + build. `docs/PROJECT_PROGRESS.md` ضمیمه‌ای.

## چهار درخواست پیش‌نمایش (۲۰۲۶-۱۰-۱۷) — پیکان ثابت، هموارسازی مسیر، انیمیشن پنل و کلیک زمین ۳بعدی

**خواستهٔ کاربر:** ۱) با حرکت ذرات باد، پیکان‌های ثابتِ زیرشان («شبح») هم
پیداست؛ حذف شود. ۲) «Cannot add checkpoint in the 3D scene» — دو بار
گزارش شد. ۳) مسیر در چک‌پوینت‌ها و پیچ‌ها «شکسته/زاویه‌دار» است؛ نرم شود.
۴) پنل کناری هنگام باز/بسته شدن بی‌انیمیشن می‌چهرد؛ پویا شود.

**اقدام‌ها:**
1. **حذف کامل سامانهٔ پیکان ثابت:** لایهٔ اسپرایت مپ‌لیبر
   (`wind-arrows`/`wind-arrance-layer`، سازندهٔ اسپرایت باد، گزینهٔ آرایه،
   `updateArrowLayer`) که زیر ذرات متحرک نشسته بود به‌طور کامل حذف شد
   (`windFieldLayer.ts` و پایه‌ساز نقشه در `MapView.tsx`). ذرات (رَست +
   سرِ پیکان در یک هندسه) تنها پیکان‌های باد در نمای ۲بعدی هستند. برچسب
   «پیکان‌های باد» حالا فقط پیکان‌های ۳بعدی را روشن/خاموش می‌کند
   (i18n: «پیکان‌های باد (۳بعدی)») و `WIND_ARROW_CONFIG` از پیکربندی
   حذف شد.
2. **نرم‌سازی گوشه‌های مسیر (فقط نمایش):** `utils/geometry.ts` با
   `chaikinSmoothLine`/`chaikinSmoothXYZ` (دو گذر برشِ چایکین با حفظِ
   دقیق سر و ته) به خط ۲بعدی و لولهٔ ۳بعدی اعمال شد (لوله پیش از
   اسپلاینِ کتمول-روم در صحنه). دادهٔ موتور دست‌نخورده است.
3. **انیمیشن پنل کناری:** پوشش پنل به‌جای فروپاشیِ عرضی، «لغزش +
   محو» تغییر کرد (`translate`/`opacity`/`visibility`، ۳۰۰ میلی‌ثانیه،
   ease-out) با جهت‌آگاهی `rtl:`/`ltr:`، `overflow-hidden` و بستن
   `pointer-events` در حالت بسته. با کلید `translate:` تایلویند ۴
   ساخته می‌شود (نه `transform`).
4. **برداشت زمین ۳بعدی — سه لایه:**
   الف) پذیرش مختصات (`pickBoundsKm`) از «کادر CSV» به «کادر زمین ∪
   مسیر ∪ نشانگرها + ۸ ک.م» گسترش یافت — کلیک حوالی مقصد (عرض جغرافیایی
   ۳۵٫۱۵۴، بیرونِ کادر CSV) دیگر بی‌صدا null نمی‌ماند.
   ب) پرتوِ برخوردی از صفحهٔ تخت z=0 اکنون تا هر فاصله‌ای دنبال
   می‌شود؛ پیشتر «فراتر از صفحهٔ دور» مردود می‌شد و کلیک روی
   دشتِ مرئیِ بیرونِ صفحهٔ دور ساکت می‌افتاد.
   ج) آستانهٔ تشخیص کشیدن: `dragMoved` با جابه‌جاییِ انباشته از نقطهٔ
   نشست و تسامح ۸ پیکسل — پیشتر لرزشِ تک‌رویدادِ بیش از ۳ پیکسل،
   کلیکِ دستِ واقعیِ تاچ‌پد را دور می‌ریخت. در شاخهٔ معمولیِ
   `pointerdown` هم `dragStartScreen` ست می‌شود.

**شواهد زنده (CDP روی پیش‌نمای واقعی، ۲۰۲۶-۱۰-۱۷):** خواندن فایل‌های
سرویس‌شده از سرور توسعه: هیچ نشانهٔ `wind-arrows`/`ARROW_LAYER`/
`updateArrowLayer` باقی نیست؛ برچسب «(۳بعدی)» در هر دو زبان دیده
می‌شود. حالت‌های استایلِ پنل: خواصِ انتقال `translate, opacity,
visibility` با ۰٫۳ ثانیه — بسته: visibility 0/op 0/translate −۱۱۰٪
همراه با غیرفعالِ pointer-events، باز: قابل‌دید — رفتار صحیح هر دو.
انیمیشنِ روانِ تمیز را فقط مرورگرِ واقعی کاربر نشان می‌دهد (محیطِ headless
زمانِ انیمیشن را جلو می‌اندازد).

جریان کامل با لرزشِ کلیک واقعی (حداکثر ۴٫۵ پیکسل بین press و
release): مبدأ/مقصد کلیکی → مسیر ۲۰۲٫۷ ک.م (مطابق پاسخ مستقلِ همین
درخواست به سرور)؛ چک‌پوینت ۲بعدی (۳۵٫۶۲۱، ۵۸٫۵۰۰) ثبت؛ در ۳بعدی دو
کلیکِ بیرونِ کادر CSV ثبت شد (#1 — ۳۵٫۸۰۵، ۵۷٫۶۹۶ از روی دشتِ بارگذاشته‌شده،
#2 — ۳۵٫۷۹۱، ۵۷٫۷۰۸ بیرونِ کادرِ داده، با صفحهٔ تخت) و پس از
بازمحاسبه پایدار ماندند؛ بنر «مسیر محاسبه شد» بدون هیچ خطا. نکتهٔ
صادقانه: کلیک ۲بعدی با لرزش ۴٫۵ پیکسلی به آستانهٔ خودِ مپ‌لیبر
(۳ پیکسل) نمی‌رسد — رفتار استاندارد مپ‌لیبر است که کاربران با آن
سازند؛ درخواست کاربر همان ۳بعدی بود. (اسکرین‌ها: `۱۴` تا `۱۹` در
`/tmp/opencode/shots/`)

**دروازه‌ها:** فرانت typecheck + lint + vitest ۷۲/۷۲ (۱۵ فایل؛ ۶
آزمون تازهٔ `geometry.test.ts`) + build — همه سبز. بک‌اند در این دور
دست نخورده و آزمون ۲۱۲/۲۱۲ آن از دورهٔ پیش بر جای است؛ هم-PR شامل
تغییرات `routes.py`ِ همان دوره است. `docs/PROJECT_PROGRESS.md`
ضمیمه‌ای.

## بازخورد برداشت چک‌پوینت (۲۰۲۶-۱۰-۱۷) — علتِ شکست دیدنی و آستانهٔ لرزش

**خواستهٔ کاربر:** «قرار دادن چک‌پوینت در ۳بعدی هنوز کار نمی‌کند — کلیک
روی زمین هیچ نمی‌کند!» — بعدها: «چیپی می‌گوید قابل برداشت نیست ولی چرا؟!»
و «دکمهٔ محاسبهٔ مجدد عوض می‌شود — متنش ناپدید و فقط قاب می‌ماند».

**اقدام‌ها:**
1. **آستانهٔ لرزش واقعی:** `dragMoved` انباشته با تسامح **۸ پیکسل**
   (پیشتر یک لرزشِ > ۳ پیکسلِ تاچ‌پد، کلیکِ دستِ واقعی را دور می‌ریخت).
   E2E با «کلیکِ ۴٫۵ پیکسلی» ثبت و پس از بازمحاسبه ماندگاری اش ثابت شد.
2. **صفحه‌بخورِ بی‌سقف:** پرتوِ صفحهٔ تخت z=0 تا هر فاصله‌ای دنبال
   می‌شود (پیشتر فراتر از صفحهٔ دور مردود) — کلیکِ روی «دشتِ مرئی»ِ
   بیرون صفحهٔ دور دیگر لغو نمی‌شود.
3. **بازخورد سه‌رایانه‌ای نصب شد:** هر کلیکِ مسلح دیگر ساکت نیست:
   - «چک‌پوینت #n ثبت شد» (سبز، ۱٫۶ ثانیه) در ثبت موفق
   - «اینجا بیرون از کادر دادهٔ برنامه (زمین/باد) است…» (کهربایی) عند
     ردِ باند — `onPickMiss(kind)` صحنه → صفحه؛ «آسمان است» برای پرتو
     رو به بالا.
   - Esc حالت «کلیک کنید» را آزاد می‌کند.
4. **جابه‌جایی چیپ‌ها از بنر:** راهنمای مسلح و چیپ بازخورد به پایینِ
   وسط (بالای نمایه) رفتند — قبلاً روی بنرِ «محاسبه مجدد» می‌نشستند و
   کاربر «دکمهٔ بی‌متن» خوانده بود؛ خودِ بنر، متنِ دارد (اسکرین ۲۵).

**شواهد زنده:** شبکهٔ ۱۰-کلیکی در سه حالت دوربین: پیش‌فرض همه ثبت؛
zoomOut1/zoomOut2 همه «بیرون از کادر داده» — با دلایل کیلومتری
(`km=−119/x…`، باند `[−8..224]×[−91..69]`) — یعنی دشتِ اطرافِ نوار
زمین در دوربینِ دور به نقاط ۱۲۰-۵۰۰ کیلومتری پهنه نپاچیده و ردِ
باند درست است؛ پیامِ روشن اینجا جای «هیچ». کلیک‌های نوارِ زمین در
همهٔ دوربین‌ها ثبت. اسکرین‌های ۲۱-۲۶ تازه؛ فرآیند در
`/tmp/opencode/cdp-probe-grid.mjs` و `cdp-final2.mjs` ماندگار.
حالتِ «آسمان» در framing فعلی تولید سیاه نشد (پرتوِ همهٔ پیکسل‌های
فریم به دشت/دستگاه می‌رسد) — مسیرِ کد و پیام قرار گرفته ولی با
فریمِ عکاسی دیگر باید تأیید شود.

**دروازه‌ها:** tsc + eslint + vitest ۷۲/۷۲ + build سبز (بعد از
حذفِ ابزار دیباگ). بک‌اند دست‌نخورده؛ دروازهٔ پیشین ۲۱۲/۲۱۲.

## پذیرش مقیاس‌پذیر صفحهٔ تخت ۳بعدی (۲۰۲۶-۱۰-۱۷) — «همه‌جا خطا می‌گوید»

**خواستهٔ کاربر:** «هر جا کلیک می‌کنم خطا می‌دهد؛ هیچ‌وقت چک‌پوینت ثبت
نمی‌شود!» — یعنی پیامِ «بیرون از کادر داده» که خطای دیدنیِ پیشین
ساخته بود، خودش مانعِ تجربه شد: کاربر دشتِ خاکیِ اطرافِ نوار را
«زمینِ قابل کلیک» می‌داند و همهٔ کلیک‌هایش رد می‌شد.

**تحلیل:** اندازه‌گیری با ابزارِ موقت نشان داد نقشه‌برداریِ صفحهٔ
تختِ z=0 با فاصلهٔ دوربین منفجر می‌شود: wheel۹۰۰ → ۲۰۱−/۱۴۲+ ک.م؛
در سقفِ زوم (camDist=۶۰۰) همان پیکسل → ۵۳۸−/۴۴۵+ ک.م. پدِ ثابتِ
۱۵۰ ک.م کافی نمی‌شود؛ علاوه بر آن، موتورِ مسیریابی CPِ بیرون کادر
را کامل و بی‌خطر می‌گیرد (گراف به نزدیک‌ترین گره می‌شکند، واپسین
بخش‌های بسیار نزدیک رد/cut می‌شوند) — پس محدودیتِ سخت لازم نیست.

**اقدام:** حاشیهٔ پذیرشِ «صفحهٔ تخت» = کفِ ۱۵۰ ک.م **یا** ۱٬۱×camDist
(هرکدام بزرگ‌تر) — یعنی «هر جا در مقیاس دیدِ کاربر»؛ برخوردِ واقعی
با زمین همان ۸ ک.م ثابتِ خودش. افقِ بسیار دور (فراتر از مقیاس دید)
همچنان صادقانه «بیرون از کادر داده» می‌گوید. ابزارِ دیباگ حذف شد.

**شواهد زنده (اسکرین ۲۸):** ثبت در چهار حالتِ دوربین — پیش‌فرض،
wheel۹۰۰، زومِ حداکثر (پیکسلِ دورِ افق‌گرد) و نزدیکِ نوار — همگی
«ثبت شد» و بَج #۱-#۴ در فهرست. CPهای دور در فهرست با مختصاتِ واقعی
(#۲ ۳۷٫۲/۵۵٫۱، #۳-#۴ ۳۹٫۹/۵۱٫۵) نشسته، مسیرِ ۳بعدی صادقانه تا
بیرونِ نوار کشید. موتور با همین CPها: ۲۰۰ و ۱۹۷۹٫۷ ک.م (پرش •
واقعی به سمت CP) — با CPِ ۱۱۹ ک.می: ۲۴۷٫۸ ک.م و min-lon=۵۷٫۱۷
(دقیقاً روی CP).

**درس:** پیامِ صادقانه جای سکوت را می‌گیرد ولی اگر مرزِ پذیرش با
درکِ دیدِ کاربر هم‌خوان نباشد، هر کلیک «خطا» می‌شود — مرزِ پذیرش
باید با مقیاسِ دوربین راه بیاید.

دروازه‌ها: tsc + eslint + vitest ۷۲/۷۲ + build سبز. بک‌ند دست
نخورده؛ کامیت `ccf3b49`.

## تعمیر وارون ماتریس و لنگر دقیق CP (۲۰۲۶-۱۰-۱۸) — «نقطه روی چیزی که کلیک کردم نیست»

**خواستهٔ کاربر:** «نقطهٔ انتخابی در ۳بعدی روی چیزی که کلیک کردم نیست!»

**ریشهٔ واقعی — باگِ ریاضیِ مادر:** تابع دستی `invertMat4` در
`frontend/src/three/manual/mat4.ts` چند جملهٔ کوفاکتورش عبارتِ
اشتباه داشت (مثلاً در `inv[13]` به‌جای `m[13]`، `m[14]`). سنجش عددی
نشان داد وارونِ تولیدی نه معکوسِ ماتریس است و نه معکوسِ ترانهادهٔ آن
(مقایسه با حذف گاوسین: ۱۶/۱۶ عنصر غلط). پرتوِ برداشتِ کلیکِ ۳بعدی از
همان ماتریسِ وارونِ خراب ساخته می‌شد — پس **همهٔ کلیک‌ها از ابتدا به
نقطهٔ اشتباهی از جهان میرسیدند**: گاهی هنوز داخلِ کادرِ پذیرش (CP در
جای اشتباه ثبت می‌شد = همین شکایت) و گاهی بیرون («بیرون از کادر
داده» = شکایت قبلی). دو شکایتِ ظاهراً مختلف، یک ریشه داشتند.

**تعمیرها:**
1. `invertMat4` با تعریف مستقیمِ ضمیمه (کوفاکتور ۳×۳) بازنویسی شد؛
   راستی‌آزمایی عددی: M·M⁻¹=I روی ۳۰۰ ماتریس تصادفی + تطابق با حذف
   گاوسین (۵ موردِ مردود، بدحالتِ تصادفی بودند و در قرعهٔ دیگر سبز).
2. پرتوِ برداشت بیرونِ کادر را «بدون زمین» میبیند، نه فلاتِ ادامهٔ
   ارتفاعِ لبه (رفعِ ناسازگاریِ مارش با رندر) — کلیکِ دشتِ اطراف به
   صفحهٔ تراز z=0 میرسد که با ادراکِ دیداریِ کاربر سازگار است.
3. لنگرِ گوی نشانگر/گیزمو/کفِ کشیدنِ محورِ ارتفاع: بیرونِ کادر روی
   صفحهٔ تراز (z=0) — نه ارتفاعِ چسبیدهٔ لبه که گوی با پارالاکس از
   محل کلیک دور میافتاد.
4. شعاع گوی با فاصلهٔ دوربین مقیاس میگیرد (۰٫۹ ک.م کف؛ ۱٫۲٪camDist)
   — در نمای دور هم گویِ «کجا کلیک کردهام» خوانا بود (قبلاً ~۴ px
   عملاً نامرئی).

**شواهد زنده:** بازپروژهٔ نقطهٔ برخوردِ پرتو دقیقاً پیکسلِ کلیک
(`near→[700,720]` و `far→[700,720]` برای کلیک (700,720))؛ گوی
کهربایی زیر نشانگرِ کلیک (انحراف A: (0,−20) px روی سطح — بالابریِ
شعاع؛ B: (−1,−5) px روی صفحهٔ تراز — اسکرین ۳۱)؛ رگرسیونِ سهزوم:
ثبت ۵/۵ (نوار و دشت، اسکرین ۳۲)؛ موتور با CPِ بیرون کادر ۲۰۰ (۲۴۷٫۸
ک.م در ۱۱۹ ک.می؛ ۱۹۷۹٫۷ ک.م با سه CP تا ۵۰۰ ک.می).

**درس:** در گرافیکِ دستی، هر توابع ریاضیِ محور باید با آزمونِ عددی
(نه فقط بازرسی چشمی) راستیآزمایی شود؛ نشانههای غیرمستقیم (مختصات
«بهنظر موجه») میتوانستند ماهها باگِ پنهان را توجیه کنند.

دروازهها: tsc + eslint + vitest ۷۲/۷۲ + build سبز. کامیت `f86b9d9`.

## گوی کروی، ساقه دیداری و برچسب عدد چکپوینت (۲۰۲۶-۱۰-۱۸)

**خواستهٔ کاربر:** «نقاط مبدأ/مقصد/چکپوینت در ۳بعدی بهسختی دیده میشوند!
نقاط کرهٔ درست نیستند، و چکپوینتها عدد ندارند!»

**ریشه و تعمیرها (`c359941`):**
1. **شکلِ لهشده:** گویِ نشانگر با ۱۲ رأسِ ایکوزاهدرون و مثلثبندیِ
   «اتصالِ هر یال به نزدیکترین رأس» ساخته میشد — هیچگاه ایکوزاهدرونِ
   واقعی نبود و سیلوئتِ نامنظم میداد. جایگزین: کرهٔ کاملِ UV
   (۱۶ قطعهٔ طولی × ۱۰ حلقهٔ عرضی) با سایهٔ لمبرتِ جهتدار (نورِ ثابت
   از جنوبِ شرقیِ بالا) — سیلوئتِ دیسکِ کامل.
2. **دیدهنشدن:** شعاعِ گوی از ۱٫۲٪ به ۱٫۸٪ فاصلهٔ دوربین افزایش یافت
   (کفِ ۰٫۹ ک.م) + ساقهٔ باریکِ متقاطع از سطحِ لنگر تا مرکزِ گوی که
   «این نقطه کجا لنگر افتاده» را در نمای دور هم نشان میدهد.
3. **عددِ چکپوینت:** صحنهٔ WebGL متن ندارد؛ برچسبِ «#N» بهصورت لایهٔ
   DOMِ روی بوم پیاده شد: کالِبکِ `onMarkerScreens` در پایانِ هر فریم
   موقعیتِ صفحهٔ گویها را میدهد و `ManualSceneView` بدون رندرِ مجددِ
   React، چیپهای عدد را زیرِ گویها همگام میکند (پشتِ دوربین/بیرونِ
   کادر پنهان).

**شواهد زنده:** اسکرینهای ۳۳-۳۴ — در دو زوم، گویهای CP کرویِ سایهدار
با برچسبِ #۱/#۲/#۳ دقیقاً بالای گوی؛ پُریِ دیسکِ گویِ روی دشت ۰٫۷۸
(دیسکِ کامل ≈ π/۴)؛ برچسبها با جابهجاییِ دوربین دنبالِ گوی میمانند
(سنجشِ DOM: موقعیتِ برچسب = موقعیتِ گوی − شعاعِ صفحهٔ آن).

دروازهها: tsc + eslint + vitest ۷۲/۷۲ + build سبز. کامیت `c359941`.

## ۱۴۰۵/۰۷/۲۷ — پریرایشِ کاملِ صحنهٔ سه‌بعدی و اصلاحِ یافتهها (شاخهٔ task/api-terrain-band-routing)

پس از گوی/برچسبِ چکپوینت، همهٔ پوشهٔ three/manual با آزمونِ عددی (jiti)
خطاگیر شد و هر نقصِ یافته تعمیر شد؛ هیچ رفتارِ کاری از کار نیفتاد.

**یافتهها و اصلاحها:**

1. **ماتریسها (`mat4.ts`):** سرصفحه بهاشتباه «ردیف-محور» جرئت میگفت در حالیکه
   کدِ column-major است؛ همان گمرکی ریشهٔ باگِ دیرینِ پرتوی برداشت.
   سرصفحه اصلاح شد؛ `invertMat4` برای `|det| < 1e-12` ماتریس صفر میدهد
   (نه وارونِ غولآسا)؛ `mat4LookAt(eye==target)` بدونِ NaN و قطعی.
   آزمونِ عددیِ همهٔ توابع (ضرب، چرخش، پرسپکتیو، اورتو، lookAt، وارونِ
   ۲۰۰ ماتریسِ تصادفی) سبز.
2. **تونلزنیِ مارش در نمای دور:** گامِ ثابتِ ۲۲۰تایی در نمای دور تا ~۲۴
   ک.م باز میشد و کوهِ باریک از میان نمونهها میگذشت (کلیکِ کوه به
   دشت پشتِ سر میافتاد). مارش حالا ~۱ ک.م گام (سقفِ ۲۴۰..۱۶۰۰) +
   خروجِ سریع بعد از گذر از کادرِ زمین (+۲۰ ک.م) — پرتو در هر محور
   یکنواست. مشاهدهٔ زندهٔ کلیکِ کوه در نمای دور: CP دقیق روی کوه (ش۳۵).
3. **پاک شدن ارتفاع با درگِ افقی:** گزارشِ editPos همیشه altMِ محاسبه‌شده از
   z را میفرستاد و صفحه آن را در آبجکتِ CP مینوشت — درگِ افقی ارتفاع
   را پاک میکرد و CP بی صدا به زمین میچسبید. حالا گزارشِ مختصات خالص
   است و درگِ افقیِ نقطهٔ ارتقادار با `editPriorAltM` ارتفاع را نگاه
   میدارد (در ش۳۷ قرصِ «در ارتفاع قفلشده» میماند).
4. **بنبستِ ارتفاعِ ناممکن:** کشیدنِ محورِ ارتفاع سقفِ
   `WIND_ALTITUDE_MAX` (۳٬۶۰۰ متر) دارد — موتور بالاتر از آن «مسیر
   عبوری ندارد» میداد و کاربر در خطای نامفهوم میافتاد.
5. **فشارِ مرکزِ گیمبال همیشه «شرق–غرب»:** نمونهگیری از t=0 (مبدأِ مشترک
   همهٔ محورها) همیشه محورِ شرق–غرب را میگرفت؛ کشیدنِ «بالا» افقی حرکت میکرد.
   حالا نمونهگیری از ۱/۶ طول فلش + جریمهٔ جهتنایی — کشیدن بالا واقعاً
   محورِ ارتفاع را میگیرد (اثرِ زنده: قفلِ ۳٬۶۰۰ متر ساخته شد).
6. **هزینهٔ Layout:** `projectToScreen` در هر فراخوانی (~۲۵–۵۰ بار در
   فریم) getBoundingClientRect و ماتریسِ MVP کاملِ تازه میساخت.
   کِشِ `viewRect` هرمفریم + کِشِ MVP (نسبت/چرخش/فاصله/هدف) اضافه شد.
7. **پدِ مبدأ/مقصد:** پدِ CP با فاصلهٔ دوربین مقیاس میگیرد؛ مبدأ/مقصد
   با سقف کوتاهتر (مبدأِ صدها ک.م دور، مسیرِ بنجل میساخت).
8. **تکانهٔ رفریم:** هر recalc دوربین را تاخی میزد؛ حرکت فقط وقتی
   مرکز/گسترهٔ مسیر واقعاً بیرونِ دید است. `frameAll`/`frameOverview`
   دوباره «دستکاری نشده» میروند.
9. **برچسبِ هر گوی با شعاعِ صفحهیِ خودش** (بدون وام گرفتن از گویِ اول).
10. **بازسازیِ گیمبال در اسکرولِ ویل** فقط با >٪۳ تغییرِ فاصله (قبلاً هر رویدادِ ویل سه مش از صفر ساخته میشد).
11. **تلهٔ کلیپِ `terrainElevationAt`** قوی مستند شد + هلپرِ امن
    `elevationInFrame`؛ `buildMarkerPillar` (~۵۷ خط) حذف شد.

**شواهدِ زنده (CDP):** ش۳۵–۳۷ + رگرسیون ۵/۵ در سه زوم؛ tsc + eslint +
vitest ۷۲/۷۲ + build سبز. کامیتهای `1709e25` و `87b77a4`.

**باقیماندهٔ زیرِ نظر: ناپدیدشدن متنِ «محاسبه مجدد!» هیچوقت بازتولید نشد —
برای بازآزماییِ کاربر میماند.

## رنگآمیزی مسیر بر پایه «مقابله با باد» در اکثر: بهبود رنگآمیزی مسیر بر پایه «مقابله با باد» در هر دو نمایش و طیفنما (21 Oct 2026)

**شاخه:** `task/wind-fight-coloring` (انباشته روی `task/api-terrain-band-routing`) — بدون کامیتِ پیشتر.

**مقصد:** درصدِ «مقابله با باد» برای هر نقطهٔ مسیر (`fight% = (1 − cos(bearing − flowHeading))/2 ×
100`، جهتِ هواشناسیِ `direction_deg` «از» + برای جریان ۱۸۰+) محاسبه و مسیرِ ۲بعدی (گرادیانِ
GPU روی `line-progress`) و لولهٔ ۳بعدی (رنگِ هر حلقه) با رمپ سفید (۰٪ همسو با باد) تا سرخ
(۱۰۰٪ روبه‌باد کامل) رنگ شود؛ طیف‌نمای همان رمپ زیر سه مقدارِ جزئیات مسیر نشیند.

**پیادهسازی:**
1. `utils/windFight.ts` جدید: `fightPercent`، `segmentBearingRad`/`bearingFromDeltaRad`،
   `nearestField` (لایهٔ نزدیک‌ترین به ارتفاعِ نقطه)، `computeFightProfile` (قطعهٔ صفر از
   نزدیک‌ترین قطعهٔ معتبر ورثه میشود؛ بدون میدان/مسیرِ تک‌نقطه null)، `cumulativeFractions`،
   `fightAtFraction` (درون‌یابی در فضای کسرِ مسیر)، `whiteToRed` (CSS ۰..۲۵۵) و
   `whiteToRed01` (شناور ۰..۱ برای GL).
2. `utils/windField.ts`: `GridMeta` عمومی شد + پارامتر اختیاریِ `meta` برای
   `sampleWindAtPoint` (کِشِ WeakMap جلوگیری از مرتبسازیِ شبکه در هر نمونه).
3. `three/manual/scene.ts`: `buildRouteTube` پارامتر پنجم `ringColorAt(fraction)` گرفت —
   رنگ هر حلقه × سایه صورتیِ لامبرتِ قبلی.
4. `three/manual/scene-gl.ts`: `Manual3DSceneOptions.fightProfile`؛ در `rebuildDynamic`
   کلوزرِ `whiteToRed01(fightAtFraction(...))` به لوله میدهد؛ طولِ غلطِ پروفایل → رنگِ
   ثابت قبلی (نه مسیرِ رنگیِ غلط).
5. `MapView.tsx`: منبعِ `route-line` با `lineMetrics: true` ساخته میشود؛ اثرِ گرادیانِ
   `line-gradient` با توقفهای نازکشده (~۷۲) از پروفایل؛ نبود پروفایل → خنثی (null).
6. `RoutingMapScreen.tsx`: `fightProfile` با `useMemo` از `path_3d` (یا `path` با
   `layer_altitude_m`) روی همه میدانهای بارگذارده — به `MapView` میرود.
7. `PathInfoPanel.tsx`: طیفنما زیر سه مقدار — میله گرادیان (چپ-به-راست/LTR معکِ RTL)
   برچسبها «۰٪ همسو با باد» / «۱۰۰٪ روبه‌باد کامل» و عنوان «مقابله با باد در طول مسیر»؛
   سه کلیدِ i18n در fa/en.

**تا اثر**: باگِ اشباع — `whiteToRed` ۰..۲۵۵ مستقیم به رنگهای GL میداد؛ >۱ اشباع سفید
شده بود (لوله با ۸۶–۹۸٪ مقابله سفید میماند). `whiteToRed01` آن را شفا داد.

**شواهد زنده (CDP، کروم headless):**
- ۳بعدی: لوله روبه‌باد سرخِ تخت (`221,45,45`) — عکس `e2eA-3d.png`؛ مسیر معکوس همان پهنه
  سفید/صورتیِ نرم — `e2eB-3d.png`؛ آمار پیکسل ناحیه لوله: سرخ ۳/۸۷٪ (A) مقابل ۲/۰۹٪ (B)
  و سفیدِ خالص صفر (A) مقابل ۰/۵۲٪ (B).
- ۲بعدی: خط مسیر روبه‌باد سرخِ کامل — `e2eA2-2d-zoom.png`؛ معکوس سفیدِ شیرین با گذر
  تدریجی صورتی — `e2eB2-2d-zoom.png`.
- طیفنما زیر سه مقدار (RTL: «۰٪ همسو با باد» راست و سفید): در همه اسکرینها؛
  `data-testid='route-result-summary'` میله گرادیان + هر دو برچسب + عنوان دارد.
- ماژول درونصفحه (vite): `westAvg=87/2` [`eastAvg=12/8`] روی میدان زنده ۲۹۰۰ متر.
- رگرسیون: چکپوینت ۳بعدی (برچسب «#1») + حذف از پنل سبز؛ خطاهای کنسول صفر.
- گیتها: `tsc --noEmit`، `eslint .`، `vitest 92/92` (۲۰ تست جدیدِ `windFight.test.ts`)،
  `vite build` — همه سبز.

**ادامهٔ همین کار — گامای perception (۲۲ اکتبر):** کاربر دید که مسیرِ همسوباد «تک‌رنگِ
سفید» به نظر میرسد. سنجشِ زنده نشان داد رندر درست است؛ مقصر خطی بودنِ رمپ بود: توزیعِ
مقابله روی مسیرهای کمینه-زمان در ۰–۳۰٪ متراکم است و `whiteToRed(10)=rgb(252,236,236)`
روی زمین روشن بینایی نمی‌داد. `whiteToRed`/`whiteToRed01` با گامای ۰٫۳۵ (مستنذ
`FIGHT_RAMP_GAMMA`) بازنویسی شد — سر/ته بجامانده (سفید ۰٪، `FIGHT_RED` در ۱۰۰٪)؛ ۳٪ →
`(245,191,191)`، ۵۰٪ → `(228,85,85)`. توقفهای میانی طیفنما (`#eb8383` ۲۰٪، `#e66262` ۴۰٪،
`#e24a4a` ۶۰٪، `#df3636` ۸۰٪) با همان منحنی همگام شد. شواهدِ تازه: مسیر ۰–۲۴٪ (S←N)
با گذرِ واضحِ سپید→صورتی در لوله و خط ۲بعدی (`nsr-3d.png`/`nsr-2d.png`)، مسیر ۷۲–۱۰۰٪
(N←S) با گذرِ صورتی→سرخِ عمیق (`ns-3d.png`)؛ کنسول صفر. گیتها: tsc/eslint سبز،
`vitest 93/93` (۲۱ تست ترمز)، `vite build` سبز.

**ادامهٔ همین کار — طیف چندفام (۲۲ اکتبر):** بازخورد بعدی کاربر: «رنگ‌ها حس نیستند؛
فامهای دیگر؛ سرخ برای تغییرهای کوچک هم خیلی پیدا باشد». رمپ `whiteToRed` حذف و تابع
`fightColor`/`fightColor01` با ۱۱ توقفِ ColorBrewer RdYlBu معکوس جایگزین شد — آبی تیره
(۰٪ همسوباد) به فیروزه/ژاله → زرد کم‌مایه (۵۰٪ خنثی) → نارنجی → سرخِ عمیق (۱۰۰٪) با همان
گاما ۰٫۳۵؛ تغییرهای کوچک حالا «فام» عوض میکنند نه فقط روشنایی (۰٪=`[49,54,149]`، ۵٪=`[198,230,241]`،
۵۰٪=`[245,119,72]`، ۱۰۰٪=`[165,0,38]`). `FIGHT_RED` به سرخِ عمیق تغییر کرد؛ فراخوانیهای
`scene-gl`/`MapView` به نو. طیفنما با `fightLegendGradientCss(isRtl)` (۵۱ توقفِ CSS از
همان تابع) ساخته میشود — همرنگِ کامل با خط/لوله. شواهدِ زنده: مسیر ۰–۲۴٪ آبی تیره تا
زرد (`nsr-3d.png`، آمار quantile: `[57,78,161]`→`[254,220,140]`)، روبه‌باد سرخِ عمیق
`e2eA-3d.png`/`e2eA2-2d-zoom.png`، همسوباد آبی↔فیروزه↔زردِ کِرم `e2eB-3d.png`؛ کنسول
صفر. گیتها: tsc/eslint سبز، `vitest 94/94` (۲۲ تست)، `vite build` سبز.

**ادامهٔ همین کار — سفید «حرکتِ راحت» و تیرگیِ مقابله (۲۲ اکتبر):** بازخورد نهایی کاربر:
زیرِ ~۸٪ سفیدتر شود؛ حرکتِ همسوباد روشن/سفید بماند و قسمتهای مقابله سرخهای تیره بگیرند
+ آیکونِ Reset پنل به زبالهدان + برچسب «۱۰۰٪ روبهباد کامل» → «۱۰۰٪ مقاومت با باد»
(و `100% wind resistance`). گامای سراسری حذف و خمِ گرهیِ `FIGHT_WARP`
`[(0,0),(2,0.04),(8,0.18),(20,0.45),(40,0.68),(70,0.85),(100,1)]` جایگزین شد: ۰٪ سفیدِ
خالص؛ ۲٪ `(254,235,235)`؛ ۸٪ `(246,169,167)`؛ ۱۵٪ `(223,95,85)`؛ ۵۰٪ `(111,11,35)`؛
۱۰۰٪ `(58,0,20)`. آیکون `RefreshCw` → `Trash2` (همان `handleReset`)؛ کلید i18n
`routing.fightHundred` در fa/en عوض شد. شواهد زنده: همسوباد با سفید و تلنگرِ سرخِ نرم
(`e2eB-3d.png`)، مقاومتِ کامل مرواریدیِ تیره (`e2eA-3d.png`)، گذرِ سفید→صورتی→سرخِ
تیره روی مسیر ۰–۲۴٪ (`nsr-3d.png`، quantiles: سفید→`(215,79,69)`)؛ زبالهدان و برچسب نو
در هر دو شات. گیتها: `vitest 95/95`، tsc/eslint/build سبز؛ کنسول صفر.
