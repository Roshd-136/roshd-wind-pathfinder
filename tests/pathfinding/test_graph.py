"""تست‌های واحد برای ساخت گراف بادی (``pathfinding.graph``)."""

from __future__ import annotations

import pandas as pd
import pytest

from pathfinding.graph import (
    EdgeData,
    GraphNode,
    MultiLayerWindGraph,
    WindGraph,
)

# ---------------------------------------------------------------------------
# داده‌های آزمایشی
# ---------------------------------------------------------------------------

def _make_simple_df() -> pd.DataFrame:
    """DataFrame ساده با ۳ نقطه و باد از غرب (۲۷۰ درجه)."""
    return pd.DataFrame(
        {
            "lat": [36.0, 36.0, 36.1],
            "lon": [58.0, 58.2, 58.1],
            "wind_speed": [10.0, 10.0, 10.0],
            "wind_direction": [270.0, 270.0, 270.0],
        }
    )


def _make_multi_layer_df() -> pd.DataFrame:
    """DataFrame با ۲ لایه ارتفاعی."""
    rows = []
    for alt in [500.0, 1000.0]:
        for lat in [36.0, 36.1]:
            for lon in [58.0, 58.1]:
                rows.append(
                    {
                        "altitude": alt,
                        "lat": lat,
                        "lon": lon,
                        "wind_speed": 10.0 if alt == 500.0 else 15.0,
                        "wind_direction": 270.0,
                    }
                )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# تست‌های GraphNode
# ---------------------------------------------------------------------------

class TestGraphNode:
    """تست‌های گره گراف."""

    def test_create_node(self) -> None:
        node = GraphNode(
            node_id="36.0,58.0",
            lat=36.0,
            lon=58.0,
            wind_speed_mps=10.0,
            wind_direction_deg=270.0,
            altitude=500.0,
        )
        assert node.lat == 36.0
        assert node.wind_speed_mps == 10.0


# ---------------------------------------------------------------------------
# تست‌های WindGraph
# ---------------------------------------------------------------------------

class TestWindGraph:
    """تست‌های گراف تک‌لایه‌ای."""

    def test_empty_graph(self) -> None:
        g = WindGraph(altitude=500.0)
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_add_node(self) -> None:
        g = WindGraph(altitude=500.0)
        n = GraphNode(node_id="A", lat=36.0, lon=58.0)
        g.add_node(n)
        assert g.node_count == 1
        assert g.get_node("A") is n

    def test_add_edge(self) -> None:
        g = WindGraph(altitude=500.0)
        g.add_node(GraphNode("A", 36.0, 58.0))
        g.add_node(GraphNode("B", 36.1, 58.0))
        e = EdgeData(from_node="A", to_node="B", distance_km=11.1, weight=0.5)
        g.add_edge(e)
        assert g.edge_count == 1
        assert g.get_neighbors("A") == ["B"]
        assert g.get_edge("A", "B") is e

    def test_bidirectional_edges(self) -> None:
        g = WindGraph(altitude=500.0)
        g.add_node(GraphNode("A", 36.0, 58.0))
        g.add_node(GraphNode("B", 36.1, 58.0))
        g.add_edge(EdgeData("A", "B", 11.1, weight=0.5))
        g.add_edge(EdgeData("B", "A", 11.1, weight=0.7))
        assert g.edge_count == 2
        assert "A" in g.get_neighbors("B")
        assert "B" in g.get_neighbors("A")

    def test_find_nearest_node(self) -> None:
        g = WindGraph(altitude=500.0)
        g.add_node(GraphNode("A", 36.0, 58.0))
        g.add_node(GraphNode("B", 36.5, 58.5))
        nearest = g.find_nearest_node(36.01, 58.01)
        assert nearest == "A"

    def test_find_nearest_node_empty(self) -> None:
        g = WindGraph(altitude=500.0)
        assert g.find_nearest_node(36.0, 58.0) is None


# ---------------------------------------------------------------------------
# تست‌های build_from_dataframe
# ---------------------------------------------------------------------------

class TestBuildFromDataframe:
    """تست‌های ساخت گراف از DataFrame."""

    def test_build_basic(self) -> None:
        df = _make_simple_df()
        graph = WindGraph.build_from_dataframe(df, altitude=500.0)
        assert graph.node_count == 3
        assert graph.altitude == 500.0
        # ۳ نقطه نزدیک → ۶ یال (هر جفت ۲ جهت)
        assert graph.edge_count == 6

    def test_build_missing_columns_raises(self) -> None:
        df = pd.DataFrame({"lat": [1.0], "lon": [2.0]})
        with pytest.raises(ValueError, match="missing required wind columns"):
            WindGraph.build_from_dataframe(df, altitude=500.0)

    def test_build_filters_nan(self) -> None:
        df = pd.DataFrame(
            {
                "lat": [36.0, 36.1],
                "lon": [58.0, 58.1],
                "wind_speed": [10.0, float("nan")],
                "wind_direction": [270.0, 270.0],
            }
        )
        graph = WindGraph.build_from_dataframe(df, altitude=500.0)
        # فقط یک نقطه باقی می‌ماند
        assert graph.node_count == 1

    def test_build_with_timestamps_averages(self) -> None:
        df = pd.DataFrame(
            {
                "lat": [36.0, 36.0],
                "lon": [58.0, 58.0],
                "wind_speed": [8.0, 12.0],
                "wind_direction": [270.0, 270.0],
                "timestamp": ["2026-01-01", "2026-01-02"],
            }
        )
        graph = WindGraph.build_from_dataframe(df, altitude=500.0)
        assert graph.node_count == 1
        node = list(graph.nodes.values())[0]
        assert node.wind_speed_mps == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# تست‌های MultiLayerWindGraph
# ---------------------------------------------------------------------------

class TestMultiLayerWindGraph:
    """تست‌های گراف چندلایه."""

    def test_empty_multi(self) -> None:
        m = MultiLayerWindGraph()
        assert m.layer_count == 0
        assert m.available_layers == []

    def test_add_layer(self) -> None:
        m = MultiLayerWindGraph()
        g = WindGraph(altitude=500.0)
        m.add_layer(g)
        assert m.layer_count == 1
        assert m.available_layers == [500.0]

    def test_build_from_dataframe(self) -> None:
        df = _make_multi_layer_df()
        m = MultiLayerWindGraph.build_from_dataframe(df)
        assert m.layer_count == 2
        assert m.available_layers == [500.0, 1000.0]
        # هر لایه باید گراف با گره داشته باشد
        for alt in [500.0, 1000.0]:
            layer = m.get_layer(alt)
            assert layer is not None
            assert layer.node_count == 4  # 2x2 grid

    def test_build_skips_nan_layers(self) -> None:
        df = pd.DataFrame(
            {
                "altitude": [500.0, 1000.0],
                "lat": [36.0, 36.0],
                "lon": [58.0, 58.0],
                "wind_speed": [10.0, float("nan")],
                "wind_direction": [270.0, float("nan")],
            }
        )
        m = MultiLayerWindGraph.build_from_dataframe(df)
        assert m.layer_count == 1
        assert m.available_layers == [500.0]

    def test_build_without_altitude_creates_single_layer(self) -> None:
        """اگر ستون altitude وجود نداشته باشد، لایه تک‌لایه‌ای ساخته شود."""
        df = pd.DataFrame(
            {
                "lat": [36.0],
                "lon": [58.0],
                "wind_speed": [10.0],
                "wind_direction": [270.0],
            }
        )
        m = MultiLayerWindGraph.build_from_dataframe(df)
        assert m.layer_count == 1
        assert m.available_layers == [0.0]

    def test_layer_independence(self) -> None:
        """لایه‌های مختلف باید مستقل باشند (تغییر در یکی روی دیگری تأثیر ندارد)."""
        df = _make_multi_layer_df()
        m = MultiLayerWindGraph.build_from_dataframe(df)
        layer_500 = m.get_layer(500.0)
        layer_1000 = m.get_layer(1000.0)
        assert layer_500 is not None and layer_1000 is not None
        # باد لایه ۱۰۰۰ باید متفاوت باشد (۱۵ م/ث)
        n1000 = list(layer_1000.nodes.values())[0]
        assert n1000.wind_speed_mps == pytest.approx(15.0)
