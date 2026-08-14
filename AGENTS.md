# AGENTS.md — Rules for AI Agents Working in This Repository

> This file is auto-loaded into the context of any AI coding agent (Hermes, Claude
> Code, Cursor, Copilot, Codex, etc.) that works in this repo. If you are an AI
> agent, you MUST read and follow every rule below before doing anything.

## 1. Project Overview

**Roshd Wind Pathfinder** — a wind-data preprocessing and pathfinding pipeline for
a meteorological project (Persian team). The project is built incrementally in
stages (گام ۱: data sources & API keys, گام ۲: preprocessing & interpolation,
future stages: pathfinding).

The human team:
- **Arman (owner)** — reviews and merges everything. Never overrule him.
- **Mehdi** — collaborator.
- **Amirali** — collaborator.

**Language rule:** all user-facing content (docs, PR descriptions, commit
messages, code comments) is written in **Persian (Farsi)** with proper
half-spaces (ZWNJ). Technical identifiers stay in English.

## 2. Task Source — ClickUp

**All tasks live in ClickUp, not in this repo.** Each task has:
- Title (Persian + English in parentheses)
- Description with 5 sections: **Purpose / Items to Check / Required Output / Deadline / Priority**
- A checklist (7 items)
- Dependencies on other tasks

### How to read a task

1. **Get the task URL from the human.** Example:
   `https://app.clickup.com/t/86bb9vt6d`
2. **Fetch the task** using the ClickUp API or ask the human to paste the description.
3. **Parse the 5 sections:**
   - **Purpose** → what this task accomplishes
   - **Items to Check** → the checklist you must implement (every item must be done)
   - **Required Output** → what files/functions/artifacts you must produce
   - **Deadline** → Persian date + time (17:00 Iran)
   - **Priority** → High (1-2) or Normal (3-4)
4. **Check dependencies** → if the task depends on others, ensure those are merged first.

### ClickUp API (if you have a token)

```bash
# Get task details (replace TASK_ID)
curl -H "Authorization: $CLICKUP_TOKEN" \
  "https://api.clickup.com/api/v2/task/TASK_ID?include_markdown_description=true"
```

The response includes `markdown_description` (the 5 sections) and `dependencies`.

## 3. Golden Rules (Non-Negotiable)

1. **NEVER push to `main` directly. NEVER commit to `main`.** All work happens
   on a feature branch; `main` changes only through a Pull Request that the owner
   approves and merges.
2. **Always pull the latest `main` before starting work** and merge/rebase
   `origin/main` into your branch before opening a PR.
3. **One branch per task.** Branch name: `task/<short-slug>` (e.g.
   `task/idw-interpolation`).
4. **Never commit secrets.** No API keys, tokens, passwords, or credentials —
   ever. Not in code, not in config, not in docs. Secrets live only in
   environment variables / GitHub Secrets.
5. **Do not invent facts.** If you don't know something (API behavior, a library,
   a requirement), check the actual source or ask. Never guess.
6. **Do not modify files outside the scope of your task** without saying so.

## 4. Task Workflow (What "doing a task" means)

1. **Read the task description and its checklist carefully.** If anything is
   ambiguous, ask the owner — do not guess.
2. **Create your branch:** `git checkout -b task/<slug>`.
3. **Implement ONLY the items on the checklist.** Do not add extra features.
4. **Run the full test suite and linter before pushing** (see §6). All must pass.
5. **Push the branch and open a PR** using the repository PR template. The PR
   description MUST:
   - Restate the task's Purpose in one paragraph.
   - Repeat the task's **Items to Check** as a checkbox list (`- [ ]`), ticking
     the ones you completed.
   - Include **evidence**: paste the output of the tests/linter you ran.
   - State the task's Deadline and Priority.
   - Link the ClickUp task (paste its URL).
6. **Never merge your own PR.** Merging is the owner's job. If the owner requests
   changes, address them and re-request review.
7. **If CI fails on your PR, fix it** — a red PR is an unfinished PR.

## 5. Repository Layout

```
roshd-wind-pathfinder/
├── AGENTS.md                  # this file
├── CONTRIBUTING.md            # human guide (Persian)
├── README.md
├── pyproject.toml             # project config + ruff/pytest settings
├── .github/
│   ├── pull_request_template.md
│   └── workflows/ci.yml       # runs on every PR and push
├── src/                       # Python package source
│   └── roshd_wind_pathfinder/
│       ├── __init__.py
│       ├── data/              # data fetching & caching (گام ۱)
│       ├── preprocessing/     # interpolation, QC (گام ۲)
│       └── pathfinding/       # pathfinding algorithms (گام ۳+)
└── tests/                     # pytest suite (one file per module)
```

### Module ownership (who owns which files)

| Module | Owner | Files |
|--------|-------|-------|
| `src/roshd_wind_pathfinder/data/` | Arman | API clients, caching |
| `src/roshd_wind_pathfinder/preprocessing/` | Shared | IDW, Kriging, QC |
| `src/roshd_wind_pathfinder/pathfinding/` | Future | — |

**Rule:** If a file is created by someone else's task, you may read it but not
rewrite it — coordinate through PRs.

## 6. Commands

```bash
# install dev dependencies
python -m pip install -e ".[dev]"

# run linter (ruff)
ruff check .

# run tests
pytest -q

# run tests with coverage
pytest --cov=src
```

**Definition of done:** `ruff check .` passes **and** `pytest -q` passes **and**
every checklist item is either implemented or explicitly marked as not-applicable
with a reason.

## 7. Code Style

- **Python 3.10+** with type hints where practical.
- **Docstrings** in Persian for public functions/classes.
- **Imports:** stdlib → third-party → local, alphabetized within each group.
- **Line length:** 100 chars max (enforced by ruff).

### Allowed libraries (dependencies)

```toml
# Core
numpy>=1.24
scipy>=1.11
xarray>=2023.1
pandas>=2.0

# Data fetching
requests>=2.31
aiohttp>=3.8  # if async needed

# Interpolation
scipy.interpolate
# (IDW and Kriging use scipy/numpy — no extra deps)

# Testing
pytest>=7.4
pytest-cov>=4.0

# Dev
ruff>=0.4
```

**Do not add new dependencies without owner approval.**

## 8. Commit Message Style

- Written in Persian, imperative mood, one line under 72 chars, plus a short body
  if needed.
- Prefix with the task area: `data: ...`, `preprocess: ...`, `interp: ...`,
  `qc: ...`, `pathfinding: ...`, `docs: ...`, `test: ...`.

Examples:
```
interp: پیادهسازی درونیابی IDW با پارامتر توان قابل تنظیم
```
```
qc: افزودن اعتبارسنجی بازه معتبر برای دادههای باد
```

## 9. PR Etiquette

- **PR title = task title** (Persian first, English in parentheses if present).
- Keep PRs small and focused on one task. If you need to touch shared code,
  mention it in the PR description.
- Resolve conflicts on your branch before re-requesting review.
- Be polite and concise; the owner reviews in Persian.

## 10. When You're Stuck

1. **Read the task again** — the answer is usually in the Items to Check.
2. **Check existing code** in `src/` for patterns and conventions.
3. **Ask the owner** — better to ask than to guess wrong.
4. **Document blockers** in the PR if you can't proceed.
