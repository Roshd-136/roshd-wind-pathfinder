"""Module for preparing wind data for pathfinding algorithms."""

import numpy as np
import pandas as pd

DEFAULT_ALTITUDES = (500.0, 1000.0, 1500.0, 2000.0)


def speed_direction_to_uv(
    wind_speed: pd.Series,
    wind_direction: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    direction_rad = np.deg2rad(wind_direction)
    u = -wind_speed * np.sin(direction_rad)
    v = -wind_speed * np.cos(direction_rad)
    return u, v


def uv_to_speed_direction(
    u: pd.Series,
    v: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    speed = np.sqrt(u**2 + v**2)
    direction = (np.degrees(np.arctan2(-u, -v)) + 360.0) % 360.0
    return speed, direction


def normalize_components(
    u: pd.Series,
    v: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    magnitude = np.sqrt(u**2 + v**2)
    safe_magnitude = magnitude.replace(0.0, np.nan)
    u_normalized = (u / safe_magnitude).fillna(0.0)
    v_normalized = (v / safe_magnitude).fillna(0.0)
    return u_normalized, v_normalized


def prepare_for_pathfinding(
    data: pd.DataFrame,
    lat_step: float,
    lon_step: float,
    altitude_levels: tuple[float, ...] = DEFAULT_ALTITUDES,
    normalize: bool = True,
) -> pd.DataFrame:
    required_base = {"lat", "lon", "altitude", "timestamp"}
    missing = required_base.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required base columns: {sorted(missing)}")

    if lat_step <= 0 or lon_step <= 0:
        raise ValueError("Grid steps must be positive.")

    result = data.copy()

    has_uv = {"u", "v"}.issubset(result.columns)
    has_speed_dir = {"wind_speed", "wind_direction"}.issubset(result.columns)

    if not has_uv and not has_speed_dir:
        raise ValueError("Input must contain either ('u', 'v') or ('wind_speed', 'wind_direction').")

    if has_speed_dir and not has_uv:
        result["u"], result["v"] = speed_direction_to_uv(result["wind_speed"], result["wind_direction"])

    if has_uv and not has_speed_dir:
        result["wind_speed"], result["wind_direction"] = uv_to_speed_direction(result["u"], result["v"])

    if normalize:
        result["u_normalized"], result["v_normalized"] = normalize_components(result["u"], result["v"])

    result = result[result["altitude"].isin(altitude_levels)].copy()

    lat_min, lat_max = result["lat"].min(), result["lat"].max()
    lon_min, lon_max = result["lon"].min(), result["lon"].max()

    lat_grid = np.arange(lat_min, lat_max + lat_step / 2, lat_step)
    lon_grid = np.arange(lon_min, lon_max + lon_step / 2, lon_step)

    grid = pd.MultiIndex.from_product(
        [result["timestamp"].unique(), altitude_levels, lat_grid, lon_grid],
        names=["timestamp", "altitude", "lat", "lon"],
    ).to_frame(index=False)

    result = grid.merge(result, on=["timestamp", "altitude", "lat", "lon"], how="left")
    return result.sort_values(["timestamp", "altitude", "lat", "lon"]).reset_index(drop=True)
