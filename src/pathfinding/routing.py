"""لایه ارکستراسیون نهایی مسیریابی باد — اتصال مدل هزینه به الگوریتم‌ها.

این ماژول آخرین یکپارچه‌ساز پروژه مسیریابی باد است و ماژول‌های مدل هزینه
(``cost.py``)، گراف (``graph.py``) و الگوریتم‌ها (``algorithms.py``) را به هم
وصل می‌کند.

عملکردهای اصلی:

- **انتخاب خودکار لایه بهینه:** تمام لایه‌های ارتفاعی موجود ارزیابی و بهترین
  لایه بر اساس معیار بهینگی انتخاب می‌شود.

- **احترام به معیار و تنظیمات کاربر:** معیار بهینگی در زمان *ساخت* گراف روی وزن
  یال‌ها پخته می‌شود. اگر معیار/تنظیمات درخواستی کاربر با آنچه گراف با آن ساخته
  شده متفاوت باشد، این لایه گراف را با ``WindGraph.reweight`` **بازمحاسبه**
  می‌کند. پیش‌تر پارامترهای ``criterion``/``time_weight``/``config`` فقط ذخیره
  می‌شدند و هیچ اثری روی مسیر یافت‌شده نداشتند.

- **تفکیک زمان سفر واقعی از مقدار هزینه:** ``total_cost`` مقدار تابع هدف است
  (ساعت برای معیارهای ``time``/``energy``/``balanced`` و کیلومتر برای
  ``distance``)، در حالی که ``estimated_time_hours`` زمان واقعی پرواز است. پیش‌تر
  این دو یکی گرفته می‌شدند و تحت معیار انرژی/متعادل/مسافت عددی برمی‌گرداندند که
  زمان نبود.

- **مسیریابی تک‌لایه:** ``route_on_single_layer`` مسیر را فقط روی یک لایه ارتفاعی
  مشخص حساب می‌کند (بدون انتخاب خودکار لایه).

- **جدول مقایسه:** مقایسه زمان/مسافت/انرژی روی لایه‌های مختلف.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import pandas as pd

from pathfinding.algorithms import a_star, dijkstra, smooth_dijkstra
from pathfinding.cost import CRITERIA, CostModelConfig, initial_bearing_deg
from pathfinding.effort import (
    LegSample,
    MotorEffortConfig,
    RouteEffort,
    compute_route_effort,
    sample_horizontal_leg,
)
from pathfinding.geometry import (
    RELAX_MAX_DEVIATION_KM,
    relax_path_curvature,
    round_path_corners,
)
from pathfinding.graph import (
    MultiLayerWindGraph,
    StackedGraph,
    VerticalCostConfig,
    WindGraph,
)
from pathfinding.profile import ramp_vertical_transitions
from preprocessing.consistency import haversine_km

__all__ = [
    "RouteResult",
    "LayerComparison",
    "WindRouter",
    "SUPPORTED_ALGORITHMS",
    "DEFAULT_DIRECTION_PENALTY_THRESHOLD_DEG",
]

# الگوریتم‌های قابل انتخاب برای مسیریابی هر لایه.
SUPPORTED_ALGORITHMS: tuple[str, ...] = ("astar", "dijkstra", "smooth")

# آستانه پیش‌فرض تغییر جهت (درجه) برای شمارش «تغییر مسیر» در گزارش مسیر.
DEFAULT_DIRECTION_PENALTY_THRESHOLD_DEG = 30.0


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
        ارتفاع *کروز* مسیر (متر). برای مسیر تک‌لایه همان ارتفاع لایه است. برای
        مسیر چندلایه (که می‌تواند در میانه راه ارتفاع را تغییر دهد)، ارتفاعی
        است که بیشترین زمان پرواز در آن سپری شده است.
    total_cost : float
        مقدار تابع هدف. واحد آن به معیار بستگی دارد: ساعت برای
        ``time``/``energy``/``balanced`` و کیلومتر برای ``distance``. برای
        الگوریتم ``smooth`` جریمه تغییر جهت هم در این مقدار لحاظ شده است.
    total_distance_km : float
        مسافت *افقی* کل مسیر (کیلومتر). گذارهای عمودی (صعود/فرود) در این عدد
        حساب نمی‌شوند تا مسافت مسیرهای چندلایه با تک‌لایه قابل مقایسه بماند؛
        ارتفاع‌های پیموده‌شده جداگانه در ``total_climb_m``/``total_descent_m``
        گزارش می‌شوند. این عدد مستقل از معیار، همیشه مسافت هندسی واقعی است.
    estimated_time_hours : float
        زمان واقعی پرواز (ساعت). این مقدار از مجموع ``time_hours`` یال‌های مسیر
        به‌دست می‌آید و **مستقل از معیار بهینگی** است؛ بنابراین بر خلاف
        ``total_cost`` همیشه بر حسب ساعت است.
    criterion : str
        معیار بهینگی مورد استفاده.
    total_energy_index : float
        شاخص *نسبی* انرژی (مجموع ``energy_hours`` یال‌ها، بر حسب ساعتِ معادل با
        جریمه درگ القایی). این عدد انرژی فیزیکی (ژول/کیلووات‌ساعت) نیست و
        تنها برای مقایسه نسبی مسیرها معنا دارد.
    tailwind_leg_fraction : float
        نسبت قطعات مسیر که مؤلفه هم‌راستای باد در آن‌ها مثبت است (باد پشت).
        معیار سنجش «حرکت هم‌راستا با باد».
    heading_changes : int
        تعداد تغییر جهت‌های بیش از ``direction_penalty_threshold_deg`` درجه.
    algorithm : str
        الگوریتم استفاده‌شده برای این مسیر.
    node_altitudes : list[float]
        ارتفاع (متر) هر گره مسیر، هم‌ترتیب با ``node_ids``. برای مسیرهای
        چندلایه این لیست تغییر ارتفاع را نشان می‌دهد؛ گره‌های زمین (مبدأ/مقصد)
        ارتفاع صفر دارند.
    total_climb_m, total_descent_m : float
        مجموع ارتفاع صعود/فرود مسیر (متر).
    climb_legs : int
        تعداد گذارهای عمودی (تعداد قطعاتی که اختلاف ارتفاع دارند).
    effort : RouteEffort, اختیاری
        برآورد تلاش موتوری و سوخت مسیر: چند بار سمت هوایی برای حفظ مسیر عوض
        شده، توان اضافهٔ هر دور، و تفکیک سوخت کروز/دور/صعود. این مدل پارامتری
        است (به ``pathfinding.effort`` نگاه کنید) و باید در گزارش «مدل، نه
        اندازه‌گیری» برچسب بخورد.
    layers_used : tuple[float, ...], اختیاری
        لایه‌های ارتفاعی *کروز* مسیر، وقتی از ``node_altitudes`` قابل استنتاج
        نیست. مسیرهای گرافی در هر گره دقیقاً روی یک لایه می‌نشینند، پس برای
        آن‌ها لازم نیست. مسیر بادسواری (``pathfinding.wind_riding``) در فاز
        فرود **پیوسته** کم می‌کند، پس ``node_altitudes`` ده‌ها ارتفاع میانی
        دارد و اگر مبنای ``altitudes_used`` باشد، «لایه‌های پیموده‌شده» به
        اشتباه چند ده لایه گزارش می‌شود. در آن حالت این فیلد صریح داده می‌شود.
    """

    path: list[tuple[float, float]]
    node_ids: list[str]
    layer_altitude: float
    total_cost: float
    total_distance_km: float
    estimated_time_hours: float
    criterion: str
    total_energy_index: float = 0.0
    tailwind_leg_fraction: float = 0.0
    heading_changes: int = 0
    algorithm: str = "astar"
    node_altitudes: list[float] = field(default_factory=list)
    total_climb_m: float = 0.0
    total_descent_m: float = 0.0
    climb_legs: int = 0
    effort: RouteEffort | None = None
    layers_used: tuple[float, ...] | None = None
    min_clearance_m: float | None = None
    leg_samples: list[LegSample] = field(default_factory=list)

    @property
    def altitudes_used(self) -> list[float]:
        """ارتفاع لایه‌های واقعی که مسیر از آن‌ها عبور کرده است (بدون گره زمین).

        برای مسیر تک‌لایه: یک عضو. برای مسیر چندلایه: چند عضو. همین ویژگی
        تفاوت «پرواز در یک لایه» و «جابجایی بین لایه‌ها» را قابل‌آزمون می‌کند.
        اگر ``layers_used`` صریح داده شده باشد (مسیرهایی که پروفیل ارتفاع‌شان
        پیوسته است، مثل بادسواری)، همان برگردانده می‌شود.
        """
        if self.layers_used is not None:
            return sorted({round(alt, 6) for alt in self.layers_used})
        airborne = sorted(
            {
                round(alt, 6)
                for alt in (self.node_altitudes or [self.layer_altitude])
                if alt > 0.0
            }
        )
        return airborne if airborne else [round(self.layer_altitude, 6)]

    @property
    def is_multilayer(self) -> bool:
        """آیا مسیر بین بیش از یک لایه ارتفاعی جابجا شده است؟"""
        return len(self.altitudes_used) > 1

    def summary_row(self) -> dict[str, float | str | int]:
        """یک ردیف خلاصه برای گزارش/جدول مقایسه مسیرها."""
        row: dict[str, float | str | int] = {
            "criterion": self.criterion,
            "algorithm": self.algorithm,
            "layer_altitude_m": self.layer_altitude,
            "altitudes_used_m": "، ".join(f"{alt:.0f}" for alt in self.altitudes_used),
            "total_distance_km": round(self.total_distance_km, 4),
            "estimated_time_hours": round(self.estimated_time_hours, 6),
            "total_energy_index": round(self.total_energy_index, 6),
            "total_cost": round(self.total_cost, 6),
            "tailwind_leg_fraction": round(self.tailwind_leg_fraction, 4),
            "heading_changes": self.heading_changes,
            "total_climb_m": round(self.total_climb_m, 2),
            "total_descent_m": round(self.total_descent_m, 2),
            "climb_legs": self.climb_legs,
            "path_length_nodes": len(self.path),
        }
        if self.min_clearance_m is not None:
            row["min_clearance_m"] = round(self.min_clearance_m, 1)
        if self.effort is not None:
            row.update(
                {
                    "powered_course_changes": self.effort.powered_course_changes,
                    "course_change_deg_total": round(self.effort.course_change_deg_total, 3),
                    "turn_time_s": round(self.effort.turn_time_s, 3),
                    "turn_extra_power_w": round(self.effort.turn_extra_power_w, 3),
                    "total_fuel_kg": round(self.effort.total_fuel_kg, 6),
                    "fuel_per_100km_kg": round(self.effort.fuel_per_100km_kg, 6),
                }
            )
        return row


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
        """جدول مقایسه‌ای مسیرها در لایه‌های مختلف تولید می‌کند.

        برمی‌گرداند
        ----------
        DataFrame
            جدول شامل ارتفاع، مسافت، زمان سفر، شاخص انرژی، تعداد تغییر جهت و
            هزینه برای هر لایه.
        """
        rows = []
        for alt in sorted(self.results.keys()):
            r = self.results[alt]
            rows.append(
                {
                    "layer_altitude_m": alt,
                    "total_distance_km": round(r.total_distance_km, 2),
                    "estimated_time_hours": round(r.estimated_time_hours, 4),
                    "total_energy_index": round(r.total_energy_index, 4),
                    "tailwind_leg_fraction": round(r.tailwind_leg_fraction, 3),
                    "heading_changes": r.heading_changes,
                    "total_cost": round(r.total_cost, 4),
                    "path_length_nodes": len(r.path),
                    "is_best": alt == self.best_altitude,
                }
            )
        return pd.DataFrame(rows)


def _mean_ground_speed(
    samples: Sequence[tuple[float, float]],
    fallback_mps: float,
) -> float:
    """میانگین *وزنی‌به‌مسافت* سرعت زمینی مسیر (متر بر ثانیه).

    گذر عمودی یک سرعت زمینی خودش را ندارد (یال عمودی مسافت افقی ندارد)، پس
    مسافت افقی رمپ باید از سرعت خود مسیر بیاید. میانگین ساده، یالهای کوتاه
    داخل پیچ‌ها را هم‌وزن یالهای بلند کروز می‌کرد؛ وزن‌دادن به مسافت همان چیزی
    است که «هواپیما با چه سرعتی این مسیر را می‌پیماید» را جواب می‌دهد.

    بدون هیچ نمونه‌ای (گراف دستی بدون نتیجهٔ هزینه) سرعت هوایی برمی‌گردد:
    نبود داده دلیل نمی‌شود رمپ ساخته نشود.
    """
    total_km = sum(distance_km for distance_km, _speed in samples)
    if total_km <= 0.0:
        return max(fallback_mps, 1e-6)
    weighted = sum(distance_km * speed for distance_km, speed in samples)
    return max(weighted / total_km, 1e-6)


# یک درجهٔ عرض جغرافیایی (کیلومتر) — همان مقداری که لایهٔ هندسه با آن در صفحهٔ
# محلی کار می‌کند، تا سنجش شیب و ساخت کمان دو چارچوب جدا نداشته باشند.
_KM_PER_DEG_LAT = 111.32

# حاشیهٔ مجاز روی سقف نرخ عمودی هنگام سنجش «پروازپذیری» پروفیل. همان ۲۵٪
# حاشیه‌ای است که تست صحنه هم اعمال می‌کند: پروفیل نسبت به زمین لنگر می‌اندازد،
# پس شیبش با زمین زیرش تغییر می‌کند، و نقاط پیش از گزارش تُنُک می‌شوند.
_VERTICAL_RATE_MARGIN = 1.25

# چند تلاش برای پخش انحنا با بودجهٔ کاهش‌یابنده (۲.۵ → ۱.۲۵ → ... کیلومتر).
_RELAX_ATTEMPTS = 6


def _profile_steepest_ratio(
    path: Sequence[tuple[float, float]],
    levels: Sequence[float],
    *,
    ground_elevation_at: Callable[[float, float], float] | None,
    limit: float,
) -> float:
    """بیشینهٔ شیب پروفیل تقسیم بر سقف مجاز (۱ یعنی درست روی مرز).

    قرارداد ``RouteResult`` دو سر مسیر را **صفر (روی زمین)** گزارش می‌کند، پس
    همان تبدیلی که صحنه انجام می‌دهد این‌جا هم لازم است: هر نمونهٔ صفر با ارتفاع
    زمین جایگزین می‌شود تا اختلاف‌ها همه در یک چارچوب (MSL) باشند.

    چرا لازم است؟ پخش انحنا می‌تواند مسیر را افقی جابه‌جا کند — مثلاً روی یک
    یال که شیبش از سقف صعود هواپیما تندتر است. آن‌وقت تنها راهی که رمپ برای
    نگه‌داشتن فاصلهٔ ایمنی دارد، بالا رفتن با شیبی تندتر از توان هواپیما است:
    هندسهٔ رسم‌شده *پروازناپذیر* می‌شود. اندازه‌گیری روی R3: رشته‌کوهی با
    ۶۲۰ متر برآمدگی در ۳ کیلومتر (شیب ۰.۲۱) در برابر سقف صعود ۰.۱۴ — مسیر
    مجبور بود با ۲۳٪ بالا برود. این تابع همان وضعیت را تشخیص می‌دهد تا لایهٔ
    مسیریابی بتواند بودجهٔ نرم‌شدن را کم کند و مسیر روی گذرگاهِ خودش بماند.
    """
    if len(path) != len(levels) or len(path) < 2 or limit <= 0.0:
        return 0.0
    heights = [float(level) for level in levels]
    if ground_elevation_at is not None:
        for index, (lat, lon) in enumerate(path):
            if heights[index] <= 0.0:
                heights[index] = float(ground_elevation_at(lat, lon))
    lat0 = sum(lat for lat, _lon in path) / len(path)
    cos_lat = max(math.cos(math.radians(lat0)), 1e-6)
    worst = 0.0
    for (alat, alon), (blat, blon), aalt, balt in zip(
        path, path[1:], heights, heights[1:], strict=False
    ):
        run_m = math.hypot((blon - alon) * cos_lat, blat - alat) * _KM_PER_DEG_LAT * 1000.0
        if run_m <= 1e-6:
            continue
        worst = max(worst, (abs(balt - aalt) / run_m) / limit)
    return worst


def _count_heading_changes(
    graph: WindGraph,
    node_ids: list[str],
    threshold_deg: float,
) -> int:
    """تعداد تغییر جهت‌های بیش از ``threshold_deg`` درجه در طول مسیر.

    گذارهای عمودی (صعود/فرود بین لایه‌ها) شمرده نمی‌شوند: آزیموت آن‌ها تعریف
    ندارد (مبدأ و مقصد یک مختصات دارند) و در گراف سه‌بعدی هر مسیر ناچار دو
    گذار عمودی دارد، پس شمردن آن‌ها یک عدد ثابت و بی‌معنا به همه مسیرها اضافه
    می‌کرد.
    """
    changes = 0
    for i in range(1, len(node_ids) - 1):
        a = graph.get_node(node_ids[i - 1])
        b = graph.get_node(node_ids[i])
        c = graph.get_node(node_ids[i + 1])
        if a is None or b is None or c is None:
            continue
        in_edge = graph.get_edge(node_ids[i - 1], node_ids[i])
        out_edge = graph.get_edge(node_ids[i], node_ids[i + 1])
        if (in_edge is not None and in_edge.is_vertical) or (
            out_edge is not None and out_edge.is_vertical
        ):
            continue
        bearing_in = initial_bearing_deg(a.lat, a.lon, b.lat, b.lon)
        bearing_out = initial_bearing_deg(b.lat, b.lon, c.lat, c.lon)
        diff = abs(bearing_in - bearing_out) % 360.0
        turn = diff if diff <= 180.0 else 360.0 - diff
        if turn > threshold_deg:
            changes += 1
    return changes


class WindRouter:
    """ارکستراسیون نهایی مسیریابی باد — اتصال تمام ماژول‌ها.

    این کلاس رابط نهایی بین کاربر و زیرسیستم مسیریابی است. با دریافت مختصات
    مبدأ و مقصد، تمام لایه‌های موجود را ارزیابی کرده، بهترین لایه را انتخاب و
    مسیر بهینه را برمی‌گرداند.

    پارامترها
    ----------
    multi_graph : MultiLayerWindGraph
        گراف چندلایه. اگر معیار/تنظیمات درخواستی با کلید وزن‌دهی این گراف
        متفاوت باشد، یک نسخه بازمحاسبه‌شده ساخته و استفاده می‌شود.
    config : CostModelConfig, اختیاری
        تنظیمات مدل هزینه فیزیکی.
    criterion : str
        معیار بهینگی: ``"time"``، ``"energy"``، ``"balanced"`` یا ``"distance"``.
    time_weight : float, اختیاری
        وزن معیار زمان در حالت متعادل.
    algorithm : str
        الگوریتم مسیریابی هر لایه: ``"astar"`` (پیش‌فرض)، ``"dijkstra"`` یا
        ``"smooth"`` (Dijkstra با جریمه تغییر جهت، مناسب مسیرهای کم‌پیچ‌وخم).
    direction_penalty : float
        جریمه هر تغییر جهت بیش از آستانه، فقط برای الگوریتم ``"smooth"``.
        این مقدار در واحد تابع هدف جمع می‌شود.
    direction_penalty_threshold_deg : float
        آستانه تغییر جهت (درجه) برای فعال شدن جریمه و برای شمارش
        ``heading_changes`` در خروجی.
    allow_layer_changes : bool
        اگر ``True`` باشد، مسیر در یک گراف سه‌بعدی ادغام‌شده حساب می‌شود و
        می‌تواند در میانه راه ارتفاع را تغییر دهد (صعود/فرود بین لایه‌ها)
        تا تابع هدف کوچک‌تر شود. اگر ``False`` باشد (پیش‌فرض)، هر لایه جدا
        مسیریابی و بهترین لایه انتخاب می‌شود — یعنی کل مسیر در یک لایه می‌ماند.
        مسیر چندلایه همیشه بهینه‌تر یا مساوی حالت تک‌لایه است، چون حالت
        تک‌لایه یکی از مسیرهای ممکن آن است.
    vertical_cost : VerticalCostConfig, اختیاری
        فرض‌های صعود/فرود که فقط در حالت ``allow_layer_changes=True`` استفاده
        می‌شود.
    """

    def __init__(
        self,
        multi_graph: MultiLayerWindGraph,
        config: CostModelConfig | None = None,
        criterion: str = "balanced",
        time_weight: float | None = None,
        algorithm: str = "astar",
        direction_penalty: float = 0.05,
        direction_penalty_threshold_deg: float = DEFAULT_DIRECTION_PENALTY_THRESHOLD_DEG,
        allow_layer_changes: bool = False,
        vertical_cost: VerticalCostConfig | None = None,
        effort_config: MotorEffortConfig | None = None,
        steer_on_air_heading: bool = False,
        ground_elevation_at: Callable[[float, float], float] | None = None,
        min_clearance_m: float = 0.0,
    ) -> None:
        if multi_graph.layer_count == 0:
            raise ValueError("MultiLayerWindGraph has no layers. Build from data first.")
        if criterion not in CRITERIA:
            raise ValueError(f"Unknown criterion {criterion!r}; expected one of {CRITERIA}.")
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unknown algorithm {algorithm!r}; expected one of {SUPPORTED_ALGORITHMS}."
            )
        if direction_penalty < 0.0:
            raise ValueError("direction_penalty cannot be negative.")

        self._config = config or CostModelConfig()
        self.criterion = criterion
        self.time_weight = (
            self._config.time_weight if time_weight is None else time_weight
        )
        if not (0.0 <= self.time_weight <= 1.0):
            raise ValueError("time_weight must be within [0, 1].")
        self.algorithm = algorithm
        self.direction_penalty = direction_penalty
        self.direction_penalty_threshold_deg = direction_penalty_threshold_deg
        self.allow_layer_changes = allow_layer_changes
        self.vertical_cost = vertical_cost or VerticalCostConfig()
        self.effort_config = effort_config or MotorEffortConfig()
        # با ``True`` جریمهٔ تغییر جهت روی *سمت هوایی* سنجیده می‌شود: مسیرهایی
        # که می‌توان با فرمان ثابت (بادسواری) طی کرد ترجیح داده می‌شوند. پیش‌فرض
        # ``False`` است تا رفتار مسیرهای قبلی (معیار سمت مسیر روی زمین) تغییر
        # نکند.
        self.steer_on_air_heading = steer_on_air_heading
        # مدل زمین: ارتفاع زمین زیر هر نقطه و کمترین فاصلهٔ مجاز. بدون این دو،
        # گره زمین مسیر روی «سطح دریا» می‌نشست و صعودِ واقعی از زمین هیچ‌وقت
        # پرداخت نمی‌شد؛ و هیچ مسیری نمی‌دانست قله‌ای سر راهش هست.
        self.ground_elevation_at = ground_elevation_at
        self.min_clearance_m = min_clearance_m

        # وزن یال‌ها در زمان ساخت گراف پخته شده‌اند؛ اگر تنظیمات درخواستی متفاوت
        # باشد، گراف را بازمحاسبه می‌کنیم تا پارامترها واقعاً اثر داشته باشند.
        requested_key = (self.criterion, self._config, self.time_weight)
        if multi_graph.weighting_key != requested_key:
            multi_graph = multi_graph.reweight(
                criterion=self.criterion,
                config=self._config,
                time_weight=self.time_weight,
            )
        self.multi_graph = multi_graph

    @property
    def config(self) -> CostModelConfig:
        """تنظیمات مدل هزینه‌ای که این روتر با آن مسیریابی می‌کند."""
        return self._config

    @property
    def available_layers(self) -> list[float]:
        """لیست لایه‌های ارتفاعی موجود."""
        return self.multi_graph.available_layers

    def find_optimal_path(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        layers: Sequence[float] | None = None,
    ) -> RouteResult:
        """مسیر بهینه از مبدأ به مقصد با انتخاب خودکار لایه.

        پارامترها
        ----------
        origin : tuple[float, float]
            مختصات مبدأ (عرض, طول).
        destination : tuple[float, float]
            مختصات مقصد (عرض, طول).
        layers : Sequence[float], اختیاری
            اگر داده شود و ``allow_layer_changes`` روشن باشد، مسیر روی
            گراف سه‌بعدی **محدود به همین لایه‌ها** حساب می‌شود. با یک لایه،
            نتیجه مسیری تک‌لایه است که با این حال روی زمین شروع/تمام می‌شود و
            هزینه صعود و فرود را می‌پردازد؛ به همین دلیل برای مقایسه منصفانه
            با مسیر آزاد مناسب است (بر خلاف ``route_on_single_layer`` که فقط
            روی خود لایه و بدون گره زمین می‌چرخد).

        برمی‌گرداند
        ----------
        RouteResult
            نتیجه مسیر بهینه شامل مسیر، لایه انتخابی، و تخمین زمان سفر.

        استثناها
        --------
        ValueError
            اگر هیچ لایه‌ای در دسترس نباشد یا مسیری یافت نشود.
        """
        if self.allow_layer_changes:
            return self._route_across_layers(origin, destination, layers=layers)
        if layers is not None:
            raise ValueError(
                "`layers` only applies when allow_layer_changes=True; otherwise "
                "use route_on_single_layer()."
            )
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

    def route_on_single_layer(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        altitude: float,
    ) -> RouteResult:
        """مسیر بهینه را **فقط** روی یک لایه ارتفاعی مشخص حساب می‌کند.

        بر خلاف ``find_optimal_path`` هیچ انتخاب خودکاری بین لایه‌ها انجام
        نمی‌شود؛ این همان حالت «پرواز تنها در یک لایه» است.

        پارامترها
        ----------
        origin : tuple[float, float]
            مختصات مبدأ (عرض, طول).
        destination : tuple[float, float]
            مختصات مقصد (عرض, طول).
        altitude : float
            ارتفاع لایه مورد استفاده (باید در ``available_layers`` باشد).

        برمی‌گرداند
        ----------
        RouteResult
            نتیجه مسیر روی همان لایه.

        استثناها
        --------
        ValueError
            اگر لایه وجود نداشته باشد یا مسیری روی آن یافت نشود.
        """
        graph = self.multi_graph.get_layer(altitude)
        if graph is None:
            raise ValueError(
                f"Layer {altitude} is not available. Available: {self.available_layers}."
            )

        result = self._route_on_layer(graph, origin, destination)
        if result is None:
            raise ValueError(
                f"No feasible path found between {origin} and {destination} "
                f"on layer {altitude}."
            )
        return result

    def _route_across_layers(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        layers: Sequence[float] | None = None,
    ) -> RouteResult:
        """مسیر بهینه روی گراف سه‌بعدی ادغام‌شده (با امکان تغییر لایه در میانه راه).

        بر خلاف مسیریابی تک‌لایه، این‌جا مسیر می‌تواند برای استفاده از باد بهتر،
        از یک لایه به لایه دیگر صعود/فرود کند و هزینه آن گذار (``vertical_cost``)
        هم در تابع هدف حساب می‌شود. مسیر از گره زمین مبدأ شروع و به گره زمین
        مقصد ختم می‌شود، پس صعود اولیه و فرود نهایی هم بخشی از مسیر بهینه‌اند.

        استثناها
        --------
        ValueError
            اگر هیچ مسیری در گراف سه‌بعدی پیدا نشود.
        """
        stacked: StackedGraph = self.multi_graph.to_stacked_graph(
            origin,
            destination,
            vertical_cost=self.vertical_cost,
            criterion=self.criterion,
            config=self._config,
            time_weight=self.time_weight,
            layers=layers,
            ground_elevation_at=self.ground_elevation_at,
        )
        result = self._route_on_graph(
            stacked.graph, stacked.origin_id, stacked.destination_id
        )
        if result is None:
            raise ValueError(
                f"No feasible multi-layer path found between {origin} and "
                f"{destination} across layers {list(stacked.layer_altitudes)}."
            )
        return result

    def _route_on_layer(
        self,
        graph: WindGraph,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> RouteResult | None:
        """مسیریابی روی یک لایه خاص با الگوریتم انتخابی این روتر.

        مسیر از **گره زمین** مبدأ شروع و به گره زمین مقصد می‌رسد، پس صعود اولیه
        و فرود نهایی بخشی از هزینه‌اند — دقیقاً مثل حالت چندلایه.

        این‌جا همین یک تغییر مهم است: پیش‌تر این تابع مستقیم روی گراف *خودِ لایه*
        مسیریابی می‌کرد و آن گراف گره زمین ندارد (هر گره روی ارتفاع لایه است).
        نتیجه این بود که هر مسیر تک‌لایه «در آسمان» شروع می‌شد، ``total_climb_m``
        و ``total_descent_m`` صفر می‌ماندند، و انتخاب لایه با گراف آزاد سه‌بعدی
        (که گره زمین دارد و صعود را می‌پردازد) پیوسته هم‌مقیاس** نبود**. آن
        تفاوت، یعنی برتری ظاهری لایه‌های بالا، فقط یک خطای حسابداری بود.
        الان هر دو مسیر از یک قرارداد پیروی می‌کنند: ``to_stacked_graph`` با
        ``layers=(altitude,)``.

        اگر مسیری یافت نشود ``None`` برمی‌گرداند.
        """
        altitude = graph.altitude
        if altitude in self.multi_graph.available_layers:
            try:
                stacked: StackedGraph = self.multi_graph.to_stacked_graph(
                    origin,
                    destination,
                    vertical_cost=self.vertical_cost,
                    criterion=self.criterion,
                    config=self._config,
                    time_weight=self.time_weight,
                    layers=(altitude,),
                    ground_elevation_at=self.ground_elevation_at,
                )
            except ValueError:
                # این لایه نمی‌تواند گره زمین را بپذیرد (گراف ساخته‌شده دستی، یا
                # مختصات بیرون از دامنه لایه). قرارداد این تابع «مسیری روی این
                # لایه وجود ندارد» است، پس ``None`` برمی‌گردانیم تا
                # ``compare_layers`` لایه بعدی را امتحان کند و اگر هیچ لایه‌ای
                # جواب نداد، همان خطای «مسیری یافت نشد» بلند شود.
                return None
            return self._route_on_graph(
                stacked.graph, stacked.origin_id, stacked.destination_id
            )

        # گرافی که بخشی از مجموعه چندلایه نیست (گراف ساخته‌شده دستی در آزمون‌ها):
        # مسیریابی مستقیم، بدون گره زمین.
        start_id = graph.find_nearest_node(origin[0], origin[1])
        end_id = graph.find_nearest_node(destination[0], destination[1])

        if start_id is None or end_id is None:
            return None
        if start_id == end_id:
            return None

        return self._route_on_graph(graph, start_id, end_id)

    def _route_on_graph(
        self,
        graph: WindGraph,
        start_id: str,
        end_id: str,
    ) -> RouteResult | None:
        """اجرای الگوریتم انتخاب‌شده روی گراف و جمع‌بندی آماری مسیر.

        این تابع هم گراف تک‌لایه و هم گراف ادغام‌شده چندلایه را می‌پذیرد. تنها
        تفاوت رفتار روی گراف ادغام‌شده، وجود یال‌های عمودی است: مسافت افقی و
        نسبت باد پشت گذارهای عمودی را نمی‌شمارند (وگرنه با صعود مصنوعی کوچک
        می‌شدند) و ارتفاع پیموده‌شده جداگانه گزارش می‌شود.
        """
        if self.algorithm == "smooth":
            path_ids, total_cost = smooth_dijkstra(
                graph,
                start_id,
                end_id,
                direction_penalty=self.direction_penalty,
                direction_penalty_threshold_deg=self.direction_penalty_threshold_deg,
                steering_airspeed_mps=(
                    self._config.airspeed_mps if self.steer_on_air_heading else None
                ),
            )
        elif self.algorithm == "dijkstra":
            path_ids, total_cost = dijkstra(graph, start_id, end_id)
        else:
            path_ids, total_cost = a_star(
                graph,
                start_id,
                end_id,
                airspeed_mps=self._config.airspeed_mps,
                criterion=graph.criterion,
            )
            if not path_ids or total_cost == float("inf"):
                # A* با تخمین مجاز مسیر را از دست نمی‌دهد؛ این fallback تنها برای
                # گراف‌هایی است که با معیار متفاوتی وزن‌دهی شده‌اند.
                path_ids, total_cost = dijkstra(graph, start_id, end_id)

        if not path_ids or total_cost == float("inf"):
            return None

        # تبدیل شناسه‌ها به مختصات + جمع مسافت، زمان واقعی و شاخص انرژی
        path_coords: list[tuple[float, float]] = []
        node_altitudes: list[float] = []
        flight_clearances: list[float] = []
        for nid in path_ids:
            node = graph.get_node(nid)
            if node is not None:
                path_coords.append((node.lat, node.lon))
                # گره زمین ارتفاع صفر گزارش می‌شود (قرارداد ``RouteResult``)،
                # حتی اگر ارتفاع واقعی زمین ۱۴۰۰ متر باشد: «صفر» این‌جا یعنی
                # «روی زمین»، نه «سطح دریا».
                node_altitudes.append(0.0 if node.is_ground else node.altitude)
                if not node.is_ground:
                    flight_clearances.append(node.altitude - node.ground_elevation_m)

        total_distance = 0.0
        total_time_hours = 0.0
        total_energy_index = 0.0
        tailwind_legs = 0
        horizontal_legs = 0
        climb_m = 0.0
        descent_m = 0.0
        climb_legs = 0
        time_by_altitude: dict[float, float] = {}
        # نمونه‌های سرعت زمینی (مسافت، سرعت) برای ساخت رمپ‌های عمودی: مسافت
        # افقی هر گذر ارتفاعی از همین سرعت می‌آید، پس رمپ با همان سرعتی پخش
        # می‌شود که مسیر واقعاً با آن طی می‌شود.
        ground_speed_samples: list[tuple[float, float]] = []
        # قطعات افقی برای مدل تلاش موتوری: باد هر قطعه همان باد *گرهٔ شروع*
        # است — دقیقاً همان بادی که در زمان ساخت گراف وزن همان یال را تعیین
        # کرده، پس اعداد سوخت با همان فرض‌های مسیریابی هم‌خوان می‌مانند.
        leg_samples: list[LegSample] = []

        for i in range(len(path_ids) - 1):
            n1 = graph.get_node(path_ids[i])
            n2 = graph.get_node(path_ids[i + 1])
            if n1 is None or n2 is None:
                continue

            leg_edge = graph.get_edge(path_ids[i], path_ids[i + 1])
            is_vertical = leg_edge is not None and leg_edge.is_vertical
            cost_result = leg_edge.cost_result if leg_edge is not None else None

            if is_vertical:
                delta = n2.altitude - n1.altitude
                if delta >= 0.0:
                    climb_m += delta
                else:
                    descent_m += -delta
                climb_legs += 1
            else:
                if leg_edge is not None:
                    total_distance += leg_edge.distance_km
                else:
                    total_distance += haversine_km(n1.lat, n1.lon, n2.lat, n2.lon)
                horizontal_legs += 1
                if cost_result is not None and cost_result.along_track_mps > 0.0:
                    tailwind_legs += 1
                leg_samples.append(
                    sample_horizontal_leg(
                        n1.lat,
                        n1.lon,
                        n2.lat,
                        n2.lon,
                        n1.wind_speed_mps,
                        n1.wind_direction_deg,
                        leg_edge.distance_km if leg_edge is not None else 0.0,
                        cost_result.time_hours if cost_result is not None else 0.0,
                    )
                )

            if cost_result is not None:
                total_time_hours += cost_result.time_hours
                total_energy_index += cost_result.energy_hours
                if not is_vertical:
                    leg_km = (
                        leg_edge.distance_km
                        if leg_edge is not None
                        else haversine_km(n1.lat, n1.lon, n2.lat, n2.lon)
                    )
                    if cost_result.ground_speed_mps > 0.0 and leg_km > 0.0:
                        ground_speed_samples.append((leg_km, cost_result.ground_speed_mps))
                    # زمان کروز هر ارتفاع، مبنای تعیین ارتفاع کروز مسیر است.
                    time_by_altitude[n1.altitude] = (
                        time_by_altitude.get(n1.altitude, 0.0) + cost_result.time_hours
                    )
            elif is_vertical:
                # گراف دستی بدون نتیجه هزینه → تخمین با نرخ صعود/فرود.
                delta = abs(n2.altitude - n1.altitude)
                total_time_hours += delta / graph.vertical_cost.rate_mps(delta) / 3600.0
            else:
                # یال بدون نتیجه هزینه (گراف دستی) → تخمین زمان با سرعت هوایی.
                leg_km = leg_edge.distance_km if leg_edge is not None else 0.0
                total_time_hours += leg_km / (self._config.airspeed_mps * 3.6)

        # ارتفاع کروز = ارتفاعی که بیشترین زمان پرواز در آن سپری شده است.
        cruise_altitude = graph.altitude
        if time_by_altitude:
            cruise_altitude = max(time_by_altitude, key=lambda alt: time_by_altitude[alt])

        # لایه‌های واقعی مسیر = ارتفاع گره‌های *پرواز*. پیش از نرم‌کردن پروفیل
        # گرفته می‌شود، وگرنه ارتفاع‌های میانی رمپ‌ها هم «لایه» شمرده می‌شدند و
        # یک مسیر تک‌لایه به‌غلط چندلایه به‌نظر می‌رسید (به ``altitudes_used``
        # در ``RouteResult`` نگاه کنید).
        flight_layers = tuple(
            sorted(
                {
                    node.altitude
                    for node in (graph.get_node(nid) for nid in path_ids)
                    if node is not None and not node.is_ground
                }
            )
        )

        # **پروفیل عمودی.** یال‌های عمودی گراف یک پله‌اند: گرهٔ بعدی همان‌جاست
        # ولی ارتفاع دیگری دارد. هواپیما این‌طور پرواز نمی‌کند — با نرخ معین
        # صعود/فرود می‌کند و هر گذر ارتفاعی به همان اندازه مسافت افقی می‌خواهد.
        # تبدیل در همین لایه (مسیریابی) انجام می‌شود، نه در صحنه، تا هندسهٔ
        # گزارش‌شده همان چیزی باشد که الگوریتم تولید می‌کند.
        # **هندسهٔ منحنی.** گراف لایه‌ای است، پس مسیر دنباله‌ای از پاره‌های مستقیم
        # است که در گره‌ها گوشه می‌سازند. علامت آن در صحنه صریح است: ۹۷٪ پاره‌های
        # رسم‌شده کمتر از ۰.۵ درجه می‌چرخند، یعنی خطی که دیده می‌شود یک خط شکستهٔ
        # راست است و «اسپلاین» فقط روی همان خط شکسته می‌نشست. گردکردن گوشه **در
        # همین لایه** انجام می‌شود (نه در رندرگر) تا هندسهٔ گزارش‌شده همان چیزی
        # باشد که الگوریتم تولید می‌کند. قید زمین هم داخل همان تابع بررسی می‌شود.
        path_coords, node_altitudes = round_path_corners(
            path_coords,
            node_altitudes,
            ground_elevation_at=self.ground_elevation_at,
            min_clearance_m=self.min_clearance_m,
        )
        # **پروفیل عمودی *قبل* از پخش انحنا.** ترتیب قبلی (گرد ← پخش ← رمپ)
        # یک نقص ساختاری داشت و اندازه‌گیری شد: ``relax_path_curvature`` کف
        # ایمنی خودش را از پروفیل پله‌ایِ ارتفاع می‌گرفت، و در هر گذر لایه
        # (مثلاً ۲۹۰۰ ← ۲۲۰۰) این کف *ناگهان* می‌پرید؛ پخشِ حرارتی نمونه را
        # از مرز می‌گذراند، کفِ پله‌ای برمی‌گرداندش و یک شکستگی همیشگی روی
        # مرز لایه میخکوب می‌شد (اندازه‌گیری: R1 روی مرز لایه در ۴۸ کیلومتری
        # با گارد زمین ۲۲°/km می‌ماند، بدون گارد به ۱.۴°/km می‌رسد). با
        # نرم‌شدن پروفیل عمودی *پیش* از پخش، گارد زمین ارتفاعِ واقعیِ پیوسته
        # را می‌بیند — نه پلهٔ لایه‌ها — و هیچ مرزی برای میخکوب‌شدن باقی
        # نمی‌ماند. رمپ خودش کف زمین را نگه می‌دارد، پس ترتیب جدید همان تضمین
        # ایمنی را دارد.
        path_coords, node_altitudes = ramp_vertical_transitions(
            path_coords,
            node_altitudes,
            climb_rate_mps=self.vertical_cost.climb_rate_mps,
            descent_rate_mps=self.vertical_cost.descent_rate_mps,
            ground_speed_mps=_mean_ground_speed(
                ground_speed_samples, self._config.airspeed_mps
            ),
            ground_elevation_at=self.ground_elevation_at,
            # سقف شیب فرود از همان نسبت گلاید می‌آید که مدل تلاش موتوری با آن
            # سوختِ گلاید را حساب می‌کند: یک عدد، دو مصرف‌کننده. اگر هندسه و
            # حسابداری دو عدد جدا داشته باشند، شیبی که دیده می‌شود با سوختی که
            # گزارش می‌شود یکی نیست.
            glide_ratio=self.effort_config.glide_ratio,
            min_clearance_m=self.min_clearance_m,
        )
        # **پخش‌کردن انحنا — پس از رمپ عمودی.** فیلت گوشه‌ها را گرد می‌کند،
        # ولی پاره‌های بین گره‌ها راست می‌مانند و کمان هر گوشه کوتاه است؛
        # نتیجهٔ اندازه‌گیری‌شده روی آرتیفکت: R4 یک بخش ۸۴ کیلومتری **کاملاً
        # راست** دارد و بعد در یک نمونهٔ ۰.۳ کیلومتری ۶.۲ درجه می‌چرخد
        # (≈ ۲۱°/km). این تابع انحنا را در طول مسیر پخش می‌کند، با قید سخت
        # روی انحراف از مسیر مسیریابی‌شده و روی زمین. چون رمپ عمودی قبلاً
        # اجرا شده، پروفیل ارتفاع پیوسته است و گارد زمینِ این تابع دیگر با
        # پلهٔ لایه‌ها نمی‌جنگد (توضیح بالای رمپ).
        # **گارد زمین این‌جا خاموش است — و کف زمین *پس* از این مرحله دوباره
        # برقرار می‌شود.** این تفکیک، هستهٔ اصلاح است. اندازه‌گیری روی همین
        # کریدور نشان داد گارد زمینِ درون پخش انحنا، نرم‌شدن را *میخکوب*
        # می‌کند: در گردنهٔ شمال مشهد مسیر مسیریابی‌شده خودش با ۲۹۰ متر فاصله
        # از زمین رد می‌شود (کمتر از کف ۳۰۰ متری)، پس کف گارد می‌شود «همان
        # ۲۹۰ متر» و هر جابه‌جایی افقی به سمت رشته‌کوه رد می‌شود. نتیجه:
        # R1/R2/R4 با خوشهٔ متناوب‌العلامت روی ۹ تا ۱۲ درجه بر کیلومتر
        # دست‌نخورده می‌ماندند در حالی که R3/R6 (بالاتر از رشته‌کوه) نرم
        # می‌شدند — یعنی تفاوت «خوب دیده‌شدن» فقط به فاصله از کوه بسته بود،
        # نه به الگوریتم. تفکیک درست همان است که پرنده انجام می‌دهد: **افقی
        # را نرم کن، عمودی را بالا ببر تا ایمنی برگردد.** پس پخش انحنا فقط
        # با قید انحراف (``max_deviation_km``) کار می‌کند و رمپ زیر، که کف
        # زمین و سقف صعود/فرود را روی *همین* هندسهٔ افقی دوباره حساب می‌کند،
        # تضمین ایمنی را پس می‌گیرد. هیچ‌کدام از این‌ها کریدور-خاص نیست.
        ground_speed_mps = _mean_ground_speed(
            ground_speed_samples, self._config.airspeed_mps
        )
        vertical_limit = (
            _VERTICAL_RATE_MARGIN
            * max(
                self.vertical_cost.climb_rate_mps,
                self.vertical_cost.descent_rate_mps,
            )
            / max(ground_speed_mps, 1e-6)
        )

        def _ramp(coords, levels):
            """پروفیل عمودی روی یک هندسهٔ افقی داده‌شده."""
            return ramp_vertical_transitions(
                coords,
                levels,
                climb_rate_mps=self.vertical_cost.climb_rate_mps,
                descent_rate_mps=self.vertical_cost.descent_rate_mps,
                ground_speed_mps=ground_speed_mps,
                ground_elevation_at=self.ground_elevation_at,
                glide_ratio=self.effort_config.glide_ratio,
                min_clearance_m=self.min_clearance_m,
            )

        # **پروفیل عمودی روی هندسهٔ *نهایی*، با بودجهٔ نرم‌شدنِ کاهش‌یابنده.**
        # پخش انحنا آزاد است (گارد زمینش خاموش است) ولی «آزاد» به معنای
        # «بی‌قید» نیست: اگر مسیر را روی رشته‌کوهی ببرد که شیبش از توان صعود
        # هواپیما تندتر است، رمپ برای نگه‌داشتن فاصلهٔ ایمنی باید با همان شیب
        # تند بالا برود — یعنی یک هندسهٔ پروازناپذیر.
        # اندازه‌گیری روی R3: برآمدگی ۶۲۰ متری در ۳ کیلومتر (شیب ۰٫۲۱) در برابر
        # سقف ۰٫۱۴؛ مسیر مجبور می‌شد با ۲۳٪ بالا برود. پس هر تلاش، هندسه را نرم
        # می‌کند و *شیب پروفیل* را دوباره می‌سنجد؛ تا وقتی پروازپذیر بماند بودجه
        # کامل است، وگرنه نصف می‌شود. بودجهٔ نزدیک به صفر یعنی «همان هندسهٔ
        # مسیریابی‌شده»، که خودش پروازپذیر است — پس حلقه هیچ‌وقت بدتر از قبل
        # برنمی‌گرداند.
        smooth_coords, smooth_levels = path_coords, node_altitudes
        path_coords, node_altitudes = _ramp(path_coords, node_altitudes)
        for _attempt in range(_RELAX_ATTEMPTS):
            budget = RELAX_MAX_DEVIATION_KM / (2.0**_attempt)
            relaxed_coords, relaxed_levels = relax_path_curvature(
                smooth_coords,
                smooth_levels,
                max_deviation_km=max(budget, 1e-3),
                ground_elevation_at=None,
                min_clearance_m=0.0,
            )
            relaxed_coords, relaxed_levels = _ramp(relaxed_coords, relaxed_levels)
            path_coords, node_altitudes = relaxed_coords, relaxed_levels
            if (
                _profile_steepest_ratio(
                    path_coords,
                    node_altitudes,
                    ground_elevation_at=self.ground_elevation_at,
                    limit=vertical_limit,
                )
                <= 1.0
            ):
                break

        # **مسافت گزارش‌شده = مسافت *پروازشده*، نه جمع پاره‌های گراف.** فیلت
        # گوشه‌ها را کمان می‌کند و هواپیما کمان را کوتاه‌تر از زاویه می‌پیماید،
        # پس هندسهٔ نهایی همیشه کمی کوتاه‌تر از خط‌شکن گره‌ها است. عدد قبلی
        # همان خط‌شکن بود و آن چیزی که در صحنه دیده می‌شود را توصیف نمی‌کرد —
        # اندازه‌گیری روی R4: ۱۹۲.۸ کیلومتر در جدول در برابر ۱۹۰.۶ کیلومتر خط
        # رسم‌شده؛ یعنی تصویر، جدول را رد می‌کرد. حالا جدول همان هندسه‌ای را
        # می‌گوید که پرواز می‌شود.
        flown_km = sum(
            haversine_km(lat1, lon1, lat2, lon2)
            for (lat1, lon1), (lat2, lon2) in zip(
                path_coords, path_coords[1:], strict=False
            )
        )

        return RouteResult(
            path=path_coords,
            node_ids=path_ids,
            layer_altitude=cruise_altitude,
            total_cost=total_cost,
            total_distance_km=flown_km if flown_km > 0.0 else total_distance,
            estimated_time_hours=total_time_hours,
            criterion=self.criterion,
            total_energy_index=total_energy_index,
            tailwind_leg_fraction=(tailwind_legs / horizontal_legs) if horizontal_legs else 0.0,
            heading_changes=_count_heading_changes(
                graph, path_ids, self.direction_penalty_threshold_deg
            ),
            algorithm=self.algorithm,
            node_altitudes=node_altitudes,
            layers_used=flight_layers,
            total_climb_m=climb_m,
            total_descent_m=descent_m,
            climb_legs=climb_legs,
            # کمترین فاصلهٔ عمودی از زمین در تمام گره‌های *پرواز* مسیر. بدون
            # داده زمین، این عدد معنا ندارد و ``None`` می‌ماند تا با عدد جعلی
            # اشتباه گرفته نشود.
            min_clearance_m=(
                min(flight_clearances)
                if flight_clearances and self.ground_elevation_at is not None
                else None
            ),
            # قطعه‌های افقی برای سنجش *اندازهٔ* ناهم‌راستایی مسیر با باد. بدون
            # این‌ها تنها می‌شد شمرد که مؤلفهٔ هم‌راستا مثبت بوده یا نه، نه
            # اینکه مسیر چند درجه با باد کج است.
            leg_samples=leg_samples,
            effort=compute_route_effort(
                leg_samples,
                aircraft=self._config,
                effort=self.effort_config,
                climb_m=climb_m,
                descent_m=descent_m,
            ),
        )
