"""تولید صحنه سه‌بعدی تعاملی مسیریابی باد.

خروجی یک فایل HTML خودکفا است که آفلاین (بدون CDN و بدون توکن نقشه) باز می‌شود:

    docs/assets/routing_scene.html

اجرا:

    python scripts/generate_routing_scene.py

صحنه شامل سطح زمین (رنگ = بهترین لایه ارتفاعی)، پیکان‌های باد هر لایه با
tooltip، و مسیرها است: مسیرهای روی گراف سه‌بعدی (کم‌مصرف/کم‌پیچ‌وخم،
سریع‌ترین، کوتاه‌ترین، مقید به سطح پایین و مقید به سطح بالا) به‌علاوه خانوادهٔ
«بادسواری» که روی گراف حساب نمی‌شود: مسیر را سمت‌به‌سمت باد می‌برد و فرودش
در حال حرکت است. خانوادهٔ بادسواری چند مسیر است، نه یکی: همان مسیر با دالان
‌های صریح مختلف تا مبادلهٔ «موازی باد ↔ مسافت» دیده شود.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viz.scene3d import write_scene  # noqa: E402

DATA_PATH = ROOT / "data" / "khorasan_wind_qc_cleaned.csv"
OUTPUT_PATH = ROOT / "docs" / "assets" / "routing_scene.html"


def main() -> None:
    print("Building 3D routing scene from real Khorasan station data...")
    path, routes = write_scene(OUTPUT_PATH, DATA_PATH)

    size_mb = path.stat().st_size / 1e6
    print(f"Scene written to {path.relative_to(ROOT)} ({size_mb:.1f} MB, self-contained)")
    print()
    print(f"{'route':6} {'layer(m)':>9} {'dist(km)':>9} {'time(h)':>8} "
          f"{'energy':>7} {'tailwind':>9} {'turns':>6}")
    for key, result in routes.items():
        print(
            f"{key:6} {result.layer_altitude:9.0f} {result.total_distance_km:9.1f} "
            f"{result.estimated_time_hours:8.3f} {result.total_energy_index:7.3f} "
            f"{result.tailwind_leg_fraction * 100:8.0f}% {result.heading_changes:6d}"
        )


if __name__ == "__main__":
    main()
