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

## 2026-08-31 — Task: Data Preparation for Pathfinding (Stage 2)

**Agent:** Claude (AI)
**Branch:** `task/data-prep-pathfinding-units`
**PR:** #TBD (opened by owner/token holder; see note below)

### Summary
Reviewed `src/preprocessing/pathfinding_preparation.py`, which already existed
on `main` (added in PR #8, "documentation overhaul", not as a dedicated task
PR) and already covered most of the checklist: grid construction, altitude
range 500-2000 m, u/v conversion, and vector normalization. Added the one
missing checklist item — unit unification — and fixed a stale, mismatched doc.

### What I built
- `normalize_units()` in `pathfinding_preparation.py`: accepts `speed`/`direction`
  or `wind_speed`/`wind_direction` column names, converts speed to m/s from
  `m/s`/`km/h`/`kt`, rejects negative speeds, wraps direction into `[0, 360)`.
- Wired `normalize_units` into `prepare_for_pathfinding` via a new `speed_unit=` parameter.
- Exported the module's public functions from `preprocessing/__init__.py`.

### Input I used
Existing `src/preprocessing/pathfinding_preparation.py` and its test file;
`data/khorasan_pathfinding_ready.csv` as a reference for real-world column
naming (it uses `speed`/`direction`, which is what motivated the alias support).

### Output of this task
- `src/preprocessing/pathfinding_preparation.py` — added `normalize_units`, `SPEED_ALIASES`, `DIRECTION_ALIASES`, `SPEED_UNIT_TO_MPS`; `prepare_for_pathfinding` gained `speed_unit=` param.
- `tests/test_pathfinding_preparation.py` — 6 new tests (38 total in repo, up from 32).
- `docs/task_data_prep_pathfinding.md` — rewritten; previously described an unimplemented, unrelated `networkx` graph-builder design that did not match the real code.
- `docs/PATHFINDING_DATA_FORMAT.md` — added an "Accepted Input Units and Column Names" section and documented dense-grid behavior for missing cells.

### For the next task
- Canonical output columns: `timestamp, lat, lon, altitude, wind_speed, wind_direction, u, v, u_normalized, v_normalized` — see `docs/PATHFINDING_DATA_FORMAT.md`.
- Import via `from preprocessing import prepare_for_pathfinding`.
- **Known gap, flagged to task owner, who chose to proceed anyway:** the QC dependency's real completion status is unclear (progress log above says incomplete, but 32 tests now exist and pass), and the Spatiotemporal Consistency dependency has not been started at all (`src/preprocessing/consistency.py` does not exist). This module has not been validated against either module's real output.
- The task's stated deadline (1405-05-29 17:00 Iran time) had already passed by the time this was picked up.

### Test
```
pytest -q       → 38 passed
ruff check .    → All checks passed!
```

### PR
Not yet opened — no valid GitHub token was supplied for this session (the
prompt's token field only contained the placeholder text). Branch and commits
are ready locally; opening the PR requires a token with push + PR scopes.

### Separate note — AGENTS.md vs .github/PROMPT.md conflict
`AGENTS.md` §1 requires all user-facing content (docs, PR descriptions, commit
messages, code comments) to be in Persian. `.github/PROMPT.md` §6 requires
English for the same categories ("comments, PRs, commit messages, docs...
enforced for AI-agent-facing files"). These directly conflict. This PR follows
`.github/PROMPT.md` (the more specific, more recently updated canonical prompt,
and what was explicitly pasted as this session's instructions), but the
conflict itself should be resolved by the owner in a separate docs PR.
