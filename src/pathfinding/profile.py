"""پروفیل عمودی پرواز: تبدیل «پله»های ارتفاع به یک مسیر نرم و تدریجی.

مسئله
-----
گراف مسیریابی *لایه‌ای* است: هر گره روی یک سطح پرواز ثابت می‌نشیند و گره زمین هم
ارتفاع زمین دارد. پس هر گذر ارتفاعی در گراف یک **یال عمودی** است — گرهٔ بعدی همان‌جا
است که گرهٔ قبلی و فقط ارتفاعش عوض می‌شود. برای *جست‌وجو* این درست است (هزینهٔ گذر
جدا پرداخت می‌شود)، ولی همان مسیر که رسم شود یک دیوار عمودی است و به چشم «افتادن از
آسمان» می‌آید.

هواپیما این‌طور پرواز نمی‌کند. صعود و فرود **نرخ** دارند، پس هر گذر ارتفاعی به همان
اندازه مسافت افقی می‌خواهد، و شیب آن هم ثابت نیست: گذر با شیب صفر شروع می‌شود
(پایان بخش تراز)، به شیب بیشینه می‌رسد، و دوباره به صفر برمی‌گردد.

روش
----
پروفیل با یک «پیروِ نرخ‌محدود» ساخته می‌شود، نه با پنجره‌بندی روی هر گذر، و بعد
گوشه‌هایش گرد می‌شود:

۱) مسیر با گام ثابت نمونه‌برداری می‌شود و ارتفاع هر نمونه به **هدف** آن نقطه
   (ارتفاع گره‌ای که در آن قرار دارد) کشیده می‌شود، ولی هیچ‌گاه سریع‌تر از سقف
   شیب آن فاز:

   * گذر صعودی فقط به اندازهٔ ``سقف صعود × Δs`` جلو می‌رود، پس از نقطه‌ای که هدف
     بالا می‌رود به بعد پخش می‌شود؛
   * گذر نزولی فقط به همان اندازه، ولی *عقب‌گرد* شمارش می‌شود تا درست روی همان
     نقطه‌ای که هدف پایین می‌آید (مقصد) تمام شود.

   این دو پاس هر پروفیلی را می‌پذیرد — از جمله مسیرهایی که چند بار بالا و پایین
   می‌روند. پنجره‌بندی روی هر گذر در چنین مسیرهایی یا پنجره‌ها را روی هم
   می‌انداخت یا یکی را کوتاه می‌کرد و همان پلهٔ اول را برمی‌گرداند.

۲) **گوشه‌ها گرد می‌شوند.** پیروی نرخ‌محدود یک خط شکسته می‌دهد: تراز، رمپ با شیب
   بیشینه، تراز. همان سه‌قطعی است که «پله‌ای» دیده می‌شود. چند دور میانگین‌گیری
   وزنی روی نمونه‌های داخلی (با دو سر ثابت) شیب را در دو سر هر گذر به صفر
   می‌رساند: گذر مثل یک منحنی S شروع می‌شود، اوج می‌گیرد و تمام می‌شود. میانگین
   وزنی هیچ‌وقت از بیشینهٔ همسایگی بالاتر نمی‌رود، پس نه از سقف شیب می‌زند و نه از
   سطح هدف. یک نتیجهٔ جانبی هم دارد که همان چیزی است که فرود واقعی دارد: **فلر**
   — نزدیک مقصد شیب به‌تدریج کم می‌شود و هواپیما به‌جای «کوبیدن» می‌نشیند.

   آخرین دور گردکردن *کف‌آگاه* است: اگر میانگین به زیر زمین برسد، همان کف
   گذاشته می‌شود. بدون این، "چسبیدن به کف" روی یک دامنه یک گوشهٔ تیز باقی
   می‌گذاشت که هیچ دور بعدی آن را نرم نمی‌کرد.

۳) **شیب فرود، گلاید دور آرام است.** فرود نیازی به نرخ موتور ندارد: ارتفاع خرج
   می‌شود و مسافت به دست می‌آید. پس سقف شیب فرود از نسبت برآر به پسار
   (``glide_ratio``) می‌آید — یعنی همان عددی که مدل تلاش موتوری با آن «سوختِ
   صرفه‌جویی‌شده» را حساب می‌کند — و اگر نرخ فرود هواپیما محدودتر بود، همان حاکم
   می‌شود:

       سقف شیب فرود = min(1 / (L/D) , نرخ فرود ÷ سرعت زمینی)

   با این انتخاب فرود **زودتر و ملایم‌تر** شروع می‌شود: گذر از ارتفاع ۲۶۰۰ متری با
   L/D = ۱۲ روی ۳۱ کیلومتر پخش می‌شود، در حالی که نرخ بیشینهٔ فرود (۳ m/s در
   سرعت زمینی ۲۸ m/s) فقط ۲۴ کیلومتر می‌داد. این همان رفتار پرنده است: بالا برو،
   با باد برو، و ارتفاع را در راه خرج کن — نه اینکه تا نوک مقصد تراز بمانی و بعد
   سقوط کنی.

۴) **کف زمین.** اگر مدل ارتفاع زمین داده شود، هیچ نمونه‌ای زیر ارتفاع زمین نمی‌رود.
   فاصلهٔ ایمنی بالای زمین هم طلب می‌شود، ولی *فقط تا جایی که هواپیما بتواند به
   آن ارتفاع برسد*: کف از مبدأ با سقف صعود و از مقصد با سقف فرود بالا می‌آید و
   در برخورد آن دو به ارتفاع زمین می‌رسد. پس کف هرگز تندتر از خود هواپیما بالا
   نمی‌رود و در دو سر مسیر دقیقاً روی زمین است. یک گلاید ملایم هم نمی‌تواند داخل
   رشته‌کوه برود؛ اگر کوه سر راه باشد، کف آن را بالا می‌آورد و شیب موضعی تندتر
   می‌شود — و این یک قید فیزیکی است، نه یک آرزو. اولویت همیشه با زمین است.

هزینه‌ها دست‌نخورده می‌مانند
--------------------------
این ماژول *فقط هندسه* را نرم می‌کند. زمان و سوخت گذر عمودی همان‌طور که در
``compute_vertical_cost`` و ``compute_route_effort`` حساب شده بود باقی می‌ماند:
رمپ روی همان مسافت افقیِ مسیر پخش می‌شود، مسافت جدیدی اضافه نمی‌کند، و ارتفاع کل
صعود/فرود هم عوض نمی‌شود. مدل هزینه برای فرود نرخ بیشینه را فرض می‌کند، پس اگر
پروفیل با گلاید ملایم‌تر پایین بیاید، آن تخمین *محافظه‌کارانه* است (زمان فرود را
کمتر از واقع تخمین می‌زند) و سوخت گلاید هم جداگانه به‌عنوان صرفه‌جویی حساب می‌شود.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

from preprocessing.consistency import haversine_km

__all__ = ["ramp_vertical_transitions"]

# گام نمونه‌برداری داخل مسیر (کیلومتر). هم رزولوشن رمپ‌ها را تعیین می‌کند و هم
# فاصلهٔ نقطه‌های گزارش‌شده.
INTEGRATION_STEP_KM = 0.5

# فاصلهٔ نقطه‌های گزارش‌شده (کیلومتر). پروفیل خروجی دیگر «تراز + رمپ» نیست بلکه
# یک منحنی پیوسته است، پس همهٔ نمونه‌ها گزارش می‌شوند: اگر نقطه‌ها تُنُک شوند،
# *خودِ هندسهٔ گزارش‌شده* پله‌ای می‌شود و صحنه ناچار می‌شود از روی همان نقطه‌های
# تُنُک منحنی بسازد — یعنی نرمی به رندرگر واگذار می‌شد، نه به الگوریتم.
REPORTED_STEP_KM = 0.5

# چند دور «کف → سقف شیب → گردکردن گوشه». هر دور گوشه‌ها را نرم‌تر می‌کند و
# دور بعد سقف شیب را دوباره برقرار می‌کند؛ همگرایی سریع است.
_PROFILE_PASSES = 4

# چند دور میانگین‌گیری برای گردکردن گوشه‌ها در هر پاس. پهنای نرمی هر گوشه با
# جذر تعداد دورها زیاد می‌شود (پخش گاوسی)، پس چند دور برای چند کیلومتر کافی است.
_CORNER_ROUNDING_ROUNDS = 8


def ramp_vertical_transitions(
    path: Sequence[tuple[float, float]],
    altitudes: Sequence[float],
    *,
    climb_rate_mps: float,
    descent_rate_mps: float,
    ground_speed_mps: float,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    glide_ratio: float | None = None,
    min_clearance_m: float = 0.0,
    integration_step_km: float = INTEGRATION_STEP_KM,
    reported_step_km: float = REPORTED_STEP_KM,
    passes: int = _PROFILE_PASSES,
    corner_rounding_rounds: int = _CORNER_ROUNDING_ROUNDS,
) -> tuple[list[tuple[float, float]], list[float]]:
    """پله‌های ارتفاعی یک مسیر را به یک پروفیل پیوسته و نرم بدل می‌کند.

    پارامترها
    ----------
    path : Sequence[tuple[float, float]]
        نقاط مسیر روی زمین (عرض، طول) به ترتیب حرکت.
    altitudes : Sequence[float]
        ارتفاع هر نقطه (متر). قرارداد: صفر = «روی زمین همان نقطه» (نه سطح دریا).
    climb_rate_mps, descent_rate_mps : float
        نرخ صعود/فرود هواپیما (متر بر ثانیه) — همان اعدادی که
        ``VerticalCostConfig`` به مدل هزینه می‌دهد. این‌ها **سقف** شیب‌اند.
    ground_speed_mps : float
        سرعت زمینی هواپیما (متر بر ثانیه). مسافت افقی هر گذر از همین می‌آید:
        صعودی که ۲۰۰۰ متر ارتفاع می‌گیرد با نرخ ۲.۵ m/s، ۸۰۰ ثانیه طول می‌کشد
        و در سرعت ۲۸ m/s روی ۲۲.۴ کیلومتر پخش می‌شود.
    ground_elevation_at : Callable[[float, float], float], اختیاری
        ارتفاع زمین. اگر داده شود، هندسه بر مبنای ارتفاع **بالای سطح دریا**
        ساخته می‌شود (گره زمین مبدأ/مقصد هم ارتفاع واقعی زمین همان نقطه می‌گیرد):
        هیچ بخشی زیر زمین نمی‌رود و کف ``ارتفاع زمین + min_clearance_m``
        برقرار می‌ماند. ارتفاع **گزارش‌شدهٔ** دو سر مسیر همان مقداری می‌ماند که
        ورودی داده (یعنی صفر برای گره زمین)، تا قرارداد ``RouteResult``
        نشکند.
    glide_ratio : float, اختیاری
        نسبت برآر به پسار. سقف شیب فرود را از ``1 / glide_ratio`` می‌گیرد (گلاید
        با موتور دور آرام). اگر ``None`` باشد، فقط نرخ فرود حاکم است.
    min_clearance_m : float
        کمترین فاصلهٔ مجاز از زمین در فاز پرواز (متر). در دو سر مسیر به صفر
        می‌رسد چون خودِ هواپیما آن‌جا روی زمین است: فاصلهٔ ایمنی فقط تا جایی
        طلب می‌شود که با سقف صعود/فرود از مبدأ و مقصد قابل دسترسی باشد.
    integration_step_km, reported_step_km : float
        گام انتگرال‌گیری و بیشینهٔ فاصلهٔ نقطه‌های گزارش‌شده (کیلومتر).
    passes, corner_rounding_rounds : int
        تعداد دورهای «کف/سقف شیب/گردکردن گوشه» و تعداد دورهای میانگین‌گیری در هر
        دور. هر دو باید مثبت باشند؛ مقادیر پیش‌فرض برای منحنی نرم کافی‌اند.

    برمی‌گرداند
    ----------
    (path, altitudes)
        همان مسیر با پروفیلی پیوسته. طول هر دو فهرست یکی است، نقطهٔ شروع و پایان
        دست‌نخورده می‌ماند (مسیر از زمین بلند می‌شود و روی زمین می‌نشیند)، و هر
        نمونهٔ گزارش‌شده حداکثر ``reported_step_km`` از نمونهٔ بعدی فاصله دارد.
    """
    if len(path) != len(altitudes):
        raise ValueError(
            f"path and altitudes must have the same length, got {len(path)} and "
            f"{len(altitudes)}."
        )
    points = [(float(lat), float(lon)) for lat, lon in path]
    levels = [float(alt) for alt in altitudes]
    if len(points) < 2:
        return points, levels
    if climb_rate_mps <= 0.0 or descent_rate_mps <= 0.0:
        raise ValueError("climb and descent rates must be positive.")
    if ground_speed_mps <= 0.0:
        raise ValueError("ground_speed_mps must be positive.")
    if integration_step_km <= 0.0 or reported_step_km <= 0.0:
        raise ValueError("integration and reporting steps must be positive.")
    if passes <= 0 or corner_rounding_rounds <= 0:
        raise ValueError("passes and corner_rounding_rounds must be positive.")
    if glide_ratio is not None and glide_ratio <= 0.0:
        raise ValueError("glide_ratio must be positive when given.")
    if min_clearance_m < 0.0:
        raise ValueError("min_clearance_m cannot be negative.")

    # ۱) مسافت تجمعی گره‌ها.
    cumulative = [0.0]
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:], strict=False):
        cumulative.append(cumulative[-1] + haversine_km(lat1, lon1, lat2, lon2))
    total_km = cumulative[-1]
    if total_km <= 0.0:
        return points, levels

    # ۲) شبکهٔ یکنواخت مسافت + هدف هر نمونه. گره زمین با ارتفاع واقعی زمین
    #    جایگزین می‌شود؛ «صفر» یعنی «روی زمین»، پس هدف باید همان ارتفاع باشد.
    # ``ceil`` نه ``int``: با تقسیم صحیح، گام واقعی شبکه کمی از گام درخواستی
    # بزرگ‌تر می‌شد (مثلاً ۰.۵۰۰۳۸ به‌ازای ۰.۵) و در گزارش، فاصلهٔ نمونه‌ها
    # از سقفی که وعده داده شده بود می‌گذشت.
    count = max(int(np.ceil(total_km / integration_step_km)), 2)
    grid = [total_km * index / count for index in range(count + 1)]

    def point_at(distance_km: float) -> tuple[float, float]:
        """نقطهٔ روی مسیر در یک مسافت مشخص (میان‌یابی خطی روی پاره‌ها)."""
        if distance_km <= 0.0:
            return points[0]
        if distance_km >= total_km:
            return points[-1]
        index = 0
        while index + 2 < len(cumulative) and cumulative[index + 1] < distance_km:
            index += 1
        span = cumulative[index + 1] - cumulative[index]
        fraction = 0.0 if span <= 0.0 else (distance_km - cumulative[index]) / span
        lat = points[index][0] + fraction * (points[index + 1][0] - points[index][0])
        lon = points[index][1] + fraction * (points[index + 1][1] - points[index][1])
        return lat, lon

    def node_at(distance_km: float) -> int:
        """شمارهٔ آخرین گره‌ای که در این مسافت یا پیش از آن است."""
        index = 0
        while index + 1 < len(cumulative) and cumulative[index + 1] <= distance_km + 1e-9:
            index += 1
        return index

    def resolve(level: float, distance_km: float) -> float:
        """ارتفاع هدف یک نقطه: مقدار گره، یا ارتفاع واقعی زمین اگر گره زمین است."""
        if level <= 0.0 and ground_elevation_at is not None:
            lat, lon = point_at(distance_km)
            return float(ground_elevation_at(lat, lon))
        return level

    targets = [
        resolve(levels[node_at(distance_km)], distance_km) for distance_km in grid
    ]
    # دو سر پروفیل، ارتفاع **اولین و آخرین گره** است، نه مقدار «پس از گذرِ» آن
    # نقطه: گراف اولین گذر را در همان مختصات مبدأ می‌گذارد، پس مقدار آخرین گرهٔ
    # هم‌مکان با گره زمین، ارتفاع سطح پرواز است — و اگر همان را برای نقطهٔ صفر
    # بگذاریم، مسیر از وسط آسمان شروع می‌شود و زمین را نمی‌بیند.
    targets[0] = resolve(levels[0], 0.0)
    targets[-1] = resolve(levels[-1], total_km)

    # ۳) سقف شیب هر فاز (متر ارتفاع بر متر مسافت افقی).
    climb_cap = climb_rate_mps / ground_speed_mps
    descent_cap = descent_rate_mps / ground_speed_mps
    if glide_ratio is not None:
        # فرود = گلاید با موتور دور آرام: ارتفاع خرج می‌شود و مسافت به دست
        # می‌آید. اگر این ملایم‌تر از نرخ فرود هواپیما باشد، همان حاکم می‌شود؛
        # پس فرود هم زودتر شروع می‌شود و هم شیب کمتری دارد.
        descent_cap = min(descent_cap, 1.0 / glide_ratio)

    # ۴) کف زمین: ارتفاع زمین + فاصلهٔ ایمنی — ولی *فقط* به‌اندازه‌ای که با
    #    سقف صعود/فرود از دو سر مسیر قابل دسترسی باشد. بدون این قید، کفِ
    #    فاصلهٔ ایمنی خودش یک رمپ خطی با شیب ثابت می‌سازد که هواپیما آن را
    #    نمی‌تواند پرواز کند و همان رمپ، پلهٔ ابتدای مسیر می‌شود.
    floor = _terrain_floor(
        grid,
        total_km,
        point_at,
        ground_elevation_at,
        min_clearance_m,
        climb_cap=climb_cap,
        descent_cap=descent_cap,
    )

    # ۵) کف → سقف صعود → سقف فرود → گردکردن گوشه‌ها. کف آخرین کار است تا اگر
    #    کوهی سر راه باشد، پروفیل هرگز زیر آن نماند (اولویت با زمین است، نه با
    #    شیب آرمانی).
    profile = list(targets)
    for _ in range(passes):
        _clamp_to_floor(profile, floor)
        _limit_climb(profile, grid, climb_cap)
        _limit_descent(profile, grid, descent_cap)
        _round_corners(profile, corner_rounding_rounds)
    # آخرین کف، و بعد یک گردکردنِ *کف‌آگاه*. ترتیب معنا دارد: اگر همین‌جا
    # تمام کنیم، "چسبیدن به کف" (مثلاً روی دامنهٔ کوه) یک گوشهٔ تیز باقی
    # می‌گذارد که هیچ دور گردکردنی آن را نرم نمی‌کند — همان چیزیکه یک رمپ
    # صاف را در چشم "پله‌ای" می‌کند. گردکردنِ کف‌آگاه همان گوشه را نرم می‌کند
    # ولی هرگز زیر زمین نمی‌رود.
    _clamp_to_floor(profile, floor)
    _round_corners_above_floor(profile, floor, corner_rounding_rounds)
    profile[0] = targets[0]
    profile[-1] = targets[-1]

    # ۶) گزارش: نقطه‌ها با فاصلهٔ حداکثر ``reported_step_km``. پروفیل دیگر
    #    «تراز و رمپ» ندارد، پس تُنُک‌کردن بخش‌های تراز معنا ندارد؛ تنها چیزی که
    #    مهم است این است که فاصلهٔ نقطه‌ها یکنواخت بماند تا خط رسم‌شده نرم بماند.
    #    گام گزارش با گام شبکه ساخته می‌شود، نه با مقایسهٔ فاصله‌ها: اگر شبکه
    #    کمی ریزتر از گام گزارش باشد، مقایسهٔ فاصلهٔ انباشته هیچ‌وقت به آستانه
    #    نمی‌رسد و ناگهان فقط دو سر مسیر گزارش می‌شود (یک = دو برابر فاصله).
    grid_step_km = total_km / count
    stride = max(1, int(reported_step_km / grid_step_km))
    keep = set(range(0, count + 1, stride))
    keep.add(count)
    for position in cumulative:
        keep.add(min(range(count + 1), key=lambda i: abs(grid[i] - position)))

    out_points: list[tuple[float, float]] = []
    out_altitudes: list[float] = []
    for index in sorted(keep):
        out_points.append(point_at(grid[index]))
        out_altitudes.append(profile[index])

    # قرارداد ارتفاع گزارش‌شده برگردانده می‌شود: گره زمین «صفر» است، نه ارتفاع
    # خود زمین. پروفیل *داخلی* بالای سطح دریا ساخته می‌شود (چون کف زمین MSL است
    # و باید با کوه‌ها مقایسه شود)، ولی اگر همان MSL در دو سر گزارش شود، قرارداد
    # عمومی ``RouteResult`` می‌شکند و هر مصرف‌کنندهٔ دیگری باید حدس بزند کدام
    # نمونه روی زمین است. دو سر مسیر همیشه در ``keep`` هستند، پس این تبدیل
    # دقیقاً روی همان دو نمونه اعمال می‌شود و بی‌اتلاف است.
    if levels[0] <= 0.0:
        out_altitudes[0] = levels[0]
    if levels[-1] <= 0.0:
        out_altitudes[-1] = levels[-1]
    return out_points, out_altitudes


def _terrain_floor(
    grid: Sequence[float],
    total_km: float,
    point_at: Callable[[float], tuple[float, float]],
    ground_elevation_at: Callable[[float, float], float] | None,
    min_clearance_m: float,
    *,
    climb_cap: float,
    descent_cap: float,
) -> list[float | None]:
    """کف مجاز ارتفاع در هر نمونه (یا ``None`` اگر مدل زمینی داده نشده باشد).

    کف دو جزء دارد و هر دو لازم‌اند:

    * **زمین سخت.** هیچ نمونه‌ای زیر ارتفاع زمین نیست. اولویت همیشه با زمین است،
      حتی اگر معنی‌اش شیبی تندتر از سقف باشد (کوه یک قید فیزیکی است، نه یک آرزو).
    * **فاصلهٔ ایمنی نرم.** فاصلهٔ ایمنی خواستهٔ *برنامه‌ریزی* است، پس فقط تا
      جایی طلب می‌شود که هواپیما بتواند در آن ارتفاع باشد. سقف دسترسی از مبدأ
      با ``climb_cap`` و از مقصد با ``descent_cap`` بالا می‌آید؛ در برخورد این
      دو مخروط، فاصلهٔ ایمنی به صفر می‌رسد. نتیجه این است که کف **هرگز سریع‌تر
      از خود هواپیما بالا نمی‌رود** — و در نقط نخست دقیقاً روی ارتفاع زمین
      است، چون هنوز هیچ ارتفاعی گرفته نشده.

    دلیل اینکه پنجرهٔ خطی برخاست/نشستن حذف شد: آن پنجره فاصلهٔ ایمنی را روی ۲
    کیلومتر اول با شیب ثابت ``clearance / 2 km`` توزیع می‌کرد، و این شیب از سقف
    صعود هواپیما مستقل بود؛ با فاصلهٔ ایمنی ۳۰۰ متر و پنجرهٔ ۲ کیلومتری شیبی
    معادل ۰.۱۵ می‌ساخت که از سقف واقعی (۰.۱۲۵) تندتر بود و همان‌جا یک «پله» و
    یک شکستگی در پروفیل جا می‌گذاشت. اکنون شکل برخاست از خود سقف صعود می‌آید.
    """
    if ground_elevation_at is None:
        return [None] * len(grid)
    ground = [
        float(ground_elevation_at(*point_at(distance_km))) for distance_km in grid
    ]
    start_elevation = ground[0]
    end_elevation = ground[-1]
    floor: list[float | None] = []
    for index, distance_km in enumerate(grid):
        reachable = min(
            start_elevation + climb_cap * distance_km * 1000.0,
            end_elevation + descent_cap * (total_km - distance_km) * 1000.0,
        )
        clearance = min(min_clearance_m, max(reachable - ground[index], 0.0))
        floor.append(ground[index] + clearance)

    # **کف باید *قابل پرواز* باشد — نه فقط *قابل دسترس*.** محاسبهٔ بالا فقط
    # همان نقطه را می‌سنجد: اگر رشته‌کوهی پیش رو کف را بلند کند، کف همان‌جا
    # می‌پرد و پروفیل مجبور می‌شود با شیبی تندتر از توان هواپیما از آن بالا
    # برود. اندازه‌گیری روی R3: برآمدگی ۶۲۰ متری در ۳ کیلومتر (شیب ۰.۲۱) در
    # برابر سقف صعود ۰.۰۹۶ (۲.۵ m/s در ۲۶ m/s) — پروفیل با ۲۳٪ بالا می‌رفت،
    # یعنی هندسهٔ *پروازناپذیر*. راه درست «زودتر بالا رفتن» است، نه «تندتر
    # بالا رفتن»؛ همان کاری که پرنده می‌کند.
    #
    # یک پاس از راست به چپ کف را منتشر می‌کند: هر نمونه حداکثر یک گامِ
    # ``climb_cap`` کم‌شیب‌تر از نمونهٔ *بعدی* می‌شود. نتیجه دقیقاً «مخروطی»
    # است که از کوه به عقب باز می‌شود؛ چون محاسبه از راست به چپ است، یک پاس
    # برای همهٔ برآمدگی‌ها کافی است. کف فقط بلند می‌شود (هرگز پایین نمی‌آید)،
    # پس قید سخت زمین دست‌نخورده است. یک پاس رو‌به‌جلو هم همین را برای فرود
    # برقرار می‌کند. اگر یک برآمدگی از مخروط مبدأ بالاتر باشد، انتشار به
    # زمینِ سخت می‌رسد و همان می‌ماند — آن‌جا واقعاً پروازناپذیر است و
    # اولویت با زمین است.
    for index in range(len(floor) - 2, -1, -1):
        allowed = climb_cap * (grid[index + 1] - grid[index]) * 1000.0
        floor[index] = max(floor[index], floor[index + 1] - allowed)
    for index in range(1, len(floor)):
        allowed = descent_cap * (grid[index] - grid[index - 1]) * 1000.0
        floor[index] = max(floor[index], floor[index - 1] - allowed)
    return floor


def _clamp_to_floor(profile: list[float], floor: Sequence[float | None]) -> None:
    """هیچ نمونه‌ای زیر کف مجاز نمی‌ماند (کف ``None`` = بدون قید)."""
    for index, elevation in enumerate(floor):
        if elevation is not None and profile[index] < elevation:
            profile[index] = elevation


def _limit_climb(profile: list[float], grid: Sequence[float], cap: float) -> None:
    """هر نمونه را حداکثر به اندازهٔ یک گام بالاتر از نمونهٔ قبلی نگه می‌دارد."""
    for index in range(1, len(profile)):
        allowed = cap * (grid[index] - grid[index - 1]) * 1000.0
        if profile[index] > profile[index - 1] + allowed:
            profile[index] = profile[index - 1] + allowed


def _limit_descent(profile: list[float], grid: Sequence[float], cap: float) -> None:
    """از راست: هر نمونه حداکثر یک گام بالاتر از نمونهٔ بعدی (فرود درجا تمام شود)."""
    for index in range(len(profile) - 2, -1, -1):
        allowed = cap * (grid[index + 1] - grid[index]) * 1000.0
        if profile[index] > profile[index + 1] + allowed:
            profile[index] = profile[index + 1] + allowed


def _round_corners(profile: list[float], rounds: int) -> None:
    """گوشه‌ها را با میانگین وزنی ۱-۲-۱ گرد می‌کند؛ دو سر ثابت می‌مانند.

    میانگین وزنی هیچ‌وقت از بیشینهٔ همسایگی بالاتر نمی‌رود، پس نه از سطح هدف
    می‌زند و نه شیبی تندتر از سقف می‌سازد — فقط «سه‌قطعی» تراز/رمپ/تراز را به یک
    منحنی S بدل می‌کند و نزدیک مقصد فلر می‌سازد.
    """
    for _ in range(rounds):
        previous = profile[0]
        for index in range(1, len(profile) - 1):
            current = profile[index]
            profile[index] = 0.25 * previous + 0.5 * current + 0.25 * profile[index + 1]
            previous = current


def _round_corners_above_floor(
    profile: list[float],
    floor: Sequence[float | None],
    rounds: int,
) -> None:
    """مانند ``_round_corners``، ولی هیچ نمونه‌ای را زیر کف نمی‌برد.

    تفاوت در یک چیز است: اگر میانگین به زیر کف برسد، همان کف گذاشته می‌شود.
    پس زمین همچنان قید سخت است، ولی گوشه‌های باقی‌مانده از "چسبیدن به کف"
    (شیبی که کوه تحمیل می‌کند) نرم می‌شوند و پروفیل دیگر پله نمی‌سازد.
    """
    for _ in range(rounds):
        previous = profile[0]
        for index in range(1, len(profile) - 1):
            current = profile[index]
            candidate = 0.25 * previous + 0.5 * current + 0.25 * profile[index + 1]
            limit = floor[index]
            if limit is not None and candidate < limit:
                candidate = limit
            profile[index] = candidate
            previous = current
