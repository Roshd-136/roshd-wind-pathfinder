import pandas as pd
from roshd_wind_pathfinder.data.qc import WindDataQC


def test_qc_range_check():
    qc = WindDataQC()
    df = pd.DataFrame({
        "wind_speed": [10.0, -5.0, 80.0, 25.0],
        "wind_direction": [180.0, 90.0, 400.0, -10.0],
    })
    errors = qc.check_range(df)
    assert errors.tolist() == [False, True, True, True]


def test_qc_temporal_check():
    qc = WindDataQC(max_step_speed=15.0, flatline_limit=3)
    df = pd.DataFrame({"wind_speed": [10.0, 30.0, 30.0, 30.0, 12.0]})
    errors = qc.check_temporal(df)
    assert errors.tolist() == [False, True, True, True, True]


def test_qc_spatial_check():
    qc = WindDataQC()
    df = pd.DataFrame({
        "wind_speed": [10.0, 11.0, 12.0, 50.0],
        "neighbor_avg_speed": [10.5, 10.8, 11.5, 12.0],
    })
    errors = qc.check_spatial(df)
    assert errors.iloc[3] == True
    assert errors.iloc[0] == False


def test_qc_full_run():
    qc = WindDataQC()
    df = pd.DataFrame({
        "wind_speed": [15.0, 100.0, 16.0],
        "wind_direction": [90.0, 90.0, 90.0],
    })
    df_clean, report = qc.run_qc(df)
    assert len(df_clean) == 2
    assert report["total_records"] == 3
    assert report["range_errors"] == 1
    assert report["total_invalid"] == 1
