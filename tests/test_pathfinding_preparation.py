import numpy as np
import pandas as pd
import pytest

from preprocessing.pathfinding_preparation import normalize_units, prepare_for_pathfinding


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


def test_pathfinding_prep_covers_full_altitude_range():
    altitudes = [500.0, 1000.0, 1500.0, 2000.0]
    df = pd.DataFrame({
        "timestamp": ["2026-01-01T00:00:00"] * len(altitudes),
        "lat": [36.0] * len(altitudes),
        "lon": [58.0] * len(altitudes),
        "altitude": altitudes,
        "wind_speed": [5.0, 6.0, 7.0, 8.0],
        "wind_direction": [10.0, 20.0, 30.0, 40.0],
    })
    prep_df = prepare_for_pathfinding(df, lat_step=0.5, lon_step=0.5)
    assert set(prep_df["altitude"].unique()) == set(altitudes)


def test_normalize_units_accepts_speed_direction_aliases():
    # The sample data in data/khorasan_pathfinding_ready.csv uses "speed" and
    # "direction" rather than "wind_speed"/"wind_direction"; both must work.
    df = pd.DataFrame({"speed": [10.0], "direction": [400.0]})
    result = normalize_units(df)
    assert "wind_speed" in result.columns
    assert "wind_direction" in result.columns
    assert "speed" not in result.columns
    assert "direction" not in result.columns
    # 400 degrees should wrap to 40 degrees.
    assert result["wind_direction"].iloc[0] == pytest.approx(40.0)


def test_normalize_units_converts_kmh_to_ms():
    df = pd.DataFrame({"wind_speed": [36.0], "wind_direction": [0.0]})
    result = normalize_units(df, speed_unit="km/h")
    assert result["wind_speed"].iloc[0] == pytest.approx(10.0)


def test_normalize_units_rejects_negative_speed():
    df = pd.DataFrame({"wind_speed": [-1.0], "wind_direction": [0.0]})
    with pytest.raises(ValueError):
        normalize_units(df)


def test_normalize_units_rejects_unknown_unit():
    df = pd.DataFrame({"wind_speed": [1.0]})
    with pytest.raises(ValueError):
        normalize_units(df, speed_unit="mph")


def test_prepare_for_pathfinding_accepts_km_h_input():
    df = pd.DataFrame({
        "timestamp": ["2026-01-01T00:00:00"],
        "lat": [36.0],
        "lon": [58.0],
        "altitude": [500.0],
        "speed": [36.0],
        "direction": [90.0],
    })
    prep_df = prepare_for_pathfinding(
        df, lat_step=0.5, lon_step=0.5, altitude_levels=(500.0,), speed_unit="km/h"
    )
    assert np.isclose(prep_df["wind_speed"].iloc[0], 10.0)
