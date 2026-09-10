"""تست‌های واحد برای لایه ارکستراسیون مسیریابی ``pathfinding.routing``."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from pathfinding.graph import GraphNode, MultiLayerWindGraph, WindGraph
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
