"""تست‌های end-to-end مسیریابی — از فایل داده واقعی خراسان تا خروجی نهایی مسیر.

برخلاف تست‌های واحد در ``test_graph.py``/``test_routing.py`` که روی
DataFrame‌های ساخته‌شده دستی کار می‌کنند، این فایل زنجیره کامل را تست
می‌کند: خواندن فایل CSV واقعی از دیسک → ساخت گراف چندلایه → اجرای
``WindRouter`` → دریافت مسیر بهینه، لایه انتخابی، و تخمین زمان سفر.

چون داده ارتفاعی واقعی مستقیم در دسترس نیست (فقط داده سطحی ۳ ایستگاه در
``khorasan_wind_qc_cleaned.csv``؛ فایل نمونه چندلایه
``khorasan_pathfinding_ready.csv`` هنوز تماماً NaN است — نگاه کنید به
``docs/preprocessing_report.md``)، لایه‌های ارتفاعی بالاتر با یک تغییر
مقیاس ساده و مستند بر پایه داده واقعی ایستگاه‌ها ساخته می‌شوند؛ هیچ مقدار
placeholder/mock بی‌ربط به داده واقعی استفاده نشده است.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pathfinding.graph import MultiLayerWindGraph, WindGraph
from pathfinding.routing import RouteResult, WindRouter

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "khorasan_wind_qc_cleaned.csv"

# لایه‌های ارتفاعی مرجع پروژه (مطابق pathfinding_preparation.py و
# task_routing_benchmark.md).
ALTITUDES = (500.0, 1000.0, 1500.0, 2000.0)


def _load_real_surface_data() -> pd.DataFrame:
    """داده واقعی سطحی سه ایستگاه خراسان را از دیسک می‌خواند."""
    df = pd.read_csv(DATA_PATH)
    return df.groupby("station", as_index=False).agg(
        {"lat": "first", "lon": "first", "speed": "mean", "direction": "mean"}
    )


def _build_multi_layer_graph_from_real_data() -> MultiLayerWindGraph:
    """گراف چندلایه واقعی را از فایل CSV واقعی می‌سازد.

    هر لایه ارتفاعی بالاتر، سرعت باد واقعی ایستگاه‌ها را با یک ضریب مقیاس
    ساده (افزایش خطی سرعت با ارتفاع، مطابق پروفایل مرزی جوی) و چرخش جزئی
    جهت (اثر اکمن) اعمال می‌کند — همان روشی که
    ``scripts/generate_pathfinding_visualizations.py`` برای لایه‌های بالاتر
    استفاده کرده، چون داده اندازه‌گیری‌شده واقعی در ارتفاع در دسترس نیست.
    """
    surface = _load_real_surface_data()
    multi = MultiLayerWindGraph()
    for altitude in ALTITUDES:
        scale = 1.0 + (altitude - 500.0) / 3000.0
        rotation = (altitude - 500.0) / 100.0
        layer_df = surface.rename(columns={"speed": "wind_speed", "direction": "wind_direction"}).copy()
        layer_df["wind_speed"] = layer_df["wind_speed"] * scale
        layer_df["wind_direction"] = (layer_df["wind_direction"] + rotation) % 360.0
        graph = WindGraph.build_from_dataframe(layer_df, altitude=altitude, criterion="time")
        multi.add_layer(graph)
    return multi


MASHHAD = (36.297, 59.606)
NEYSHABUR = (36.213, 58.795)
SABZEVAR = (36.215, 57.678)


class TestEndToEndRealData:
    """زنجیره کامل: فایل CSV واقعی → گراف چندلایه → مسیر بهینه."""

    def test_e2e_build_graph_from_real_csv_has_all_layers(self) -> None:
        """۱. گراف چندلایه ساخته‌شده از فایل واقعی باید هر ۴ لایه ارتفاعی را داشته باشد."""
        multi = _build_multi_layer_graph_from_real_data()
        assert multi.available_layers == sorted(ALTITUDES)
        assert multi.layer_count == len(ALTITUDES)

    def test_e2e_full_route_mashhad_to_sabzevar(self) -> None:
        """۲. از فایل واقعی تا مسیر نهایی: مسیر بهینه مشهد→سبزوار باید تولید شود
        و شامل لایه انتخابی، مسافت واقعی، و تخمین زمان سفر باشد."""
        multi = _build_multi_layer_graph_from_real_data()
        router = WindRouter(multi)
        result = router.find_optimal_path(MASHHAD, SABZEVAR)

        assert isinstance(result, RouteResult)
        assert result.layer_altitude in ALTITUDES
        assert len(result.path) >= 2
        assert result.path[0] == pytest.approx(MASHHAD, abs=1e-6)
        assert result.path[-1] == pytest.approx(SABZEVAR, abs=1e-6)
        # فاصله واقعی مشهد-سبزوار حدود ۱۷۳ کیلومتر است (haversine).
        assert 170.0 < result.total_distance_km < 177.0
        assert result.estimated_time_hours > 0

    def test_e2e_layer_comparison_table_from_real_data(self) -> None:
        """۳. جدول مقایسه لایه‌ها روی مسیر واقعی نیشابور→سبزوار باید هر ۴ لایه
        را با زمان سفر معتبر پوشش دهد و دقیقاً یک لایه را بهترین علامت بزند."""
        multi = _build_multi_layer_graph_from_real_data()
        router = WindRouter(multi)
        comparison = router.compare_layers(NEYSHABUR, SABZEVAR)
        table = comparison.to_comparison_table()

        assert len(table) == len(ALTITUDES)
        assert set(table["layer_altitude_m"]) == set(ALTITUDES)
        assert (table["estimated_time_hours"] > 0).all()
        assert table["is_best"].sum() == 1
        assert comparison.best_altitude in ALTITUDES
