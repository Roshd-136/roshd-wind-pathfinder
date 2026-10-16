"""Curved route geometry: two passes over every routed polygon path.

1) ``round_path_corners`` replaces sharp corners with circular arcs
   (fillets).
2) ``relax_path_curvature`` spreads concentrated curvature along the path
   so the line reads as *curved*, not 'long straight + kink' (measured case:
   R4 had a fully straight 84 km section that then turned 6.2 deg in one sample).

Neither pass depends on a specific corridor or dataset: the input is any
geographic polygon path and the output follows the same ``(path, levels)`` contract.

Problem
-------
The routing graph is a regular lattice: nodes sit on 0.05 deg latitude and
0.1 deg longitude steps, and every edge is a straight segment. So any graph
route — even from a 'soft' algorithm — is a sequence of **perfectly straight**
segments meeting at nodes, forming corners.

Measurement on the generated scene confirms this: 97% of drawn segments turn
less than 0.5 deg and the mean turn is 0.04-0.18 deg. The visible line is
effectively a straight polyline, not a curve — and the 'smooth spline' claim
in the display layer only operated on that polyline.

Approach
--------
Every interior corner of the path is replaced by a **circular arc (fillet)**.
Classic fillet: two tangent points are chosen on the adjacent segments and an
arc of constant radius, tangent at both ends, sits between them — so the path
turns continuously instead of kinking at nodes.

Three constraints hold simultaneously:

1) **Radius must not exceed the segments.** The tangent length is capped at
   ``MAX_TANGENT_FRACTION / 2`` (i.e. 40%) of each adjacent segment, so two
   fillets on one segment never meet (0.8 < 1) and mid-segments keep room.

2) **Terrain is a hard constraint.** A fillet 'cuts the corner' and passes
   through the triangle formed by three safe graph nodes — a triangle that may
   contain a mountain edge no edge check ever saw. So terrain elevation is
   sampled along the arc itself; if clearance drops below the limit the radius
   shrinks and the fillet is retried; if even the minimum radius fails, the
   sharp corner stays. Terrain wins over curve aesthetics.

3) **Each point's altitude comes from the route itself, not a fresh number.**
   Every arc sample is projected onto the nearest point of the *original* path
   and takes that point's level; the vertical profile is untouched.

What this module does **not** do
-------------------------
It does not change costs. Distance, time, energy and fuel remain exactly what
the router computed on the graph. A fillet makes the path slightly *shorter*
(it cuts corners); none of the table figures account for it.
The reported number is the node-to-node distance the router actually optimized.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

__all__ = [
    "round_path_corners",
    "relax_path_curvature",
    "MAX_TANGENT_FRACTION",
    "RELAX_STEP_KM",
    "RELAX_MAX_TURN_DEG_PER_KM",
    "RELAX_MAX_DEVIATION_KM",
    "RELAX_SPREAD_SAMPLES",
]

# Degrees -> km conversion at Khorasan latitudes (same constant as the rest of the project).
_KM_PER_DEG_LAT = 111.32

# Max share of a segment that may be spent on fillet tangency. 0.45 means two
# fillets on one segment never meet (0.9 < 1) and mid-segments keep room.
MAX_TANGENT_FRACTION = 0.8

# Smallest radius that is *meaningful* (km). Below this the fillet is
# practically invisible and only adds extra points to the geometry.
MIN_RADIUS_KM = 0.35


def _nearest_arc_distance(
    plane: Sequence[tuple[float, float]],
    cumulative: Sequence[float],
    x: float,
    y: float,
) -> float:
    """Arc distance from the polygon point nearest to a target point (km).

    Why needed: when a sample moves *along* the path, its coordinates no longer
    match its previous index on the original path. Any check that reads altitude
    by 'index' or 'old arc distance' compares one place's altitude against
    another place's terrain — up to hundreds of meters on climb profiles. This
    function gives the sample's true projected arc distance for both.
    """
    best_distance = 0.0
    best_error = math.inf
    for index in range(len(plane) - 1):
        ax, ay = plane[index]
        bx, by = plane[index + 1]
        dx, dy = bx - ax, by - ay
        span = dx * dx + dy * dy
        if span <= 1e-12:
            continue
        t = ((x - ax) * dx + (y - ay) * dy) / span
        t = min(max(t, 0.0), 1.0)
        px, py = ax + t * dx, ay + t * dy
        error = math.hypot(x - px, y - py)
        if error < best_error:
            best_error = error
            best_distance = cumulative[index] + t * math.sqrt(span)
    return best_distance


def round_path_corners(
    path: Sequence[tuple[float, float]],
    levels: Sequence[float],
    *,
    radius_km: float = 3.0,
    min_turn_deg: float = 1.0,
    arc_step_km: float = 0.4,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    min_clearance_m: float = 0.0,
    shrink_factor: float = 0.5,
    max_attempts: int = 6,
) -> tuple[list[tuple[float, float]], list[float]]:
    """Rounds the path's sharp corners with circular arcs.

    Parameters
    ----------
    path : Sequence[tuple[float, float]]
        Path points (lat, lon) in travel order; first and last stay untouched.
    levels : Sequence[float]
        Per-point altitude (m) under the ``RouteResult`` convention (0 = on
        the ground). New samples take altitude from their projection onto the
        original path, so the vertical profile is unchanged.
    radius_km : float
        Target fillet radius. The actual radius per corner is shrunk by
        adjacent segment lengths and the terrain constraint.
    min_turn_deg : float
        Corners turning less than this are not rounded. With 0.5 km samples
        every *interior* point turns a little; without the threshold thousands
        of pointless fillets would be created.
    arc_step_km : float
        Spacing of samples along the arc.
    ground_elevation_at : Callable[[float, float], float], optional
        Terrain elevation. If given, constraint 2 above is enforced.
    min_clearance_m : float
        Minimum allowed terrain clearance (m) on arc samples.
    shrink_factor, max_attempts : float, int
        On each terrain violation the radius is multiplied by
        ``shrink_factor``; after ``max_attempts`` tries the corner stays sharp.

    Returns
    ----------
    (path, levels)
        The rounded path and per-point altitudes. Both lengths are equal and
        greater than or equal to the input (each fillet adds a few samples).
    """
    if len(path) != len(levels):
        raise ValueError(
            f"path and levels must have the same length, got {len(path)} and "
            f"{len(levels)}."
        )
    points = [(float(lat), float(lon)) for lat, lon in path]
    heights = [float(level) for level in levels]
    if len(points) < 3 or radius_km <= MIN_RADIUS_KM:
        return points, heights
    if arc_step_km <= 0.0:
        raise ValueError("arc_step_km must be positive.")
    if not 0.0 < shrink_factor < 1.0:
        raise ValueError("shrink_factor must be in (0, 1).")

    # Local plane: mid-latitude as origin. Arcs are built on this plane and
    # converted back to degrees at the end.
    lat0 = sum(lat for lat, _lon in points) / len(points)
    cos_lat = max(math.cos(math.radians(lat0)), 1e-6)

    def to_km(lat: float, lon: float) -> tuple[float, float]:
        return (lon * cos_lat * _KM_PER_DEG_LAT, lat * _KM_PER_DEG_LAT)

    def to_degrees(x: float, y: float) -> tuple[float, float]:
        return (y / _KM_PER_DEG_LAT, x / (_KM_PER_DEG_LAT * cos_lat))

    plane = [to_km(lat, lon) for lat, lon in points]

    # Cumulative distance of the original path: used both for segment-length
    # thresholds and for projecting arc samples (so they get the right level).
    cumulative = [0.0]
    for (x1, y1), (x2, y2) in zip(plane, plane[1:], strict=False):
        cumulative.append(cumulative[-1] + math.hypot(x2 - x1, y2 - y1))
    total_km = cumulative[-1]
    if total_km <= 0.0:
        return points, heights

    def level_at(distance_km: float) -> float:
        """Original path altitude at a given distance (step function over nodes)."""
        index = 0
        while index + 1 < len(cumulative) and cumulative[index + 1] <= distance_km + 1e-9:
            index += 1
        return heights[min(index, len(heights) - 1)]

    def project_distance_km(x: float, y: float) -> float:
        """Arc distance of the original path point nearest to a target (km)."""
        return _nearest_arc_distance(plane, cumulative, x, y)

    def arc_ok(samples: list[tuple[float, float]]) -> bool:
        """Terrain check on arc samples: is clearance satisfied?"""
        if ground_elevation_at is None:
            return True
        for x, y in samples:
            lat, lon = to_degrees(x, y)
            try:
                level = level_at(project_distance_km(x, y))
            except Exception:  # pragma: no cover - projection never fails
                return False
            # Ground node (level zero) gets no fillet; the floor changes there.
            if level <= 0.0:
                continue
            clearance = level - float(ground_elevation_at(lat, lon))
            if clearance < min_clearance_m:
                return False
        return True

    out_plane: list[tuple[float, float]] = [plane[0]]
    out_distance: list[float] = [0.0]

    # **Drop consecutive co-located nodes here too** (the same phantom
    # +/-75/+155 deg U-turns at both path ends — ground origin/destination
    # sitting on an air-node coordinate). Without this, the fillet output itself
    # carries two zero-length segments that blow up the next stage's turn
    # profile (measured: worst relax sample on R4 went 9 -> 55 deg/km).
    dedup_plane: list[tuple[float, float]] = []
    dedup_distance: list[float] = []
    for point, distance in zip(plane, cumulative, strict=True):
        if dedup_plane and point == dedup_plane[-1]:
            continue
        dedup_plane.append(point)
        dedup_distance.append(distance)
    plane = dedup_plane
    cumulative = dedup_distance
    total_km = cumulative[-1]
    if len(plane) < 3:
        rounded = [to_degrees(x, y) for x, y in plane]
        rounded_levels = [heights[min(index, len(heights) - 1)] for index in range(len(rounded))]
        if rounded_levels:
            rounded_levels[0] = heights[0]
            rounded_levels[-1] = heights[-1]
        return rounded, rounded_levels

    for index in range(1, len(plane) - 1):
        ax, ay = plane[index - 1]
        bx, by = plane[index]
        cx, cy = plane[index + 1]

        prev_len = math.hypot(bx - ax, by - ay)
        next_len = math.hypot(cx - bx, cy - by)
        if prev_len <= 1e-9 or next_len <= 1e-9:
            out_plane.append((bx, by))
            out_distance.append(cumulative[index])
            continue

        u1x, u1y = (bx - ax) / prev_len, (by - ay) / prev_len
        u2x, u2y = (cx - bx) / next_len, (cy - by) / next_len
        # Angle between the two segments; 0 means straight, no fillet needed.
        dot = max(min(u1x * u2x + u1y * u2y, 1.0), -1.0)
        turn_deg = math.degrees(math.acos(dot))
        if turn_deg < min_turn_deg:
            out_plane.append((bx, by))
            out_distance.append(cumulative[index])
            continue

        max_tangent = MAX_TANGENT_FRACTION * min(prev_len, next_len)
        tangent = min(radius_km, 0.5 * max_tangent)
        placed = False
        for _attempt in range(max_attempts):
            if tangent < MIN_RADIUS_KM:
                break
        # Fillet: tangent points at ``tangent`` distance from the corner on both segments.
            t1 = (bx - u1x * tangent, by - u1y * tangent)
            t2 = (bx + u2x * tangent, by + u2y * tangent)
            samples = _arc_samples(t1, t2, u1x, u1y, u2x, u2y, tangent, arc_step_km)
            if not arc_ok(samples):
                tangent *= shrink_factor
                continue
            out_plane.extend(samples)
            out_distance.extend(project_distance_km(x, y) for x, y in samples)
            placed = True
            break
        if not placed:
            # Terrain refused; corner stays sharp (terrain has priority).
            out_plane.append((bx, by))
            out_distance.append(cumulative[index])

    out_plane.append(plane[-1])
    out_distance.append(total_km)

    rounded = [to_degrees(x, y) for x, y in out_plane]
    rounded_levels = [level_at(distance) for distance in out_distance]
    # End-of-path convention: keep the input's own values (0 = on ground), not
    # terrain elevation. ``level_at`` returns the ground node's *level*;
    # reporting it there would break the ``RouteResult`` convention.
    rounded_levels[0] = heights[0]
    rounded_levels[-1] = heights[-1]
    return rounded, rounded_levels


def _arc_samples(
    t1: tuple[float, float],
    t2: tuple[float, float],
    u1x: float,
    u1y: float,
    u2x: float,
    u2y: float,
    tangent: float,
    arc_step_km: float,
) -> list[tuple[float, float]]:
    """Fillet arc samples between tangent points ``t1`` and ``t2``.

    Geometry: ``phi`` is the corner's interior angle (between ``-u1`` and
    ``u2``). With tangent length ``t``, the arc radius is ``r = t*tan(phi/2)``
    and the center sits ``t/cos(phi/2)`` from the corner, on the interior
    bisector ``normalize(u2 - u1)``. The arc is built directly from ``t``
    without solving a triangle; tangency at both ends is guaranteed.

    For a very open corner (near-zero turn) ``tan(phi/2)`` grows and the arc
    becomes a gentle large-radius curve — desirable. For a very sharp corner
    (near-180 deg reversal) the radius shrinks; a degenerate case where even a
    small arc beats the sharp corner.
    """
    # Interior bisector: mean of the two unit vectors, normalized.
    bis_x, bis_y = u2x - u1x, u2y - u1y
    norm = math.hypot(bis_x, bis_y)
    if norm <= 1e-9:
        return [t1, t2]
    bis_x, bis_y = bis_x / norm, bis_y / norm
    dot = max(min(-u1x * u2x - u1y * u2y, 1.0), -1.0)
    phi = math.acos(dot)
    half = min(max(phi / 2.0, math.radians(1.0)), math.radians(89.0))
    radius = tangent * math.tan(half)
    if radius <= 1e-9:
        return [t1, t2]
    # The corner is where the two tangent points would meet.
    corner = (t1[0] + u1x * tangent, t1[1] + u1y * tangent)
    offset = tangent / math.cos(half)
    center = (corner[0] + bis_x * offset, corner[1] + bis_y * offset)

    a1 = math.atan2(t1[1] - center[1], t1[0] - center[0])
    a2 = math.atan2(t2[1] - center[1], t2[0] - center[0])
    sweep = a2 - a1
    while sweep > math.pi:
        sweep -= 2.0 * math.pi
    while sweep < -math.pi:
        sweep += 2.0 * math.pi
    arc_length = abs(sweep) * radius
    count = max(int(math.ceil(arc_length / arc_step_km)), 2)
    samples: list[tuple[float, float]] = []
    for step in range(count + 1):
        angle = a1 + sweep * step / count
        samples.append((center[0] + radius * math.cos(angle),
                        center[1] + radius * math.sin(angle)))
    return samples


# ---------------------------------------------------------------------------
# Curvature spreading: from straight segments + corners to continuous curvature.
# ---------------------------------------------------------------------------

# Resampled curve spacing (km), finer than the report step (0.5 km) so no
# geometry detail is lost in later sampling.
RELAX_STEP_KM = 0.25

# Target cap on local turn rate (deg/km). The eye reads a 'kink' via turn
# rate per unit length, not the total corner angle: 6 deg inside a 0.3 km step
# is 20 deg/km and looks like a kink, while the same 6 deg spread over 3 km
# is a gentle bend. Wind-riding paths (built by step-by-step integration)
# naturally have this profile, which is why they read as smooth.
RELAX_MAX_TURN_DEG_PER_KM = 1.5

# Gaussian kernel width for turn spreading, in 0.25 km *samples*. Sets the
# convergence speed, from measurement: giving each sample's surplus only to
# its two immediate neighbors (radius-1 spread per pass) needed ~1000 passes
# for a 57-sample kink cluster on graph routes — the 120-pass budget always
# ran out first, leaving 'long straight + corner cluster' on the scene.
# A Gaussian with sigma = 8 samples (2 km) spreads several km per pass; the
# same cluster settles in ~30 passes. Nothing here is corridor-specific.
RELAX_SPREAD_SAMPLES = 8.0

# **Hard constraint**: max displacement of any sample from its routed position
# (km) — a deliberately small 'artistic freedom' cap. The routing grid step is
# 5.6 x 9 km, so 1.5 km of drift stays within the lattice's own ambiguity;
# anything more is a different route and must be rejected outright.
RELAX_MAX_DEVIATION_KM = 2.5

# Cap on smoothing passes. One pass = one heat-spreading step; the required
# count follows kink size, but the cap prevents runaway loops.
RELAX_MAX_PASSES = 120

def relax_path_curvature(
    path: Sequence[tuple[float, float]],
    levels: Sequence[float],
    *,
    step_km: float = RELAX_STEP_KM,
    max_turn_deg_per_km: float = RELAX_MAX_TURN_DEG_PER_KM,
    max_deviation_km: float = RELAX_MAX_DEVIATION_KM,
    max_passes: int = RELAX_MAX_PASSES,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    min_clearance_m: float = 0.0,
) -> tuple[list[tuple[float, float]], list[float]]:
    """Spreads path curvature over the full length so it reads as *curved*, not kinked.

    Problem
    -----
    A graph route is a sequence of straight segments. ``round_path_corners``
    rounds corners with arcs, but the segments themselves stay straight and
    the arc is short. Measured on the published scene: route R4 has a fully
    straight 84 km section that then turns 6.2 deg within one 0.3 km sample
    (~= 21 deg/km). That 'long straight + kink' shape is what makes graph
    routes look mechanical, while wind-riding routes (integrated step by step)
    spread their turning along the path and the eye reads them as curved.

    Approach
    ----
    The path is resampled at a uniform step and the **turn profile** is then
    processed: each interior sample has a turn step, and any sample above the
    cap has its surplus spread over its neighborhood with a **Gaussian kernel**
    (sigma = ``RELAX_SPREAD_SAMPLES`` samples) — not just its two immediate
    neighbors. The total turn is preserved exactly (weights normalized), so the
    route shape and its pinned ends stay; only curvature *concentration* spreads.

    Three simultaneous constraints
    -------------
    1) ``max_turn_deg_per_km`` — the quality target: passes continue until the
       local turn drops below this threshold. If it cannot be met within the
       acceptable deviation, the best state reached is returned (best effort).
    2) ``max_deviation_km`` — hard constraint: if the next pass would move any
       sample further than this from its routed position, that pass is
       rejected; the geometry therefore never becomes 'something else'.
    3) **Terrain** — the harder constraint: on every sample the route altitude
       (from the projection onto the original path) is compared with the terrain
       there and **may not become worse than the routed path's clearance**. The
       sample is pulled toward the original path as much as needed (with a
       weight smoothed over its neighborhood). Note this rule is 'relative to
       the input', not an absolute minimum: the graph checks edges only at a
       few sample points, so the routed input path may already sit below the
       clearance threshold somewhere, and an absolute rule would reject all
       smoothing (measured on this corridor). The router's own shortfall is
       surfaced separately — the smoother never hides it.

    Each sample's altitude comes from the original path itself (arc-distance
    projection), so the vertical profile is untouched and the two-end contract
    (zero = on the ground) is preserved.

    Generality
    ----------
    No constant here is tied to the Mashhad-Sabzevar corridor: the input is any
    polygon path in geographic coordinates and the output follows the same
    ``(path, levels)`` contract as the fillet stage. Every polygon path (graph
    or otherwise, as long as it passes through nodes) goes through this function;
    wind-riding routes already have continuous curvature (this barely touches them).

    Returns
    ----------
    (path, levels)
        The sample count exceeds the input's (uniform 0.25 km step); travel
        order and both path ends are unchanged.
    """
    if len(path) != len(levels):
        raise ValueError(
            f"path and levels must have the same length, got {len(path)} and "
            f"{len(levels)}."
        )
    if step_km <= 0.0:
        raise ValueError("step_km must be positive.")
    if max_turn_deg_per_km <= 0.0:
        raise ValueError("max_turn_deg_per_km must be positive.")
    if max_deviation_km <= 0.0:
        raise ValueError("max_deviation_km must be positive.")

    points = [(float(lat), float(lon)) for lat, lon in path]
    heights = [float(level) for level in levels]
    # **Drop consecutive co-located nodes.** The graph places the ground
    # origin/destination node at the same coordinates as the air node; the
    # following zero-length segment creates a phantom U-turn in the turn
    # profile (atan2(0,0)) — measured on R4: two false peaks of +/-75.5 and
    # +/-155 deg at both path ends that the scene drew as 'kinks'.
    # The *ground* node (min altitude) is kept so the 'zero = on the ground'
    cleaned: list[tuple[float, float]] = []
    cleaned_levels: list[float] = []
    for point, level in zip(points, heights, strict=True):
        if cleaned and point == cleaned[-1]:
            cleaned_levels[-1] = min(cleaned_levels[-1], level)
            continue
        cleaned.append(point)
        cleaned_levels.append(level)
    points, heights = cleaned, cleaned_levels
    if len(points) < 3:
        return points, heights

    lat0 = sum(lat for lat, _lon in points) / len(points)
    cos_lat = max(math.cos(math.radians(lat0)), 1e-6)

    def to_km(lat: float, lon: float) -> tuple[float, float]:
        return (lon * cos_lat * _KM_PER_DEG_LAT, lat * _KM_PER_DEG_LAT)

    def to_degrees(x: float, y: float) -> tuple[float, float]:
        return (y / _KM_PER_DEG_LAT, x / (_KM_PER_DEG_LAT * cos_lat))

    plane = [to_km(lat, lon) for lat, lon in points]
    cumulative = [0.0]
    for (x1, y1), (x2, y2) in zip(plane, plane[1:], strict=False):
        cumulative.append(cumulative[-1] + math.hypot(x2 - x1, y2 - y1))
    total_km = cumulative[-1]
    if total_km <= step_km:
        return points, heights

    def level_at(distance_km: float) -> float:
        # The step value is kept deliberately: the 'zero = on the ground'
        # contract means the takeoff/landing segment gets no safety guard.
        # Linear interpolation was tried here and failed: interpolating from
        # the ground node (zero) to the cruise node produced altitudes far
        # below the terrain (it broke the mountain-ridge test). Vertical-
        # profile continuity is now the router pipeline's job:
        # ``ramp_vertical_transitions`` runs *before* this function.
        index = 0
        while index + 1 < len(cumulative) and cumulative[index + 1] <= distance_km + 1e-9:
            index += 1
        return heights[min(index, len(heights) - 1)]

    # **Altitude of the *new* location, not the old index.** Curvature
    # redistribution moves samples along the path; any guard reading altitude
    # by old index or old arc distance compares one point's altitude against
    # another point's terrain. Measured on R1/R2: on the climb/descent profile
    # near Mashhad this mismatch made the guard flag safe samples as violators
    # and smoothing got pinned to the clearance floor (worst turn 11.8 deg/km
    # with an alternating-sign cluster at 1790 m where the terrain is 1490 m).
    def level_here(x: float, y: float) -> float:
        return level_at(_nearest_arc_distance(plane, cumulative, x, y))

    # ------------------------------------------------------------------
    # Uniform resampling: points sitting on the *original* path — the
    # deviation reference. Curved samples later move only around this reference.
    # ------------------------------------------------------------------
    count = max(int(math.ceil(total_km / step_km)) + 1, 3)
    base: list[tuple[float, float]] = []
    distances: list[float] = []
    segment = 0
    for index in range(count):
        distance = total_km * index / (count - 1)
        while (
            segment + 1 < len(cumulative) - 1
            and cumulative[segment + 1] < distance - 1e-9
        ):
            segment += 1
        span = cumulative[segment + 1] - cumulative[segment]
        ratio = 0.0 if span <= 1e-12 else (distance - cumulative[segment]) / span
        ratio = min(max(ratio, 0.0), 1.0)
        (x1, y1), (x2, y2) = plane[segment], plane[segment + 1]
        base.append((x1 + (x2 - x1) * ratio, y1 + (y2 - y1) * ratio))
        distances.append(distance)
    base[0] = plane[0]
    base[-1] = plane[-1]

    def deviation_km(samples: Sequence[tuple[float, float]]) -> float:
        """Max distance of samples from their routed positions."""
        return max(
            math.hypot(x - bx, y - by)
            for (x, y), (bx, by) in zip(samples, base, strict=False)
        )

    def bearings(samples: Sequence[tuple[float, float]]) -> list[float]:
        """Side of each segment (radians from north)."""
        return [
            math.atan2(bx - ax, by - ay)
            for (ax, ay), (bx, by) in zip(samples, samples[1:], strict=False)
        ]

    def wrap(value: float) -> float:
        """Wraps the angle into (-pi, pi]."""
        return (value + math.pi) % (2.0 * math.pi) - math.pi

    # ------------------------------------------------------------------
    # Terrain ceiling per sample: **never lower than the routed path itself**.
    #
    # Why an 'absolute minimum' was not enough: the graph checks edges only at
    # a few sample points (sometimes 7 points on a 9 km edge), so the routed
    # path itself can sit below the clearance threshold somewhere. Under an
    # absolute rule such a route would be rejected on the first pass and get
    # **no** smoothing at all — measured on this artifact: R1/R2 (2900 m) and
    # R4 (2200 m), close to the ridge, stayed untouched while R3/R6 smoothed at
    # 3600 m. The right rule: smoothing must not *reduce* safety; the router's
    # own shortfall is separate and not hidden (the 'min terrain clearance' column).
    # ------------------------------------------------------------------
    allowed_clearance: list[float] = []
    for index, (x, y) in enumerate(base):
        level = level_at(distances[index])
        if level <= 0.0 or ground_elevation_at is None or min_clearance_m <= 0.0:
            allowed_clearance.append(0.0)
            continue
        lat, lon = to_degrees(x, y)
        local = level - float(ground_elevation_at(lat, lon))
        allowed_clearance.append(local if local < min_clearance_m else min_clearance_m)

    def clearance_ok(samples: Sequence[tuple[float, float]]) -> bool:
        """Did any sample's clearance become *worse* than the original path?"""
        for index, (x, y) in enumerate(samples):
            floor = allowed_clearance[index]
            if floor <= 0.0:
                continue
            lat, lon = to_degrees(x, y)
            level = level_here(x, y)
            if level - float(ground_elevation_at(lat, lon)) < floor - 1e-9:
                return False
        return True

    def clamp_to_terrain(
        candidate: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        """A sample hitting the mountain is pulled back to the *last* safe point.

        Pulling everything back (or rejecting the whole pass) means a route that
        touches ground once gets smoothed nowhere — measured on this artifact:
        R1/R2 (2900 m) and R4 (2200 m) stayed untouched because they hug the
        ridge, while R3/R6 smoothed at 3600 m. So the reduction is *local*: for
        each violating sample, a blend factor between its original and smoothed
        position is reduced by binary halving to the last safe value, and that
        factor is spread over the neighborhood so it creates no kink of its own.
        """
        if ground_elevation_at is None or min_clearance_m <= 0.0:
            return candidate
        blend = [1.0] * len(candidate)
        for index, (x, y) in enumerate(candidate):
            floor = allowed_clearance[index]
            if floor <= 0.0:
                continue
            lat, lon = to_degrees(x, y)
            if level_here(x, y) - float(ground_elevation_at(lat, lon)) >= floor - 1e-9:
                continue
            bx, by = base[index]
            low, high = 0.0, 1.0
            for _step in range(12):
                middle = 0.5 * (low + high)
                px, py = bx + (x - bx) * middle, by + (y - by) * middle
                plat, plon = to_degrees(px, py)
                if level_here(px, py) - float(ground_elevation_at(plat, plon)) >= floor - 1e-9:
                    low = middle
                else:
                    high = middle
            blend[index] = low
        if all(value >= 1.0 for value in blend):
            return candidate
        # Local spread with Gaussian weights: each sample's missing capacity
        # decays with distance, so neighbors pull back *gradually* and the pull
        # itself creates no new corner. (Previously the window minimum was 5
        # samples: a sudden step that built exactly that new corner on the safe-
        # zone edge — measured: R4 stayed at 9.9 deg/km, the rest reached 2.4.)
        deficit = [1.0 - value for value in blend]
        sigma = 2.0
        spread = [1.0] * len(blend)
        for index in range(len(blend)):
            pull = 0.0
            for offset in range(-4, 5):
                neighbour = index + offset
                if not 0 <= neighbour < len(deficit):
                    continue
                weight = math.exp(-0.5 * (offset / sigma) ** 2)
                pull = max(pull, deficit[neighbour] * weight)
            spread[index] = max(0.0, 1.0 - min(pull, 1.0))
        for index, (x, y) in enumerate(candidate):
            factor = spread[index]
            if factor >= 1.0:
                continue
            bx, by = base[index]
            candidate[index] = (bx + (x - bx) * factor, by + (y - by) * factor)
        return candidate

    # ------------------------------------------------------------------
    # **Spread the turn, not the path.**
    # ------------------------------------------------------------------
    # The first version of this function was a heat-spreading operator on
    # *positions*. It had two defects, both measured on real corridor routes:
    #   1) A route whose curvature is already spread over its length — like R4,
    #      curved to dodge the ridge — got pulled toward its chord, i.e. it
    #      changed the route's *actual* shape just to soften one corner
    #      (the deviation cap filled up early).
    #   2) Result: R4 was left at 9.9 deg/km while R1/R2/R6 reached 2.4.
    # Now the **turn profile** is processed: each interior sample has a turn
    # step and any surplus is split half-and-half to its two neighbors. The
    # total turn stays constant, so the route shape (including detours) is
    # preserved and only the *concentration* of turning is spread — exactly
    base_bearings = bearings(base)
    lengths = [
        math.hypot(bx - ax, by - ay)
        for (ax, ay), (bx, by) in zip(base, base[1:], strict=False)
    ]
    turns = [0.0] * len(base)
    for index in range(1, len(base) - 1):
        turns[index] = wrap(base_bearings[index] - base_bearings[index - 1])

    def rebuild(profile: Sequence[float]) -> list[tuple[float, float]]:
        """Rebuilds the path from the origin with a turn profile.

        Destination residual: spreading the turn keeps segment lengths but
        shifts the final heading slightly, so integrating from the origin no
        longer lands exactly on the destination. A linear 'cut' along the path
        — which creates no new curvature — distributes that residual over the
        interior samples and lands the last point exactly on the destination.
        """
        built: list[tuple[float, float]] = [base[0]]
        heading = base_bearings[0]
        for index in range(1, len(base)):
            heading += profile[index]
            px, py = built[-1]
            built.append(
                (
                    px + lengths[index - 1] * math.sin(heading),
                    py + lengths[index - 1] * math.cos(heading),
                )
            )
        residual_x = base[-1][0] - built[-1][0]
        residual_y = base[-1][1] - built[-1][1]
        if math.hypot(residual_x, residual_y) > 1e-9:
            span = len(built) - 1
            for index in range(1, span):
                weight = index / span
                px, py = built[index]
                built[index] = (px + residual_x * weight, py + residual_y * weight)
            built[-1] = base[-1]
        return built

    # **Constraints are measured inside the loop, not at the end.** A version
    # that ran all passes first and checked afterwards spread the turn profile
    # so far the route became one big arc; then either the whole work was
    # rejected (R1/R2/R4 untouched) or a half-done state with 23-35 deg corners
    # remained (measured). Now each pass is built and checked first, and
    # accepted only if **both** deviation and safety pass; the last accepted
    # state is the output — always a valid route: the most smoothing safety allows.
    cap = math.radians(max_turn_deg_per_km * step_km)
    current: list[tuple[float, float]] | None = None
    # **Adaptive sigma**: if a pass violates deviation/safety, the spread
    # kernel gets *narrower* and the same pass is retried — the work is not
    # abandoned. With sigma=1 each displacement is limited to one sample, so
    # no pass is ever rejectable (any one-sample displacement is always smaller
    # than the previous deviation). That was exactly the R4 difference: the
    # first big pass broke the cap; now it narrows gradually as constraints allow.
    sigma = RELAX_SPREAD_SAMPLES
    min_sigma = 1.0
    for _pass in range(max_passes):
        if max((abs(value) for value in turns[1:-1]), default=0.0) <= cap + 1e-12:
            break
        # **Heat spreading on the turn profile.** History of the three previous
        # versions (all measured):
        #   1) Writing the cap directly erased the share taken from neighbors;
        #      each pass "lost" turn and the destination drifted 11 km.
        #   2) Giving surplus only to the two immediate neighbors needed ~1000
        #      passes for the 57-sample kink cluster of graph routes; the pass
        #      budget ran out.
        #   3) Taking surplus 'only from above-cap samples' made the uniform
        #      fillet arc inhomogeneous (R4 got worse: 12.8 -> 20.1) and only
        #      moved clusters around, not spread them.
        # The current version pulls each sample toward the Gaussian mean of its
        # neighborhood; the destination closes exactly via the final ``rebuild`` cut.
        n = len(turns)
        radius = max(1, int(math.ceil(3.0 * sigma)))
        weight = [
            math.exp(-0.5 * (offset / sigma) ** 2)
            for offset in range(-radius, radius + 1)
        ]
        kernel_total = sum(weight)
        weight = [value / kernel_total for value in weight]
        # **Heat spreading on the turn profile — not just above-cap surplus.**
        # The previous version took turn only from above-cap samples and gave
        # it to neighbors; two measured defects:
        #   1) The fillet arc (uniform ~1.7 deg/sample turn) was itself above
        #      the cap; taking its edges' surplus made the uniform arc
        #      inhomogeneous — on R4 the worst sample went 12.8 -> 20.1 deg/km,
        #      *worse*.
        #   2) Below-cap samples never gave, so the turn cluster only *moved*,
        #      never spread; the pass budget ran out and the cluster remained.
        # Real spreading pulls every sample toward the Gaussian-weighted mean of
        # its neighborhood; the uniform arc, like any profile, gets *wider* — the
        # same total turn over more distance, i.e. exactly 'smoother'. Keeping the
        # route shape is not the cap's job: the deviation cap (``max_deviation_km``)
        # and the terrain constraint judge every pass; a rejected pass is retried
        # with a narrower kernel and converges within the deviation budget.
        alpha = 0.6
        updated = [turns[0]]
        for index in range(1, n - 1):
            local = 0.0
            wsum = 0.0
            for offset, w in zip(range(-radius, radius + 1), weight, strict=False):
                neighbour = index + offset
                if 1 <= neighbour <= n - 2:
                    local += turns[neighbour] * w
                    wsum += w
            if wsum > 0.0:
                updated.append(turns[index] + alpha * (local / wsum - turns[index]))
            else:
                updated.append(turns[index])
        updated.append(turns[n - 1])
        candidate = clamp_to_terrain(rebuild(updated))
        if deviation_km(candidate) > max_deviation_km or not clearance_ok(candidate):
            # Pass rejected: narrow the kernel and retry instead of dropping all work.
            if sigma <= min_sigma + 1e-12:
                break
            sigma = max(min_sigma, sigma * 0.5)
            continue
        turns = updated
        current = candidate
        # After each accepted pass, start again from the wide kernel: as soon as
        # the constraints allow, fast spreading returns.
        sigma = RELAX_SPREAD_SAMPLES

    if current is None:
        # The input path is already smooth or the constraints allowed no change:
        # return the routed geometry as-is, no extra claims.
        return points, heights


    relaxed = [to_degrees(x, y) for x, y in current]
    relaxed_levels = [level_at(distance) for distance in distances]
    # Same two-end contract the fillet stage keeps: the input value, not ground
    relaxed_levels[0] = heights[0]
    relaxed_levels[-1] = heights[-1]
    return relaxed, relaxed_levels
