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
