# Pathfinding Wind Data Specification

## Overview
This document specifies the required input and normalized output data format for the AEROPATH routing algorithm.

## Standard Columns
- `timestamp`: ISO-8601 formatted datetime.
- `lat`: Latitude in decimal degrees.
- `lon`: Longitude in decimal degrees.
- `altitude`: Height above ground level (m).
- `u`: Zonal wind component (m/s).
- `v`: Meridional wind component (m/s).
- `u_normalized`: Vector-normalized u component.
- `v_normalized`: Vector-normalized v component.
