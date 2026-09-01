"""Module for preparing wind data for pathfinding algorithms."""

import numpy as np
import pandas as pd

DEFAULT_ALTITUDES = (500.0, 1000.0, 1500.0, 2000.0)

# Accepted input column aliases -> canonical column name.
# Upstream tasks (QC, IDW, Kriging) do not all agree on column names, so we
# accept the common variants instead of silently failing or duplicating data.
SPEED_ALIASES = ("wind_speed", "speed")
DIRECTION_ALIASES = ("wind_direction", "direction")

# Supported speed units and their conversion factor to m/s (the canonical unit).
SPEED_UNIT_TO_MPS = {
    "m/s": 1.0,
    "km/h": 1.0 / 3.6,
    "kmh": 1.0 / 3.6,
    "kt": 0.514444,
    "knots": 0.514444,
}


def _resolve_alias(columns: pd.Index, aliases: tuple[str, ...]) -> str | None:
    """Return the first alias present in ``columns``, or ``None``."""
    for alias in aliases:
        if alias in columns:
            return alias
    return None


def normalize_units(
    data: pd.DataFrame,
    speed_unit: str = "m/s",
) -> pd.DataFrame:
    """Unify wind speed/direction columns onto the canonical schema.

    - Speed columns (``wind_speed`` or ``speed``) are converted to m/s and
      renamed to ``wind_speed``.
    - Direction columns (``wind_direction`` or ``direction``) are wrapped into
      the ``[0, 360)`` degree range and renamed to ``wind_direction``.

    ``data`` is not required to contain speed/direction at all (a caller may
    be supplying ``u``/``v`` directly); in that case the frame is returned
    unchanged aside from a copy.
    """
    if speed_unit not in SPEED_UNIT_TO_MPS:
        raise ValueError(
            f"Unsupported speed_unit {speed_unit!r}; expected one of {sorted(SPEED_UNIT_TO_MPS)}"
        )

    result = data.copy()

    speed_col = _resolve_alias(result.columns, SPEED_ALIASES)
    if speed_col is not None:
        factor = SPEED_UNIT_TO_MPS[speed_unit]
        speed_mps = result[speed_col].astype(float) * factor
        if (speed_mps < 0).any():
            raise ValueError("Wind speed cannot be negative.")
        if speed_col != "wind_speed":
            result = result.drop(columns=[speed_col])
        result["wind_speed"] = speed_mps

    direction_col = _resolve_alias(result.columns, DIRECTION_ALIASES)
    if direction_col is not None:
        direction_deg = result[direction_col].astype(float) % 360.0
        if direction_col != "wind_direction":
            result = result.drop(columns=[direction_col])
        result["wind_direction"] = direction_deg

    return result


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
    speed_unit: str = "m/s",
) -> pd.DataFrame:
    required_base = {"lat", "lon", "altitude", "timestamp"}
    missing = required_base.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required base columns: {sorted(missing)}")

    if lat_step <= 0 or lon_step <= 0:
        raise ValueError("Grid steps must be positive.")

    result = normalize_units(data, speed_unit=speed_unit)

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
