# Run doc

Pure-Python project (no Node, no dev server). The deliverable the user watches is
a single self-contained HTML file, so the preview is a **file registration**, not
a server.

## Reproduce the artifacts

```bash
# 1) Python environment (only if .venv/ is missing)
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,viz]"

# 2) Terrain DEM (network: Open-Meteo elevation API, no key needed)
#    Writes data/khorasan_terrain.csv. The grid follows CORRIDOR_BBOX with ~2.5 km
#    *square* cells; currently 25 x 88 points (lat 35.90-36.45, lon 57.45-59.85).
#    The southern edge is deliberately 0.15 deg further out than the others: the
#    corridor's low route around the Binalud front needs that plain, and without
#    it the graph can only use the lattice row glued to the southern data edge.
.venv/bin/python scripts/fetch_terrain_data.py

# 3) Wind dataset (network: Open-Meteo forecast archive, no key needed)
.venv/bin/python scripts/fetch_khorasan_data.py --start 2026-08-29 --end 2026-08-30
#    Then QC it, which is what the scene reads:
#      data/khorasan_wind_qc_cleaned.csv

# 4) The routing scene itself (~8 MB, plotly.js inlined, works offline)
.venv/bin/python scripts/generate_routing_scene.py
#    -> docs/assets/routing_scene.html
```

Steps 2 and 3 need network access. Their outputs are committed, so a fresh
checkout can skip straight to step 4.

## Run / view

No server is required. Register the generated file directly as the preview:

```
docs/assets/routing_scene.html
```

By default the preview attaches to `docs/assets/routing_scene.html` in this
worktree. Nothing here binds a port or needs environment files.
