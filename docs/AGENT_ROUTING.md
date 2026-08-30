# Agent Routing Guide — Where to Put Code?

> **AI agents:** When you receive a task, route your code to the **correct folder**
> by matching the task topic to the categories below. Putting code in the wrong
> folder causes merge conflicts and will not pass PR review.

---

## Decision Tree — Routing Flowchart

```
What is your task?
│
├── Data fetching/saving/caching
│   └── src/data/
│       Tests → tests/data/
│       Docs → docs/task_data_caching.md
│
├── Data preprocessing
│   ├── IDW interpolation
│   │   └── src/preprocessing/idw.py
│   │       Tests → tests/preprocessing/test_idw.py
│   │       Docs → docs/task_idw_interpolation.md
│   │
│   ├── Kriging interpolation
│   │   └── src/preprocessing/kriging.py
│   │       Tests → tests/preprocessing/test_kriging.py
│   │       Docs → docs/task_kriging_interpolation.md
│   │
│   ├── Quality control
│   │   └── src/qc/wind_qc.py
│   │       Tests → tests/test_wind_qc.py
│   │       Docs → docs/task_wind_qc.md
│   │
│   ├── Spatiotemporal consistency
│   │   └── src/preprocessing/consistency.py
│   │       Tests → tests/preprocessing/test_consistency.py
│   │       Docs → docs/task_spatiotemporal_consistency.md
│   │
│   └── Data prep for pathfinding
│       └── src/preprocessing/pathfinding_preparation.py
│           Tests → tests/test_pathfinding_preparation.py
│           Docs → docs/task_data_prep_pathfinding.md
│
├── Pathfinding (Stage 3)
│   ├── Graph construction
│   │   └── src/pathfinding/graph.py
│   │       Tests → tests/pathfinding/test_graph.py
│   │
│   ├── Algorithms (A*, Dijkstra)
│   │   └── src/pathfinding/algorithms.py
│   │       Tests → tests/pathfinding/test_algorithms.py
│   │
│   └── Route optimization
│       └── src/pathfinding/routing.py
│           Tests → tests/pathfinding/test_routing.py
│
└── Docs / CI / Project structure
    └── docs/ or .github/
```

---

## General Rules

1. **Each task creates exactly one `*.py` file** in the relevant module — nowhere else.
2. **Each `*.py` module has a separate `test_*.py` file** in the corresponding test folder.
3. **Each task has a design document** in `docs/task_*.md` — use the file
   `tasks/templates/task_template.md`.
4. **`__init__.py` imports only those modules that actually exist** — do not import future (tbd) modules.
5. **Do not modify raw data files (`data/*.csv`, `data/*.json`)** — these are fixed inputs.
6. **Only append to `docs/PROJECT_PROGRESS.md`** — do not touch previous sections.

---

## Branch and PR Naming

```
task/<clickup-task-id>-<short-slug>
```

Example: `task/86bba36de-idw-interpolation`

- English slug, dash-separated
- ClickUp task id (if present)
- Max 40 characters
