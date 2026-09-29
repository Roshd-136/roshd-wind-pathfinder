"""سنجهٔ «بادسواری واقعی»: چه سهمی از مسیر موازی باد بود و چه سهمی با باد جنگید.

مسیری که «بادسواری» نام گرفته باید با عدد قابل حسابرسی باشد، نه با ادعا. این
ماژول همان عدد را از ``leg_samples`` هر مسیر می‌سازد — یعنی از همان قطعه‌هایی که
خود الگوریتم تولید کرده، نه از بازخوانی هندسه.

قرارداد زاویه
-------------
``wind_direction_from_deg`` جهت *وزش* است (هواشناسی: از کجا می‌وزد). برای مقایسه
با سمت حرکت روی زمین، جهت «به‌سوی» باد لازم است: ``(from + 180) % 360``.
انحراف هر قطعه یعنی زاویهٔ بین سمت مسیر و جهت «به‌سوی» باد:

* ``0`` — مسیر کاملاً موازی باد و هم‌سو با آن (باد پشت، بدون پسار جانبی).
* ``90`` — مسیر عمود بر باد.
* ``180`` — مسیر درست رو-به-روی باد (بدترین حالت: باید تمام سرعت را از موتور
  گرفت).

سنجهٔ اصلی
----------
``WindAlignmentProfile.label`` یک عدد ترکیبی می‌دهد که به یک نگاه خوانده می‌شود:
``«۲° – ۹۸٪»`` یعنی «در بخش موازی، میانگین انحراف ۲ درجه بود و ۹۸ درصد مسیر موازی
بود». این همان چیزی است که در جدول صحنه خواسته شده بود و هر دو مؤلفه‌اش از داده
می‌آید، نه از یک ثابت نمایشی.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from pathfinding.effort import LegSample

__all__ = [
    "ALIGNED_TOLERANCE_DEG",
    "FIGHTING_TOLERANCE_DEG",
    "WindAlignmentProfile",
    "leg_deviation_deg",
    "wind_alignment_profile",
]

# رواداری «موازی با باد». سه درجه یعنی خطای جانبی حدود ۵ درصد سرعت باد؛ کمتر از
# آن را در دادهٔ قطعه‌ای نمی‌توان از نویز گام‌های انتگرال‌گیری تشخیص داد.
ALIGNED_TOLERANCE_DEG = 3.0

# از این زاویه به بعد، مؤلفهٔ *رو-به-روی* باد مثبت است: هواپیما با باد می‌جنگد
# (سرعت زمینی‌اش از سرعت هوایی کمتر می‌شود)، نه اینکه سوار آن باشد.
FIGHTING_TOLERANCE_DEG = 90.0


def leg_deviation_deg(leg: LegSample) -> float:
    """انحراف سمت مسیر یک قطعه از جهت «به‌سوی» باد (درجه، ۰ تا ۱۸۰)."""
    wind_toward = (float(leg.wind_direction_from_deg) + 180.0) % 360.0
    return abs((float(leg.track_bearing_deg) - wind_toward + 180.0) % 360.0 - 180.0)


@dataclass(frozen=True)
class _Bucket:
    """سهم مسافت یک بازهٔ زاویه‌ای."""

    limit_deg: float
    km: float
    share: float


@dataclass(frozen=True)
class WindAlignmentProfile:
    """کارنامهٔ هم‌راستایی مسیر با باد (همه مسافت‌وزن‌دار).

    پارامترها
    ----------
    total_km : float
        مسافت افقی کل مسیر که سنجه از آن ساخته شده.
    parallel_km : float
        مسافتی که انحرافش از ``tolerance_deg`` کمتر بود.
    parallel_mean_deg : float
        میانگین مسافت‌وزن انحراف *در همان بخش موازی*. اگر بخش موازی خالی باشد
        ``nan`` است (نه صفر: صفر یعنی «کاملاً موازی» و این‌جا هیچ قطعه‌ای نبود).
    mean_deg : float
        میانگین مسافت‌وزن انحراف در کل مسیر.
    fighting_share : float
        سهم مسافت با انحراف بیش از ۹۰ درجه (باد رو-به-رو، جنگ با باد).
    final_correction_km : float
        مسافتی از *آخرین* قطعهٔ موازی تا مقصد. این عدد جواب «تصحیح‌ها کجا
        افتادند؟» است: اگر نزدیک صفر باشد، فقط چند کیلومتر آخر با موتور تصحیح
        شده؛ اگر بزرگ باشد، تصحیح تا وسط مسیر کشیده شده است.
    buckets : tuple[_Bucket, ...]
        سهم مسافت در بازه‌های ۳/۱۰/۳۰/۹۰ درجه، برای هیستوگرام.
    tolerance_deg : float
        رواداری به‌کاررفته برای «موازی».
    """

    total_km: float
    parallel_km: float
    parallel_mean_deg: float
    mean_deg: float
    median_deg: float
    fighting_share: float
    final_correction_km: float
    buckets: tuple[_Bucket, ...] = field(default_factory=tuple)
    tolerance_deg: float = ALIGNED_TOLERANCE_DEG

    @property
    def aligned_share(self) -> float:
        """سهم مسافت موازی باد (۰ تا ۱)."""
        if self.total_km <= 0.0:
            return 0.0
        return self.parallel_km / self.total_km

    def share_within(self, limit_deg: float) -> float:
        """سهم مسافتی که انحرافش از ``limit_deg`` کمتر بود."""
        for bucket in self.buckets:
            if math.isclose(bucket.limit_deg, limit_deg):
                return bucket.share
        raise KeyError(f"no bucket for {limit_deg}")

    @property
    def label(self) -> str:
        """برچسب ترکیبی «میانگین انحراف بخش موازی – سهم موازی»."""
        if self.total_km <= 0.0:
            return "—"
        if math.isnan(self.parallel_mean_deg):
            return "— – ۰٪"
        return f"{self.parallel_mean_deg:.0f}° – {self.aligned_share * 100:.0f}٪"


def wind_alignment_profile(
    legs: Sequence[LegSample],
    tolerance_deg: float = ALIGNED_TOLERANCE_DEG,
) -> WindAlignmentProfile:
    """کارنامهٔ هم‌راستایی را از قطعه‌های یک مسیر می‌سازد.

    قطعه‌های بدون مسافت (گذارهای عمودی، یا قطعه‌های صفر) در محاسبه نمی‌آیند:
    زاویهٔ یک گذار عمودی تعریف‌شده نیست و اگر وارد میانگین شود، میانگین را
    بی‌معنا می‌کند.
    """
    if tolerance_deg <= 0.0:
        raise ValueError("tolerance_deg must be positive.")

    weights: list[float] = []
    deviations: list[float] = []
    # درازای مسیر در لحظهٔ هر قطعه، برای پیدا کردن «آخرین قطعهٔ موازی».
    cumulative: list[float] = []
    running = 0.0
    for leg in legs:
        distance = float(getattr(leg, "distance_km", 0.0))
        if distance <= 1e-9:
            continue
        weights.append(distance)
        deviations.append(leg_deviation_deg(leg))
        running += distance
        cumulative.append(running)

    total_km = running
    if total_km <= 0.0:
        return WindAlignmentProfile(
            total_km=0.0,
            parallel_km=0.0,
            parallel_mean_deg=math.nan,
            mean_deg=math.nan,
            median_deg=math.nan,
            fighting_share=0.0,
            final_correction_km=0.0,
            buckets=tuple(
                _Bucket(limit, 0.0, 0.0) for limit in (3.0, 10.0, 30.0, 90.0)
            ),
            tolerance_deg=tolerance_deg,
        )

    parallel_km = 0.0
    parallel_weighted = 0.0
    fighting_km = 0.0
    last_parallel_km = 0.0
    order = sorted(range(len(deviations)), key=lambda i: deviations[i])
    for i, distance in enumerate(weights):
        deviation = deviations[i]
        if deviation <= tolerance_deg:
            parallel_km += distance
            parallel_weighted += deviation * distance
            last_parallel_km = cumulative[i]
        if deviation > FIGHTING_TOLERANCE_DEG:
            fighting_km += distance

    weighted_sum = sum(d * w for d, w in zip(deviations, weights, strict=True))
    # میانهٔ مسافت‌وزن: اولین انحراوی که مسافت تجمعی به نیمه می‌رسد.
    half = total_km / 2.0
    median_deg = math.nan
    acc = 0.0
    for idx in order:
        acc += weights[idx]
        if acc >= half:
            median_deg = deviations[idx]
            break

    buckets = tuple(
        _Bucket(
            limit,
            sum(w for d, w in zip(deviations, weights, strict=True) if d <= limit),
            sum(w for d, w in zip(deviations, weights, strict=True) if d <= limit) / total_km,
        )
        for limit in (3.0, 10.0, 30.0, 90.0)
    )
    return WindAlignmentProfile(
        total_km=total_km,
        parallel_km=parallel_km,
        parallel_mean_deg=(parallel_weighted / parallel_km if parallel_km > 0.0 else math.nan),
        mean_deg=weighted_sum / total_km,
        median_deg=median_deg,
        fighting_share=fighting_km / total_km,
        final_correction_km=max(total_km - last_parallel_km, 0.0),
        buckets=buckets,
        tolerance_deg=tolerance_deg,
    )
