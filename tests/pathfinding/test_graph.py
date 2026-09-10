"""تست‌های واحد برای ساخت گراف بادی چندلایه ``pathfinding.graph``."""

from __future__ import annotations

import pandas as pd
import pytest

from pathfinding.graph import EdgeData, GraphNode, MultiLayerWindGraph, WindGraph

# Real Khorasan station coordinates (data/khorasan_wind_qc_cleaned.csv).
MASHHAD = (36.297, 59.606)
NEYSHABUR = (36.213, 58.795)
SABZEVAR = (36.215, 57.678)


# ---------------------------------------------------------------------------
# Helper: build a small connected graph manually
# ---------------------------------------------------------------------------


def _make_three_station_graph(altitude: float = 500.0) -> WindGraph:
    """Three real Khorasan stations connected with mild wind."""
    graph = WindGraph(altitude=altitude)
    for _name, (lat, lon) in [
        ("Mashhad", MASHHAD),
        ("Neyshabur", NEYSHABUR),
        ("Sabzevar", SABZEVAR),
    ]:
        graph.add_node(
            GraphNode(
                node_id=f"{lat:.6f},{lon:.6f}",
                lat=lat,
                lon=lon,
                wind_speed_mps=5.0,
                wind_direction_deg=270.0,
                altitude=altitude,
            )
        )
    # Connect all pairs
    graph.get_neighbors(
        list(graph.nodes.keys())[0]
    ) or []
    all_ids = sorted(graph.nodes.keys())
    for i, a in enumerate(all_ids):
        for b in all_ids[i + 1 :]:
            from preprocessing.consistency import haversine_km

            na = graph.get_node(a)
            nb = graph.get_node(b)
            assert na is not None and nb is not None
            dist = haversine_km(na.lat, na.lon, nb.lat, nb.lon)
            from pathfinding.cost import compute_edge_cost

            cost_ab = compute_edge_cost(
                na.lat, na.lon, nb.lat, nb.lon,
                na.wind_speed_mps, na.wind_direction_deg,
                criterion="time",
            )
            graph.add_edge(
                EdgeData(from_node=a, to_node=b, distance_km=dist,
                         cost_result=cost_ab, weight=cost_ab.cost)
            )
            cost_ba = compute_edge_cost(
                nb.lat, nb.lon, na.lat, na.lon,
                nb.wind_speed_mps, nb.wind_direction_deg,
                criterion="time",
            )
            graph.add_edge(
                EdgeData(from_node=b, to_node=a, distance_km=dist,
                         cost_result=cost_ba, weight=cost_ba.cost)
            )
    return graph


# ---------------------------------------------------------------------------
# Tests: WindGraph basic operations
# ---------------------------------------------------------------------------


def test_empty_graph() -> None:
    g = WindGraph(altitude=0.0)
    assert g.node_count == 0
    assert g.edge_count == 0
    assert g.nodes == {}


def test_add_node_and_get_node() -> None:
    g = WindGraph(altitude=500.0)
    node = GraphNode(node_id="A", lat=36.0, lon=59.0, wind_speed_mps=5.0, wind_direction_deg=180.0)
    g.add_node(node)
    assert g.node_count == 1
    assert g.get_node("A") is node
    assert g.get_node("nonexistent") is None


def test_add_edge_and_get_edge() -> None:
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0))
    g.add_node(GraphNode(node_id="B", lat=36.5, lon=59.5))
    edge = EdgeData(from_node="A", to_node="B", distance_km=50.0, weight=1.5)
    g.add_edge(edge)
    assert g.edge_count == 1
    retrieved = g.get_edge("A", "B")
    assert retrieved is not None
    assert retrieved.weight == 1.5
    # Reverse direction not created (half-edge model)
    assert g.get_edge("B", "A") is None


def test_get_neighbors() -> None:
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0))
    g.add_node(GraphNode(node_id="B", lat=36.5, lon=59.5))
    g.add_node(GraphNode(node_id="C", lat=37.0, lon=60.0))
    g.add_edge(EdgeData(from_node="A", to_node="B", distance_km=50.0, weight=1.0))
    g.add_edge(EdgeData(from_node="A", to_node="C", distance_km=100.0, weight=2.0))
    neighbors = g.get_neighbors("A")
    assert neighbors == ["B", "C"]


def test_find_nearest_node() -> None:
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="Mashhad", lat=36.297, lon=59.606))
    g.add_node(GraphNode(node_id="Sabzevar", lat=36.215, lon=57.678))
    # Point closer to Mashhad
    nearest = g.find_nearest_node(36.3, 59.5)
    assert nearest == "Mashhad"
    # Point closer to Sabzevar
    nearest = g.find_nearest_node(36.2, 57.7)
    assert nearest == "Sabzevar"


def test_find_nearest_node_empty_graph() -> None:
    g = WindGraph(altitude=0.0)
    assert g.find_nearest_node(36.0, 59.0) is None


# ---------------------------------------------------------------------------
# Tests: build_from_dataframe
# ---------------------------------------------------------------------------


def test_build_from_dataframe_basic() -> None:
    """Build a simple graph from a DataFrame with two nodes and verify structure."""
    df = pd.DataFrame(
        [
            {"lat": 36.297, "lon": 59.606, "wind_speed": 5.0, "wind_direction": 270.0},
            {"lat": 36.213, "lon": 58.795, "wind_speed": 3.0, "wind_direction": 180.0},
        ]
    )
    g = WindGraph.build_from_dataframe(df, altitude=500.0)
    assert g.node_count == 2
    assert g.altitude == 500.0
    # Two nodes within 200 km → edges both directions
    assert g.edge_count == 2


def test_build_from_dataframe_missing_columns() -> None:
    df = pd.DataFrame([{"lat": 36.0, "lon": 59.0}])
    with pytest.raises(ValueError, match="DataFrame missing required wind columns"):
        WindGraph.build_from_dataframe(df, altitude=500.0)


def test_build_from_dataframe_alternate_column_names() -> None:
    """pathfinding_preparation uses 'speed' and 'direction' column names."""
    df = pd.DataFrame(
        [
            {"lat": 36.297, "lon": 59.606, "speed": 5.0, "direction": 270.0},
            {"lat": 36.213, "lon": 58.795, "speed": 3.0, "direction": 180.0},
        ]
    )
    g = WindGraph.build_from_dataframe(df, altitude=1000.0)
    assert g.node_count == 2
    assert g.edge_count == 2


def test_build_from_dataframe_averages_timestamps() -> None:
    """Multiple timestamps for same lat/lon should be averaged."""
    df = pd.DataFrame(
        [
            {"lat": 36.297, "lon": 59.606, "wind_speed": 4.0, "wind_direction": 270.0, "timestamp": "t1"},
            {"lat": 36.297, "lon": 59.606, "wind_speed": 8.0, "wind_direction": 270.0, "timestamp": "t2"},
        ]
    )
    g = WindGraph.build_from_dataframe(df, altitude=500.0)
    assert g.node_count == 1
    node = list(g.nodes.values())[0]
    assert node.wind_speed_mps == pytest.approx(6.0, abs=1e-6)


def test_build_from_dataframe_filters_nan() -> None:
    """Rows with NaN wind data should be dropped."""
    df = pd.DataFrame(
        [
            {"lat": 36.297, "lon": 59.606, "wind_speed": 5.0, "wind_direction": 270.0},
            {"lat": 36.213, "lon": 58.795, "wind_speed": float("nan"), "wind_direction": float("nan")},
        ]
    )
    g = WindGraph.build_from_dataframe(df, altitude=500.0)
    assert g.node_count == 1


def test_build_from_dataframe_far_nodes_no_edges() -> None:
    """Nodes farther than max_edge_distance_km should have no edges."""
    df = pd.DataFrame(
        [
            {"lat": 36.297, "lon": 59.606, "wind_speed": 5.0, "wind_direction": 270.0},
            {"lat": 35.000, "lon": 50.000, "wind_speed": 3.0, "wind_direction": 180.0},
        ]
    )
    g = WindGraph.build_from_dataframe(df, altitude=500.0, max_edge_distance_km=50.0)
    assert g.node_count == 2
    assert g.edge_count == 0


# ---------------------------------------------------------------------------
# Tests: MultiLayerWindGraph
# ---------------------------------------------------------------------------


def test_multi_layer_empty() -> None:
    ml = MultiLayerWindGraph()
    assert ml.layer_count == 0
    assert ml.available_layers == []


def test_multi_layer_build_from_dataframe() -> None:
    df = pd.DataFrame(
        [
            {"lat": 36.297, "lon": 59.606, "altitude": 500, "wind_speed": 5.0, "wind_direction": 270.0},
            {"lat": 36.297, "lon": 59.606, "altitude": 1000, "wind_speed": 8.0, "wind_direction": 240.0},
            {"lat": 36.297, "lon": 59.606, "altitude": 1500, "wind_speed": float("nan"), "wind_direction": float("nan")},
        ]
    )
    ml = MultiLayerWindGraph.build_from_dataframe(df)
    # Layer 1500 has only NaN → dropped
    assert ml.layer_count == 2
    assert ml.available_layers == [500.0, 1000.0]


def test_multi_layer_build_no_altitude_column() -> None:
    """DataFrame without altitude column → single layer at altitude=0."""
    df = pd.DataFrame(
        [
            {"lat": 36.297, "lon": 59.606, "wind_speed": 5.0, "wind_direction": 270.0},
        ]
    )
    ml = MultiLayerWindGraph.build_from_dataframe(df)
    assert ml.layer_count == 1
    assert ml.available_layers == [0.0]
