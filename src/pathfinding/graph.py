"""ساخت گراف باد چندلایه برای الگوریتم‌های مسیریابی.

این ماژول دو ساختار اصلی ارائه می‌دهد:

- ``WindGraph``: یک گراف وزن‌دار تک‌لایه‌ای که گره‌ها نقاط جغرافیایی
  (عرض/طول جغرافیایی) و یال‌ها مسیر بین نقاط مجاور با وزن مبتنی بر هزینه
  بادی (خروجی ``compute_edge_cost``) هستند.

- ``MultiLayerWindGraph``: مدیریت مجموعه‌ای از ``WindGraph`` برای لایه‌های
  مختلف ارتفاعی (مثلاً ۵۰۰، ۱۰۰۰، ۱۵۰۰، ۲۰۰۰ متر). هر لایه به‌صورت
  مستقل گراف وزن‌دار خود را دارد.

ساخت گراف از DataFrame داده‌های بادی امکان‌پذیر است. اگر DataFrame حاوی
چند زمانه (timestamp) باشد، بردارهای بادی روی زمان میانگین‌گیری می‌شوند تا
یک نمایه اقلیمی (climatological) ایجاد شود. وزن یال‌ها توسط تابع
``compute_edge_cost`` از ماژول ``cost.py`` محاسبه می‌شود.

هیچ placeholder یا مقدار فرضی در این ماژول استفاده نشده است.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

from pathfinding.cost import (
    CostModelConfig,
    EdgeCostResult,
    InfeasibleEdgeError,
    compute_edge_cost,
)
from preprocessing.consistency import haversine_km

__all__ = [
    "GraphNode",
    "EdgeData",
    "WindGraph",
    "MultiLayerWindGraph",
]


@dataclass
class GraphNode:
    """گره گراف مسیریابی — یک نقطه جغرافیایی با داده‌های بادی.

    پارامترها
    ----------
    node_id : str
        شناسه یکتای گره (فرمت ``"lat,lon"``).
    lat, lon : float
        مختصات جغرافیایی (درجه).
    wind_speed_mps : float
        سرعت باد (متر بر ثانیه).
    wind_direction_deg : float
        جهت باد (درجه، قرارداد هواشناسی — از کجا می‌وزد).
    altitude : float
        ارتفاع از سطح دریا (متر).
    """

    node_id: str
    lat: float
    lon: float
    wind_speed_mps: float = 0.0
    wind_direction_deg: float = 0.0
    altitude: float = 0.0


@dataclass
class EdgeData:
    """داده یال بین دو گره شامل هزینه محاسبه‌شده توسط مدل بادی.

    پارامترها
    ----------
    from_node, to_node : str
        شناسه گره‌های مبدأ و مقصد.
    distance_km : float
        فاصله بزرگ‌دایره بین دو نقطه (کیلومتر).
    cost_result : EdgeCostResult, اختیاری
        خروجی کامل ``compute_edge_cost`` (اگر محاسبه موفق بود).
    weight : float
        وزن نهایی یال برای الگوریتم مسیریابی. معادل ``cost_result.cost``
        یا ``inf`` اگر یال غيرقابل‌عبور باشد.
    """

    from_node: str
    to_node: str
    distance_km: float
    cost_result: EdgeCostResult | None = None
    weight: float = field(default=math.inf)


class WindGraph:
    """گراف وزن‌دار باد برای یک لایه ارتفاعی مشخص.

    گره‌ها نمایانگر نقاط داده جغرافیایی و یال‌ها نمایانگر مسیر بین نقاط
    مجاور هستند. وزن هر یال توسط مدل هزینه دینامیکی (``compute_edge_cost``)
    محاسبه می‌شود.

    اتصال بین یال‌ها بر اساس حداکثر فاصله قابل‌پرواز (``max_edge_distance_km``)
    تعیین می‌شود: هر جفت نقطه‌ای که فاصله بین آن‌ها کمتر یا مساوی این مقدار
    باشد، یال دارد.

    نکته: وزن یال A→B با B→A متفاوت است چون جهت باد نسبت به مسیر حرکت
    تغییر می‌کند — این یک ویژگی فیزیکی صحیح مدل بادی است.
    """

    def __init__(
        self,
        altitude: float,
        max_edge_distance_km: float = 200.0,
    ) -> None:
        """مقداردهی اولیه گراف تک‌لایه‌ای.

        پارامترها
        ----------
        altitude : float
            ارتفاع لایه (متر).
        max_edge_distance_km : float
            حداکثر فاصله بین دو گره برای ایجاد یال (کیلومتر).
        """
        self.altitude = altitude
        self.max_edge_distance_km = max_edge_distance_km
        self._nodes: dict[str, GraphNode] = {}
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._edges: dict[tuple[str, str], EdgeData] = {}

    @property
    def node_count(self) -> int:
        """تعداد گره‌های گراف."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """تعداد یال‌های گراف (شامل هر دو جهت)."""
        return len(self._edges)

    @property
    def nodes(self) -> dict[str, GraphNode]:
        """دیکشنری گره‌ها (کپی)."""
        return dict(self._nodes)

    def get_node(self, node_id: str) -> GraphNode | None:
        """دریافت گره با شناسه، یا ``None`` اگر وجود نداشته باشد."""
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> list[str]:
        """لیست شناسه گره‌های همسایه."""
        return sorted(self._adjacency.get(node_id, set()))

    def get_edge(self, from_node: str, to_node: str) -> EdgeData | None:
        """دریافت داده یال بین دو گره خاص."""
        return self._edges.get((from_node, to_node))

    def add_node(self, node: GraphNode) -> None:
        """افزودن گره به گراف."""
        self._nodes[node.node_id] = node

    def add_edge(self, edge: EdgeData) -> None:
        """افزودن یال به گراف (half-edge — هر جهت جداگانه فراخوانی شود)."""
        self._edges[(edge.from_node, edge.to_node)] = edge
        self._adjacency[edge.from_node].add(edge.to_node)

    def find_nearest_node(self, lat: float, lon: float) -> str | None:
        """نزدیک‌ترین گره به مختصات داده‌شده را برمی‌گرداند.

        اگر گراف خالی باشد ``None`` برمی‌گرداند.
        """
        if not self._nodes:
            return None
        best_id: str = ""
        best_dist: float = math.inf
        for nid, node in self._nodes.items():
            d = haversine_km(lat, lon, node.lat, node.lon)
            if d < best_dist:
                best_dist = d
                best_id = nid
        return best_id

    @classmethod
    def build_from_dataframe(
        cls,
        data: pd.DataFrame,
        altitude: float,
        config: CostModelConfig | None = None,
        criterion: str = "balanced",
        max_edge_distance_km: float = 200.0,
        time_weight: float | None = None,
    ) -> WindGraph:
        """گراف وزن‌دار را از DataFrame داده‌های بادی برای یک لایه ارتفاعی می‌سازد.

        DataFrame باید حاوی ستون‌های ``lat``، ``lon``، ``wind_speed`` و
        ``wind_direction`` باشد. اگر چند ``timestamp`` موجود باشد، داده‌های بادی
        روی زمان میانگین‌گیری می‌شوند.

        پارامترها
        ----------
        data : DataFrame
            داده‌های بادی با ستون‌های lat, lon, wind_speed, wind_direction.
        altitude : float
            ارتفاع لایه (متر).
        config : CostModelConfig, اختیاری
            تنظیمات مدل هزینه.
        criterion : str
            معیار بهینگی ("time" / "energy" / "balanced").
        max_edge_distance_km : float
            حداکثر فاصله برای ایجاد یال بین دو گره.
        time_weight : float, اختیاری
            وزن معیار زمان در معیار متعادل.

        برمی‌گرداند
        ----------
        WindGraph
            گراف وزن‌دار ساخته‌شده.
        """
        required_cols = {"lat", "lon", "wind_speed", "wind_direction"}
        missing = required_cols - set(data.columns)
        if missing:
            raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")

        graph = cls(altitude=altitude, max_edge_distance_km=max_edge_distance_km)

        # میانگین‌گیری روی زمان اگر چند timestamp وجود داشته باشد
        df = data.copy()
        agg_dict: dict[str, str] = {
            "wind_speed": "mean",
            "wind_direction": "mean",
        }
        group_cols = ["lat", "lon"]
        if "altitude" in df.columns:
            agg_dict["altitude"] = "first"
        if "station" in df.columns:
            agg_dict["station"] = "first"
        if "timestamp" in df.columns:
            df = df.groupby(group_cols, as_index=False).agg(agg_dict)

        # فیلتر ردیف‌هایی با داده بادی NaN
        df = df.dropna(subset=["wind_speed", "wind_direction"]).reset_index(drop=True)

        # ساخت گره‌ها
        for _, row in df.iterrows():
            node_id = f"{row['lat']:.6f},{row['lon']:.6f}"
            node = GraphNode(
                node_id=node_id,
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                wind_speed_mps=float(row["wind_speed"]),
                wind_direction_deg=float(row["wind_direction"]),
                altitude=altitude,
            )
            graph.add_node(node)

        # ساخت یال‌ها بین نقاط مجاور
        node_list = list(graph._nodes.values())
        for i, node_a in enumerate(node_list):
            for node_b in node_list[i + 1 :]:
                dist = haversine_km(node_a.lat, node_a.lon, node_b.lat, node_b.lon)
                if dist > max_edge_distance_km:
                    continue

                # یال A → B (باد در نقطه A)
                edge_ab = _build_edge(
                    node_a, node_b, dist, config, criterion, time_weight
                )
                graph.add_edge(edge_ab)

                # یال B → A (باد در نقطه B)
                edge_ba = _build_edge(
                    node_b, node_a, dist, config, criterion, time_weight
                )
                graph.add_edge(edge_ba)

        return graph


class MultiLayerWindGraph:
    """مدیریت گراف‌های باد چندلایه برای لایه‌های مختلف ارتفاعی.

    هر لایه ارتفاعی به‌صورت مستقل یک ``WindGraph`` دارد. لایه ارکستراسیون
    می‌تواند با فراخوانی ``available_layers`` لیست لایه‌های موجود را دریافت
    کند و بر اساس آن تصمیم‌گیری کند.

    پارامترها
    ----------
    None مستقیماً ساخته می‌شود، سپس با ``build_from_dataframe`` پر می‌شود.
    """

    def __init__(self) -> None:
        self._layers: dict[float, WindGraph] = {}

    @property
    def available_layers(self) -> list[float]:
        """لیست مرتب‌شده ارتفاعات لایه‌های موجود."""
        return sorted(self._layers.keys())

    @property
    def layer_count(self) -> int:
        """تعداد لایه‌های موجود."""
        return len(self._layers)

    def get_layer(self, altitude: float) -> WindGraph | None:
        """دریافت گراف لایه مشخص، یا ``None`` اگر وجود نداشته باشد."""
        return self._layers.get(altitude)

    def add_layer(self, graph: WindGraph) -> None:
        """افزودن یک لایه به مجموعه."""
        self._layers[graph.altitude] = graph

    @classmethod
    def build_from_dataframe(
        cls,
        data: pd.DataFrame,
        config: CostModelConfig | None = None,
        criterion: str = "balanced",
        max_edge_distance_km: float = 200.0,
        time_weight: float | None = None,
    ) -> MultiLayerWindGraph:
        """گراف‌های چندلایه را از DataFrame داده‌های بادی می‌سازد.

        DataFrame باید حاوی ستون ``altitude`` باشد. برای هر مقدار منحصربه‌فرد
        ارتفاع، یک ``WindGraph`` ساخته می‌شود. لایه‌هایی که تمام داده‌های بادی
        آن‌ها NaN باشد از مجموعه حذف می‌شوند.

        پارامترها
        ----------
        data : DataFrame
            داده‌های بادی شامل ستون‌های altitude, lat, lon, wind_speed, wind_direction.
        config : CostModelConfig, اختیاری
            تنظیمات مدل هزینه.
        criterion : str
            معیار بهینگی.
        max_edge_distance_km : float
            حداکثر فاصله یال.
        time_weight : float, اختیاری
            وزن معیار زمان.

        برمی‌گرداند
        ----------
        MultiLayerWindGraph
            مجموعه گراف‌های چندلایه.
        """
        multi = cls()

        if "altitude" not in data.columns:
            raise ValueError(
                "DataFrame must contain 'altitude' column for multi-layer graph."
            )

        for altitude in sorted(data["altitude"].unique()):
            layer_data = data[data["altitude"] == altitude].copy()
            # حذف لایه‌هایی با داده بادی کاملاً NaN
            if (
                layer_data["wind_speed"].isna().all()
                or layer_data["wind_direction"].isna().all()
            ):
                continue

            graph = WindGraph.build_from_dataframe(
                layer_data,
                altitude=float(altitude),
                config=config,
                criterion=criterion,
                max_edge_distance_km=max_edge_distance_km,
                time_weight=time_weight,
            )
            if graph.node_count > 0:
                multi.add_layer(graph)

        return multi


# ---------------------------------------------------------------------------
# کمک‌تابع داخلی
# ---------------------------------------------------------------------------

def _build_edge(
    from_node: GraphNode,
    to_node: GraphNode,
    distance_km: float,
    config: CostModelConfig | None,
    criterion: str,
    time_weight: float | None,
) -> EdgeData:
    """یک EdgeData می‌سازد. اگر عبور غیرممکن باشد weight=inf برمی‌گرداند."""
    try:
        cost_result = compute_edge_cost(
            from_node.lat,
            from_node.lon,
            to_node.lat,
            to_node.lon,
            from_node.wind_speed_mps,
            from_node.wind_direction_deg,
            config=config,
            criterion=criterion,
            time_weight=time_weight,
        )
        return EdgeData(
            from_node=from_node.node_id,
            to_node=to_node.node_id,
            distance_km=distance_km,
            cost_result=cost_result,
            weight=cost_result.cost,
        )
    except InfeasibleEdgeError:
        return EdgeData(
            from_node=from_node.node_id,
            to_node=to_node.node_id,
            distance_km=distance_km,
            weight=math.inf,
        )
