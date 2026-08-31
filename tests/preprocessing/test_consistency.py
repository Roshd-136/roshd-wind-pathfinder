"""
تست‌های ماژول اعتبارسنجی پیوستگی زمانی و مکانی.
"""

import pandas as pd
import pytest

from preprocessing.consistency import (
    ConsistencyConfig,
    SpatiotemporalConsistencyChecker,
    circular_diff_deg,
    haversine_km,
)

STATION_COORDS = {
    "Mashhad": (36.297, 59.606),
    "Neyshabur": (36.213, 58.795),
    "Sabzevar": (36.215, 57.678),
}


def _make_df(rows):
    return pd.DataFrame(
        rows, columns=["timestamp", "station", "lat", "lon", "speed", "direction"]
    )


def _clean_two_station_series(n=6, freq_hours=1):
    """سری زمانی کاملاً پیوسته برای دو ایستگاه همسایه، بدون گپ یا ناسازگاری."""
    rows = []
    start = pd.Timestamp("2026-08-29 00:00:00")
    for i in range(n):
        ts = start + pd.Timedelta(hours=i * freq_hours)
        for station, (lat, lon) in [
            ("Mashhad", STATION_COORDS["Mashhad"]),
            ("Neyshabur", STATION_COORDS["Neyshabur"]),
        ]:
            rows.append([ts, station, lat, lon, 5.0, 280.0])
    return _make_df(rows)


class TestHelpers:
    def test_haversine_known_distance(self):
        """۱. فاصله haversine باید با فاصله واقعی مشهد-نیشابور (~۷۳ کیلومتر) هم‌خوانی داشته باشد."""
        d = haversine_km(*STATION_COORDS["Mashhad"], *STATION_COORDS["Neyshabur"])
        assert 65 < d < 80

    def test_circular_diff_wraparound(self):
        """۲. اختلاف دایره‌ای بین ۳۵۰ و ۱۰ درجه باید ۲۰ باشد، نه ۳۴۰."""
        assert circular_diff_deg(350.0, 10.0) == pytest.approx(20.0)
        assert circular_diff_deg(10.0, 350.0) == pytest.approx(20.0)
        assert circular_diff_deg(0.0, 180.0) == pytest.approx(180.0)


class TestTemporalGaps:
    def test_no_gap_on_clean_hourly_data(self):
        """۳. داده کاملاً ساعتی نباید هیچ گپی گزارش کند."""
        df = _clean_two_station_series(n=6)
        checker = SpatiotemporalConsistencyChecker()
        gaps = checker.check_temporal_gaps(df)
        assert gaps.empty

    def test_detects_small_fixable_gap(self):
        """۴. حذف یک رکورد میانی باید به‌عنوان گپ قابل‌ترمیم (۱ گام) شناسایی شود."""
        df = _clean_two_station_series(n=6)
        df = df[~((df["station"] == "Mashhad") & (df["timestamp"] == df["timestamp"].iloc[2]))]
        checker = SpatiotemporalConsistencyChecker()
        gaps = checker.check_temporal_gaps(df)
        mashhad_gaps = gaps[gaps["station"] == "Mashhad"]
        assert len(mashhad_gaps) == 1
        assert mashhad_gaps.iloc[0]["missing_steps"] == 1
        assert mashhad_gaps.iloc[0]["fixable"]

    def test_detects_large_unfixable_gap(self):
        """۵. گپ بزرگ‌تر از آستانه باید غیرقابل‌ترمیم علامت بخورد."""
        config = ConsistencyConfig(max_fixable_gap_steps=2)
        rows = [
            ["2026-08-29 00:00:00", "Mashhad", 36.297, 59.606, 5.0, 280.0],
            ["2026-08-29 10:00:00", "Mashhad", 36.297, 59.606, 6.0, 280.0],
        ]
        df = _make_df(rows)
        checker = SpatiotemporalConsistencyChecker(config)
        gaps = checker.check_temporal_gaps(df)
        assert len(gaps) == 1
        assert gaps.iloc[0]["missing_steps"] == 9
        assert not gaps.iloc[0]["fixable"]

    def test_fill_fixable_gaps_interpolates_linearly(self):
        """۶. پر کردن گپ قابل‌ترمیم باید مقدار درون‌یابی‌شده خطی تولید کند."""
        rows = [
            ["2026-08-29 00:00:00", "Mashhad", 36.297, 59.606, 4.0, 280.0],
            ["2026-08-29 02:00:00", "Mashhad", 36.297, 59.606, 6.0, 280.0],
        ]
        df = _make_df(rows)
        checker = SpatiotemporalConsistencyChecker()
        filled = checker.fill_fixable_gaps(df)
        assert len(filled) == 3
        mid = filled[filled["interpolated"]].iloc[0]
        assert mid["speed"] == pytest.approx(5.0)
        assert mid["timestamp"] == pd.Timestamp("2026-08-29 01:00:00")

    def test_unfixable_gap_not_filled(self):
        """۷. گپ غیرقابل‌ترمیم نباید رکورد جدیدی تولید کند."""
        config = ConsistencyConfig(max_fixable_gap_steps=1)
        rows = [
            ["2026-08-29 00:00:00", "Mashhad", 36.297, 59.606, 4.0, 280.0],
            ["2026-08-29 05:00:00", "Mashhad", 36.297, 59.606, 6.0, 280.0],
        ]
        df = _make_df(rows)
        checker = SpatiotemporalConsistencyChecker(config)
        filled = checker.fill_fixable_gaps(df)
        assert len(filled) == 2
        assert not filled["interpolated"].any()


class TestSpatialConsistency:
    def test_consistent_neighbors_no_violation(self):
        """۸. ایستگاه‌های همسایه با سرعت/جهت مشابه نباید ناسازگاری گزارش کنند."""
        df = _clean_two_station_series(n=4)
        checker = SpatiotemporalConsistencyChecker()
        spatial = checker.check_spatial_consistency(df)
        assert not spatial.empty
        assert not spatial["exceeds_threshold"].any()

    def test_large_speed_diff_flagged(self):
        """۹. اختلاف زیاد سرعت بین دو ایستگاه نزدیک باید علامت بخورد."""
        rows = [
            ["2026-08-29 00:00:00", "Mashhad", 36.297, 59.606, 5.0, 280.0],
            ["2026-08-29 00:00:00", "Neyshabur", 36.213, 58.795, 40.0, 280.0],
        ]
        df = _make_df(rows)
        checker = SpatiotemporalConsistencyChecker()
        spatial = checker.check_spatial_consistency(df)
        assert len(spatial) == 1
        assert spatial.iloc[0]["exceeds_threshold"]

    def test_far_apart_stations_not_compared(self):
        """۱۰. ایستگاه‌های دورتر از آستانه فاصله نباید با هم مقایسه شوند."""
        config = ConsistencyConfig(max_neighbor_distance_km=50.0)
        rows = [
            ["2026-08-29 00:00:00", "Mashhad", 36.297, 59.606, 5.0, 280.0],
            ["2026-08-29 00:00:00", "Sabzevar", 36.215, 57.678, 5.0, 280.0],
        ]
        df = _make_df(rows)
        checker = SpatiotemporalConsistencyChecker(config)
        spatial = checker.check_spatial_consistency(df)
        assert spatial.empty


class TestReport:
    def test_generate_report_structure(self):
        """۱۱. گزارش خروجی باید ساختار مورد انتظار و is_consistent=True برای داده تمیز داشته باشد."""
        df = _clean_two_station_series(n=4)
        checker = SpatiotemporalConsistencyChecker()
        report = checker.generate_report(df)
        assert set(report.keys()) >= {"temporal", "spatial", "is_consistent", "stations"}
        assert report["is_consistent"] is True
        assert report["temporal"]["total_gaps"] == 0
        assert report["spatial"]["violations"] == 0

    def test_missing_required_column_raises(self):
        """۱۲. نبود ستون ضروری باید ValueError ایجاد کند."""
        df = pd.DataFrame({"timestamp": ["2026-08-29 00:00:00"], "station": ["Mashhad"]})
        checker = SpatiotemporalConsistencyChecker()
        with pytest.raises(ValueError):
            checker.check_temporal_gaps(df)
