"""دریافت ارتفاع زمین (DEM) کریدور مشهد–سبزوار و ذخیره آن در ``data/``.

اجرا:

    python scripts/fetch_terrain_data.py

خروجی: ``data/khorasan_terrain.csv`` (شبکه منظم ۱۹×۳۷ نقطه، ارتفاع بر حسب متر).

منبع: سرویس Elevation اوپن‌متیو (بر پایه DEM کپرنیکوس GLO-90). این سرویس
نیازی به کلید ندارد و ارتفاع را در هر نقطه از مختصات می‌دهد. چون صحنه سه‌بعدی
باید آفلاین و تکرارپذیر باشد، نتیجه یک‌بار گرفته و ذخیره می‌شود؛ صحنه‌سازی هم
از همین فایل می‌خواند و به شبکه وابسته نیست.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viz.terrain import (  # noqa: E402
    TERRAIN_CELL_KM,
    TerrainModel,
    terrain_grid,
    write_terrain_csv,
)

OUTPUT_PATH = ROOT / "data" / "khorasan_terrain.csv"
ENDPOINT = "https://api.open-meteo.com/v1/elevation"
SOURCE = "Open-Meteo Elevation API (Copernicus DEM GLO-90)"
# سرویس در هر درخواست حداکثر ۱۰۰ مختصات می‌پذیرد.
BATCH_SIZE = 100
MAX_ATTEMPTS = 4


def fetch_batch(lats: np.ndarray, lons: np.ndarray) -> list[float]:
    """ارتفاع یک دسته مختصات را از سرویس می‌گیرد (با تلاش مجدد)."""
    query = "&".join(
        [
            "latitude=" + ",".join(f"{value:.5f}" for value in lats),
            "longitude=" + ",".join(f"{value:.5f}" for value in lons),
        ]
    )
    url = f"{ENDPOINT}?{query}"

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                payload = json.load(response)
            elevations = payload.get("elevation")
            if not isinstance(elevations, list) or len(elevations) != len(lats):
                raise ValueError(
                    f"Unexpected elevation payload: {payload!r}"
                )
            return [float(value) for value in elevations]
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = error
            if attempt < MAX_ATTEMPTS:
                time.sleep(2.0 * attempt)
    raise RuntimeError(f"Elevation request failed after {MAX_ATTEMPTS} attempts: {last_error}")


def main() -> None:
    lats, lons = terrain_grid()
    lon_mesh, lat_mesh = np.meshgrid(lons, lats)
    flat_lats = lat_mesh.ravel()
    flat_lons = lon_mesh.ravel()

    print(
        f"Fetching terrain for {len(flat_lats)} points "
        f"({len(lats)}x{len(lons)} grid, ~{TERRAIN_CELL_KM:g} km square cells) "
        f"from {SOURCE}..."
    )

    elevations: list[float] = []
    for start in range(0, len(flat_lats), BATCH_SIZE):
        stop = start + BATCH_SIZE
        batch = fetch_batch(flat_lats[start:stop], flat_lons[start:stop])
        elevations.extend(batch)
        print(f"  fetched {min(stop, len(flat_lats))}/{len(flat_lats)}")

    terrain = TerrainModel(
        lats=lats,
        lons=lons,
        elevation_m=np.array(elevations, dtype=float).reshape(len(lats), len(lons)),
        source=SOURCE,
    )
    path = write_terrain_csv(OUTPUT_PATH, terrain)
    print(
        f"Terrain written to {path.relative_to(ROOT)} — "
        f"elevation {terrain.min_elevation_m:.0f}..{terrain.max_elevation_m:.0f} m "
        f"(relief {terrain.relief_m:.0f} m)"
    )


if __name__ == "__main__":
    main()
