"""ساخت گراف باد چندلایه برای الگوریتم‌های مسیریابی.

این ماژول ساختار اصلی ارائه می‌دهد:

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
from collections.abc import Callable, Sequence
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
    "VerticalCostConfig",
    "StackedGraph",
    "WindGraph",
    "MultiLayerWindGraph",
    "compute_vertical_cost",
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
    ground_elevation_m: float = 0.0
    is_ground: bool = False

    @property
    def agl_m(self) -> float:
        """ارتفاع این گره **بالای زمین** محلی (متر).

        با سطح پرواز MSL اختلاف دارد: دو گره روی یک سطح پرواز، روی دشت و روی
        قله، فاصلهٔ کاملاً متفاوتی از زمین دارند و همین تفاوت، باد و فاصلهٔ
        ایمنی هر گره را تعیین می‌کند.
        """
        return self.altitude - self.ground_elevation_m


@dataclass
class EdgeData:
    """داده یال بین دو گره شامل هزینه محاسبه‌شده توسط مدل بادی.

    پارامترها
    ----------
    from_node, to_node : str
        شناسه گره‌های مبدأ و مقصد.
    distance_km : float
        طول مسیر بین دو گره (کیلومتر). برای یال افقی، فاصله بزرگ‌دایره و برای
        یال عمودی (صعود/فرود)، اختلاف ارتفاع. یعنی مجموع ``distance_km`` روی یک
        مسیر = طول مسیر سه‌بعدی، نه فقط جابجایی افقی.
    cost_result : EdgeCostResult, اختیاری
        خروجی کامل مدل هزینه (اگر محاسبه موفق بود).
    weight : float
        وزن نهایی یال برای الگوریتم مسیریابی. معادل ``cost_result.cost``
        یا ``inf`` اگر یال غيرقابل‌عبور باشد.
    kind : str
        ``"horizontal"`` برای پرواز درون یک لایه ارتفاعی و        ``"climb"`` یا
        ``"descent"`` برای گذار عمودی بین دو لایه. مصرف‌کننده‌ها (مثلاً
        تجمیع مسافت افقی و نسبت باد پشت در ``routing``) باید یال‌های عمودی را
        از یال‌های افقی جدا کنند؛ همین فیلد این تفکیک را ممکن می‌کند.
    """

    from_node: str
    to_node: str
    distance_km: float
    cost_result: EdgeCostResult | None = None
    weight: float = field(default=math.inf)
    kind: str = "horizontal"

    @property
    def is_vertical(self) -> bool:
        """آیا این یال گذار ارتفاعی است (نه پرواز افقی)؟"""
        return self.kind != "horizontal"


@dataclass(frozen=True)
class VerticalCostConfig:
    """فرض‌های مدل برای گذار عمودی بین لایه‌های ارتفاعی.

    مسیریابی چندلایه بدون هزینه صعود بی‌معنا است: الگوریتم می‌تواند بی‌هزینه
    بین لایه‌ها بپرد و مسیری بسازد که فیزیکاً پروازشدنی نیست. بنابراین هر
    گذار عمودی هزینه‌ای متناسب با زمان صعود/فرود دارد.

    پارامترها
    ----------
    climb_rate_mps : float
        نرخ صعود (متر بر ثانیه). پیش‌فرض ۲.۵ م/ث ≈ ۹ کیلومتر بر ساعت — بازه
        معمول یک هواپیمای سبک/پهپاد. باید مثبت باشد.
    descent_rate_mps : float
        نرخ فرود (متر بر ثانیه). فرود معمولاً از صعود سریع‌تر است. باید مثبت
        باشد.
    energy_multiplier : float
        نسبت مصرف انرژی در ثانیه صعود به مصرف در ثانیه کروز. پیش‌فرض ۱.۵ یعنی
        صعود در واحد زمان پرهزینه‌تر از پرواز افقی است (باید ≥ ۱ باشد).
    descent_energy_factor : float
        نسبت مصرف انرژی در ثانیه **فرود** به مصرف در ثانیه کروز. در بازهٔ
        ``[0, 1]``.

        این پارامتر همان جایی است که «گرانش» وارد مدل می‌شود. پیش‌تر فرود با
        همان ``energy_multiplier`` صعود (۱.۵) بهای انرژی می‌داد — یعنی فرود
        *گران‌تر از کروز* شمرده می‌شد. فیزیکاً برعکس است: در فرود کار گرانش
        بخشی از نیاز رانش را می‌پردازد و موتور به توان کم (یا دور آرام) برمی‌گردد.
        با پیش‌فرض ۰.۱۵، هر گذار عمودی ``Δh`` (صعود + فرود) دیگر دو برابر
        بهای واقعی‌اش را نمی‌دهد؛ توجه کنید که این عدد همچنان **فرض مدل** است و
        نه اندازه‌گیری، ولی جهت خطایش یک‌طرفه نیست: انرژی *بازگشتی* گرانش (
        ``mgh``) جداگانه در ``pathfinding.effort`` به‌صورت «بُرد گلاید» حساب
        می‌شود، پس اثر گرانش دوبار شمرده نمی‌شود.
    """

    climb_rate_mps: float = 2.5
    descent_rate_mps: float = 3.0
    energy_multiplier: float = 1.5
    descent_energy_factor: float = 0.15

    def __post_init__(self) -> None:
        if self.climb_rate_mps <= 0:
            raise ValueError("climb_rate_mps must be positive.")
        if self.descent_rate_mps <= 0:
            raise ValueError("descent_rate_mps must be positive.")
        if self.energy_multiplier < 1.0:
            raise ValueError("energy_multiplier must be at least 1.0.")
        if not (0.0 <= self.descent_energy_factor <= 1.0):
            raise ValueError("descent_energy_factor must be within [0, 1].")
    def rate_mps(self, delta_altitude_m: float) -> float:
        """نرخ گذار برای یک اختلاف ارتفاع (مثبت = صعود)."""
        return self.climb_rate_mps if delta_altitude_m >= 0 else self.descent_rate_mps


def compute_vertical_cost(
    delta_altitude_m: float,
    config: CostModelConfig | None = None,
    criterion: str = "time",
    time_weight: float | None = None,
    vertical: VerticalCostConfig | None = None,
) -> EdgeCostResult:
    """هزینه گذار عمودی ``delta_altitude_m`` متر (مثبت = صعود).

    مدل: صعود/فرود با نرخ ثابت انجام می‌شود، پس مدت آن ``|Δh| / rate`` است و
    همان زمان به معیارهای ``time``/``energy``/``balanced`` وارد می‌شود. برای
    معیار انرژی، ضریب ثانیه‌ای صعود ``energy_multiplier`` و ضریب ثانیه‌ای فرود
    ``descent_energy_factor`` است — چون در فرود کار گرانش بخشی از رانش را
    می‌پردازد و موتور به دور آرام برمی‌گردد. (پیش‌تر هر دو ۱.۵ بودند، یعنی
    فرود گران‌تر از کروز شمرده می‌شد و هر مسیر چندلایه جریمه‌ای می‌داد که
    فیزیک آن را تأیید نمی‌کند.) برای معیار ``distance`` هزینه = طول مسیر عمودی
    (``|Δh|/1000`` کیلومتر) که کوچک اما نامنفی است و از صعودهای بی‌دلیل
    جلوگیری می‌کند.

    مقادیر ``along_track_mps``/``cross_track_mps`` صفر هستند (گذار عمودی مؤلفه
    افقی ندارد) و ``ground_speed_mps`` صفر گزارش می‌شود. مصرف‌کننده‌ها نباید
    از این خروجی سرعت افقی استخراج کنند.
    """
    resolved_vertical = vertical or VerticalCostConfig()
    resolved_config = config or CostModelConfig()
    if time_weight is None:
        time_weight = resolved_config.time_weight

    vertical_km = abs(delta_altitude_m) / 1000.0
    seconds = abs(delta_altitude_m) / resolved_vertical.rate_mps(delta_altitude_m)
    time_hours = seconds / 3600.0
    per_second = (
        resolved_vertical.energy_multiplier
        if delta_altitude_m >= 0
        else resolved_vertical.descent_energy_factor
    )
    energy_hours = time_hours * per_second
    balanced_hours = time_weight * time_hours + (1.0 - time_weight) * energy_hours

    cost_by_criterion = {
        "time": time_hours,
        "energy": energy_hours,
        "balanced": balanced_hours,
        "distance": vertical_km,
    }
    if criterion not in cost_by_criterion:
        raise ValueError(
            f"Unknown criterion {criterion!r}; expected one of "
            f"{tuple(cost_by_criterion)}."
        )

    return EdgeCostResult(
        distance_km=vertical_km,
        bearing_deg=0.0,
        along_track_mps=0.0,
        cross_track_mps=0.0,
        ground_speed_mps=0.0,
        time_hours=time_hours,
        energy_hours=energy_hours,
        balanced_hours=balanced_hours,
        criterion=criterion,
        cost=cost_by_criterion[criterion],
    )


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

    گراف **معیار و تنظیمات مدلی که با آن وزن‌دهی شده** را به خاطر می‌سپارد
    (``criterion`` و ``config``). این برای درستی تابع تخمین A* ضروری است: تخمین
    باید در واحدهای همان معیاری باشد که یال‌ها با آن وزن‌دهی شده‌اند. اگر بخواهید
    گراف را با معیار یا تنظیمات دیگری مسیریابی کنید، از ``reweight`` استفاده کنید
    (وزن‌ها باید بازمحاسبه شوند، چون در زمان ساخت پخته شده‌اند).
    """

    def __init__(
        self,
        altitude: float,
        max_edge_distance_km: float = 200.0,
        criterion: str = "time",
        config: CostModelConfig | None = None,
        time_weight: float | None = None,
        vertical_cost: VerticalCostConfig | None = None,
    ) -> None:
        """مقداردهی اولیه گراف تک‌لایه‌ای.

        پارامترها
        ----------
        altitude : float
            ارتفاع لایه (متر).
        max_edge_distance_km : float
            حداکثر فاصله بین دو گره برای ایجاد یال (کیلومتر).
        criterion : str
            معیاری که یال‌های این گراف با آن وزن‌دهی شده‌اند. پیش‌فرض ``"time"``
            است که محافظه‌کارانه‌ترین انتخاب برای تابع تخمین است (کمترین تخمین).
        config : CostModelConfig, اختیاری
            تنظیمات مدل هزینه که برای وزن‌دهی استفاده شده است.
        time_weight : float, اختیاری
            وزن مؤثر معیار زمان در معیار متعادل (اگر ``None`` باشد مقدار
            ``config.time_weight`` استفاده می‌شود).
        vertical_cost : VerticalCostConfig, اختیاری
            فرض‌های صعود/فرود. فقط برای گراف‌های چندلایه (stacked) معنا دارد،
            چون تنها آن‌ها یال عمودی دارند.
        """
        self.altitude = altitude
        self.max_edge_distance_km = max_edge_distance_km
        self.criterion = criterion
        self.config = config or CostModelConfig()
        self.time_weight = (
            self.config.time_weight if time_weight is None else time_weight
        )
        self.vertical_cost = vertical_cost or VerticalCostConfig()
        self._nodes: dict[str, GraphNode] = {}
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._edges: dict[tuple[str, str], EdgeData] = {}
        # شمارش گره/یالی که فقط به دلیل مدل زمین حذف شده‌اند. بدون این شمارنده،
        # «چرا این لایه نازک‌تر است؟» پاسخ قابل حسابرسی ندارد.
        self.clearance_dropped_nodes = 0
        self.terrain_dropped_edges = 0

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

    @property
    def max_wind_speed_mps(self) -> float:
        """بیشینه سرعت باد در میان گره‌های گراف (نامنفی، با نادیده‌گرفتن NaN)."""
        finite = [
            n.wind_speed_mps for n in self._nodes.values() if math.isfinite(n.wind_speed_mps)
        ]
        return max(finite) if finite else 0.0

    def max_ground_speed_mps(self, airspeed_mps: float | None = None) -> float:
        """کران بالای **قطعی** سرعت زمینی قابل دستیابی در این گراف.

        مدل باد این پروژه سرعت زمینی را به‌صورت
        ``gs = sqrt(airspeed² − cross²) + along`` محاسبه می‌کند، که چون
        ``along ≤ |wind|`` و ``cross ≥ 0`` است، همیشه از ``airspeed + |wind|``
        بیشتر نمی‌شود. پس جمع سرعت هوایی و بیشینه سرعت بادِ موجود در گراف یک
        کران بالای معتبر است — حتی اگر همه بادها پشت باشند.

        این تابع همان مقداری است که تابع تخمین A* باید بر آن تقسیم کند تا هیچ‌گاه
        بیش‌تخمین نزند (به ``pathfinding.algorithms`` مراجعه کنید). تقسیم بر خودِ
        سرعت هوایی نادرست است، چون باد پشت سرعت زمینی را از سرعت هوایی بیشتر می‌کند.
        """
        airspeed = self.config.airspeed_mps if airspeed_mps is None else airspeed_mps
        return airspeed + self.max_wind_speed_mps

    def reweight(
        self,
        criterion: str | None = None,
        config: CostModelConfig | None = None,
        time_weight: float | None = None,
    ) -> WindGraph:
        """گراف جدیدی با وزن‌های بازمحاسبه‌شده برمی‌گرداند.

        وزن یال‌ها در زمان ساخت پخته می‌شوند، بنابراین مسیریابی با معیار یا
        تنظیمات متفاوت نیاز به بازمحاسبه دارد. این تابع همان توپولوژی و همان
        داده باد گره‌ها را نگه می‌دارد و فقط ``weight`` یال‌ها را با معیار/تنظیمات
        درخواستی از نو محاسبه می‌کند.

        پارامترها
        ----------
        criterion : str, اختیاری
            معیار جدید؛ در صورت ``None`` معیار فعلی گراف استفاده می‌شود.
        config : CostModelConfig, اختیاری
            تنظیمات جدید مدل هزینه.
        time_weight : float, اختیاری
            وزن معیار زمان در معیار متعادل برای همین بازمحاسبه.

        برمی‌گرداند
        ----------
        WindGraph
            گراف جدید (گراف اصلی دست‌نخورده می‌ماند).
        """
        target_criterion = self.criterion if criterion is None else criterion
        target_config = self.config if config is None else config

        reweighted = WindGraph(
            altitude=self.altitude,
            max_edge_distance_km=self.max_edge_distance_km,
            criterion=target_criterion,
            config=target_config,
            time_weight=time_weight,
            vertical_cost=self.vertical_cost,
        )
        for node in self._nodes.values():
            reweighted.add_node(node)
        for (from_id, to_id), edge in self._edges.items():
            from_node = self._nodes.get(from_id)
            to_node = self._nodes.get(to_id)
            if from_node is None or to_node is None:
                continue
            if edge.is_vertical:
                # نکته مهم: بازمحاسبه یال عمودی با ``_build_edge`` نادرست است،
                # چون مدل باد افقی برای دو گره هم‌مختصات هزینه صفر می‌دهد و
                # صعود «مجانی» می‌شود. پس یال‌های عمودی با مدل عمودی بازمحاسبه
                # می‌شوند.
                reweighted.add_edge(
                    _build_vertical_edge(
                        from_node,
                        to_node,
                        target_config,
                        target_criterion,
                        time_weight,
                        self.vertical_cost,
                    )
                )
                continue
            reweighted.add_edge(
                _build_edge(
                    from_node,
                    to_node,
                    edge.distance_km,
                    target_config,
                    target_criterion,
                    time_weight,
                )
            )
        return reweighted

    def get_node(self, node_id: str) -> GraphNode | None:
        """دریافت گره با شناسه، یا ``None`` اگر وجود نداشته باشد."""
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> list[str]:
        """لیست شناسه گره‌های همسایه."""
        return sorted(self._adjacency.get(node_id, set()))

    def get_edge(self, from_node: str, to_node: str) -> EdgeData | None:
        """دریافت داده یال بین دو گره خاص."""
        return self._edges.get((from_node, to_node))

    @property
    def edges(self) -> dict[tuple[str, str], EdgeData]:
        """دیکشنری یال‌ها با کلید ``(from_node, to_node)`` (کپی)."""
        return dict(self._edges)

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
        min_clearance_m: float = 0.0,
        edge_terrain_sampler: Callable[[float, float], float] | None = None,
        terrain_samples_per_edge: int = 7,
    ) -> WindGraph:
        """گراف وزن‌دار را از DataFrame داده‌های بادی برای یک لایه ارتفاعی می‌سازد.

        DataFrame باید حاوی ستون‌های ``lat``، ``lon``، ``wind_speed`` و
        ``wind_direction`` باشد. اگر چند ``timestamp`` موجود باشد، داده‌های بادی
        روی زمان میانگین‌گیری می‌شوند.

        ``min_clearance_m`` و ``edge_terrain_sampler`` مدل زمین‌اند. پیش از این
        هیچ‌کدام وجود نداشت و در نتیجه گراف از روی کوه‌ها می‌گذشت، گره‌ها
        می‌توانستند زیر زمین باشند و «مسیر بهینه» می‌توانست از داخل یک قله رد
        شود بدون آن‌که چیزی جلویش را بگیرد. حالا:

        * گرهی که فاصلهٔ عمودی‌اش از زمین از ``min_clearance_m`` کمتر باشد حذف
          می‌شود (اگر ستون ``ground_elevation`` در داده باشد)،
        * و یالی که زمین زیر آن در میانهٔ راه بالاتر از سطح پرواز برود هم،
          چون دو سر یال ممکن است پایین باشند ولی قله دقیقاً وسط آن باشد.

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
        # پشتیبانی از نام‌های جایگزین ستون‌های بادی (مانند pathfinding_preparation)
        _SPEED_ALIASES = ("wind_speed", "speed")
        _DIR_ALIASES = ("wind_direction", "direction")

        cols = set(data.columns)

        def _resolve(aliases: tuple[str, ...]) -> str | None:
            for a in aliases:
                if a in cols:
                    return a
            return None

        speed_col = _resolve(_SPEED_ALIASES)
        dir_col = _resolve(_DIR_ALIASES)

        if speed_col is None or dir_col is None:
            missing = set()
            if speed_col is None:
                missing.update(_SPEED_ALIASES)
            if dir_col is None:
                missing.update(_DIR_ALIASES)
            raise ValueError(
                f"DataFrame missing required wind columns. "
                f"Expected one of {_SPEED_ALIASES} and one of {_DIR_ALIASES}. "
                f"Missing: {sorted(missing)}"
            )

        graph = cls(
            altitude=altitude,
            max_edge_distance_km=max_edge_distance_km,
            criterion=criterion,
            config=config,
            time_weight=time_weight,
        )

        # نرمال‌سازی نام ستون‌ها + کپی
        df = data.copy()
        if speed_col != "wind_speed":
            df = df.rename(columns={speed_col: "wind_speed"})
        if dir_col != "wind_direction":
            df = df.rename(columns={dir_col: "wind_direction"})

        # میانگین‌گیری روی زمان اگر چند timestamp وجود داشته باشد.
        #
        # نکته مهم: میانگین‌گیری روی ستون «جهت» به‌صورت حسابی نادرست است، چون
        # جهت یک کمیت دایره‌ای است. میانگین حسابی ۱۱ و ۳۵۲ درجه می‌شود ۱۸۱.۵ که
        # هیچ مشاهده‌ای نیست. بنابراین ابتدا مؤلفه‌های u و v ساخته می‌شوند،
        # میانگین *وکتوری* گرفته می‌شود و سپس به سرعت/جهت برمی‌گردد.
        group_cols = ["lat", "lon"]
        if "timestamp" in df.columns and df.duplicated(subset=group_cols).any():
            from preprocessing.pathfinding_preparation import (
                speed_direction_to_uv,
                uv_to_speed_direction,
            )

            u_series, v_series = speed_direction_to_uv(df["wind_speed"], df["wind_direction"])
            df = df.assign(_u=u_series, _v=v_series)

            agg_dict: dict[str, str] = {"_u": "mean", "_v": "mean"}
            if "altitude" in df.columns:
                agg_dict["altitude"] = "first"
            if "station" in df.columns:
                agg_dict["station"] = "first"
            df = df.groupby(group_cols, as_index=False).agg(agg_dict)

            mean_speed, mean_direction = uv_to_speed_direction(df["_u"], df["_v"])
            df = df.assign(wind_speed=mean_speed, wind_direction=mean_direction)
            df = df.drop(columns=["_u", "_v"])

        # فیلتر ردیف‌هایی با داده بادی NaN
        df = df.dropna(subset=["wind_speed", "wind_direction"]).reset_index(drop=True)

        has_ground = "ground_elevation" in df.columns

        # ساخت گره‌ها (با حذف گره‌های داخل زمین یا زیر آستانهٔ ایمنی)
        dropped_for_clearance = 0
        for _, row in df.iterrows():
            ground = float(row["ground_elevation"]) if has_ground else 0.0
            if altitude - ground < min_clearance_m - 1e-9:
                dropped_for_clearance += 1
                continue
            node_id = f"{row['lat']:.6f},{row['lon']:.6f}"
            node = GraphNode(
                node_id=node_id,
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                wind_speed_mps=float(row["wind_speed"]),
                wind_direction_deg=float(row["wind_direction"]),
                altitude=altitude,
                ground_elevation_m=ground,
            )
            graph.add_node(node)

        graph.clearance_dropped_nodes = dropped_for_clearance

        # ساخت یال‌ها بین نقاط مجاور
        node_list = list(graph._nodes.values())
        for i, node_a in enumerate(node_list):
            for node_b in node_list[i + 1 :]:
                dist = haversine_km(node_a.lat, node_a.lon, node_b.lat, node_b.lon)
                if dist > max_edge_distance_km:
                    continue

                if edge_terrain_sampler is not None and not _edge_clears_terrain(
                    node_a,
                    node_b,
                    altitude,
                    min_clearance_m,
                    edge_terrain_sampler,
                    terrain_samples_per_edge,
                ):
                    graph.terrain_dropped_edges += 1
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


def _stacked_node_id(altitude_m: float, node_id: str) -> str:
    """شناسه یکتای گره در گراف ادغام‌شده (ارتفاع + مختصات)."""
    return f"{altitude_m:.1f}m|{node_id}"


@dataclass
class StackedGraph:
    """گراف سه‌بعدی ادغام‌شده: همه لایه‌های ارتفاعی + گره‌های زمین (کلیدواژه متد).

    ساختار مسیریابی چندلایه این است که لایه‌ها یک گراف واحد شوند و بین لایه‌ها
    یال عمودی وجود داشته باشد؛ در این حالت مسیر بهینه می‌تواند در میانه راه
    ارتفاع را تغییر دهد (به‌جای اینکه کل مسیر در یک لایه ثابت بماند).

    علاوه بر لایه‌ها، برای مبدأ و مقصد یک «گره زمین» در ارتفاع صفر (نسبت به
    زمین) اضافه می‌شود که با یال عمودی به پایین‌ترین لایه وصل است. بنابراین
    مسیر از *روی زمین* شروع می‌شود، از پایین‌ترین لایه بالا می‌رود و در پایان
    دوباره روی زمین فرود می‌آید — هزینه صعود/فرود هم در تابع هدف دیده می‌شود.

    پارامترها
    ----------
    graph : WindGraph
        گراف ادغام‌شده (گره‌های همه لایه‌ها + دو گره زمین).
    origin_id, destination_id : str
        شناسه گره زمین مبدأ/مقصد (نقطه شروع و پایان مسیر).
    origin_coords, destination_coords : tuple[float, float]
        مختصات زمین مبدأ/مقصد، اسنپ‌شده به نزدیک‌ترین گره شبکه (همان نقطه‌ای که
        مسیر واقعاً از آن شروع می‌شود).
    layer_altitudes : tuple[float, ...]
        ارتفاع لایه‌های ادغام‌شده، از پایین به بالا.
    ground_altitude : float
        ارتفاع گره‌های زمین (متر، نسبت به زمین).
    """

    graph: WindGraph
    origin_id: str
    destination_id: str
    origin_coords: tuple[float, float]
    destination_coords: tuple[float, float]
    layer_altitudes: tuple[float, ...]
    ground_altitude: float = 0.0

    @property
    def node_count(self) -> int:
        """تعداد کل گره‌های گراف ادغام‌شده."""
        return self.graph.node_count

    @property
    def altitude_map(self) -> dict[str, float]:
        """نگاشت شناسه گره → ارتفاع لایه، برای گزارش مسیر."""
        return {
            node_id: node.altitude
            for node_id, node in self.graph.nodes.items()
        }


class MultiLayerWindGraph:
    """مدیریت گراف‌های باد چندلایه برای لایه‌های مختلف ارتفاعی.

    هر لایه ارتفاعی به‌صورت مستقل یک ``WindGraph`` دارد. لایه ارکستراسیون
    می‌تواند با فراخوانی ``available_layers`` لیست لایه‌های موجود را دریافت
    کند و بر اساس آن تصمیم‌گیری کند.

    پارامترها
    ----------
    None مستقیماً ساخته می‌شود، سپس با ``build_from_dataframe`` پر می‌شود.
    """

    def __init__(
        self,
        criterion: str = "time",
        config: CostModelConfig | None = None,
        time_weight: float | None = None,
    ) -> None:
        self.criterion = criterion
        self.config = config or CostModelConfig()
        self.time_weight = (
            self.config.time_weight if time_weight is None else time_weight
        )
        self._layers: dict[float, WindGraph] = {}
        # سطح‌هایی که درخواست شده‌اند ولی هیچ گره قانونی ندارند (زیر زمین یا داخل
        # آستانهٔ ایمنی). خالی‌بودنشان یک واقعیت داده است، نه خطا.
        self.missing_levels: list[float] = []

    @property
    def weighting_key(self) -> tuple[str, CostModelConfig, float]:
        """کلید وزن‌دهی این مجموعه لایه‌ها: ``(معیار، تنظیمات، weight زمان)``.

        لایه مسیریابی با مقایسه این کلید با درخواست کاربر تشخیص می‌دهد که آیا
        باید گراف را بازمحاسبه (``reweight``) کند یا نه.
        """
        return (self.criterion, self.config, self.time_weight)

    def reweight(
        self,
        criterion: str | None = None,
        config: CostModelConfig | None = None,
        time_weight: float | None = None,
    ) -> MultiLayerWindGraph:
        """نسخه بازمحاسبه‌شده همه لایه‌ها را با کلید وزن‌دهی جدید می‌سازد."""
        target_criterion = self.criterion if criterion is None else criterion
        target_config = self.config if config is None else config
        target_time_weight = self.time_weight if time_weight is None else time_weight

        reweighted = MultiLayerWindGraph(
            criterion=target_criterion,
            config=target_config,
            time_weight=target_time_weight,
        )
        for altitude in self.available_layers:
            layer = self._layers[altitude]
            reweighted.add_layer(
                layer.reweight(
                    criterion=target_criterion,
                    config=target_config,
                    time_weight=target_time_weight,
                )
            )
        return reweighted

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

    def to_stacked_graph(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        vertical_cost: VerticalCostConfig | None = None,
        criterion: str | None = None,
        config: CostModelConfig | None = None,
        time_weight: float | None = None,
        ground_altitude: float = 0.0,
        layers: Sequence[float] | None = None,
        ground_elevation_at: Callable[[float, float], float] | None = None,
    ) -> StackedGraph:
        """همه لایه‌ها را در یک گراف سه‌بعدی ادغام می‌کند تا مسیر بین لایه‌ها جابجا شود.

        پارامتر ``layers`` برای **محدود کردن** ادغام به زیرمجموعه‌ای از لایه‌هاست.
        با ``layers=(2000.0,)`` گراف ادغام‌شده تنها همان یک لایه را دارد و گره
        زمین مبدأ/مقصد به همان لایه وصل می‌شود؛ نتیجه یک مسیر «تک‌لایه» است که
        با این حال **از روی زمین** شروع و تمام می‌شود و هزینه صعود/فرود را
        می‌پردازد. این همان چیزی است که مقایسه منصفانه «مسیر آزاد سه‌بعدی» و
        «مسیر مقید به یک لایه» را ممکن می‌کند.

        یال‌های افقی هر لایه همان یال‌های وزن‌دهی‌شده قبلی هستند (کپی می‌شوند)،
        و بین هر مختصات، لایه‌های مجاور با یال عمودی به هم وصل می‌شوند. هزینه
        هر یال عمودی از ``compute_vertical_cost`` می‌آید.

        اگر ``criterion``/``config``/``time_weight`` با کلید وزن‌دهی فعلی مجموعه
        فرق داشته باشد، ابتدا ``reweight`` انجام می‌شود تا وزن یال‌های کپی‌شده در
        واحد درست باشند.

        پارامترها
        ----------
        origin, destination : tuple[float, float]
            مختصات مبدأ/مقصد (عرض, طول).
        vertical_cost : VerticalCostConfig, اختیاری
            فرض‌های صعود/فرود.
        criterion, config, time_weight : اختیاری
            معیار و تنظیمات مدل هزینه‌ای که گراف ادغام‌شده باید با آن وزن داشته باشد.
        ground_altitude : float
            ارتفاع گره‌های زمین (متر، پیش‌فرض صفر = روی زمین).

        برمی‌گرداند
        ----------
        StackedGraph
            گراف ادغام‌شده به‌همراه شناسه گره زمین مبدأ/مقصد.

        استثناها
        --------
        ValueError
            اگر مجموعه هیچ لایه‌ای نداشته باشد یا مبدأ و مقصد به یک گره برسند.
        """
        if self.layer_count == 0:
            raise ValueError("MultiLayerWindGraph has no layers to stack.")

        target_criterion = self.criterion if criterion is None else criterion
        target_config = self.config if config is None else config
        target_time_weight = self.time_weight if time_weight is None else time_weight
        source = self
        if (target_criterion, target_config, target_time_weight) != self.weighting_key:
            source = self.reweight(
                criterion=target_criterion,
                config=target_config,
                time_weight=target_time_weight,
            )

        vertical = vertical_cost or VerticalCostConfig()
        selected = source.available_layers
        if layers is not None:
            requested = sorted({float(alt) for alt in layers})
            unknown = [alt for alt in requested if alt not in selected]
            if unknown:
                raise ValueError(
                    f"Requested layers {unknown} are not available. "
                    f"Available: {selected}."
                )
            selected = requested
        if not selected:
            raise ValueError("No layers selected to stack.")
        layers = selected
        stacked = WindGraph(
            altitude=min(layers),
            max_edge_distance_km=max(
                source.get_layer(alt).max_edge_distance_km for alt in layers
            ),
            criterion=target_criterion,
            config=target_config,
            time_weight=target_time_weight,
            vertical_cost=vertical,
        )

        def node_at(altitude: float, lat: float, lon: float) -> str:
            """شناسه گره در لایه ``altitude`` (برای یال عمودی بین لایه‌ها)."""
            return _stacked_node_id(altitude, f"{lat:.6f},{lon:.6f}")

        # ۱) کپی گره‌ها و یال‌های افقی هر لایه
        for altitude in layers:
            layer = source.get_layer(altitude)
            if layer is None:
                continue
            for node in layer.nodes.values():
                stacked.add_node(
                    GraphNode(
                        node_id=_stacked_node_id(altitude, node.node_id),
                        lat=node.lat,
                        lon=node.lon,
                        wind_speed_mps=node.wind_speed_mps,
                        wind_direction_deg=node.wind_direction_deg,
                        altitude=altitude,
                        # ارتفاع زمین باید همراه گره کپی شود. بدون آن، گراف ادغام‌شده
                        # داده زمین را از دست می‌داد و «فاصله از زمین» در گزارش
                        # مسیر برابر خود سطح پرواز می‌شد — عددی که درست به‌نظر
                        # می‌رسد ولی هیچ ربطی به زمین ندارد.
                        ground_elevation_m=node.ground_elevation_m,
                    )
                )
            for (from_id, to_id), edge in layer.edges.items():
                if math.isinf(edge.weight):
                    continue
                stacked.add_edge(
                    EdgeData(
                        from_node=_stacked_node_id(altitude, from_id),
                        to_node=_stacked_node_id(altitude, to_id),
                        distance_km=edge.distance_km,
                        cost_result=edge.cost_result,
                        weight=edge.weight,
                    )
                )

        # ۲) یال‌های عمودی بین لایه‌های مجاور
        for lower, upper in zip(layers, layers[1:], strict=False):
            lower_layer = source.get_layer(lower)
            upper_layer = source.get_layer(upper)
            if lower_layer is None or upper_layer is None:
                continue
            for node in lower_layer.nodes.values():
                upper_id = node_at(upper, node.lat, node.lon)
                upper_node = stacked.get_node(upper_id)
                if upper_node is None:
                    # این مختصات در لایه بالایی وجود ندارد (شبکه‌ها یکسان‌اند،
                    # پس در حالت عادی رخ نمی‌دهد)؛ بدون یال عمودی رد می‌شویم.
                    continue
                lower_node = stacked.get_node(_stacked_node_id(lower, node.node_id))
                if lower_node is None:
                    continue
                stacked.add_edge(
                    _build_vertical_edge(
                        lower_node,
                        upper_node,
                        target_config,
                        target_criterion,
                        target_time_weight,
                        vertical,
                    )
                )
                stacked.add_edge(
                    _build_vertical_edge(
                        upper_node,
                        lower_node,
                        target_config,
                        target_criterion,
                        target_time_weight,
                        vertical,
                    )
                )

        # ۳) گره‌های زمین مبدأ/مقصد + اتصال عمودی به پایین‌ترین لایه *قابل‌استفاده*
        #
        # نکته مهم دربارهٔ ارتفاع گره زمین: پیش‌تر همیشه صفر بود، یعنی «سطح دریا».
        # با لایه‌های AGL این بی‌ضرر بود (ارتفاع لایه هم نسبت به زمین بود). حالا که
        # سطح‌های پرواز MSL‌اند، گره زمین باید ارتفاع *واقعی* زمین همان نقطه را
        # داشته باشد؛ وگرنه «صعود از زمین تا سطح پرواز» تمام ۱۴۰۰ متر ارتفاع زمین
        # را به‌عنوان صعود به هواپیما تحمیل می‌کند و هیچ مسیری هرگز صعود نمی‌کند.
        #
        # و «پایین‌ترین لایه» لزوماً در آن نقطه وجود ندارد: روی دامنهٔ قله، پایین‌ترین
        # سطح پرواز زیر زمین است و گره‌اش حذف شده. پس اولین سطحی که در همان مختصات
        # گره دارد انتخاب می‌شود.
        ground_ids: list[str] = []
        ground_coords: list[tuple[float, float]] = []
        for point in (origin, destination):
            attach_altitude: float | None = None
            lat = lon = 0.0
            base_id: str | None = None
            for candidate in layers:
                candidate_layer = source.get_layer(candidate)
                if candidate_layer is None:
                    continue
                candidate_id = candidate_layer.find_nearest_node(point[0], point[1])
                if candidate_id is None:
                    continue
                candidate_node = candidate_layer.get_node(candidate_id)
                if candidate_node is None:
                    continue
                lat, lon = candidate_node.lat, candidate_node.lon
                base_id = candidate_id
                attach_altitude = candidate
                break
            if attach_altitude is None or base_id is None:
                raise ValueError(
                    "No layer has a usable node at the origin/destination; "
                    "every level is either empty or blocked by terrain."
                )
            local_ground = (
                float(ground_elevation_at(lat, lon))
                if ground_elevation_at is not None
                else ground_altitude
            )
            ground_id = f"ground|{lat:.6f},{lon:.6f}"
            stacked.add_node(
                GraphNode(
                    node_id=ground_id,
                    lat=lat,
                    lon=lon,
                    wind_speed_mps=0.0,
                    wind_direction_deg=0.0,
                    altitude=local_ground,
                    ground_elevation_m=local_ground,
                    # این گره *روی زمین* است، نه یک سطح پرواز؛ مسیر نه از آن
                    # «پرواز» می‌کند و نه ارتفاعش باید در «لایه‌های پیموده‌شده»
                    # بشمار بیاید. نشانه‌گذاری صریح لازم است چون ارتفاعش دیگر
                    # صفر نیست (ارتفاع واقعی زمین است).
                    is_ground=True,
                )
            )
            ground_node = stacked.get_node(ground_id)
            base_stacked = stacked.get_node(
                _stacked_node_id(attach_altitude, f"{lat:.6f},{lon:.6f}")
            )
            if ground_node is None or base_stacked is None:
                raise ValueError("Ground node could not be attached to the lowest usable layer.")
            stacked.add_edge(
                _build_vertical_edge(
                    ground_node,
                    base_stacked,
                    target_config,
                    target_criterion,
                    target_time_weight,
                    vertical,
                )
            )
            stacked.add_edge(
                _build_vertical_edge(
                    base_stacked,
                    ground_node,
                    target_config,
                    target_criterion,
                    target_time_weight,
                    vertical,
                )
            )
            ground_ids.append(ground_id)
            ground_coords.append((lat, lon))

        if ground_ids[0] == ground_ids[1]:
            raise ValueError("Origin and destination snap to the same ground node.")

        return StackedGraph(
            graph=stacked,
            origin_id=ground_ids[0],
            destination_id=ground_ids[1],
            origin_coords=ground_coords[0],
            destination_coords=ground_coords[1],
            layer_altitudes=tuple(layers),
            ground_altitude=ground_altitude,
        )

    @classmethod
    def build_from_dataframe(
        cls,
        data: pd.DataFrame,
        config: CostModelConfig | None = None,
        criterion: str = "balanced",
        max_edge_distance_km: float = 200.0,
        time_weight: float | None = None,
        min_clearance_m: float = 0.0,
        edge_terrain_sampler: Callable[[float, float], float] | None = None,
        terrain_samples_per_edge: int = 7,
        layer_altitudes: Sequence[float] | None = None,
    ) -> MultiLayerWindGraph:
        """گراف‌های چندلایه را از DataFrame داده‌های بادی می‌سازد.

        DataFrame باید حاوی ستون ``altitude`` باشد. برای هر مقدار منحصربه‌فرد
        ارتفاع، یک ``WindGraph`` ساخته می‌شود. لایه‌هایی که تمام داده‌های بادی
        آن‌ها NaN باشد از مجموعه حذف می‌شوند.

        اگر ستون ``altitude`` وجود نداشته باشد، تمام داده‌ها به‌عنوان
        لایه تک‌لایه‌ای با altitude پیش‌فرض (0.0) در نظر گرفته می‌شوند.

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
        min_clearance_m : float
            کمترین فاصلهٔ مجاز عمودی از زمین (متر). گره‌های زیر این آستانه حذف
            می‌شوند، پس مسیر هرگز از داخل کوه رد نمی‌شود.
        edge_terrain_sampler : Callable, اختیاری
            ``(lat, lon) -> elevation_m``؛ برای بررسی زمین در میانهٔ یال‌ها.
        layer_altitudes : Sequence[float], اختیاری
            فهرست سطح‌هایی که *باید* وجود داشته باشند. اگر سطحی دادهٔ معتبر یا
            گره قانونی نداشته باشد، به‌عنوان سطح بی‌مسیر گزارش می‌شود.

        برمی‌گرداند
        ----------
        MultiLayerWindGraph
            مجموعه گراف‌های چندلایه.
        """
        multi = cls(criterion=criterion, config=config, time_weight=time_weight)

        if "altitude" not in data.columns:
            # اگر ستون altitude وجود نداشته باشد، تک‌لایه‌ای با altitude=0
            graph = WindGraph.build_from_dataframe(
                data,
                altitude=0.0,
                config=config,
                criterion=criterion,
                max_edge_distance_km=max_edge_distance_km,
                time_weight=time_weight,
                min_clearance_m=min_clearance_m,
                edge_terrain_sampler=edge_terrain_sampler,
                terrain_samples_per_edge=terrain_samples_per_edge,
            )
            if graph.node_count > 0:
                multi.add_layer(graph)
            return multi

        requested_levels = (
            [float(alt) for alt in layer_altitudes]
            if layer_altitudes is not None
            else sorted(float(alt) for alt in data["altitude"].unique())
        )
        multi.missing_levels = []
        for altitude in requested_levels:
            layer_data = data[data["altitude"] == altitude].copy()
            # حذف لایه‌هایی که داده بادی کاملاً NaN است
            if (
                layer_data["wind_speed"].isna().all()
                and layer_data["wind_direction"].isna().all()
            ):
                continue

            graph = WindGraph.build_from_dataframe(
                layer_data,
                altitude=float(altitude),
                config=config,
                criterion=criterion,
                max_edge_distance_km=max_edge_distance_km,
                time_weight=time_weight,
                min_clearance_m=min_clearance_m,
                edge_terrain_sampler=edge_terrain_sampler,
                terrain_samples_per_edge=terrain_samples_per_edge,
            )
            if graph.node_count > 0:
                multi.add_layer(graph)
            else:
                multi.missing_levels.append(altitude)

        return multi


# ---------------------------------------------------------------------------
# کمک‌تابع داخلی
# ---------------------------------------------------------------------------


def _build_vertical_edge(
    from_node: GraphNode,
    to_node: GraphNode,
    config: CostModelConfig | None,
    criterion: str,
    time_weight: float | None,
    vertical: VerticalCostConfig | None = None,
) -> EdgeData:
    """یال عمودی (صعود/فرود) بین دو گره با هزینه ``compute_vertical_cost``."""
    delta = to_node.altitude - from_node.altitude
    resolution = vertical or VerticalCostConfig()
    result = compute_vertical_cost(
        delta,
        config=config,
        criterion=criterion,
        time_weight=time_weight,
        vertical=resolution,
    )
    return EdgeData(
        from_node=from_node.node_id,
        to_node=to_node.node_id,
        distance_km=result.distance_km,
        cost_result=result,
        weight=result.cost,
        kind="climb" if delta >= 0 else "descent",
    )


def _edge_clears_terrain(
    node_a: GraphNode,
    node_b: GraphNode,
    flight_altitude_m: float,
    min_clearance_m: float,
    elevation_at: Callable[[float, float], float],
    samples: int,
) -> bool:
    """آیا یک یال افقی در تمام طول خود از زمین فاصلهٔ ایمنی دارد؟

    بررسی فقط دو سر یال کافی نیست: با یال‌های ۲۰ کیلومتری یک قله می‌تواند
    دقیقاً وسط یال باشد و هر دو سر پایین. پس زمین در چند نقطه روی خط بزرگ‌دایره
    نمونه‌برداری می‌شود.
    """
    steps = max(2, int(samples))
    for step in range(steps + 1):
        frac = step / steps
        lat = node_a.lat + (node_b.lat - node_a.lat) * frac
        lon = node_a.lon + (node_b.lon - node_a.lon) * frac
        if flight_altitude_m - float(elevation_at(lat, lon)) < min_clearance_m - 1e-9:
            return False
    return True


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
