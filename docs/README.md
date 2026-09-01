# Documentation Index

> Single point of reference for all docs in this folder. Update the status column
> in the same PR that lands or changes the code a doc describes.

| File | Purpose | Language | Status |
|------|---------|----------|--------|
| [`PROJECT_PROGRESS.md`](PROJECT_PROGRESS.md) | Project progress log (append-only) | English (headers) / mixed | Always current |
| [`AGENT_ROUTING.md`](AGENT_ROUTING.md) | Code routing — where each task's code/tests/docs live | English | Current |
| [`task_data_caching.md`](task_data_caching.md) | Stage 1 & 2 — WindDataCache | Persian + English | ✅ Implemented (tests pass) |
| [`task_idw_interpolation.md`](task_idw_interpolation.md) | IDW interpolation (`src/preprocessing/idw.py`) | Persian | ✅ Implemented (7 tests pass) |
| [`task_kriging_interpolation.md`](task_kriging_interpolation.md) | Kriging interpolation (`src/preprocessing/kriging.py`) | Persian | ✅ Implemented (11 tests pass) |
| [`task_kriging_variogram.md`](task_kriging_variogram.md) | Kriging variogram selection | Persian | ✅ Implemented (part of Kriging) |
| [`task_wind_qc.md`](task_wind_qc.md) | Quality control (`src/qc/wind_qc.py`) | Persian | ✅ Implemented (2 tests pass) |
| [`task_data_prep_pathfinding.md`](task_data_prep_pathfinding.md) | Data prep (`src/preprocessing/pathfinding_preparation.py`) | Persian | ✅ Implemented (1 test pass) |
| [`task_spatiotemporal_consistency.md`](task_spatiotemporal_consistency.md) | Spatio-temporal consistency (future module) | Persian | 🔄 Pending (no code yet) |
| [`task_preprocessing_docs.md`](task_preprocessing_docs.md) | Preprocessing docs task | Persian | 🔄 Pending (no code yet) |
| [`PATHFINDING_DATA_FORMAT.md`](PATHFINDING_DATA_FORMAT.md) | Data format spec for pathfinding stage | English | ✅ Current |
| [`wind_qc.md`](wind_qc.md) | QC method detail | Persian | ✅ Current |

**Status values:** ✅ Implemented (tests pass) · 🔄 Pending (no code yet) · 📝 Template only

**Note:** Some Persian docs still show "در انتظار پیادهسازی" (pending) but the
corresponding modules are **fully implemented and tested** — the doc status is
stale. Update the doc's status badge in the PR that finalizes documentation.