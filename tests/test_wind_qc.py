import pandas as pd
import pytest
from roshd_wind_pathfinder.qc.wind_qc import QCConfig, WindQualityControl


def test_qc_range_and_missing():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=4, freq="1h"),
        "lat": [35.0] * 4,
        "lon": [51.0] * 4,
        "speed": [10.0, 150.0, None, 20.0],
        "direction": [180.0, 180.0, 180.0, 400.0],
    })
    qc = WindQualityControl()
    clean_df, report = qc.run(df)
    assert len(clean_df) == 1
    assert report["summary"]["removed_records"] == 3


def test_qc_uv_conversion():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=2, freq="1h"),
        "lat": [35.0, 35.0],
        "lon": [51.0, 51.0],
        "u": [3.0, 0.0],
        "v": [4.0, 5.0],
    })
    qc = WindQualityControl()
    clean_df, _ = qc.run(df)
    assert len(clean_df) == 2
    assert clean_df["speed"].iloc[0] == pytest.approx(5.0)
