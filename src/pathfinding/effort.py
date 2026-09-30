"""برآورد «تلاش موتوری» و مصرف سوخت یک مسیر — مدل مبتنی بر فرض‌های مستند.

چرا این ماژول لازم است
----------------------
مدل هزینهٔ ``pathfinding.cost`` سینماتیک است: مسیر را بر اساس زمان یا
«شاخص انرژی» بهینه می‌کند و هیچ‌وقت نمی‌گوید هواپیما **چند بار** باید با موتور
مسیرش را تصحیح کند، **با چه توانی**، و **چقدر سوخت** می‌سوزاند. این ماژول همان
لایه است: از هندسهٔ مسیر (سمت حرکت هر قطعه + باد هر قطعه) بردار سرعت هوایی را
می‌سازد و از آن، تلاش موتوری را حساب می‌کند.

هشدار صداقت — این‌ها فرض مدل‌اند، نه اندازه‌گیری
------------------------------------------------
هیچ‌کدام از اعداد خروجی «داده» نیستند. تمام آن‌ها از فرض‌های پارامتری
``MotorEffortConfig`` می‌آیند (جرم، نسبت برآر به پسار، زاویهٔ کرنش، راندمان‌ها،
ارزش حرارتی سوخت) و این پارامترها در هیچ فایل داده‌ای این پروژه وجود ندارند.
پس هر عدد سوختی که در گزارش/صحنه دیده می‌شود باید با همین برچسب «مدل، نه
اندازه‌گیری» نمایش داده شود.

فیزیک مدل (چهار بخش مستقل)
---------------------------
۱) **بردار سرعت هوایی و سمت واقعی:** برای هر قطعهٔ افقی، باد (سرعت، جهت) و
   سمت مسیر (track) معلوم است. با ثابت‌بودن اندازهٔ سرعت هوایی، تنها سمت و
   سرعت زمینیِ سازگار با حفظ مسیر به‌دست می‌آید (مثلث ناوبری باد). سمت
   هوایی همان چیزی است که خلبان/کنترلر باید فرمان بدهد، و **تفاوت سمت هوایی
   دو قطعهٔ متوالی** = «تغییر مسیر موتوری» (چیزی که کاربر می‌پرسد چند بار
   رخ می‌دهد).
۲) **توان کروز:** در پرواز تراز، پسار کل ``D = m·g / (L/D)`` است و توان شافت
   لازم برای غلبه بر آن ``P = D·V_air / η_prop`` است. توان به سرعت *هوایی*
   بسته است (نه زمینی)، اما سوخت هر کیلومتر به سرعت زمینی بسته است: باد پشت
   زمان قطعه را کوتاه می‌کند و سوخت همان قطعه را کم می‌کند — همان چیزی که
   مسیریابی بادی باید نشان دهد.
۳) **هزینهٔ تغییر مسیر:** هر تغییر سمت با کرنش (bank) با نرخ شناخته‌شده
   ``ω = g·tan(φ)/V_air`` انجام می‌شود، پس زمان دور زدن ``t = |Δψ|/ω`` است.
   در دور تراز، ضریب بار ``n = 1/cos(φ)`` است و پسار القایی با ``n²`` بزرگ
   می‌شود؛ پس توان اضافهٔ دور ``P_extra = D_i·(n²−1)·V_air/η_prop`` است که
   ``D_i`` سهم پسار القایی از پسار کل است (کسر ``induced_drag_fraction``).
   توجه: موتور برای «چرخیدن» رانش اضافه نمی‌دهد؛ چرخش آیرودینامیکی است — سوخت
   اضافه از پسار القایی بزرگ‌شده در طول دور می‌آید. این تفکیک صریح است تا عدد
   به‌دست‌آمده قابل دفاع بماند.
۴) **سوخت:** سوخت مصرفی از انرژی شافت به دست می‌آید:
   ``fuel_kg = E_shaft_J / (η_thermal · LHV)``. جمع چهار مؤلفه گزارش می‌شود
   (کروز، دورها، صعود، فرود) تا معلوم باشد کدام بخش سوخت از *خودِ مسیر* آمده.

فرض‌های پیش‌فرض برای یک پهپاد کوچک (۷۲ km/h) انتخاب شده‌اند — همان
``VIZ_AIRCRAFT`` — و در دیتاکلاس قابل بازنویسی‌اند.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from pathfinding.cost import (
    CostModelConfig,
    InfeasibleEdgeError,
    air_heading_deg,
)

__all__ = [
    "GRAVITY_MPS2",
    "MotorEffortConfig",
    "LegSample",
    "RouteEffort",
    "air_heading_deg",
    "sample_horizontal_leg",
    "compute_route_effort",
]

# شتاب گرانش استاندارد (m/s²). یک مقدار ثابت فیزیکی است، نه فرض پروژه.
GRAVITY_MPS2 = 9.80665


@dataclass(frozen=True)
class MotorEffortConfig:
    """فرض‌های مدل تلاش موتوری.

    پارامترها
    ----------
    mass_kg : float
        جرم کل وسیله در لحظهٔ برخاست (کیلوگرم). باید مثبت باشد.
    lift_to_drag : float
        نسبت برآر به پسار در پرواز تراز (بی‌بعد). پسار کل ``m·g/(L/D)``.
    induced_drag_fraction : float
        سهم پسار القایی از پسار کل در بازهٔ [0, 1]. تنها همین بخش در دور تشدید
        می‌شود، پس اگر صفر باشد هزینهٔ دور صفر می‌شود.
    bank_angle_deg : float
        زاویهٔ کرنش در دورهای تراز (درجه). نرخ دور و ضریب بار از آن می‌آید.
    propulsive_efficiency : float
        راندمان تبدیل توان شافت به توان رانش در بازهٔ (0, 1].
    thermal_efficiency : float
        راندمان تبدیل انرژی سوخت به توان شافت در بازهٔ (0, 1].    fuel_lhv_mj_per_kg: float
        ارزش حرارتی پایین سوخت (مگاژول بر کیلوگرم). برای بنزین/سوخت جت ≈۴۳.
    course_change_threshold_deg : float
        حداقل تغییر سمت هوایی (درجه) که «یک بار استفاده از موتور برای تصحیح
        مسیر» شمرده می‌شود. تغییرات کوچک‌تر نادیده گرفته می‌شوند.
    descent_idle_power_fraction : float
        توان شافت موتور در فاز فرود، به‌عنوان کسری از توان کروز (در بازهٔ
        ``[0, 1]``). پیش‌فرض ۰.۱۰ یعنی موتور در فرود تقریباً دور آرام است —
        همان چیزی که فرود گلایدی را «رایگان» می‌کند.
    """

    mass_kg: float = 25.0
    lift_to_drag: float = 12.0
    induced_drag_fraction: float = 0.5
    bank_angle_deg: float = 25.0
    propulsive_efficiency: float = 0.60
    thermal_efficiency: float = 0.28
    fuel_lhv_mj_per_kg: float = 43.0
    course_change_threshold_deg: float = 1.0
    descent_idle_power_fraction: float = 0.10


    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0:
            raise ValueError("mass_kg must be positive.")
        if self.lift_to_drag <= 0.0:
            raise ValueError("lift_to_drag must be positive.")
        if not (0.0 <= self.induced_drag_fraction <= 1.0):
            raise ValueError("induced_drag_fraction must be within [0, 1].")
        if not (0.0 <= self.bank_angle_deg < 90.0):
            raise ValueError("bank_angle_deg must be within [0, 90).")
        if not (0.0 < self.propulsive_efficiency <= 1.0):
            raise ValueError("propulsive_efficiency must be within (0, 1].")
        if not (0.0 < self.thermal_efficiency <= 1.0):
            raise ValueError("thermal_efficiency must be within (0, 1].")
        if self.fuel_lhv_mj_per_kg <= 0.0:
            raise ValueError("fuel_lhv_mj_per_kg must be positive.")
        if self.course_change_threshold_deg < 0.0:
            raise ValueError("course_change_threshold_deg cannot be negative.")
        if not (0.0 <= self.descent_idle_power_fraction <= 1.0):
            raise ValueError("descent_idle_power_fraction must be within [0, 1].")

    @property
    def glide_ratio(self) -> float:
        """نسبت گلاید = نسبت برآر به پسار در پرواز بی‌توان.

        در پرواز تراز همین نسبت است (برآر = وزن، پسار ثابت)، پس یک هواپیما با
        ``L/D = 12`` در ازای هر متر كاهش ارتفاع ۱۲ متر جلو می‌رود.
        """
        return self.lift_to_drag

    def glide_range_km(self, altitude_m: float) -> float:
        """بُرد گلاید از یک ارتفاع (کیلومتر): ``h · (L/D)``.

        این همان مسافتی است که هواپیما **با موتور در دور آرام** طی می‌کند، پس
        بهای سوختی ندارد در حالی که بُرد افقی واقعی است. پیش‌تر این مسافت در
        هیچ‌جای مدل نمی‌آمد: صعود `mgh/η` بهای انرژی می‌داد ولی گرانش هیچ‌وقت
        آن ذخیره را بازنمی‌گرداند و نتیجه‌اش جانبداری یک‌طرفه به نفع لایه‌های
        پایین بود.
        """
        return max(altitude_m, 0.0) * self.glide_ratio / 1000.0
    @property
    def load_factor(self) -> float:
        """ضریب بار در دور تراز: ``1 / cos(bank)``."""
        return 1.0 / math.cos(math.radians(self.bank_angle_deg))

    @property
    def induced_drag_multiplier(self) -> float:
        """ضریب بزرگ‌شدن پسار القایی در دور: ``n² − 1`` (زاویهٔ صفر → صفر)."""
        return self.load_factor**2 - 1.0

    @property
    def drag_force_n(self) -> float:
        """پسار کل در پرواز تراز (نیوتن): ``m·g/(L/D)``."""
        return self.mass_kg * GRAVITY_MPS2 / self.lift_to_drag

    @property
    def fuel_energy_j_per_kg(self) -> float:
        """انرژی سوخت به‌ازای هر کیلوگرم (ژول)."""
        return self.fuel_lhv_mj_per_kg * 1.0e6

    def shaft_power_w(self, airspeed_mps: float) -> float:
        """توان شافت لازم برای پرواز تراز با سرعت هوایی داده‌شده (وات)."""
        if airspeed_mps <= 0.0:
            raise ValueError("airspeed_mps must be positive.")
        return self.drag_force_n * airspeed_mps / self.propulsive_efficiency

    def fuel_kg_from_shaft_energy_j(self, energy_j: float) -> float:
        """سوخت لازم برای یک مقدار انرژی شافت (کیلوگرم)."""
        if energy_j < 0.0:
            raise ValueError("energy_j cannot be negative.")
        return energy_j / (self.thermal_efficiency * self.fuel_energy_j_per_kg)


@dataclass(frozen=True)
class LegSample:
    """یک قطعهٔ افقی مسیر، همان‌قدر که مدل تلاش موتوری لازم دارد.

    پارامترها
    ----------
    track_bearing_deg : float
        سمت حرکت روی زمین (درجه، از شمال).
    wind_speed_mps, wind_direction_from_deg : float
        باد همان قطعه (جهت با قرارداد هواشناسی: از کجا می‌وزد).
    distance_km : float
        مسافت افقی قطعه (کیلومتر).
    time_hours : float, اختیاری
        زمان واقعی قطعه از مدل هزینه. اگر صفر باشد از سرعت زمینی حساب می‌شود.
    air_heading_deg : float, اختیاری
        سمت هوایی *فرمان‌داده‌شدهٔ* این قطعه. برای مسیرهای الگوریتمی خالی می‌ماند
        و از مثلث ناوبری (سمت مسیر + باد) بازسازی می‌شود. مسیرهای برنامه‌ریزی‌شده
        (مثل بادسواری) سمت فرمان را خودشان می‌دانند؛ وقتی داده شود همان استفاده
        می‌شود و «تغییر مسیر» دقیقاً اختلاف دو فرمان است، نه اختلاف دو مقدار
        بازسازی‌شده از تقریب گره‌ای.
    power_fraction : float
        کسری از توان شافت کروز که این قطعه مصرف می‌کند (در بازهٔ ``[0, 1]``).
        قرارداد: ۱ = پرواز توان‌دار معمولی، ``descent_idle_power_fraction`` =
        گلاید با موتور دور آرام. این فیلد همان جایی است که فرود گلایدی *داخل*
        مسیر (و نه به‌عنوان یک گذار عمودی جدا) حساب می‌شود: آن مسافت هست، ولی
        سوختش از گرانش می‌آید، نه از باک. برای این‌گونه مسیرها ``descent_m`` را
        صفر بدهید، وگرنه تسویهٔ گرانش دو بار شمرده می‌شود.
    """

    track_bearing_deg: float
    wind_speed_mps: float
    wind_direction_from_deg: float
    distance_km: float
    time_hours: float = 0.0
    air_heading_deg: float | None = None
    power_fraction: float = 1.0


def sample_horizontal_leg(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    wind_speed_mps: float,
    wind_direction_from_deg: float,
    distance_km: float,
    time_hours: float = 0.0,
) -> LegSample:
    """یک قطعهٔ افقی را از مختصات دو سرش می‌سازد (سمت مسیر از همان دو نقطه)."""
    from pathfinding.cost import initial_bearing_deg

    return LegSample(
        track_bearing_deg=initial_bearing_deg(lat1, lon1, lat2, lon2),
        wind_speed_mps=wind_speed_mps,
        wind_direction_from_deg=wind_direction_from_deg,
        distance_km=distance_km,
        time_hours=time_hours,
    )


@dataclass(frozen=True)
class RouteEffort:
    """خروجی مدل تلاش موتوری برای یک مسیر کامل.

    پارامترها
    ----------
    powered_course_changes : int
        چند بار سمت هوایی بیش از آستانه تغییر کرده است — یعنی چند بار موتور باید
        برای تصحیح مسیر درگیر شود.
    course_change_deg_total : float
        مجموع اندازهٔ همهٔ همین تغییرها (درجه).
    turn_time_s : float
        مجموع زمان دورهای کرنش‌دار (ثانیه).
    turn_extra_power_w : float
        توان شافت اضافه در حین دورها (وات). صفر اگر دوری نباشد.
    cruise_shaft_energy_kj : float
        انرژی شافت پرواز تراز در کل مسیر (کیلوژول).
    turn_extra_energy_kj : float
        انرژی شافت اضافهٔ دورها (کیلوژول).
    climb_energy_kj, descent_energy_kj : float
        انرژی شافت برای تغییر ارتفاع (کیلوژول). ``climb_energy_kj``
        انرژی *ناخالص* صعود است (``mgh/η``). ``descent_energy_kj`` دیگر
        ``mgh/η`` نیست: در فرود کار گرانش بخش عمدهٔ رانش را می‌پردازد، پس موتور
        با ``descent_idle_power_fraction`` از توان کروز کار می‌کند.
    glide_range_km : float
        بُرد گلاید فرود: ``h · (L/D)`` کیلومتر پرواز با موتور دور آرام.
    glide_energy_saved_kj : float
        انرژی شافتی که *به‌خاطر* همین بُرد صرفه‌جویی می‌شود: ``D · s_g / η``.
        اتحاد دقیق این‌جاست و در آزمون اثبات می‌شود:
        ``D·(L/D)·h/η = mgh/η`` — یعنی صرفه‌جویی گلاید **مو‌به‌مو** برابر
        انرژی صعود است. پس در مسیری که روی زمین شروع و تمام می‌شود، سوخت
        *خالص* تغییر ارتفاع فقط دور آرام فرود است، نه ``mgh/η``.
    net_altitude_energy_kj : float
        ``climb + descent_idle − glide_saved`` (کیلوژول). قرینهٔ همان اتحاد.
    cruise_fuel_kg, turn_fuel_kg, climb_fuel_kg : float
        تفکیک سوخت مصرفی (کیلوگرم). ``climb_fuel_kg`` از انرژی خالص ارتفاع
        می‌آید (نه از صعود ناخالص).
    glide_fuel_saved_kg : float
        سوختی که تسویهٔ گرانش صرفه‌جویی می‌کند (کیلوگرم) — جدا از ``climb_fuel_kg``
        گزارش می‌شود تا تفکیک قابل حسابرسی بماند.
    total_fuel_kg : float
        جمع مؤلفه‌های بالا (کیلوگرم).
    """

    powered_course_changes: int = 0
    course_change_deg_total: float = 0.0
    turn_time_s: float = 0.0
    turn_extra_power_w: float = 0.0
    cruise_shaft_energy_kj: float = 0.0
    turn_extra_energy_kj: float = 0.0
    climb_energy_kj: float = 0.0
    descent_energy_kj: float = 0.0
    glide_range_km: float = 0.0
    glide_energy_saved_kj: float = 0.0
    net_altitude_energy_kj: float = 0.0
    cruise_fuel_kg: float = 0.0
    turn_fuel_kg: float = 0.0
    climb_fuel_kg: float = 0.0
    glide_fuel_saved_kg: float = 0.0
    total_fuel_kg: float = 0.0
    total_distance_km: float = 0.0
    legs: int = 0
    fuel_per_100km_kg: float = 0.0
    headings_deg: list[float] = field(default_factory=list)


def _wrap_deg(value: float) -> float:
    """کوتاه‌ترین اختلاف زاویه‌ای در بازهٔ (−۱۸۰, ۱۸۰]."""
    return (value + 180.0) % 360.0 - 180.0


def compute_route_effort(
    legs: list[LegSample],
    *,
    aircraft: CostModelConfig | None = None,
    effort: MotorEffortConfig | None = None,
    climb_m: float = 0.0,
    descent_m: float = 0.0,
) -> RouteEffort:
    """تلاش موتوری و سوخت یک مسیر را از قطعه‌های افقی و ارتفاع جابجاشده می‌سازد.

    پارامترها
    ----------
    legs : list[LegSample]
        قطعه‌های افقی مسیر، به ترتیب حرکت. قطعه‌های عمودی این‌جا نمی‌آیند؛
        جمع صعود/فرود جداگانه داده می‌شود چون سمت حرکت آن‌ها تعریف ندارد.
    aircraft : CostModelConfig, اختیاری
        مشخصات هواپیما (فقط ``airspeed_mps`` استفاده می‌شود).
    effort : MotorEffortConfig, اختیاری
        فرض‌های مدل تلاش موتوری. پیش‌فرض برای پهپاد کوچک است.
    climb_m, descent_m : float
        جمع ارتفاع صعود و فرود مسیر (متر).

    برمی‌گرداند
    ----------
    RouteEffort
        شمارش تغییر مسیرهای موتوری + تفکیک توان و سوخت.

    توجه: قطعه‌هایی که مؤلفهٔ عمود بادشان از سرعت هوایی بیشتر است نادیده
    گرفته می‌شوند (چنین قطعه‌ای در گراف اصلاً یال معتبر نمی‌گرفت).
    """
    config = effort or MotorEffortConfig()
    aircraft_config = aircraft or CostModelConfig()
    airspeed = aircraft_config.airspeed_mps

    headings: list[float] = []
    distances: list[float] = []
    ground_speeds: list[float] = []
    times: list[float] = []
    power_fractions: list[float] = []

    for leg in legs:
        try:
            derived_heading, ground_speed = air_heading_deg(
                leg.track_bearing_deg,
                leg.wind_speed_mps,
                leg.wind_direction_from_deg,
                airspeed,
            )
        except InfeasibleEdgeError:
            continue
        heading = derived_heading if leg.air_heading_deg is None else leg.air_heading_deg
        headings.append(heading)
        distances.append(leg.distance_km)
        ground_speeds.append(ground_speed)
        power_fractions.append(min(max(leg.power_fraction, 0.0), 1.0))
        if leg.time_hours > 0.0:
            times.append(leg.time_hours)
        else:
            times.append(leg.distance_km / (ground_speed * 3.6) if ground_speed > 0 else 0.0)

    effort_result = RouteEffort(
        legs=len(headings),
        total_distance_km=float(sum(distances)),
        headings_deg=headings,
    )
    if not headings:
        return effort_result

    # ۱) تغییر مسیر: اختلاف سمت هوایی دو قطعهٔ متوالی.
    changes = 0
    change_total = 0.0
    for i in range(1, len(headings)):
        delta = abs(_wrap_deg(headings[i] - headings[i - 1]))
        if delta >= config.course_change_threshold_deg:
            changes += 1
            change_total += delta

    # ۲) زمان و انرژی دور، از نرخ دور مجاز با کرنش ثابت.
    turn_time_s = 0.0
    if config.bank_angle_deg > 0.0 and airspeed > 0.0:
        turn_rate = (
            GRAVITY_MPS2 * math.tan(math.radians(config.bank_angle_deg)) / airspeed
        )
        turn_time_s = math.radians(change_total) / turn_rate

    induced_drag_n = config.drag_force_n * config.induced_drag_fraction
    turn_extra_power_w = (
        induced_drag_n * config.induced_drag_multiplier * airspeed
        / config.propulsive_efficiency
    )
    turn_extra_energy_j = turn_extra_power_w * turn_time_s

    # ۳) کروز: توان شافت ثابت (سرعت هوایی ثابت است)، زمان از سرعت زمینی هر قطعه.
    # قطعه‌هایی که ``power_fraction < 1`` دارند (گلاید) به همان نسبت کم‌تر
    # می‌سوزانند؛ به همین دلیل سوخت از توانِ *وزنی‌شده* می‌آید، نه از یک توان ثابت
    # ضرب در کل زمان.
    shaft_power = config.shaft_power_w(airspeed)
    powered_time_s = sum(
        time_hours * fraction
        for time_hours, fraction in zip(times, power_fractions, strict=True)
    ) * 3600.0
    cruise_energy_j = shaft_power * powered_time_s

    # ۴) ارتفاع — و این‌جا گرانش.
    #
    # صعود: انرژی ناخالص ``mgh/η`` (کار لازم برای بالا بردن وزن منهای رانش
    # گرانشی که در صعود *علیه* ما کار می‌کند، با راندمان رانش).
    climb_energy_j = (
        config.mass_kg * GRAVITY_MPS2 * max(climb_m, 0.0) / config.propulsive_efficiency
    )

    # فرود: موتور دور آرام. انرژی در فرود ``mgh/η`` *نیست* — چون کار گرانش
    # پرواز را جلو می‌برد؛ موتور فقط دور آرام و سیستم‌ها را می‌گرداند.
    descent_m = max(descent_m, 0.0)
    descent_energy_j = 0.0
    glide_range_km = 0.0
    glide_energy_saved_j = 0.0
    if descent_m > 0.0:
        glide_range_km = config.glide_range_km(descent_m)
        glide_range_m = glide_range_km * 1000.0
        # صرفه‌جویی: پسار ثابت روی همین مسافت، تقسیم بر راندمان رانش.
        # اتحاد: ``D·s_g/η = D·(L/D)·h/η = mgh/η`` — مو‌به‌مو برابر انرژی صعود.
        glide_energy_saved_j = (
            config.drag_force_n * glide_range_m / config.propulsive_efficiency
        )
        # سقف منطقی: یک مسیر نمی‌تواند بیش از کل سوخت کروزش را «از گرانش»
        # پس بگیرد، و بُرد گلاید هم نمی‌تواند از مسافت افقی خود مسیر بیشتر باشد
        # (وگرنه مسافت نپیموده حساب می‌شود).
        glide_energy_saved_j = min(glide_energy_saved_j, cruise_energy_j)
        glide_range_km = min(glide_range_km, float(sum(distances)))
        # مدت گلاید: مسافت بر سرعت هوایی (سرعت زمینی گلاید در گره معلوم نیست،
        # پس بدبینانه‌ترین حالت بی‌باد گرفته می‌شود — همین باعث می‌شود مقدار دور
        # آرام در سمت بزرگ‌تر تخمین بخورد، نه کوچک‌تر).
        glide_seconds = glide_range_m / airspeed if airspeed > 0.0 else 0.0
        descent_energy_j = (
            config.descent_idle_power_fraction * shaft_power * glide_seconds
        )

    net_altitude_energy_j = climb_energy_j + descent_energy_j - glide_energy_saved_j
    # تسویهٔ گرانش نمی‌تواند به سوخت *منفی* برسد؛ کف آن صفر است.
    fuelable_altitude_j = max(net_altitude_energy_j, 0.0)

    cruise_fuel = config.fuel_kg_from_shaft_energy_j(cruise_energy_j)
    turn_fuel = config.fuel_kg_from_shaft_energy_j(turn_extra_energy_j)
    climb_fuel = config.fuel_kg_from_shaft_energy_j(fuelable_altitude_j)
    glide_fuel_saved = config.fuel_kg_from_shaft_energy_j(glide_energy_saved_j)
    total_distance = float(sum(distances))

    return RouteEffort(
        powered_course_changes=changes,
        course_change_deg_total=change_total,
        turn_time_s=turn_time_s,
        turn_extra_power_w=turn_extra_power_w if changes else 0.0,
        cruise_shaft_energy_kj=cruise_energy_j / 1000.0,
        turn_extra_energy_kj=turn_extra_energy_j / 1000.0,
        climb_energy_kj=climb_energy_j / 1000.0,
        descent_energy_kj=descent_energy_j / 1000.0,
        glide_range_km=glide_range_km,
        glide_energy_saved_kj=glide_energy_saved_j / 1000.0,
        net_altitude_energy_kj=net_altitude_energy_j / 1000.0,
        cruise_fuel_kg=cruise_fuel,
        turn_fuel_kg=turn_fuel,
        climb_fuel_kg=climb_fuel,
        glide_fuel_saved_kg=glide_fuel_saved,
        total_fuel_kg=cruise_fuel + turn_fuel + climb_fuel,
        total_distance_km=total_distance,
        legs=len(headings),
        fuel_per_100km_kg=(
            (cruise_fuel + turn_fuel + climb_fuel) / total_distance * 100.0
            if total_distance > 0.0
            else 0.0
        ),
        headings_deg=headings,
    )
