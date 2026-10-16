"""
Wind Layers Router — GET /wind-layers, GET /wind-layers/{altitudeM}/field.

Provides access to multi-altitude wind data layers using real station data
and interpolation (matching FLIGHT_LEVELS_MSL from routing_scene).

هشدار صداقت داده: باد ایستگاه‌ها واقعی است، ولی پروفیل عمودی (ضریب سرعت/
چرخش بر ارتفاع) یک «فرض مدل» سنتزی در ``viz.wind_field`` است — پاسخ این روتر
میدان‌های سنتزیِ برساخته از باد سطح ۱۰ متر است.
"""
import sys
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Add src to path for viz imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from viz.terrain import TERRAIN_CSV_PATH, load_terrain
from viz.wind_field import (
    CORRIDOR_BBOX,
    FLIGHT_LEVELS_MSL,
    GRAPH_LAT_STEP,
    build_level_fields,
    corridor_lattice,
    load_station_winds,
    select_scene_hour,
)

router = APIRouter(prefix="/wind-layers", tags=["wind-layers"])

# Cache for station winds and level fields — computed once per process.
# ورودی‌ها (CSV ایستگاه‌ها و DEM) در زمان اجرا ثابت‌اند، پس کش بی‌پایان درست است؛
# قبلاً متغیرها اعلام شده بودند ولی هرگز پر نمی‌شدند و هر GET کل خط لولهٔ
# CSV + IDW + ساخت لایه‌ها را از نو اجرا می‌کرد.
_station_cache: tuple[pd.Timestamp, pd.DataFrame] | None = None
_level_fields_cache: list | None = None

# مسیر داده به‌صورت مطلق — مسیر نسبی «data/...» فقط وقتی CWD ریشهٔ مخزن باشد
# کار می‌کرد و زیر uvicorn با کاری دیگر ۴۰۴/فایل‌نیافت می‌داد.
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _get_cached_fields():
    """Get or compute cached station winds and level fields."""
    global _station_cache, _level_fields_cache

    if _level_fields_cache is not None and _station_cache is not None:
        return _level_fields_cache, _station_cache[0]

    csv_path = _DATA_DIR / "khorasan_wind_qc_cleaned.csv"
    raw = pd.read_csv(csv_path)
    hour = select_scene_hour(raw)
    stations = load_station_winds(csv_path, timestamp=hour)

    terrain = load_terrain(TERRAIN_CSV_PATH)
    graph_lats, graph_lons = corridor_lattice(stations)
    level_lon_mesh, level_lat_mesh = np.meshgrid(graph_lons, graph_lats)
    corridor_ground = terrain.elevation_at(level_lat_mesh, level_lon_mesh).reshape(
        level_lat_mesh.shape
    )

    fields = build_level_fields(stations, corridor_ground)
    _station_cache = (hour, stations)
    _level_fields_cache = fields
    return fields, hour


class WindVector(BaseModel):
    lat: float
    lon: float
    speed_mps: float
    direction_deg: float


class WindField(BaseModel):
    altitude_m: float
    vectors: list[WindVector]


class WindLayerSummary(BaseModel):
    altitude_m: float
    timestamp: str
    source: Literal["station_interpolated"]
    coverage_bbox: list[float]
    resolution_deg: float


class WindLayersList(BaseModel):
    layers: list[WindLayerSummary]
    available_altitudes_m: list[float]
    latest_timestamp: str


@router.get("", response_model=WindLayersList)
async def list_wind_layers(
    timestamp: str | None = Query(None, description="ISO8601 timestamp, defaults to latest"),
    bbox: str | None = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
):
    """List available wind layers for a given time and bounding box."""
    # Use FLIGHT_LEVELS_MSL matching routing_scene
    fields, hour = _get_cached_fields()

    layers = [
        WindLayerSummary(
            altitude_m=float(alt),
            timestamp=hour.isoformat(),
            source="station_interpolated",
            coverage_bbox=[
                CORRIDOR_BBOX["lon_min"],
                CORRIDOR_BBOX["lat_min"],
                CORRIDOR_BBOX["lon_max"],
                CORRIDOR_BBOX["lat_max"],
            ],
            # شبکهٔ گراف دوگام است (۰٫۰۵° عرض × ۰٫۱۰° طول)؛ اسکما یک عدد
            # می‌خواهد — ریزترین گام گزارش می‌شود.
            resolution_deg=float(GRAPH_LAT_STEP),
        )
        for alt in FLIGHT_LEVELS_MSL
    ]

    return WindLayersList(
        layers=layers,
        available_altitudes_m=[float(a) for a in FLIGHT_LEVELS_MSL],
        latest_timestamp=hour.isoformat(),
    )


@router.get("/{altitude_m}/field", response_model=WindField)
async def get_wind_field(
    altitude_m: float,
    timestamp: str | None = Query(None),
    bbox: str | None = Query(None),
):
    """Get full wind vector grid for a layer (for visualization)."""
    fields, hour = _get_cached_fields()

    # Find the matching field
    field = next((f for f in fields if abs(f.altitude - altitude_m) < 1.0), None)
    if field is None:
        raise HTTPException(status_code=404, detail=f"Layer at {altitude_m}m not found")

    # Convert LayerField to WindField for API response
    lat_mesh, lon_mesh = np.meshgrid(field.lats, field.lons, indexing='ij')

    vectors = [
        WindVector(
            lat=round(float(la), 4),
            lon=round(float(lo), 4),
            speed_mps=round(float(sp), 2),
            direction_deg=round(float(di), 1),
        )
        for la, lo, sp, di in zip(
            lat_mesh.ravel(),
            lon_mesh.ravel(),
            field.speed_mps.ravel(),
            field.direction_deg.ravel(),
            strict=True,
        )
    ]

    return WindField(
        altitude_m=field.altitude,
        vectors=vectors,
    )
