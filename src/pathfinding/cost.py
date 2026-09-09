"""مدل هزینه دینامیکی یال‌های گراف مسیریابی بر اساس باد واقعی.

این ماژول هزینه عبور از یک یال مسیر (بین دو نقطه جغرافیایی) را بر اساس سرعت
و جهت واقعی باد محاسبه می‌کند. بر خلاف مدل ساده‌شده «فقط موافق/مخالف»، اثر
باد به دو مؤلفه مستقل تجزیه می‌شود:

- **مؤلفه هم‌راستا (along-track):** تصویر بردار باد روی راستای حرکت. مقدار
  مثبت یعنی باد کمک‌رسان (تندباد پشت) و مقدار منفی یعنی باد مقاومت‌رسان
  (بادِ رو-به-رو).
- **مؤلفه عمود (cross-track):** تصویر بردار باد عمود بر راستای حرکت (باد
  جانبی). این مؤلفه باعث انحراف اجباری از مسیر مستقیم می‌شود و برای جبران آن
  هواپیما باید زاویه تصحیح باد (wind correction angle) بگیرد که سرعت زمینی
  مؤثر را کاهش می‌دهد و درگ القایی اضافه تولید می‌کند.

سه معیار بهینگی قابل انتخاب پیاده‌سازی شده‌اند:

1. **حداقل زمان سفر** (``criterion="time"``) — بر اساس سرعت مؤثر زمینی
   (ground speed) که از مثلث ناوبری باد به‌دست می‌آید.
2. **حداقل مصرف انرژی** (``criterion="energy"``) — بر اساس زمان پرواز به‌علاوه
   جریمه درگ القایی ناشی از باد جانبی (تصحیح هدینگ پرهزینه‌تر است).
3. **بادِ متعادل** (``criterion="balanced"``) — ترکیب وزن‌دار دو معیار بالا با
   وزن قابل تنظیم توسط کاربر (``time_weight``).

هیچ placeholder یا مقدار ثابت/فرضی در این ماژول استفاده نشده است: تمام
محاسبات بر اساس ورودی واقعی (مختصات دو نقطه + سرعت/جهت باد اندازه‌گیری‌شده)
انجام می‌شود. تنها فرض‌های فیزیکی مدل (سرعت هوایی هواپیما و ضریب درگ القایی)
در ``CostModelConfig`` قابل تنظیم و مستند شده‌اند (به ``docs/task_wind_cost_model.md``
مراجعه کنید).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from preprocessing.consistency import haversine_km

__all__ = [
    "CostModelConfig",
    "EdgeCostResult",
    "InfeasibleEdgeError",
    "initial_bearing_deg",
    "decompose_wind",
    "ground_speed_mps",
    "compute_edge_cost",
]


class InfeasibleEdgeError(ValueError):
    """باد جانبی از سرعت هوایی هواپیما بیشتر است؛ نگه‌داشتن مسیر ممکن نیست."""


@dataclass(frozen=True)
class CostModelConfig:
    """پارامترهای فیزیکی/سیاستی مدل هزینه.

    پارامترها
    ----------
    airspeed_mps : float
        سرعت هوایی حقیقی (True Airspeed) فرض‌شده برای هواپیما/پهپاد، بر حسب
        متر بر ثانیه. باید مثبت باشد. مقدار پیش‌فرض (۵۰ م/ث ≈ ۱۸۰ کیلومتر بر
        ساعت) بازه‌ی معمول پهپادهای مسیریاب منطقه‌ای است؛ برای ناوگان دیگر
        باید صراحتاً بازنویسی شود.
    induced_drag_coeff : float
        ضریب جریمه درگ القایی ناشی از باد جانبی در معیار انرژی. هزینه انرژی
        با ضریب ``1 + induced_drag_coeff * (cross / airspeed) ** 2`` نسبت به
        هزینه زمانی افزایش می‌یابد. باید نامنفی باشد.
    time_weight : float
        وزن معیار «حداقل زمان» در معیار متعادل (بازه [0, 1]). وزن معیار انرژی
        برابر ``1 - time_weight`` است. توسط کاربر در هر فراخوانی قابل تغییر
        است (نیازی به ساخت شیء تنظیمات جدید نیست، چون ``compute_edge_cost``
        نیز پارامتر ``time_weight`` جداگانه می‌پذیرد).
    """

    airspeed_mps: float = 50.0
    induced_drag_coeff: float = 0.3
    time_weight: float = 0.5

    def __post_init__(self) -> None:
        if self.airspeed_mps <= 0:
            raise ValueError("airspeed_mps must be positive.")
        if self.induced_drag_coeff < 0:
            raise ValueError("induced_drag_coeff cannot be negative.")
        if not (0.0 <= self.time_weight <= 1.0):
            raise ValueError("time_weight must be within [0, 1].")


@dataclass(frozen=True)
class EdgeCostResult:
    """خروجی کامل محاسبه هزینه یک یال، آماده فراخوانی توسط لایه مسیریابی."""

    distance_km: float
    bearing_deg: float
    along_track_mps: float
    cross_track_mps: float
    ground_speed_mps: float
    time_hours: float
    energy_hours: float
    balanced_hours: float
    criterion: str
    cost: float

    def as_dict(self) -> dict[str, float | str]:
        """بازنمایی dict برای سریال‌سازی JSON در اسکریپت اعتبارسنجی/گزارش."""
        return {
            "distance_km": self.distance_km,
            "bearing_deg": self.bearing_deg,
            "along_track_mps": self.along_track_mps,
            "cross_track_mps": self.cross_track_mps,
            "ground_speed_mps": self.ground_speed_mps,
            "time_hours": self.time_hours,
            "energy_hours": self.energy_hours,
            "balanced_hours": self.balanced_hours,
            "criterion": self.criterion,
            "cost": self.cost,
        }


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """آزیموت اولیه (forward bearing) از نقطه ۱ به نقطه ۲، بر حسب درجه [0, 360)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def decompose_wind(
    wind_speed_mps: float,
    wind_direction_from_deg: float,
    path_bearing_deg: float,
) -> tuple[float, float]:
    """تجزیه بردار باد به مؤلفه هم‌راستا و عمود نسبت به راستای حرکت.

    ``wind_direction_from_deg`` طبق قرارداد هواشناسی، جهتی است که باد از آن
    می‌وزد (نه جهتی که باد به آن می‌رود).

    برمی‌گرداند: ``(along_track_mps, cross_track_mps)`` که مقدار مثبت
    ``along_track_mps`` به معنای باد کمک‌رسان (پشت) و مقدار منفی به معنای باد
    مقاومت‌رسان (رو-به-رو) است. ``cross_track_mps`` همواره نامنفی است (اندازه
    انحراف جانبی، صرف‌نظر از سمت چپ/راست).
    """
    if wind_speed_mps < 0:
        raise ValueError("wind_speed_mps cannot be negative.")

    wind_to_deg = (wind_direction_from_deg + 180.0) % 360.0
    relative_rad = math.radians(path_bearing_deg - wind_to_deg)

    along_track_mps = wind_speed_mps * math.cos(relative_rad)
    cross_track_mps = abs(wind_speed_mps * math.sin(relative_rad))
    return along_track_mps, cross_track_mps


def ground_speed_mps(airspeed_mps: float, along_track_mps: float, cross_track_mps: float) -> float:
    """سرعت مؤثر زمینی با فرض تصحیح هدینگ برای خنثی‌سازی باد جانبی.

    از مثلث ناوبری کلاسیک استفاده می‌شود: خلبان زاویه‌ای می‌گیرد تا مؤلفه
    عمود باد را خنثی کند (drift correction)، و مؤلفه باقی‌مانده سرعت هوایی با
    مؤلفه هم‌راستای باد جمع می‌شود.

    اگر باد جانبی از سرعت هوایی بیشتر باشد، نگه‌داشتن مسیر ممکن نیست و
    ``InfeasibleEdgeError`` رخ می‌دهد.
    """
    if cross_track_mps > airspeed_mps:
        raise InfeasibleEdgeError(
            f"Crosswind ({cross_track_mps:.2f} m/s) exceeds airspeed "
            f"({airspeed_mps:.2f} m/s); heading cannot be held on this edge."
        )
    drift_corrected_forward = math.sqrt(airspeed_mps**2 - cross_track_mps**2)
    return drift_corrected_forward + along_track_mps


def compute_edge_cost(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    wind_speed_mps: float,
    wind_direction_from_deg: float,
    config: CostModelConfig | None = None,
    criterion: str = "balanced",
    time_weight: float | None = None,
) -> EdgeCostResult:
    """هزینه دینامیکی عبور از یال (نقطه ۱ → نقطه ۲) را با در نظر گرفتن باد واقعی محاسبه می‌کند.

    پارامترها
    ----------
    lat1, lon1, lat2, lon2 : float
        مختصات جغرافیایی دو سر یال (درجه).
    wind_speed_mps : float
        سرعت باد در راستای یال، بر حسب متر بر ثانیه (نامنفی).
    wind_direction_from_deg : float
        جهت (هواشناسی) بادِ منبع، بر حسب درجه.
    config : CostModelConfig, اختیاری
        فرض‌های فیزیکی مدل. در صورت عدم ارائه، مقادیر پیش‌فرض استفاده می‌شود.
    criterion : {"time", "energy", "balanced"}
        معیار بهینگی که مقدار ``cost`` نهایی بر اساس آن انتخاب می‌شود. در هر
        سه حالت، مقادیر هر سه معیار در خروجی موجود است — فقط ``cost`` انتخاب‌شده
        تغییر می‌کند، بنابراین لایه مسیریابی می‌تواند بدون محاسبه مجدد بین
        معیارها سوییچ کند.
    time_weight : float, اختیاری
        در صورت ارائه، وزن معیار متعادل را برای همین فراخوانی override می‌کند
        (بدون نیاز به ساخت ``CostModelConfig`` جدید).

    این تابع مستقیماً توسط لایه ارکستراسیون مسیریابی (``src/pathfinding/graph.py``،
    که در گام بعدی پروژه ساخته می‌شود) به‌عنوان تابع وزن‌دهی یال قابل فراخوانی
    است: ``weight = compute_edge_cost(...).cost``.
    """
    distance_km = haversine_km(lat1, lon1, lat2, lon2)

    if config is None:
        config = CostModelConfig()
    if time_weight is None:
        time_weight = config.time_weight
    if not (0.0 <= time_weight <= 1.0):
        raise ValueError("time_weight must be within [0, 1].")
    if criterion not in ("time", "energy", "balanced"):
        raise ValueError(f"Unknown criterion {criterion!r}; expected 'time', 'energy' or 'balanced'.")

    bearing_deg = initial_bearing_deg(lat1, lon1, lat2, lon2)
    along_track_mps, cross_track_mps = decompose_wind(
        wind_speed_mps, wind_direction_from_deg, bearing_deg
    )
    ground_speed = ground_speed_mps(config.airspeed_mps, along_track_mps, cross_track_mps)
    if ground_speed <= 0:
        raise InfeasibleEdgeError(
            f"Headwind ({-along_track_mps:.2f} m/s) leaves zero or negative ground "
            f"speed ({ground_speed:.2f} m/s); this edge cannot be flown as specified."
        )

    ground_speed_kmh = ground_speed * 3.6
    time_hours = distance_km / ground_speed_kmh

    induced_penalty = 1.0 + config.induced_drag_coeff * (cross_track_mps / config.airspeed_mps) ** 2
    energy_hours = time_hours * induced_penalty

    balanced_hours = time_weight * time_hours + (1.0 - time_weight) * energy_hours

    cost_by_criterion = {
        "time": time_hours,
        "energy": energy_hours,
        "balanced": balanced_hours,
    }

    return EdgeCostResult(
        distance_km=distance_km,
        bearing_deg=bearing_deg,
        along_track_mps=along_track_mps,
        cross_track_mps=cross_track_mps,
        ground_speed_mps=ground_speed,
        time_hours=time_hours,
        energy_hours=energy_hours,
        balanced_hours=balanced_hours,
        criterion=criterion,
        cost=cost_by_criterion[criterion],
    )
