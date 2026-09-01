"""
اعتبارسنجی پیوستگی زمانی و مکانی داده‌های باد.

این ماژول دو نوع بررسی انجام می‌دهد:
1. پیوستگی زمانی: برای هر ایستگاه، گپ‌های زمانی نسبت به بازه نمونه‌برداری
   مورد انتظار (مثلاً هر یک ساعت) تشخیص داده می‌شوند و برای گپ‌های کوتاه
   راهکار درون‌یابی خطی پیشنهاد می‌شود.
2. ناسازگاری مکانی: بین جفت ایستگاه‌های همسایه (نزدیک‌تر از یک آستانه فاصله)
   در هر بازه زمانی مشترک، اختلاف سرعت و جهت باد سنجیده می‌شود و مواردی که
   از آستانه قابل‌قبول فراتر می‌روند علامت‌گذاری می‌شوند.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """فاصله بزرگ‌دایره (haversine) بین دو مختصات جغرافیایی بر حسب کیلومتر."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def circular_diff_deg(a: float, b: float) -> float:
    """کوچک‌ترین اختلاف زاویه‌ای بین دو جهت (بر حسب درجه)، در بازه [0, 180]."""
    diff = abs(a - b) % 360
    return diff if diff <= 180 else 360 - diff


@dataclass
class ConsistencyConfig:
    """آستانه‌های قابل‌قبول برای بررسی پیوستگی زمانی و مکانی.

    پارامترها
    ----------
    expected_interval_hours : float
        بازه نمونه‌برداری مورد انتظار بین رکوردهای متوالی هر ایستگاه.
    max_fixable_gap_steps : int
        بیشینه تعداد گام‌های زمانی متوالی گم‌شده که با درون‌یابی خطی
        قابل ترمیم در نظر گرفته می‌شوند. گپ‌های بزرگ‌تر فقط گزارش می‌شوند.
    max_neighbor_distance_km : float
        بیشینه فاصله بین دو ایستگاه برای این‌که «همسایه» در نظر گرفته شوند.
    max_speed_diff : float
        بیشینه اختلاف قابل‌قبول سرعت باد (m/s) بین دو ایستگاه همسایه در یک زمان.
        مقدار پیش‌فرض (۱۵ m/s) نزدیک صدک ۹۰ توزیع اختلاف سرعت در داده مرجع
        خراسان است (رجوع کنید به docs/task_spatiotemporal_consistency.md).
    max_direction_diff_deg : float
        بیشینه اختلاف قابل‌قبول جهت باد (درجه) بین دو ایستگاه همسایه در یک زمان.
        در فاصله‌های ۷۰ تا ۱۷۰ کیلومتری (مانند ایستگاه‌های خراسان)، جهت باد به‌دلیل
        تأثیرات محلی توپوگرافی به‌طور طبیعی پراکندگی زیادی دارد؛ مقدار پیش‌فرض
        (۱۵۰ درجه، نزدیک صدک ۹۰ داده مرجع) فقط بازگشت‌های تقریباً کامل جهت را
        علامت می‌زند و از هشدار کاذب روی نوسانات طبیعی جلوگیری می‌کند.
    """

    expected_interval_hours: float = 1.0
    max_fixable_gap_steps: int = 2
    max_neighbor_distance_km: float = 250.0
    max_speed_diff: float = 15.0
    max_direction_diff_deg: float = 150.0


class SpatiotemporalConsistencyChecker:
    """بررسی پیوستگی زمانی (درون هر ایستگاه) و سازگاری مکانی (بین ایستگاه‌های
    همسایه) داده‌های باد، به‌همراه پیشنهاد راهکار اصلاح گپ‌های کوتاه.

    ورودی مورد انتظار: DataFrame با ستون‌های
    ``timestamp, station, lat, lon, speed, direction``.
    """

    required_columns = ("timestamp", "station", "lat", "lon", "speed", "direction")

    def __init__(self, config: ConsistencyConfig | None = None) -> None:
        self.config = config or ConsistencyConfig()

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in self.required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"ستون‌های ضروری در داده وجود ندارند: {missing}")
        out = df.copy()
        out["timestamp"] = pd.to_datetime(out["timestamp"])
        return out.sort_values(["station", "timestamp"]).reset_index(drop=True)

    # ------------------------------------------------------------------
    # ۱. پیوستگی زمانی
    # ------------------------------------------------------------------
    def check_temporal_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """برای هر ایستگاه، گپ‌های زمانی نسبت به بازه مورد انتظار را پیدا می‌کند.

        خروجی
        -------
        DataFrame با ستون‌های:
        ``station, gap_start, gap_end, missing_steps, missing_hours, fixable``
        """
        df = self._prepare(df)
        expected = pd.Timedelta(hours=self.config.expected_interval_hours)
        rows: list[dict[str, Any]] = []

        for station, group in df.groupby("station"):
            ts = group["timestamp"].reset_index(drop=True)
            for i in range(1, len(ts)):
                delta = ts[i] - ts[i - 1]
                if delta > expected:
                    missing_steps = int(round(delta / expected)) - 1
                    rows.append(
                        {
                            "station": station,
                            "gap_start": ts[i - 1],
                            "gap_end": ts[i],
                            "missing_steps": missing_steps,
                            "missing_hours": missing_steps * self.config.expected_interval_hours,
                            "fixable": missing_steps <= self.config.max_fixable_gap_steps,
                        }
                    )

        return pd.DataFrame(
            rows,
            columns=[
                "station",
                "gap_start",
                "gap_end",
                "missing_steps",
                "missing_hours",
                "fixable",
            ],
        )

    def fill_fixable_gaps(self, df: pd.DataFrame, gaps: pd.DataFrame | None = None) -> pd.DataFrame:
        """گپ‌های قابل‌ترمیم (طول <= max_fixable_gap_steps) را با درون‌یابی
        خطی زمانی روی speed و درون‌یابی دایره‌ای روی direction پر می‌کند و
        رکوردهای تولیدشده را با ستون ``interpolated=True`` برمی‌گرداند.

        رکوردهای گپ‌های غیرقابل‌ترمیم اضافه نمی‌شوند (فقط در گزارش علامت می‌خورند).
        """
        df = self._prepare(df)
        if gaps is None:
            gaps = self.check_temporal_gaps(df)

        df["interpolated"] = False
        filled_frames = [df]
        expected = pd.Timedelta(hours=self.config.expected_interval_hours)

        for _, gap in gaps[gaps["fixable"]].iterrows():
            station = gap["station"]
            before = df[(df["station"] == station) & (df["timestamp"] == gap["gap_start"])]
            after = df[(df["station"] == station) & (df["timestamp"] == gap["gap_end"])]
            if before.empty or after.empty:
                continue
            before, after = before.iloc[0], after.iloc[0]
            n_missing = int(gap["missing_steps"])

            new_rows = []
            for step in range(1, n_missing + 1):
                frac = step / (n_missing + 1)
                ts = gap["gap_start"] + expected * step
                speed = before["speed"] + frac * (after["speed"] - before["speed"])
                dir_diff = ((after["direction"] - before["direction"] + 540) % 360) - 180
                direction = (before["direction"] + frac * dir_diff) % 360
                new_rows.append(
                    {
                        "timestamp": ts,
                        "station": station,
                        "lat": before["lat"],
                        "lon": before["lon"],
                        "speed": speed,
                        "direction": direction,
                        "interpolated": True,
                    }
                )
            if new_rows:
                filled_frames.append(pd.DataFrame(new_rows))

        result = pd.concat(filled_frames, ignore_index=True)
        return result.sort_values(["station", "timestamp"]).reset_index(drop=True)

    # ------------------------------------------------------------------
    # ۲. ناسازگاری مکانی
    # ------------------------------------------------------------------
    def check_spatial_consistency(self, df: pd.DataFrame) -> pd.DataFrame:
        """در هر بازه زمانی، جفت ایستگاه‌های همسایه (نزدیک‌تر از
        max_neighbor_distance_km) را با هم مقایسه می‌کند و مواردی که اختلاف
        سرعت یا جهت باد از آستانه فراتر می‌رود را علامت‌گذاری می‌کند.

        خروجی
        -------
        DataFrame با ستون‌های:
        ``timestamp, station_a, station_b, distance_km, speed_diff,
        direction_diff, exceeds_threshold``
        """
        df = self._prepare(df)
        stations = df[["station", "lat", "lon"]].drop_duplicates("station").set_index("station")
        station_names = list(stations.index)

        # فاصله بین هر جفت ایستگاه، یک‌بار محاسبه می‌شود
        neighbor_pairs = []
        for i in range(len(station_names)):
            for j in range(i + 1, len(station_names)):
                a, b = station_names[i], station_names[j]
                dist = haversine_km(
                    stations.loc[a, "lat"], stations.loc[a, "lon"],
                    stations.loc[b, "lat"], stations.loc[b, "lon"],
                )
                if dist <= self.config.max_neighbor_distance_km:
                    neighbor_pairs.append((a, b, dist))

        rows: list[dict[str, Any]] = []
        if not neighbor_pairs:
            return pd.DataFrame(
                columns=[
                    "timestamp", "station_a", "station_b", "distance_km",
                    "speed_diff", "direction_diff", "exceeds_threshold",
                ]
            )

        pivot = df.pivot_table(index="timestamp", columns="station", values=["speed", "direction"])

        for a, b, dist in neighbor_pairs:
            if ("speed", a) not in pivot.columns or ("speed", b) not in pivot.columns:
                continue
            speed_a, speed_b = pivot[("speed", a)], pivot[("speed", b)]
            dir_a, dir_b = pivot[("direction", a)], pivot[("direction", b)]
            common = speed_a.notna() & speed_b.notna() & dir_a.notna() & dir_b.notna()

            for ts in pivot.index[common]:
                speed_diff = abs(speed_a[ts] - speed_b[ts])
                direction_diff = circular_diff_deg(dir_a[ts], dir_b[ts])
                exceeds = (
                    speed_diff > self.config.max_speed_diff
                    or direction_diff > self.config.max_direction_diff_deg
                )
                rows.append(
                    {
                        "timestamp": ts,
                        "station_a": a,
                        "station_b": b,
                        "distance_km": round(dist, 2),
                        "speed_diff": round(float(speed_diff), 3),
                        "direction_diff": round(float(direction_diff), 3),
                        "exceeds_threshold": bool(exceeds),
                    }
                )

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # ۳. گزارش نهایی
    # ------------------------------------------------------------------
    def generate_report(self, df: pd.DataFrame) -> dict[str, Any]:
        """گزارش کامل پیوستگی زمانی و مکانی را به‌صورت دیکشنری (قابل تبدیل به JSON) برمی‌گرداند."""
        df = self._prepare(df)
        gaps = self.check_temporal_gaps(df)
        spatial = self.check_spatial_consistency(df)

        n_fixable = int(gaps["fixable"].sum()) if not gaps.empty else 0
        n_unfixable = int((~gaps["fixable"]).sum()) if not gaps.empty else 0
        n_spatial_violations = (
            int(spatial["exceeds_threshold"].sum()) if not spatial.empty else 0
        )

        return {
            "config": {
                "expected_interval_hours": self.config.expected_interval_hours,
                "max_fixable_gap_steps": self.config.max_fixable_gap_steps,
                "max_neighbor_distance_km": self.config.max_neighbor_distance_km,
                "max_speed_diff": self.config.max_speed_diff,
                "max_direction_diff_deg": self.config.max_direction_diff_deg,
            },
            "stations": sorted(df["station"].unique().tolist()),
            "total_records": int(len(df)),
            "temporal": {
                "total_gaps": int(len(gaps)),
                "fixable_gaps": n_fixable,
                "unfixable_gaps": n_unfixable,
                "gaps": gaps.to_dict(orient="records"),
            },
            "spatial": {
                "neighbor_pairs_checked": int(spatial[["station_a", "station_b"]].drop_duplicates().shape[0])
                if not spatial.empty
                else 0,
                "comparisons": int(len(spatial)),
                "violations": n_spatial_violations,
                "violation_records": spatial[spatial["exceeds_threshold"]].to_dict(orient="records")
                if not spatial.empty
                else [],
            },
            "is_consistent": n_unfixable == 0 and n_spatial_violations == 0,
        }
