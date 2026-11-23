"""ساخت DEM سراسری از کاشی‌های Terrarium (SRTM/GMTED) و ذخیره در قالب CSV پروژه.

چرا این منبع؟
-------------
روش اصلی (``scripts/fetch_terrain_data.py``) از سرویس Elevation اوپن‌متیو
(کپرنیکوس GLO-90) می‌خواند. آن سرویس سهمیهٔ روزانهٔ ۱۰٬۰۰۰ درخواست برای هر IP
دارد و IP مشترک پروکسی در میانهٔ کار تمام شد. این اسکریپت **همان شبکهٔ ۱۰
کیلومتری** را از کاشی‌های عمومی Terrarium (ترکیب SRTM/GMTED/ETOPO1) می‌سازد؛
خروجی دقیقاً همان قالب ``data/iran_terrain.csv`` است، پس API و صحنهٔ سه‌بعدی
تفاوتی نمی‌بینند. منبع در هدر CSV و سند تسک صادقانه ذکر می‌شود. هر زمان سهمیهٔ
اوپن‌متیو آزاد شد، ``fetch_terrain_data.py --bbox iran`` همین فایل را با GLO-90
بازمی‌سازد.

روش
---
۱) کاشی‌های ۲۵۶×۲۵۶ پیکسلی وب‌مرکاتور که کادر را می‌پوشانند دانلود می‌شوند
   (با کش محلی، قابل ادامه بین اجراها)؛
۲) کاشی‌ها به یک موزاییک پیوسته چسبانده می‌شوند؛
۳) ارتفاع هر پیکسل با فرمول Terrarium رمزگشایی می‌شود:
   ``R * 256 + G + B / 256 - 32768``؛
۴) ارتفاع مرکز هر سلول شبکهٔ ۱۰ کیلومتری با درون‌یابی دوخطی نمونه‌برداری
   می‌شود. ارتفاع آب‌ها (خلیج فارس/دریای عمان/خزر) روی صفر بسته می‌شود تا مثل
   رفتار سرویس Elevation، سطح دریا مبنای ارتفاع بالای زمین باشد.

اجرا:

    python scripts/fetch_terrain_tiles.py
    python scripts/fetch_terrain_tiles.py --bbox iran --cell-km 10 --zoom 8
"""

from __future__ import annotations

import argparse
import io
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viz.terrain import (  # noqa: E402
    IRAN_TERRAIN_CELL_KM,
    IRAN_TERRAIN_CSV_PATH,
    TERRAIN_CELL_KM,
    TerrainModel,
    terrain_grid,
    write_terrain_csv,
)
from viz.wind_field import CORRIDOR_BBOX, IRAN_BBOX  # noqa: E402

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
TILE_SIZE = 256
MAX_ATTEMPTS = 5
# مرزهای کادرهای آماده — همان دو کادر ``wind_field``.
PRESET_BBOXES = {"iran": IRAN_BBOX, "khorasan": CORRIDOR_BBOX}


def _parse_bbox(raw: str) -> tuple[dict[str, float], str]:
    """کادر را از نام آماده یا ``lat_min,lat_max,lon_min,lon_max`` می‌خواند."""
    key = raw.strip().lower()
    if key in PRESET_BBOXES:
        return dict(PRESET_BBOXES[key]), key
    parts = [piece.strip() for piece in raw.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "bbox باید یکی از نام‌های iran/khorasan یا چهار عدد "
            "lat_min,lat_max,lon_min,lon_max باشد."
        )
    lat_min, lat_max, lon_min, lon_max = (float(piece) for piece in parts)
    if not (lat_min < lat_max and lon_min < lon_max):
        raise argparse.ArgumentTypeError("ترتیب کادر باید صعودی باشد.")
    return (
        {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "custom",
    )


def mercator_pixel(
    lat: float | np.ndarray, lon: float | np.ndarray, zoom: int
) -> tuple[np.ndarray, np.ndarray]:
    """مختصات پیوستهٔ پیکسلی وب‌مرکاتور برای یک نقطه یا آرایهٔ نقاط."""
    scale = TILE_SIZE * (2**zoom)
    lon_arr = np.asarray(lon, dtype=float)
    lat_rad = np.radians(np.asarray(lat, dtype=float))
    x = (lon_arr + 180.0) / 360.0 * scale
    y = (1.0 - np.log(np.tan(lat_rad) + 1.0 / np.cos(lat_rad)) / np.pi) / 2.0 * scale
    return x, y


def _fetch_tile(zoom: int, x: int, y: int, cache_dir: Path) -> np.ndarray:
    """یک کاشی RGB را از کش محلی می‌خواند یا دانلود می‌کند (با تلاش مجدد)."""
    cache_path = cache_dir / str(zoom) / str(x) / f"{y}.png"
    if cache_path.exists():
        with Image.open(cache_path) as image:
            return np.asarray(image.convert("RGB"))
    url = TILE_URL.format(z=zoom, x=x, y=y)
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                payload = response.read()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(payload)
            with Image.open(io.BytesIO(payload)) as image:
                return np.asarray(image.convert("RGB"))
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt < MAX_ATTEMPTS:
                time.sleep(2.0 * attempt)
    raise RuntimeError(f"Tile {zoom}/{x}/{y} failed after {MAX_ATTEMPTS} attempts: {last_error}")


def _decode_terrarium(rgb: np.ndarray) -> np.ndarray:
    """رمزگشایی ارتفاع Terrarium از آرایهٔ RGB (شکل ``(..., 3)``)."""
    red, green, blue = (rgb[..., index].astype(np.float64) for index in range(3))
    return red * 256.0 + green + blue / 256.0 - 32768.0


def build_terrain(
    bbox: dict[str, float],
    cell_km: float,
    zoom: int,
    cache_dir: Path,
) -> TerrainModel:
    """موزاییک کاشی‌ها را می‌سازد و DEM را روی شبکهٔ پروژه نمونه‌برداری می‌کند."""
    lats, lons = terrain_grid(bbox=bbox, cell_km=cell_km)

    # کادر پیکسلی: عرض جغرافیایی بیشتر ⇒ y کوچک‌تر (شمال بالای تصویر).
    x_left, y_top = mercator_pixel(bbox["lat_max"], bbox["lon_min"], zoom)
    x_right, y_bottom = mercator_pixel(bbox["lat_min"], bbox["lon_max"], zoom)
    tile_x0 = int(math.floor(float(x_left) / TILE_SIZE))
    tile_x1 = int(math.floor(float(x_right) / TILE_SIZE))
    tile_y0 = int(math.floor(float(y_top) / TILE_SIZE))
    tile_y1 = int(math.floor(float(y_bottom) / TILE_SIZE))

    n_cols = tile_x1 - tile_x0 + 1
    n_rows = tile_y1 - tile_y0 + 1
    mosaic = np.empty((n_rows * TILE_SIZE, n_cols * TILE_SIZE, 3), dtype=np.uint8)
    total = n_rows * n_cols
    done = 0
    for row, tile_y in enumerate(range(tile_y0, tile_y1 + 1)):
        for col, tile_x in enumerate(range(tile_x0, tile_x1 + 1)):
            tile = _fetch_tile(zoom, tile_x, tile_y, cache_dir)
            if tile.shape != (TILE_SIZE, TILE_SIZE, 3):
                raise ValueError(f"Tile {zoom}/{tile_x}/{tile_y} has shape {tile.shape}")
            mosaic[
                row * TILE_SIZE : (row + 1) * TILE_SIZE,
                col * TILE_SIZE : (col + 1) * TILE_SIZE,
            ] = tile
            done += 1
            if done % 20 == 0 or done == total:
                print(f"  tiles {done}/{total}")

    elevation_grid = _decode_terrarium(mosaic)

    # نمونه‌برداری دوخطی در مرکز هر سلول شبکه — همان چیزی که یک پرس‌وجوی نقطه‌ای
    # از سرویس Elevation می‌داد.
    lon_mesh, lat_mesh = np.meshgrid(lons, lats)
    pixel_x, pixel_y = mercator_pixel(lat_mesh.ravel(), lon_mesh.ravel(), zoom)
    sample_x = pixel_x - tile_x0 * TILE_SIZE
    sample_y = pixel_y - tile_y0 * TILE_SIZE
    elevation = map_coordinates(
        elevation_grid, [sample_y, sample_x], order=1, mode="nearest"
    ).reshape(lat_mesh.shape)
    # آب‌ها روی سطح دریا بسته می‌شوند؛ Terrarium در دریا عمق (منفی) می‌دهد و
    # سرویس Elevation اوپن‌متیو صفر برمی‌گرداند — برای AGL و رنگ‌آمیزی صحنه،
    # صفر مبنای درست است.
    elevation = np.maximum(elevation, 0.0)
    if not np.isfinite(elevation).all():
        raise ValueError("DEM has non-finite elevations — a tile is probably corrupt.")

    return TerrainModel(
        lats=lats,
        lons=lons,
        elevation_m=elevation,
        source=(
            "Terrarium terrain tiles (SRTM/GMTED blend), "
            f"zoom {zoom}, sampled on a {cell_km:g} km grid"
        ),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "ساخت DEM از کاشی‌های Terrarium (SRTM/GMTED). پیش‌فرض: کل ایران با "
            "سلول ۱۰ کیلومتر. جایگزین fetch_terrain_data.py وقتی سهمیهٔ "
            "Open-Meteo تمام است."
        )
    )
    parser.add_argument(
        "--bbox",
        default="iran",
        help="iran | khorasan | lat_min,lat_max,lon_min,lon_max (پیش‌فرض: iran)",
    )
    parser.add_argument(
        "--cell-km",
        type=float,
        default=None,
        help="اندازهٔ سلول بر حسب کیلومتر (پیش‌فرض: ۱۰ ایران، ۲٫۵ کریدور)",
    )
    parser.add_argument(
        "--zoom",
        type=int,
        default=8,
        help="زوم کاشی‌های وب‌مرکاتور (۸ ≈ ۵۰۰ متر/پیکسل — پیش‌فرض)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="مسیر فایل خروجی (پیش‌فرض: data/iran_terrain.csv یا data/khorasan_terrain.csv)",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(ROOT / "tmp" / "terrain_tiles"),
        help="پوشهٔ کش کاشی‌ها (پیش‌فرض: tmp/terrain_tiles)",
    )
    args = parser.parse_args(argv)

    try:
        bbox, preset = _parse_bbox(args.bbox)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))

    if args.cell_km is not None:
        cell_km = args.cell_km
    elif preset == "iran":
        cell_km = IRAN_TERRAIN_CELL_KM
    else:
        cell_km = TERRAIN_CELL_KM

    if args.output is not None:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
    elif preset == "iran":
        output_path = IRAN_TERRAIN_CSV_PATH
    else:
        output_path = ROOT / "data" / "khorasan_terrain.csv"

    if args.zoom < 5 or args.zoom > 14:
        parser.error("zoom باید بین ۵ و ۱۴ باشد.")

    print(f"Building terrain from Terrarium tiles — bbox {preset}, cell {cell_km:g} km")
    terrain = build_terrain(
        bbox=bbox,
        cell_km=cell_km,
        zoom=args.zoom,
        cache_dir=Path(args.cache_dir),
    )
    path = write_terrain_csv(output_path, terrain)
    try:
        shown = path.relative_to(ROOT)
    except ValueError:
        shown = path
    print(
        f"Terrain written to {shown} — "
        f"elevation {terrain.min_elevation_m:.0f}..{terrain.max_elevation_m:.0f} m "
        f"(relief {terrain.relief_m:.0f} m)"
    )


if __name__ == "__main__":
    main()
