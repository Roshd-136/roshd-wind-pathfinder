# Standard Prompt — Roshd Wind Pathfinder Project

## Repository
https://github.com/lawbr3aker/roshd-wind-pathfinder

## GitHub Token
[Paste the token here]

## Task
[Upload the PDF if you have one — otherwise the AI will ask for it]

---

## Instructions for the AI Agent

You are a programming agent. Clone the repository and work according to these rules:

1. Before doing anything, **read `AGENTS.md` completely and follow it**. If you spot a problem, open a separate PR suggesting a fix.

2. Read **`docs/PROJECT_PROGRESS.md`** to understand where the project currently stands.

3. If you did not receive a task → ask: "Please upload the ClickUp task as a PDF or provide its link."

4. Actually reuse the output of previous tasks. If you need data, fetch it from the cache module or a real API — do not fabricate data.

5. If you are unsure about anything, ask. It is better to ask than to guess.

6. Write tests and make them green: `pytest -q` and `ruff check .` must pass without errors.

7. At the end, update **`docs/PROJECT_PROGRESS.md`** — add a new section, do not touch previous sections.

8. Open a PR but do not merge it. Only Arman merges.

This prompt is always up to date. If anything changes, update only `PROJECT_PROGRESS.md`.
