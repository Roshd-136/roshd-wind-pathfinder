# AGENTS.md — AI Agent Rules for This Repository

> This file is automatically loaded into the context of every AI coding agent
> (Hermes, Claude Code, Cursor, Copilot, Codex, and others) working on this repo.
> If you are an AI agent, you **must** read these rules completely and follow
> them before doing anything.

---

## 1. Project Overview

**Roshd Wind Pathfinder** — a wind-data preprocessing and pathfinding pipeline
for a meteorological project (Persian-speaking team). The project is built in
stages:
- **Stage 1:** Data sources and API keys (done)
- **Stage 2:** Preprocessing and interpolation (in progress)
- **Stage 3+:** Pathfinding (future)

**Team:**
- **Arman (project owner)** — reviews and merges everything. Never bypass him.
- **Mehdi** — collaborator (QC and data-preparation tasks)
- **AmirAli** — collaborator (consistency and documentation tasks)

**Language rule:** All user-facing content (docs, PR descriptions, commit
messages, code comments) is written in **Persian** with correct ZWNJ half-spaces.
Technical identifiers stay English.

---

## 2. Task Source — ClickUp

**All tasks are defined in ClickUp, not in this repo.** Each task has:
- Title (Persian + English in parentheses)
- Description with 5 sections: **Purpose / Items to Check / Required Output / Deadline / Priority**
- Checklist (7 items)
- Dependencies on other tasks

### How to read a task

1. **Get the task link from a human.** Example:
   `https://app.clickup.com/t/86bb9vt6d`
2. **Fetch the task with the ClickUp API**, or ask a human to paste the description.
3. **Analyze the 5 sections:**
   - **Purpose** ← what this task accomplishes
   - **Items to Check** ← the checklist to implement (all items must be done)
   - **Required Output** ← which files/functions/artifacts you must produce
   - **Deadline** ← Persian date + time (17:00 Iran)
   - **Priority** ← High (1-2) or Normal (3-4)
4. **Check dependencies** ← if a task depends on others, make sure those tasks are merged first.

---

## 3. Golden Rules (non-negotiable)

1. **Never push or commit directly to `main`.** All work happens on a feature
   branch; `main` only changes through a Pull Request that the owner approves and merges.
2. **Pull the latest `main` before starting work**, and merge/rebase
   `origin/main` into your branch before opening a PR.
3. **One branch per task.** Branch name: `task/<short-slug>` (e.g. `task/idw-interpolation`).
4. **Never commit a secret.** No API key, token, password, or credential — not in
   code, not in config, not in docs. Secrets live only in environment variables /
   GitHub Secrets.
5. **Do not fabricate facts.** If you do not know something (API behavior, a
   library, a requirement), check the real source or ask. Never guess.
6. **Do not modify files outside your task's scope without announcing it.**
7. **Do not fabricate data.** If you need data, fetch it from the cache module or a real API.

---

## 4. Task Workflow (what "doing a task" means)

1. **Read the task description and its checklist completely.** If anything is
   unclear, ask the owner — do not guess.
2. **Create a branch:** `git checkout -b task/<slug>`.
3. **Implement only the checklist items.** Do not add extra features.
4. **Put code in the correct folder.** Read the file
   [`docs/AGENT_ROUTING.md`](docs/AGENT_ROUTING.md) — the routing table is there
   (code in `src/<module>/`, tests in `tests/<module>/`, docs in `docs/task_*.md`).
5. **Run the full tests and linter before pushing** (see §6). All must pass.
6. **Push the branch and open a PR** using the repo's PR template. The PR
   description **must:**
   - Restate the task's purpose in one paragraph.
   - Repeat the **Items to Check** as a checklist (`- [ ]`) and tick the ones done.
   - Provide **evidence**: the actual test/lint output you ran.
   - Mention the task deadline and priority.
   - Include the ClickUp task link (paste the URL).
7. **Never merge your own PR.** Merging is the owner's job. If the owner requests
   changes, apply them and request review again.
8. **If the CI on your PR turns red, fix it** — a red PR means an unfinished PR.
9. **At the end, add a new section to `docs/PROJECT_PROGRESS.md`** — do not touch
   previous sections (this file is append-only).

---

## 5. Repository Structure

```
roshd-wind-pathfinder/
├── AGENTS.md                  # This file — AI agent rules
├── CONTRIBUTING.md            # Guide for human collaborators (Persian)
├── README.md                  # Project overview + architecture
├── pyproject.toml             # Project settings + ruff/pytest
├── .github/
│   ├── PROMPT.md              # ⚡ Standard prompt for AI agents
│   ├── pull_request_template.md
│   └── workflows/ci.yml       # Runs on every PR and push
├── docs/                      # ⚡ Project reference
│   ├── PROJECT_PROGRESS.md    # Project progress (append-only — read before any work)
│   ├── AGENT_ROUTING.md       # Code routing — where to put what
│   └── task_*.md              # Per-task documentation
├── tasks/                     # Task templates and status
│   ├── templates/task_template.md
│   ├── active/
│   └── completed/
├── src/                       # Python package (src-layout)
│   ├── __init__.py
│   ├── data/                  # Stage 1 — data fetching and caching
│   │   ├── __init__.py
│   │   └── cache.py           # WindDataCache
│   ├── preprocessing/         # Stage 2 — preprocessing and interpolation
│   │   ├── __init__.py
│   │   ├── idw.py             # IDWInterpolator
│   │   ├── kriging.py         # KrigingInterpolator
│   │   ├── qc.py              # WindQualityControl
│   │   ├── pathfinding_preparation.py
│   │   └── consistency.py     # (future)
│   └── pathfinding/           # Stage 3 — pathfinding (future)
│       ├── __init__.py
│       ├── graph.py           # (future)
│       ├── algorithms.py      # (future)
│       └── routing.py         # (future)
├── tests/
│   ├── data/
│   │   ├── test_cache.py
│   │   └── test_cache_no_pandas.py
│   ├── preprocessing/
│   │   ├── test_idw.py
│   │   └── test_kriging.py
│   ├── test_pathfinding_preparation.py
│   └── test_wind_qc.py
└── data/                      # Sample/test data
    ├── khorasan_wind_qc_cleaned.csv
    ├── khorasan_qc_report.json
    └── khorasan_pathfinding_ready.csv
```

> ⚠️ **Package structure:** The main modules live directly under `src/`.
> Imports look like `from data.cache import WindDataCache`.
> The correct path for the cache file is `src/data/cache.py`.

### Code Routing (summary)

> Full file: [`docs/AGENT_ROUTING.md`](docs/AGENT_ROUTING.md)

| Task | Code | Test | Docs |
|------|------|------|------|
| Data caching | `src/data/cache.py` | `tests/data/test_cache.py` | `docs/task_data_caching.md` |
| IDW interpolation | `src/preprocessing/idw.py` | `tests/preprocessing/test_idw.py` | `docs/task_idw_interpolation.md` |
| Kriging interpolation | `src/preprocessing/kriging.py` | `tests/preprocessing/test_kriging.py` | `docs/task_kriging_interpolation.md` |
| Quality control | `src/qc/wind_qc.py` | `tests/test_wind_qc.py` | `docs/task_wind_qc.md` |
| Consistency | `src/preprocessing/consistency.py` | `tests/preprocessing/test_consistency.py` | `docs/task_spatiotemporal_consistency.md` |
| Data prep for pathfinding | `src/preprocessing/pathfinding_preparation.py` | `tests/test_pathfinding_preparation.py` | `docs/task_data_prep_pathfinding.md` |
| Graph construction | `src/pathfinding/graph.py` | `tests/pathfinding/test_graph.py` | — |
| Algorithms | `src/pathfinding/algorithms.py` | `tests/pathfinding/test_algorithms.py` | — |
| Route optimization | `src/pathfinding/routing.py` | `tests/pathfinding/test_routing.py` | — |

### Module Ownership (who owns which files)

| Module | Owner | Files |
|--------|-------|-------|
| `src/data/` | Arman | API clients, caching |
| `src/preprocessing/` | Shared | IDW, Kriging, QC, pathfinding_preparation |
| `src/qc/` | Shared | WindQualityControl |
| `src/pathfinding/` | Future | — |

**Rule:** If a file was created by another person's task, you may read it but not
rewrite it — coordinate through a PR.

---

## 6. Commands

```bash
# Install dev dependencies
python -m pip install -e ".[dev]" --break-system-packages

# Linter (ruff)
ruff check .

# Tests
pytest -q

# Tests with coverage
pytest --cov=src
```

**Definition of done:** `ruff check .` passes **and** `pytest -q` passes **and**
every checklist item is either implemented or explicitly marked not-applicable.

---

## 7. Code Style

- **Python 3.10+** with type hints where possible.
- **Docstrings** in Persian for public functions/classes.
- **Imports:** stdlib → third-party → local, alphabetical within each group.
- **Line length:** max 100 characters (enforced by ruff).
- **Test structure:** every `*.py` module has a matching `test_*.py` file in the
  corresponding tests folder.

### Allowed Libraries (dependencies)

```toml
# Core
numpy>=1.24
pandas>=2.0
xarray>=2023.1     # if needed
scipy>=1.11        # if needed (interpolation)

# Data fetching
requests>=2.31
aiohttp>=3.8       # if needed (async)

# Testing
pytest>=7.4
pytest-cov>=4.0

# Dev
ruff>=0.4
```

**Do not add new dependencies without the owner's approval.**

---

## 8. Commit Message Style

- In Persian, imperative mood, one line under 72 characters, plus a short body if needed.
- Prefix with the task scope: `data: ...`, `preprocess: ...`, `interp: ...`, `qc: ...`,
  `pathfinding: ...`, `docs: ...`, `test: ...`, `ci: ...`.

Examples:
```
interp: پیادهسازی درونیابی IDW با پارامتر توان قابل تنظیم
```
```
qc: افزودن اعتبارسنجی بازه معتبر برای دادههای باد
```

---

## 9. PR Etiquette

- **PR title = task title** (Persian first, English in parentheses if present).
- Keep PRs small and focused on one task. If you need to touch shared code,
  mention it in the PR description.
- Resolve conflicts in your branch before requesting review again.
- Be polite and concise; the owner reviews in Persian.

---

## 10. If You Get Stuck

1. **Re-read the task** — the answer is usually in Items to Check.
2. **Review the existing code under `src/`** for patterns and conventions.
3. **Read the docs:** `docs/PROJECT_PROGRESS.md` (status),
   `docs/AGENT_ROUTING.md` (routing).
4. **Ask the owner** — it is better to ask than to guess wrong.
5. **Document blockers in the PR** if you cannot proceed.
