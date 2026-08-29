import pandas as pd
import pytest
from src.wind_qc import QCConfig, WindQualityControl


def test_qc_range_and_missing():
    df = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=4, freq="1h"),
        "lat": [35.0] * 4,
        "lon": [51.0] * 4,
        "speed": [10.0, 150.0, None, 20.0],  # 150 is out of range, None is missing
        "direction": [180.0, 180.0, 180.0, 400.0],  # 400 is out of range
    })

    qc = WindQualityControl()
    clean_df, report = qc.run(df)

    assert len(clean_df) == 1
    assert report["summary"]["removed_records"] == 3
    assert "INVALID_RANGE" in report["error_counts"]
    assert "MISSING_VALUE" in report["error_counts"]


def test_qc_uv_conversion():
    df = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=2, freq="1h"),
        "lat": [35.0, 35.0],
        "lon": [51.0, 51.0],
        "u": [3.0, 0.0],
        "v": [4.0, 5.0],
    })

    qc = WindQualityControl()
    clean_df, report = qc.run(df)

    assert len(clean_df) == 2
    assert "speed" in clean_df.columns
    assert "direction" in clean_df.columns
    assert clean_df["speed"].iloc[0] == pytest.approx(5.0)


def test_qc_temporal_jump():
    df = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=3, freq="1h"),
        "lat": [35.0] * 3,
        "lon": [51.0] * 3,
        "speed": [10.0, 50.0, 52.0],  # 10 -> 50 is a jump of 40 (> max_speed_jump 30)
        "direction": [180.0, 180.0, 180.0],
    })

    config = QCConfig(max_speed_jump=30.0)
    qc = WindQualityControl(config)
    clean_df, report = qc.run(df)

    assert "TEMPORAL_JUMP" in report["error_counts"]
