import pandas as pd
from roshd_wind_pathfinder.data.prep import PathfindingDataPrep


def test_unit_conversion_and_vectors():
    prep = PathfindingDataPrep()
    df = pd.DataFrame({
        "latitude": [35.0],
        "longitude": [51.0],
        "wind_speed": [10.0],
        "wind_direction": [90.0],
    })
    res = prep.convert_units(df)
    assert "u_component" in res.columns
    assert "v_component" in res.columns
    assert round(res["u_component"].iloc[0], 2) == -10.0


def test_regular_grid_generation():
    prep = PathfindingDataPrep(heights=[500, 1000], grid_resolution=1.0)
    df = pd.DataFrame({
        "latitude": [35.0, 36.0],
        "longitude": [51.0, 52.0],
        "wind_speed": [10.0, 15.0],
        "wind_direction": [180.0, 180.0],
    })
    grid = prep.create_regular_grid(df)
    assert set(grid["altitude"].unique()) == {500, 1000}
    assert "u_component_norm" in grid.columns
