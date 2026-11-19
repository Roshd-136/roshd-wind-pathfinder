"""صحت دادهٔ سراسری ایران — جایگزین دادهٔ سه‌ایستگاهی خراسان.

دادهٔ باد با همان روش خراسان از Open-Meteo گرفته می‌شود
(``scripts/fetch_iran_data.py``) و DEM با همان سرویس Elevation
(``scripts/fetch_terrain_data.py --bbox iran``). این آزمون‌ها همان چیزهایی را
می‌سنجند که «جایگزینی درست» را از «فایلی که اتفاقی موجود است» جدا می‌کنند:

  ۱) طرح‌وارهٔ ستون‌ها و پاکی مقادیر (بدون NaN)؛
  ۲) پوشش جغرافیایی کل کشور، نه یک کریدور؛
  ۳) ماندن مقادیر داخل بازهٔ QC (همان ``QCConfig(max_speed=100)``)؛
  ۴) هم‌خوانی گزارش QC با CSV تمیز؛
  ۵) DEM سراسری با گسترهٔ ارتفاع واقعی ایران؛
  ۶) منظم و کوچک ماندن شبکهٔ نمایش (خواستهٔ «پیکان‌های بهینه»).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from viz.terrain import IRAN_TERRAIN_CSV_PATH, load_terrain
from viz.wind_field import (
    DISPLAY_LAT_STEP,
    DISPLAY_LON_STEP,
    IRAN_BBOX,
    display_lattice,
)

ROOT = Path(__file__).resolve().parents[1]
WIND_CSV = ROOT / "data" / "iran_wind_qc_cleaned.csv"
QC_REPORT = ROOT / "data" / "iran_qc_report.json"

EXPECTED_COLUMNS = ["timestamp", "station", "lat", "lon", "speed", "direction"]


@pytest.fixture(scope="module")
def wind_frame() -> pd.DataFrame:
    assert WIND_CSV.exists(), f"{WIND_CSV} موجود نیست — scripts/fetch_iran_data.py را اجرا کنید."
    return pd.read_csv(WIND_CSV)


def test_wind_dataset_schema(wind_frame: pd.DataFrame) -> None:
    """ستون‌ها دقیقاً قالب پروژه‌اند و هیچ مقدار خالی/غیرعددی ندارد."""
    assert list(wind_frame.columns) == EXPECTED_COLUMNS
    assert not wind_frame.isna().any().any(), "دادهٔ تمیز نباید NaN داشته باشد"
    assert pd.api.types.is_numeric_dtype(wind_frame["lat"])
    assert pd.api.types.is_numeric_dtype(wind_frame["lon"])
    assert pd.api.types.is_numeric_dtype(wind_frame["speed"])
    assert pd.api.types.is_numeric_dtype(wind_frame["direction"])
    assert wind_frame["station"].astype(str).str.len().gt(0).all()


def test_wind_dataset_covers_whole_iran(wind_frame: pd.DataFrame) -> None:
    """ایستگاه‌ها داخل کادر ایران و پراکنده روی کل کشورند (نه یک کریدور)."""
    assert wind_frame["lat"].between(IRAN_BBOX["lat_min"], IRAN_BBOX["lat_max"]).all()
    assert wind_frame["lon"].between(IRAN_BBOX["lon_min"], IRAN_BBOX["lon_max"]).all()

    stations = wind_frame.drop_duplicates("station")
    assert len(stations) >= 30, "پوشش شهری سراسری: دست‌کم ۳۰ ایستگاه لازم است"

    lat_span = stations["lat"].max() - stations["lat"].min()
    lon_span = stations["lon"].max() - stations["lon"].min()
    assert lat_span >= 10.0, f"گسترهٔ عرضی ایستگاه‌ها کم است ({lat_span:.1f}°)"
    assert lon_span >= 15.0, f"گسترهٔ طولی ایستگاه‌ها کم است ({lon_span:.1f}°)"

    # چهار ربع کشور باید دست‌کم یک ایستگاه داشته باشند — وگرنه درون‌یابی IDW
    # یک گوشهٔ کشور را با اکستراپولاسیون بی‌پشتوانه پر می‌کند.
    mid_lat = 0.5 * (IRAN_BBOX["lat_min"] + IRAN_BBOX["lat_max"])
    mid_lon = 0.5 * (IRAN_BBOX["lon_min"] + IRAN_BBOX["lon_max"])
    for lat_sign in (-1, 1):
        for lon_sign in (-1, 1):
            quadrant = stations[
                ((stations["lat"] - mid_lat) * lat_sign > 0)
                & ((stations["lon"] - mid_lon) * lon_sign > 0)
            ]
            assert not quadrant.empty, "هر ربع کشور باید ایستگاه داشته باشد"


def test_wind_values_within_qc_bounds(wind_frame: pd.DataFrame) -> None:
    """همان بازه‌های ``QCConfig`` که اسکریپت با آن اجرا شده است."""
    assert wind_frame["speed"].between(0.0, 100.0).all()
    assert wind_frame["direction"].between(0.0, 360.0).all()


def test_station_coordinates_are_constant(wind_frame: pd.DataFrame) -> None:
    """هر نام ایستگاه دقیقاً یک مختصات دارد — نام تکراری برای دو شهر مجاز نیست."""
    spread = wind_frame.groupby("station")[["lat", "lon"]].nunique()
    assert (spread <= 1).all().all(), "یک ایستگاه با دو مختصات مختلف ثبت شده است"


def test_station_series_is_hourly_and_long_enough(wind_frame: pd.DataFrame) -> None:
    """هر ایستگاه یک سری ساعتی دارد (پیش‌بینی ۴۸ ساعته منهای حذف‌های QC).

    حذف‌های QC تک‌ساعتی‌اند، پس «فاصلهٔ صفر» یا ساعت تکراری ممنوع است ولی
    شکاف چندساعته طبیعی است؛ معیار درست، میانهٔ گام‌ها و گسترهٔ زمانی است، نه
    پیوستگی صد‌درصدی.
    """
    for station, group in wind_frame.groupby("station"):
        stamps = pd.to_datetime(group["timestamp"]).sort_values()
        assert stamps.is_unique, f"{station}: مهر زمانی تکراری"
        gaps = stamps.diff().dropna().dt.total_seconds() / 3600.0
        assert not gaps.empty
        assert (gaps >= 1.0).all(), f"{station}: گام زیر یک ساعت"
        assert gaps.median() == 1.0, f"{station}: سری ساعتی نیست ({gaps.unique()[:3]})"
        assert len(group) >= 35, f"{station}: تنها {len(group)} مشاهده"
        span_hours = (stamps.iloc[-1] - stamps.iloc[0]).total_seconds() / 3600.0
        assert span_hours <= 49.0, f"{station}: گسترهٔ زمانی بیش از پنجرهٔ ۴۸ ساعته"


def test_qc_report_matches_clean_csv(wind_frame: pd.DataFrame) -> None:
    """گزارش QC همان تعداد ردیف فایل تمیز را تأیید می‌کند."""
    assert QC_REPORT.exists(), "گزارش QC ساخته نشده است"
    report = json.loads(QC_REPORT.read_text(encoding="utf-8"))
    summary = report["summary"]
    assert summary["valid_records"] == len(wind_frame)
    assert summary["valid_records"] + summary["removed_records"] == summary["total_records"]
    assert summary["removal_rate_pct"] < 10.0, "نرخ حذف QC غیرعادی است"
    assert report["config"]["max_speed"] == 100.0


def test_terrain_dataset_covers_iran() -> None:
    """DEM سراسری: گسترهٔ کادر ایران، شبکهٔ ۱۰ کیلومتری و برجستگی واقعی."""
    assert IRAN_TERRAIN_CSV_PATH.exists(), (
        f"{IRAN_TERRAIN_CSV_PATH} موجود نیست — "
        "scripts/fetch_terrain_data.py --bbox iran را اجرا کنید."
    )
    terrain = load_terrain(IRAN_TERRAIN_CSV_PATH)

    assert terrain.lats[0] == pytest.approx(IRAN_BBOX["lat_min"], abs=1e-6)
    assert terrain.lats[-1] == pytest.approx(IRAN_BBOX["lat_max"], abs=1e-6)
    assert terrain.lons[0] == pytest.approx(IRAN_BBOX["lon_min"], abs=1e-6)
    assert terrain.lons[-1] == pytest.approx(IRAN_BBOX["lon_max"], abs=1e-6)

    assert len(terrain.lats) >= 150 and len(terrain.lons) >= 170, "شبکه درشت‌تر از ۱۰ km است"
    # ایران از کرانهٔ خزر (~-۲۸ m) تا دماوند (~۵۶۱۰ m) — بازهٔ واقعی، نه ثابت دلبخواه.
    assert -80.0 < terrain.min_elevation_m < 200.0
    assert 4500.0 < terrain.max_elevation_m < 6000.0
    assert terrain.relief_m > 4000.0


def test_display_lattice_is_regular_and_bounded() -> None:
    """شبکهٔ نمایش منظم (گام ثابت) و بهینه (کمتر از ۲۰۰۰ بردار در هر لایه) است.

    دلیل: فرانت گام شبکه را از دو محور اول حدس می‌زند؛ گام نایکنوا تصویر حرارتی
    و ذرات باد را جابه‌جا می‌کند. سقف تعداد هم «بهینه بودن پیکان‌ها» را تضمین
    می‌کند — اگر کسی گام را ریز کند، حجم پاسخ چند برابر می‌شود و این آزمون
    هشدار می‌دهد.
    """
    lats, lons = display_lattice()

    assert lats[0] == pytest.approx(IRAN_BBOX["lat_min"], abs=1e-6)
    assert lats[-1] == pytest.approx(IRAN_BBOX["lat_max"], abs=1e-6)
    assert lons[0] == pytest.approx(IRAN_BBOX["lon_min"], abs=1e-6)
    assert lons[-1] == pytest.approx(IRAN_BBOX["lon_max"], abs=1e-6)

    assert np.allclose(np.diff(lats), DISPLAY_LAT_STEP)
    assert np.allclose(np.diff(lons), DISPLAY_LON_STEP)
    assert len(lats) * len(lons) <= 2000
