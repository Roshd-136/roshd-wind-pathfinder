import pandas as pd
from roshd_wind_pathfinder.preprocessing.pathfinding_preparation import prepare_for_pathfinding


def test_pathfinding_prep():
    df = pd.DataFrame({
        "timestamp": ["2026-01-01T00:00:00"] * 2,
        "lat": [36.0, 36.5],
        "lon": [58.0, 58.5],
        "altitude": [500.0, 500.0],
        "wind_speed": [10.0, 20.0],
        "wind_direction": [180.0, 90.0],
    })
    prep_df = prepare_for_pathfinding(df, lat_step=0.5, lon_step=0.5, altitude_levels=(500.0,))
    assert "u_normalized" in prep_df.columns
    assert "v_normalized" in prep_df.columns
    assert len(prep_df) >= 2
