"""تست‌های واحد و end-to-end برای لایه ارکستراسیون (``pathfinding.routing``)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from pathfinding.cost import CostModelConfig
from pathfinding.graph import MultiLayerWindGraph
from pathfinding.routing import LayerComparison, RouteResult, WindRouter

# ---------------------------------------------------------------------------
# داده‌های آزمایشی
# ---------------------------------------------------------------------------

def _make_two_layer_df() -> pd.DataFrame:
    """DataFrame دو لایه‌ای با الگوی باد متفاوت.

    لایه ۵۰۰م: باد شدید از شمال (۰ درجه، ۱۵ م/ث) — باد رو-به-رو
    لایه ۱۰۰۰م: باد ضعیف از شمال (۰ درجه، ۵ م/ث)
    چهار نقطه به‌صورت مربع.

    مبدأ (36.0, 58.0) → مقصد (36.1, 58.2): حرکت تقریباً شمال‌شرقی
    باد از شمال = باد رو-به-رو → باد شدیدتر = هزینه بیشتر = لایه ۱۰۰۰ بهتر.
    """
    rows = []
    coords = [(36.0, 58.0), (36.0, 58.2), (36.1, 58.0), (36.1, 58.2)]
    for alt, speed in [(500.0, 15.0), (1000.0, 5.0)]:
        for lat, lon in coords:
            rows.append(
                {
                    "altitude": alt,
                    "lat": lat,
                    "lon": lon,
                    "wind_speed": speed,
                    "wind_direction": 0.0,
                }
            )
    return pd.DataFrame(rows)


def _make_single_layer_df() -> pd.DataFrame:
    """DataFrame تک‌لایه‌ای."""
    return pd.DataFrame(
        {
            "altitude": [500.0] * 4,
            "lat": [36.0, 36.0, 36.1, 36.1],
            "lon": [58.0, 58.2, 58.0, 58.2],
            "wind_speed": [10.0, 10.0, 10.0, 10.0],
            "wind_direction": [270.0, 270.0, 270.0, 270.0],
        }
    )


# ---------------------------------------------------------------------------
# تست‌های RouteResult
# ---------------------------------------------------------------------------

class TestRouteResult:
    """تست‌های ساختار خروجی مسیر."""

    def test_create_result(self) -> None:
        r = RouteResult(
            path=[(36.0, 58.0), (36.0, 58.2)],
            node_ids=["A", "B"],
            layer_altitude=500.0,
            total_cost=0.5,
            total_distance_km=18.5,
            estimated_time_hours=0.5,
            criterion="time",
        )
        assert r.layer_altitude == 500.0
        assert len(r.path) == 2


# ---------------------------------------------------------------------------
# تست‌های WindRouter
# ---------------------------------------------------------------------------

class TestWindRouter:
    """تست‌های ارکستراسیون مسیریابی."""

    def test_basic_path(self) -> None:
        """مسیر ساده بین دو نقطه در یک لایه."""
        df = _make_single_layer_df()
        mg = MultiLayerWindGraph.build_from_dataframe(df)
        router = WindRouter(mg, criterion="time")
        result = router.find_optimal_path((36.0, 58.0), (36.1, 58.2))
        assert isinstance(result, RouteResult)
        assert len(result.path) >= 2
        assert result.total_cost < math.inf
        assert result.layer_altitude == 500.0

    def test_single_layer_router(self) -> None:
        """do router with a single layer only."""
        df = _make_single_layer_df()
        mg = MultiLayerWindGraph.build_from_dataframe(df)
        router = WindRouter(mg, criterion="balanced")
        assert router.available_layers == [500.0]

    def test_compare_layers_returns_all(self) -> None:
        """compare_layers باید نتیجه هر لایه را برگرداند."""
        df = _make_two_layer_df()
        mg = MultiLayerWindGraph.build_from_dataframe(df)
        router = WindRouter(mg, criterion="time")
        comparison = router.compare_layers((36.0, 58.0), (36.1, 58.2))
        assert isinstance(comparison, LayerComparison)
        assert len(comparison.results) >= 1
        assert comparison.best_altitude in [500.0, 1000.0]

    def test_layer_selection_picks_best(self) -> None:
        """لایه با وزن باد کمتر باید بهتر انتخاب شود."""
        df = _make_two_layer_df()
        mg = MultiLayerWindGraph.build_from_dataframe(df)
        router = WindRouter(mg, criterion="time")
        comparison = router.compare_layers((36.0, 58.0), (36.1, 58.2))
        # باد ضعیف‌تر → سرعت زمینی بهتر → هزینه کمتر
        assert comparison.best_altitude == 1000.0

    def test_no_feasible_path_raises(self) -> None:
        """اگر هیچ مسیری وجود نداشته باشد، خطا برمی‌گرداند."""
        df = pd.DataFrame(
            {
                "altitude": [500.0, 500.0],
                "lat": [36.0, 37.0],
                "lon": [58.0, 59.0],
                "wind_speed": [10.0, 10.0],
                "wind_direction": [270.0, 270.0],
            }
        )
        mg = MultiLayerWindGraph.build_from_dataframe(
            df, max_edge_distance_km=10.0  # نقاط خیلی دور از هم
        )
        if mg.layer_count > 0:
            router = WindRouter(mg)
            with pytest.raises(ValueError, match="No feasible path"):
                router.find_optimal_path((36.0, 58.0), (37.0, 59.0))

    def test_empty_graph_raises(self) -> None:
        """do router with empty graph raises."""
        mg = MultiLayerWindGraph()
        with pytest.raises(ValueError, match="no layers"):
            WindRouter(mg)


# ---------------------------------------------------------------------------
# تست end-to-end: جدول مقایسه
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """تست‌های end-to-end کامل."""

    def test_full_pipeline(self) -> None:
        """کل خط لوله: DataFrame → چندلایه → مسیریابی → نتیجه."""
        df = _make_two_layer_df()
        mg = MultiLayerWindGraph.build_from_dataframe(df)
        router = WindRouter(
            mg,
            config=CostModelConfig(airspeed_mps=50.0),
            criterion="time",
        )

        # اطلاعات لایه‌ها
        assert router.available_layers == [500.0, 1000.0]

        # مسیر بهینه
        origin = (36.0, 58.0)
        dest = (36.1, 58.2)
        result = router.find_optimal_path(origin, dest)
        assert result.total_cost < math.inf
        assert result.total_distance_km > 0

        # جدول مقایسه
        comparison = router.compare_layers(origin, dest)
        table = comparison.to_comparison_table()
        assert len(table) >= 1
        assert "layer_altitude_m" in table.columns
        assert "estimated_time_hours" in table.columns
        assert "is_best" in table.columns
        # دقیقاً یک لایه بهتر است
        assert table["is_best"].sum() == 1

    def test_compare_layers_table_format(self) -> None:
        """جدول مقایسه باید فرمت صحیح داشته باشد."""
        df = _make_two_layer_df()
        mg = MultiLayerWindGraph.build_from_dataframe(df)
        router = WindRouter(mg, criterion="balanced")
        comparison = router.compare_layers((36.0, 58.0), (36.1, 58.2))
        table = comparison.to_comparison_table()
        assert set(table.columns) == {
            "layer_altitude_m",
            "total_distance_km",
            "estimated_time_hours",
            "total_cost",
            "path_length_nodes",
            "is_best",
        }

    def test_criterion_switch(self) -> None:
        """سوییچ بین معیارها باید نتایج متفاوت تولید کند (یا حداقل خطا ندهد)."""
        df = _make_two_layer_df()
        mg = MultiLayerWindGraph.build_from_dataframe(df)
        for crit in ["time", "energy", "balanced"]:
            router = WindRouter(mg, criterion=crit)
            result = router.find_optimal_path((36.0, 58.0), (36.1, 58.2))
            assert result.criterion == crit
            assert result.total_cost < math.inf
