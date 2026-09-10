"""تست‌های واحد برای الگوریتم‌های مسیریابی (``pathfinding.algorithms``)."""

from __future__ import annotations

import math

import pytest

from pathfinding.algorithms import a_star, dijkstra
from pathfinding.graph import EdgeData, GraphNode, WindGraph

# ---------------------------------------------------------------------------
# کمک‌تابع: ساخت گراف ساده دستی
# ---------------------------------------------------------------------------

def _build_triangle_graph() -> WindGraph:
    """گراف مثلثی ساده: A — B — C با وزن‌های مشخص.

    A(36.0, 58.0) — B(36.0, 58.2) — C(36.0, 58.4)
    یال A→B: وزن 1.0    یال B→C: وزن 1.0
    یال A→C: وزن 3.0 (مسیر مستقیم ولی سنگین)
    """
    g = WindGraph(altitude=500.0, max_edge_distance_km=500.0)
    g.add_node(GraphNode("A", 36.0, 58.0, wind_speed_mps=5.0, wind_direction_deg=270.0))
    g.add_node(GraphNode("B", 36.0, 58.2, wind_speed_mps=5.0, wind_direction_deg=270.0))
    g.add_node(GraphNode("C", 36.0, 58.4, wind_speed_mps=5.0, wind_direction_deg=270.0))

    g.add_edge(EdgeData("A", "B", distance_km=18.5, weight=1.0))
    g.add_edge(EdgeData("B", "A", distance_km=18.5, weight=1.0))
    g.add_edge(EdgeData("B", "C", distance_km=18.5, weight=1.0))
    g.add_edge(EdgeData("C", "B", distance_km=18.5, weight=1.0))
    g.add_edge(EdgeData("A", "C", distance_km=37.0, weight=3.0))
    g.add_edge(EdgeData("C", "A", distance_km=37.0, weight=3.0))
    return g


def _build_asymmetric_graph() -> WindGraph:
    """گراف نامتقارن: وزن A→B ≠ B→A (شبیه باد واقعی).

    A(36.0, 58.0) — B(36.0, 58.2)
    A→B وزن 0.5 (باد پشت)    B→A وزن 2.0 (باد رو-به-رو)
    """
    g = WindGraph(altitude=500.0, max_edge_distance_km=500.0)
    g.add_node(GraphNode("A", 36.0, 58.0, wind_speed_mps=10.0, wind_direction_deg=270.0))
    g.add_node(GraphNode("B", 36.0, 58.2, wind_speed_mps=10.0, wind_direction_deg=90.0))

    g.add_edge(EdgeData("A", "B", distance_km=18.5, weight=0.5))
    g.add_edge(EdgeData("B", "A", distance_km=18.5, weight=2.0))
    return g


# ---------------------------------------------------------------------------
# تست‌های Dijkstra
# ---------------------------------------------------------------------------

class TestDijkstra:
    """تست‌های الگوریتم Dijkstra."""

    def test_shortest_path_via_middle(self) -> None:
        """مسیر بهینه از A به C باید از B عبور کند (وزن کل 2.0)."""
        g = _build_triangle_graph()
        path, cost = dijkstra(g, "A", "C")
        assert path == ["A", "B", "C"]
        assert cost == pytest.approx(2.0)

    def test_direct_shortest(self) -> None:
        """مسیر مستقیم A→B (وزن 1.0)."""
        g = _build_triangle_graph()
        path, cost = dijkstra(g, "A", "B")
        assert path == ["A", "B"]
        assert cost == pytest.approx(1.0)

    def test_same_start_end(self) -> None:
        """مسیر از A به A باید خود A باشد."""
        g = _build_triangle_graph()
        path, cost = dijkstra(g, "A", "A")
        assert path == ["A"]
        assert cost == pytest.approx(0.0)

    def test_no_path(self) -> None:
        """اگر مسیری وجود نداشته باشد، لیست خالی."""
        g = WindGraph(altitude=500.0)
        g.add_node(GraphNode("A", 36.0, 58.0))
        g.add_node(GraphNode("B", 37.0, 59.0))
        path, cost = dijkstra(g, "A", "B")
        assert path == []
        assert cost == math.inf

    def test_nonexistent_node(self) -> None:
        """گره وجود ندارد."""
        g = _build_triangle_graph()
        path, cost = dijkstra(g, "A", "Z")
        assert path == []
        assert cost == math.inf

    def test_asymmetric_path_prefers_tailwind(self) -> None:
        """مسیر A→B ارزان‌تر (باد پشت) ولی B→A گران‌تر (باد رو-به-رو)."""
        g = _build_asymmetric_graph()
        _, cost_ab = dijkstra(g, "A", "B")
        _, cost_ba = dijkstra(g, "B", "A")
        assert cost_ab == pytest.approx(0.5)
        assert cost_ba == pytest.approx(2.0)
        assert cost_ab < cost_ba

    def test_infinite_edge_skipped(self) -> None:
        """یال با وزن inf باید نادیده گرفته شود."""
        g = WindGraph(altitude=500.0, max_edge_distance_km=500.0)
        g.add_node(GraphNode("A", 36.0, 58.0))
        g.add_node(GraphNode("B", 36.0, 58.2))
        g.add_node(GraphNode("C", 36.0, 58.4))
        g.add_edge(EdgeData("A", "B", 18.5, weight=1.0))
        g.add_edge(EdgeData("B", "A", 18.5, weight=1.0))
        g.add_edge(EdgeData("A", "C", 37.0, weight=math.inf))
        g.add_edge(EdgeData("C", "A", 37.0, weight=3.0))
        g.add_edge(EdgeData("B", "C", 18.5, weight=1.0))
        g.add_edge(EdgeData("C", "B", 18.5, weight=1.0))
        path, cost = dijkstra(g, "A", "C")
        assert path == ["A", "B", "C"]
        assert cost == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# تست‌های A*
# ---------------------------------------------------------------------------

class TestAStar:
    """تست‌های الگوریتم A*."""

    def test_shortest_path_via_middle(self) -> None:
        """A* باید مسیر بهینه مشابه Dijkstra برگرداند."""
        g = _build_triangle_graph()
        path, cost = a_star(g, "A", "C")
        assert path == ["A", "B", "C"]
        assert cost == pytest.approx(2.0)

    def test_direct_shortest(self) -> None:
        g = _build_triangle_graph()
        path, cost = a_star(g, "A", "B")
        assert path == ["A", "B"]
        assert cost == pytest.approx(1.0)

    def test_same_start_end(self) -> None:
        g = _build_triangle_graph()
        path, cost = a_star(g, "A", "A")
        assert path == ["A"]
        assert cost == pytest.approx(0.0)

    def test_no_path(self) -> None:
        g = WindGraph(altitude=500.0)
        g.add_node(GraphNode("A", 36.0, 58.0))
        g.add_node(GraphNode("B", 37.0, 59.0))
        path, cost = a_star(g, "A", "B")
        assert path == []
        assert cost == math.inf

    def test_asymmetric(self) -> None:
        g = _build_asymmetric_graph()
        _, cost_ab = a_star(g, "A", "B")
        _, cost_ba = a_star(g, "B", "A")
        assert cost_ab < cost_ba
