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

## 2. Golden Rules (Non-Negotiable)

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

## 3. Task Workflow (What "doing a task" means)

Each task comes from ClickUp and has: a title, a description with **Purpose /
Items to Check / Required Output / Deadline / Priority**, a checklist, and
dependencies.

1. Read the task description and its checklist **carefully**. If anything is
   ambiguous, ask the owner — do not guess.
2. Create your branch: `git checkout -b task/<slug>`.
3. Implement **only** the items on the checklist.
4. **Run the full test suite and linter before pushing** (see §5). All must pass.
5. Push the branch and open a PR using the repository PR template. The PR
   description MUST:
   - Restate the task's Purpose in one paragraph.
   - Repeat the task's **Items to Check** as a checkbox list (`- [ ]`), ticking
     the ones you completed.
   - Include **evidence**: paste the output of the tests/linter you ran.
   - State the task's Deadline and Priority.
   - Link the ClickUp task (paste its URL).
6. **Never merge your own PR.** Merging is the owner's job. If the owner requests
   changes, address them and re-request review.
7. If CI fails on your PR, fix it — a red PR is an unfinished PR.

## 4. Repository Layout

```
roshd-wind-pathfinder/
├── AGENTS.md                  # this file
├── CONTRIBUTING.md            # human guide (Persian)
├── README.md
├── pyproject.toml             # project config + ruff/pytest settings
├── .github/
│   ├── pull_request_template.md
│   └── workflows/ci.yml       # runs on every PR and push
├── src/                       # Python package source (starts with گام ۳)
└── tests/                     # pytest suite (one file per module)
```

The module ownership map (who owns which files) will be added here as the code
lands. Until then: **if a file is created by someone else's task, you may read
it but not rewrite it** — coordinate through PRs.

## 5. Commands

```bash
# install dev dependencies
python -m pip install -e ".[dev]"

# run linter (ruff)
ruff check .

# run tests
pytest -q
```

**Definition of done:** `ruff check .` passes **and** `pytest -q` passes **and**
every checklist item is either implemented or explicitly marked as not-applicable
with a reason.

## 6. Commit Message Style

- Written in Persian, imperative mood, one line under 72 chars, plus a short body
  if needed.
- Prefix with the task area: `preprocess: ...`, `interp: ...`, `qc: ...`, `docs: ...`.

Examples:
```
interp: پیادهسازی درونیابی IDW با پارامتر توان قابل تنظیم
```
```
qc: افزودن اعتبارسنجی بازه معتبر برای دادههای باد
```

## 7. PR Etiquette

- PR title = task title (Persian first, English in parentheses if present).
- Keep PRs small and focused on one task. If you need to touch shared code,
  mention it in the PR description.
- Resolve conflicts on your branch before re-requesting review.
- Be polite and concise; the owner reviews in Persian.
