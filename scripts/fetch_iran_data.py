"""دریافت دادهٔ باد سراسری ایران از Open-Meteo و اجرای همان QC خراسان.

روش — دقیقاً همان روش ``scripts/fetch_khorasan_data.py``: برای هر ایستگاه
(این‌بار شبکهٔ شهری سراسری به‌جای سه شهر خراسان) باد ۱۰ متری ۴۸ ساعت آینده
از API پیش‌بینی Open-Meteo گرفته می‌شود (بدون کلید)، سپس
``WindQualityControl`` با همان پیکربندی (``max_speed=100``) روی آن اجرا و
خروجی تمیز قالبِ پروژه ذخیره می‌شود: باد سطح واقعی است؛ نمایهٔ عمودی لایه‌ها
در ``viz.wind_field`` یک «فرض مدل» اعلام‌شده می‌ماند.

خروجی:

    data/iran_wind_qc_cleaned.csv   (timestamp,station,lat,lon,speed,direction)
    data/iran_qc_report.json

اجرا:

    python scripts/fetch_iran_data.py
"""

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qc.wind_qc import QCConfig, WindQualityControl, save_report_json  # noqa: E402

# شبکهٔ ایستگاه‌های شهریِ پراکنده روی کل کشور — پوشش شمال/جنوب/شرق/غرب/مرکز.
# سه ایستگاه خراسان با همان مختصات قبلی نگه داشته شده‌اند تا مسیر نمایشی
# مشهد→سبزوار دقیقاً روی گره‌های ایستگاهی بیفتد (corridor_lattice مختصات
# ایستگاه‌ها را به محورهای گراف اضافه می‌کند).
IRAN_STATIONS = [
    # شمال و شمال‌غرب
    {"name": "Tabriz", "lat": 38.080, "lon": 46.291},
    {"name": "Urmia", "lat": 37.552, "lon": 45.076},
    {"name": "Ardabil", "lat": 38.249, "lon": 48.293},
    {"name": "Rasht", "lat": 37.280, "lon": 49.583},
    {"name": "Zanjan", "lat": 36.673, "lon": 48.478},
    {"name": "Sari", "lat": 36.563, "lon": 53.060},
    {"name": "Gorgan", "lat": 36.842, "lon": 54.434},
    {"name": "Bojnurd", "lat": 37.475, "lon": 57.329},
    # غرب
    {"name": "Sanandaj", "lat": 35.311, "lon": 47.002},
    {"name": "Kermanshah", "lat": 34.314, "lon": 47.065},
    {"name": "Ilam", "lat": 33.637, "lon": 46.423},
    {"name": "Khorramabad", "lat": 33.487, "lon": 48.356},
    {"name": "Hamadan", "lat": 34.799, "lon": 48.515},
    # مرکز
    {"name": "Tehran", "lat": 35.689, "lon": 51.389},
    {"name": "Qom", "lat": 34.642, "lon": 50.879},
    {"name": "Arak", "lat": 34.092, "lon": 49.701},
    {"name": "Isfahan", "lat": 32.654, "lon": 51.668},
    {"name": "Kashan", "lat": 33.983, "lon": 51.436},
    {"name": "Shahrekord", "lat": 32.326, "lon": 50.864},
    {"name": "Yasuj", "lat": 30.668, "lon": 51.588},
    {"name": "Semnan", "lat": 35.576, "lon": 53.392},
    # شرق و خراسان
    {"name": "Mashhad", "lat": 36.297, "lon": 59.606},
    {"name": "Neyshabur", "lat": 36.213, "lon": 58.795},
    {"name": "Sabzevar", "lat": 36.215, "lon": 57.678},
    {"name": "Birjand", "lat": 32.866, "lon": 59.221},
    {"name": "Tabas", "lat": 33.595, "lon": 56.924},
    {"name": "Zabol", "lat": 31.031, "lon": 61.494},
    {"name": "Zahedan", "lat": 29.496, "lon": 60.862},
    # مرکز-جنوب
    {"name": "Yazd", "lat": 31.897, "lon": 54.368},
    {"name": "Kerman", "lat": 30.283, "lon": 57.078},
    {"name": "Rafsanjan", "lat": 30.407, "lon": 55.994},
    {"name": "Bam", "lat": 29.106, "lon": 58.357},
    # جنوب
    {"name": "Ahvaz", "lat": 31.320, "lon": 48.674},
    {"name": "Shiraz", "lat": 29.591, "lon": 52.584},
    {"name": "Bushehr", "lat": 28.923, "lon": 50.820},
    {"name": "Bandar Abbas", "lat": 27.184, "lon": 56.267},
    {"name": "Chabahar", "lat": 25.292, "lon": 60.643},
]


def fetch_openmeteo_wind(lat: float, lon: float) -> pd.DataFrame:
    """باد ۱۰ متری ۴۸ ساعت آیندهٔ یک نقطه — همان درخواست اسکریپت خراسان."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"hourly=wind_speed_10m,wind_direction_10m&"
        f"forecast_days=2"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AEROPATH/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode())

    hourly = data["hourly"]
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(hourly["time"]),
            "station": None,
            "lat": lat,
            "lon": lon,
            "speed": hourly["wind_speed_10m"],
            "direction": hourly["wind_direction_10m"],
        }
    )


def main() -> None:
    print(f"Fetching Iran wind data from Open-Meteo ({len(IRAN_STATIONS)} stations)...")
    frames: list[pd.DataFrame] = []
    for index, station in enumerate(IRAN_STATIONS, start=1):
        frame = fetch_openmeteo_wind(station["lat"], station["lon"])
        frame["station"] = station["name"]
        frames.append(frame)
        print(f"  [{index:02d}/{len(IRAN_STATIONS)}] {station['name']} — {len(frame)} hours")

    raw_df = pd.concat(frames, ignore_index=True)
    # ترتیب ستون‌ها هم‌سان با قالب پروژه (خراسان).
    raw_df = raw_df[["timestamp", "station", "lat", "lon", "speed", "direction"]]

    qc = WindQualityControl(QCConfig(max_speed=100.0))
    clean_df, report = qc.run(raw_df)

    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    clean_df.to_csv(data_dir / "iran_wind_qc_cleaned.csv", index=False)
    save_report_json(report, str(data_dir / "iran_qc_report.json"))

    print(
        f"Saved data/iran_wind_qc_cleaned.csv — rows: {len(clean_df)} "
        f"(raw {len(raw_df)}), stations: {clean_df['station'].nunique()}"
    )


if __name__ == "__main__":
    main()
