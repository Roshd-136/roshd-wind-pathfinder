# Pathfinding Wind Data Specification

## Overview
This document specifies the required input and normalized output data format for the AEROPATH routing algorithm.
Data reaches this format via `preprocessing.prepare_for_pathfinding` (see `docs/task_data_prep_pathfinding.md`).

## Accepted Input Units and Column Names

Input data does not need to already be in the canonical schema below.
`prepare_for_pathfinding` / `normalize_units` accept:
- Speed as `wind_speed` or `speed`, in `m/s` (default), `km/h`, or `kt`/`knots`
  (set via `speed_unit=`). Converted to m/s.
- Direction as `wind_direction` or `direction`, in degrees; any value is
  wrapped into `[0, 360)` (e.g. 400° becomes 40°, and negative values wrap
  the same way).
- Alternatively, `u`/`v` wind components directly, in m/s.

Wind speed must be non-negative; negative values raise a `ValueError` rather
than being silently coerced.

## Standard Output Columns
- `timestamp`: ISO-8601 formatted datetime.
- `lat`: Latitude in decimal degrees, on a regular grid at the requested `lat_step`.
- `lon`: Longitude in decimal degrees, on a regular grid at the requested `lon_step`.
- `altitude`: Height above ground level (m). Restricted to the requested `altitude_levels` (default: 500, 1000, 1500, 2000).
- `wind_speed`: Wind speed in m/s (always m/s regardless of input unit).
- `wind_direction`: Wind direction in degrees, `[0, 360)`.
- `u`: Zonal wind component (m/s).
- `v`: Meridional wind component (m/s).
- `u_normalized`: Vector-normalized u component.
- `v_normalized`: Vector-normalized v component.

Grid cells with no matching observation are still present in the output, with
wind-related columns left as `NaN` — the grid itself is always dense and
regular, even where data is sparse.
