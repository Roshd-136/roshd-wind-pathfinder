"""دریافت ارتفاع زمین (DEM) و ذخیره آن در ``data/``.

اجرا:

    # کریدور مشهد–سبزوار (پیش‌فرض — همان فایل مرجع آزمون‌ها)
    python scripts/fetch_terrain_data.py

    # سراسری ایران، سلول ۱۰ کیلومتری
    python scripts/fetch_terrain_data.py --bbox iran --output data/iran_terrain.csv

خروجی: ``data/khorasan_terrain.csv`` (شبکه منظم ۱۹×۳۷ نقطه) یا
``data/iran_terrain.csv`` (شبکه ۱۶۸×۱۹۸ نقطه)، ارتفاع بر حسب متر.

منبع: سرویس Elevation اوپن‌متیو (بر پایه DEM کپرنیکوس GLO-90). این سرویس
نیازی به کلید ندارد و ارتفاع را در هر نقطه از مختصات می‌دهد. چون صحنه سه‌بعدی
باید آفلاین و تکرارپذیر باشد، نتیجه یک‌بار گرفته و ذخیره می‌شود؛ صحنه‌سازی هم
از همین فایل می‌خواند و به شبکه وابسته نیست.
"""

from __future__ import annotations

import argparse
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
    IRAN_TERRAIN_CELL_KM,
    IRAN_TERRAIN_CSV_PATH,
    TERRAIN_CELL_KM,
    TerrainModel,
    terrain_grid,
    write_terrain_csv,
)
from viz.wind_field import CORRIDOR_BBOX, IRAN_BBOX  # noqa: E402

OUTPUT_PATH = ROOT / "data" / "khorasan_terrain.csv"
ENDPOINT = "https://api.open-meteo.com/v1/elevation"
SOURCE = "Open-Meteo Elevation API (Copernicus DEM GLO-90)"
# سرویس در هر درخواست حداکثر ۱۰۰ مختصات می‌پذیرد.
BATCH_SIZE = 100
MAX_ATTEMPTS = 6

# کادرهای آماده — نام کوتاه روی خط فرمان کافی است.
PRESET_BBOXES = {"khorasan": CORRIDOR_BBOX, "iran": IRAN_BBOX}


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
        except urllib.error.HTTPError as error:
            last_error = error
            if attempt >= MAX_ATTEMPTS:
                break
            # ۴۲۹ = سهمیهٔ نرخ درخواست. سرویس سرصفحهٔ ``Retry-After`` می‌دهد؛
            # صبر کوتاه (۲ ثانیه) فقط دوباره ۴۲۹ می‌گیرد و درخواست را می‌سوزاند.
            if error.code == 429:
                retry_after = float(error.headers.get("Retry-After", 0) or 0)
                wait = max(retry_after, 10.0 * attempt)
            else:
                wait = 2.0 * attempt
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = error
            if attempt < MAX_ATTEMPTS:
                time.sleep(2.0 * attempt)
    raise RuntimeError(f"Elevation request failed after {MAX_ATTEMPTS} attempts: {last_error}")


def _parse_bbox(raw: str) -> tuple[dict[str, float], str]:
    """کادر را از نام آماده یا ``lat_min,lat_max,lon_min,lon_max`` می‌خواند."""
    key = raw.strip().lower()
    if key in PRESET_BBOXES:
        return dict(PRESET_BBOXES[key]), key
    parts = [piece.strip() for piece in raw.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "bbox باید یکی از نام‌های khorasan/iran یا چهار عدد "
            "lat_min,lat_max,lon_min,lon_max باشد."
        )
    lat_min, lat_max, lon_min, lon_max = (float(piece) for piece in parts)
    if not (lat_min < lat_max and lon_min < lon_max):
        raise argparse.ArgumentTypeError("ترتیب کادر باید صعودی باشد.")
    return (
        {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "custom",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "دریافت DEM از سرویس Elevation اوپن‌متیو و ذخیره در CSV پروژه. "
            "پیش‌فرض همان کریدور خراسان است؛ برای داده سراسری ایران: "
            "--bbox iran --output data/iran_terrain.csv"
        )
    )
    parser.add_argument(
        "--bbox",
        default="khorasan",
        help="khorasan | iran | lat_min,lat_max,lon_min,lon_max (پیش‌فرض: khorasan)",
    )
    parser.add_argument(
        "--cell-km",
        type=float,
        default=None,
        help="اندازهٔ سلول بر حسب کیلومتر (پیش‌فرض: ۲٫۵ کریدور، ۱۰ ایران)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="مسیر فایل خروجی (پیش‌فرض: data/khorasan_terrain.csv یا data/iran_terrain.csv)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="مکث بین دسته‌ها بر حسب ثانیه (پیش‌فرض: ۱ — سهمیهٔ نرخ سرویس)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="چک‌پوینت دسته‌های قبلی را نادیده بگیر و از صفر بگیر",
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
        output_path = OUTPUT_PATH

    lats, lons = terrain_grid(bbox=bbox, cell_km=cell_km)
    lon_mesh, lat_mesh = np.meshgrid(lons, lats)
    flat_lats = lat_mesh.ravel()
    flat_lons = lon_mesh.ravel()

    print(
        f"Fetching terrain for {len(flat_lats)} points "
        f"({len(lats)}x{len(lons)} grid, ~{cell_km:g} km square cells) "
        f"from {SOURCE}..."
    )

    # — ذخیرهٔ پیشرفت به‌صورت دسته‌ای (resume) —
    #
    # سرویس Elevation سهمیهٔ نرخ دارد و اجرای ~۳۳۳ درخواستی می‌تواند وسط کار
    # قطع شود (۴۲۹/قطعی شبکه). هر دستهٔ موفق در یک فایل کنار خروجی نوشته
    # می‌شود تا اجرای بعدی از همان‌جا ادامه دهد، نه از صفر. فایل پس از
    # نوشتن کامل CSV حذف می‌شود؛ با ``--fresh`` نادیده گرفته می‌شود.
    partial_path = output_path.with_name(output_path.name + ".partial.jsonl")
    completed: dict[int, list[float]] = {}
    if partial_path.exists() and not args.fresh:
        for line in partial_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            completed[int(record["batch"])] = [float(value) for value in record["elevation"]]
        print(f"Resuming — {len(completed)} batches already fetched from {partial_path.name}.")
    elif args.fresh and partial_path.exists():
        partial_path.unlink()

    elevations: list[float] = []
    with partial_path.open("a", encoding="utf-8") as sink:
        for start in range(0, len(flat_lats), BATCH_SIZE):
            stop = min(start + BATCH_SIZE, len(flat_lats))
            index = start // BATCH_SIZE
            if index in completed:
                elevations.extend(completed[index])
                continue
            batch = fetch_batch(flat_lats[start:stop], flat_lons[start:stop])
            completed[index] = batch
            elevations.extend(batch)
            sink.write(json.dumps({"batch": index, "elevation": batch}) + "\n")
            sink.flush()
            print(f"  fetched {min(stop, len(flat_lats))}/{len(flat_lats)}")
            if stop < len(flat_lats) and args.sleep > 0:
                time.sleep(args.sleep)

    if len(elevations) != len(flat_lats):
        raise RuntimeError(
            f"Expected {len(flat_lats)} elevations, got {len(elevations)} — "
            f"checkpoint {partial_path} is incomplete."
        )
    terrain = TerrainModel(
        lats=lats,
        lons=lons,
        elevation_m=np.array(elevations, dtype=float).reshape(len(lats), len(lons)),
        source=SOURCE,
    )
    path = write_terrain_csv(output_path, terrain)
    # چک‌پوینت فقط پس از نوشتن موفق CSV پاک می‌شود.
    if partial_path.exists():
        partial_path.unlink()
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
