"""هندسهٔ *منحنی* مسیر: دو مرحله روی هر مسیر چندضلعی مسیریابی‌شده.

۱) ``round_path_corners`` گوشه‌های تیز را با کمان دایره‌ای (فیلت) جایگزین
   می‌کند.
۲) ``relax_path_curvature`` انحنای تمرکز‌یافته را در طول مسیر پخش می‌کند تا خط
   *منحنی* دیده شود، نه «راستِ دراز + شکستگی» (مورد دوم اندازه‌گیری‌شده: R4 یک
   بخش ۸۴ کیلومتری کاملاً راست داشت و بعد در یک نمونه ۶.۲ درجه می‌چرخید).

هیچ‌کدام از دو مرحله به کریدور یا دادهٔ خاصی وابسته نیست: ورودی هر مسیر
چندضلعی جغرافیایی است و خروجی همان قرارداد ``(path, levels)``.

مسئله

مسئله
-----
گراف مسیریابی یک شبکهٔ منظم است: گره‌ها روی گام‌های ۰.۰۵ درجه عرض و ۰.۱ درجه
طول می‌نشینند و هر یال یک پارهٔ خط مستقیم است. پس هر مسیر گرافی — حتی مسیری که
الگوریتم «نرم» تولید می‌کند — دنباله‌ای از پاره‌های **کاملاً مستقیم** است که در
گره‌ها به هم می‌رسند و گوشه می‌سازند.

اندازه‌گیری روی صحنهٔ تولیدشده این را نشان می‌دهد: ۹۷٪ پاره‌های رسم‌شده کمتر از
۰.۵ درجه چرخش دارند و میانگین چرخش ۰.۰۴ تا ۰.۱۸ درجه است. یعنی خطی که دیده
می‌شود عملاً یک خط شکستهٔ راست است، نه یک منحنی — و ادعای «اسپلاین نرم» در لایهٔ
نمایش فقط روی همان خط شکسته اعمال می‌شد.

روش
----
هر گوشهٔ داخلی مسیر با یک **کمان دایره‌ای (فیلت)** جایگزین می‌شود. فیلت کلاسیک
است: دو نقطهٔ مماس روی دو پارهٔ مجاور انتخاب می‌شود و بین آن‌ها کمانی با شعاع
ثابت می‌نشیند که در دو سر مماس است، پس مسیر در نقطهٔ اتصال هم G1 پیوسته است.

سه قید هم‌زمان رعایت می‌شود:

۱) **شعاع از پاره‌ها بزرگ‌تر نشود.** طول مماس حداکثر ۴۵٪ طول هر پارهٔ مجاور است.
   وگرنه فیلت دو گوشهٔ پشت‌سرهم را می‌خورد یا از پاره رد می‌شود.

۲) **زمین قید سخت است.** فیلت «گوشه را می‌برد» و از داخل مثلثی می‌گذرد که سه
   رأسش گره‌های امن مسیرند. داخل آن مثلث می‌تواند یال کوه باشد که هیچ‌کدام از
   یال‌ها نمی‌دیدند. پس ارتفاع زمین روی خود کمان نمونه‌برداری می‌شود و اگر
   فاصلهٔ ایمنی زیر حد مجاز برود، شعاع کوچک می‌شود و دوباره امتحان می‌شود؛ اگر
   با کمترین شعاع هم نشد، همان گوشهٔ تیز دست‌نخورده می‌ماند. اولویت با زمین است،
   نه با زیبایی منحنی.

۳) **ارتفاع هر نقطه از خود مسیر بیاید، نه از یک عدد تازه.** هر نمونهٔ کمان به
   نزدیک‌ترین نقطه روی مسیر *اصلی* تصویر می‌شود و سطح همان نقطه را می‌گیرد. پس
   پروفیل عمودی مسیر عوض نمی‌شود؛ فقط افق آن منحنی می‌شود.

آنچه این ماژول **نمی‌کند**
-------------------------
هزینه‌ها را عوض نمی‌کند. مسافت، زمان، انرژی و سوخت همان چیزی می‌ماند که روتر روی
گراف حساب کرده است. فیلت مسیر را کمی *کوتاه‌تر* می‌کند (گوشه را می‌برد) و همان
کوتاه‌شدن جزئی در هیچ‌کدام از اعداد جدول حساب نمی‌شود — عدد گزارش‌شده همان مسافت
پیموده‌شده بین گره‌ها است، یعنی چیزی که روتر واقعاً بهینه کرده است.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

__all__ = [
    "round_path_corners",
    "relax_path_curvature",
    "MAX_TANGENT_FRACTION",
    "RELAX_STEP_KM",
    "RELAX_MAX_TURN_DEG_PER_KM",
    "RELAX_MAX_DEVIATION_KM",
    "RELAX_SPREAD_SAMPLES",
]

# تبدیل درجه به کیلومتر در عرض جغرافیایی خراسان (همان عدد بقیهٔ پروژه).
_KM_PER_DEG_LAT = 111.32

# سهم بیشینهٔ هر پاره که می‌تواند صرف مماس فیلت شود. ۰.۴۵ یعنی دو فیلت روی دو
# سر یک پاره هرگز به هم نمی‌رسند (۰.۹ < ۱) و برای پاره‌های میانی جا می‌ماند.
MAX_TANGENT_FRACTION = 0.8

# کمترین شعاعی که *معنا* دارد (کیلومتر). کوچک‌تر از این، فیلت عملاً دیده نمی‌شود
# و فقط چند نقطهٔ اضافی به هندسه می‌افزاید.
MIN_RADIUS_KM = 0.35


def _nearest_arc_distance(
    plane: Sequence[tuple[float, float]],
    cumulative: Sequence[float],
    x: float,
    y: float,
) -> float:
    """مسافت کمانی نزدیک‌ترین نقطهٔ یک چندضلعی به یک نقطهٔ دلخواه (کیلومتر).

    چرا لازم است؟ وقتی نمونه‌ای *در طول* مسیر جابه‌جا می‌شود، مختصاتش دیگر به
    ایندکس قبلی‌اش روی مسیر اصلی نمی‌خورد. هر قیدی که ارتفاع را با «ایندکس» یا
    «مسافت کمانی قدیمی» بردارد، ارتفاع *جای دیگری* را با زمین *جای جدید* می‌سنجد؛
    روی پروفیل صعود/فرود این اختلاف تا صدها متر می‌شود. این تابع مسافت کمانی
    واقعی تصویرِ نمونه را می‌دهد تا ارتفاع و زمین به یک نقطه اشاره کنند.
    """
    best_distance = 0.0
    best_error = math.inf
    for index in range(len(plane) - 1):
        ax, ay = plane[index]
        bx, by = plane[index + 1]
        dx, dy = bx - ax, by - ay
        span = dx * dx + dy * dy
        if span <= 1e-12:
            continue
        t = ((x - ax) * dx + (y - ay) * dy) / span
        t = min(max(t, 0.0), 1.0)
        px, py = ax + t * dx, ay + t * dy
        error = math.hypot(x - px, y - py)
        if error < best_error:
            best_error = error
            best_distance = cumulative[index] + t * math.sqrt(span)
    return best_distance


def round_path_corners(
    path: Sequence[tuple[float, float]],
    levels: Sequence[float],
    *,
    radius_km: float = 3.0,
    min_turn_deg: float = 1.0,
    arc_step_km: float = 0.4,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    min_clearance_m: float = 0.0,
    shrink_factor: float = 0.5,
    max_attempts: int = 6,
) -> tuple[list[tuple[float, float]], list[float]]:
    """گوشه‌های تیز مسیر را با کمان دایره‌ای گرد می‌کند.

    پارامترها
    ----------
    path : Sequence[tuple[float, float]]
        نقاط مسیر (عرض، طول) به ترتیب حرکت. نقطهٔ اول و آخر دست‌نخورده می‌مانند.
    levels : Sequence[float]
        ارتفاع هر نقطه (متر) با همان قرارداد ``RouteResult`` (صفر = روی زمین).
        ارتفاع نمونه‌های تازه از تصویر کردن آن‌ها روی مسیر اصلی می‌آید، پس پروفیل
        عمودی عوض نمی‌شود.
    radius_km : float
        شعاع *هدف* فیلت. شعاع واقعی هر گوشه از طول پاره‌های مجاور و از قید زمین
        کوچک‌تر می‌شود.
    min_turn_deg : float
        گوشه‌هایی که کمتر از این مقدار می‌چرخند گرد نمی‌شوند. با نمونه‌های ۰.۵
        کیلومتری، هر نقطهٔ *داخلی* مسیر کمی می‌چرخد؛ بدون این آستانه، هزاران فیلت
        بی‌معنا ساخته می‌شد.
    arc_step_km : float
        فاصلهٔ نمونه‌های روی کمان.
    ground_elevation_at : Callable[[float, float], float], اختیاری
        ارتفاع زمین. اگر داده شود، قید ۲ بالا اعمال می‌شود.
    min_clearance_m : float
        کمترین فاصلهٔ مجاز از زمین (متر) روی نمونه‌های کمان.
    shrink_factor, max_attempts : float, int
        در هر شکست قید زمین، شعاع در ``shrink_factor`` ضرب می‌شود؛ پس از
        ``max_attempts`` بار، گوشه تیز می‌ماند.

    برمی‌گرداند
    ----------
    (path, levels)
        مسیر گردشده و ارتفاع هر نقطهٔ آن. طول هر دو یکی است و بزرگ‌تر یا مساوی
        ورودی است (هر فیلت چند نمونه اضافه می‌کند).
    """
    if len(path) != len(levels):
        raise ValueError(
            f"path and levels must have the same length, got {len(path)} and "
            f"{len(levels)}."
        )
    points = [(float(lat), float(lon)) for lat, lon in path]
    heights = [float(level) for level in levels]
    if len(points) < 3 or radius_km <= MIN_RADIUS_KM:
        return points, heights
    if arc_step_km <= 0.0:
        raise ValueError("arc_step_km must be positive.")
    if not 0.0 < shrink_factor < 1.0:
        raise ValueError("shrink_factor must be in (0, 1).")

    # صفحهٔ محلی: عرض جغرافیایی میانی به‌عنوان مبدأ. کمان‌ها روی این صفحه ساخته
    # می‌شوند و در پایان به درجه برمی‌گردند.
    lat0 = sum(lat for lat, _lon in points) / len(points)
    cos_lat = max(math.cos(math.radians(lat0)), 1e-6)

    def to_km(lat: float, lon: float) -> tuple[float, float]:
        return (lon * cos_lat * _KM_PER_DEG_LAT, lat * _KM_PER_DEG_LAT)

    def to_degrees(x: float, y: float) -> tuple[float, float]:
        return (y / _KM_PER_DEG_LAT, x / (_KM_PER_DEG_LAT * cos_lat))

    plane = [to_km(lat, lon) for lat, lon in points]

    # مسافت تجمعی مسیر اصلی: هم برای آستانه‌های طول پاره و هم برای تصویر کردن
    # نمونه‌های کمان روی مسیر اصلی (تا ارتفاع درست را بگیرند).
    cumulative = [0.0]
    for (x1, y1), (x2, y2) in zip(plane, plane[1:], strict=False):
        cumulative.append(cumulative[-1] + math.hypot(x2 - x1, y2 - y1))
    total_km = cumulative[-1]
    if total_km <= 0.0:
        return points, heights

    def level_at(distance_km: float) -> float:
        """ارتفاع مسیر اصلی در یک مسافت مشخص (تابع پله‌ای روی گره‌ها)."""
        index = 0
        while index + 1 < len(cumulative) and cumulative[index + 1] <= distance_km + 1e-9:
            index += 1
        return heights[min(index, len(heights) - 1)]

    def project_distance_km(x: float, y: float) -> float:
        """مسافت نزدیک‌ترین نقطهٔ مسیر اصلی به یک نقطه (کیلومتر)."""
        return _nearest_arc_distance(plane, cumulative, x, y)

    def arc_ok(samples: list[tuple[float, float]]) -> bool:
        """قید زمین روی نمونه‌های کمان: فاصلهٔ ایمنی برقرار است؟"""
        if ground_elevation_at is None:
            return True
        for x, y in samples:
            lat, lon = to_degrees(x, y)
            try:
                level = level_at(project_distance_km(x, y))
            except Exception:  # pragma: no cover - تصویر کردن هرگز خطا نمی‌دهد
                return False
            # گرهٔ زمین (سطح صفر) فیلت نمی‌گیرد؛ همان‌جا کف عوض می‌شود.
            if level <= 0.0:
                continue
            clearance = level - float(ground_elevation_at(lat, lon))
            if clearance < min_clearance_m:
                return False
        return True

    out_plane: list[tuple[float, float]] = [plane[0]]
    out_distance: list[float] = [0.0]

    # **گره‌های هم‌مکان متوالی را این‌جا هم حذف کن** (همان برگشت‌های خیالی
    # ±۷۵°/±۱۵۵° در دو سر مسیر — مبدأ/مقصدِ زمین که روی مختصاتِ گرهٔ هوایی
    # می‌نشینند). بدون این، خروجی فیلت خودش دو پارهٔ صفر دارد که پروفیل
    # چرخشِ مرحلهٔ بعد را منفجر می‌کند (اندازه‌گیری: بدترین نمونهٔ خروجی
    # relax روی R4 از ۹ به ۵۵ درجه بر کیلومتر).
    dedup_plane: list[tuple[float, float]] = []
    dedup_distance: list[float] = []
    for point, distance in zip(plane, cumulative, strict=True):
        if dedup_plane and point == dedup_plane[-1]:
            continue
        dedup_plane.append(point)
        dedup_distance.append(distance)
    plane = dedup_plane
    cumulative = dedup_distance
    total_km = cumulative[-1]
    if len(plane) < 3:
        rounded = [to_degrees(x, y) for x, y in plane]
        rounded_levels = [heights[min(index, len(heights) - 1)] for index in range(len(rounded))]
        if rounded_levels:
            rounded_levels[0] = heights[0]
            rounded_levels[-1] = heights[-1]
        return rounded, rounded_levels

    for index in range(1, len(plane) - 1):
        ax, ay = plane[index - 1]
        bx, by = plane[index]
        cx, cy = plane[index + 1]

        prev_len = math.hypot(bx - ax, by - ay)
        next_len = math.hypot(cx - bx, cy - by)
        if prev_len <= 1e-9 or next_len <= 1e-9:
            out_plane.append((bx, by))
            out_distance.append(cumulative[index])
            continue

        u1x, u1y = (bx - ax) / prev_len, (by - ay) / prev_len
        u2x, u2y = (cx - bx) / next_len, (cy - by) / next_len
        # زاویهٔ بین دو پاره. زاویهٔ ۰ یعنی مسیر راست است و فیلتی لازم نیست.
        dot = max(min(u1x * u2x + u1y * u2y, 1.0), -1.0)
        turn_deg = math.degrees(math.acos(dot))
        if turn_deg < min_turn_deg:
            out_plane.append((bx, by))
            out_distance.append(cumulative[index])
            continue

        max_tangent = MAX_TANGENT_FRACTION * min(prev_len, next_len)
        tangent = min(radius_km, 0.5 * max_tangent)
        placed = False
        for _attempt in range(max_attempts):
            if tangent < MIN_RADIUS_KM:
                break
            # فیلت: دو نقطهٔ مماس به فاصلهٔ ``tangent`` از گوشه روی دو پاره.
            t1 = (bx - u1x * tangent, by - u1y * tangent)
            t2 = (bx + u2x * tangent, by + u2y * tangent)
            samples = _arc_samples(t1, t2, u1x, u1y, u2x, u2y, tangent, arc_step_km)
            if not arc_ok(samples):
                tangent *= shrink_factor
                continue
            out_plane.extend(samples)
            out_distance.extend(project_distance_km(x, y) for x, y in samples)
            placed = True
            break
        if not placed:
            # زمین اجازه نداد؛ گوشه همان‌طور تیز می‌ماند (اولویت با زمین است).
            out_plane.append((bx, by))
            out_distance.append(cumulative[index])

    out_plane.append(plane[-1])
    out_distance.append(total_km)

    rounded = [to_degrees(x, y) for x, y in out_plane]
    rounded_levels = [level_at(distance) for distance in out_distance]
    # قرارداد دو سر مسیر: همان مقداری که ورودی داده بود (صفر = روی زمین)، نه
    # ارتفاع زمین. ``level_at`` روی گرهٔ زمین ارتفاع *سطح* آن را برمی‌گرداند و
    # اگر همان‌جا گزارش شود، قرارداد ``RouteResult`` می‌شکند.
    rounded_levels[0] = heights[0]
    rounded_levels[-1] = heights[-1]
    return rounded, rounded_levels


def _arc_samples(
    t1: tuple[float, float],
    t2: tuple[float, float],
    u1x: float,
    u1y: float,
    u2x: float,
    u2y: float,
    tangent: float,
    arc_step_km: float,
) -> list[tuple[float, float]]:
    """نمونه‌های کمان فیلت بین دو نقطهٔ مماس ``t1`` و ``t2``.

    هندسه: ``φ`` زاویهٔ داخلی گوشه است (بین ``-u1`` و ``u2``). با طول مماس
    ``t``، شعاع کمان ``r = t·tan(φ/2)`` و فاصلهٔ مرکز از گوشه ``t/cos(φ/2)``
    می‌شود. مرکز روی نیمساز داخلی گوشه می‌نشیند؛ نیمساز همان
    ``normalize(u2 − u1)`` است. پس کمان بدون حل مثلث، مستقیم از ``t`` ساخته
    می‌شود و مماس‌بودن در دو سر تضمین‌شده است.

    برای گوشهٔ خیلی باز (چرخش نزدیک صفر) ``tan(φ/2)`` بزرگ می‌شود و کمان به یک
    منحنی ملایم با شعاع بزرگ می‌رسد — مطلوب است. برای گوشهٔ خیلی تیز (بازگشت
    نزدیک ۱۸۰ درجه) شعاع کوچک می‌شود؛ حالت بیمارگونهٔ مسیر است و همان کمان
    کوچک هم از گوشهٔ تیز بهتر است.
    """
    # نیمساز داخلی: میانگین دو بردار یکه، نرمال‌شده.
    bis_x, bis_y = u2x - u1x, u2y - u1y
    norm = math.hypot(bis_x, bis_y)
    if norm <= 1e-9:
        return [t1, t2]
    bis_x, bis_y = bis_x / norm, bis_y / norm
    dot = max(min(-u1x * u2x - u1y * u2y, 1.0), -1.0)
    phi = math.acos(dot)
    half = min(max(phi / 2.0, math.radians(1.0)), math.radians(89.0))
    radius = tangent * math.tan(half)
    if radius <= 1e-9:
        return [t1, t2]
    # گوشه همان نقطه‌ای است که دو نقطهٔ مماس را به هم وصل می‌کند.
    corner = (t1[0] + u1x * tangent, t1[1] + u1y * tangent)
    offset = tangent / math.cos(half)
    center = (corner[0] + bis_x * offset, corner[1] + bis_y * offset)

    a1 = math.atan2(t1[1] - center[1], t1[0] - center[0])
    a2 = math.atan2(t2[1] - center[1], t2[0] - center[0])
    sweep = a2 - a1
    while sweep > math.pi:
        sweep -= 2.0 * math.pi
    while sweep < -math.pi:
        sweep += 2.0 * math.pi
    arc_length = abs(sweep) * radius
    count = max(int(math.ceil(arc_length / arc_step_km)), 2)
    samples: list[tuple[float, float]] = []
    for step in range(count + 1):
        angle = a1 + sweep * step / count
        samples.append((center[0] + radius * math.cos(angle),
                        center[1] + radius * math.sin(angle)))
    return samples


# ---------------------------------------------------------------------------
# پخش‌کردن انحنا: از «پاره‌های راست + گوشه» به یک منحنی با انحنای پیوسته
# ---------------------------------------------------------------------------

# فاصلهٔ نمونه‌های بازنمونه‌شدهٔ منحنی (کیلومتر). ریزتر از گام گزارش (۰.۵ km)
# تا هیچ بند انگشتی از هندسه در نمونه‌برداری بعدی گم نشود.
RELAX_STEP_KM = 0.25

# سقف *هدف* چرخش محلی (درجه بر کیلومتر). چشم، «شکستگی» را با آهنگ چرخش در واحد
# طول می‌بیند، نه با زاویهٔ کل گوشه: یک چرخش ۶ درجه‌ای در یک گام ۰.۳ کیلومتری
# ۲۰ درجه بر کیلومتر است و مثل یک شکستگی دیده می‌شود، ولی همان ۶ درجه اگر در
# ۳ کیلومتر پخش شود یک خم آرام است. مسیرهای بادسواری (که با انتگرال‌گیری گام‌به‌گام
# ساخته می‌شوند) عملاً همین ترتیب را دارند و همین است که آن‌ها را «نرم» نشان می‌دهد.
RELAX_MAX_TURN_DEG_PER_KM = 1.5

# پهنای هستهٔ گاوسی پخش چرخش، بر حسب *نمونهٔ* ۰.۲۵ کیلومتری. این عدد سرعت
# همگرایی را تعیین می‌کند و از اندازه‌گیری آمده: نسخه‌ای که مازاد هر نمونه را فقط
# به دو همسایهٔ فوری می‌داد (انتشار شعاع ۱ نمونه در هر پاس) برای خوشهٔ شکستگی
# ۵۷ نمونه‌ای مسیرهای گرافی به ~۱۰۰۰ پاس نیاز داشت — بودجهٔ ۱۲۰ پاس همیشه پیش
# از همگرایی تمام می‌شد و همان «راستِ دراز + خوشهٔ گوشه» روی صحنه می‌ماند.
# گاوسی با σ = ۸ نمونه (۲ کیلومتر) در هر پاس چند کیلومتر پخش می‌کند؛ همان
# خوشه در ~۳۰ پاس روی می‌نشیند. هیچ‌کدام به کریدور خاصی وابسته نیست.
RELAX_SPREAD_SAMPLES = 8.0

# **قید سخت**: بیشینهٔ جابه‌جایی هر نمونه از جای خودش روی مسیر مسیریابی‌شده
# (کیلومتر). این عدد سقف «آزادی هنری» است و عمداً کوچک است: گام شبکهٔ مسیریابی
# ۵.۶ × ۹ کیلومتر است، پس ۱.۵ کیلومتر انحراف درون همان ابهامی است که خودِ گره‌بندی
# گراف دارد — اما بیشتر از آن دیگر «همان مسیر» نیست و باید صریح رد شود.
RELAX_MAX_DEVIATION_KM = 2.5

# سقف تکرار پاس‌های هموارسازی. یک پاس = یک گام انتشار گرما؛ تعداد لازم از
# اندازهٔ شکستگی‌ها می‌آید ولی این سقف جلوی حلقه‌های بی‌پایان را می‌گیرد.
RELAX_MAX_PASSES = 120

def relax_path_curvature(
    path: Sequence[tuple[float, float]],
    levels: Sequence[float],
    *,
    step_km: float = RELAX_STEP_KM,
    max_turn_deg_per_km: float = RELAX_MAX_TURN_DEG_PER_KM,
    max_deviation_km: float = RELAX_MAX_DEVIATION_KM,
    max_passes: int = RELAX_MAX_PASSES,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    min_clearance_m: float = 0.0,
) -> tuple[list[tuple[float, float]], list[float]]:
    """انحنای مسیر را روی کل طول پخش می‌کند تا *منحنی* دیده شود، نه شکستگی.

    مسئله
    -----
    مسیر گرافی دنباله‌ای از پاره‌های مستقیم است. ``round_path_corners`` گوشه‌ها را
    با کمان گرد می‌کند، ولی خودِ پاره‌ها راست می‌مانند و کمان کوتاه است؛ نتیجه
    اندازه‌گیری‌شده روی صحنهٔ منتشرشده: مسیر R4 یک بخش **۸۴ کیلومتری کاملاً راست**
    دارد و بعد در یک نمونهٔ ۰.۳ کیلومتری ۶.۲ درجه می‌چرخد (≈ ۲۱ درجه بر کیلومتر).
    همین «راستِ دراز + شکستگی» است که مسیرهای گرافی را ماشینی نشان می‌دهد، در
    حالی که مسیرهای بادسواری (که گام‌به‌گام انتگرال گرفته می‌شوند) چرخش را در طول
    مسیر پخش می‌کنند و چشم آن‌ها را منحنی می‌بیند.

    روش
    ----
    مسیر با گام یکنواخت بازنمونه‌شده و سپس **پروفیل چرخش** پردازش می‌شود: هر
    نمونهٔ داخلی یک گام چرخش دارد و نمونه‌ای که از سقف بیشتر شود، مازادش با
    **هستهٔ گاوسی** (σ = ``RELAX_SPREAD_SAMPLES`` نمونه) روی همسایه‌های دور و بر
    پخش می‌شود — نه فقط دو همسایهٔ فوری. جمع چرخش در هر پاس دقیقاً حفظ می‌شود
    (وزن‌ها نرمال‌اند)، پس شکل مسیر و دو سر آن (میخ‌شده) می‌ماند و فقط *تمرکز*
    انحنا در طول مسیر پخش می‌گردد.

    سه قید هم‌زمان
    -------------
    ۱) ``max_turn_deg_per_km`` — هدف کیفیت: تا وقتی چرخش محلی از این آستانه
       کم نشده، پاس‌ها ادامه دارند. اگر با بیشینهٔ انحراف قابل‌قبول به هدف نرسد،
       همان بهترین حالت برمی‌گردد (بهترین تلاش، نه یک وعده).
    ۲) ``max_deviation_km`` — قید سخت: اگر پاس بعدی هر نمونه‌ای را بیش از این از
       جای خودش روی مسیر مسیریابی‌شده دور کند، همان پاس پذیرفته نمی‌شود. پس
       هندسه هرگز «یک چیز دیگر» نمی‌شود.
    ۳) **زمین** — قید سخت‌تر: روی هر نمونه ارتفاع مسیر (از تصویر نقطه روی مسیر
       اصلی) با زمین همان نقطه سنجیده می‌شود و **اجازه ندارد از فاصلهٔ ایمنی
       مسیر مسیریابی‌شده بدتر شود**. آن نمونه به اندازهٔ لازم به سمت مسیر اصلی
       کشیده می‌شود (با وزنی که در همسایگی نرم می‌شود). دقت کنید که این قاعده
       «نسبت به ورودی» است، نه «کمینهٔ مطلق»: خودِ گراف لبه‌ها را روی چند نقطه
       بررسی می‌کند، پس ممکن است مسیر ورودی جایی فاصلهٔ ایمنی‌اش کمتر از
       آستانه باشد و قاعدهٔ مطلق همهٔ نرم‌شدن را رد می‌کرد (اندازه‌گیری‌شده روی
       همین کریدور). کمبود خودِ روتر در ستون «کمینه فاصله از زمین» جدول دیده
       می‌شود؛ این تابع نه آن را بهتر می‌کند و نه پنهان.

    ارتفاع هر نمونه از خود مسیر اصلی می‌آید (تصویر بر پایهٔ مسافت کمانی)، پس
    پروفیل عمودی دست‌نخورده می‌ماند و قرارداد دو سر مسیر (صفر = روی زمین) حفظ
    می‌شود.

    عمومی بودن
    ----------
    هیچ ثابتی این‌جا به کریدور مشهد–سبزوار وابسته نیست: ورودی هر چندضلعی دلخواه
    در مختصات جغرافیایی است و خروجی همان قرارداد ``(path, levels)`` مرحلهٔ فیلت.
    هر مسیر چندضلعی (گرافی یا هر مسیر دیگری که از گره می‌گذرد) از همین تابع رد
    می‌شود؛ مسیرهای بادسواری مسیرِ خودشان را گام‌به‌گام می‌سازند و همین حالا
    انحنای پیوسته دارند (این تابع روی آن‌ها تقریباً کاری نمی‌کند).

    برمی‌گرداند
    ----------
    (path, levels)
        تعداد نمونه‌ها از ورودی بیشتر است (گام یکنواخت ۰.۲۵ کیلومتر)؛ ترتیب حرکت
        و دو سر مسیر یکی است.
    """
    if len(path) != len(levels):
        raise ValueError(
            f"path and levels must have the same length, got {len(path)} and "
            f"{len(levels)}."
        )
    if step_km <= 0.0:
        raise ValueError("step_km must be positive.")
    if max_turn_deg_per_km <= 0.0:
        raise ValueError("max_turn_deg_per_km must be positive.")
    if max_deviation_km <= 0.0:
        raise ValueError("max_deviation_km must be positive.")

    points = [(float(lat), float(lon)) for lat, lon in path]
    heights = [float(level) for level in levels]
    # **حذف گره‌های هم‌مکان متوالی.** گراف گرهٔ زمینِ مبدأ/مقصد را روی همان
    # مختصاتِ گرهٔ هوایی می‌گذارد؛ پارهٔ صفرِ بعدی در پروفیل چرخش یک برگشت
    # خیالی می‌سازد (atan2(0,0)) — اندازه‌گیری‌شده روی R4: دو قلهٔ کاذب
    # ±۷۵.۵° و ±۱۵۵° در دو سر مسیر که صحنه آن‌ها را «شکستگی» نشان می‌داد.
    # گرهٔ *زمین* (کمینهٔ ارتفاع) نگه داشته می‌شود تا قرارداد «صفر = روی
    # زمین» دو سر مسیر دست‌نخورده بماند و صعود/فرود از سطح زمین ساخته شود.
    cleaned: list[tuple[float, float]] = []
    cleaned_levels: list[float] = []
    for point, level in zip(points, heights, strict=True):
        if cleaned and point == cleaned[-1]:
            cleaned_levels[-1] = min(cleaned_levels[-1], level)
            continue
        cleaned.append(point)
        cleaned_levels.append(level)
    points, heights = cleaned, cleaned_levels
    if len(points) < 3:
        return points, heights

    lat0 = sum(lat for lat, _lon in points) / len(points)
    cos_lat = max(math.cos(math.radians(lat0)), 1e-6)

    def to_km(lat: float, lon: float) -> tuple[float, float]:
        return (lon * cos_lat * _KM_PER_DEG_LAT, lat * _KM_PER_DEG_LAT)

    def to_degrees(x: float, y: float) -> tuple[float, float]:
        return (y / _KM_PER_DEG_LAT, x / (_KM_PER_DEG_LAT * cos_lat))

    plane = [to_km(lat, lon) for lat, lon in points]
    cumulative = [0.0]
    for (x1, y1), (x2, y2) in zip(plane, plane[1:], strict=False):
        cumulative.append(cumulative[-1] + math.hypot(x2 - x1, y2 - y1))
    total_km = cumulative[-1]
    if total_km <= step_km:
        return points, heights

    def level_at(distance_km: float) -> float:
        # مقدار پله‌ای عمداً حفظ شده: قرارداد «صفر = روی زمین» یعنی پارهٔ
        # برخاست/فرود گارد ایمنی نمی‌گیرد. میان‌یابی خطی این‌جا آزموده شد و
        # درست درآمد نداشت: از گرهٔ زمین (صفر) تا گرهٔ کروز میان‌یابی می‌کرد
        # و ارتفاع‌های خیلی زیر زمین می‌ساخت (تست رشته‌کوه را می‌شکست).
        # پیوستگیِ پروفیل عمودی حالا کارِ ترتیب تازهٔ خط‌لولهٔ روتر است:
        # ``ramp_vertical_transitions`` *پیش* از این تابع اجرا می‌شود تا
        # گارد زمین پروفیل واقعی پیوسته را ببیند، نه پلهٔ لایه‌ها.
        index = 0
        while index + 1 < len(cumulative) and cumulative[index + 1] <= distance_km + 1e-9:
            index += 1
        return heights[min(index, len(heights) - 1)]

    # **ارتفاعِ جای *جدید*، نه ارتفاعِ ایندکس قدیمی.** توزیع انحنا نمونه را در
    # طول مسیر جابه‌جا می‌کند؛ هر گاردی که ارتفاع را با ایندکس یا مسافت کمانیِ
    # قدیمی بردارد، ارتفاعِ یک نقطه را با زمینِ نقطهٔ دیگری می‌سنجد. اندازه‌گیری
    # روی R1/R2: روی پروفیل صعود/فرود نزدیک مشهد، همین ناهم‌خوانی گارد را
    # وادار می‌کرد نمونه‌های امن را «متخلف» ببیند و نرم‌شدن روی کف ایمنی
    # میخکوب می‌شد (بدترین چرخش ۱۱.۸ درجه بر کیلومتر با خوشهٔ متناوب‌العلامت
    # در ارتفاع ۱۷۹۰ متری جایی که زمین ۱۴۹۰ متر است).
    def level_here(x: float, y: float) -> float:
        return level_at(_nearest_arc_distance(plane, cumulative, x, y))

    # ------------------------------------------------------------------
    # بازنمونه‌برداری یکنواخت: نقاطی که روی مسیر *اصلی* می‌نشینند و مرجع سنجش
    # انحراف‌اند. هر نمونهٔ منحنی بعداً فقط حول همین مرجع حرکت می‌کند.
    # ------------------------------------------------------------------
    count = max(int(math.ceil(total_km / step_km)) + 1, 3)
    base: list[tuple[float, float]] = []
    distances: list[float] = []
    segment = 0
    for index in range(count):
        distance = total_km * index / (count - 1)
        while (
            segment + 1 < len(cumulative) - 1
            and cumulative[segment + 1] < distance - 1e-9
        ):
            segment += 1
        span = cumulative[segment + 1] - cumulative[segment]
        ratio = 0.0 if span <= 1e-12 else (distance - cumulative[segment]) / span
        ratio = min(max(ratio, 0.0), 1.0)
        (x1, y1), (x2, y2) = plane[segment], plane[segment + 1]
        base.append((x1 + (x2 - x1) * ratio, y1 + (y2 - y1) * ratio))
        distances.append(distance)
    base[0] = plane[0]
    base[-1] = plane[-1]

    def turns_deg(samples: Sequence[tuple[float, float]]) -> list[float]:
        """اندازهٔ چرخش در هر نمونهٔ داخلی (درجه)."""
        result: list[float] = []
        for index in range(1, len(samples) - 1):
            ax, ay = samples[index - 1]
            bx, by = samples[index]
            cx, cy = samples[index + 1]
            first = math.atan2(bx - ax, by - ay)
            second = math.atan2(cx - bx, cy - by)
            delta = math.degrees(second - first)
            while delta > 180.0:
                delta -= 360.0
            while delta < -180.0:
                delta += 360.0
            result.append(abs(delta))
        return result

    def deviation_km(samples: Sequence[tuple[float, float]]) -> float:
        """بیشینهٔ فاصلهٔ نمونه‌ها از جای خودشان روی مسیر اصلی."""
        return max(
            math.hypot(x - bx, y - by)
            for (x, y), (bx, by) in zip(samples, base, strict=False)
        )

    def bearings(samples: Sequence[tuple[float, float]]) -> list[float]:
        """سمت هر پاره (رادیان از شمال)."""
        return [
            math.atan2(bx - ax, by - ay)
            for (ax, ay), (bx, by) in zip(samples, samples[1:], strict=False)
        ]

    def wrap(value: float) -> float:
        """زاویه را به بازهٔ (−π, π] می‌آورد."""
        return (value + math.pi) % (2.0 * math.pi) - math.pi

    # ------------------------------------------------------------------
    # سقف زمین برای هر نمونه: **نه کمتر از خود مسیر مسیریابی‌شده**.
    #
    # چرا «کمینهٔ مطلق» کافی نبود؟ چون گراف لبه‌ها را فقط روی چند نقطهٔ نمونه
    # بررسی می‌کند (گاه ۷ نقطه روی یک یال ۹ کیلومتری)، پس خودمسیرِ مسیریابی‌شده
    # می‌تواند جایی فاصلهٔ ایمنی‌اش کمتر از آستانه باشد. با قاعدهٔ مطلق، چنین
    # مسیری در پاس اول رد می‌شد و **هیچ** نرم‌شدنی نمی‌گرفت — اندازه‌گیری روی
    # آرتیفکت همین را نشان داد: R1/R2 (۲۹۰۰ m) و R4 (۲۲۰۰ m) که به رشته‌کوه
    # نزدیک‌اند دست‌نخورده می‌ماندند، در حالی که R3/R6 در ۳۶۰۰ m نرم می‌شدند.
    # قاعدهٔ درست همین است: نرم‌کردن نباید ایمنی را *کم* کند؛ کمبودی که خودِ
    # روتر دارد چیز دیگری است و پنهان نمی‌شود (ستون «کمینه فاصله از زمین» جدول).
    # ------------------------------------------------------------------
    allowed_clearance: list[float] = []
    for index, (x, y) in enumerate(base):
        level = level_at(distances[index])
        if level <= 0.0 or ground_elevation_at is None or min_clearance_m <= 0.0:
            allowed_clearance.append(0.0)
            continue
        lat, lon = to_degrees(x, y)
        local = level - float(ground_elevation_at(lat, lon))
        allowed_clearance.append(local if local < min_clearance_m else min_clearance_m)

    def clearance_ok(samples: Sequence[tuple[float, float]]) -> bool:
        """آیا هیچ نمونه‌ای ایمنی‌اش از مسیر اصلی *بدتر* نشده است؟"""
        for index, (x, y) in enumerate(samples):
            floor = allowed_clearance[index]
            if floor <= 0.0:
                continue
            lat, lon = to_degrees(x, y)
            level = level_here(x, y)
            if level - float(ground_elevation_at(lat, lon)) < floor - 1e-9:
                return False
        return True

    def clamp_to_terrain(
        candidate: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        """نمونه‌ای که به کوه می‌خورد، تا *آخرین* نقطهٔ امن به عقب کشیده می‌شود.

        کشیدنِ همه‌جا به عقب (یا رد کردن کل پاس) یعنی مسیری که یک جا زمین را لمس
        می‌کند هیچ‌جا نرم نشود — و اندازه‌گیری روی همین آرتیفکت نشان داد این‌طور
        می‌شود: R1/R2 (سطح ۲۹۰۰) و R4 (۲۲۰۰) دست‌نخورده می‌ماندند چون به رشته‌کوه
        نزدیک‌اند، در حالی که R3/R6 در ۳۶۰۰ متر نرم می‌شدند. پس کاهش *محلی* است:
        برای هر نمونهٔ متخلف، عامل اختلاط بین جای اصلی و جای نرم‌شده با نصف‌کردن
        دودویی تا آخرین مقدار امن کم می‌شود و این عامل در همسایگی با مینیمم پخش
        می‌شود تا خودش شکستگی نسازد.
        """
        if ground_elevation_at is None or min_clearance_m <= 0.0:
            return candidate
        blend = [1.0] * len(candidate)
        for index, (x, y) in enumerate(candidate):
            floor = allowed_clearance[index]
            if floor <= 0.0:
                continue
            lat, lon = to_degrees(x, y)
            if level_here(x, y) - float(ground_elevation_at(lat, lon)) >= floor - 1e-9:
                continue
            bx, by = base[index]
            low, high = 0.0, 1.0
            for _step in range(12):
                middle = 0.5 * (low + high)
                px, py = bx + (x - bx) * middle, by + (y - by) * middle
                plat, plon = to_degrees(px, py)
                if level_here(px, py) - float(ground_elevation_at(plat, plon)) >= floor - 1e-9:
                    low = middle
                else:
                    high = middle
            blend[index] = low
        if all(value >= 1.0 for value in blend):
            return candidate
        # پخش محلی با وزن گاوسی: کمبود ظرفیت هر نمونه با فاصله کم می‌شود، پس
        # همسایه‌ها *تدریجاً* عقب می‌کشند و خودِ عقب‌کشیدن گوشهٔ تازه نمی‌سازد.
        # (پیش‌تر مینیمم پنجرهٔ ۵ نمونه‌ای بود: یک پلهٔ ناگهانی که همان گوشهٔ
        # تازه را روی لبهٔ ناحیهٔ امن می‌ساخت — اندازه‌گیری: R4 می‌ماند با ۹.۹
        # درجه بر کیلومتر، باقی مسیرها روی ۲.۴.)
        deficit = [1.0 - value for value in blend]
        sigma = 2.0
        spread = [1.0] * len(blend)
        for index in range(len(blend)):
            pull = 0.0
            for offset in range(-4, 5):
                neighbour = index + offset
                if not 0 <= neighbour < len(deficit):
                    continue
                weight = math.exp(-0.5 * (offset / sigma) ** 2)
                pull = max(pull, deficit[neighbour] * weight)
            spread[index] = max(0.0, 1.0 - min(pull, 1.0))
        for index, (x, y) in enumerate(candidate):
            factor = spread[index]
            if factor >= 1.0:
                continue
            bx, by = base[index]
            candidate[index] = (bx + (x - bx) * factor, by + (y - by) * factor)
        return candidate

    # ------------------------------------------------------------------
    # **چرخش را پخش می‌کنیم، نه مسیر را صاف.**
    # ------------------------------------------------------------------
    # نسخهٔ اول همین تابع، عملگر انتشار گرما روی *موقعیت* بود. دو ایراد داشت و
    # هر دو روی مسیرهای واقعی همین کریدور اندازه‌گیری شدند:
    #   ۱) مسیری که انحنایش در کل طول پخش شده — مثل R4 که برای دور زدن رشته‌کوه
    #      منحنی است — را به سمت وتر می‌کشد؛ یعنی شکل *واقعی* مسیر را عوض می‌کند
    #      تا یک گوشه را نرم کند (سقف انحراف زود پر می‌شد).
    #   ۲) نتیجه: R4 با ۹.۹ درجه بر کیلومتر رها می‌شد در حالی که R1/R2/R6 به ۲.۴
    #      می‌رسیدند.
    # حالا **پروفیل چرخش** پردازش می‌شود: هر نمونهٔ داخلی یک گام چرخش دارد و اگر
    # از سقف بیشتر شود، مازادش نصف‌نصف به دو همسایه داده می‌شود. جمع چرخش ثابت
    # می‌ماند، پس شکل مسیر (از جمله دور زدن‌ها) حفظ می‌شود و فقط *تمرکز* چرخش
    # پخش می‌گردد — دقیقاً همان چیزی که یک منحنی چشم‌نواز دارد.
    base_bearings = bearings(base)
    lengths = [
        math.hypot(bx - ax, by - ay)
        for (ax, ay), (bx, by) in zip(base, base[1:], strict=False)
    ]
    turns = [0.0] * len(base)
    for index in range(1, len(base) - 1):
        turns[index] = wrap(base_bearings[index] - base_bearings[index - 1])

    def rebuild(profile: Sequence[float]) -> list[tuple[float, float]]:
        """مسیر را از مبدأ با یک پروفیل چرخش می‌سازد و مقصد را با برش می‌بندد.

        اختلاف‌ماندهٔ مقصد: پخش‌کردن چرخش طول گام‌ها را نگه می‌دارد ولی جهت پایانی
        را کمی جابه‌جا می‌کند. یک «برش» خطی در طول مسیر — که انحنای تازه‌ای نمی‌سازد
        — مقصد را دقیقاً روی مقصد می‌نشاند؛ مبدأ هم دست‌نخورده می‌ماند.
        """
        built: list[tuple[float, float]] = [base[0]]
        heading = base_bearings[0]
        for index in range(1, len(base)):
            heading += profile[index]
            px, py = built[-1]
            built.append(
                (
                    px + lengths[index - 1] * math.sin(heading),
                    py + lengths[index - 1] * math.cos(heading),
                )
            )
        residual_x = base[-1][0] - built[-1][0]
        residual_y = base[-1][1] - built[-1][1]
        if math.hypot(residual_x, residual_y) > 1e-9:
            span = len(built) - 1
            for index in range(1, span):
                weight = index / span
                px, py = built[index]
                built[index] = (px + residual_x * weight, py + residual_y * weight)
            built[-1] = base[-1]
        return built

    # **قیدها درون حلقه سنجیده می‌شوند، نه در پایان.** نسخه‌ای که همهٔ پاس‌ها را
    # اول اجرا می‌کرد و بعد قید را بررسی می‌کرد، پروفیل چرخش را آن‌قدر پخش می‌کرد
    # که مسیر به یک قوس بزرگ بدل شود؛ آن‌وقت یا کل کار رد می‌شد (R1/R2/R4
    # دست‌نخورده) یا یک حالت نیم‌کاره با گوشه‌های ۲۳ تا ۳۵ درجه می‌ماند (اندازه‌گیری
    # شد). حالا هر پاس ابتدا ساخته و سنجیده می‌شود و تنها اگر **هم** انحراف و
    # **هم** ایمنی قبول باشند پذیرفته می‌گردد؛ آخرین حالت پذیرفته‌شده خروجی است.
    # پس خروجی همیشه یک مسیر معتبر است و «بیشترین نرم‌شدنی که ایمنی می‌دهد».
    cap = math.radians(max_turn_deg_per_km * step_km)
    current: list[tuple[float, float]] | None = None
    # **σ تطبیقی**: اگر یک پاس انحراف/ایمنی را نقض کند، هستهٔ پخش *باریک‌تر* می‌شود
    # و همان پاس دوباره تلاش می‌شود — نه این‌که کل کار رها شود. با σ=۱ هر جابه‌جایی
    # محدود به یک نمونه است، پس پاس ردشدنی وجود ندارد (هر جابه‌جایی یکنمونه‌ای
    # همیشه از انحراف قبلی کوچک‌تر است). این همان تفاوت R4 بود: اولین پاسِ بزرگ
    # قید انحراف را می‌شکست و مسیر دست‌نخورده می‌ماند؛ حالا به‌تدریج باریک می‌شود
    # تا جایی که قیدها اجازهٔ ادامه بدهند.
    sigma = RELAX_SPREAD_SAMPLES
    min_sigma = 1.0
    for _pass in range(max_passes):
        if max((abs(value) for value in turns[1:-1]), default=0.0) <= cap + 1e-12:
            break
        # **انتشار حرارتی پروفیل چرخش.** تاریخچهٔ سه نسخهٔ قبلی (هر سه
        # اندازه‌گیری‌شده):
        #   ۱) نوشتن مستقیم سقف، سهمِ گرفته‌شده از همسایه‌ها را پاک می‌کرد؛
        #      هر پاس چرخش «گم» می‌شد و مقصد ۱۱ کیلومتر جابه‌جا می‌شد.
        #   ۲) دادن مازاد فقط به دو همسایهٔ فوری، برای خوشهٔ ۵۷ نمونه‌ای
        #      مسیرهای گرافی به ~۱۰۰۰ پاس نیاز داشت؛ بودجهٔ پاس می‌گذشت.
        #   ۳) گرفتن مازاد «فقط از نمونه‌های بالای سقف» کمان یکنواخت فیلت را
        #      ناهمگون می‌کرد (R4 بدتر شد: ۱۲.۸ ← ۲۰.۱) و خوشه‌ها را فقط
        #      جابه‌جا می‌کرد، نه پخش.
        # نسخهٔ کنونی هر نمونه را به سمت میانگین گاوسی همسایگی می‌کشد؛ جمع
        # چرخش تقریباً ثابت می‌ماند (دو سر میخ‌اند) و مقصد با برش پایانیِ
        # ``rebuild`` دقیق بسته می‌شود.
        n = len(turns)
        radius = max(1, int(math.ceil(3.0 * sigma)))
        weight = [
            math.exp(-0.5 * (offset / sigma) ** 2)
            for offset in range(-radius, radius + 1)
        ]
        kernel_total = sum(weight)
        weight = [value / kernel_total for value in weight]
        # **انتشار حرارتی روی پروفیل چرخش — نه فقط مازادِ بالای سقف.**
        # نسخهٔ قبلی فقط از نمونه‌های بالای سقف چرخش می‌گرفت و به همسایه‌ها
        # می‌داد؛ دو ایراد اندازه‌گیری‌شده:
        #   ۱) کمان فیلت (چرخش یکنواخت ~۱.۷° بر نمونه) بالای سقف بود؛ گرفتن
        #      مازادِ لبه‌هایش کمان یکنواخت را ناهمگون می‌کرد — روی R4
        #      بدترین نمونه از ۱۲.۸ به ۲۰.۱ درجه بر کیلومتر *بدتر* شد.
        #   ۲) نمونه‌های زیر سقف هرگز نمی‌دادند، پس «خوشه»ٔ چرخش جابه‌جا
        #      می‌شد ولی پخش نمی‌شد؛ بودجهٔ پاس تمام می‌شد و خوشه می‌ماند.
        # انتشار واقعی هر نمونه را به سمت میانگین وزنی‌گاوسی همسایگی می‌کشد؛
        # قوس یکنواخت هم مثل هر پروفیل دیگری *پهن‌تر* می‌شود — همان چرخش کل
        # روی مسافت بیشتر، یعنی دقیقاً «نرم‌تر». حفظ شکل مسیر کار سقف نیست:
        # قید انحراف (``max_deviation_km``) و قید زمین هر پاس را می‌سنجند و
        # پاسِ ردشده با هستهٔ باریک‌تر دوباره تلاش می‌شود؛ با σ=۱ جابه‌جایی
        # هر پاس چند متر است و هرگز قید نمی‌شکند، پس حلقه به «نرم‌ترین
        # منحنیِ درون بودجهٔ انحراف» همگرا می‌شود.
        alpha = 0.6
        updated = [turns[0]]
        for index in range(1, n - 1):
            local = 0.0
            wsum = 0.0
            for offset, w in zip(range(-radius, radius + 1), weight, strict=False):
                neighbour = index + offset
                if 1 <= neighbour <= n - 2:
                    local += turns[neighbour] * w
                    wsum += w
            if wsum > 0.0:
                updated.append(turns[index] + alpha * (local / wsum - turns[index]))
            else:
                updated.append(turns[index])
        updated.append(turns[n - 1])
        candidate = clamp_to_terrain(rebuild(updated))
        if deviation_km(candidate) > max_deviation_km or not clearance_ok(candidate):
            # پاس رد شد: هسته را باریک‌کن و دوباره — به‌جای رهاکردن کل کار.
            if sigma <= min_sigma + 1e-12:
                break
            sigma = max(min_sigma, sigma * 0.5)
            continue
        turns = updated
        current = candidate
        # پس از هر پاس پذیرفته‌شده، دوباره از هستهٔ پهن شروع کن: به‌محض این‌که
        # قیدها اجازه بدهند، پخش سریع برمی‌گردد.
        sigma = RELAX_SPREAD_SAMPLES

    if current is None:
        # مسیر ورودی از قبل نرم است یا قیدها اجازهٔ هیچ تغییری ندادند: همان
        # هندسهٔ مسیریابی‌شده برمی‌گردد، بدون ادعای اضافه.
        return points, heights


    relaxed = [to_degrees(x, y) for x, y in current]
    relaxed_levels = [level_at(distance) for distance in distances]
    # همان قرارداد دو سر مسیر که فیلت هم رعایت می‌کند: مقدار ورودی، نه سطح زمین.
    relaxed_levels[0] = heights[0]
    relaxed_levels[-1] = heights[-1]
    return relaxed, relaxed_levels
