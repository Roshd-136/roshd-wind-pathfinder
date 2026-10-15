"""خروجی JSON فیلد باد و مسیر نمایشی برای پیش‌نمایش وب (frontend).

خروجی‌ها را در ``frontend/public/mock/`` می‌نویسد تا پیش‌نمایش dev بدون بک‌اند
هم میدان باد و مسیر واقعی این پروژه را نشان دهد:

    wind-field-50.json / wind-field-200.json / wind-field-500.json
        میدان باد سه لایهٔ رابط کاربری (۵۰/۲۰۰/۵۰۰ متر بالای زمین) در قالب
        دقیق ``WindField`` از ``api/openapi.yaml`` — بردارهای منظم روی شبکه.
    route-demo.json
        مسیر نمایشی R2 صحنه (سریع‌ترین، A*) بین مبدأ/مقصد دموی کریدور، در قالب
        ``RouteResult`` قرارداد.
    wind-layers.json
        خروجی ``GET /wind-layers`` (سه لایهٔ بالا).

هشدار صداقت داده
-----------------
باد ایستگاه‌ها **واقعی** است (``data/khorasan_wind_qc_cleaned.csv``، ساعت با
بیشینهٔ باد از ``select_scene_hour``) و درون‌یابی با همان IDW خط لولهٔ
بصری‌سازی است (``viz.wind_field``). نمایهٔ عمودی (ضریب سرعت/چرخش جهت در
ارتفاع‌های ۵۰/۲۰۰/۵۰۰ متر) «فرض مدل» اعلام‌شدهٔ همان ماژول است
(``profile_at``) — نه اندازه‌گیری. مسیر نمایشی با ``WindRouter`` واقعی روی
گراف چندلایهٔ سطوح پرواز MSL (با زمین‌مرجع DEM) محاسبه می‌شود؛ همان مسیری که
در صحنهٔ سه‌بعدی پذیرش‌آزمایی شده است.

اجرا:

    python scripts/export_web_wind_fixture.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pathfinding.effort import MotorEffortConfig  # noqa: E402
from pathfinding.graph import VerticalCostConfig  # noqa: E402
from viz.scene3d import (  # noqa: E402
    DEMO_DESTINATION,
    DEMO_ORIGIN,
    MIN_TERRAIN_CLEARANCE_M,
    VIZ_AIRCRAFT,
    RouteSpec,
    build_routes,
)
from viz.terrain import TERRAIN_CSV_PATH, load_terrain  # noqa: E402
from viz.wind_field import (  # noqa: E402
    CORRIDOR_BBOX,
    build_level_fields,
    build_multi_layer_graph,
    corridor_lattice,
    interpolate_layer_field,
    load_station_winds,
    profile_at,
    select_scene_hour,
)

WIND_CSV_PATH = ROOT / "data" / "khorasan_wind_qc_cleaned.csv"
OUTPUT_DIR = ROOT / "frontend" / "public" / "mock"

# ارتفاع‌های «بالای زمین» سه لایهٔ رابط کاربری (میان‌باند همان چک‌باکس‌ها:
# سطحی ۰-۵۰، میانی ۵۰-۲۰۰، بالا ۲۰۰-۵۰۰).
UI_LAYER_AGL_M: tuple[float, ...] = (50.0, 200.0, 500.0)

# شبکهٔ منظم خروجی وب — ریزتر از شبکهٔ گراف تا رنگ ملایم درآید.
FIELD_LAT_STEP = 0.03
FIELD_LON_STEP = 0.05


def _regular_lattice() -> tuple[np.ndarray, np.ndarray]:
    """شبکهٔ کاملاً منظم روی کریدور (بدون نقطهٔ اضافهٔ ایستگاه‌ها)."""
    lats = np.arange(
        CORRIDOR_BBOX["lat_min"],
        CORRIDOR_BBOX["lat_max"] + FIELD_LAT_STEP / 2,
        FIELD_LAT_STEP,
    )
    lons = np.arange(
        CORRIDOR_BBOX["lon_min"],
        CORRIDOR_BBOX["lon_max"] + FIELD_LON_STEP / 2,
        FIELD_LON_STEP,
    )
    return lats, lons


def export_fields(stations: pd.DataFrame, output_dir: Path) -> None:
    """میدان باد سه لایهٔ UI را در قالب ``WindField`` قرارداد می‌نویسد."""
    lats, lons = _regular_lattice()
    for agl_m in UI_LAYER_AGL_M:
        scale, rotation = profile_at(agl_m)
        field = interpolate_layer_field(
            stations, (float(agl_m), float(scale), float(rotation)), lats, lons
        )
        lon_mesh, lat_mesh = np.meshgrid(field.lons, field.lats)
        payload = {
            "altitude_m": float(agl_m),
            "vectors": [
                {
                    "lat": round(float(la), 4),
                    "lon": round(float(lo), 4),
                    "speed_mps": round(float(sp), 2),
                    "direction_deg": round(float(di), 1),
                }
                for la, lo, sp, di in zip(
                    lat_mesh.ravel(),
                    lon_mesh.ravel(),
                    field.speed_mps.ravel(),
                    field.direction_deg.ravel(),
                    strict=True,
                )
            ],
        }
        path = output_dir / f"wind-field-{int(agl_m)}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(f"  {path.name}: {len(payload['vectors'])} vectors")


def export_layers(output_dir: Path) -> None:
    """خروجی ``GET /wind-layers`` برای سه لایهٔ UI."""
    payload = [
        {
            "altitude_m": float(agl_m),
            "unit": "mps",
            "bbox": [
                CORRIDOR_BBOX["lon_min"],
                CORRIDOR_BBOX["lat_min"],
                CORRIDOR_BBOX["lon_max"],
                CORRIDOR_BBOX["lat_max"],
            ],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        for agl_m in UI_LAYER_AGL_M
    ]
    (output_dir / "wind-layers.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  wind-layers.json: {len(payload)} layers")


def export_demo_route(stations: pd.DataFrame, output_dir: Path) -> None:
    """مسیر نمایشی R2 (سریع‌ترین، A*) را در قالب ``RouteResult`` می‌نویسد."""
    terrain = load_terrain(TERRAIN_CSV_PATH)
    graph_lats, graph_lons = corridor_lattice(stations)
    level_lon_mesh, level_lat_mesh = np.meshgrid(graph_lons, graph_lats)
    corridor_ground = terrain.elevation_at(level_lat_mesh, level_lon_mesh).reshape(
        level_lat_mesh.shape
    )

    def ground_elevation_at(lat: float, lon: float) -> float:
        return float(np.atleast_1d(terrain.elevation_at(lat, lon))[0])

    fields = build_level_fields(stations, corridor_ground)
    multi_graph = build_multi_layer_graph(
        fields,
        config=VIZ_AIRCRAFT,
        criterion="time",
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
        edge_terrain_sampler=ground_elevation_at,
    )
    specs = (
        RouteSpec(
            key="demo",
            label="نمایشی — سریع‌ترین",
            short="نمایشی",
            criterion="time",
            algorithm="astar",
            color="#3b82f6",
        ),
    )
    routes = build_routes(
        multi_graph,
        VIZ_AIRCRAFT,
        origin=DEMO_ORIGIN,
        destination=DEMO_DESTINATION,
        specs=specs,
        effort_config=MotorEffortConfig(),
        vertical_config=VerticalCostConfig(),
        ground_elevation_at=ground_elevation_at,
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
    )
    result = routes["demo"]
    payload = {
        "route_id": "demo-khorasan-fastest",
        "path": [
            {"lat": round(float(la), 4), "lon": round(float(lo), 4)}
            for la, lo in result.path
        ],
        "layer_altitude_m": float(result.layer_altitude),
        "algorithm": "a_star",
        "criterion": "time",
        "total_distance_km": round(float(result.total_distance_km), 2),
        "estimated_time_hours": round(float(result.estimated_time_hours), 2),
        "total_cost": round(float(result.total_cost), 3),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "route-demo.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"  route-demo.json: {len(payload['path'])} points, "
        f"{payload['total_distance_km']} km @ {payload['layer_altitude_m']} m"
    )


def main() -> None:
    print("Loading real station winds (peak-wind hour)...")
    raw = pd.read_csv(WIND_CSV_PATH)
    hour = select_scene_hour(raw)
    stations = load_station_winds(WIND_CSV_PATH, timestamp=hour)
    print(f"  {len(stations)} stations @ {hour}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Exporting wind fields...")
    export_fields(stations, OUTPUT_DIR)
    export_layers(OUTPUT_DIR)
    print("Computing demo route (real WindRouter on MSL multi-layer graph)...")
    export_demo_route(stations, OUTPUT_DIR)
    print(f"Done -> {OUTPUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
