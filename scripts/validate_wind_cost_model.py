"""اسکریپت اعتبارسنجی مدل هزینه باد روی داده واقعی خراسان.

این اسکریپت مدل هزینه (``pathfinding.cost.compute_edge_cost``) را روی حداقل
سه جفت مبدأ/مقصد واقعی (بین سه ایستگاه خراسان: مشهد، نیشابور، سبزوار) اجرا
می‌کند و برای هر یال، هزینه سه معیار بهینگی را روی تمام رکوردهای واقعی ساعتی
موجود در ``data/khorasan_wind_qc_cleaned.csv`` محاسبه می‌کند (باد اندازه‌گیری‌شده
در ایستگاه مبدأ به‌عنوان شرط باد آن یال در آن ساعت در نظر گرفته می‌شود).

هیچ مقدار فرضی/mock استفاده نمی‌شود: سرعت و جهت باد مستقیماً از داده واقعی
QC-شده خوانده می‌شود.

اجرا:
    python scripts/validate_wind_cost_model.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pandas as pd

from pathfinding.cost import CostModelConfig, InfeasibleEdgeError, compute_edge_cost

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "khorasan_wind_qc_cleaned.csv"

# Three real origin/destination station pairs (station coordinates come
# directly from the dataset, not hardcoded guesses).
EDGE_PAIRS = [
    ("Mashhad", "Neyshabur"),
    ("Neyshabur", "Sabzevar"),
    ("Mashhad", "Sabzevar"),
]


def _station_coords(df: pd.DataFrame) -> dict[str, tuple[float, float]]:
    first = df.groupby("station")[["lat", "lon"]].first()
    return {station: (row.lat, row.lon) for station, row in first.iterrows()}


def _summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "min": min(values),
        "max": max(values),
        "n": len(values),
    }


def validate() -> dict:
    df = pd.read_csv(DATA_PATH)
    coords = _station_coords(df)
    config = CostModelConfig()  # documented defaults, see docs/task_wind_cost_model.md

    results: dict[str, dict] = {}
    for origin, destination in EDGE_PAIRS:
        origin_lat, origin_lon = coords[origin]
        dest_lat, dest_lon = coords[destination]
        origin_readings = df[df["station"] == origin][["speed", "direction"]]

        per_criterion: dict[str, list[float]] = {"time": [], "energy": [], "balanced": []}
        infeasible_count = 0
        for _, reading in origin_readings.iterrows():
            for criterion in per_criterion:
                try:
                    result = compute_edge_cost(
                        origin_lat,
                        origin_lon,
                        dest_lat,
                        dest_lon,
                        wind_speed_mps=float(reading["speed"]),
                        wind_direction_from_deg=float(reading["direction"]),
                        config=config,
                        criterion=criterion,
                    )
                except InfeasibleEdgeError:
                    infeasible_count += 1
                    continue
                per_criterion[criterion].append(result.cost)

        edge_key = f"{origin} -> {destination}"
        results[edge_key] = {
            "distance_km": compute_edge_cost(
                origin_lat,
                origin_lon,
                dest_lat,
                dest_lon,
                wind_speed_mps=0.0,
                wind_direction_from_deg=0.0,
                config=config,
            ).distance_km,
            "n_hourly_readings": len(origin_readings),
            "n_infeasible_headwind_hours": infeasible_count,
            "time_hours": _summarize(per_criterion["time"]),
            "energy_hours": _summarize(per_criterion["energy"]),
            "balanced_hours": _summarize(per_criterion["balanced"]),
        }

    return results


def main() -> None:
    results = validate()
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
