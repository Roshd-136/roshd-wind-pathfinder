"""ارائه‌دهنده داده باد برای بک‌اند — از داده واقعی ایستگاه‌ها گراف چندلایه و نمونه‌برداری می‌سازد.

داده اندازه‌گیری‌شده واقعی فقط در سطح (سه ایستگاه خراسان) موجود است؛ لایه‌های ارتفاعی
بالاتر با همان تغییر مقیاس مستند‌شده در ``tests/pathfinding/test_end_to_end.py`` و
``scripts/generate_pathfinding_visualizations.py`` ساخته می‌شوند (افزایش خطی سرعت با
ارتفاع و چرخش اکمن). هیچ داده ساختگی بی‌ربط به داده واقعی تولید نمی‌شود.
"""

from __future__ import annotations

import math
import threading
from pathlib import Path

import numpy as np
import pandas as pd

from backend.errors import DataUnavailable
from pathfinding.cost import CostModelConfig
from pathfinding.graph import MultiLayerWindGraph
from preprocessing.idw import IDWInterpolator

__all__ = ["WindDataProvider", "DEFAULT_ALTITUDES", "DEFAULT_DATA_PATH"]

DEFAULT_ALTITUDES = (500.0, 1000.0, 1500.0, 2000.0)
DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "khorasan_wind_qc_cleaned.csv"
_MAX_FIELD_VECTORS = 5000


def _to_uv(speed: np.ndarray, direction_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """جهت هواشناسی (از کجا می‌وزد) → مؤلفه‌های u/v."""
    rad = np.deg2rad(direction_deg)
    return -speed * np.sin(rad), -speed * np.cos(rad)


def _from_uv(u: float, v: float) -> tuple[float, float]:
    speed = math.hypot(u, v)
    direction = math.degrees(math.atan2(-u, -v)) % 360.0
    return speed, direction


class WindDataProvider:
    """نگهدارنده داده ایستگاه‌ها و سازنده گراف/نمونه باد برای لایه سرویس.

    پارامترها
    ----------
    stations : DataFrame
        ستون‌های ``lat``, ``lon``, ``speed``, ``direction`` (یک ردیف به ازای هر ایستگاه).
    altitudes : tuple[float, ...]
        ارتفاع لایه‌ها (متر).
    last_updated : str | None
        زمان آخرین داده (ISO 8601) برای متادیتای لایه‌ها.
    """

    def __init__(
        self,
        stations: pd.DataFrame,
        altitudes: tuple[float, ...] = DEFAULT_ALTITUDES,
        last_updated: str | None = None,
        config: CostModelConfig | None = None,
        max_edge_distance_km: float = 200.0,
    ) -> None:
        cols = ["lat", "lon", "speed", "direction"]
        missing = [c for c in cols if c not in stations.columns]
        if missing:
            raise ValueError(f"stations is missing columns: {missing}")
        self._stations = stations[cols].dropna().reset_index(drop=True)
        self.altitudes = tuple(sorted(float(a) for a in altitudes))
        self.last_updated = last_updated
        self.config = config or CostModelConfig()
        self.max_edge_distance_km = max_edge_distance_km
        self._graphs: dict[tuple[str, float | None], MultiLayerWindGraph] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_csv(cls, path: Path | str = DEFAULT_DATA_PATH, **kwargs) -> WindDataProvider:
        """از فایل CSV واقعی (سطحی، هر ایستگاه چند timestamp) می‌سازد."""
        path = Path(path)
        if not path.exists():
            raise DataUnavailable(f"Wind data file not found: {path.name}")
        df = pd.read_csv(path)
        need = {"station", "lat", "lon", "speed", "direction"}
        if not need.issubset(df.columns):
            raise DataUnavailable(f"Wind data file lacks columns: {sorted(need - set(df.columns))}")
        stations = df.groupby("station", as_index=False).agg(
            {"lat": "first", "lon": "first", "speed": "mean", "direction": "mean"}
        )
        last = None
        if "timestamp" in df.columns and df["timestamp"].notna().any():
            last = str(pd.to_datetime(df["timestamp"], utc=True).max().isoformat())
        return cls(stations, last_updated=last, **kwargs)

    # ------------------------------------------------------------------ لایه‌ها
    @property
    def has_data(self) -> bool:
        return len(self._stations) > 0

    def _require_data(self) -> None:
        if not self.has_data:
            raise DataUnavailable("No wind station data is available.")

    def layer_frame(self, altitude: float) -> pd.DataFrame:
        """DataFrame باد یک لایه (ستون‌های lat, lon, wind_speed, wind_direction)."""
        scale = 1.0 + (altitude - 500.0) / 3000.0
        rotation = (altitude - 500.0) / 100.0
        return pd.DataFrame(
            {
                "lat": self._stations["lat"],
                "lon": self._stations["lon"],
                "wind_speed": self._stations["speed"] * scale,
                "wind_direction": (self._stations["direction"] + rotation) % 360.0,
            }
        )

    def has_layer(self, altitude: float) -> bool:
        return any(abs(altitude - a) < 1e-9 for a in self.altitudes)

    def bbox(self) -> list[float]:
        """[min_lon, min_lat, max_lon, max_lat] ایستگاه‌ها."""
        self._require_data()
        s = self._stations
        return [float(s.lon.min()), float(s.lat.min()), float(s.lon.max()), float(s.lat.max())]

    def layers_meta(self) -> list[dict]:
        self._require_data()
        return [
            {
                "altitude_m": a,
                "unit": "m/s",
                "bbox": self.bbox(),
                "last_updated": self.last_updated,
            }
            for a in self.altitudes
        ]

    def multi_graph(self, criterion: str, time_weight: float | None) -> MultiLayerWindGraph:
        """گراف چندلایه برای معیار/وزن مشخص (وزن یال‌ها هنگام ساخت ثابت می‌شود؛ کش می‌شود)."""
        self._require_data()
        key = (criterion, time_weight if criterion == "balanced" else None)
        with self._lock:
            if key not in self._graphs:
                frames = []
                for a in self.altitudes:
                    f = self.layer_frame(a)
                    f["altitude"] = a
                    frames.append(f)
                self._graphs[key] = MultiLayerWindGraph.build_from_dataframe(
                    pd.concat(frames, ignore_index=True),
                    config=self.config,
                    criterion=criterion,
                    max_edge_distance_km=self.max_edge_distance_km,
                    time_weight=key[1],
                )
            return self._graphs[key]

    # -------------------------------------------------------------- نمونه‌برداری
    def sample(self, altitude: float, lat: float, lon: float) -> dict:
        """باد درون‌یابی‌شده (IDW روی مؤلفه‌های u/v) در یک نقطه و یک لایه."""
        self._require_data()
        frame = self.layer_frame(altitude)
        u, v = _to_uv(frame["wind_speed"].to_numpy(float), frame["wind_direction"].to_numpy(float))
        pts = frame[["lat", "lon"]].to_numpy(float)
        target = np.array([[lat, lon]], dtype=float)
        idw = IDWInterpolator(power=2.0)
        ui = float(idw.interpolate_scalar(target, pts, u)[0])
        vi = float(idw.interpolate_scalar(target, pts, v)[0])
        speed, direction = _from_uv(ui, vi)
        return {
            "altitude_m": altitude,
            "speed_mps": round(speed, 4),
            "direction_deg": round(direction, 2),
        }

    def sample_all(self, lat: float, lon: float) -> list[dict]:
        self._require_data()
        return [self.sample(a, lat, lon) for a in self.altitudes]

    def field(self, altitude: float, bbox: list[float] | None, resolution_deg: float) -> dict:
        """میدان برداری منظم روی bbox؛ اگر تعداد بردارها زیاد شود ``ValueError``."""
        self._require_data()
        box = bbox or self.bbox()
        min_lon, min_lat, max_lon, max_lat = box
        n_lon = int(math.floor((max_lon - min_lon) / resolution_deg)) + 1
        n_lat = int(math.floor((max_lat - min_lat) / resolution_deg)) + 1
        if n_lon * n_lat > _MAX_FIELD_VECTORS:
            raise ValueError(
                f"resolution too fine: {n_lon * n_lat} vectors exceeds limit {_MAX_FIELD_VECTORS}"
            )
        vectors = []
        for i in range(n_lat):
            lat = min_lat + i * resolution_deg
            for j in range(n_lon):
                lon = min_lon + j * resolution_deg
                s = self.sample(altitude, lat, lon)
                vectors.append(
                    {
                        "lat": round(lat, 6),
                        "lon": round(lon, 6),
                        "speed_mps": s["speed_mps"],
                        "direction_deg": s["direction_deg"],
                    }
                )
        return {"altitude_m": altitude, "vectors": vectors}
