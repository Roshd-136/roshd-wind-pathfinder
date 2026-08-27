"""
Wind Data Quality Control (QC) Module — AEROPATH
=================================================
ماژول کنترل کیفیت داده‌های باد

هدف: شناسایی داده‌های پرت، اعتبارسنجی بازه معتبر مقادیر، بررسی پیوستگی
زمانی و بررسی همخوانی با داده‌های مجاور (فضایی)، به‌همراه گزارش‌دهی خطاها
و داده‌های حذف‌شده.

ورودی مورد انتظار: داده‌ی باد خام از NetCDF/GRIB (مثلاً خروجی ECMWF Open
Data یا NOMADS) که با xarray باز شده و به DataFrame تخت (flat) با ستون‌های
زیر تبدیل شده است:

    time        : زمان مشاهده (datetime64)
    lat, lon    : مختصات مکانی
    level       : تراز فشار/ارتفاع (اختیاری، برای داده‌های چندلایه)
    u, v        : مولفه‌های سرعت باد (m/s) در جهت شرق و شمال
    (یا به‌جای u,v: ستون‌های speed و direction مستقیم)

اگر u,v داده شده باشند، speed و direction به‌صورت خودکار محاسبه می‌شوند:
    speed     = sqrt(u^2 + v^2)
    direction = (270 - degrees(atan2(v, u))) % 360   [قرارداد هواشناسی: از کجا می‌وزد]

خروجی: (clean_df, report) — داده‌ی پاک‌سازی‌شده (با ستون‌های پرچم QC) و
یک دیکشنری گزارش کامل که می‌توان آن را با ReportBuilder.to_json /
to_markdown ذخیره کرد.

نویسنده: محمدمهدی دستگیر — پروژه AEROPATH
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────
# ۱) تنظیمات و آستانه‌ها (Config & Thresholds)
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class QCConfig:
    """آستانه‌های قابل‌تنظیم کنترل کیفیت.

    مقادیر پیش‌فرض بر اساس بازه‌های فیزیکی معقول برای باد جوی تا ترازهای
    استراتوسفر پایین انتخاب شده‌اند و برای پرواز اجسام سبک در ارتفاع پایین
    (طبق پروژه AEROPATH) قابل تنگ‌تر کردن هستند.
    """

    # --- بازه‌ی معتبر فیزیکی (Range Validation) ---
    min_speed: float = 0.0          # m/s
    max_speed: float = 120.0        # m/s (~ طوفان‌های شدید جوی بالا)
    min_direction: float = 0.0      # درجه
    max_direction: float = 360.0    # درجه

    # --- شناسایی داده‌ی پرت آماری (Outlier Detection) ---
    outlier_method: str = "zscore"  # "zscore" | "iqr" | "mad"
    zscore_threshold: float = 3.0
    iqr_multiplier: float = 1.5
    mad_threshold: float = 3.5

    # --- پیوستگی زمانی (Temporal Continuity) ---
    max_time_gap: timedelta = timedelta(hours=6)   # حداکثر شکاف مجاز بین مشاهدات متوالی یک نقطه
    max_speed_jump: float = 30.0                   # m/s تغییر ناگهانی سرعت بین دو گام زمانی متوالی
    max_direction_jump: float = 150.0               # درجه تغییر ناگهانی جهت (با احتساب دوره‌ای بودن ۰-۳۶۰)

    # --- همخوانی مکانی با داده‌های مجاور (Spatial Consistency) ---
    spatial_neighbor_radius_deg: float = 0.5        # شعاع جستجوی همسایه (درجه‌ی جغرافیایی، تقریبی)
    spatial_speed_std_threshold: float = 3.0        # حداکثر انحراف مجاز از میانگین همسایگان (بر حسب std)
    min_neighbors_required: int = 3                 # حداقل تعداد همسایه برای اجرای این بررسی

    # --- عمومی ---
    drop_invalid: bool = True        # اگر True، ردیف‌های نامعتبر از خروجی نهایی حذف می‌شوند
    group_cols: tuple = ("lat", "lon")  # ستون‌های تعریف‌کننده‌ی یک "ایستگاه/نقطه" برای بررسی زمانی


# ─────────────────────────────────────────────────────────────────────────
# ۲) توابع کمکی محاسباتی
# ─────────────────────────────────────────────────────────────────────────

def uv_to_speed_direction(u: pd.Series, v: pd.Series) -> tuple[pd.Series, pd.Series]:
    """تبدیل مولفه‌های u,v به سرعت و جهت باد (قرارداد هواشناسی)."""
    speed = np.sqrt(u ** 2 + v ** 2)
    direction = (270 - np.degrees(np.arctan2(v, u))) % 360
    return speed, direction


def circular_diff(a: pd.Series, b: pd.Series) -> pd.Series:
    """اختلاف زاویه‌ای بین دو سری جهت (۰-۳۶۰ درجه) با احتساب دوره‌ای بودن.
    خروجی همیشه در بازه‌ی [0, 180] است."""
    d = (a - b).abs() % 360
    return np.minimum(d, 360 - d)


# ─────────────────────────────────────────────────────────────────────────
# ۳) کلاس اصلی QC
# ─────────────────────────────────────────────────────────────────────────

FLAG_OK = "OK"
FLAG_RANGE = "INVALID_RANGE"
FLAG_OUTLIER = "OUTLIER"
FLAG_TEMPORAL = "TEMPORAL_DISCONTINUITY"
FLAG_SPATIAL = "SPATIAL_INCONSISTENCY"
FLAG_MISSING = "MISSING_VALUE"


class WindQualityControl:
    """اجرای کامل خط لوله‌ی کنترل کیفیت روی یک DataFrame داده‌ی باد."""

    def __init__(self, config: QCConfig | None = None):
        self.config = config or QCConfig()
        self.report: dict = {}

    # -- نقطه‌ی ورود اصلی -----------------------------------------------
    def run(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        df = df.copy()
        cfg = self.config

        self._validate_input_columns(df)

        # محاسبه‌ی speed/direction در صورت نیاز
        if "speed" not in df.columns or "direction" not in df.columns:
            if "u" in df.columns and "v" in df.columns:
                df["speed"], df["direction"] = uv_to_speed_direction(df["u"], df["v"])
            else:
                raise ValueError(
                    "ستون‌های لازم یافت نشد: باید یا (speed, direction) یا (u, v) موجود باشند."
                )

        n_total = len(df)
        df["qc_flags"] = [[] for _ in range(n_total)]

        # مراحل QC به ترتیب
        df = self._flag_missing(df)
        df = self._flag_range(df)
        df = self._flag_outliers(df)
        df = self._flag_temporal(df)
        df = self._flag_spatial(df)

        df["qc_status"] = df["qc_flags"].apply(lambda f: FLAG_OK if len(f) == 0 else ";".join(f))
        df["qc_valid"] = df["qc_flags"].apply(len).eq(0)

        report = self._build_report(df)
        self.report = report

        if cfg.drop_invalid:
            clean_df = df[df["qc_valid"]].drop(columns=["qc_flags"]).reset_index(drop=True)
        else:
            clean_df = df.drop(columns=["qc_flags"]).reset_index(drop=True)

        return clean_df, report

    # -- ۱. اعتبارسنجی ستون‌های ورودی ------------------------------------
    def _validate_input_columns(self, df: pd.DataFrame) -> None:
        required = {"time", "lat", "lon"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"ستون‌های ضروری در داده‌ی ورودی یافت نشد: {missing}")
        if not np.issubdtype(df["time"].dtype, np.datetime64):
            raise ValueError("ستون time باید از نوع datetime64 باشد (pd.to_datetime را اجرا کنید).")

    # -- ۲. مقادیر گم‌شده --------------------------------------------------
    def _flag_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        mask = df["speed"].isna() | df["direction"].isna()
        for idx in df.index[mask]:
            df.at[idx, "qc_flags"].append(FLAG_MISSING)
        return df

    # -- ۳. اعتبارسنجی بازه‌ی معتبر (Range Validation) --------------------
    def _flag_range(self, df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        mask = df["speed"].notna() & (
            (df["speed"] < cfg.min_speed) | (df["speed"] > cfg.max_speed)
            | (df["direction"] < cfg.min_direction) | (df["direction"] > cfg.max_direction)
        )
        for idx in df.index[mask]:
            df.at[idx, "qc_flags"].append(FLAG_RANGE)
        return df

    # -- ۴. شناسایی داده‌ی پرت آماری (Outlier Detection) -------------------
    def _flag_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        valid = df["speed"].notna()
        s = df.loc[valid, "speed"]

        if cfg.outlier_method == "zscore":
            mu, sigma = s.mean(), s.std(ddof=0)
            if sigma > 0:
                z = (s - mu).abs() / sigma
                outlier_idx = s.index[z > cfg.zscore_threshold]
            else:
                outlier_idx = []
        elif cfg.outlier_method == "iqr":
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - cfg.iqr_multiplier * iqr, q3 + cfg.iqr_multiplier * iqr
            outlier_idx = s.index[(s < lower) | (s > upper)]
        elif cfg.outlier_method == "mad":
            median = s.median()
            mad = (s - median).abs().median()
            if mad > 0:
                modified_z = 0.6745 * (s - median).abs() / mad
                outlier_idx = s.index[modified_z > cfg.mad_threshold]
            else:
                outlier_idx = []
        else:
            raise ValueError(f"روش outlier ناشناخته: {cfg.outlier_method}")

        for idx in outlier_idx:
            df.at[idx, "qc_flags"].append(FLAG_OUTLIER)
        return df

    # -- ۵. بررسی پیوستگی زمانی (Temporal Continuity) ----------------------
    def _flag_temporal(self, df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        group_cols = list(cfg.group_cols)
        df_sorted = df.sort_values(group_cols + ["time"])

        for _, group in df_sorted.groupby(group_cols):
            group = group.sort_values("time")
            idxs = group.index.to_list()
            times = group["time"].to_list()
            speeds = group["speed"].to_list()
            directions = group["direction"].to_list()

            for i in range(1, len(idxs)):
                dt = times[i] - times[i - 1]
                if pd.isna(speeds[i]) or pd.isna(speeds[i - 1]):
                    continue

                # شکاف زمانی بزرگ -> نمی‌توان جهش را قضاوت کرد، فقط علامت شکاف
                if dt > cfg.max_time_gap:
                    df.at[idxs[i], "qc_flags"].append(f"{FLAG_TEMPORAL}:GAP")
                    continue

                speed_jump = abs(speeds[i] - speeds[i - 1])
                dir_jump = circular_diff(
                    pd.Series([directions[i]]), pd.Series([directions[i - 1]])
                ).iloc[0]

                if speed_jump > cfg.max_speed_jump:
                    df.at[idxs[i], "qc_flags"].append(f"{FLAG_TEMPORAL}:SPEED_JUMP")
                if dir_jump > cfg.max_direction_jump:
                    df.at[idxs[i], "qc_flags"].append(f"{FLAG_TEMPORAL}:DIRECTION_JUMP")

        return df

    # -- ۶. همخوانی با داده‌های مجاور (Spatial Consistency) ----------------
    def _flag_spatial(self, df: pd.DataFrame) -> pd.DataFrame:
        """برای هر زمان مشاهده، سرعت هر نقطه با میانگین/انحراف‌معیار همسایگان
        هم‌زمانش (در شعاع مشخص) مقایسه می‌شود. مناسب برای گرید یا داده‌ی
        چندایستگاهی هم‌زمان (مثلاً یک تایم‌استپ NetCDF)."""
        cfg = self.config
        r = cfg.spatial_neighbor_radius_deg

        for _t, group in df.groupby("time"):
            valid_group = group[group["speed"].notna()]
            if len(valid_group) < cfg.min_neighbors_required + 1:
                continue  # داده‌ی کافی برای مقایسه‌ی همسایگی نیست

            lats = valid_group["lat"].to_numpy()
            lons = valid_group["lon"].to_numpy()
            speeds = valid_group["speed"].to_numpy()
            idxs = valid_group.index.to_numpy()

            for i in range(len(idxs)):
                dist = np.sqrt((lats - lats[i]) ** 2 + (lons - lons[i]) ** 2)
                neighbor_mask = (dist > 0) & (dist <= r)
                n_neighbors = neighbor_mask.sum()
                if n_neighbors < cfg.min_neighbors_required:
                    continue

                neighbor_speeds = speeds[neighbor_mask]
                mu, sigma = neighbor_speeds.mean(), neighbor_speeds.std(ddof=0)
                if sigma == 0:
                    continue
                z = abs(speeds[i] - mu) / sigma
                if z > cfg.spatial_speed_std_threshold:
                    df.at[idxs[i], "qc_flags"].append(FLAG_SPATIAL)

        return df

    # -- ۷. ساخت گزارش نهایی ------------------------------------------------
    def _build_report(self, df: pd.DataFrame) -> dict:
        n_total = len(df)
        n_invalid = int((~df["qc_valid"]).sum())
        n_valid = n_total - n_invalid

        flag_counts: dict[str, int] = {}
        for flags in df["qc_flags"]:
            for f in flags:
                key = f.split(":")[0]
                flag_counts[key] = flag_counts.get(key, 0) + 1

        removed_records = df.loc[~df["qc_valid"], ["time", "lat", "lon", "speed", "direction", "qc_status"]]

        report = {
            "summary": {
                "total_records": n_total,
                "valid_records": n_valid,
                "invalid_records": n_invalid,
                "invalid_ratio": round(n_invalid / n_total, 4) if n_total else 0.0,
            },
            "flag_counts": flag_counts,
            "config_used": {
                "min_speed": self.config.min_speed,
                "max_speed": self.config.max_speed,
                "outlier_method": self.config.outlier_method,
                "zscore_threshold": self.config.zscore_threshold,
                "max_time_gap_hours": self.config.max_time_gap.total_seconds() / 3600,
                "max_speed_jump": self.config.max_speed_jump,
                "max_direction_jump": self.config.max_direction_jump,
                "spatial_neighbor_radius_deg": self.config.spatial_neighbor_radius_deg,
                "spatial_speed_std_threshold": self.config.spatial_speed_std_threshold,
            },
            "removed_records_preview": removed_records.head(50).to_dict(orient="records"),
            "removed_records_count": len(removed_records),
        }
        return report


# ─────────────────────────────────────────────────────────────────────────
# ۴) ابزار گزارش‌گیری (Report Export)
# ─────────────────────────────────────────────────────────────────────────

def save_report_json(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)


def save_removed_records_csv(df_full: pd.DataFrame, path: str) -> None:
    """df_full باید همان خروجی میانی با ستون qc_status باشد (drop_invalid=False)."""
    invalid = df_full[df_full["qc_valid"] == False]  # noqa: E712
    invalid.to_csv(path, index=False, encoding="utf-8-sig")


def report_to_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# گزارش کنترل کیفیت داده‌های باد",
        "",
        "## خلاصه",
        f"- تعداد کل رکوردها: {s['total_records']}",
        f"- رکوردهای معتبر: {s['valid_records']}",
        f"- رکوردهای نامعتبر/حذف‌شده: {s['invalid_records']} ({s['invalid_ratio']*100:.2f}%)",
        "",
        "## تعداد به تفکیک نوع خطا",
    ]
    for flag, count in sorted(report["flag_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"- {flag}: {count}")
    lines.append("")
    lines.append("## پیکربندی استفاده‌شده")
    for k, v in report["config_used"].items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# ۵) نمونه اجرا (Example usage)
# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # نمونه داده‌ی مصنوعی برای تست سریع ماژول (جایگزین با داده‌ی واقعی NetCDF شود)
    rng = np.random.default_rng(42)
    times = pd.date_range("2026-08-01", periods=24, freq="h")
    lats = [35.5, 35.6, 35.7]
    lons = [51.3, 51.4, 51.5]

    rows = []
    for t in times:
        for lat in lats:
            for lon in lons:
                speed = float(rng.normal(10, 2))
                direction = float(rng.uniform(0, 360))
                rows.append({"time": t, "lat": lat, "lon": lon, "speed": speed, "direction": direction})

    df = pd.DataFrame(rows)

    # تزریق عمدی چند خطا برای تست
    df.loc[5, "speed"] = 999.0        # خارج از بازه
    df.loc[10, "direction"] = -30.0   # خارج از بازه
    df.loc[15, "speed"] = np.nan      # مقدار گم‌شده
    df.loc[20, "speed"] = 80.0        # پرت آماری احتمالی

    qc = WindQualityControl(QCConfig())
    clean_df, report = qc.run(df)

    print(report_to_markdown(report))
    print("\nنمونه داده‌ی پاک‌سازی‌شده:")
    print(clean_df.head())
