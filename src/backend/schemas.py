"""اعتبارسنجی ورودی و مدل‌های درخواست — مطابق ``RouteRequest`` در ``api/openapi.yaml``."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from backend.errors import ValidationFailed

__all__ = [
    "Coordinate",
    "AvoidZone",
    "Constraints",
    "RouteRequest",
    "parse_route_request",
    "parse_coordinate",
    "ALGORITHMS",
    "CRITERIA",
]

ALGORITHMS = ("a_star", "dijkstra")
CRITERIA = ("time", "energy", "balanced")
_MAX_CHECKPOINTS = 10
_MAX_AVOID_ZONES = 20


@dataclass(frozen=True)
class Coordinate:
    lat: float
    lon: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.lat, self.lon)


@dataclass(frozen=True)
class AvoidZone:
    center: Coordinate
    radius_km: float


@dataclass(frozen=True)
class Constraints:
    max_wind_speed_mps: float | None = None
    altitude_range_m: tuple[float, float] | None = None
    avoid_zones: tuple[AvoidZone, ...] = ()
    criterion: str = "time"
    time_weight: float = 0.5  # فقط برای criterion=balanced معنی دارد


@dataclass(frozen=True)
class RouteRequest:
    origin: Coordinate
    destination: Coordinate
    checkpoints: tuple[Coordinate, ...] = ()
    layer_mode: str = "auto"
    altitude_m: float | None = None
    algorithm: str = "a_star"
    constraints: Constraints = field(default_factory=Constraints)
    is_async: bool = False


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_coordinate(raw: Any, name: str, issues: list[tuple[str, str]]) -> Coordinate | None:
    """یک مختصات ``{lat, lon}`` را اعتبارسنجی می‌کند؛ مشکلات را در ``issues`` جمع می‌کند."""
    if not isinstance(raw, dict):
        issues.append((name, "must be an object with lat and lon"))
        return None
    ok = True
    for key, lo, hi in (("lat", -90.0, 90.0), ("lon", -180.0, 180.0)):
        val = raw.get(key)
        if val is None:
            issues.append((f"{name}.{key}", "is required"))
            ok = False
        elif not _num(val):
            issues.append((f"{name}.{key}", "must be a finite number"))
            ok = False
        elif not lo <= val <= hi:
            issues.append((f"{name}.{key}", f"must be within [{lo:g}, {hi:g}]"))
            ok = False
    return Coordinate(float(raw["lat"]), float(raw["lon"])) if ok else None


def _parse_constraints(raw: Any, issues: list[tuple[str, str]]) -> Constraints:
    if raw is None:
        return Constraints()
    if not isinstance(raw, dict):
        issues.append(("constraints", "must be an object"))
        return Constraints()

    max_wind = raw.get("max_wind_speed_mps")
    if max_wind is not None and (not _num(max_wind) or max_wind <= 0):
        issues.append(("constraints.max_wind_speed_mps", "must be a positive number or null"))
        max_wind = None

    alt_range = raw.get("altitude_range_m")
    parsed_range: tuple[float, float] | None = None
    if alt_range is not None:
        if (
            not isinstance(alt_range, (list, tuple))
            or len(alt_range) != 2
            or not all(_num(a) for a in alt_range)
        ):
            issues.append(("constraints.altitude_range_m", "must be [min, max] numbers or null"))
        elif alt_range[0] > alt_range[1]:
            issues.append(("constraints.altitude_range_m", "min must be <= max"))
        else:
            parsed_range = (float(alt_range[0]), float(alt_range[1]))

    zones: list[AvoidZone] = []
    raw_zones = raw.get("avoid_zones") or []
    if not isinstance(raw_zones, list):
        issues.append(("constraints.avoid_zones", "must be an array"))
        raw_zones = []
    if len(raw_zones) > _MAX_AVOID_ZONES:
        issues.append(("constraints.avoid_zones", f"at most {_MAX_AVOID_ZONES} zones allowed"))
        raw_zones = raw_zones[:_MAX_AVOID_ZONES]
    for i, z in enumerate(raw_zones):
        name = f"constraints.avoid_zones[{i}]"
        if not isinstance(z, dict) or z.get("type") != "circle":
            issues.append((name, "must be an object with type 'circle'"))
            continue
        center = parse_coordinate(z.get("center"), f"{name}.center", issues)
        radius = z.get("radius_km")
        if not _num(radius) or radius < 0:
            issues.append((f"{name}.radius_km", "must be a non-negative number"))
        elif center is not None:
            zones.append(AvoidZone(center, float(radius)))

    criterion = raw.get("criterion", "time")
    if criterion not in CRITERIA:
        issues.append(("constraints.criterion", f"must be one of {list(CRITERIA)}"))
        criterion = "time"

    time_weight = 0.5
    weights = raw.get("weights")
    if weights is not None:
        if not isinstance(weights, dict):
            issues.append(("constraints.weights", "must be an object"))
        else:
            wt, we = weights.get("time", 0.5), weights.get("energy", 0.5)
            if not (_num(wt) and _num(we)) or wt < 0 or we < 0:
                issues.append(("constraints.weights", "time and energy must be non-negative numbers"))
            elif abs(wt + we - 1.0) > 1e-6:
                issues.append(("constraints.weights", "time + energy must sum to 1"))
            else:
                time_weight = float(wt)

    return Constraints(
        max_wind_speed_mps=None if max_wind is None else float(max_wind),
        altitude_range_m=parsed_range,
        avoid_zones=tuple(zones),
        criterion=criterion,
        time_weight=time_weight,
    )


def parse_route_request(raw: Any) -> RouteRequest:
    """بدنه JSON را به ``RouteRequest`` تبدیل می‌کند؛ در صورت مشکل ``ValidationFailed``."""
    issues: list[tuple[str, str]] = []
    if not isinstance(raw, dict):
        raise ValidationFailed([("body", "must be a JSON object")])

    origin = parse_coordinate(raw.get("origin"), "origin", issues) if "origin" in raw else None
    if "origin" not in raw:
        issues.append(("origin", "is required"))
    destination = (
        parse_coordinate(raw.get("destination"), "destination", issues)
        if "destination" in raw
        else None
    )
    if "destination" not in raw:
        issues.append(("destination", "is required"))
    if origin and destination and origin == destination:
        issues.append(("destination", "must differ from origin"))

    checkpoints: list[tuple[int, int, Coordinate]] = []
    raw_cps = raw.get("checkpoints") or []
    if not isinstance(raw_cps, list):
        issues.append(("checkpoints", "must be an array"))
        raw_cps = []
    if len(raw_cps) > _MAX_CHECKPOINTS:
        issues.append(("checkpoints", f"at most {_MAX_CHECKPOINTS} checkpoints allowed"))
        raw_cps = raw_cps[:_MAX_CHECKPOINTS]
    for i, cp in enumerate(raw_cps):
        c = parse_coordinate(cp, f"checkpoints[{i}]", issues)
        order = cp.get("order", i) if isinstance(cp, dict) else i
        if not isinstance(order, int) or isinstance(order, bool):
            issues.append((f"checkpoints[{i}].order", "must be an integer"))
            order = i
        if c is not None:
            checkpoints.append((order, i, c))

    layer_mode = raw.get("layer_mode", "auto")
    if layer_mode not in ("auto", "manual"):
        issues.append(("layer_mode", "must be 'auto' or 'manual'"))
    altitude = raw.get("altitude_m")
    if altitude is not None and not _num(altitude):
        issues.append(("altitude_m", "must be a number or null"))
        altitude = None
    if layer_mode == "manual" and altitude is None:
        issues.append(("altitude_m", "is required when layer_mode is 'manual'"))

    algorithm = raw.get("algorithm", "a_star")
    if algorithm not in ALGORITHMS:
        issues.append(("algorithm", f"must be one of {list(ALGORITHMS)}"))

    is_async = raw.get("async", False)
    if not isinstance(is_async, bool):
        issues.append(("async", "must be a boolean"))
        is_async = False

    constraints = _parse_constraints(raw.get("constraints"), issues)

    if issues:
        raise ValidationFailed(issues)
    assert origin is not None and destination is not None
    return RouteRequest(
        origin=origin,
        destination=destination,
        checkpoints=tuple(c for _, _, c in sorted(checkpoints, key=lambda t: (t[0], t[1]))),
        layer_mode=layer_mode,
        altitude_m=None if altitude is None else float(altitude),
        algorithm=algorithm,
        constraints=constraints,
        is_async=is_async,
    )
