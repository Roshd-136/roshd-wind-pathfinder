"""مسیریابی «بادسواری» — با یک فرمان سمت، باد مسیر را می‌برد.

ایدهٔ مسیر
----------
مسیریابی روی گراف (A*/Dijkstra) مسیر را روی یک شبکهٔ گره‌ای می‌سازد، پس مسیر ناچار
«پله‌ای» می‌شود و هر پله یک تصحیح سمت با موتور لازم دارد. در این میدان باد (باد
غالباً از شرق به غرب، یعنی هم‌راستا با کریدور مشهد→سبزوار) راه دیگری هم هست که
گراف نمی‌تواند بیانش کند:

۱) صعود به یک لایه،
۲) نگه‌داشتن **یک** سمت هوایی ثابت،
۳) اینکه باد هواپیما را جلو ببرد — مسیر روی زمین هرچه باد می‌خواهد می‌شود،
۴) و در پایان فرود تدریجی روی مقصد.

«بادسواری» همین است. سمت فرمان با جست‌وجوی یک‌پارامتری انتخاب می‌شود: برای هر
سمت، مسیر روی زمین *انتگرال‌گیری* می‌شود و سمتی برگزیده می‌شود که با کمترین زمان
کل به مقصد برسد. لایه هم با همان معیار (صعود + بادسواری + فرود + قطعهٔ پایانی)
انتخاب می‌شود.

هشدار صداقت
-----------
- این برنامه‌ریز روی *میدان باد* انتگرال می‌گیرد، نه روی گراف. مسافت/زمانش از
  همان میدان بادِ مسیرهای گرافی می‌آید (``LayerField``)، ولی مسیر در فضای پیوسته
  ساخته می‌شود و می‌تواند از گره‌های گراف نگذرد. پس «کوتاه‌ترین مسیر گراف» و
  «بادسواری» دو فضای جواب متفاوت‌اند؛ مقایسه‌شان در جدول صحنه همین را می‌گوید.
- زیر پایین‌ترین لایه (AGL < ۵۰۰ متر) میدان باد تعریف نشده است؛ در فاز فرود، باد
  همان **پایین‌ترین لایهٔ موجود** استفاده می‌شود. این محدودیت داده است، نه فرض
  فیزیکی.
- صعود در همین یک نقطه انجام می‌شود (همان قراردادی که یال‌های عمودی گراف دارند).
  صعود در حال حرکت مدل نشده است.
- **فرود یک *شیب* است، نه یک شیرجه.** فرود وقتی شروع می‌شود که فاصلهٔ باقی‌مانده
  با ``h · descent_glideslope_ratio`` برابر شود و بعد روی همان شیب ثابت تا ارتفاع
  زمین مقصد ادامه می‌یابد. شیب پیش‌فرض (۱ به ۴۰) از شیب گلاید بیشینهٔ هواپیما
  (۱ به L/D = ۱ به ۱۲) *ملایم‌تر* است، یعنی موتور خاموش نمی‌تواند آن را نگه دارد؛
  پس موتور با توان *جزئی* کار می‌کند و همان توان هم واقعاً حساب می‌شود. از توازن
  رانش در فرود (`T = D − m·g·sinγ` و `D = m·g/(L/D)`) کسر توان
  `۱ − (L/D)·sinγ` می‌آید؛ اگر شیبِ لازم از گلاید بیشینه تندتر شود، دور آرام
  (`descent_idle_power_fraction`) کف کار می‌شود.
- **شکل پروفیل، سوخت را رایگان نمی‌کند.** ملایم‌کردن فرود یعنی مسافتِ بیشتری
  زیر شیب سپری شود و همان مسافت از کروز کم شود؛ اتحاد انرژی می‌گوید در مسیری که
  از زمین شروع و روی زمین تمام می‌شود تنها هزینهٔ واقعی *کار پسار در طول مسیر*
  است، نه شکل پروفیل ارتفاع. پس فرود ملایم تقریباً هم‌قیمتِ فرود تند است و انتخاب
  بین آن دو یک انتخاب *نمایشی/عملیاتی* است، نه یک بهینه‌سازی پنهان.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from pathfinding.alignment import wind_alignment_profile
from pathfinding.cost import CostModelConfig, compute_edge_cost, initial_bearing_deg
from pathfinding.effort import LegSample, MotorEffortConfig, compute_route_effort
from pathfinding.graph import VerticalCostConfig, compute_vertical_cost
from pathfinding.profile import ramp_vertical_transitions
from pathfinding.routing import RouteResult
from preprocessing.consistency import haversine_km

__all__ = [
    "WindSampler",
    "WindRidingConfig",
    "WindRidingPlan",
    "plan_wind_riding_route",
    "wind_riding_route_result",
]

# نمونه‌بردار باد یک لایه: ``(lat, lon) -> (speed_mps, direction_from_deg)``.
WindSampler = Callable[[float, float], tuple[float, float]]

_KM_PER_DEG_LAT = 111.32

@dataclass(frozen=True)
class WindRidingConfig:
    """پارامترهای عددی برنامه‌ریزی بادسواری (همه «سیاست محاسباتی»، نه فیزیک).

    پارامترها
    ----------
    step_s : float
        گام انتگرال‌گیری زمانی (ثانیه). کوچک‌تر = دقیق‌تر و کندتر.
    max_hours : float
        سقف زمان شبیه‌سازی هر سمت فرمان (ساعت).
    max_arrival_miss_km : float
        بیشترین فاصلهٔ نهایی قابل‌قبول از مقصد (کیلومتر). برنامه‌ای که بدتر از
        این باشد رد می‌شود؛ باقی‌مانده با یک قطعهٔ پایانی بسته می‌شود.
    arrival_radius_km : float
        اگر فاصله به این مقدار برسد، «رسیدن» پذیرفته می‌شود.
    heading_coarse_step_deg : float
        گام پویش درشت روی ۳۶۰ درجه.
    heading_refine_steps_deg : tuple[float, ...]
        گام‌های ریزکردن پشت‌سرهم: هر مرحله حول بهترین سمت مرحلهٔ قبل، در بازهٔ
        ±گام مرحلهٔ قبل، با گام این مرحله پویش می‌کند. چند مرحله لازم است چون
        «خطای رسیدن» به سمت فرمان حساس است: با یک مرحله ۰.۲۵ درجه‌ای، مسیر
        چند صد متر بیرون مقصد فرود می‌آمد و همان باقی‌مانده یک قطعهٔ پایانی
        (و یک تصحیح سمت) به مسیر تحمیل می‌کرد — چیزی که کل ایدهٔ بادسواری را
        بی‌اثر می‌کرد.
    path_sample_s : float
        گام زمانی نگه‌داشتن نقطه/قطعه در مسیر گزارش‌شده (ثانیه). انتگرال‌گیری با
        ``step_s`` انجام می‌شود؛ برای مسیر، هر ``path_sample_s`` یک نقطه نگه
        داشته می‌شود وگرنه مسیر چند صد قطعه می‌شود و مقادیر بازسازی‌شده از وترها
        نویز می‌گیرند.
    abandon_margin_km : float
        قاعدهٔ هرس جست‌وجو: اگر فاصله به مقصد از بهترین فاصلهٔ دیدهٔ‌شده در همان
        شبیه‌سازی بیشتر از این مقدار شود، آن سمت رها می‌شود. سمت‌هایی که مقصد را
        نمی‌گیرند ناچار تا ``max_hours`` می‌رفتند و کل جست‌وجو را کند می‌کردند.
        این فقط یک قاعدهٔ *محاسباتی* است: سمت رهاشده هرگز نمی‌تواند بهترین
        برنامه باشد (در حال دور شدن از مقصد است).
    descent_glideslope_ratio : float
        شیب فرود به‌صورت «۱ به N» — به‌ازای هر متر کم‌کردن ارتفاع، N متر جلو
        رفتن. بُرد گلاید *بیشینه* هواپیما ``L/D`` است؛ مقدار بزرگ‌تر یعنی فرود
        ملایم‌تر و طولانی‌تر که فقط با توان جزئی موتور ممکن است (و همان توان در
        ``power_fraction`` قطعه‌های فرود حساب می‌شود). مقدار کوچک‌تر از ``L/D``
        یعنی فرود تندتر از گلاید: دور آرام کف کار می‌شود و باقی انرژی از
        تندترکم‌کردن ارتفاع می‌آید.
    approach_km : float
        طول تقرب پایانی (کیلومتر). کف فاصلهٔ ایمنی از زمین در فرود تنها وقتی
        بر فراز *کوه* معنا دارد؛ در این چند کیلومتر آخر، کف خطی از `زمین + آستانه`
        به ارتفاع زمین مقصد می‌رسد تا نشستن روی مقصد ممکن باشد. بدون این
        گذار، فرود مجبور می‌شد ۳۰۰ متر بالای مقصد تمام شود.
    """

    step_s: float = 20.0
    max_hours: float = 8.0
    max_arrival_miss_km: float = 2.0
    arrival_radius_km: float = 0.2
    heading_coarse_step_deg: float = 4.0
    heading_refine_steps_deg: tuple[float, ...] = (1.0, 0.1)
    path_sample_s: float = 120.0
    abandon_margin_km: float = 5.0
    descent_glideslope_ratio: float = 40.0
    approach_km: float = 3.0
    track_wind: bool = True
    wind_corridor_fraction: float = 0.5
    wind_corridor_min_km: float = 0.2
    # **جست‌وجوی سیاست، نه یک سیاست ثابت.** دالان ``wind_corridor_fraction``
    # تعیین می‌کند هواپیما تا چه اندازه اجازه دارد از خط مبدأ–مقصد دور شود تا
    # «موازی باد» بماند. این یک *مبادله* است، نه یک انتخاب درست/غلط: دالان
    # بازتر یعنی سهم بیشترِ مسیرِ موازی باد، به بهای مسافت/زمان/سوخت بیشتر و
    # یک تصحیح پایانی بزرگ‌تر. اندازه‌گیری روی همین کریدور (جدول «مبادلهٔ
    # بادسواری» در صحنه) نشان می‌دهد سهم موازی از ۹٪ (دالان ۰.۲) تا ۶۲٪
    # (دالان ۰.۹۵) می‌رود و زمان از ۲.۱۲ به ۲.۳۱ ساعت. پس بهترین دالان یک عدد
    # ثابت نیست و باید با *هدف* انتخاب شود؛ همان کاری که این جست‌وجو می‌کند.
    search_fractions: tuple[float, ...] = (0.5, 0.75, 0.95)
    # هدف: بیشترین مسافت موازی باد، مشروط به اینکه زمان از این ضریب روی
    # کم‌زمان‌ترین برنامهٔ همان لایه بیشتر نشود. بدون این سقف، «بیشترین موازی»
    # یک مسیر بی‌معنا می‌شود (کل کریدور را دور می‌زند تا هم‌راستا بماند).
    alignment_first: bool = True
    alignment_slack_ratio: float = 1.15
    # **یک دالان مشخص، به‌جای جست‌وجو.** اگر این مقدار داده شود، برنامه‌ریز فقط
    # همان یک دالان را می‌سنجد و انتخاب خودکار را کنار می‌گذارد. کاربردش ساختن
    # «گونه‌های هم‌خانواده» یک مسیر بادسواری است: چند نقطهٔ متفاوت روی همان
    # مبادله (دالان تنگ = سریع‌ترین و کم‌موازی‌ترین، دالان باز = موازی‌ترین)،
    # تا در صحنه و جدول کنار هم دیده شوند و تفاوت استراتژی قابل مقایسه باشد.
    # ``None`` یعنی همان جست‌وجوی خودکار (رفتار پیش‌فرض).
    corridor_override: float | None = None

    def __post_init__(self) -> None:
        if self.descent_glideslope_ratio <= 0.0:
            raise ValueError("descent_glideslope_ratio must be positive.")
        if self.approach_km <= 0.0:
            raise ValueError("approach_km must be positive.")
        if not 0.0 < self.wind_corridor_fraction < 1.0:
            raise ValueError("wind_corridor_fraction must be in (0, 1).")
        if self.wind_corridor_min_km <= 0.0:
            raise ValueError("wind_corridor_min_km must be positive.")
        if not self.search_fractions:
            raise ValueError("search_fractions cannot be empty.")
        for fraction in self.search_fractions:
            if not 0.0 < fraction < 1.0:
                raise ValueError("every search fraction must be in (0, 1).")
        if self.alignment_slack_ratio < 1.0:
            raise ValueError("alignment_slack_ratio must be at least 1.0.")
        if self.corridor_override is not None and not 0.0 < self.corridor_override < 1.0:
            raise ValueError("corridor_override must be in (0, 1) when given.")

    # سیاست بادسواری، دو حالت دارد و هر دو در همین ماژول پیاده شده‌اند:
    #
    # ``track_wind=True`` (پیش‌فرض) — **دنبال‌کردن باد.** فرمان طوری حل می‌شود که
    #   *سمت مسیر روی زمین* روی جهت خودِ باد بیفتد (مثلث باد). پس مسیر در فاز
    #   بادسواری موازی پیکان‌های باد است و پسار القایی و باد رو-به-رو صفر می‌شود
    #   (هواپیما باد را دنبال می‌کند، با آن نمی‌جنگد). تصحیح مسیر فقط تا آنجا
    #   رخ می‌دهد که لازم باشد *دالان فرود* (`wind_corridor_fraction`) برقرار
    #   بماند؛ پس می‌شود چند تصحیح کوتاه، نه یک نبرد مداوم.
    #
    # ``track_wind=False`` — **سمت فرمان ثابت.** همان مدل قبلی: یک سمت هوایی
    #   برای همهٔ مسیر، باد هواپیما را می‌برد و مسیر روی زمین کج می‌شود. با آن،
    #   مسیر بادسواری یک خط راست بود، نه یک مسیر «هم‌سو با باد».
    #
    # دلیل تغییر: اندازه‌گیری روی صحنه نشان داد مسیر قبلی میانگین چرخش ۰.۰۴
    # درجه داشت، یعنی یک خط راست؛ و زاویهٔ *مسیر* با بادِ محلی حدود ۲۰ درجه بود
    # (زاویهٔ دریفت)، پس در هیچ نقطه‌ای موازی باد نبود.


@dataclass(frozen=True)
class WindRidingPlan:
    """نتیجهٔ برنامه‌ریزی بادسواری.

    پارامترها
    ----------
    altitude_m : float
        ارتفاع بادسواری (بالای زمین).
    heading_deg : float
        سمت هوایی مسیر. در حالت ``track_wind=False`` همان سمت ثابتی است که در
        تمام فاز بادسواری و فرود نگه داشته می‌شود؛ در حالت ``track_wind=True``
        سمت‌ها هر گام از مثلث باد می‌آیند و این عدد میانگین مسافت‌وزن آن‌ها است
        (سمت غالب پرواز).
    path : list[tuple[float, float]]
        مسیر روی زمین از مبدأ تا مقصد. طول آن یکی بیشتر از ``legs`` است.
    node_altitudes : list[float]
        ارتفاع AGL هر نقطه (متر): صفر در مبدأ، ``altitude_m`` در فاز بادسواری،
        کم‌شدن در فاز فرود و صفر روی مقصد.
    climb_time_hours, ride_time_hours, descent_time_hours, final_leg_hours : float
        تفکیک زمان پرواز به فازها.
    ride_distance_km, descent_distance_km : float
        مسافت روی زمین در فاز بادسواری و در فاز فرود.
    total_distance_km : float
        مسافت افقی کل (بادسواری + فرود + قطعهٔ پایانی).
    arrival_miss_km : float
        فاصلهٔ باقی‌مانده به مقصد *پس از* فرود (پیش از قطعهٔ پایانی).
    final_leg_km, final_bearing_deg : float
        طول و سمت قطعهٔ پایانی (صفر اگر فرود روی مقصد بیفتد).
    descent_slope_ratio : float
        شیب *واقعی* فرود «۱ به N» در همین برنامه (``مسافت فرود ÷ ارتفاع فرود``).
        این عدد با ``descent_glideslope_ratio`` یکی می‌شود مگر آنکه مسیر از
        همان ابتدا کوتاه‌تر از شیب خواسته‌شده باشد؛ در آن حالت از خود مسیر می‌آید.
    descent_power_fraction : float
        کسر توان کروز در فاز فرود، از توازن رانش همان شیب واقعی. برای شیب
        ملایم‌تر از گلاید بیشینه عددی بین دور آرام و ۱ است.
    """

    altitude_m: float
    heading_deg: float
    path: list[tuple[float, float]]
    node_altitudes: list[float]
    # کمترین فاصلهٔ عمودی از زمین در تمام مسیر (متر). ``None`` یعنی ارتفاع‌ها
    # نسبت به زمین‌اند و مسئلهٔ برخورد با زمین اصلاً مطرح نیست.
    min_terrain_clearance_m: float | None
    # ارتفاعی که واقعاً باید صعود شود: از زمین مبدأ تا سطح پرواز.
    climb_m: float
    climb_time_hours: float
    ride_time_hours: float
    descent_time_hours: float
    final_leg_hours: float
    ride_distance_km: float
    descent_distance_km: float
    descent_slope_ratio: float
    descent_power_fraction: float
    total_distance_km: float
    arrival_miss_km: float
    final_leg_km: float
    final_bearing_deg: float
    legs: list[LegSample] = field(default_factory=list)
    # کارنامهٔ هم‌راستایی همین برنامه (از ``pathfinding.alignment``).
    # ``aligned_share`` سهم مسافت با انحراف ≤۳ درجه از جهت باد است؛
    # ``parallel_mean_deg`` میانگین انحراف *در همان بخش*؛ و
    # ``final_correction_km`` مسافت از آخرین قطعهٔ موازی تا مقصد (یعنی «چند
    # کیلومتر آخر تصحیح شد»). این سه عدد همان چیزی است که در جدول گزارش می‌شود
    # و ادعای «بادسواری» را قابل حسابرسی می‌کند.
    aligned_share: float = 0.0
    parallel_mean_deg: float = math.nan
    final_correction_km: float = 0.0
    corridor_fraction: float = 0.0

    @property
    def wind_aligned_fraction(self) -> float:
        """سهم مسافت افقی که سمت مسیرش موازی جهت باد بود (۰ تا ۱).

        از خود قطعه‌های گزارش‌شده حساب می‌شود، پس «بادسواری» یک ادعا نیست:
        اگر مسیر با باد بجنگد، همین عدد نزدیک صفر می‌ماند.
        """
        total = sum(leg.distance_km for leg in self.legs)
        if total <= 0.0:
            return 0.0
        aligned = sum(
            leg.distance_km
            for leg in self.legs
            if _angle_between(
                leg.track_bearing_deg,
                (leg.wind_direction_from_deg + 180.0) % 360.0,
            )
            <= _ALIGNED_TOLERANCE_DEG
        )
        return aligned / total

    @property
    def total_time_hours(self) -> float:
        """زمان کل پرواز (ساعت): صعود + بادسواری + فرود + قطعهٔ پایانی."""
        return (
            self.climb_time_hours
            + self.ride_time_hours
            + self.descent_time_hours
            + self.final_leg_hours
        )


@dataclass(frozen=True)
class _Simulation:
    """مسیر روی زمین برای یک سمت فرمان (خروجی خام انتگرال‌گیری)."""

    heading_deg: float
    points: list[tuple[float, float]]
    altitudes: list[float]
    legs: list[LegSample]
    ride_km: float
    descent_km: float
    ride_hours: float
    descent_hours: float
    final_leg_km: float
    final_leg_hours: float
    final_bearing_deg: float
    miss_km: float
    min_terrain_clearance_m: float | None = None
    # شیب واقعی فرود (۱ به N) و کسر توان موتور در همان فاز. هر دو *خروجی* محاسبه
    # هستند نه ورودی: از نقطه‌ای که فرود شروع می‌شود و ارتفاعی که باید خرج شود
    # ساخته می‌شوند، پس نمایش و حسابداری از یک منبع می‌آیند.
    descent_slope_ratio: float = 0.0
    descent_power_fraction: float = 1.0
    # آيا کف زمین در فاز بادسواری با سقف صعود هواپیما قابل‌پرواز بود. ``False``
    # یعنی مسیر برای رد شدن از کوه به صعودی تندتر از توان هواپیما نیاز دارد، پس
    # این سطح «مسیر دارد» فقط روی کاغذ.
    terrain_climb_feasible: bool = True
    # مسافت *وزن‌داری* که سمت مسیر، موازی (در حد ``_ALIGNED_TOLERANCE_DEG``)
    # جهت خود باد بود. مبنای سنجهٔ ``wind_aligned_fraction`` است: «چند درصد از
    # مسیر واقعاً بادسواری بود؟» — یک عدد اندازه‌گیری‌شده، نه یک صفت.
    aligned_km: float = 0.0

    def flight_hours(self) -> float:
        """زمان پرواز بدون صعود اولیه (کروز + فرود + قطعهٔ پایانی).

        هنگام مقایسهٔ *سیاست‌ها* همین عدد ملاک است: صعود در مبدأ برای همهٔ
        سیاست‌ها یکی است، پس واردکردنش فقط نویز به مقایسه می‌آورد.
        """
        return self.ride_hours + self.descent_hours + self.final_leg_hours


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """آزیموت مسیر روی زمین بین دو نقطه (درجه، از شمال)."""
    return initial_bearing_deg(lat1, lon1, lat2, lon2)


def _approx_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """فاصلهٔ محلی با تصویر تخت (کیلومتر) — فقط برای *کنترل حلقهٔ انتگرال*.

    این تابع در حلقهٔ جست‌وجو صدها هزار بار صدا زده می‌شود؛ ``haversine_km``
    روی کره برای همین کار گران است. تمام اعدادی که *گزارش* می‌شوند (مسافت
    قطعات، مسافت کل، خطای رسیدن) در ``wind_riding_route_result`` با فاصلهٔ
    بزرگ‌دایره بازمحاسبه می‌شوند، پس این تقریب به خروجی راه پیدا نمی‌کند.
    """
    d_lat = (lat2 - lat1) * _KM_PER_DEG_LAT
    d_lon = (lon2 - lon1) * _KM_PER_DEG_LAT * math.cos(math.radians(lat1))
    return math.hypot(d_lat, d_lon)


def _wind_vector(speed_mps: float, direction_from_deg: float) -> tuple[float, float]:
    """بردار باد در محورهای (شرق، شمال) — جهتی که باد *به* آن می‌وزد."""
    to_rad = math.radians((direction_from_deg + 180.0) % 360.0)
    return speed_mps * math.sin(to_rad), speed_mps * math.cos(to_rad)


# آستانهٔ «موازی باد». ۱۵ درجه یعنی زاویهٔ بین سمت مسیر و جهت باد کمتر از ۱۵
# درجه باشد؛ با این آستانه «بادسواری» از «جنگیدن با باد» جدا می‌شود.
_ALIGNED_TOLERANCE_DEG = 15.0


def _angle_between(bearing_a_deg: float, bearing_b_deg: float) -> float:
    """کمترین زاویهٔ بین دو آزیموت (۰ تا ۱۸۰ درجه)."""
    difference = (bearing_a_deg - bearing_b_deg) % 360.0
    return difference if difference <= 180.0 else 360.0 - difference


def _solve_wind_triangle(
    track_bearing_deg: float,
    wind_east: float,
    wind_north: float,
    airspeed_mps: float,
) -> tuple[float, float, float] | None:
    """مثلث باد را برای «سمت مسیر خواسته‌شده» حل می‌کند.

    می‌خواهیم **سمت مسیر روی زمین** دقیقاً ``track_bearing_deg`` باشد، نه سمت
    فرمان. بردار سرعت زمینی ``G·û`` است (``û`` بردار یکهٔ آن سمت) و باد ``W``
    معلوم است، پس بردار سرعت هوایی ``A = G·û − W`` باید طولش ``V`` باشد:

        G² − 2G(W·û) + (|W|² − V²) = 0
        ⇒ G = (W·û) + √(V² − |W⊥|²)

    ریشهٔ مثبت انتخاب می‌شود (سرعت زمینی بیشتر). شرط وجود جواب ``V ≥ |W⊥|``
    است؛ یعنی باد جانبی نتواند بیشتر از سرعت هوایی باشد. این همان چیزی است که
    «جنگیدن با باد» را در مدل به یک عدد تبدیل می‌کند.

    برمی‌گرداند
    ----------
    (air_east, air_north, ground_speed) | None
        بردار سرعت هوایی و سرعت زمینی، یا ``None`` اگر این سمت مسیر با این باد
        و این سرعت هوایی قابل‌نگه‌داشتن نباشد.
    """
    to_rad = math.radians(track_bearing_deg)
    ux_east, ux_north = math.sin(to_rad), math.cos(to_rad)
    along = wind_east * ux_east + wind_north * ux_north
    wind_speed = math.hypot(wind_east, wind_north)
    cross_sq = max(wind_speed * wind_speed - along * along, 0.0)
    if cross_sq >= airspeed_mps * airspeed_mps:
        return None
    ground_speed = along + math.sqrt(airspeed_mps * airspeed_mps - cross_sq)
    if ground_speed <= 1e-6:
        return None
    air_east = ground_speed * ux_east - wind_east
    air_north = ground_speed * ux_north - wind_north
    return air_east, air_north, ground_speed


def _cross_track_km(
    origin: tuple[float, float],
    destination: tuple[float, float],
    lat: float,
    lon: float,
) -> float:
    """فاصلهٔ جانبی امضاشده از خط مستقیم مبدأ–مقصد (کیلومتر، مثبت = چپ مسیر)."""
    lat0 = math.radians(origin[0])
    scale = _KM_PER_DEG_LAT * math.cos(lat0)
    dir_east = (destination[1] - origin[1]) * scale
    dir_north = (destination[0] - origin[0]) * _KM_PER_DEG_LAT
    norm = math.hypot(dir_east, dir_north)
    if norm <= 1e-12:
        return 0.0
    dir_east, dir_north = dir_east / norm, dir_north / norm
    off_east = (lon - origin[1]) * math.cos(math.radians(lat)) * _KM_PER_DEG_LAT
    off_north = (lat - origin[0]) * _KM_PER_DEG_LAT
    # نرمال چپگرد بردار مسیر.
    return off_east * (-dir_north) + off_north * dir_east


def _heading_scan(step_deg: float) -> list[float]:
    """پویش درشت سمت فرمان روی ۳۶۰ درجه."""
    if step_deg <= 0.0:
        raise ValueError("heading_coarse_step_deg must be positive.")
    count = max(int(round(360.0 / step_deg)), 1)
    return [index * 360.0 / count for index in range(count)]


def _refine_scan(center_deg: float, span_deg: float, step_deg: float) -> list[float]:
    """سمت‌های اطراف ``center_deg`` در بازهٔ ±``span_deg`` با گام ``step_deg``.

    نقطهٔ مرکزی هم در فهرست می‌آید تا بهترین سمت مرحلهٔ قبل در مقایسهٔ همین
    مرحله هم بماند.
    """
    if step_deg <= 0.0:
        raise ValueError("heading refine steps must be positive.")
    count = max(int(round(2.0 * span_deg / step_deg)), 1)
    return [((center_deg - span_deg) + index * step_deg) % 360.0 for index in range(count + 1)]


def _simulate_heading(
    origin: tuple[float, float],
    destination: tuple[float, float],
    sampler: WindSampler,
    descent_sampler: WindSampler,
    heading_deg: float,
    *,
    altitude_m: float,
    airspeed_mps: float,
    glide_ratio: float,
    glide_power_fraction: float,
    config: WindRidingConfig,
    descent_ratio: float = 40.0,
    approach_km: float = 3.0,
    ground_end_m: float = 0.0,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    clearance_floor_m: float = 0.0,
    track_wind: bool = False,
    sampler_for_altitude: Callable[[float], WindSampler] | None = None,
    max_climb_gradient: float | None = None,
) -> _Simulation:
    """یک سمت فرمان را از مبدأ انتگرال می‌گیرد تا فرود و بستن باقی‌مانده.

    فازها و **نقش گرانش**
    -------------------
    ۱) صعود در مبدأ تا ارتفاع لایه (موتور).
    ۲) بادسواری در ارتفاع ثابت: یک سمت فرمان، باد هواپیما را ارمغان می‌برد.
    ۳) فرود **شیب‌دار ملایم**: وقتی فاصلهٔ باقی‌مانده برابر ``h · descent_ratio``
       شود، فرود روی همان شیب ثابت شروع می‌شود و ارتفاع مو‌به‌مو با فاصلهٔ
       باقی‌مانده کم می‌شود تا صفر روی مقصد.

    پیش‌تر فاز سوم یک *گلاید بیشینه* بود: از ``h · L/D`` شروع می‌شد و در ۶ کیلومتر
    آخر ارتفاع می‌گرفت. آن نسخه از نظر سوخت بی‌نقص بود ولی در صحنه مثل یک
    شیرجه دیده می‌شد و به کاربر چیزی «تدریجی» نمی‌نمود. حالا شیب فرود یک سیاست
    است: ملایم‌تر از گلاید بیشینه، با توان جزئی موتور، و همان توان هم از توازن
    رانش حساب می‌شود — پس «تدریجی‌تر» به معنی «رایگان‌تر» نیست، فقط توزیع‌یافته‌تر
    است.
    """
    # بُرد گلاید (کیلومتر): از سطح پرواز *تا ارتفاع زمین مقصد*، نه تا سطح دریا،
    # برای همان ارتفاعی که واقعاً باید کم شود. اگر سطح دریا مبنا بماند، بُرد بیش
    # از حد طول می‌کشد و هواپیما پیش از مقصد ارتفاعش را تمام می‌کند.
    height_to_lose_m = max(altitude_m - ground_end_m, 0.0)
    # مسافت *افقی* فرود روی شیب سیاست‌گذاری‌شده (``h · ratio``). فرود از همان
    # نقطه‌ای شروع می‌شود که این مسافت با فاصلهٔ باقی‌مانده برابر شود.
    descent_span_km = height_to_lose_m * descent_ratio / 1000.0
    heading_rad = math.radians(heading_deg)
    air_east = airspeed_mps * math.sin(heading_rad)
    air_north = airspeed_mps * math.cos(heading_rad)
    # سمت فرمانی که *واقعاً* در گام جاری به کار می‌رود. در حالت دنبال‌کردن
    # باد، هر گام سمت خودش را دارد (مثلث باد) و همین عدد در پروندهٔ سوخت
    # «تعداد تصحیح مسیر با موتور» را می‌سازد؛ در حالت سمت ثابت، همان ورودی است.
    current_heading = heading_deg
    # سمت مسیر خواسته‌شده نسبت به باد: ۰ = کاملاً موازی باد، ۹۰ = عمود بر باد.
    # به‌صورت مسافت وزن‌دار جمع می‌شود تا «چه سهمی از مسیر موازی باد بود»
    # اندازه‌گیری شود، نه ادعا.
    aligned_km = 0.0

    lat, lon = origin
    points: list[tuple[float, float]] = [(lat, lon)]
    # پروفیل ارتفاع نمایشی: با مدل زمین، ارتفاع‌ها **مطلق**‌اند و مبدأ/مقصد روی
    # زمین خودشان می‌نشینند؛ بدون مدل زمین، همان ۰ تا ارتفاع لایه قبلی است.
    altitudes: list[float] = [_terrain_height(origin, ground_elevation_at)]
    legs: list[LegSample] = []
    ride_km = 0.0
    descent_km = 0.0
    ride_hours = 0.0
    descent_hours = 0.0
    descending = False
    # مسافت باقی‌مانده در لحظهٔ شروع فرود (کیلومتر). تا وقتی فرود شروع نشده
    # صفر می‌ماند؛ بعد از آن مبنای شيب فرود است.
    descent_start_km = 0.0
    # کسر توان موتور در فاز فرود، از توازن رانش *همان قطعه*. هر قطعه جداگانه
    # حساب می‌شود و نه یک‌بار برای کل فرود: پروفیل فرود می‌تواند به‌خاطر کف
    # فاصله از زمین تکه‌تکه شود و شیب هر تکه فرق کند.
    descent_power = glide_power_fraction
    # ارتفاع مطلق هواپیما (متر). در فاز بادسواری برابر سطح پرواز، و در فاز فرود
    # روی گلایدش سوار است. پیش از ورود به حلقه مقدار می‌گیرد چون انتخاب بادِ
    # «همین ارتفاع» در گام اول به آن نیاز دارد.
    agl_now = altitude_m
    # پاسخ «آیا کل مسیر قابل‌پرواز است؟». در فاز بادسواری به‌روز می‌شود و در
    # ``_Simulation`` گزارش می‌شود تا برنامه‌ریز سطح ناممکن را رد کند.
    terrain_climb_ok = True
    time_s = 0.0
    window_s = 0.0
    last_point = (lat, lon)
    # باد پنجرهٔ جاری از همان نقطهٔ فعلی خوانده می‌شود، نه صفر. بدون این
    # مقدارگذاری، پنجرهٔ *اول* جهت باد صفر گزارش می‌کرد و سنجهٔ «چند درصد مسیر
    # موازی باد بود» از همان‌جا غلط می‌شد.
    window_speed, window_direction = sampler(lat, lon)
    min_clearance: float | None = None if ground_elevation_at is None else math.inf

    def close_window(new_lat: float, new_lon: float, agl_now: float) -> None:
        """پنجرهٔ نمونه‌برداری جاری را به یک قطعه/نقطه تبدیل می‌کند."""
        nonlocal window_s, last_point, window_speed, window_direction
        nonlocal aligned_km
        segment_km = _approx_km(last_point[0], last_point[1], new_lat, new_lon)
        if segment_km <= 1e-9:
            window_s = 0.0
            return
        track_now = _bearing(last_point[0], last_point[1], new_lat, new_lon)
        if _angle_between(track_now, (window_direction + 180.0) % 360.0) <= _ALIGNED_TOLERANCE_DEG:
            aligned_km += segment_km
        legs.append(
            LegSample(
                track_bearing_deg=track_now,
                wind_speed_mps=window_speed,
                wind_direction_from_deg=window_direction,
                distance_km=segment_km,
                time_hours=window_s / 3600.0,
                # فرمانِ خودِ برنامه‌ریز در این قطعه. در حالت سمت ثابت، عددی است
                # که همهٔ قطعه‌های بادسواری و فرود با آن پرواز می‌شوند؛ در حالت
                # دنبال‌کردن باد، از مثلث باد همان گام می‌آید و همین است که
                # تغییر سمت و بهای سوخت تصحیح‌ها را واقعی می‌کند.
                air_heading_deg=current_heading,
                # در فاز فرود بخشی از رانش از گرانش می‌آید، پس سوخت این مسافت
                # کمتر از کروز است؛ مدل سوخت همین کسر را می‌بیند.
                power_fraction=(
                    min(
                        max(
                            1.0 - glide_ratio * _sink_sine(altitudes[-1], agl_now, segment_km),
                            glide_power_fraction,
                        ),
                        1.0,
                    )
                    if descending
                    else 1.0
                ),
            )
        )
        points.append((new_lat, new_lon))
        altitudes.append(agl_now)
        last_point = (new_lat, new_lon)
        window_s = 0.0

    max_seconds = config.max_hours * 3600.0
    closest_remaining = math.inf
    while time_s < max_seconds:
        remaining = _approx_km(lat, lon, destination[0], destination[1])
        if remaining <= config.arrival_radius_km:
            break
        if remaining < closest_remaining:
            closest_remaining = remaining
        elif remaining > closest_remaining + config.abandon_margin_km:
            # این سمت مقصد را دور می‌زند؛ ادامه‌دادن فقط جست‌وجو را کند می‌کند.
            break

        # **باد در ارتفاع *واقعی* هواپیما.** اگر پروفیل عمودی داده شده باشد، باد
        # از لایه‌ای خوانده می‌شود که هواپیما همین حالا در آن است — نه از لایهٔ
        # کروز. همین است که «صعود کن تا در بادی بیفتی که تو را می‌برد» را واقعی
        # می‌کند: با بالا رفتن از رشته‌کوه، بادِ همان ارتفاع (که راست‌تر چرخیده)
        # خودش وارد مسئله می‌شود. بدون پروفیل، همان نمونه‌بردار ثابت قبلی.
        if sampler_for_altitude is None:
            sampler_now = descent_sampler if descending else sampler
        else:
            sampler_now = sampler_for_altitude(agl_now)
        speed, direction = sampler_now(lat, lon)
        wind_east, wind_north = _wind_vector(speed, direction)
        if track_wind:
            # **دنبال‌کردن باد، با دالان همگرا.**
            #
            # سمت *پیش‌فرض* همان جهت خود باد است (موازی پیکان‌ها). ولی باد این
            # کریدور به سمت مقصد نمی‌وزد؛ هرچه جلوتر می‌رویم باد به راست
            # می‌چرخد، پس «موازی باد رفتن» به‌تنهایی هواپیما را از کنار مقصد
            # می‌گذراند. پس زاویهٔ مسیر در *یک بازه* انتخاب می‌شود:
            #
            #     زاویهٔ مسیر نسبت به «مستقیم به مقصد» را ``δ`` بگیریم. با مسافت
            #     باقی‌ماندهٔ ``R`` و انحراف جانبی کنونی ``x``، انحراف پایانی
            #     می‌شود ``x − R·sin δ`` (علامت منفی از این می‌آید که افزایش
            #     آزیموت در دستگاه شرق–شمال به سمت *راست* می‌چرخد). اگر بخواهیم
            #     اندازهٔ همین عدد از دالان ``±b`` بیرون نزند:
            #
            #         δ ∈ [asin((x − b)/R)، asin((x + b)/R)]
            #
            # و ``δ`` انتخابی همان جهت *خود باد* است اگر داخل این بازه باشد،
            # وگرنه نزدیک‌ترین سر بازه. یعنی «تا جایی که ممکن است موازی باد، و
            # از آن به بعد کمترین تصحیح لازم» — نه یک نبرد مداوم با باد.
            #
            # دالان ``b`` نسبت به مسافت باقی‌مانده کوچک می‌شود
            # (``wind_corridor_fraction``)، پس در چند کیلومتر آخر بازه به صفر
            # می‌رسد و هواپیما روی مقصد می‌نشیند. همین چند درجه کج‌شدن هم پسار
            # القایی و باد رو-به-رو را در مدل سوخت فعال می‌کند. با باد ثابت و
            # ۸.۲ درجه اختلاف، این کنترل تا ۱۱۲ کیلومتر *کاملاً* موازی باد
            # می‌رود و بقیه را تصحیح می‌کند؛ مسافت کل ۱۷۵ کیلومتر می‌شود، یعنی
            # فقط ۲ کیلومتر بیشتر از خط مستقیم.
            direct_bearing = _bearing(lat, lon, destination[0], destination[1])
            cross_track = _cross_track_km(origin, destination, lat, lon)
            wind_magnitude = math.hypot(wind_east, wind_north)
            if wind_magnitude <= 1e-9:
                # **هواي آرام ≠ «موازي باد نامعلوم».** با باد صفر جهت باد وجود
                # ندارد و ``atan2(0, 0)`` یک عدد دلبخواه برمی‌گرداند (شمال).
                # در این حالت تنها سمت مسیر قابل‌دفاع، همان ستمی است که انحراف
                # جانبی را صفر می‌کند — یعنی مستقیم به مقصد.
                deviation = math.degrees(
                    math.asin(min(max(cross_track / remaining, -1.0), 1.0))
                )
            else:
                wind_track = math.degrees(math.atan2(wind_east, wind_north)) % 360.0
                deviation = ((wind_track - direct_bearing + 180.0) % 360.0) - 180.0
            budget = max(
                config.wind_corridor_min_km,
                config.wind_corridor_fraction * remaining,
            )
            safe_remaining = max(remaining, 1e-9)
            lowest = math.degrees(
                math.asin(min(max((cross_track - budget) / safe_remaining, -1.0), 1.0))
            )
            highest = math.degrees(
                math.asin(min(max((cross_track + budget) / safe_remaining, -1.0), 1.0))
            )
            desired_bearing = direct_bearing + min(max(deviation, lowest), highest)
            desired_track = desired_bearing % 360.0
            solution = _solve_wind_triangle(
                desired_track, wind_east, wind_north, airspeed_mps
            )
            if solution is None:
                # باد جانبی از سرعت هوایی بیشتر است: این سمت مسیر قابل‌نگه‌داشتن
                # نیست. به همان «رو به مقصد» می‌افتیم؛ اگر آن هم نشد، مسیری با
                # این باد و این سرعت هوایی برای این مقصد وجود ندارد.
                solution = _solve_wind_triangle(
                    direct_bearing, wind_east, wind_north, airspeed_mps
                )
                if solution is None:
                    break
                desired_track = direct_bearing
            air_east, air_north, ground_speed = solution
            v_east = ground_speed * math.sin(math.radians(desired_track))
            v_north = ground_speed * math.cos(math.radians(desired_track))
            current_heading = math.degrees(math.atan2(air_east, air_north)) % 360.0
        else:
            v_east = air_east + wind_east
            v_north = air_north + wind_north
            ground_speed = math.hypot(v_east, v_north)
            current_heading = heading_deg
        if ground_speed <= 1e-6:
            break

        dt = config.step_s
        if not descending and remaining <= descent_span_km:
            # مرز بادسواری/فرود *همین‌جا* بسته می‌شود. وگرنه پنجرهٔ نمونه‌برداری
            # جاری (تا ۲ دقیقه پرواز کروز) به فاز فرود نسبت داده می‌شد و
            # مسافت/سرعت هر دو فاز غلط گزارش می‌شد.
            before = last_point
            close_window(lat, lon, altitude_m)
            if last_point != before:
                ride_km += _approx_km(before[0], before[1], lat, lon)
            # شروع فرود یک *رخداد زمانی* است، نه تصحیح سمت: با یک گام کوتاه
            # دقیقاً به نقطهٔ شروع فرود می‌رسیم و سمت فرمان عوض نمی‌شود.
            descending = True
            # شیب *واقعی* از همین نقطه ساخته می‌شود: ارتفاع تابع خطی فاصلهٔ
            # باقی‌مانده است، پس هواپیما مو‌به‌مو روی مقصد می‌نشیند و خطای گامِ
            # شروع فرود به مقصد منتقل نمی‌شود.
            descent_start_km = max(remaining, 1e-6)
            # کسر توان موتور در فرود از توازن رانش می‌آید، نه از یک عدد دلبخواه:
            # ``T = D − m·g·sinγ`` و ``D = m·g/(L/D)`` ⇒ ``T/D = 1 − (L/D)·sinγ``.
            # شیب ۱ به ۴۰ با L/D = ۱۲ یعنی ۰.۷ توان کروز — نه دور آرام. دور آرام
            # *کف* کار است: هر وقت شیبِ لازم از گلاید بیشینه تندتر شود (مسیر کوتاه
            # یا فرود دیرهنگام)، گرانش تنها منبع رانش می‌شود.
            descent_power = min(
                max(
                    1.0
                    - glide_ratio
                    * _sink_sine(altitude_m, altitude_m - height_to_lose_m, descent_start_km),
                    glide_power_fraction,
                ),
                1.0,
            )

        lat += (v_north * dt) / (_KM_PER_DEG_LAT * 1000.0)
        lon += (v_east * dt) / (_KM_PER_DEG_LAT * 1000.0 * math.cos(math.radians(lat)))
        time_s += dt
        window_s += dt

        if descending:
            descent_hours += dt / 3600.0
            # شيب گلاید: ارتفاع متناسب با مسافت باقی‌مانده کم می‌شود، پس هواپیما
            # *همزمان* با رسیدن به مقصد به ارتفاع زمین مقصد می‌رسد. شيب همان
            # ۱/(L/D) است — گلاید با موتور دور آرام، نه فرود توان‌دار.
            left_km = _approx_km(lat, lon, destination[0], destination[1])
            agl_now = ground_end_m + max(
                height_to_lose_m * min(left_km / descent_start_km, 1.0), 0.0
            )
            # **کف زمین.** یک فرود ملایم که از ۱۰۰ کیلومتر قبل شروع شود، در
            # ارتفاع پایین‌تر به کوه می‌رسد. بادسواری نباید از داخل کوه رد شود،
            # پس پروفیل سیاست‌گذاری‌شده در فراز *کوه* بالا نگه داشته می‌شود.
            # در تقرب پایانی این کف به ارتفاع زمین مقصد می‌رسد (``approach_km``)،
            # وگرنه هواپیما هرگز نمی‌توانست بنشیند.
            if ground_elevation_at is not None and clearance_floor_m > 0.0:
                fade = min(left_km / approach_km, 1.0)
                floor_msl = (
                    float(ground_elevation_at(lat, lon)) + clearance_floor_m * fade
                )
                agl_now = max(agl_now, floor_msl)
        else:
            ride_hours += dt / 3600.0
            agl_now = altitude_m
            # **کف زمین در فاز بادسواری.** این کریدور رشته‌کوهی تا ۳۱۷۵ متر دارد؛
            # سطح پرواز ۱۵۰۰ یا ۲۲۰۰ متری از قله پایین‌تر است، پس کروز تراز
            # یعنی پرواز از داخل کوه. هواپیما ناچار *بالا می‌رود* تا از زمین رد
            # شود — و همان صعود، ارتفاعش را عوض می‌کند و از این‌جا به بعد بادِ
            # همان ارتفاع تازه خوانده می‌شود (به ``sampler_for_altitude`` نگاه
            # کنید). این تنها جای مسئله است که دو مدل به هم تکیه می‌کنند و هر دو
            # جا عدد یکسان (``clearance_floor_m`` گراف) به کار می‌رود.
            if ground_elevation_at is not None and clearance_floor_m > 0.0:
                floor_msl = float(ground_elevation_at(lat, lon)) + clearance_floor_m
                # **آیا این صعود را می‌تواند انجام دهد؟** کف زمین می‌تواند بالاتر از
                # سطح کروز بیفتد (یال کوه). اگر همان کف را تحمیل کنیم، هواپیما در
                # یک لحظه جهش می‌کند — یک صعود با شیب بینهایت که فقط روی کاغذ کار
                # می‌کند. پس *صعود لازم برای رسیدن به کف* با سقف شیب هواپیما سنجیده
                # می‌شود و اگر از آن بگذرد، این سطح قابل‌پرواز نیست: همان کاری که
                # گراف با حذف گره‌های زیر آستانه می‌کند. نتیجه برای این کریدور این
                # است که سطح ۱۵۰۰ تا ۲۹۰۰ متری برای بادسواری رد می‌شود (یال تا ۳۱۷۵
                # متر بالا می‌رود) و بادسواری فقط در بالاترین سطح مسیر دارد.
                if floor_msl > agl_now:
                    rise = floor_msl - agl_now
                    allowed = (
                        None
                        if max_climb_gradient is None
                        else max_climb_gradient * (ground_speed * dt / 1000.0)
                    )
                    if allowed is not None and rise > allowed + 1e-9:
                        terrain_climb_ok = False
                    agl_now = floor_msl

        # فاصله از زمین در **همین گام**. این‌جا و نه در نقطه‌های نمونه‌برداری
        # سنجیده می‌شود: نمونه‌برداری هر ۲ دقیقه (≈۲.۵ کیلومتر) است و یک
        # یال باریک کوه می‌تواند دقیقاً بین دو نمونه بیفتد.
        # آستانهٔ سنجش فاصله از زمین فقط **بیرون از تقرب پایانی** اعمال می‌شود.
        # در تقرب پایانی هواپیما *باید* به زمین برسد، پس اگر نقطهٔ نشستن هم در
        # آمار بیاید کمترین فاصله از زمین همیشه صفر می‌شود و سنجهٔ ایمنی
        # بی‌معنا. «تقرب پایانی» با **مسافت** تعریف می‌شود، نه با ارتفاع: تعریف
        # ارتفاعی روی کوه اشتباه می‌کرد — اگر زمین زیر مسیر چند صد متر بالاتر از
        # زمین مقصد باشد، هواپیما در تقرب پایانی هنوز بالای آستانهٔ ارتفاعی است
        # و همان چند متر کاهش یافته به‌عنوان «نقض ایمنی» شمرده می‌شد، درحالی‌که
        # هیچ کار دیگری نمی‌شد کرد. مسافت، همان تعریفی است که کف زمین هم با آن
        # ساخته می‌شود (``approach_km``).
        if (
            min_clearance is not None
            and ground_elevation_at is not None
            and _approx_km(lat, lon, destination[0], destination[1]) > approach_km
        ):
            clearance_now = agl_now - float(ground_elevation_at(lat, lon))
            if clearance_now < min_clearance:
                min_clearance = clearance_now

        # نمونه‌برداری: هر ``path_sample_s`` (و در فاز فرود در هر گام، تا
        # پروفیل ارتفاع دقیق بماند).
        if window_s >= config.path_sample_s or descending:
            before = last_point
            close_window(lat, lon, agl_now)
            if last_point != before:
                segment_km = _approx_km(before[0], before[1], lat, lon)
                if descending:
                    descent_km += segment_km
                else:
                    ride_km += segment_km
                window_speed, window_direction = speed, direction


    # قطعهٔ پایانی: باقی‌ماندهٔ مستقیم به مقصد (اگر بیرون شعاع رسیدن باشیم).
    miss_km = haversine_km(lat, lon, destination[0], destination[1])
    final_bearing = _bearing(lat, lon, destination[0], destination[1])

    final_leg_km = 0.0
    final_leg_hours = 0.0
    if miss_km > config.arrival_radius_km:
        speed, direction = descent_sampler(lat, lon)
        wind_east, wind_north = _wind_vector(speed, direction)
        trail = math.radians(final_bearing)
        v_east = airspeed_mps * math.sin(trail) + wind_east
        v_north = airspeed_mps * math.cos(trail) + wind_north
        ground_speed = max(math.hypot(v_east, v_north), 1e-6)
        final_leg_km = miss_km
        final_leg_hours = miss_km / (ground_speed * 3.6)
        legs.append(
            LegSample(
                track_bearing_deg=final_bearing,
                wind_speed_mps=speed,
                wind_direction_from_deg=direction,
                distance_km=miss_km,
                time_hours=final_leg_hours,
            )
        )
    # اگر هواپیما همین حالا داخل شعاع رسیدن است، نقطهٔ آخر *با* مقصد جایگزین
    # می‌شود؛ اضافه‌کردن مقصد یک قطعهٔ کوتاهِ رو‌به‌عقب می‌سازد.
    #
    # چرا این مهم است: حلقه وقتی می‌شکند که فاصله به مقصد از شعاع رسیدن کمتر
    # شود، و آن لحظه *قبل* از گام بعدی سنجیده می‌شود، پس نقطهٔ پایانی می‌تواند
    # چند صد متر از مقصد گذشته باشد (یک گام ۲۰ ثانیه‌ای حدود ۰.۶ کیلومتر است).
    # مقصدی که بعد از آن نقطه اضافه شود، انتهای مسیر را روی خودش برمی‌گرداند و
    # همان پیچِ کوچک در پروفیل رسم‌شده به شکل یک «افتِ تیز» درست روی مقصد دیده
    # می‌شود — چیزی که هیچ هواپیمایی انجام نمی‌دهد. جایگزینی، هندسه را با فیزیک
    # یکی می‌کند: آخرین قطعه همان قطعهٔ مستقیم نهایی به مقصد می‌شود.
    if len(points) > 1 and miss_km <= config.arrival_radius_km:
        points[-1] = destination
        altitudes[-1] = ground_end_m
    else:
        points.append(destination)
        altitudes.append(ground_end_m)

    return _Simulation(
        heading_deg=heading_deg,
        points=points,
        altitudes=altitudes,
        legs=legs,
        aligned_km=aligned_km,
        terrain_climb_feasible=terrain_climb_ok,
        min_terrain_clearance_m=min_clearance,
        ride_km=ride_km,
        descent_km=descent_km,
        ride_hours=ride_hours,
        descent_hours=descent_hours,
        final_leg_km=final_leg_km,
        final_leg_hours=final_leg_hours,
        final_bearing_deg=final_bearing,
        miss_km=miss_km,
        # شیب *واقعی* فرود (۱ به N) از مسافت طی‌شده می‌آید، نه از سیاست: اگر کف
        # زمین وسط راه بخشی از فرود را بالا نگه داشته باشد، میانگین شیب تند‌تر
        # از ۱ به ``descent_ratio`` می‌شود و همین عدد باید گزارش شود. توان فرود
        # هم از توازن رانش *همین* شیب میانگین می‌آید تا دو ستون جدول با هم یکی
        # باشند — نه اینکه یک ستون سیاست را بگوید و دیگری هندسهٔ واقعی را.
        descent_slope_ratio=(
            descent_km * 1000.0 / height_to_lose_m if height_to_lose_m > 0.0 else 0.0
        ),
        descent_power_fraction=(
            min(
                max(
                    1.0 - glide_ratio * _sink_sine(height_to_lose_m, 0.0, descent_km),
                    glide_power_fraction,
                ),
                1.0,
            )
            if descent_km > 0.0 and height_to_lose_m > 0.0
            else descent_power
        ),
    )


def _sink_sine(from_alt_m: float, to_alt_m: float, run_km: float) -> float:
    """``sin`` زاویهٔ فرود یک قطعه از کم‌کردن ارتفاع و مسافت افقی همان قطعه.

    زاویهٔ فرود یک قطعهٔ فرود است، نه یک خاصیت ثابت مسیر: با کف فاصله از زمین،
    یک فرود می‌تواند تکه‌های ملایم و تند داشته باشد و توان موتور هر تکه باید از
    شیب *همان تکه* بیاید — وگرنه سوخت کل مسیر از شیب میانگین حساب می‌شد.
    """
    run_m = max(run_km * 1000.0, 1e-9)
    drop_m = max(from_alt_m - to_alt_m, 0.0)
    return drop_m / math.hypot(drop_m, run_m)


def _terrain_height(
    point: tuple[float, float],
    elevation_at: Callable[[float, float], float] | None,
) -> float:
    """ارتفاع زمین زیر یک نقطه (متر) — صفر اگر مدل زمین داده نشده باشد."""
    if elevation_at is None:
        return 0.0
    return float(elevation_at(point[0], point[1]))


def plan_wind_riding_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    layers: Sequence[tuple[float, WindSampler]],
    *,
    aircraft: CostModelConfig | None = None,
    vertical: VerticalCostConfig | None = None,
    effort: MotorEffortConfig | None = None,
    config: WindRidingConfig | None = None,            ground_elevation_at: Callable[[float, float], float] | None = None,
            min_clearance_m: float = 0.0,
            cruise_altitudes: Sequence[float] | None = None,
) -> WindRidingPlan | None:
    """بهترین مسیر بادسواری را برای یک مبدأ/مقصد پیدا می‌کند.

    برای هر لایه، بهترین سمت فرمان با پویش درشت + ریزکردن جست‌وجو می‌شود؛ سپس
    برنامه‌ای انتخاب می‌شود که در میان برنامه‌های قابل‌قبول (خطای رسیدن کمتر از
    ``config.max_arrival_miss_km``) کمترین زمان کل را داشته باشد.

    پارامترها
    ----------
    origin, destination : tuple[float, float]
        مختصات (عرض، طول).
    layers : Sequence[tuple[float, WindSampler]]
        جفت‌های (ارتفاع AGL، نمونه‌بردار باد همان لایه). میدان باد از سمت صحنه
        (``viz.wind_field``) ساخته و این‌جا تزریق می‌شود تا این ماژول به لایه
        نمایش وابسته نباشد. این فهرست **پروفیل عمودی** هواپیما است: باد در هر
        لحظه از لایه‌ای خوانده می‌شود که هواپیما واقعاً در آن ارتفاع است.
    cruise_altitudes : Sequence[float], اختیاری
        ارتفاع‌های کروزی که باید جست‌وجو شوند. پیش‌فرض، همان ارتفاع‌های
        ``layers``. جدا کردن این دو یعنی می‌توان کارنامهٔ یک سطح را خواست در
        حالی که هواپیما اجازه دارد برای رد شدن از کوه به سطح باالتر برود.
    aircraft : CostModelConfig, اختیاری
        مشخصات هواپیما (فقط ``airspeed_mps``).
    vertical : VerticalCostConfig, اختیاری
        نرخ صعود؛ زمان صعود = ارتفاع/نرخ صعود — همان فرض یال‌های عمودی گراف.
        (نرخ فرود این‌جا دیگر تعیین‌کننده نیست: شيب فرود از بُرد گلاید می‌آید.)
    effort : MotorEffortConfig, اختیاری
        فرض‌های مدل سوخت. **تنها منبع حقیقت برای دو عدد فیزیکی** است که این
        برنامه‌ریز لازم دارد: نسبت برآر به پسار (``lift_to_drag``) که با آن سهم
        گرانش در رانش فرود حساب می‌شود، و کسر توان دور آرام
        (``descent_idle_power_fraction``) که *کف* توان در فاز فرود است. شکل خودِ
        فرود (شیبش) از ``WindRidingConfig.descent_glideslope_ratio`` می‌آید.
    config : WindRidingConfig, اختیاری
        پارامترهای عددی جست‌وجو.
    ground_elevation_at : Callable, اختیاری
        ``(lat, lon) -> elevation_m``. اگر داده شود، ``layers`` **سطح پرواز
        مطلق** تفسیر می‌شود: صعود از ارتفاع زمین مبدأ حساب می‌شود، بُرد گلاید
        تا ارتفاع زمین مقصد است، و مسیری که از داخل کوه بگذرد رد می‌شود.
        اگر ``None`` باشد، همان معنای «بالای زمین» قبلی حفظ می‌شود.
    min_clearance_m : float
        کمترین فاصلهٔ مجاز عمودی با زمین (متر) — همان آستانهٔ گراف.

    برمی‌گرداند
    ----------
    WindRidingPlan | None
        بهترین برنامه، یا ``None`` اگر هیچ لایه/سمتی به مقصد (در حد خطای مجاز)
        نرسد.
    """
    settings = config or WindRidingConfig()
    plane = aircraft or CostModelConfig()
    verticals = vertical or VerticalCostConfig()
    effort_settings = effort or MotorEffortConfig()
    if not layers:
        raise ValueError("layers cannot be empty.")

    # پروفیل عمودی به ترتیب ارتفاع. نمونه‌بردارِ هر ارتفاع، لایه‌ای است که
    # آن ارتفاع یا پایین‌ترش را می‌پوشاند (و اگر زیر همه بود، پایین‌ترین لایه).
    profile = sorted(layers, key=lambda item: item[0])
    descent_sampler = profile[0][1]
    best_plan: WindRidingPlan | None = None
    descent_ratio = settings.descent_glideslope_ratio

    def sampler_at(altitude_m: float) -> WindSampler:
        """نمونه‌بردار باد در یک ارتفاع دلخواه (پله‌ای روی لایه‌های معلوم)."""
        chosen = profile[0][1]
        for level_altitude, level_sampler in profile:
            if level_altitude <= altitude_m + 1e-9:
                chosen = level_sampler
        return chosen

    # ارتفاع زمین در مبدأ/مقصد و در طول مسیر. بدون نمونه‌بردار زمین، همهٔ
    # ارتفاع‌ها نسبت به زمین‌اند (همان رفتار قبلی) و کاری با برخورد با زمین
    # نداریم؛ با آن، سطح پرواز مطلق می‌شود و برخورد با قله یک پرسش واقعی است.
    ground_start = _terrain_height(origin, ground_elevation_at)
    ground_end = _terrain_height(destination, ground_elevation_at)
    targets = (
        list(cruise_altitudes)
        if cruise_altitudes is not None
        else [level_altitude for level_altitude, _sampler in profile]
    )

    for altitude_m in targets:
        sampler = sampler_at(altitude_m)
        # صعود = اختلاف *سطح پرواز* با زمین زیر مبدأ، نه ارتفاع پرواز از صفر.
        climb_m = max(altitude_m - ground_start, 0.0)
        climb_hours = climb_m / verticals.climb_rate_mps / 3600.0

        def simulate(
            heading_deg: float,
            sampler: WindSampler = sampler,
            altitude_m: float = altitude_m,
            policy: WindRidingConfig = settings,
        ) -> _Simulation:
            """سمت را در همین لایه شبیه‌سازی می‌کند (پیش‌فرض‌ها دور متغیر گره می‌بندند).

            ``policy`` همان سیاستی است که در *این* فراخوانی آزموده می‌شود: زمانی
            که روی دالان بادسواری جست‌وجو می‌کنیم، هر دالان یک سیاست جداگانه است.
            """
            return _simulate_heading(
                origin,
                destination,
                sampler,
                descent_sampler,
                heading_deg,
                altitude_m=altitude_m,
                airspeed_mps=plane.airspeed_mps,
                glide_ratio=effort_settings.lift_to_drag,
                glide_power_fraction=effort_settings.descent_idle_power_fraction,
                config=policy,
                descent_ratio=descent_ratio,
                approach_km=settings.approach_km,
                ground_end_m=ground_end,
                ground_elevation_at=ground_elevation_at,
                clearance_floor_m=min_clearance_m,
                track_wind=settings.track_wind,
                sampler_for_altitude=sampler_at,
                # سقف شیب صعود (متر بر کیلومتر) = نرخ صعود ÷ سرعت زمینی. همان
                # عددی که ``VerticalCostConfig`` به گراف می‌دهد، پس دو مدل
                # «صعود ممکن» را با یک معیار می‌سنجند.
                max_climb_gradient=verticals.climb_rate_mps
                / max(plane.airspeed_mps, 1e-6)
                * 1000.0,
            )

        # کش جدا برای هر دالان: یک سمت فرمان زیر یک *سیاست* همیشه یک نتیجه
        # می‌دهد، ولی از یک دالان به دالان دیگر نتیجه فرق می‌کند، پس کش مشترک
        # غلط می‌شود.
        caches: dict[float, dict[float, _Simulation]] = {}

        def simulation(
            heading_deg: float,
            fraction: float,
            caches: dict[float, dict[float, _Simulation]] = caches,
        ) -> _Simulation:
            """شبیه‌سازی یک سمت زیر یک دالان مشخص، با کش.

            ``caches`` به‌عنوان آرگومان پیش‌فرض بسته می‌شود تا حلقهٔ سطوح پرواز
            یک دیکشنری *تازه* به هر تکرار بدهد (بستن متغیر حلقه خطای خاموش
            «کش مشترک بین سطوح» می‌سازد).
            """
            cache = caches.setdefault(round(fraction, 6), {})
            key = round(heading_deg % 360.0, 6)
            result = cache.get(key)
            if result is None:
                policy = (
                    settings
                    if math.isclose(fraction, settings.wind_corridor_fraction)
                    else dataclasses.replace(settings, wind_corridor_fraction=fraction)
                )
                result = simulate(heading_deg, policy=policy)
                cache[key] = result
            return result

        def rank(sim: _Simulation) -> tuple[float, float]:
            """رتبهٔ یک شبیه‌سازی در پویش سمت: اول کمترین خطای رسیدن، بعد کمترین زمان.

            ترتیب مهم است: پویش برای *رسیدن* انجام می‌شود و ریزکردن حول نامزدی
            ادامه می‌یابد که به مقصد نزدیک‌تر است. اگر اول زمان بیاید، پویش حول
            یک سمتِ سریعِ دورافتاده متمرکز می‌شود و سمت درست‌رسانده هرگز دیده
            نمی‌شود.
            """
            return (sim.miss_km, sim.flight_hours())

        initial = _bearing(origin[0], origin[1], destination[0], destination[1])
        # هر نامزد: (شبیه‌سازی، دالان سیاستی‌اش). دالان برای گزارش و برای
        # جداکردن «کم‌زمان‌ترین» از «موازی‌ترین» لازم است.
        candidates: list[tuple[_Simulation, float]] = []

        if settings.track_wind:
            # در حالت دنبال‌کردن باد، «سمت فرمان» دیگر یک پارامتر جست‌وجو نیست:
            # هر گام سمتش را از مثلث باد می‌گیرد، پس پویش ۳۶۰ درجه‌ای بی‌معنا
            # است. درجهٔ آزادی واقعی همان *دالان* است: هواپیما تا کجا اجازه دارد
            # از خط مبدأ–مقصد دور شود تا موازی باد بماند. برای هر دالان یک
            # شبیه‌سازی کامل اجرا می‌شود و کارنامهٔ هم‌راستایی‌اش نگه داشته
            # می‌شود.
            # سه حالت، به ترتیب اولویت:
            #   ۱) دالان صریح (``corridor_override``) — یک نامزد، بدون جست‌وجو.
            #      همین حالت «گونهٔ هم‌خانواده» را می‌سازد.
            #   ۲) جست‌وجوی چند دالانی (``alignment_first``) — نردبان دالان‌ها.
            #   ۳) سیاست قدیمی تک‌دالانی.
            if settings.corridor_override is not None:
                fractions = (settings.corridor_override,)
            elif settings.alignment_first:
                fractions = (settings.wind_corridor_fraction, *settings.search_fractions)
            else:
                fractions = (settings.wind_corridor_fraction,)
            for fraction in dict.fromkeys(round(value, 6) for value in fractions):
                candidates.append((simulation(initial, fraction), fraction))
        else:
            scan = [
                simulation(heading, settings.wind_corridor_fraction)
                for heading in _heading_scan(settings.heading_coarse_step_deg)
            ]
            seed = min(scan, key=rank)
            span = settings.heading_coarse_step_deg
            for step in settings.heading_refine_steps_deg:
                stage = [
                    simulation(heading, settings.wind_corridor_fraction)
                    for heading in _refine_scan(seed.heading_deg, span, step)
                ]
                scan.extend(stage)
                seed = min(stage, key=rank)
                span = step
            candidates = [(sim, settings.wind_corridor_fraction) for sim in scan]

        # شرط ایمنی زمین: مسیری که از داخل کوه می‌گذرد «قابل‌پرواز» نیست،
        # هرچند ریاضیات باد و گلایدش کامل باشد. بدون این فیلتر، بهترین
        # بادسواری می‌توانست مستقیم از میان قلهٔ بینالود رد شود — همان
        # چیزی که در گراف با حذف گره‌های زیر آستانه جلویش گرفته شد.
        flyable = [
            item
            for item in candidates
            if item[0].miss_km <= settings.max_arrival_miss_km
            and item[0].terrain_climb_feasible
            and (
                item[0].min_terrain_clearance_m is None
                or item[0].min_terrain_clearance_m >= min_clearance_m - 1e-9
            )
        ]
        if not flyable:
            continue
        # کارنامهٔ هم‌راستایی فقط برای نامزدهای قابل‌پرواز ساخته می‌شود (ساخت آن
        # ارزان است ولی روی صدها نامزد پویش سمت هم بی‌دلیل است).
        alignment_by_sim = {
            id(sim): wind_alignment_profile(sim.legs) for sim, _fraction in flyable
        }
        fastest = min(flyable, key=lambda item: item[0].flight_hours())
        time_limit = fastest[0].flight_hours() * settings.alignment_slack_ratio
        aligned = [
            item for item in flyable if item[0].flight_hours() <= time_limit + 1e-9
        ]
        if settings.alignment_first:
            # هدف: بیشترین مسافت موازی باد، و در تساوی، کم‌زمان‌ترین.
            chosen, chosen_fraction = max(
                aligned,
                key=lambda item: (
                    alignment_by_sim[id(item[0])].aligned_share,
                    -item[0].flight_hours(),
                ),
            )
        else:
            chosen, chosen_fraction = fastest
        chosen_profile = alignment_by_sim[id(chosen)]
        plan = WindRidingPlan(
            altitude_m=altitude_m,
            # در حالت دنبال‌کردن باد سمت *ثابت* نیست، پس گزارش «سمت فرمان»
            # نمی‌تواند یک سمت دلبخواه باشد: میانگین مسافت‌وزن سمت‌های هوایی
            # همین مسیر گزارش می‌شود — عددی که واقعاً پرواز شده است.
            heading_deg=(
                _mean_air_heading(chosen.legs, chosen.heading_deg)
                if settings.track_wind
                else chosen.heading_deg
            ),
            path=chosen.points,
            node_altitudes=chosen.altitudes,
            min_terrain_clearance_m=chosen.min_terrain_clearance_m,
            climb_m=climb_m,
            climb_time_hours=climb_hours,
            ride_time_hours=chosen.ride_hours,
            descent_time_hours=chosen.descent_hours,
            final_leg_hours=chosen.final_leg_hours,
            ride_distance_km=chosen.ride_km,
            descent_distance_km=chosen.descent_km,
            descent_slope_ratio=chosen.descent_slope_ratio,
            descent_power_fraction=chosen.descent_power_fraction,
            total_distance_km=chosen.ride_km + chosen.descent_km + chosen.final_leg_km,
            arrival_miss_km=chosen.miss_km,
            final_leg_km=chosen.final_leg_km,
            final_bearing_deg=chosen.final_bearing_deg,
            legs=chosen.legs,
            aligned_share=chosen_profile.aligned_share,
            parallel_mean_deg=chosen_profile.parallel_mean_deg,
            final_correction_km=chosen_profile.final_correction_km,
            corridor_fraction=chosen_fraction,
        )
        if best_plan is None or _plan_preference(plan, best_plan, settings):
            best_plan = plan

    return best_plan


def _plan_preference(
    plan: WindRidingPlan,
    best: WindRidingPlan,
    settings: WindRidingConfig,
) -> bool:
    """آیا ``plan`` از ``best`` بهتر است؟ (سیاست انتخاب بین سطوح پرواز).

    در حالت ``alignment_first`` هدف بیشترین سهم موازی باد است، مشروط به اینکه
    زمان از همان سقف ‎``alignment_slack_ratio``‎ روی سریع‌ترین سطح بیشتر نشود.
    بدون سقف، «بیشترین موازی» می‌تواند یک سطح کند را انتخاب کند که کاربر
    *به‌خاطر باد* نمی‌خواست؛ و بدون هدف، همان انتخاب کم‌زمان‌ترین قبلی می‌ماند.
    """
    if not settings.alignment_first:
        return plan.total_time_hours < best.total_time_hours
    # سقف زمانی: اختلاف دو سطح آن‌قدر زیاد نباشد که «موازی‌تر بودن» را به یک
    # پرواز بی‌معنا تبدیل کند.
    limit = min(plan.total_time_hours, best.total_time_hours) * settings.alignment_slack_ratio
    if plan.aligned_share > best.aligned_share + 1e-9:
        return plan.total_time_hours <= limit + 1e-9
    if math.isclose(plan.aligned_share, best.aligned_share, abs_tol=1e-9):
        return plan.total_time_hours < best.total_time_hours
    return False


def _mean_air_heading(legs: Sequence[LegSample], fallback: float) -> float:
    """میانگین مسافت‌وزن سمت‌های هوایی (میانگین دایره‌ای، نه میانگین معمولی).

    در حالت دنبال‌کردن باد سمت فرمان هر قطعه فرق دارد، پس جمع کردن سادهٔ اعداد
    درجه غلط می‌شود (۲۵۰ و ۳۵۰ به ۳۰۰ می‌رسند که هیچ‌کدام نیست). بردار یکهٔ هر
    سمت در جهت مسافتش وزن می‌گیرد و میانگین بردار، سمت را می‌دهد.
    """
    east = 0.0
    north = 0.0
    total = 0.0
    for leg in legs:
        if leg.air_heading_deg is None or leg.distance_km <= 0.0:
            continue
        weight = leg.distance_km
        radians = math.radians(leg.air_heading_deg)
        east += weight * math.sin(radians)
        north += weight * math.cos(radians)
        total += weight
    if total <= 0.0:
        return fallback
    return math.degrees(math.atan2(east, north)) % 360.0


def _drift_leg_metrics(
    heading_deg: float,
    wind_speed_mps: float,
    wind_direction_from_deg: float,
    airspeed_mps: float,
) -> tuple[float, float, float]:
    """سرعت زمینی و مؤلفه‌های باد نسبت به **سمت فرمان** (نه سمت مسیر).

    در پرواز با سمت ثابت، خلبان زاویهٔ تصحیح نمی‌گیرد؛ بردار سرعت زمینی مستقیماً
    ``airspeed·û(ψ) + W`` است. پس برخلاف حالت «نگه‌داشتن مسیر» (که در
    ``pathfinding.cost`` مدل شده)، مؤلفهٔ عمود باد سرعت زمینی را *کم نمی‌کند* بلکه
    آن را می‌چرخاند — و همین است که بادسواری را کارآمد می‌کند.

    برمی‌گرداند
    ----------
    (ground_speed_mps, along_heading_mps, cross_heading_mps)
        سرعت زمینی، مؤلفهٔ باد هم‌راستا با سمت فرمان (مثبت = کمک‌رسان) و اندازهٔ
        مؤلفهٔ عمود بر آن.
    """
    heading_rad = math.radians(heading_deg)
    wind_east, wind_north = _wind_vector(wind_speed_mps, wind_direction_from_deg)
    along = wind_east * math.sin(heading_rad) + wind_north * math.cos(heading_rad)
    cross = wind_east * math.cos(heading_rad) - wind_north * math.sin(heading_rad)
    ground_speed = math.sqrt(
        max(airspeed_mps**2 + wind_speed_mps**2 + 2.0 * airspeed_mps * along, 0.0)
    )
    return ground_speed, along, abs(cross)


def wind_riding_route_result(
    plan: WindRidingPlan,
    *,
    aircraft: CostModelConfig | None = None,
    effort: MotorEffortConfig | None = None,
    vertical: VerticalCostConfig | None = None,
    criterion: str = "energy",
    ground_elevation_at: Callable[[float, float], float] | None = None,
) -> RouteResult:
    """برنامهٔ بادسواری را به ``RouteResult`` تبدیل می‌کند تا با مسیرهای گرافی
    در همان جدول/صحنه مقایسه شود.

    دو حالت محاسبه، عمداً کنار هم:

    - **قطعه‌های بادسواری و فرود** سمت فرمان ثابت دارند، پس سرعت زمینی از
      ``airspeed·û(ψ) + W`` می‌آید و جریمه‌های شاخص انرژی (پسار القایی و بادِ
      رو-به-رو) نسبت به **سمت فرمان** سنجیده می‌شوند، نه سمت مسیر روی زمین.
    - **قطعهٔ پایانی** (اگر لازم شود) یک مسیر روی زمین است؛ همان‌جا
      ``compute_edge_cost`` استفاده می‌شود، مثل مسیرهای گرافی.

    «تغییر جهت» عمداً روی **سمت مسیر روی زمین** شمرده می‌شود (مثل بقیهٔ
    مسیرها): مسیر بادسواری روی زمین خمیده است ولی فرمانِ سمت ثابت می‌ماند و همین
    تفاوت استراتژی است. تعداد «تصحیح مسیر با موتور» در ستون مدل سوخت، صفر است.
    """
    plane = aircraft or CostModelConfig()
    effort_config = effort or MotorEffortConfig()
    verticals = vertical or VerticalCostConfig()

    # ۱) بازمحاسبهٔ دقیق قطعات: فاصلهٔ بزرگ‌دایره + زمان از همان مدل هزینه‌ای که
    #    مسیرهای گرافی با آن ساخته می‌شوند. حلقهٔ جست‌وجو با تقریب تخت کار کرده
    #    بود؛ این‌جا اعداد *گزارش‌شده* دقیق می‌شوند.
    legs: list[LegSample] = []
    total_distance = 0.0
    total_time = 0.0
    energy_index = 0.0
    tailwind_legs = 0
    for index, leg in enumerate(plan.legs):
        if index + 1 >= len(plan.path):
            break
        lat1, lon1 = plan.path[index]
        lat2, lon2 = plan.path[index + 1]
        distance_km = haversine_km(lat1, lon1, lat2, lon2)
        bearing = initial_bearing_deg(lat1, lon1, lat2, lon2)
        if leg.air_heading_deg is None:
            # حالت «نگه‌داشتن مسیر روی زمین» — مثل مسیرهای گرافی.
            result = compute_edge_cost(
                lat1,
                lon1,
                lat2,
                lon2,
                leg.wind_speed_mps,
                leg.wind_direction_from_deg,
                config=plane,
                criterion=criterion,
            )
            leg_time = result.time_hours
            leg_energy = result.energy_hours
            along = result.along_track_mps
        else:
            # حالت «نگه‌داشتن سمت فرمان» — خودِ بادسواری.
            ground_speed, along, cross = _drift_leg_metrics(
                leg.air_heading_deg,
                leg.wind_speed_mps,
                leg.wind_direction_from_deg,
                plane.airspeed_mps,
            )
            # زمان قطعه همان زمان *انتگرال‌گیری* است (ساعت شبیه‌سازی)، نه
            # مسافت/سرعتِ لحظه‌ای نمونه: در فاز بادسواری موقعیت با همان dt
            # انتگرال گرفته شده، پس این دو با هم سازگارند و اختلاف باد در طول
            # قطعه (۲ دقیقه‌ای) جمع نمی‌شود.
            leg_time = leg.time_hours or (
                distance_km / (ground_speed * 3.6) if ground_speed > 0.0 else 0.0
            )
            leg_energy = (
                leg_time
                * (1.0 + plane.induced_drag_coeff * (cross / plane.airspeed_mps) ** 2)
                * (
                    1.0
                    + plane.headwind_penalty_coeff
                    * max(0.0, -along)
                    / plane.airspeed_mps
                )
            )
        total_distance += distance_km
        total_time += leg_time
        energy_index += leg_energy
        if along > 0.0:
            tailwind_legs += 1
        legs.append(
            LegSample(
                track_bearing_deg=bearing,
                wind_speed_mps=leg.wind_speed_mps,
                wind_direction_from_deg=leg.wind_direction_from_deg,
                distance_km=distance_km,
                time_hours=leg_time,
                air_heading_deg=leg.air_heading_deg,
                # قطعه‌های فرود با همان کسر توانی سنجیده می‌شوند که برنامه‌ریز
                # از توازن رانش همان شیب بیرون داده؛ نتیجه‌اش این است که پروندهٔ
                # سوخت خودش تسویهٔ گرانش را می‌سازد (کار پسار منهای ``m·g·h`` که
                # راه کم‌کردن ارتفاع در همان مسافت می‌پردازد) و لازم نیست مقدار
                # ``descent_m`` هم داده شود — آن یکی همان تسویه را دو بار
                # می‌شمرد و سوخت را کمتر از واقع درمی‌آورد.
                power_fraction=leg.power_fraction,
            )
        )

    # ۲) صعود — یک فاز عمودی جدا در مبدأ، با همان تابع هزینهٔ گذار عمودی گراف
    #    تا «مسافت سه‌بعدی»، زمان و شاخص انرژی با مسیرهای گرافی هم‌مقیاس باشد.
    # **صعود واقعی = تا بلندترین نقطهٔ مسیر.** ارتفاع هواپیما در فاز بادسواری
    # همیشه سطح کروز نیست: اگر رشته‌کوه سر راه باشد هواپیما بالا می‌رود تا از
    # زمین رد شود (به کف زمین در ``_simulate_heading`` نگاه کنید). آن ارتفاع
    # اضافی هم با موتور گرفته شده، پس باید در کارنامهٔ سوخت حساب شود؛ وگرنه
    # «صعود برای رد شدن از کوه» یک وعدهٔ رایگان می‌شد که نیست.
    ground_start_msl = plan.altitude_m - plan.climb_m
    peak_altitude_m = max(plan.node_altitudes) if plan.node_altitudes else plan.altitude_m
    climb_height_m = max(peak_altitude_m - ground_start_msl, 0.0)
    # ارتفاع کل فرود = بلندترین نقطه منهای ارتفاع زمین **مقصد** (نه مبدأ): پروفیل
    # دقیقاً روی زمین مقصد تمام می‌شود، پس اگر مثل سمت صعود از زمین مبدأ شمرده
    # شود، اختلاف کوچک ناهمواری دو سر کریدور را نادیده می‌گیرد و مسیر بادسواری
    # یک عدد ناسازگار با بقیهٔ مسیرها گزارش می‌کند.
    descent_height_m = climb_height_m
    if plan.node_altitudes:
        descent_height_m = max(peak_altitude_m - float(plan.node_altitudes[-1]), 0.0)
    climb = compute_vertical_cost(
        climb_height_m, config=plane, criterion=criterion, vertical=verticals,
    )
    total_time += climb.time_hours
    energy_index += climb.energy_hours

    # فرود *جدا* شمرده نمی‌شود: در بادسواری، فرود درون همان فاز بادسواری و در
    # حرکت انجام می‌شود (هواپیما هنگام کم‌کردن ارتفاع هم جلو می‌رود)، پس زمانش
    # در قطعه‌های همین مسیر است و توانش هم در ``power_fraction`` همان قطعه‌ها
    # حساب شده. اگر انرژی پتانسیل فرود را جدا هم می‌نوشتیم، همان فاز دو بار
    # بهای سوخت می‌داد. تنها انرژی پتانسیل **صعود** شمرده می‌شود.
    #
    # نگاهی به کل: صعود ``mgh/η`` هزینه دارد و قطعه‌های فرود به اندازهٔ ``m·g·h``
    # کمتر از کروز توان می‌خواهند، پس دو تسویه یکدیگر را می‌گیرند و جمع برابر
    # «کار پسار در طول همان مسیر» می‌ماند — یعنی شکل پروفیل فرود (شیب ملایم یا
    # گلاید تند) سوخت را رایگان نمی‌کند، فقط جایش را عوض می‌کند.
    effort_result = compute_route_effort(
        legs,
        aircraft=plane,
        effort=effort_config,
        climb_m=climb_height_m,
        # صفر است و باید صفر بماند: مسافت فرود *داخل* قطعه‌های همین مسیر است و
        # با ``power_fraction`` به نرخ دور آرام بهای سوخت می‌دهد، پس اگر بُرد
        # گلاید را هم به‌عنوان تسویهٔ گرانش اضافه کنیم، همان سوخت دو بار
        # پس‌گرفته می‌شود.
        descent_m=0.0,
    )
    horizontal_legs = len(legs)

    # پروفیل عمودی: پلهٔ صعود → رمپ نرم و تدریجی (به توضیح بالای ``node_altitudes``
    # نگاه کنید). هم مسیر و هم ارتفاع‌ها از یک فراخوانی می‌آیند تا طولشان یکی
    # بماند.
    #
    # ``min_clearance_m`` صفر می‌ماند چون خود برنامه‌ریز فرود را زمین‌آگاه کرده و
    # پنجرهٔ نشستن خودش را دارد؛ دادن فاصلهٔ ایمنی این‌جا فقط مسیر را نزدیک مقصد
    # یک‌بار دیگر بالا می‌برد. ``glide_ratio`` هم داده می‌شود تا سقف شیب فرود در
    # همهٔ مسیرهای صحنه یک معنا داشته باشد (گلاید با موتور دور آرام).
    ramped_path, ramped_altitudes = ramp_vertical_transitions(
        plan.path,
        _ground_anchored_altitudes(plan.node_altitudes),
        climb_rate_mps=verticals.climb_rate_mps,
        descent_rate_mps=verticals.descent_rate_mps,
        ground_speed_mps=_mean_ground_speed_from_legs(legs, plane.airspeed_mps),
        ground_elevation_at=ground_elevation_at,
        glide_ratio=effort_config.glide_ratio,
    )

    return RouteResult(
        path=ramped_path,
        node_ids=[f"ride|{lat:.5f},{lon:.5f}" for lat, lon in ramped_path],
        layer_altitude=plan.altitude_m,
        total_cost=plan.total_time_hours,
        total_distance_km=total_distance,
        estimated_time_hours=total_time,
        criterion=criterion,
        total_energy_index=energy_index,
        tailwind_leg_fraction=(tailwind_legs / horizontal_legs) if horizontal_legs else 0.0,
        # «تغییر جهت» = تغییر سمت مسیر روی زمین (نه فرمان سمت)، مثل بقیه مسیرها.
        heading_changes=_ground_heading_changes(plan.path),
        algorithm="wind-riding",
        # پروفیل ارتفاع این مسیر پیوسته است (فرود با شيب)، پس تنها لایهٔ کروز
        # را صریح اعلام می‌کنیم. بدون این فیلد، ``altitudes_used`` هر ارتفاع
        # میانی فرود را یک «لایه» می‌شمرد و مسیر «چند لایه» به نظر می‌رسید.
        layers_used=(plan.altitude_m,),
        leg_samples=legs,
        # گره‌های زمین صفر گزارش می‌شوند — همان قرارداد ``RouteResult`` که
        # ``WindRouter`` هم رعایت می‌کند (به مستند ``node_altitudes`` نگاه کنید).
        # بدون این تبدیل، اولین گرهٔ همین مسیر ارتفاع *زمین* مبدأ (≈۹۸۳ متر)
        # را می‌گرفت در حالی که مسیر گرافی در همان نقطه صفر می‌دهد؛ یعنی دو
        # مسیر هم‌کریدور با دو مبنای متفاوت گزارش می‌شدند و مقایسهٔ «از زمین
        # تا زمین» فقط برای یکی از آن‌ها درست بود.
        # **پروفیل عمودی.** صعود این مسیر یک فاز عمودی جدا در مبدأ است (با همان
        # ``compute_vertical_cost`` مسیرهای گرافی)، پس در هندسهٔ گزارش‌شده هم
        # باید روی همان مسافت افقی پخش شود، نه یک دیوار در مبدأ. فرودِ خودِ
        # بادسواری از قبل پیوسته است، پس نرم‌کننده دستش را نمی‌زند؛ فقط همان
        # پلهٔ صعود را رمپ می‌کند. مسافت پخش از سرعت زمینی همین مسیر می‌آید.
        node_altitudes=ramped_altitudes,
        total_climb_m=climb_height_m,
        total_descent_m=descent_height_m,
        climb_legs=2,
        min_clearance_m=plan.min_terrain_clearance_m,
        effort=effort_result,
    )


def _mean_ground_speed_from_legs(
    legs: Sequence[LegSample],
    fallback_mps: float,
) -> float:
    """میانگین *وزنی‌به‌مسافت* سرعت زمینی قطعه‌های مسیر (متر بر ثانیه).

    مسافت افقی رمپ عمودی از این عدد می‌آید، پس باید از خود مسیر خوانده شود نه
    از یک ثابت: سرعت زمینی بادسواری با باد پشت به ۲۸ m/s می‌رسد در حالی که سرعت
    هوایی ۲۰ m/s است؛ اگر رمپ با سرعت هوایی ساخته شود، شیب صعود گزارش‌شده
    با شیبی که برناه‌ریز و مدل هزینه فرض کرده‌اند یکی نمی‌شود.
    """
    total_km = sum(leg.distance_km for leg in legs)
    if total_km <= 0.0:
        return max(fallback_mps, 1e-6)
    weighted = 0.0
    for leg in legs:
        if leg.time_hours > 0.0 and leg.distance_km > 0.0:
            weighted += leg.distance_km * (leg.distance_km / (leg.time_hours * 3.6))
    return max(weighted / total_km, 1e-6)


def _ground_anchored_altitudes(
    altitudes: Sequence[float],
) -> list[float]:
    """ارتفاع گره‌های زمین را صفر می‌کند (قرارداد ``RouteResult.node_altitudes``).

    پروفیل بادسواری از سطح زمین شروع و به سطح زمین تمام می‌شود، پس دو سر آن دو
    گرهٔ زمین‌اند و مثل مسیرهای گرافی باید صفر گزارش شوند. مقدار واقعی زمین
    (که ۹۰۰ تا ۳۰۰۰ متر است) در همان قرارداد گفته نمی‌شود؛ مصرف‌کنندهٔ صحنه
    خودش ارتفاع زمین محلی را از DEM می‌گیرد.
    """
    values = list(altitudes)
    if not values:
        return values
    values[0] = 0.0
    values[-1] = 0.0
    return values


def _ground_heading_changes(path: Sequence[tuple[float, float]], threshold_deg: float = 30.0) -> int:
    """تعداد تغییرهای بیش از ``threshold_deg`` در سمت *مسیر روی زمین*."""
    if len(path) < 3:
        return 0
    bearings = [
        _bearing(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
        for i in range(len(path) - 1)
    ]
    changes = 0
    for i in range(1, len(bearings)):
        diff = abs(bearings[i] - bearings[i - 1]) % 360.0
        turn = diff if diff <= 180.0 else 360.0 - diff
        if turn > threshold_deg:
            changes += 1
    return changes
