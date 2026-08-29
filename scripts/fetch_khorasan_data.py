"""Fetch real wind data from Open-Meteo API for Khorasan region and run QC."""

import json
from pathlib import Path
import urllib.request
import pandas as pd
from roshd_wind_pathfinder.qc.wind_qc import QCConfig, WindQualityControl, save_report_json

KHORASAN_STATIONS = [
    {"name": "Mashhad", "lat": 36.297, "lon": 59.606},
    {"name": "Neyshabur", "lat": 36.213, "lon": 58.795},
    {"name": "Sabzevar", "lat": 36.215, "lon": 57.678},
]


def fetch_openmeteo_wind(lat: float, lon: float) -> pd.DataFrame:
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"hourly=wind_speed_10m,wind_direction_10m&"
        f"forecast_days=2"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AEROPATH/1.0"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())

    hourly = data["hourly"]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(hourly["time"]),
        "lat": lat,
        "lon": lon,
        "speed": hourly["wind_speed_10m"],
        "direction": hourly["wind_direction_10m"],
    })


def main():
    print("Fetching Khorasan wind data from Open-Meteo...")
    dfs = [fetch_openmeteo_wind(s["lat"], s["lon"]) for s in KHORASAN_STATIONS]
    raw_df = pd.concat(dfs, ignore_index=True)

    qc = WindQualityControl(QCConfig(max_speed=100.0))
    clean_df, report = qc.run(raw_df)

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    clean_df.to_csv(data_dir / "khorasan_wind_qc_cleaned.csv", index=False)
    save_report_json(report, str(data_dir / "khorasan_qc_report.json"))

    print(f"Data saved to data/khorasan_wind_qc_cleaned.csv. Total fetched: {len(raw_df)}")


if __name__ == "__main__":
    main()
