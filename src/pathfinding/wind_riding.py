"""Wind-riding routing — one fixed heading, and the wind carries the route.

Route idea
----------
Graph routing (A*/Dijkstra) builds the route over a node lattice, so the path is
inevitably "staircased" and every step needs a motor heading correction. In this
wind field (wind mostly east-to-west, i.e. aligned with the Mashhad->Sabzevar
corridor) there is another option the graph cannot express:

1) climb to a layer,
2) hold **one** fixed air heading,
3) let the wind push the aircraft forward — the ground track becomes whatever
   the wind wants,

"Wind riding" is exactly this. The heading is chosen with a one-parameter
search: for each candidate heading the ground track is *integrated*, and the
heading reaching the destination in the least total time wins. The layer is
selected with the same criterion (climb + wind riding + descent + final leg).

Honesty notes
-----------
- This planner integrates over the *wind field*, not the graph. Its
  distance/time come from the same wind field used for graph routes
  (``LayerField``), but the path is built in continuous space and may bypass
  graph nodes. So "shortest graph route" and "wind riding" are two different
  routing models; the numbers are comparable because both read the same
  wind field, but the geometries differ by construction.
- Below the lowest layer (AGL < 500 m) the wind field is undefined; during the
  descent phase the **lowest available layer** wind is used. That is a data
  limitation, not a physical assumption.
- The climb happens at a single point (same convention as the graph's vertical
  edges). Climbing while moving is not modeled.
- **Descent is a *glide slope*, not a dive.** Descent begins when the remaining
  distance equals ``h · descent_glideslope_ratio`` and then follows that fixed
  slope down to the destination's ground elevation. The default slope (1 in 40)
  is deliberately *gentler* than max glide (1 in L/D = 1 in 12) — i.e. a dead
  engine cannot sustain it; so the engine runs at *partial* power, and that
  power is genuinely accounted for. From the thrust balance at landing
  (``T = D − m·g·sinγ`` and ``D = m·g/(L/D)``) the power fraction
  ``1 − (L/D)·sinγ`` follows; if the required slope steepens beyond max glide,
  ``descent_idle_power_fraction`` is the floor.
- **The profile shape does not make fuel free.** Softening the descent means
  more distance spent under the slope and that distance is taken from cruise;
  energy conservation says for a route that starts and ends on the ground the
  only real cost is *work against drag along the path*, not the altitude
  profile shape. So a soft descent costs roughly the same as a steep one,
  and what changes is only how the same total work is distributed.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from pathfinding.alignment import wind_alignment_profile
from pathfinding.cost import CostModelConfig, compute_edge_cost, initial_bearing_deg
from pathfinding.effort import LegSample, MotorEffortConfig, compute_route_effort
from pathfinding.graph import VerticalCostConfig, compute_vertical_cost
from pathfinding.profile import ramp_vertical_transitions
from pathfinding.routing import RouteResult
from preprocessing.consistency import haversine_km

__all__ = [
    "WindSampler",
    "WindRidingConfig",
    "WindRidingPlan",
    "plan_wind_riding_route",
    "wind_riding_route_result",
]

# Wind sampler for one layer: ``(lat, lon) -> (speed_mps, direction_from_deg)``.
WindSampler = Callable[[float, float], tuple[float, float]]

_KM_PER_DEG_LAT = 111.32

@dataclass(frozen=True)
class WindRidingConfig:
    """Numerical parameters for wind-riding planning (all are computational
    parameters, not physical hypotheses).

    Parameters
    ----------
    step_s : float
        Time integration step (seconds). Smaller = more accurate, slower.
    max_hours : float
        Simulation time cap per candidate heading (hours).
    max_arrival_miss_km : float
        Maximum acceptable final distance from the destination (km). Plans
        worse than this are rejected; the remainder is closed with a final leg.
    arrival_radius_km : float
        Distance at which "arrival" is accepted.
    heading_coarse_step_deg : float
        Coarse sweep step over the 360 degrees.
    heading_refine_steps_deg : tuple[float, ...]
        Successive refinement steps: each stage sweeps around the previous
        stage's best heading, within +/- the previous stage's step, using this
        stage's step. Several stages are needed because "arrival error" is
        sensitive to heading: with a single 0.25 deg stage the route landed
        several hundred meters past the destination, and that residual forced
        a final leg (and one more heading correction) — defeating the whole
        point of a single clean wind-riding ride.
    path_sample_s : float
        Time step for holding a point/segment in the reported route (seconds).
        Integration uses ``step_s``; for the route, one point is kept per
        ``path_sample_s``, otherwise the route becomes hundreds of segments
        and values reconstructed from chords turn noisy.
    abandon_margin_km : float
        Search pruning rule: if the distance to the destination exceeds the
        best distance seen so far in the same simulation by more than this
        value, that heading is abandoned. Headings that never reach the
        destination would otherwise run to ``max_hours`` and slow the whole
        search. This is purely a *computational* rule: an abandoned heading can
    descent_glideslope_ratio : float
        Descent slope as "1 in N" — for every meter of altitude lost, N meters
        flown forward. The aircraft's *maximum* glide range is ``L/D``; a
        larger value means a gentler, longer descent possible only with slight
        engine power (accounted in ``power_fraction`` of descent segments). A
        value below ``L/D`` means descending steeper than glide: part of the
        energy comes from descending faster.
    approach_km : float
        Final approach length (km). The terrain clearance floor only matters
        over *mountains*; in these last kilometers the floor ramps linearly
        from `terrain + threshold` down to the destination's ground elevation so
        landing on the destination becomes possible. Without this transition,
    """

    step_s: float = 20.0
    max_hours: float = 8.0
    max_arrival_miss_km: float = 2.0
    arrival_radius_km: float = 0.2
    heading_coarse_step_deg: float = 4.0
    heading_refine_steps_deg: tuple[float, ...] = (1.0, 0.1)
    path_sample_s: float = 120.0
    abandon_margin_km: float = 5.0
    descent_glideslope_ratio: float = 40.0
    approach_km: float = 3.0
    track_wind: bool = True
    wind_corridor_fraction: float = 0.5
    wind_corridor_min_km: float = 0.2
    # **Policy search, not one fixed policy.** The ``wind_corridor_fraction``
    # corridor decides how far the aircraft may stray from the origin-destination
    # line while staying "parallel to the wind". This is a *trade-off*, not a
    # right/wrong choice: a wider corridor means a larger share of wind-parallel
    # flight at the cost of more distance/time/fuel and a bigger final
    # correction. Measurement on this corridor (the "wind-riding trade-off"
    # table in the scene) shows the parallel share goes from 9% (corridor 0.2)
    # to 62% (corridor 0.95) and time from 2.12 to 2.31 h. So the best corridor
    # is itself a search result, not a constant.
    search_fractions: tuple[float, ...] = (0.5, 0.75, 0.95)
    # Objective: maximize wind-parallel distance, subject to time not exceeding
    # this factor over the fastest plan of the same layer. Without this cap,
    # "maximum parallel" degenerates into a meaningless route (it would wander
    # away from the destination just to stay parallel).
    alignment_first: bool = True
    alignment_slack_ratio: float = 1.15
    # **One explicit corridor, instead of a search.** When this value is given,
    # measures that one corridor and skips the automatic choice. Use case:
    # building "sibling variants" of one wind-riding route: several points on
    # the same trade-off (narrow corridor = fastest, least-parallel; wide
    # corridor = most parallel), so the scene and table can show them side by
    # side and the strategy difference becomes comparable. ``None`` means the
    # automatic policy search runs instead.
    corridor_override: float | None = None
    # **Band ceiling (MSL).** When given, a plan that would have to climb above
    # this ceiling to clear terrain is *rejected* (``terrain_climb_feasible``
    # becomes false) instead of being flown through or over. This is how the
    # "selected altitude band" promise is kept: within the band the aircraft may
    # climb to clear a mountain, but it never leaves the band. ``None`` keeps the
    # free behaviour — climb over any terrain, which is what the "all layers"
    # mode wants.
    max_altitude_msl_m: float | None = None

    def __post_init__(self) -> None:
        if self.descent_glideslope_ratio <= 0.0:
            raise ValueError("descent_glideslope_ratio must be positive.")
        if self.approach_km <= 0.0:
            raise ValueError("approach_km must be positive.")
        if self.max_altitude_msl_m is not None and self.max_altitude_msl_m <= 0.0:
            raise ValueError("max_altitude_msl_m must be positive when given.")
        if not 0.0 < self.wind_corridor_fraction < 1.0:
            raise ValueError("wind_corridor_fraction must be in (0, 1).")
        if self.wind_corridor_min_km <= 0.0:
            raise ValueError("wind_corridor_min_km must be positive.")
        if not self.search_fractions:
            raise ValueError("search_fractions cannot be empty.")
        for fraction in self.search_fractions:
            if not 0.0 < fraction < 1.0:
                raise ValueError("every search fraction must be in (0, 1).")
        if self.alignment_slack_ratio < 1.0:
            raise ValueError("alignment_slack_ratio must be at least 1.0.")
        if self.corridor_override is not None and not 0.0 < self.corridor_override < 1.0:
            raise ValueError("corridor_override must be in (0, 1) when given.")

    # The wind-riding policy has two modes, both implemented in this module:
    #
    # ``track_wind=True`` (default) — **follow the wind.** The command is solved
    #   so the *ground track* falls on the wind's own direction (wind triangle).
    #   The wind-riding phase is then parallel to the wind arrows and induced
    #   drag and crosswind terms vanish (the aircraft follows the wind instead
    #   of fighting it). Course correction happens only as needed to keep the
    #   landing corridor (``wind_corridor_fraction``) satisfied — a few short
    #   crab corrections near the destination.
    #
    # ``track_wind=False`` — **fixed heading.** The previous model: one air
    #   heading for the whole leg; the wind carries the aircraft and the ground
    #   track skews off. With it, the wind-riding route was a straight line,
    #   not the wind's own path.
    #
    # Reason for the change: measurement on the scene showed the old route had
    # 0.04 deg mean turning — a straight line — and its *track* angle sat about
    # 20 deg off the local wind (the drift angle), so nowhere was it parallel
    # to the wind.


@dataclass(frozen=True)
class WindRidingPlan:
    """Wind-riding plan result.

    Attributes
    ----------
        altitude_m : float
            Wind-riding altitude (metres). With a terrain model this is an
            *absolute* (MSL) level; without one the historic AGL meaning holds
            and terrain collision is not modelled.
    heading_deg : float
        Air heading of the route. In ``track_wind=False`` mode this is the fixed
        heading held through the wind-riding and descent phases; in
        ``track_wind=True`` mode the headings come from the wind triangle each
        step and this number is the distance-weighted mean (the dominant
    path : list[tuple[float, float]]
        Ground track from origin to destination. One element longer than
    node_altitudes : list[float]
        AGL altitude of each point (m): zero at the origin, ``altitude_m`` in
        the wind-riding phase, decreasing in the descent, zero at the
    climb_time_hours, ride_time_hours, descent_time_hours, final_leg_hours : float
        Flight time broken down by phase.
    ride_distance_km, descent_distance_km : float
        Ground distance in the wind-riding phase and in the descent phase.
    total_distance_km : float
        Total horizontal distance (wind riding + descent + final leg).
    arrival_miss_km : float
        Remaining distance to the destination *after* the descent (before the
    final_leg_km, final_bearing_deg : float
        Length and bearing of the final leg (zero if the descent lands on the
    descent_slope_ratio : float
        The *actual* descent slope "1 in N" of this plan (``descent distance /
        descent height``). Equal to ``descent_glideslope_ratio`` unless the
        route was shorter than the requested slope from the start; then it
    descent_power_fraction : float
        Cruise power fraction during the descent, from the thrust balance of
        the actual slope. For a slope gentler than max glide it is a number
    """

    altitude_m: float
    heading_deg: float
    path: list[tuple[float, float]]
    node_altitudes: list[float]
    # Minimum vertical clearance above terrain along the whole route (m).
    # ``None`` means altitudes are AGL and terrain collision is not modeled.
    min_terrain_clearance_m: float | None
    # Altitude that actually had to be climbed: origin ground to cruise level.
    climb_m: float
    climb_time_hours: float
    ride_time_hours: float
    descent_time_hours: float
    final_leg_hours: float
    ride_distance_km: float
    descent_distance_km: float
    descent_slope_ratio: float
    descent_power_fraction: float
    total_distance_km: float
    arrival_miss_km: float
    final_leg_km: float
    final_bearing_deg: float
    legs: list[LegSample] = field(default_factory=list)
    # Alignment report of this plan (from ``pathfinding.alignment``).
    # ``aligned_share``: share of distance within 3 deg of the wind direction;
    # ``parallel_mean_deg``: mean deviation *within that portion*; and
    # ``final_correction_km``: distance from the last wind-parallel segment to
    # the destination (i.e. "how many final kilometers were corrected"). These
    # three numbers are exactly what the report table shows and make the
    aligned_share: float = 0.0
    parallel_mean_deg: float = math.nan
    final_correction_km: float = 0.0
    corridor_fraction: float = 0.0
    # حالت عبوری چک‌پوینت قفل‌شدهٔ ارتفاعی (فاقد فرود در مقصد قطعه) و
    # ارتفاعِ رسیدن در مبدأ قطعه. با شناخت این دو، لایهٔ گزارش
    # (``wind_riding_route_result``) می‌داند کدام دو سر مسیر «روی زمین» است
    # و باید صفر گزارش شود و کدام دو سر «در هوا» و باید همان ارتفاع واقعی MSL
    # بماند — پیش‌تر هر دو سر همیشه صفر می‌شد و مسیر عملاً در چک‌پوینت
    # قفل‌شده به زمین می‌نشست.
    land_at_end: bool = True
    start_altitude_m: float | None = None

    @property
    def wind_aligned_fraction(self) -> float:
        """Share of horizontal distance flown with the heading parallel to the

        Computed from the reported segments themselves, so "wind riding" is not
        a claim: if the route fights the wind, this number stays near zero.
        """
        total = sum(leg.distance_km for leg in self.legs)
        if total <= 0.0:
            return 0.0
        aligned = sum(
            leg.distance_km
            for leg in self.legs
            if _angle_between(
                leg.track_bearing_deg,
                (leg.wind_direction_from_deg + 180.0) % 360.0,
            )
            <= _ALIGNED_TOLERANCE_DEG
        )
        return aligned / total

    @property
    def total_time_hours(self) -> float:
        """Total flight time (hours): climb + wind riding + descent + final leg."""
        return (
            self.climb_time_hours
            + self.ride_time_hours
            + self.descent_time_hours
            + self.final_leg_hours
        )


@dataclass(frozen=True)
class _Simulation:
    """Ground track for one candidate heading (raw integration output)."""

    heading_deg: float
    points: list[tuple[float, float]]
    altitudes: list[float]
    legs: list[LegSample]
    ride_km: float
    descent_km: float
    ride_hours: float
    descent_hours: float
    final_leg_km: float
    final_leg_hours: float
    final_bearing_deg: float
    miss_km: float
    min_terrain_clearance_m: float | None = None
    # Real descent slope (1 in N) and engine power fraction in that phase.
    # Both are *outputs*, not inputs: derived from where the descent starts and
    # the altitude to spend, so display and accounting share one source.
    descent_slope_ratio: float = 0.0
    descent_power_fraction: float = 1.0
    # Whether the terrain floor in the wind-riding phase was flyable within the
    # aircraft climb ceiling. ``False`` means clearing the mountain needs a
    # climb steeper than the aircraft can sustain — "flyable" on paper only.
    terrain_climb_feasible: bool = True
    # Distance-weighted distance whose track stayed parallel (within
    # ``_ALIGNED_TOLERANCE_DEG``) to the wind's own direction. Basis of the
    # ``wind_aligned_fraction`` metric: "what share of the route truly rode
    aligned_km: float = 0.0

    def flight_hours(self) -> float:
        """Flight time without the initial climb (cruise + descent + final leg).

        When comparing *policies* this is the criterion: the origin climb is
        identical for every policy, so including it only adds noise.
        """
        return self.ride_hours + self.descent_hours + self.final_leg_hours


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ground-track azimuth between two points (degrees, from north)."""
    return initial_bearing_deg(lat1, lon1, lat2, lon2)


def _approx_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Local flat-projection distance (km) — for *integration loop control* only.

    Called hundreds of thousands of times in the search loop, where spherical
    ``haversine_km`` is too expensive. Every *reported* number (segment
    distances, total difference) is recomputed with great-circle
    distance in ``wind_riding_route_result``, so this approximation never
    leaks into the report.
    """
    d_lat = (lat2 - lat1) * _KM_PER_DEG_LAT
    d_lon = (lon2 - lon1) * _KM_PER_DEG_LAT * math.cos(math.radians(lat1))
    return math.hypot(d_lat, d_lon)


def _wind_vector(speed_mps: float, direction_from_deg: float) -> tuple[float, float]:
    """Wind vector in (east, north) axes — the direction the wind blows *toward*."""
    to_rad = math.radians((direction_from_deg + 180.0) % 360.0)
    return speed_mps * math.sin(to_rad), speed_mps * math.cos(to_rad)


# "Parallel to wind" threshold. 15 deg means the angle between the ground track
# and the wind direction stays under 15 deg; it separates "riding the wind"
_ALIGNED_TOLERANCE_DEG = 15.0


def _angle_between(bearing_a_deg: float, bearing_b_deg: float) -> float:
    """Smallest angle between two azimuths (0 to 180 degrees)."""
    difference = (bearing_a_deg - bearing_b_deg) % 360.0
    return difference if difference <= 180.0 else 360.0 - difference


def _solve_wind_triangle(
    track_bearing_deg: float,
    wind_east: float,
    wind_north: float,
    airspeed_mps: float,
) -> tuple[float, float, float] | None:
    """Solves the wind triangle for a *requested ground track*.

    We want the **ground track** to be exactly ``track_bearing_deg``, not the
    heading. The ground velocity is ``G·û`` (``û`` its unit vector) and the
    wind ``W`` is known, so the air velocity ``A = G·û − W`` must have length

        G² − 2G(W·û) + (|W|² − V²) = 0
        ⇒ G = (W·û) + √(V² − |W⊥|²)

    The positive root wins (higher ground speed). A solution exists only if
    ``V >= |W_perp|`` — the crosswind cannot exceed airspeed. This is what
    turns "fighting the wind" into a number in the model.

    Returns
    ----------
    (air_east, air_north, ground_speed) | None
        Air-velocity vector and ground speed, or ``None`` if this ground track
        cannot be held with this wind and airspeed.
    """
    to_rad = math.radians(track_bearing_deg)
    ux_east, ux_north = math.sin(to_rad), math.cos(to_rad)
    along = wind_east * ux_east + wind_north * ux_north
    wind_speed = math.hypot(wind_east, wind_north)
    cross_sq = max(wind_speed * wind_speed - along * along, 0.0)
    if cross_sq >= airspeed_mps * airspeed_mps:
        return None
    ground_speed = along + math.sqrt(airspeed_mps * airspeed_mps - cross_sq)
    if ground_speed <= 1e-6:
        return None
    air_east = ground_speed * ux_east - wind_east
    air_north = ground_speed * ux_north - wind_north
    return air_east, air_north, ground_speed


def _cross_track_km(
    origin: tuple[float, float],
    destination: tuple[float, float],
    lat: float,
    lon: float,
) -> float:
    """Signed lateral distance from the straight origin-destination line (km, positive = left of track)."""
    lat0 = math.radians(origin[0])
    scale = _KM_PER_DEG_LAT * math.cos(lat0)
    dir_east = (destination[1] - origin[1]) * scale
    dir_north = (destination[0] - origin[0]) * _KM_PER_DEG_LAT
    norm = math.hypot(dir_east, dir_north)
    if norm <= 1e-12:
        return 0.0
    dir_east, dir_north = dir_east / norm, dir_north / norm
    off_east = (lon - origin[1]) * math.cos(math.radians(lat)) * _KM_PER_DEG_LAT
    off_north = (lat - origin[0]) * _KM_PER_DEG_LAT
    # Left-pointing normal of the track vector.
    return off_east * (-dir_north) + off_north * dir_east


def _heading_scan(step_deg: float) -> list[float]:
    """Coarse sweep of the heading over 360 degrees."""
    if step_deg <= 0.0:
        raise ValueError("heading_coarse_step_deg must be positive.")
    count = max(int(round(360.0 / step_deg)), 1)
    return [index * 360.0 / count for index in range(count)]


def _refine_scan(center_deg: float, span_deg: float, step_deg: float) -> list[float]:
    """Headings around ``center_deg`` within +/- ``span_deg`` at ``step_deg``.

    The center point is included so the previous stage best heading stays in
    this stage comparison too.
    """
    if step_deg <= 0.0:
        raise ValueError("heading refine steps must be positive.")
    count = max(int(round(2.0 * span_deg / step_deg)), 1)
    return [((center_deg - span_deg) + index * step_deg) % 360.0 for index in range(count + 1)]


def _simulate_heading(
    origin: tuple[float, float],
    destination: tuple[float, float],
    sampler: WindSampler,
    descent_sampler: WindSampler,
    heading_deg: float,
    *,
    altitude_m: float,
    airspeed_mps: float,
    glide_ratio: float,
    glide_power_fraction: float,
    config: WindRidingConfig,
    descent_ratio: float = 40.0,
    approach_km: float = 3.0,
    ground_end_m: float = 0.0,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    clearance_floor_m: float = 0.0,
    track_wind: bool = False,
    sampler_for_altitude: Callable[[float], WindSampler] | None = None,
    max_climb_gradient: float | None = None,
    land_at_end: bool = True,
    start_altitude_m: float | None = None,
) -> _Simulation:
    """Integrates one air heading from the origin through landing and closure.

    Phases and **the role of gravity**
    -------------------
    1) Climb at the origin to the layer altitude (engine).
    2) Wind riding at constant altitude: one heading, the wind carries the
    3) Descent on a **gentle fixed slope**: when remaining distance equals
    ``h · descent_ratio``, the descent starts on that fixed slope and altitude
    decreases linearly with remaining distance down to zero at the destination.

    The third phase used to be a *max glide*: it started at ``h · L/D`` and
    regained altitude in the last 6 km. That version was fuel-perfect but
    looked like a dive in the scene and showed the user nothing "gradual".
    The descent slope is now a *policy*: gentler than max glide with partial
    engine power, that power computed from the thrust balance — so "more
    gradual" does not mean "free", only differently distributed.

    Pass-through mode (``land_at_end=False``)
    ----------------------------------------
    An intermediate waypoint the user lifted in the 3D scene (the locked
    altitude of a checkpoint) must be crossed **in the air**, not landed on.
    In that mode phase 3 never starts: the flight cruises to the destination
    of the segment, the final point keeps the cruise altitude (or the
    terrain-guided level if the ground floor lifted it), and the wind of the
    final leg is read at the cruise layer. This is how a multi-segment route
    can chain "origin → air-point → destination" without touching down at
    every checkpoint — which was exactly the bug: each segment glided to its
    segment-end ground level, so the route visibly dived to the ground at the
    checkpoint the user had dragged up.
    """
    # Glide basis (km/1000): the altitude is spent from the cruise level down
    # to the *destination ground elevation*, not sea level — anchoring at sea
    # level would overstate the height to lose and start the descent early.
    # در حالت عبوری فرودی نیست؛ ارتفاع «باید-بقدرشود» صفر می‌ماند تا هیچ فاز
    # فرودی — حتی دربست منطقی `remaining <= descent_span_km` — فعال نشود.
    height_to_lose_m = 0.0 if not land_at_end else max(altitude_m - ground_end_m, 0.0)
    # Horizontal distance of the descent on the policy slope (``h · ratio``). The
    # descent starts where this distance equals the remaining distance.
    descent_span_km = height_to_lose_m * descent_ratio / 1000.0
    heading_rad = math.radians(heading_deg)
    air_east = airspeed_mps * math.sin(heading_rad)
    air_north = airspeed_mps * math.cos(heading_rad)
    # The heading *actually* used in the current step. In follow-the-wind mode
    # each step has its own heading (wind triangle) and this number feeds the
    # fuel-record "engine course corrections"; in fixed-heading mode it is the
    current_heading = heading_deg
    # Requested track angle relative to the wind: 0 = fully wind-parallel,
    # 90 = perpendicular. Accumulated distance-weighted so "what share of the
    # route was wind-parallel" is measured, not claimed.
    aligned_km = 0.0

    lat, lon = origin
    points: list[tuple[float, float]] = [(lat, lon)]
    # Display altitude profile: with a terrain model altitudes are **absolute**
    # and origin/destination sit on their own ground; without one, the same
    # نخستین نقطهٔ مسیر: وقتی قطعه *در هوا* شروع می‌شود (چک‌پوینتِ قفل‌شدهٔ
    # قبل مسیر را همان‌جا در ارتفاع تحویل داده است) نقطهٔ شروع هم همان ارتفاع است،
    # نه زمینِ زیرش — وگرنه مسیر رندرشده در نقشهراه شیرجهٔ عمودی می‌زد.
    altitudes: list[float] = [
        start_altitude_m if start_altitude_m is not None else _terrain_height(origin, ground_elevation_at)
    ]
    legs: list[LegSample] = []
    ride_km = 0.0
    descent_km = 0.0
    ride_hours = 0.0
    descent_hours = 0.0
    descending = False
    # Remaining distance at the moment the descent started (km). Stays zero
    # until descent begins; afterwards it is the descent-slope basis.
    descent_start_km = 0.0
    # Engine power fraction in the descent phase, from the thrust balance of
    # *that segment*. Computed per segment, not once for the whole descent:
    # the descent profile can be fragmented by the terrain floor and each
    descent_power = glide_power_fraction
    # Absolute aircraft altitude (m). Equals the cruise level in the wind-riding
    # phase and rides its glide in the descent. Initialized before the loop
    # because picking the wind "at this altitude" in the first step needs it.
    agl_now = altitude_m
    # The "is the whole route flyable?" answer. Updated in the wind-riding phase
    # and reported in ``_Simulation`` so the planner rejects an impossible level.
    terrain_climb_ok = True
    time_s = 0.0
    window_s = 0.0
    last_point = (lat, lon)
    # Wind of the current window is read from the actual current point, not
    # zero. Without this initialization the *first* window reported a zero
    # wind direction and the "what share of the route was wind-parallel" metric
    window_speed, window_direction = sampler(lat, lon)
    min_clearance: float | None = None if ground_elevation_at is None else math.inf

    def close_window(new_lat: float, new_lon: float, agl_now: float) -> None:
        """Converts the current sampling window into one segment/point."""
        nonlocal window_s, last_point, window_speed, window_direction
        nonlocal aligned_km
        segment_km = _approx_km(last_point[0], last_point[1], new_lat, new_lon)
        if segment_km <= 1e-9:
            window_s = 0.0
            return
        track_now = _bearing(last_point[0], last_point[1], new_lat, new_lon)
        if _angle_between(track_now, (window_direction + 180.0) % 360.0) <= _ALIGNED_TOLERANCE_DEG:
            aligned_km += segment_km
        legs.append(
            LegSample(
                track_bearing_deg=track_now,
                wind_speed_mps=window_speed,
                wind_direction_from_deg=window_direction,
                distance_km=segment_km,
                time_hours=window_s / 3600.0,
                # The planner's own heading in this segment. In fixed-heading mode
                # it is the number every wind-riding and descent segment flies;
                # in follow-the-wind mode it comes from that step's wind triangle,
                # which is what makes heading changes and the fuel cost of
                air_heading_deg=current_heading,
                # In the descent phase part of the thrust comes from gravity, so
                # the fuel of this distance is less than cruise; the fuel model
                # reads that extra thrust from ``power_fraction`` below.
                power_fraction=(
                    min(
                        max(
                            1.0 - glide_ratio * _sink_sine(altitudes[-1], agl_now, segment_km),
                            glide_power_fraction,
                        ),
                        1.0,
                    )
                    if descending
                    else 1.0
                ),
            )
        )
        points.append((new_lat, new_lon))
        altitudes.append(agl_now)
        last_point = (new_lat, new_lon)
        window_s = 0.0

    max_seconds = config.max_hours * 3600.0
    closest_remaining = math.inf
    while time_s < max_seconds:
        remaining = _approx_km(lat, lon, destination[0], destination[1])
        if remaining <= config.arrival_radius_km:
            break
        if remaining < closest_remaining:
            closest_remaining = remaining
        elif remaining > closest_remaining + config.abandon_margin_km:
            # This heading circles away from the destination; running it to
            # ``max_hours`` only slows the whole search.
            break

        # **Wind at the aircraft's *actual* altitude.** When a vertical profile
        # is given, wind is read from the layer the aircraft is currently in —
        # not the cruise layer. This is what makes "climb until you fall into a
        # wind that carries you" real: climbing over the mountain range brings
        # the wind at that altitude (rotated further right) into the problem.
        if sampler_for_altitude is None:
            sampler_now = descent_sampler if descending else sampler
        else:
            sampler_now = sampler_for_altitude(agl_now)
        speed, direction = sampler_now(lat, lon)
        wind_east, wind_north = _wind_vector(speed, direction)
        if track_wind:
            # **Wind following, with a converging corridor.**
            #
            # The *default* track is the wind's own direction (parallel to the
            # arrows). But this corridor's wind does not blow toward the
            # destination; further along, the wind veers right, so "flying
            # parallel to the wind" alone would carry the aircraft past the
            # destination. Let ``delta`` be the track angle relative to
            # "straight to the destination". With remaining distance ``R``
            # and current lateral offset ``x``, the final offset becomes
            # ``x − R·sin(delta)`` (the minus sign comes from azimuth
            # increasing turning *right* in the east–north frame). To keep
            # |that value| inside the corridor ``±b``:
            #
            #         delta ∈ [asin((x − b)/R), asin((x + b)/R)]
            # The chosen ``delta`` is the wind's own direction when it falls
            # inside this interval, otherwise the nearest interval end. I.e.
            # "as parallel to the wind as possible, then the least correction
            # possible".
            # The corridor ``b`` shrinks relative to remaining distance
            # (``wind_corridor_fraction``), so in the last few kilometers the
            # interval closes to zero and the aircraft lands on the destination.
            # Those few degrees of crab also activate induced drag and headwind
            # terms in the fuel model. With constant wind and an 8.2 deg offset,
            # this control flies *fully* parallel to the wind for 112 km and
            # corrects towards the destination only in the last kilometers.
            direct_bearing = _bearing(lat, lon, destination[0], destination[1])
            cross_track = _cross_track_km(origin, destination, lat, lon)
            wind_magnitude = math.hypot(wind_east, wind_north)
            if wind_magnitude <= 1e-9:
                # **Calm air != "unknown parallel wind".** With zero wind there
                # is no wind direction and ``atan2(0, 0)`` returns an arbitrary
                # number (north). In that case the only defensible track is the
                # one that zeroes the lateral offset — i.e. straight to the
                # destination.
                deviation = math.degrees(
                    math.asin(min(max(cross_track / remaining, -1.0), 1.0))
                )
            else:
                wind_track = math.degrees(math.atan2(wind_east, wind_north)) % 360.0
                deviation = ((wind_track - direct_bearing + 180.0) % 360.0) - 180.0
            budget = max(
                config.wind_corridor_min_km,
                config.wind_corridor_fraction * remaining,
            )
            safe_remaining = max(remaining, 1e-9)
            lowest = math.degrees(
                math.asin(min(max((cross_track - budget) / safe_remaining, -1.0), 1.0))
            )
            highest = math.degrees(
                math.asin(min(max((cross_track + budget) / safe_remaining, -1.0), 1.0))
            )
            desired_bearing = direct_bearing + min(max(deviation, lowest), highest)
            desired_track = desired_bearing % 360.0
            solution = _solve_wind_triangle(
                desired_track, wind_east, wind_north, airspeed_mps
            )
            if solution is None:
                # Crosswind exceeds airspeed: this ground track cannot be held.
                # Fall back to "straight at the destination"; if that fails too,
                # no route exists for this wind and airspeed to this destination.
                solution = _solve_wind_triangle(
                    direct_bearing, wind_east, wind_north, airspeed_mps
                )
                if solution is None:
                    break
                desired_track = direct_bearing
            air_east, air_north, ground_speed = solution
            v_east = ground_speed * math.sin(math.radians(desired_track))
            v_north = ground_speed * math.cos(math.radians(desired_track))
            current_heading = math.degrees(math.atan2(air_east, air_north)) % 360.0
        else:
            v_east = air_east + wind_east
            v_north = air_north + wind_north
            ground_speed = math.hypot(v_east, v_north)
            current_heading = heading_deg
        if ground_speed <= 1e-6:
            break

        dt = config.step_s
        if land_at_end and not descending and remaining <= descent_span_km:
            # The wind-riding/descent boundary closes *here*. Otherwise the
            # current sampling window (up to 2 minutes of cruise flight) would
            # be attributed to the descent phase, and the distance and engine
            # power of that boundary segment would be misaccounted.
            before = last_point
            close_window(lat, lon, altitude_m)
            if last_point != before:
                ride_km += _approx_km(before[0], before[1], lat, lon)
            # Descent start is a *timing event*, not a heading change: one short
            # step lands exactly on the descent-start point and the heading is
            # kept unchanged across the boundary.
            descending = True
            # The *actual* slope is built from this point: altitude is a linear
            # function of remaining distance, so the aircraft lands exactly on
            # the destination and the descent-start step error does not drift
            # into the profile.
            descent_start_km = max(remaining, 1e-6)
            # Engine power fraction in descent comes from the thrust balance, not
            # an arbitrary number: ``T = D − m·g·sinγ`` and ``D = m·g/(L/D)``
            # give ``T/D = 1 − (L/D)·sinγ``. A 1-in-40 slope with L/D = 12 means
            # 0.7 cruise power — not idle. Idle is the *floor*: whenever the
            # required slope steepens beyond max glide (short route or late
            # descent start), the fraction bottoms out at idle.
            descent_power = min(
                max(
                    1.0
                    - glide_ratio
                    * _sink_sine(altitude_m, altitude_m - height_to_lose_m, descent_start_km),
                    glide_power_fraction,
                ),
                1.0,
            )

        lat += (v_north * dt) / (_KM_PER_DEG_LAT * 1000.0)
        lon += (v_east * dt) / (_KM_PER_DEG_LAT * 1000.0 * math.cos(math.radians(lat)))
        time_s += dt
        window_s += dt

        if descending:
            descent_hours += dt / 3600.0
            # Glide slope: altitude decreases proportionally to remaining
            # distance, so the aircraft reaches the destination ground elevation
            # exactly when it arrives — the slope is the *policy* slope
            # (``height_to_lose`` over ``descent_start``), flown with the
            # engine's partial ``descent_power``.
            left_km = _approx_km(lat, lon, destination[0], destination[1])
            agl_now = ground_end_m + max(
                height_to_lose_m * min(left_km / descent_start_km, 1.0), 0.0
            )
            # **Terrain floor.** A gentle descent starting 100 km out arrives at
            # the mountain at a lower altitude. Wind riding must not pass through
            # the mountain, so the policy profile is held up over the *summit*.
            # In the final approach the floor ramps down to the destination
            # ground elevation (``approach_km``), otherwise the aircraft could
            # never legally descend to it.
            if ground_elevation_at is not None and clearance_floor_m > 0.0:
                fade = min(left_km / approach_km, 1.0)
                floor_msl = (
                    float(ground_elevation_at(lat, lon)) + clearance_floor_m * fade
                )
                # سقف باند: اگر کف زمین از سقف باند بالاتر باشد، این سطح
                # نمی‌تواند هم‌زمان باند را نگه دارد و از کوه رد شود → غیرقابل‌پرواز.
                if (
                    config.max_altitude_msl_m is not None
                    and floor_msl > config.max_altitude_msl_m + 1e-9
                ):
                    terrain_climb_ok = False
                agl_now = max(agl_now, floor_msl)
        else:
            ride_hours += dt / 3600.0
            agl_now = altitude_m
            # **Terrain floor in the wind-riding phase.** This corridor crosses a
            # mountain range up to 3175 m; the 1500 or 2200 m cruise level is below
            # the summit, so level cruise would mean flying through the mountain.
            # The aircraft necessarily *climbs* to clear the terrain, and that
            # same climb changes its altitude, so from here on the wind is read at
            # the new altitude (see ``sampler_for_altitude``). This is the only
            # place where the two models lean on each other, and both use the
            # same clearance floor and climb ceiling.
            if ground_elevation_at is not None and clearance_floor_m > 0.0:
                floor_msl = float(ground_elevation_at(lat, lon)) + clearance_floor_m
                # سقف باند (حالت «ارتفاع انتخابی»): صعود برای رد شدن از کوه
                # فقط تا سقف باند مجاز است. اگر کف زمین از آن بالاتر باشد، این
                # سطح نمی‌تواند باند را نگه دارد؛ برنامه در فیلتر «قابل‌پرواز»
                # رد می‌شود و مسیریاب گراف — که با حذف گره‌های کم‌فاصله، مسیر
                # را *دور* کوه می‌برد — جای آن را می‌گیرد.
                if (
                    config.max_altitude_msl_m is not None
                    and floor_msl > config.max_altitude_msl_m + 1e-9
                ):
                    terrain_climb_ok = False
                # **Can this climb be sustained?** The terrain floor can sit above
                # the cruise level (a mountain edge). Imposing it as-is would make
                # the aircraft jump instantly: an infinite-gradient climb that
                # only works on paper. So the *climb needed to reach the floor* is
                # checked against the aircraft climb-gradient ceiling; beyond it,
                # this level is not flyable: exactly what the graph does by
                # dropping nodes below the threshold. For this corridor the low
                # cruise levels are rejected (the edge climbs to 3175 m) and
                # only a level above that ceiling survives.
                if floor_msl > agl_now:
                    rise = floor_msl - agl_now
                    allowed = (
                        None
                        if max_climb_gradient is None
                        else max_climb_gradient * (ground_speed * dt / 1000.0)
                    )
                    if allowed is not None and rise > allowed + 1e-9:
                        terrain_climb_ok = False
                    agl_now = floor_msl

        # Terrain clearance in **this step**. Measured here, not at the sampling
        # points: sampling is every 2 minutes (about 2.5 km) and a narrow mountain
        # edge can fall exactly between two samples.
        # The clearance threshold applies only **outside the final approach**.
        # In the final approach the aircraft *must* reach the ground, so if the
        # touchdown point entered the statistics, minimum clearance would always
        # be zero and the safety metric meaningless. "Final approach" is defined
        # by **distance**, not altitude: an altitude-based definition was wrong:
        # if the terrain under the route sits several hundred meters above the
        # destination ground, the aircraft in the final approach is still above
        # the altitude threshold and those few reduced meters would count as a
        # "safety violation" although nothing else could be done. Distance is
        # the definition that matches what the pilot can still change.
        if (
            min_clearance is not None
            and ground_elevation_at is not None
            and _approx_km(lat, lon, destination[0], destination[1]) > approach_km
        ):
            clearance_now = agl_now - float(ground_elevation_at(lat, lon))
            if clearance_now < min_clearance:
                min_clearance = clearance_now

        # Sampling: every ``path_sample_s`` (and in the descent phase every step,
        # so the altitude profile stays exact).
        if window_s >= config.path_sample_s or descending:
            before = last_point
            close_window(lat, lon, agl_now)
            if last_point != before:
                segment_km = _approx_km(before[0], before[1], lat, lon)
                if descending:
                    descent_km += segment_km
                else:
                    ride_km += segment_km
                window_speed, window_direction = speed, direction


    # **بُرش در نزدیک‌ترین نقطه — جلوگیری از پاگرد تیز مقصد.** حلقهٔ بالا لحظهٔ
    # «رسیدن» را *پیش از* هر گام می‌شکند، پس موقعیت نهایی می‌تواند از مقصد
    # بگذرد (هر گام ≈ ۰٫۶ کیلومتر)؛ قاعدهٔ «پرت شدن» (``abandon_margin``) و
    # سقف زمان هم می‌توانند مسیر را بعد از نزدیک‌ترین نقطه دور کرده باشند. درج
    # مقصد پس از چنین نقطه‌ای یک «رد شد و برگشت» می‌سازد — همان پاگرد تیزی که
    # در صحنه دیده می‌شد. پس هندسه تا نزدیک‌ترین نقطهٔ مقصد بریده می‌شود و
    # قطعهٔ پایانی از همان‌جا می‌رود. قطعه‌های حساب‌شده (``legs``) هم هم‌پا
    # بریده می‌شوند تا جفت «قطعه ↔ بازهٔ مسیر» در ``wind_riding_route_result``
    # حفظ شود. قید ``tail`` جلوی بریدن مسیرهای بلند سالم را می‌گیرد: تنها
    # جمع‌شدگی کوچک انتهایی (همان پاگرد) بسته می‌شود، نه یک مسیر پیچیده.
    if points:
        closest_index = min(
            range(len(points)),
            key=lambda index: haversine_km(
                points[index][0], points[index][1], destination[0], destination[1]
            ),
        )
        closest_km = haversine_km(
            points[closest_index][0],
            points[closest_index][1],
            destination[0],
            destination[1],
        )
        current_km = haversine_km(lat, lon, destination[0], destination[1])
        tail = len(points) - 1 - closest_index
        if current_km > closest_km + 1e-9 and tail <= max(2, len(points) // 4):
            del points[closest_index + 1:]
            del altitudes[closest_index + 1:]
            del legs[closest_index:]
            lat, lon = points[closest_index]

    # Final leg: straight remainder to the destination (if outside the arrival
    # radius).
    miss_km = haversine_km(lat, lon, destination[0], destination[1])
    final_bearing = _bearing(lat, lon, destination[0], destination[1])

    final_leg_km = 0.0
    final_leg_hours = 0.0
    if miss_km > config.arrival_radius_km:
        # بادِ پارکت پایانی: در حالت فرودی زمین دارد (modal لایهٔ پایین)، در
        # حالت عبوری هنوز در سطح کروزی است — باد باید از همان لایه خوانده شود.
        wind_sampler = descent_sampler if land_at_end else sampler
        speed, direction = wind_sampler(lat, lon)
        wind_east, wind_north = _wind_vector(speed, direction)
        trail = math.radians(final_bearing)
        v_east = airspeed_mps * math.sin(trail) + wind_east
        v_north = airspeed_mps * math.cos(trail) + wind_north
        ground_speed = max(math.hypot(v_east, v_north), 1e-6)
        final_leg_km = miss_km
        final_leg_hours = miss_km / (ground_speed * 3.6)
        legs.append(
            LegSample(
                track_bearing_deg=final_bearing,
                wind_speed_mps=speed,
                wind_direction_from_deg=direction,
                distance_km=miss_km,
                time_hours=final_leg_hours,
            )
        )
    # If the aircraft is already inside the arrival radius, the last point is
    # replaced *with* the destination; appending it would create a short
    # backward-pointing segment at the very end of the route.
    #
    # Why this matters: the loop breaks when distance to destination drops below
    # the arrival radius, and that moment is checked *before* the next step, so
    # the final point can overshoot the destination by a few hundred meters (a
    # 20-second step is about 0.6 km). Appending the destination after that
    # point would fold the route end back on itself, and that small kink shows
    # up in the plotted profile as a "sharp dip" right at the destination,
    # something no aircraft does. Replacing unifies geometry with physics: the
    # reported route ends exactly where the simulation judged "arrived".
    # ارتفاع نقطهٔ انتهایی: فرودی → ارتفاع زمین مقصد؛ عبوری → ارتفاع کروز
    # (آخرین نمونه ممکن است از کف زمین بالا رانده شده باشد — همان را نگه می‌داریم).
    if not land_at_end and altitudes:
        end_altitude_m = altitudes[-1]
    else:
        end_altitude_m = ground_end_m
    if len(points) > 1 and miss_km <= config.arrival_radius_km:
        points[-1] = destination
        altitudes[-1] = end_altitude_m
    else:
        points.append(destination)
        altitudes.append(end_altitude_m)

    return _Simulation(
        heading_deg=heading_deg,
        points=points,
        altitudes=altitudes,
        legs=legs,
        aligned_km=aligned_km,
        terrain_climb_feasible=terrain_climb_ok,
        min_terrain_clearance_m=min_clearance,
        ride_km=ride_km,
        descent_km=descent_km,
        ride_hours=ride_hours,
        descent_hours=descent_hours,
        final_leg_km=final_leg_km,
        final_leg_hours=final_leg_hours,
        final_bearing_deg=final_bearing,
        miss_km=miss_km,
        # The *actual* descent slope (1 in N) comes from the distance flown, not
        # from the policy: if the terrain floor held part of the descent up, the
        # mean slope steepens beyond 1-in-``descent_ratio`` and that is the number
        # to report. Descent power comes from the thrust balance of *that same*
        # actual slope, so the two table columns agree, rather than one column
        # quoting the policy and the other quoting the flight.
        descent_slope_ratio=(
            descent_km * 1000.0 / height_to_lose_m if height_to_lose_m > 0.0 else 0.0
        ),
        descent_power_fraction=(
            min(
                max(
                    1.0 - glide_ratio * _sink_sine(height_to_lose_m, 0.0, descent_km),
                    glide_power_fraction,
                ),
                1.0,
            )
            if descent_km > 0.0 and height_to_lose_m > 0.0
            else descent_power
        ),
    )


def _sink_sine(from_alt_m: float, to_alt_m: float, run_km: float) -> float:
    """``sin`` زاویهٔ فرود یک قطعه از کم‌کردن ارتفاع و مسافت افقی همان قطعه.

    زاویهٔ فرود یک قطعهٔ فرود است، نه یک خاصیت ثابت مسیر: با کف فاصله از زمین،
    یک فرود می‌تواند تکه‌های ملایم و تند داشته باشد و توان موتور هر تکه باید از
    شیب *همان تکه* بیاید — وگرنه سوخت کل مسیر از شیب میانگین حساب می‌شد.
    """
    run_m = max(run_km * 1000.0, 1e-9)
    drop_m = max(from_alt_m - to_alt_m, 0.0)
    return drop_m / math.hypot(drop_m, run_m)


def _terrain_height(
    point: tuple[float, float],
    elevation_at: Callable[[float, float], float] | None,
) -> float:
    """ارتفاع زمین زیر یک نقطه (متر) — صفر اگر مدل زمین داده نشده باشد."""
    if elevation_at is None:
        return 0.0
    return float(elevation_at(point[0], point[1]))


def plan_wind_riding_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    layers: Sequence[tuple[float, WindSampler]],
    *,
    aircraft: CostModelConfig | None = None,
    vertical: VerticalCostConfig | None = None,
    effort: MotorEffortConfig | None = None,
    config: WindRidingConfig | None = None,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    min_clearance_m: float = 0.0,
    cruise_altitudes: Sequence[float] | None = None,
    land_at_end: bool = True,
    start_altitude_m: float | None = None,
) -> WindRidingPlan | None:
    """بهترین مسیر بادسواری را برای یک مبدأ/مقصد پیدا می‌کند.

    برای هر لایه، بهترین سمت فرمان با پویش درشت + ریزکردن جست‌وجو می‌شود؛ سپس
    برنامه‌ای انتخاب می‌شود که در میان برنامه‌های قابل‌قبول (خطای رسیدن کمتر از
    ``config.max_arrival_miss_km``) کمترین زمان کل را داشته باشد.

    پارامترها
    ----------
    origin, destination : tuple[float, float]
        مختصات (عرض، طول).
    layers : Sequence[tuple[float, WindSampler]]
        جفت‌های (ارتفاع AGL، نمونه‌بردار باد همان لایه). میدان باد از سمت صحنه
        (``viz.wind_field``) ساخته و این‌جا تزریق می‌شود تا این ماژول به لایه
        نمایش وابسته نباشد. این فهرست **پروفیل عمودی** هواپیما است: باد در هر
        لحظه از لایه‌ای خوانده می‌شود که هواپیما واقعاً در آن ارتفاع است.
    cruise_altitudes : Sequence[float], اختیاری
        ارتفاع‌های کروزی که باید جست‌وجو شوند. پیش‌فرض، همان ارتفاع‌های
        ``layers``. جدا کردن این دو یعنی می‌توان کارنامهٔ یک سطح را خواست در
        حالی که هواپیما اجازه دارد برای رد شدن از کوه به سطح باالتر برود.
    land_at_end : bool, پیش‌فرض True
        فرود در انتهای قطعه (مقصد قطعه، یعنی مبدأ/مقصد/چک‌پوینت). وقتی
        ``False``، مسیر مقصد قطعه را **در ارتفاع کروز** رد می‌کند و فرود
        نمی‌گیرد — حالت عبوری برای چک‌پوینت‌های قفل‌شدهٔ ارتفاعی: نقطهٔ
        وسطِ مسیر که کاربر در صحنه به بالا کشیده، باید در هوا دیده شود نه
        روی زمین. (پیش از این، هر قطعه در انتهایش فرود می‌گرفت و مسیر عملاً
        «روی زمین» از آن چک‌پوینت می‌گذشت.)
    start_altitude_m : float, اختیاری
        ارتفاعِ رسیدنِ هواپیما در مبدأ این قطعه — ارتفاع قفل‌شدهٔ چک‌پوینتِ
        قبلی. صرفاً هزینهٔ صعود از آن سطح حساب می‌شود (نه از زمین) و نقطهٔ
        نخستِ پروفایل ارتفاعی مسیر همان مقدار می‌شود تا پیوستگی عمودی دو
        قطعهٔ پشت هم حفظ شود.
    aircraft : CostModelConfig, اختیاری
        مشخصات هواپیما (فقط ``airspeed_mps``).
    vertical : VerticalCostConfig, اختیاری
        نرخ صعود؛ زمان صعود = ارتفاع/نرخ صعود — همان فرض یال‌های عمودی گراف.
        (نرخ فرود این‌جا دیگر تعیین‌کننده نیست: شيب فرود از بُرد گلاید می‌آید.)
    effort : MotorEffortConfig, اختیاری
        فرض‌های مدل سوخت. **تنها منبع حقیقت برای دو عدد فیزیکی** است که این
        برنامه‌ریز لازم دارد: نسبت برآر به پسار (``lift_to_drag``) که با آن سهم
        گرانش در رانش فرود حساب می‌شود، و کسر توان دور آرام
        (``descent_idle_power_fraction``) که *کف* توان در فاز فرود است. شکل خودِ
        فرود (شیبش) از ``WindRidingConfig.descent_glideslope_ratio`` می‌آید.
    config : WindRidingConfig, اختیاری
        پارامترهای عددی جست‌وجو.
    ground_elevation_at : Callable, اختیاری
        ``(lat, lon) -> elevation_m``. اگر داده شود، ``layers`` **سطح پرواز
        مطلق** تفسیر می‌شود: صعود از ارتفاع زمین مبدأ حساب می‌شود، بُرد گلاید
        تا ارتفاع زمین مقصد است، و مسیری که از داخل کوه بگذرد رد می‌شود.
        اگر ``None`` باشد، همان معنای «بالای زمین» قبلی حفظ می‌شود.
    min_clearance_m : float
        کمترین فاصلهٔ مجاز عمودی با زمین (متر) — همان آستانهٔ گراف.

    برمی‌گرداند
    ----------
    WindRidingPlan | None
        بهترین برنامه، یا ``None`` اگر هیچ لایه/سمتی به مقصد (در حد خطای مجاز)
        نرسد.
    """
    settings = config or WindRidingConfig()
    plane = aircraft or CostModelConfig()
    verticals = vertical or VerticalCostConfig()
    effort_settings = effort or MotorEffortConfig()
    if not layers:
        raise ValueError("layers cannot be empty.")

    # پروفیل عمودی به ترتیب ارتفاع. نمونه‌بردارِ هر ارتفاع، لایه‌ای است که
    # آن ارتفاع یا پایین‌ترش را می‌پوشاند (و اگر زیر همه بود، پایین‌ترین لایه).
    profile = sorted(layers, key=lambda item: item[0])
    descent_sampler = profile[0][1]
    best_plan: WindRidingPlan | None = None
    descent_ratio = settings.descent_glideslope_ratio

    def sampler_at(altitude_m: float) -> WindSampler:
        """نمونه‌بردار باد در یک ارتفاع دلخواه (پله‌ای روی لایه‌های معلوم)."""
        chosen = profile[0][1]
        for level_altitude, level_sampler in profile:
            if level_altitude <= altitude_m + 1e-9:
                chosen = level_sampler
        return chosen

    # ارتفاع زمین در مبدأ/مقصد و در طول مسیر. بدون نمونه‌بردار زمین، همهٔ
    # ارتفاع‌ها نسبت به زمین‌اند (همان رفتار قبلی) و کاری با برخورد با زمین
    # نداریم؛ با آن، سطح پرواز مطلق می‌شود و برخورد با قله یک پرسش واقعی است.
    ground_start = _terrain_height(origin, ground_elevation_at)
    ground_end = _terrain_height(destination, ground_elevation_at)
    targets = (
        list(cruise_altitudes)
        if cruise_altitudes is not None
        else [level_altitude for level_altitude, _sampler in profile]
    )

    for altitude_m in targets:
        sampler = sampler_at(altitude_m)
        # صعود = اختلاف *سطح پرواز* با سطحِ رسیدن، نه زمین زیر مبدأ. وقتی
        # قطعه در هوا شروع می‌شود (چک‌پوینت قفل‌شدهٔ قبلی)، هواپیما ارتفاع
        # آن چک‌پوینت را «همین‌حالا» دارد: صعود از زمین دوباره حساب‌شدنِ
        # ارتفاعی است که در قطعهٔ قبل پرداخت شده بود.
        climb_base_m = (
            max(ground_start, start_altitude_m)
            if start_altitude_m is not None
            else ground_start
        )
        climb_m = max(altitude_m - climb_base_m, 0.0)
        climb_hours = climb_m / verticals.climb_rate_mps / 3600.0

        def simulate(
            heading_deg: float,
            sampler: WindSampler = sampler,
            altitude_m: float = altitude_m,
            policy: WindRidingConfig = settings,
        ) -> _Simulation:
            """سمت را در همین لایه شبیه‌سازی می‌کند (پیش‌فرض‌ها دور متغیر گره می‌بندند).

            ``policy`` همان سیاستی است که در *این* فراخوانی آزموده می‌شود: زمانی
            که روی دالان بادسواری جست‌وجو می‌کنیم، هر دالان یک سیاست جداگانه است.
            """
            return _simulate_heading(
                origin,
                destination,
                sampler,
                descent_sampler,
                heading_deg,
                altitude_m=altitude_m,
                airspeed_mps=plane.airspeed_mps,
                glide_ratio=effort_settings.lift_to_drag,
                glide_power_fraction=effort_settings.descent_idle_power_fraction,
                config=policy,
                descent_ratio=descent_ratio,
                approach_km=settings.approach_km,
                ground_end_m=ground_end,
                ground_elevation_at=ground_elevation_at,
                clearance_floor_m=min_clearance_m,
                track_wind=settings.track_wind,
                sampler_for_altitude=sampler_at,
                land_at_end=land_at_end,
                start_altitude_m=start_altitude_m,
                # سقف شیب صعود (متر بر کیلومتر) = نرخ صعود ÷ سرعت زمینی. همان
                # عددی که ``VerticalCostConfig`` به گراف می‌دهد، پس دو مدل
                # «صعود ممکن» را با یک معیار می‌سنجند.
                max_climb_gradient=verticals.climb_rate_mps
                / max(plane.airspeed_mps, 1e-6)
                * 1000.0,
            )

        # کش جدا برای هر دالان: یک سمت فرمان زیر یک *سیاست* همیشه یک نتیجه
        # می‌دهد، ولی از یک دالان به دالان دیگر نتیجه فرق می‌کند، پس کش مشترک
        # غلط می‌شود.
        caches: dict[float, dict[float, _Simulation]] = {}

        def simulation(
            heading_deg: float,
            fraction: float,
            caches: dict[float, dict[float, _Simulation]] = caches,
        ) -> _Simulation:
            """شبیه‌سازی یک سمت زیر یک دالان مشخص، با کش.

            ``caches`` به‌عنوان آرگومان پیش‌فرض بسته می‌شود تا حلقهٔ سطوح پرواز
            یک دیکشنری *تازه* به هر تکرار بدهد (بستن متغیر حلقه خطای خاموش
            «کش مشترک بین سطوح» می‌سازد).
            """
            cache = caches.setdefault(round(fraction, 6), {})
            key = round(heading_deg % 360.0, 6)
            result = cache.get(key)
            if result is None:
                policy = (
                    settings
                    if math.isclose(fraction, settings.wind_corridor_fraction)
                    else dataclasses.replace(settings, wind_corridor_fraction=fraction)
                )
                result = simulate(heading_deg, policy=policy)
                cache[key] = result
            return result

        def rank(sim: _Simulation) -> tuple[float, float]:
            """رتبهٔ یک شبیه‌سازی در پویش سمت: اول کمترین خطای رسیدن، بعد کمترین زمان.

            ترتیب مهم است: پویش برای *رسیدن* انجام می‌شود و ریزکردن حول نامزدی
            ادامه می‌یابد که به مقصد نزدیک‌تر است. اگر اول زمان بیاید، پویش حول
            یک سمتِ سریعِ دورافتاده متمرکز می‌شود و سمت درست‌رسانده هرگز دیده
            نمی‌شود.
            """
            return (sim.miss_km, sim.flight_hours())

        initial = _bearing(origin[0], origin[1], destination[0], destination[1])
        # هر نامزد: (شبیه‌سازی، دالان سیاستی‌اش). دالان برای گزارش و برای
        # جداکردن «کم‌زمان‌ترین» از «موازی‌ترین» لازم است.
        candidates: list[tuple[_Simulation, float]] = []

        if settings.track_wind:
            # در حالت دنبال‌کردن باد، «سمت فرمان» دیگر یک پارامتر جست‌وجو نیست:
            # هر گام سمتش را از مثلث باد می‌گیرد، پس پویش ۳۶۰ درجه‌ای بی‌معنا
            # است. درجهٔ آزادی واقعی همان *دالان* است: هواپیما تا کجا اجازه دارد
            # از خط مبدأ–مقصد دور شود تا موازی باد بماند. برای هر دالان یک
            # شبیه‌سازی کامل اجرا می‌شود و کارنامهٔ هم‌راستایی‌اش نگه داشته
            # می‌شود.
            # سه حالت، به ترتیب اولویت:
            #   ۱) دالان صریح (``corridor_override``) — یک نامزد، بدون جست‌وجو.
            #      همین حالت «گونهٔ هم‌خانواده» را می‌سازد.
            #   ۲) جست‌وجوی چند دالانی (``alignment_first``) — نردبان دالان‌ها.
            #   ۳) سیاست قدیمی تک‌دالانی.
            if settings.corridor_override is not None:
                fractions = (settings.corridor_override,)
            elif settings.alignment_first:
                fractions = (settings.wind_corridor_fraction, *settings.search_fractions)
            else:
                fractions = (settings.wind_corridor_fraction,)
            for fraction in dict.fromkeys(round(value, 6) for value in fractions):
                candidates.append((simulation(initial, fraction), fraction))
        else:
            scan = [
                simulation(heading, settings.wind_corridor_fraction)
                for heading in _heading_scan(settings.heading_coarse_step_deg)
            ]
            seed = min(scan, key=rank)
            span = settings.heading_coarse_step_deg
            for step in settings.heading_refine_steps_deg:
                stage = [
                    simulation(heading, settings.wind_corridor_fraction)
                    for heading in _refine_scan(seed.heading_deg, span, step)
                ]
                scan.extend(stage)
                seed = min(stage, key=rank)
                span = step
            candidates = [(sim, settings.wind_corridor_fraction) for sim in scan]

        # شرط ایمنی زمین: مسیری که از داخل کوه می‌گذرد «قابل‌پرواز» نیست،
        # هرچند ریاضیات باد و گلایدش کامل باشد. بدون این فیلتر، بهترین
        # بادسواری می‌توانست مستقیم از میان قلهٔ بینالود رد شود — همان
        # چیزی که در گراف با حذف گره‌های زیر آستانه جلویش گرفته شد.
        flyable = [
            item
            for item in candidates
            if item[0].miss_km <= settings.max_arrival_miss_km
            and item[0].terrain_climb_feasible
            and (
                item[0].min_terrain_clearance_m is None
                or item[0].min_terrain_clearance_m >= min_clearance_m - 1e-9
            )
        ]
        if not flyable:
            continue
        # کارنامهٔ هم‌راستایی فقط برای نامزدهای قابل‌پرواز ساخته می‌شود (ساخت آن
        # ارزان است ولی روی صدها نامزد پویش سمت هم بی‌دلیل است).
        alignment_by_sim = {
            id(sim): wind_alignment_profile(sim.legs) for sim, _fraction in flyable
        }
        fastest = min(flyable, key=lambda item: item[0].flight_hours())
        time_limit = fastest[0].flight_hours() * settings.alignment_slack_ratio
        aligned = [
            item for item in flyable if item[0].flight_hours() <= time_limit + 1e-9
        ]
        if settings.alignment_first:
            # هدف: بیشترین مسافت موازی باد، و در تساوی، کم‌زمان‌ترین.
            chosen, chosen_fraction = max(
                aligned,
                key=lambda item: (
                    alignment_by_sim[id(item[0])].aligned_share,
                    -item[0].flight_hours(),
                ),
            )
        else:
            chosen, chosen_fraction = fastest
        chosen_profile = alignment_by_sim[id(chosen)]
        plan = WindRidingPlan(
            altitude_m=altitude_m,
            # در حالت دنبال‌کردن باد سمت *ثابت* نیست، پس گزارش «سمت فرمان»
            # نمی‌تواند یک سمت دلبخواه باشد: میانگین مسافت‌وزن سمت‌های هوایی
            # همین مسیر گزارش می‌شود — عددی که واقعاً پرواز شده است.
            heading_deg=(
                _mean_air_heading(chosen.legs, chosen.heading_deg)
                if settings.track_wind
                else chosen.heading_deg
            ),
            path=chosen.points,
            node_altitudes=chosen.altitudes,
            min_terrain_clearance_m=chosen.min_terrain_clearance_m,
            climb_m=climb_m,
            climb_time_hours=climb_hours,
            ride_time_hours=chosen.ride_hours,
            descent_time_hours=chosen.descent_hours,
            final_leg_hours=chosen.final_leg_hours,
            ride_distance_km=chosen.ride_km,
            descent_distance_km=chosen.descent_km,
            descent_slope_ratio=chosen.descent_slope_ratio,
            descent_power_fraction=chosen.descent_power_fraction,
            total_distance_km=chosen.ride_km + chosen.descent_km + chosen.final_leg_km,
            arrival_miss_km=chosen.miss_km,
            final_leg_km=chosen.final_leg_km,
            final_bearing_deg=chosen.final_bearing_deg,
            legs=chosen.legs,
            aligned_share=chosen_profile.aligned_share,
            parallel_mean_deg=chosen_profile.parallel_mean_deg,
            final_correction_km=chosen_profile.final_correction_km,
            corridor_fraction=chosen_fraction,
            land_at_end=land_at_end,
            start_altitude_m=start_altitude_m,
        )
        if best_plan is None or _plan_preference(plan, best_plan, settings):
            best_plan = plan

    return best_plan


def _plan_preference(
    plan: WindRidingPlan,
    best: WindRidingPlan,
    settings: WindRidingConfig,
) -> bool:
    """آیا ``plan`` از ``best`` بهتر است؟ (سیاست انتخاب بین سطوح پرواز).

    در حالت ``alignment_first`` هدف بیشترین سهم موازی باد است، مشروط به اینکه
    زمان از همان سقف ‎``alignment_slack_ratio``‎ روی سریع‌ترین سطح بیشتر نشود.
    بدون سقف، «بیشترین موازی» می‌تواند یک سطح کند را انتخاب کند که کاربر
    *به‌خاطر باد* نمی‌خواست؛ و بدون هدف، همان انتخاب کم‌زمان‌ترین قبلی می‌ماند.
    """
    if not settings.alignment_first:
        return plan.total_time_hours < best.total_time_hours
    # سقف زمانی: اختلاف دو سطح آن‌قدر زیاد نباشد که «موازی‌تر بودن» را به یک
    # پرواز بی‌معنا تبدیل کند.
    limit = min(plan.total_time_hours, best.total_time_hours) * settings.alignment_slack_ratio
    if plan.aligned_share > best.aligned_share + 1e-9:
        return plan.total_time_hours <= limit + 1e-9
    if math.isclose(plan.aligned_share, best.aligned_share, abs_tol=1e-9):
        return plan.total_time_hours < best.total_time_hours
    return False


def _mean_air_heading(legs: Sequence[LegSample], fallback: float) -> float:
    """میانگین مسافت‌وزن سمت‌های هوایی (میانگین دایره‌ای، نه میانگین معمولی).

    در حالت دنبال‌کردن باد سمت فرمان هر قطعه فرق دارد، پس جمع کردن سادهٔ اعداد
    درجه غلط می‌شود (۲۵۰ و ۳۵۰ به ۳۰۰ می‌رسند که هیچ‌کدام نیست). بردار یکهٔ هر
    سمت در جهت مسافتش وزن می‌گیرد و میانگین بردار، سمت را می‌دهد.
    """
    east = 0.0
    north = 0.0
    total = 0.0
    for leg in legs:
        if leg.air_heading_deg is None or leg.distance_km <= 0.0:
            continue
        weight = leg.distance_km
        radians = math.radians(leg.air_heading_deg)
        east += weight * math.sin(radians)
        north += weight * math.cos(radians)
        total += weight
    if total <= 0.0:
        return fallback
    return math.degrees(math.atan2(east, north)) % 360.0


def _drift_leg_metrics(
    heading_deg: float,
    wind_speed_mps: float,
    wind_direction_from_deg: float,
    airspeed_mps: float,
) -> tuple[float, float, float]:
    """سرعت زمینی و مؤلفه‌های باد نسبت به **سمت فرمان** (نه سمت مسیر).

    در پرواز با سمت ثابت، خلبان زاویهٔ تصحیح نمی‌گیرد؛ بردار سرعت زمینی مستقیماً
    ``airspeed·û(ψ) + W`` است. پس برخلاف حالت «نگه‌داشتن مسیر» (که در
    ``pathfinding.cost`` مدل شده)، مؤلفهٔ عمود باد سرعت زمینی را *کم نمی‌کند* بلکه
    آن را می‌چرخاند — و همین است که بادسواری را کارآمد می‌کند.

    برمی‌گرداند
    ----------
    (ground_speed_mps, along_heading_mps, cross_heading_mps)
        سرعت زمینی، مؤلفهٔ باد هم‌راستا با سمت فرمان (مثبت = کمک‌رسان) و اندازهٔ
        مؤلفهٔ عمود بر آن.
    """
    heading_rad = math.radians(heading_deg)
    wind_east, wind_north = _wind_vector(wind_speed_mps, wind_direction_from_deg)
    along = wind_east * math.sin(heading_rad) + wind_north * math.cos(heading_rad)
    cross = wind_east * math.cos(heading_rad) - wind_north * math.sin(heading_rad)
    ground_speed = math.sqrt(
        max(airspeed_mps**2 + wind_speed_mps**2 + 2.0 * airspeed_mps * along, 0.0)
    )
    return ground_speed, along, abs(cross)


def wind_riding_route_result(
    plan: WindRidingPlan,
    *,
    aircraft: CostModelConfig | None = None,
    effort: MotorEffortConfig | None = None,
    vertical: VerticalCostConfig | None = None,
    criterion: str = "energy",
    ground_elevation_at: Callable[[float, float], float] | None = None,
) -> RouteResult:
    """برنامهٔ بادسواری را به ``RouteResult`` تبدیل می‌کند تا با مسیرهای گرافی
    در همان جدول/صحنه مقایسه شود.

    دو حالت محاسبه، عمداً کنار هم:

    - **قطعه‌های بادسواری و فرود** سمت فرمان ثابت دارند، پس سرعت زمینی از
      ``airspeed·û(ψ) + W`` می‌آید و جریمه‌های شاخص انرژی (پسار القایی و بادِ
      رو-به-رو) نسبت به **سمت فرمان** سنجیده می‌شوند، نه سمت مسیر روی زمین.
    - **قطعهٔ پایانی** (اگر لازم شود) یک مسیر روی زمین است؛ همان‌جا
      ``compute_edge_cost`` استفاده می‌شود، مثل مسیرهای گرافی.

    «تغییر جهت» عمداً روی **سمت مسیر روی زمین** شمرده می‌شود (مثل بقیهٔ
    مسیرها): مسیر بادسواری روی زمین خمیده است ولی فرمانِ سمت ثابت می‌ماند و همین
    تفاوت استراتژی است. تعداد «تصحیح مسیر با موتور» در ستون مدل سوخت، صفر است.
    """
    plane = aircraft or CostModelConfig()
    effort_config = effort or MotorEffortConfig()
    verticals = vertical or VerticalCostConfig()

    # ۱) بازمحاسبهٔ دقیق قطعات: فاصلهٔ بزرگ‌دایره + زمان از همان مدل هزینه‌ای که
    #    مسیرهای گرافی با آن ساخته می‌شوند. حلقهٔ جست‌وجو با تقریب تخت کار کرده
    #    بود؛ این‌جا اعداد *گزارش‌شده* دقیق می‌شوند.
    legs: list[LegSample] = []
    total_distance = 0.0
    total_time = 0.0
    energy_index = 0.0
    tailwind_legs = 0
    for index, leg in enumerate(plan.legs):
        if index + 1 >= len(plan.path):
            break
        lat1, lon1 = plan.path[index]
        lat2, lon2 = plan.path[index + 1]
        distance_km = haversine_km(lat1, lon1, lat2, lon2)
        bearing = initial_bearing_deg(lat1, lon1, lat2, lon2)
        if leg.air_heading_deg is None:
            # حالت «نگه‌داشتن مسیر روی زمین» — مثل مسیرهای گرافی.
            result = compute_edge_cost(
                lat1,
                lon1,
                lat2,
                lon2,
                leg.wind_speed_mps,
                leg.wind_direction_from_deg,
                config=plane,
                criterion=criterion,
            )
            leg_time = result.time_hours
            leg_energy = result.energy_hours
            along = result.along_track_mps
        else:
            # حالت «نگه‌داشتن سمت فرمان» — خودِ بادسواری.
            ground_speed, along, cross = _drift_leg_metrics(
                leg.air_heading_deg,
                leg.wind_speed_mps,
                leg.wind_direction_from_deg,
                plane.airspeed_mps,
            )
            # زمان قطعه همان زمان *انتگرال‌گیری* است (ساعت شبیه‌سازی)، نه
            # مسافت/سرعتِ لحظه‌ای نمونه: در فاز بادسواری موقعیت با همان dt
            # انتگرال گرفته شده، پس این دو با هم سازگارند و اختلاف باد در طول
            # قطعه (۲ دقیقه‌ای) جمع نمی‌شود.
            leg_time = leg.time_hours or (
                distance_km / (ground_speed * 3.6) if ground_speed > 0.0 else 0.0
            )
            leg_energy = (
                leg_time
                * (1.0 + plane.induced_drag_coeff * (cross / plane.airspeed_mps) ** 2)
                * (
                    1.0
                    + plane.headwind_penalty_coeff
                    * max(0.0, -along)
                    / plane.airspeed_mps
                )
            )
        total_distance += distance_km
        total_time += leg_time
        energy_index += leg_energy
        if along > 0.0:
            tailwind_legs += 1
        legs.append(
            LegSample(
                track_bearing_deg=bearing,
                wind_speed_mps=leg.wind_speed_mps,
                wind_direction_from_deg=leg.wind_direction_from_deg,
                distance_km=distance_km,
                time_hours=leg_time,
                air_heading_deg=leg.air_heading_deg,
                # قطعه‌های فرود با همان کسر توانی سنجیده می‌شوند که برنامه‌ریز
                # از توازن رانش همان شیب بیرون داده؛ نتیجه‌اش این است که پروندهٔ
                # سوخت خودش تسویهٔ گرانش را می‌سازد (کار پسار منهای ``m·g·h`` که
                # راه کم‌کردن ارتفاع در همان مسافت می‌پردازد) و لازم نیست مقدار
                # ``descent_m`` هم داده شود — آن یکی همان تسویه را دو بار
                # می‌شمرد و سوخت را کمتر از واقع درمی‌آورد.
                power_fraction=leg.power_fraction,
            )
        )

    # ۲) صعود — یک فاز عمودی جدا در مبدأ، با همان تابع هزینهٔ گذار عمودی گراف
    #    تا «مسافت سه‌بعدی»، زمان و شاخص انرژی با مسیرهای گرافی هم‌مقیاس باشد.
    # **صعود واقعی = تا بلندترین نقطهٔ مسیر.** ارتفاع هواپیما در فاز بادسواری
    # همیشه سطح کروز نیست: اگر رشته‌کوه سر راه باشد هواپیما بالا می‌رود تا از
    # زمین رد شود (به کف زمین در ``_simulate_heading`` نگاه کنید). آن ارتفاع
    # اضافی هم با موتور گرفته شده، پس باید در کارنامهٔ سوخت حساب شود؛ وگرنه
    # «صعود برای رد شدن از کوه» یک وعدهٔ رایگان می‌شد که نیست.
    ground_start_msl = plan.altitude_m - plan.climb_m
    peak_altitude_m = max(plan.node_altitudes) if plan.node_altitudes else plan.altitude_m
    climb_height_m = max(peak_altitude_m - ground_start_msl, 0.0)
    # ارتفاع کل فرود = بلندترین نقطه منهای ارتفاع زمین **مقصد** (نه مبدأ): پروفیل
    # دقیقاً روی زمین مقصد تمام می‌شود، پس اگر مثل سمت صعود از زمین مبدأ شمرده
    # شود، اختلاف کوچک ناهمواری دو سر کریدور را نادیده می‌گیرد و مسیر بادسواری
    # یک عدد ناسازگار با بقیهٔ مسیرها گزارش می‌کند.
    descent_height_m = climb_height_m
    if plan.node_altitudes:
        descent_height_m = max(peak_altitude_m - float(plan.node_altitudes[-1]), 0.0)
    climb = compute_vertical_cost(
        climb_height_m, config=plane, criterion=criterion, vertical=verticals,
    )
    total_time += climb.time_hours
    energy_index += climb.energy_hours

    # فرود *جدا* شمرده نمی‌شود: در بادسواری، فرود درون همان فاز بادسواری و در
    # حرکت انجام می‌شود (هواپیما هنگام کم‌کردن ارتفاع هم جلو می‌رود)، پس زمانش
    # در قطعه‌های همین مسیر است و توانش هم در ``power_fraction`` همان قطعه‌ها
    # حساب شده. اگر انرژی پتانسیل فرود را جدا هم می‌نوشتیم، همان فاز دو بار
    # بهای سوخت می‌داد. تنها انرژی پتانسیل **صعود** شمرده می‌شود.
    #
    # نگاهی به کل: صعود ``mgh/η`` هزینه دارد و قطعه‌های فرود به اندازهٔ ``m·g·h``
    # کمتر از کروز توان می‌خواهند، پس دو تسویه یکدیگر را می‌گیرند و جمع برابر
    # «کار پسار در طول همان مسیر» می‌ماند — یعنی شکل پروفیل فرود (شیب ملایم یا
    # گلاید تند) سوخت را رایگان نمی‌کند، فقط جایش را عوض می‌کند.
    effort_result = compute_route_effort(
        legs,
        aircraft=plane,
        effort=effort_config,
        climb_m=climb_height_m,
        # صفر است و باید صفر بماند: مسافت فرود *داخل* قطعه‌های همین مسیر است و
        # با ``power_fraction`` به نرخ دور آرام بهای سوخت می‌دهد، پس اگر بُرد
        # گلاید را هم به‌عنوان تسویهٔ گرانش اضافه کنیم، همان سوخت دو بار
        # پس‌گرفته می‌شود.
        descent_m=0.0,
    )
    horizontal_legs = len(legs)

    # پروفیل عمودی: پلهٔ صعود → رمپ نرم و تدریجی (به توضیح بالای ``node_altitudes``
    # نگاه کنید). هم مسیر و هم ارتفاع‌ها از یک فراخوانی می‌آیند تا طولشان یکی
    # بماند.
    #
    # ``min_clearance_m`` صفر می‌ماند چون خود برنامه‌ریز فرود را زمین‌آگاه کرده و
    # پنجرهٔ نشستن خودش را دارد؛ دادن فاصلهٔ ایمنی این‌جا فقط مسیر را نزدیک مقصد
    # یک‌بار دیگر بالا می‌برد. ``glide_ratio`` هم داده می‌شود تا سقف شیب فرود در
    # همهٔ مسیرهای صحنه یک معنا داشته باشد (گلاید با موتور دور آرام).
    ramped_path, ramped_altitudes = ramp_vertical_transitions(
        plan.path,
        # لنگرگاه دو سر: تنها سرهای «روی زمین» صفر می‌شوند (سرهای در-هوای
        # چک‌پوینت قفل‌شده، ارتفاع واقعی MSLشان حفظ می‌شود).
        _ground_anchored_altitudes(
            plan.node_altitudes,
            anchor_start=plan.start_altitude_m is None,
            anchor_end=plan.land_at_end,
        ),
        climb_rate_mps=verticals.climb_rate_mps,
        descent_rate_mps=verticals.descent_rate_mps,
        ground_speed_mps=_mean_ground_speed_from_legs(legs, plane.airspeed_mps),
        ground_elevation_at=ground_elevation_at,
        glide_ratio=effort_config.glide_ratio,
    )

    return RouteResult(
        path=ramped_path,
        node_ids=[f"ride|{lat:.5f},{lon:.5f}" for lat, lon in ramped_path],
        layer_altitude=plan.altitude_m,
        total_cost=plan.total_time_hours,
        total_distance_km=total_distance,
        estimated_time_hours=total_time,
        criterion=criterion,
        total_energy_index=energy_index,
        tailwind_leg_fraction=(tailwind_legs / horizontal_legs) if horizontal_legs else 0.0,
        # «تغییر جهت» = تغییر سمت مسیر روی زمین (نه فرمان سمت)، مثل بقیه مسیرها.
        heading_changes=_ground_heading_changes(plan.path),
        algorithm="wind-riding",
        # پروفیل ارتفاع این مسیر پیوسته است (فرود با شيب)، پس تنها لایهٔ کروز
        # را صریح اعلام می‌کنیم. بدون این فیلد، ``altitudes_used`` هر ارتفاع
        # میانی فرود را یک «لایه» می‌شمرد و مسیر «چند لایه» به نظر می‌رسید.
        layers_used=(plan.altitude_m,),
        leg_samples=legs,
        # گره‌های زمین صفر گزارش می‌شوند — همان قرارداد ``RouteResult`` که
        # ``WindRouter`` هم رعایت می‌کند (به مستند ``node_altitudes`` نگاه کنید).
        # بدون این تبدیل، اولین گرهٔ همین مسیر ارتفاع *زمین* مبدأ (≈۹۸۳ متر)
        # را می‌گرفت در حالی که مسیر گرافی در همان نقطه صفر می‌دهد؛ یعنی دو
        # مسیر هم‌کریدور با دو مبنای متفاوت گزارش می‌شدند و مقایسهٔ «از زمین
        # تا زمین» فقط برای یکی از آن‌ها درست بود.
        # **پروفیل عمودی.** صعود این مسیر یک فاز عمودی جدا در مبدأ است (با همان
        # ``compute_vertical_cost`` مسیرهای گرافی)، پس در هندسهٔ گزارش‌شده هم
        # باید روی همان مسافت افقی پخش شود، نه یک دیوار در مبدأ. فرودِ خودِ
        # بادسواری از قبل پیوسته است، پس نرم‌کننده دستش را نمی‌زند؛ فقط همان
        # پلهٔ صعود را رمپ می‌کند. مسافت پخش از سرعت زمینی همین مسیر می‌آید.
        node_altitudes=ramped_altitudes,
        total_climb_m=climb_height_m,
        total_descent_m=descent_height_m,
        climb_legs=2,
        min_clearance_m=plan.min_terrain_clearance_m,
        effort=effort_result,
    )


def _mean_ground_speed_from_legs(
    legs: Sequence[LegSample],
    fallback_mps: float,
) -> float:
    """میانگین *وزنی‌به‌مسافت* سرعت زمینی قطعه‌های مسیر (متر بر ثانیه).

    مسافت افقی رمپ عمودی از این عدد می‌آید، پس باید از خود مسیر خوانده شود نه
    از یک ثابت: سرعت زمینی بادسواری با باد پشت به ۲۸ m/s می‌رسد در حالی که سرعت
    هوایی ۲۰ m/s است؛ اگر رمپ با سرعت هوایی ساخته شود، شیب صعود گزارش‌شده
    با شیبی که برناه‌ریز و مدل هزینه فرض کرده‌اند یکی نمی‌شود.
    """
    total_km = sum(leg.distance_km for leg in legs)
    if total_km <= 0.0:
        return max(fallback_mps, 1e-6)
    weighted = 0.0
    for leg in legs:
        if leg.time_hours > 0.0 and leg.distance_km > 0.0:
            weighted += leg.distance_km * (leg.distance_km / (leg.time_hours * 3.6))
    return max(weighted / total_km, 1e-6)


def _ground_anchored_altitudes(
    altitudes: Sequence[float],
    *,
    anchor_start: bool = True,
    anchor_end: bool = True,
) -> list[float]:
    """ارتفاع گره‌های زمین را صفر می‌کند (قرارداد ``RouteResult.node_altitudes``).

    پروفیل بادسواری از سطح زمین شروع و به سطح زمین تمام می‌شود، پس دو سر آن دو
    گرهٔ زمین‌اند و مثل مسیرهای گرافی باید صفر گزارش شوند. مقدار واقعی زمین
    (که ۹۰۰ تا ۳۰۰۰ متر است) در همان قرارداد گفته نمی‌شود؛ مصرف‌کنندهٔ صحنه
    خودش ارتفاع زمین محلی را از DEM می‌گیرد.

    در حالت عبوری چک‌پوینت قفل‌شدهٔ ارتفاعی، سرِ در-هوا این قرارداد را ندارد:
    گره‌ای که در ارتفاع ``start_altitude_m`` شروع می‌کند (قطعهٔ بعد از یک
    چک‌پوینتِ قفل‌شده) یا مقصدِ قطعه که خودش همان چک‌پوینتِ در-هواست
    (``land_at_end=False``) باید با ارتفاع واقعی MSL خودش بماند؛ صفرکردنش
    یعنی «شیرجه تا زمین» در همان نقطه — همان باگِ گزارش‌شدهٔ کاربر.
    """
    values = list(altitudes)
    if not values:
        return values
    if anchor_start:
        values[0] = 0.0
    if anchor_end:
        values[-1] = 0.0
    return values


def _ground_heading_changes(path: Sequence[tuple[float, float]], threshold_deg: float = 30.0) -> int:
    """تعداد تغییرهای بیش از ``threshold_deg`` در سمت *مسیر روی زمین*."""
    if len(path) < 3:
        return 0
    bearings = [
        _bearing(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
        for i in range(len(path) - 1)
    ]
    changes = 0
    for i in range(1, len(bearings)):
        diff = abs(bearings[i] - bearings[i - 1]) % 360.0
        turn = diff if diff <= 180.0 else 360.0 - diff
        if turn > threshold_deg:
            changes += 1
    return changes
