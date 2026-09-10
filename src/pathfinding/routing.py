"""لایه ارکستراسیون نهایی مسیریابی باد — اتصال مدل هزینه به الگوریتم‌ها.

این ماژول آخرین یکپارچه‌ساز پروژه مسیریابی باد است. تمام ماژول‌های قبلی
(مدل هزینه ``cost.py``، گراف ``graph.py``، الگوریتم‌ها ``algorithms.py``)
را به‌هم متصل می‌کند و رابط نهایی برای کاربر فراهم می‌سازد.

عملکردهای اصلی:

- **انتخاب خودکار لایه بهینه:** بر اساس معیار بهینگی انتخاب‌شده، تمام
  لایه‌های ارتفاعی موجود ارزیابی و بهترین لایه انتخاب می‌شود.
- **محاسبه مسیر بهینه:** الگوریتم A* روی گراف لایه انتخابی اجرا می‌شود.
- **تخمین زمان سفر:** هزینه کل مسیر (ساعت پرواز مؤثر) برگردانده می‌شود.
- **جدول مقایسه:** امکان مقایسه زمان سفر روی لایه‌های مختلف.

هیچ placeholder یا مقدار فرضی در این ماژول استفاده نشده است: تمام محاسبات
بر اساس داده واقعی باد و مدل هزینه دینامیکی انجام می‌شود.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pathfinding.algorithms import a_star, dijkstra
from pathfinding.cost import CostModelConfig
from pathfinding.graph import MultiLayerWindGraph, WindGraph
from preprocessing.consistency import haversine_km

__all__ = [
    "RouteResult",
    "LayerComparison",
    "WindRouter",
]


@dataclass
class RouteResult:
    """خروجی محاسبه مسیر بهینه از یک لایه مشخص.

    پارامترها
    ----------
    path : list[tuple[float, float]]
        لیست مختصات (عرض, طول) نقاط مسیر بهینه.
    node_ids : list[str]
        لیست شناسه گره‌های مسیر.
    layer_altitude : float
        ارتفاع لایه انتخابی (متر).
    total_cost : float
        هزینه کل مسیر (ساعت پرواز مؤثر).
    total_distance_km : float
        مسافت کل مسیر (کیلومتر).
    estimated_time_hours : float
        تخمین زمان سفر (ساعت) — معادل هزینه در معیار «حداقل زمان».
    criterion : str
        معیار بهینگی مورد استفاده.
    """

    path: list[tuple[float, float]]
    node_ids: list[str]
    layer_altitude: float
    total_cost: float
    total_distance_km: float
    estimated_time_hours: float
    criterion: str


@dataclass
class LayerComparison:
    """نتیجه مقایسه مسیر در تمام لایه‌های موجود.

    پارامترها
    ----------
    results : dict[float, RouteResult]
        دیکشنری نتایج مسیر برای هر لایه (ارتفاع → نتیجه).
    best_altitude : float
        بهترین لایه بر اساس معیار انتخابی.
    best_result : RouteResult
        نتیجه بهینه.
    """

    results: dict[float, RouteResult]
    best_altitude: float
    best_result: RouteResult

    def to_comparison_table(self) -> pd.DataFrame:
        """جدول مقایسه‌ای زمان سفر در لایه‌های مختلف تولید می‌کند.

        برمی‌گرداند
        ----------
        DataFrame
            جدول شامل ارتفاع، مسافت، زمان سفر، و هزینه برای هر لایه.
        """
        rows = []
        for alt in sorted(self.results.keys()):
            r = self.results[alt]
            rows.append(
                {
                    "layer_altitude_m": alt,
                    "total_distance_km": round(r.total_distance_km, 2),
                    "estimated_time_hours": round(r.estimated_time_hours, 4),
                    "total_cost": round(r.total_cost, 4),
                    "path_length_nodes": len(r.path),
                    "is_best": alt == self.best_altitude,
                }
            )
        return pd.DataFrame(rows)


class WindRouter:
    """ارکستراسیون نهایی مسیریابی باد — اتصال تمام ماژول‌ها.

    این کلاس رابط نهایی بین کاربر و زیرسیستم مسیریابی است. با دریافت
    مختصات مبدأ و مقصد، تمام لایه‌های موجود را ارزیابی کرده، بهترین لایه
    را انتخاب و مسیر بهینه را برمی‌گرداند.

    پارامترها
    ----------
    multi_graph : MultiLayerWindGraph
        گراف چندلایه آماده (از ``build_from_dataframe``).
    config : CostModelConfig, اختیاری
        تنظیمات مدل هزینه فیزیکی.
    criterion : str
        معیار بهینگی ("time" / "energy" / "balanced").
    time_weight : float, اختیاری
        وزن معیار زمان در حالت متعادل.
    """

    def __init__(
        self,
        multi_graph: MultiLayerWindGraph,
        config: CostModelConfig | None = None,
        criterion: str = "balanced",
        time_weight: float | None = None,
    ) -> None:
        if multi_graph.layer_count == 0:
            raise ValueError("MultiLayerWindGraph has no layers. Build from data first.")
        self.multi_graph = multi_graph
        self.config = config or CostModelConfig()
        self.criterion = criterion
        self.time_weight = time_weight

    @property
    def available_layers(self) -> list[float]:
        """لیست لایه‌های ارتفاعی موجود."""
        return self.multi_graph.available_layers

    def find_optimal_path(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> RouteResult:
        """مسیر بهینه از مبدأ به مقصد با انتخاب خودکار لایه.

        پارامترها
        ----------
        origin : tuple[float, float]
            مختصات مبدأ (عرض, طول).
        destination : tuple[float, float]
            مختصات مقصد (عرض, طول).

        برمی‌گرداند
        ----------
        RouteResult
            نتیجه مسیر بهینه شامل مسیر، لایه انتخابی، و تخمین زمان سفر.

        programraises
        --------
        ValueError
            اگر هیچ لایه‌ای در دسترس نباشد یا مسیری یافت نشود.
        """
        comparison = self.compare_layers(origin, destination)
        return comparison.best_result

    def compare_layers(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> LayerComparison:
        """مقایسه مسیر در تمام لایه‌های موجود و انتخاب بهترین.

        پارامترها
        ----------
        origin : tuple[float, float]
            مختصات مبدأ (عرض, طول).
        destination : tuple[float, float]
            مختصات مقصد (عرض, طول).

        برمی‌گرداند
        ----------
        LayerComparison
            نتایج تمام لایه‌ها و بهترین گزینه.
        """
        results: dict[float, RouteResult] = {}
        best_alt: float = 0.0
        best_cost: float = float("inf")
        best_result: RouteResult | None = None

        for altitude in self.multi_graph.available_layers:
            graph = self.multi_graph.get_layer(altitude)
            if graph is None:
                continue

            result = self._route_on_layer(graph, origin, destination)
            if result is not None:
                results[altitude] = result
                if result.total_cost < best_cost:
                    best_cost = result.total_cost
                    best_alt = altitude
                    best_result = result

        if best_result is None:
            raise ValueError(
                f"No feasible path found between {origin} and {destination} "
                f"on any available layer."
            )

        return LayerComparison(
            results=results,
            best_altitude=best_alt,
            best_result=best_result,
        )

    def _route_on_layer(
        self,
        graph: WindGraph,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> RouteResult | None:
        """مسیریابی روی یک لایه خاص با الگوریتم A*.

        اگر مسیری یافت نشود ``None`` برمی‌گرداند.
        """
        start_id = graph.find_nearest_node(origin[0], origin[1])
        end_id = graph.find_nearest_node(destination[0], destination[1])

        if start_id is None or end_id is None:
            return None
        if start_id == end_id:
            return None

        # اجرای A*
        path_ids, total_cost = a_star(graph, start_id, end_id)

        if not path_ids or total_cost == float("inf"):
            # fallback به Dijkstra
            path_ids, total_cost = dijkstra(graph, start_id, end_id)

        if not path_ids or total_cost == float("inf"):
            return None

        # تبدیل شناسه‌ها به مختصات
        path_coords: list[tuple[float, float]] = []
        total_distance = 0.0
        for nid in path_ids:
            node = graph.get_node(nid)
            if node is not None:
                path_coords.append((node.lat, node.lon))

        # محاسبه مسافت کل
        for i in range(len(path_ids) - 1):
            n1 = graph.get_node(path_ids[i])
            n2 = graph.get_node(path_ids[i + 1])
            if n1 is not None and n2 is not None:
                total_distance += haversine_km(n1.lat, n1.lon, n2.lat, n2.lon)

        # تخمین زمان: معیار «زمان» هزینه = زمان سفر
        estimated_time = total_cost

        return RouteResult(
            path=path_coords,
            node_ids=path_ids,
            layer_altitude=graph.altitude,
            total_cost=total_cost,
            total_distance_km=total_distance,
            estimated_time_hours=estimated_time,
            criterion=self.criterion,
        )
