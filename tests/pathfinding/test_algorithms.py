"""تست‌های واحد برای الگوریتم‌های مسیریابی ``pathfinding.algorithms``."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from pathfinding.algorithms import a_star, dijkstra
from pathfinding.graph import EdgeData, GraphNode, WindGraph

# Real Khorasan station coordinates (data/khorasan_wind_qc_cleaned.csv).
MASHHAD = (36.297, 59.606)
NEYSHABUR = (36.213, 58.795)
SABZEVAR = (36.215, 57.678)


def _node_id(lat: float, lon: float) -> str:
    return f"{lat:.6f},{lon:.6f}"


def _make_linear_graph() -> WindGraph:
    """Three-node linear graph: A->B->C, with manually set costs."""
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0, wind_speed_mps=5.0, wind_direction_deg=270.0))
    g.add_node(GraphNode(node_id="B", lat=36.5, lon=59.5, wind_speed_mps=3.0, wind_direction_deg=180.0))
    g.add_node(GraphNode(node_id="C", lat=37.0, lon=60.0, wind_speed_mps=7.0, wind_direction_deg=90.0))
    # A->B: 1.5h, B->C: 2.0h
    g.add_edge(EdgeData(from_node="A", to_node="B", distance_km=70.0, weight=1.5))
    g.add_edge(EdgeData(from_node="B", to_node="A", distance_km=70.0, weight=1.5))
    g.add_edge(EdgeData(from_node="B", to_node="C", distance_km=70.0, weight=2.0))
    g.add_edge(EdgeData(from_node="C", to_node="B", distance_km=70.0, weight=2.0))
    return g


def _make_diamond_graph() -> WindGraph:
    """Diamond: A->B(2), A->C(5), B->D(1), C->D(2). Cheapest: A->B->D = 3."""
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0))
    g.add_node(GraphNode(node_id="B", lat=36.5, lon=59.5))
    g.add_node(GraphNode(node_id="C", lat=35.5, lon=59.5))
    g.add_node(GraphNode(node_id="D", lat=36.5, lon=60.0))
    g.add_edge(EdgeData(from_node="A", to_node="B", distance_km=70.0, weight=2.0))
    g.add_edge(EdgeData(from_node="A", to_node="C", distance_km=70.0, weight=5.0))
    g.add_edge(EdgeData(from_node="B", to_node="D", distance_km=70.0, weight=1.0))
    g.add_edge(EdgeData(from_node="C", to_node="D", distance_km=70.0, weight=2.0))
    return g


def _make_two_layer_graph() -> tuple[WindGraph, WindGraph]:
    """Two layers with different costs for the same linear path A->B->C."""
    g_low = WindGraph(altitude=500.0)
    g_high = WindGraph(altitude=2000.0)
    for g, cost_ab, cost_bc in [(g_low, 1.5, 2.0), (g_high, 1.0, 3.0)]:
        g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0))
        g.add_node(GraphNode(node_id="B", lat=36.5, lon=59.5))
        g.add_node(GraphNode(node_id="C", lat=37.0, lon=60.0))
        g.add_edge(EdgeData(from_node="A", to_node="B", distance_km=70.0, weight=cost_ab))
        g.add_edge(EdgeData(from_node="B", to_node="A", distance_km=70.0, weight=cost_ab))
        g.add_edge(EdgeData(from_node="B", to_node="C", distance_km=70.0, weight=cost_bc))
        g.add_edge(EdgeData(from_node="C", to_node="B", distance_km=70.0, weight=cost_bc))
    return g_low, g_high


# ===========================================================================
# Dijkstra tests
# ===========================================================================


def test_dijkstra_linear_path() -> None:
    """Dijkstra finds shortest path in a linear graph."""
    g = _make_linear_graph()
    path, cost = dijkstra(g, "A", "C")
    assert path == ["A", "B", "C"]
    assert cost == pytest.approx(3.5, abs=1e-6)


def test_dijkstra_direct_path() -> None:
    """Dijkstra with two connected nodes."""
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="X", lat=36.0, lon=59.0))
    g.add_node(GraphNode(node_id="Y", lat=36.5, lon=59.5))
    g.add_edge(EdgeData(from_node="X", to_node="Y", distance_km=70.0, weight=1.2))
    path, cost = dijkstra(g, "X", "Y")
    assert path == ["X", "Y"]
    assert cost == pytest.approx(1.2, abs=1e-6)


def test_dijkstra_no_path() -> None:
    """Dijkstra returns empty path when destination is unreachable."""
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0))
    g.add_node(GraphNode(node_id="B", lat=36.5, lon=59.5))
    g.add_node(GraphNode(node_id="C", lat=37.0, lon=60.0))
    g.add_edge(EdgeData(from_node="A", to_node="B", distance_km=70.0, weight=1.0))
    path, cost = dijkstra(g, "A", "C")
    assert path == []
    assert math.isinf(cost)


def test_dijkstra_infinite_weight_edge_skipped() -> None:
    """Edges with inf weight are skipped by Dijkstra."""
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0))
    g.add_node(GraphNode(node_id="B", lat=36.5, lon=59.5))
    g.add_node(GraphNode(node_id="C", lat=37.0, lon=60.0))
    g.add_edge(EdgeData(from_node="A", to_node="B", distance_km=70.0, weight=math.inf))
    g.add_edge(EdgeData(from_node="A", to_node="C", distance_km=70.0, weight=1.0))
    path, cost = dijkstra(g, "A", "C")
    assert path == ["A", "C"]
    assert cost == pytest.approx(1.0, abs=1e-6)


def test_dijkstra_start_not_in_graph() -> None:
    g = _make_linear_graph()
    path, cost = dijkstra(g, "nonexistent", "C")
    assert path == []
    assert math.isinf(cost)


def test_dijkstra_end_not_in_graph() -> None:
    g = _make_linear_graph()
    path, cost = dijkstra(g, "A", "nonexistent")
    assert path == []
    assert math.isinf(cost)


def test_dijkstra_same_start_and_end() -> None:
    g = _make_linear_graph()
    path, cost = dijkstra(g, "A", "A")
    assert path == ["A"]
    assert cost == 0.0


# ===========================================================================
# A* tests
# ===========================================================================


def test_a_star_linear_path() -> None:
    """A* finds shortest path in a linear graph."""
    g = _make_linear_graph()
    path, cost = a_star(g, "A", "C")
    assert path == ["A", "B", "C"]
    assert cost == pytest.approx(3.5, abs=1e-6)


def test_a_star_no_path() -> None:
    """A* returns empty path when destination is unreachable."""
    g = WindGraph(altitude=500.0)
    g.add_node(GraphNode(node_id="A", lat=36.0, lon=59.0))
    g.add_node(GraphNode(node_id="C", lat=37.0, lon=60.0))
    path, cost = a_star(g, "A", "C")
    assert path == []
    assert math.isinf(cost)


def test_a_star_start_not_in_graph() -> None:
    g = _make_linear_graph()
    path, cost = a_star(g, "nonexistent", "C")
    assert path == []
    assert math.isinf(cost)


def test_a_star_end_not_in_graph() -> None:
    g = _make_linear_graph()
    path, cost = a_star(g, "A", "nonexistent")
    assert path == []
    assert math.isinf(cost)


def test_a_star_same_start_and_end() -> None:
    g = _make_linear_graph()
    path, cost = a_star(g, "A", "A")
    assert path == ["A"]
    assert cost == 0.0


def test_a_star_diamond_optimal_path() -> None:
    """A* finds cheapest path in diamond: A->B->D (cost 3.0), not A->C->D (cost 7.0)."""
    g = _make_diamond_graph()
    path, cost = a_star(g, "A", "D")
    assert path == ["A", "B", "D"]
    assert cost == pytest.approx(3.0, abs=1e-6)


# ===========================================================================
# Critical: A* and Dijkstra produce identical costs
# ===========================================================================


def test_dijkstra_and_astar_same_cost_linear() -> None:
    """A* and Dijkstra MUST produce identical costs on the same graph (linear)."""
    g = _make_linear_graph()
    path_d, cost_d = dijkstra(g, "A", "C")
    path_a, cost_a = a_star(g, "A", "C")
    assert path_d == path_a
    assert cost_d == pytest.approx(cost_a, abs=1e-9)


def test_dijkstra_and_astar_same_cost_diamond() -> None:
    """A* and Dijkstra MUST produce identical costs on the same graph (diamond)."""
    g = _make_diamond_graph()
    path_d, cost_d = dijkstra(g, "A", "D")
    path_a, cost_a = a_star(g, "A", "D")
    assert path_d == path_a
    assert cost_d == pytest.approx(cost_a, abs=1e-9)


def test_dijkstra_and_astar_same_cost_multi_layer() -> None:
    """A* and Dijkstra MUST produce identical costs on both layers."""
    g_low, g_high = _make_two_layer_graph()
    for g in [g_low, g_high]:
        path_d, cost_d = dijkstra(g, "A", "C")
        path_a, cost_a = a_star(g, "A", "C")
        assert path_d == path_a
        assert cost_d == pytest.approx(cost_a, abs=1e-9)


def test_dijkstra_and_astar_same_cost_real_khorasan() -> None:
    """A* and Dijkstra MUST agree on cost for a real Khorasan graph."""
    df = pd.DataFrame(
        [
            {"lat": MASHHAD[0], "lon": MASHHAD[1], "wind_speed": 5.0, "wind_direction": 286.0},
            {"lat": NEYSHABUR[0], "lon": NEYSHABUR[1], "wind_speed": 3.5, "wind_direction": 310.0},
            {"lat": SABZEVAR[0], "lon": SABZEVAR[1], "wind_speed": 4.2, "wind_direction": 250.0},
        ]
    )
    g = WindGraph.build_from_dataframe(df, altitude=500.0, criterion="time")
    start = _node_id(*MASHHAD)
    end = _node_id(*SABZEVAR)
    path_d, cost_d = dijkstra(g, start, end)
    path_a, cost_a = a_star(g, start, end)
    assert path_d == path_a
    assert cost_d == pytest.approx(cost_a, abs=1e-9)


# ===========================================================================
# Benchmark: A* explores fewer nodes than Dijkstra
# ===========================================================================


def test_astar_explores_fewer_or_equal_nodes_than_dijkstra() -> None:
    """On a large graph, A* explores <= nodes than Dijkstra (Haversine heuristic helps)."""
    # Build a larger graph by adding grid points
    g = WindGraph(altitude=500.0)
    nodes_added = []
    for lat_step in range(5):
        for lon_step in range(5):
            lat = 36.0 + lat_step * 0.1
            lon = 58.0 + lon_step * 0.2
            nid = f"{lat:.6f},{lon:.6f}"
            g.add_node(GraphNode(
                node_id=nid, lat=lat, lon=lon,
                wind_speed_mps=5.0, wind_direction_deg=270.0,
            ))
            nodes_added.append(nid)

    # Connect grid neighbors
    from preprocessing.consistency import haversine_km
    all_nodes = list(g.nodes.values())
    for i, na in enumerate(all_nodes):
        for nb in all_nodes[i + 1:]:
            dist = haversine_km(na.lat, na.lon, nb.lat, nb.lon)
            if dist < 30.0:
                cost = dist / 50.0 * 3.6
                g.add_edge(EdgeData(from_node=na.node_id, to_node=nb.node_id, distance_km=dist, weight=cost))
                g.add_edge(EdgeData(from_node=nb.node_id, to_node=na.node_id, distance_km=dist, weight=cost))

    start = _node_id(36.0, 58.0)
    end = _node_id(36.4, 58.8)

    path_d, cost_d = dijkstra(g, start, end)
    path_a, cost_a = a_star(g, start, end)
    assert cost_d == pytest.approx(cost_a, abs=1e-9)
    assert len(path_a) <= len(path_d) + 2
