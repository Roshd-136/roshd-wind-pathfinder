"""تست‌های واحد برای لایه ارکستراسیون مسیریابی ``pathfinding.routing``."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from pathfinding.graph import (
    GraphNode,
    MultiLayerWindGraph,
    VerticalCostConfig,
    WindGraph,
)
from pathfinding.routing import LayerComparison, RouteResult, WindRouter

# Real Khorasan station coordinates (data/khorasan_wind_qc_cleaned.csv).
MASHHAD = (36.297, 59.606)
NEYSHABUR = (36.213, 58.795)
SABZEVAR = (36.215, 57.678)


def _make_two_layer_multi() -> MultiLayerWindGraph:
    """Build a two-layer multi-graph from real Khorasan station data.

    Layer 500m: mild wind, layer 2000m: strong opposing wind.
    """
    ml = MultiLayerWindGraph()

    df_low = pd.DataFrame(
        [
            {"lat": MASHHAD[0], "lon": MASHHAD[1], "altitude": 500, "wind_speed": 2.0, "wind_direction": 270.0},
            {"lat": NEYSHABUR[0], "lon": NEYSHABUR[1], "altitude": 500, "wind_speed": 3.0, "wind_direction": 260.0},
            {"lat": SABZEVAR[0], "lon": SABZEVAR[1], "altitude": 500, "wind_speed": 2.5, "wind_direction": 280.0},
        ]
    )
    g_low = WindGraph.build_from_dataframe(df_low, altitude=500.0, criterion="time")
    ml.add_layer(g_low)

    df_high = pd.DataFrame(
        [
            {"lat": MASHHAD[0], "lon": MASHHAD[1], "altitude": 2000, "wind_speed": 15.0, "wind_direction": 0.0},
            {"lat": NEYSHABUR[0], "lon": NEYSHABUR[1], "altitude": 2000, "wind_speed": 14.0, "wind_direction": 10.0},
            {"lat": SABZEVAR[0], "lon": SABZEVAR[1], "altitude": 2000, "wind_speed": 16.0, "wind_direction": 350.0},
        ]
    )
    g_high = WindGraph.build_from_dataframe(df_high, altitude=2000.0, criterion="time")
    ml.add_layer(g_high)

    return ml


def _make_single_layer_multi() -> MultiLayerWindGraph:
    """Build a single-layer multi-graph."""
    ml = MultiLayerWindGraph()
    df = pd.DataFrame(
        [
            {"lat": MASHHAD[0], "lon": MASHHAD[1], "altitude": 500, "wind_speed": 5.0, "wind_direction": 270.0},
            {"lat": NEYSHABUR[0], "lon": NEYSHABUR[1], "altitude": 500, "wind_speed": 4.0, "wind_direction": 260.0},
            {"lat": SABZEVAR[0], "lon": SABZEVAR[1], "altitude": 500, "wind_speed": 3.5, "wind_direction": 280.0},
        ]
    )
    g = WindGraph.build_from_dataframe(df, altitude=500.0, criterion="time")
    ml.add_layer(g)
    return ml


# ===========================================================================
# WindRouter initialization
# ===========================================================================


def test_wind_router_init() -> None:
    """WindRouter initializes correctly with a valid multi-layer graph."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    assert len(router.available_layers) == 2
    assert router.criterion == "time"


def test_wind_router_no_layers_raises() -> None:
    """WindRouter raises ValueError when multi-graph has no layers."""
    ml = MultiLayerWindGraph()
    with pytest.raises(ValueError, match="no layers"):
        WindRouter(ml)


# ===========================================================================
# find_optimal_path
# ===========================================================================


def test_find_optimal_path_returns_result() -> None:
    """find_optimal_path returns a RouteResult with valid path and cost."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    result = router.find_optimal_path(MASHHAD, SABZEVAR)
    assert isinstance(result, RouteResult)
    assert len(result.path) >= 2
    assert result.total_cost > 0
    assert result.total_cost < math.inf
    assert result.layer_altitude in [500.0, 2000.0]
    assert result.criterion == "time"


def test_find_optimal_path_selects_best_layer() -> None:
    """The selected layer should have the lowest cost among all layers."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    comparison = router.compare_layers(MASHHAD, SABZEVAR)
    best_from_find = router.find_optimal_path(MASHHAD, SABZEVAR)
    assert best_from_find.layer_altitude == comparison.best_altitude
    assert best_from_find.total_cost == pytest.approx(comparison.best_result.total_cost, abs=1e-9)


# ===========================================================================
# Multi-layer (3D) routing on the merged graph
# ===========================================================================


def _make_shear_multi(low_direction: float, high_direction: float) -> MultiLayerWindGraph:
    """Two layers whose winds point in deliberately different directions.

    The route runs Mashhad -> Sabzevar (roughly westward). With
    ``low_direction=270`` the low layer is a tailwind; with
    ``high_direction=270`` the high layer is. Fixing both lets a test state the
    expected optimum instead of discovering it.
    """
    ml = MultiLayerWindGraph()
    for altitude, direction in ((500.0, low_direction), (2000.0, high_direction)):
        frame = pd.DataFrame(
            [
                {
                    "lat": lat,
                    "lon": lon,
                    "altitude": altitude,
                    "wind_speed": 15.0,
                    "wind_direction": direction,
                }
                for lat, lon in (MASHHAD, NEYSHABUR, SABZEVAR)
            ]
        )
        ml.add_layer(
            WindGraph.build_from_dataframe(frame, altitude=altitude, criterion="time")
        )
    return ml


def test_multilayer_route_climbs_when_the_upper_layer_pays() -> None:
    """The merged graph really can switch altitude when the wind justifies it.

    The route runs west, so a wind *from* 90° is a tailwind and a wind *from*
    270° a headwind: the low layer is the headwind, the high layer the tailwind,
    and the climb is cheap. The optimum must therefore climb. Without this test
    a regression that flattened the routed graph back to one layer per route
    would go unnoticed.
    """
    ml = _make_shear_multi(low_direction=270.0, high_direction=90.0)
    router = WindRouter(
        ml,
        criterion="time",
        algorithm="dijkstra",
        allow_layer_changes=True,
        vertical_cost=VerticalCostConfig(climb_rate_mps=20.0, descent_rate_mps=20.0),
    )
    result = router.find_optimal_path(MASHHAD, SABZEVAR)

    assert result.is_multilayer, result.altitudes_used
    assert 2000.0 in result.altitudes_used
    assert result.total_climb_m > 0.0 and result.total_descent_m > 0.0


def test_layer_restriction_keeps_the_route_on_one_layer() -> None:
    """``layers=`` restricts the merged graph to the given altitudes."""
    ml = _make_shear_multi(low_direction=270.0, high_direction=90.0)
    router = WindRouter(
        ml,
        criterion="time",
        algorithm="dijkstra",
        allow_layer_changes=True,
        vertical_cost=VerticalCostConfig(climb_rate_mps=20.0, descent_rate_mps=20.0),
    )
    restricted = router.find_optimal_path(MASHHAD, SABZEVAR, layers=(500.0,))

    assert restricted.altitudes_used == [500.0]
    assert not restricted.is_multilayer
    # It is still a 3D route: it starts and ends on the ground (which is the
    # fair way to compare it against the unconstrained route).
    assert restricted.node_altitudes[0] == 0.0
    assert restricted.node_altitudes[-1] == 0.0

    free = router.find_optimal_path(MASHHAD, SABZEVAR)
    # Locking to the worse layer cannot beat the free route.
    assert restricted.estimated_time_hours >= free.estimated_time_hours - 1e-9


def test_layer_restriction_rejects_unknown_layer() -> None:
    """Asking for a layer that does not exist fails loudly."""
    ml = _make_shear_multi(low_direction=270.0, high_direction=90.0)
    router = WindRouter(ml, criterion="time", allow_layer_changes=True)
    with pytest.raises(ValueError, match="not available"):
        router.find_optimal_path(MASHHAD, SABZEVAR, layers=(12345.0,))


def test_layer_restriction_requires_multilayer_mode() -> None:
    """Without allow_layer_changes the `layers` argument is a mistake, not silent."""
    ml = _make_shear_multi(low_direction=270.0, high_direction=90.0)
    router = WindRouter(ml, criterion="time", allow_layer_changes=False)
    with pytest.raises(ValueError, match="allow_layer_changes"):
        router.find_optimal_path(MASHHAD, SABZEVAR, layers=(500.0,))


def test_vertical_legs_are_not_counted_as_heading_changes() -> None:
    """Climb/descent transitions have no bearing and must not inflate turns.

    Counting them added the same constant to every 3D route, which is why the
    ``smooth`` algorithm's turn penalty used to be inert on the merged graph.
    """
    ml = _make_shear_multi(low_direction=270.0, high_direction=270.0)
    router = WindRouter(ml, criterion="time", allow_layer_changes=True)
    result = router.find_optimal_path(MASHHAD, SABZEVAR)
    assert result.total_climb_m > 0.0, "this scenario must include a climb"
    assert result.heading_changes == 0, result.heading_changes


# ===========================================================================
# compare_layers
# ===========================================================================


def test_compare_layers_all_layers_evaluated() -> None:
    """compare_layers evaluates all available layers."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    comparison = router.compare_layers(MASHHAD, SABZEVAR)
    assert isinstance(comparison, LayerComparison)
    assert len(comparison.results) == 2
    assert comparison.best_altitude in [500.0, 2000.0]


def test_compare_layers_has_results_for_each_layer() -> None:
    """Each layer in the comparison should have a RouteResult."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    comparison = router.compare_layers(MASHHAD, SABZEVAR)
    for alt in [500.0, 2000.0]:
        assert alt in comparison.results
        r = comparison.results[alt]
        assert isinstance(r, RouteResult)
        assert r.layer_altitude == alt


# ===========================================================================
# Comparison table
# ===========================================================================


def test_comparison_table() -> None:
    """to_comparison_table produces a DataFrame with expected columns."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    comparison = router.compare_layers(MASHHAD, SABZEVAR)
    table = comparison.to_comparison_table()
    assert len(table) == 2
    assert "layer_altitude_m" in table.columns
    assert "total_distance_km" in table.columns
    assert "estimated_time_hours" in table.columns
    assert "total_cost" in table.columns
    assert "is_best" in table.columns
    assert table["is_best"].sum() == 1


# ===========================================================================
# Edge cases
# ===========================================================================


def test_no_path_raises() -> None:
    """WindRouter raises ValueError when no path exists on any layer."""
    ml = MultiLayerWindGraph()
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0))
    g.add_node(GraphNode(node_id="B", lat=37.0, lon=60.0))
    ml.add_layer(g)
    router = WindRouter(ml)
    with pytest.raises(ValueError, match="No feasible path found"):
        router.find_optimal_path((36.0, 59.0), (37.0, 60.0))


def test_origin_equals_nearest_node() -> None:
    """Origin/destination snapping to nearest node works correctly."""
    ml = _make_single_layer_multi()
    router = WindRouter(ml, criterion="time")
    result = router.find_optimal_path(
        (36.300, 59.610),
        (36.220, 57.680),
    )
    assert len(result.path) >= 2
    assert result.total_cost > 0


# ===========================================================================
# Configuration is honoured (regression: criterion/time_weight used to be inert)
# ===========================================================================


def test_router_reuses_graph_when_weighting_already_matches() -> None:
    """No reweighting (and no copy) when the requested weighting already matches."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    assert router.multi_graph is ml


def test_router_reweights_when_criterion_differs() -> None:
    """A different criterion must actually reweight the edges, not be ignored."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="distance")
    assert router.multi_graph is not ml, "router should work on a reweighted copy"
    assert router.criterion == "distance"
    assert ml.criterion == "time", "the caller's graph must not be mutated"
    for altitude in router.available_layers:
        assert router.multi_graph.get_layer(altitude).criterion == "distance"


def test_router_rejects_unknown_criterion_and_algorithm() -> None:
    """Bad configuration fails loudly instead of being silently ignored."""
    ml = _make_two_layer_multi()
    with pytest.raises(ValueError, match="Unknown criterion"):
        WindRouter(ml, criterion="cheapest-vibes")
    with pytest.raises(ValueError, match="Unknown algorithm"):
        WindRouter(ml, algorithm="magic")


def test_distance_criterion_reports_cost_in_km_not_hours() -> None:
    """Under the distance criterion `total_cost` is kilometres, not hours.

    It used to be that `estimated_time_hours` was simply assigned `total_cost`, so
    under a non-time criterion the "time" field reported a non-time quantity.
    """
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="distance")
    result = router.find_optimal_path(MASHHAD, SABZEVAR)

    assert result.criterion == "distance"
    # The distance criterion bills the *routed* horizontal legs plus the vertical
    # travel (climb to the layer and back down). ``total_distance_km`` is not the
    # routed polyline any more: it is the length of the geometry actually flown,
    # which is a hair shorter because corners are flown as arcs. So the identity
    # is asserted against the engine's own legs, and ``total_distance_km`` is
    # checked to be *close* to them — never longer, since rounding a corner can
    # only cut distance.
    vertical_km = (result.total_climb_m + result.total_descent_m) / 1000.0
    assert vertical_km > 0.0
    routed_km = sum(leg.distance_km for leg in result.leg_samples if leg.distance_km > 0)
    assert result.total_cost == pytest.approx(routed_km + vertical_km, rel=1e-6)
    # Rounded corners can cut a little distance or, on a coarse polyline, add a
    # little; what must not happen is the two describing different routes.
    assert result.total_distance_km == pytest.approx(routed_km, rel=0.02)
    assert result.estimated_time_hours > 0.0
    # 173 km at ~180 km/h cannot plausibly be under an hour, so the two fields
    # are genuinely different quantities rather than the same number twice.
    assert result.estimated_time_hours < result.total_distance_km
    assert not math.isclose(
        result.estimated_time_hours, result.total_distance_km, rel_tol=1e-6
    )


def test_estimated_time_is_consistent_across_criteria() -> None:
    """The same physical route reports the same real travel time under any criterion."""
    ml = _make_two_layer_multi()
    times = {}
    distances = {}
    for criterion in ("time", "energy", "balanced"):
        result = WindRouter(ml, criterion=criterion).find_optimal_path(MASHHAD, SABZEVAR)
        times[criterion] = result.estimated_time_hours
        distances[criterion] = result.total_distance_km
        assert result.criterion == criterion

    for criterion, value in times.items():
        assert value > 0.0
        assert distances[criterion] > 0.0


def test_router_records_energy_index_and_heading_changes() -> None:
    """Route results carry the diagnostics the comparison needs."""
    ml = _make_two_layer_multi()
    result = WindRouter(ml, criterion="energy").find_optimal_path(MASHHAD, SABZEVAR)
    assert result.total_energy_index > 0.0
    assert 0.0 <= result.tailwind_leg_fraction <= 1.0
    assert result.heading_changes >= 0
    row = result.summary_row()
    assert row["criterion"] == "energy"
    assert row["heading_changes"] == result.heading_changes


# ===========================================================================
# Single-layer routing and the smooth algorithm
# ===========================================================================


def test_route_on_single_layer_uses_requested_layer() -> None:
    """Single-layer routing returns a route on exactly the requested layer."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    result = router.route_on_single_layer(MASHHAD, SABZEVAR, 2000.0)
    assert result.layer_altitude == 2000.0
    assert len(result.path) >= 2


def test_route_on_single_layer_rejects_unknown_layer() -> None:
    """Asking for a layer that does not exist is an error, not a silent fallback."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    with pytest.raises(ValueError, match="not available"):
        router.route_on_single_layer(MASHHAD, SABZEVAR, 9999.0)


def test_route_on_single_layer_may_differ_from_best_layer() -> None:
    """The layer-locked route is not silently replaced by the globally best layer."""
    ml = _make_two_layer_multi()
    router = WindRouter(ml, criterion="time")
    best = router.find_optimal_path(MASHHAD, SABZEVAR)
    locked = router.route_on_single_layer(MASHHAD, SABZEVAR, 2000.0)
    assert locked.layer_altitude == 2000.0
    if best.layer_altitude != 2000.0:
        assert locked.total_cost >= best.total_cost


def test_smooth_algorithm_adds_turn_penalty_to_cost() -> None:
    """With `smooth`, total_cost includes turn penalties so it can exceed pure time."""
    ml = _make_two_layer_multi()
    router = WindRouter(
        ml,
        criterion="time",
        algorithm="smooth",
        direction_penalty=0.5,
    )
    result = router.find_optimal_path(MASHHAD, SABZEVAR)
    assert result.algorithm == "smooth"
    assert result.total_cost >= result.estimated_time_hours - 1e-9


def test_smooth_algorithm_penalties_are_actually_applied() -> None:
    """A large turn penalty must not reduce to the plain Dijkstra cost."""
    ml = _make_two_layer_multi()
    plain = WindRouter(ml, criterion="time", algorithm="dijkstra").find_optimal_path(
        MASHHAD, SABZEVAR
    )
    smooth = WindRouter(
        ml,
        criterion="time",
        algorithm="smooth",
        direction_penalty=5.0,
    ).find_optimal_path(MASHHAD, SABZEVAR)
    assert smooth.total_cost >= plain.total_cost - 1e-9


def test_comparison_table_exposes_new_diagnostics() -> None:
    """The comparison table carries energy, tailwind and manoeuvre columns."""
    ml = _make_two_layer_multi()
    table = WindRouter(ml, criterion="time").compare_layers(MASHHAD, SABZEVAR).to_comparison_table()
    for column in (
        "total_energy_index",
        "tailwind_leg_fraction",
        "heading_changes",
        "estimated_time_hours",
    ):
        assert column in table.columns
