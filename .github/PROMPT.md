<!---
Give this prompt to any AI agent new to the project.
Fill in two values: the repo link and the GitHub token.
If the ClickUp task is uploaded as an attachment (PDF), the AI reads it.
If not, the AI asks you to upload the task or provide the link.
-->

# Standard Prompt — Roshd Wind Pathfinder Project

## Repository
https://github.com/Roshd-136/roshd-wind-pathfinder

## GitHub Token
[Paste the token here]

## Task
[Upload the PDF if you have one — otherwise the AI will ask for it]

---

## Instructions for the AI Agent

You are a programming agent. Clone the repository and work according to these rules:

1. Before doing anything, **read `AGENTS.md` completely and follow it**. If you spot a problem, open a separate PR suggesting a fix.

2. Read **`docs/AGENT_ROUTING.md`** for the module layout and naming conventions, and **`docs/PROJECT_PROGRESS.md`** to understand where the project currently stands.

3. If you did not receive a task → ask: "Please upload the ClickUp task as a PDF or provide its link."

4. Actually reuse the output of previous tasks. If you need data, fetch it from the cache module or a real API — do not fabricate data.

5. If you are unsure about anything, ask. It is better to ask than to guess.

6. **Language** — code, technical identifiers, branch slugs, and agent-facing docs
   (`AGENTS.md`, `docs/AGENT_ROUTING.md`, this prompt, PR titles/descriptions to the
   owner) are written in **English**. Human-facing content (README, CONTRIBUTING,
   commit messages, code comments/docstrings for the Persian-speaking team) is in
   **Persian with correct ZWNJ half-spaces**. Follow `AGENTS.md` for the exact rule.

7. **Branch naming** (enforced): create a branch named
   ```
   task/<clickup-task-id>-<short-slug>
   ```
   e.g. `task/86bba36de-idw-interpolation`. English slug, dash-separated, max 40 characters.

8. **Never push to `main` directly — it is enforced and rejected by the repository ruleset.** Create a feature branch, commit there, and open a pull request targeting `main`.

9. Write tests and make them green: `pytest -q` and `ruff check .` must pass without errors. The required `Lint & Test` CI check must pass.

10. At the end, update **`docs/PROJECT_PROGRESS.md`** — add a new section, never touch previous sections.

11. Open a PR but **do not merge it** — merging is only done by the project owner (lawbr3aker). PRs touching owned files require the owner's review (CODEOWNERS), so expect review feedback before merge.

This file is the canonical prompt. If the project rules change, update this file
and `AGENTS.md` together (they must stay in sync).
