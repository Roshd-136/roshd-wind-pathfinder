"""صحنه سه‌بعدی تعاملی مسیریابی باد (Plotly).

خروجی این ماژول یک فایل HTML خودکفا است: بدون نیاز به توکن نقشه، بدون CDN و
بدون سرور کاشی، پس آفلاین هم باز می‌شود. صحنه شامل این‌هاست:

- **زمین واقعی (DEM):** شکل سطح از داده ارتفاع کپرنیکوس (فایل
  ``data/khorasan_terrain.csv``) می‌آید، پس دره‌ها و ارتفاعات شمال کریدور
  دیده می‌شوند. یک لایه رنگی ثانویه (خاموش به‌صورت پیش‌فرض) همین زمین را با
  «بهترین لایه ارتفاعی» هر سلول رنگ می‌کند.
- **پیکان‌های باد** برای هر لایه ارتفاعی، رسم‌شده **روی همان گره‌های گرافی که
  روتر با آن‌ها مسیریابی می‌کند**. پیکان‌ها **روشن** هستند و هر لایه یک ورودی
  راهنما دارد که می‌توان آن را خاموش کرد. با نگه‌داشتن نشانگر روی هر پیکان،
  سرعت، جهت، ارتفاع لایه، ارتفاع زمین محلی و مختصات همان گره دیده می‌شود.
- **مسیرها** به‌صورت منحنی هموارشده (spline) با رنگ‌های متفاوت: مسیرهای
  گرافی + مسیر بادسواری + گونه‌های هم‌خانوادهٔ آن (همان مسیر با دالان‌های
  صریح؛ به ``WIND_RIDING_VARIANT_SPECS`` نگاه کنید). سه مسیر
  اول آزادند **بین لایه‌های ارتفاعی جابجا شوند** (مسیریابی روی گراف سه‌بعدی
  ادغام‌شده با هزینه صعود/فرود)، مسیر چهارم عمداً مقید به یک لایه است تا
  هزینهٔ آن قید دیده شود، و مسیر پنجم (``wind-riding``) روی گراف حساب نمی‌شود:
  یک سمت هوایی ثابت می‌گیرد، باد مسیر را می‌برد و فرود در همان فاز و در حرکت
  انجام می‌شود — پس «تصحیح مسیر با موتور» صفر می‌شود. ارتفاع همه مسیرها
  **نسبت به زمین (AGL)** است و هر گره روی ارتفاع زمین محلی خودش کشیده
  می‌شود، پس مبدأ و مقصد روی زمین می‌مانند.
- **جدول مقایسه** بر اساس گره‌های واقعی مسیر (نه منحنی).

نکته صداقت: پیکان‌ها از نمایه لایه‌ای **سنتزی** ساخته می‌شوند (به
``viz.wind_field`` مراجعه کنید)، «شاخص انرژی» یک کمیت نسبی است نه ژول، و زمین
در مدل مسیریابی **مانع نیست** (بررسی برخورد یا حداقل فاصله ایمن وجود ندارد).
هر سه نکته در متن صحنه برچسب خورده‌اند.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from string import Template

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.interpolate import RegularGridInterpolator, make_interp_spline

from pathfinding.alignment import wind_alignment_profile
from pathfinding.cost import (
    CostModelConfig,
    InfeasibleEdgeError,
    compute_edge_cost,
    initial_bearing_deg,
)
from pathfinding.effort import MotorEffortConfig
from pathfinding.graph import MultiLayerWindGraph, VerticalCostConfig
from pathfinding.routing import RouteResult, WindRouter
from pathfinding.wind_riding import (
    WindRidingConfig,
    plan_wind_riding_route,
    wind_riding_route_result,
)
from preprocessing.consistency import haversine_km
from viz.terrain import TERRAIN_CSV_PATH, TerrainModel, load_terrain
from viz.wind_field import (
    CORRIDOR_BBOX,
    DEMO_DESTINATION,
    DEMO_ORIGIN,
    FLIGHT_LEVELS_MSL,
    MIN_TERRAIN_CLEARANCE_M,
    VIZ_AIRCRAFT,
    LayerField,
    build_level_fields,
    build_multi_layer_graph,
    corridor_lattice,
    load_station_winds,
    lonlat_to_km,
    select_scene_hour,
)

# نام الگوریتم مسیر بادسواری. مسیرهای گرافی مقدار ``astar``/``dijkstra``/
# ``smooth`` دارند؛ این یکی روی *گراف* حساب نمی‌شود (روی میدان باد پیوسته
# انتگرال گرفته می‌شود)، پس ``build_routes`` از آن رد می‌شود و
# ``build_wind_riding_route`` آن را می‌سازد.
WIND_RIDING_ALGORITHM = "wind-riding"

__all__ = [
    "GRAPH_SPECS",
    "ROUTE_SPECS",
    "ALL_WIND_RIDING_SPECS",
    "WIND_RIDING_VARIANT_SPECS",
    "VERTICAL_EXAGGERATION",
    "WIND_RIDING_ALGORITHM",
    "ARROW_KM_PER_MS",
    "RouteSpec",
    "build_scene_figure",
    "build_routes",
    "build_wind_riding_route",
    "WindRidingLayerReport",
    "wind_riding_layer_reports",
    "drawn_polyline_km",
    "route_table_rows",
    "write_scene",
]

# بزرگ‌نمایی عمودی. زمین این کریدور ۸۷۲ تا ۳۱۷۵ متر ارتفاع دارد و سطوح پرواز
# ۱۵۰۰ تا ۳۶۰۰ متر *بالای سطح دریا* هستند؛ در مقیاس ۱:۱ روی ۱۷۳ کیلومتر مسافت
# افقی هیچ‌کدام دیده نمی‌شود، پس ارتفاع در این ضریب ضرب و روی محور اعلام می‌شود.
#
# چرا ۸ و نه عددی بزرگ‌تر: با ضریب ۲۰ حتی یک فرود *واقعاً* ملایم هم به شکل
# شیرجه دیده می‌شد — یک شیب ۱ به ۴۰ که ۰.۵ کیلومتر ارتفاع را در ۲۰ کیلومتر خرج
# می‌کند، با ضریب ۲۰ می‌شد ۱۰ کیلومتر افت روی ۲۰ کیلومتر افقی؛ یعنی ۲۷ درجه.
# همان شیب با ضریب ۸ حدود ۱۱ درجه و با ۴ حدود ۶ درجه دیده می‌شود. از آن‌طرف،
# کم‌کردن این عدد بیشتر، رشته‌کوه را به یک برجستگی بی‌اهمیت تبدیل می‌کند
# (بلندترین قله ۳۱۷۵ متر است: با ضریب ۸ هنوز ۲۵ کیلومتر ارتفاع روی صفحه).
# این عدد یک انتخاب *نمایشی* است و روی محور z و در متن صحنه اعلام می‌شود.
VERTICAL_EXAGGERATION = 8.0

# مقیاس رنگی زمین: دشت سبز → دامنه خشک → ارتفاعات روشن.
TERRAIN_COLORSCALE = [
    [0.00, "#2f7d4f"],
    [0.22, "#7cb342"],
    [0.42, "#c9b25e"],
    [0.62, "#a9714b"],
    [0.82, "#9b8577"],
    [1.00, "#f2f0ec"],
]

# طول هر پیکان باد = سرعت × این ضریب (کیلومتر به ازای هر متر بر ثانیه)،
# با سقف ``ARROW_MAX_LENGTH_KM``. نسبت یک‌به‌یک و بدون تابع غیرخطی است تا
# «باد تندتر ← پیکان بلندتر» با یک نگاه دیده شود. در این میدان باد (سرعت
# گره‌ها ۵.۲ تا ۱۰.۲ متر بر ثانیه) طول پیکان‌ها به همین نسبت ۸.۳ تا ۱۶.۳
# کیلومتر می‌شود؛ سقف را عمداً بالاتر گذاشته‌ایم تا در داده فعلی *هیچ* پیکانی
# قطع نشود و تناسب کامل بماند (آزمون همین را بررسی می‌کند).
ARROW_KM_PER_MS = 1.6
ARROW_MAX_LENGTH_KM = 18.0

# قطر سرِ پیکان (کیلومتر، در فضای داده — نه پیکسل). با ``sizemode="absolute"``
# پلاتلی سر هر مخروط را نسبت به بزرگ‌ترین بردار میدان نرمال می‌کند، پس سر هم
# *متناسب با سرعت باد* بزرگ می‌شود و ``ARROW_HEAD_KM`` قطر سرِ تندترین پیکان
# است (جفت Plotly: ``n.coneSize = sizeref / normMax``).
ARROW_HEAD_KM = 3.5

# ارتفاع صفحه رنگی «بهترین لایه» بالای زمین، برای جلوگیری از تداخل (z-fighting)
# با خود سطح زمین (کیلومتر، قبل از ضرب در بزرگ‌نمایی).
BEST_LAYER_OVERLAY_OFFSET_KM = 0.02

# گام رسم پیکان‌ها روی شبکه گراف. ۱ = هر گره، ۲ = یکی‌درمیان.
# با گام ۲ تعداد پیکان‌ها از ۱۳۴۴ به ۳۳۶ کاهش می‌یابد که برای hover روان و
# خوانایی صحنه لازم است (تعداد کم‌شده در متن صحنه اعلام می‌شود).
ARROW_STRIDE = 3

# عرض خط مسیر در plotly. **۱ پیکسل عمدی است، نه یک سهل‌انگاری.**
# plotly.gl3d خط کلفت را با نوار و قطعهٔ میتر می‌کشد؛ وقتی طول تصویرشدهٔ هر پاره
# از عرض خط کمتر شود (حالت پیش‌فرض همین صحنه)، گوشه‌ها می‌شکنند و خط به زنجیر
# مهره‌مهره تبدیل می‌شود. با عرض ۱ خط *همیشه* پیوسته است (خط مویی)، و ضخامت ظاهری
# از لولهٔ مش (`ROUTE_TUBE_*`) می‌آید که هندسهٔ واقعی دارد و این ایراد را ندارد.
ROUTE_LINE_WIDTH = 1

# لولهٔ نمایشی دور هر مسیر: شعاع در فضای صحنه (کیلومتر، همراه با بزرگ‌نمایی
# عمودی)، تعداد ضلع مقطع، و گام نمونه‌برداری برای سبک‌ماندن مش.
#
# شعاع ۰.۴۵ روی صفحه حدود ۳ پیکسل در نمای باز و ۱۵ پیکسل در زوم متوسط است —
# یعنی مثل پیکان‌های باد با زوم بزرگ و کوچک می‌شود (خواستهٔ صریح کاربر)، نه یک
# ضخامت ثابت پیکسلی. (تجربهٔ زندهٔ همین صحنه: شعاع ۰.۵ در نمای باز و در زوم
# متوسط هر دو یک «رسن» پیوسته می‌دهد، در حالی که ۰.۲۸ در فاصله به نقطه‌های
# تک‌پیکسلی آب می‌رود.)
ROUTE_TUBE_RADIUS_KM = 0.45
ROUTE_TUBE_SIDES = 6
ROUTE_TUBE_STRIDE = 3

# مبدأ مختصات نمودار (گوشه جنوب‌غربی محدوده) تا محورها منفی نشوند.
PLOT_ORIGIN = (CORRIDOR_BBOX["lat_min"], CORRIDOR_BBOX["lon_min"])

# عرضی که مقیاس شرق–غرب روی آن حساب می‌شود: عرضِ **میانهٔ** کادر، نه عرض مبدأ.
# خروجی "تصویر تخت" با مبدأ گوشه با "فاصلهٔ جغرافیایی" موتور مقایسه می‌شود؛
# اگر ضریب cos روی گوشهٔ جنوب‌غربی گرفته شود، کل محور شرق–غرب چند دهم درصد
# کشیده می‌شود (با کادر ۳۶.۰۵–۳۶.۴۵ این خطا ۰.۴٪ بود، کافی برای ردِ آزمونی که
# همان تطابق را می‌سنجد).
PLOT_SCALE_LAT = 0.5 * (CORRIDOR_BBOX["lat_min"] + CORRIDOR_BBOX["lat_max"])

# مسیر پیش‌فرض فایل ارتفاع زمین (DEM) نسبت به ریشه پروژه.
TERRAIN_PATH = TERRAIN_CSV_PATH

# رنگ لایه‌های ارتفاعی، از لایه پایین به بالا.
#
# این جدول از ``FLIGHT_LEVELS_MSL`` ساخته می‌شود، نه دستی. نسخه قبلی کلیدهای
# ارتفاعی *قدیمی* (۵۰۰/۱۰۰۰/۱۵۰۰/۲۰۰۰ متر بالای زمین) را داشت در حالی که سطوح
# پرواز به ۱۵۰۰/۲۲۰۰/۲۹۰۰/۳۶۰۰ متر *بالای سطح دریا* منتقل شده بودند؛ نتیجه این
# بود که سه لایه از چهار لایه به رنگ خاکستری پیش‌فرض می‌افتادند (پیکان‌های باد
# سه سطح یک‌شکل و نامرئی) و مقیاس رنگی «بهترین لایه» سه رنگ یکسان داشت. با
# ساختن جدول از خود ثابت، این ناهم‌خوانی دیگر ممکن نیست.
_LAYER_PALETTE = ("#74b9ff", "#00cec9", "#fdcb6e", "#e84393")
_LAYER_COLORS = {
    float(altitude): _LAYER_PALETTE[index % len(_LAYER_PALETTE)]
    for index, altitude in enumerate(FLIGHT_LEVELS_MSL)
}

_COMPASS = (
    "شمال",
    "شمال‌شرق",
    "شرق",
    "جنوب‌شرق",
    "جنوب",
    "جنوب‌غرب",
    "غرب",
    "شمال‌غرب",
)


@dataclass(frozen=True)
class RouteSpec:
    """تعریف یک مسیر نمایشی در صحنه.

    پارامترها
    ----------
    key : str
        شناسه کوتاه (R1..R4).
    label : str
        برچسب کامل فارسی برای جدول و hover.
    short : str
        برچسب کوتاه برای راهنمای HTML. برچسبهای کامل (مثل «کم‌مصرف
        و کم‌پیچ‌وخم (هم‌راستا با باد)») در راهنمای Plotly چند صد پیکسل عرض
        می‌گرفتند و روی خود صحنه می‌افتادند.
    criterion : str
        معیار بهینگی مدل هزینه.
    algorithm : str
        الگوریتم مسیریابی (``astar`` / ``dijkstra`` / ``smooth``).
    color : str
        رنگ خط در صحنه.
    direction_penalty : float
        جریمه تغییر جهت برای الگوریتم ``smooth`` (در واحد تابع هدف).
    restrict_to_single_layer : bool
        اگر ``True`` باشد، مسیر فقط روی یک لایه ارتفاعی حساب می‌شود (حالت
        «پرواز تنها در یک لایه»).    allow_layer_changes : bool
        اگر ``True`` (پیش‌فرض) باشد، مسیر روی گراف سه‌بعدی ادغام‌شده حساب
        می‌شود و می‌تواند در میانه راه از لایه‌ای به لایه دیگر صعود/فرود کند تا
        تابع هدف کوچک‌تر شود. اگر ``False`` باشد، کل مسیر در یک لایه می‌ماند.
    locked_layer : float | None
        لایه مقید. اگر ``restrict_to_single_layer`` روشن باشد و این مقدار ``None``
        بماند، **بالاترین** لایه قابل پرواز انتخاب می‌شود تا هزینهٔ قید تک‌لایه
        در مقایسه با مسیر آزاد دیده شود.
    wind_corridor_fraction : float | None
        برای مسیرهای بادسواری: دالان صریح این گونه. اگر ``None`` باشد، برنامه‌ریز
        خودش بهترین دالان را جست‌وجو می‌کند (مسیر اصلی بادسواری).

    نکته: مسیر مقید به یک لایه هم روی گراف سه‌بعدی (محدود به همان لایه) حساب
    می‌شود تا از روی زمین بلند شود و بنشیند و هزینه صعود/فرود را بپردازد؛ پس
    ``allow_layer_changes`` برای آن هم ``True`` می‌ماند و قید با
    ``restrict_to_single_layer`` اعمال می‌شود.
    """

    key: str
    label: str
    criterion: str
    algorithm: str
    color: str
    short: str = ""
    direction_penalty: float = 0.05
    restrict_to_single_layer: bool = False
    allow_layer_changes: bool = True
    locked_layer: float | None = None
    wind_corridor_fraction: float | None = None


# شش مسیر:
#   R1 کم‌مصرف‌ترین و کم‌پیچ‌وخم‌ترین — انرژی + جریمه تغییر جهت، آزاد بین سطوح
#   R2 سریع‌ترین — معیار زمان، آزاد بین سطوح
#   R3 کوتاه‌ترین مسافت — معیار مسافت
#   R4 مقید به پایین‌ترین سطح قابل‌پرواز → دور زدن رشته‌کوه
#   R6 مقید به بالاترین سطح → عبور از روی رشته‌کوه
#   R5 بادسواری — یک سمت هوایی ثابت روی میدان باد *پیوسته* (نه روی گراف):
#      صعود کن، بگذار باد ببرد، با شیب فرود بنشین. «تصحیح مسیر با موتور» صفر.
# R1..R3 آزادند بین سطوح جابجا شوند؛ همین آزادی همان چیزی است که «مسیر
# بهینه سه‌بعدی» را از «بهترین سطح ثابت» جدا می‌کند.
ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        key="R1",
        label="R1 — کم‌مصرف، آزاد بین سطوح پرواز",
        short="کم‌مصرف",
        criterion="energy",
        algorithm="smooth",
        color="#00b894",
        direction_penalty=0.05,
    ),
    RouteSpec(
        key="R2",
        label="R2 — سریع‌ترین (کمترین زمان)",
        short="سریع‌ترین",
        criterion="time",
        algorithm="astar",
        color="#d63031",
    ),
    RouteSpec(
        key="R3",
        label="R3 — کوتاه‌ترین مسافت",
        short="کوتاه‌ترین",
        criterion="distance",
        algorithm="astar",
        color="#0984e3",
    ),
    # R4 و R6 یک *آزمون کنترل‌شده* روی معنای «سطح پرواز» هستند: یک هدف، دو قید.
    # کریدور مشهد–سبزوار یک رشته‌کوه تا ۳۱۷۵ متر دارد؛ دو راه کاملاً متفاوت:
    #   * R4 در پایین‌ترین سطح قابل‌پرواز بماند → باید از گردنهٔ کم‌ارتفاع جنوبی
    #     دور بزند (مسیر بلندتر، صعود کمتر)،
    #   * R6 در بالاترین سطح بماند → از روی خود قله رد شود (مسیر کوتاه‌تر،
    #     صعود ۲.۶ کیلومتری).
    # پیش‌تر همهٔ مسیرها روی خط‌الرضای کوه می‌خوابیدند چون ارتفاع نسبت به زمین
    # بود و زمین در هزینه‌ای حساب نمی‌شد؛ حالا این دو مسیر دو *استراتژی*‌اند، نه
    # دو تنظیم قید.
    RouteSpec(
        key="R4",
        label="R4 — کم‌مصرف، مقید به پایین‌ترین سطح قابل‌پرواز (گردنه)",
        short="مقید به سطح پایین",
        criterion="energy",
        algorithm="smooth",
        color="#e17055",
        direction_penalty=0.05,
        restrict_to_single_layer=True,
        allow_layer_changes=True,
        locked_layer=2200.0,
    ),
    RouteSpec(
        key="R6",
        label="R6 — کم‌مصرف، مقید به بالاترین سطح (از روی قله)",
        short="مقید به سطح بالا",
        criterion="energy",
        algorithm="smooth",
        color="#6c5ce7",
        direction_penalty=0.05,
        restrict_to_single_layer=True,
        allow_layer_changes=True,
        locked_layer=3600.0,
    ),
    # R5 روی گراف مسیریابی *نمی‌شود*: یک سمت هوایی ثابت می‌گیرد و میدان باد
    # پیوسته را انتگرال می‌گیرد تا مقصد را با «صفر تصحیح مسیر» بگیرد. هیچ گرهی
    # از شبکه لازم نیست، ولی اگر باد نتواند هواپیما را ببرد، مسیری وجود ندارد.
    RouteSpec(
        key="R5",
        label="R5 — بادسواری: مسیر موازی باد، تصحیح فقط بیرون از دالان",
        short="بادسواری",
        criterion="time",
        algorithm=WIND_RIDING_ALGORITHM,
        color="#a29bfe",
    ),
)

# مسیرهایی که واقعاً روی گراف سه‌بعدی مسیریابی می‌شوند. R5 از این جدا است
# چون اصلاً گراف را نمی‌بیند؛ جدا نگه‌داشتنش لازم است تا جمله‌های صحنه
# («مسیرهای آزاد چرا ارتفاع عوض نمی‌کنند؟») به مسیرهای گرافی اشاره کنند.
GRAPH_SPECS: tuple[RouteSpec, ...] = tuple(
    spec for spec in ROUTE_SPECS if spec.algorithm != WIND_RIDING_ALGORITHM
)
WIND_RIDING_SPECS: tuple[RouteSpec, ...] = tuple(
    spec for spec in ROUTE_SPECS if spec.algorithm == WIND_RIDING_ALGORITHM
)

# **گونه‌های هم‌خانواده بادسواری.** مسیر بادسواری یک مسیر نیست، یک *خانواده*
# است: «دالان» تعیین می‌کند هواپیما تا کجا اجازه دارد از خط مبدأ–مقصد دور شود
# تا موازی باد بماند، و هر دالان یک مسیر متفاوت می‌دهد (اندازه‌گیری روی همین
# کریدور: دالان ۰.۲۰ → ۹٪ موازی و ۲.۱۲ ساعت، ۰.۵۰ → ۴۶٪ و ۲.۲۰، ۰.۹۵ → ۶۲٪
# و ۲.۳۱). R5 خودش دالان را با هدف «بیشترین موازی» انتخاب می‌کند؛ این دو گونه
# دو نقطهٔ دیگر همان مبادله‌اند تا تفاوت استراتژی در صحنه *دیده* شود، نه فقط
# خوانده. گونه‌ای که با دالانِ انتخاب‌شدهٔ R5 یکی شود رسم نمی‌شود (خط روی خط).
WIND_RIDING_VARIANT_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        key="R7",
        label="R7 — بادسواری با دالان تنگ (کمترین انحراف از خط مستقیم)",
        short="بادسواری — دالان تنگ",
        criterion="time",
        algorithm=WIND_RIDING_ALGORITHM,
        color="#00b0ff",
        wind_corridor_fraction=0.20,
    ),
    RouteSpec(
        key="R8",
        label="R8 — بادسواری با دالان میانه",
        short="بادسواری — دالان میانه",
        criterion="time",
        algorithm=WIND_RIDING_ALGORITHM,
        color="#ff8a5c",
        wind_corridor_fraction=0.50,
    ),
)
# همان مسیر خودکار R5 + گونه‌ها: فهرست کاملی که «همهٔ بادسواری‌ها» را می‌سازد.
ALL_WIND_RIDING_SPECS: tuple[RouteSpec, ...] = WIND_RIDING_SPECS + WIND_RIDING_VARIANT_SPECS


def _arrow_indices(node_count: int, n_lon: int, stride: int) -> np.ndarray:
    """اندیس گره‌هایی که باید به‌عنوان پیکان باد رسم شوند.

    گره‌ها به ترتیب ردیفی (عرض بیرونی، طول درونی) اضافه شده‌اند، پس با دانستن
    تعداد ستون‌ها می‌توان یک شبکه منظم را یکی‌درمیان نمونه‌برداری کرد (نه یک
    گام خطی تخت که الگوی ناهموار می‌سازد). اگر ساختار گراف با شبکه نخواند،
    به گام خطی برمی‌گردیم.
    """
    if stride <= 1:
        return np.arange(node_count)
    if n_lon <= 0 or node_count % n_lon != 0:
        return np.arange(0, node_count, stride)

    n_rows = node_count // n_lon
    mask = np.zeros((n_rows, n_lon), dtype=bool)
    mask[np.ix_(np.arange(0, n_rows, stride), np.arange(0, n_lon, stride))] = True
    return np.flatnonzero(mask.ravel())


def _nice_km_step(extent_km: float, target_ticks: int = 7) -> float:
    """گام تیک «گرد» (۱، ۲، ۵ × ۱۰ⁿ) نزدیک به ``extent_km / target_ticks``."""
    if not np.isfinite(extent_km) or extent_km <= 0.0:
        return 1.0
    rough = extent_km / max(target_ticks, 1)
    magnitude = 10.0 ** np.floor(np.log10(rough))
    for factor in (1.0, 2.0, 2.5, 5.0, 10.0):
        if rough <= factor * magnitude:
            return float(factor * magnitude)
    return float(10.0 * magnitude)


def _compass_point(direction_deg: float) -> str:
    """نزدیک‌ترین جهت هشت‌گانه فارسی به یک زاویه."""
    index = int((direction_deg % 360.0) / 45.0 + 0.5) % 8
    return _COMPASS[index]


def build_routes(
    multi_graph: MultiLayerWindGraph,
    config: CostModelConfig,
    origin: tuple[float, float] = DEMO_ORIGIN,
    destination: tuple[float, float] = DEMO_DESTINATION,
    specs: tuple[RouteSpec, ...] = ROUTE_SPECS,
    effort_config: MotorEffortConfig | None = None,
    vertical_config: VerticalCostConfig | None = None,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    min_clearance_m: float = 0.0,
) -> dict[str, RouteResult]:
    """مسیرهای گرافی نمایشی را با استفاده از ``WindRouter`` واقعی محاسبه می‌کند.

    هر مسیر یک ``WindRouter`` جدا با معیار/الگوریتم خودش دارد؛ چون وزن یال‌ها در
    زمان ساخت گراف پخته می‌شود، روتر گراف را برای هر معیار بازمحاسبه می‌کند.
    مسیرهای آزاد (``allow_layer_changes=True``) روی گراف سه‌بعدی ادغام‌شده
    مسیریابی می‌شوند و می‌توانند ارتفاع را در میانه راه تغییر دهند.
    """
    routes: dict[str, RouteResult] = {}
    for spec in specs:
        # مسیرهای بادسواری روی این گراف حساب نمی‌شوند؛ سازندهٔ جداگانه‌ای
        # (``build_wind_riding_route``) دارند که میدان باد پیوسته را می‌بیند.
        if spec.algorithm == WIND_RIDING_ALGORITHM:
            continue
        router = WindRouter(
            multi_graph,
            config=config,
            criterion=spec.criterion,
            algorithm=spec.algorithm,
            direction_penalty=spec.direction_penalty,
            allow_layer_changes=spec.allow_layer_changes,
            effort_config=effort_config,
            vertical_cost=vertical_config,
            ground_elevation_at=ground_elevation_at,
            min_clearance_m=min_clearance_m,
        )
        if not spec.restrict_to_single_layer:
            result = router.find_optimal_path(origin, destination)
            routes[spec.key] = result
            continue

        # مسیر مقید به یک لایه: لایه صریح، یا **بالاترین لایهٔ قابل پرواز**.
        # (بالاترین لایه لزوماً پروازپذیر نیست؛ ممکن است باد جانبی‌اش از سرعت
        # هوایی بیشتر باشد.)
        #
        # چرا بالاترین و نه «بهترین» لایه؟ چون در این میدان باد بهترین لایهٔ
        # تک‌لایه دقیقاً همان ۵۰۰ متری می‌شود که مسیر آزاد هم انتخاب می‌کند،
        # پس R4 نقطه‌به‌نقطه با R1 یکی می‌شد و هیچ چیزی نشان نمی‌داد. قید
        # عمدی روی بالاترین لایه، بدترین حالت یک قید را دیدنی می‌کند؛ و همین
        # که مسیر آزاد به هیچ‌وجه به آن ارتفاع نمی‌رود، خودش نشان می‌دهد
        # بهینه‌سازی ارتفاع در این میدان سودی ندارد (جدول شواهد همین را ثابت
        # می‌کند).
        layer = spec.locked_layer
        if layer is None or layer not in router.available_layers:
            # "پایین‌ترین سطحی که مسیر روی آن وجود دارد": با مدل زمین، این
            # لزوماً پایین‌ترین سطح موجود نیست — سطحی که روی همهٔ عرض‌های کریدور
            # در قله فرو رفته باشد مسیری ندارد.
            layer = None
            for candidate in router.available_layers:
                try:
                    routes[spec.key] = router.find_optimal_path(
                        origin, destination, layers=(candidate,)
                    )
                    layer = candidate
                    break
                except ValueError:
                    continue
            if layer is None:
                # هیچ سطح قیدی مسیر ندارد؛ مسیر در نمودار نمی‌آید و دلیلش در
                # یادداشت صحنه گفته می‌شود. عدد جعلی گزارش نمی‌کنیم.
                continue
            continue
        # عمداً روی گراف سه‌بعدی محدود به همان یک سطح مسیریابی می‌شود، نه روی
        # خود سطح تنها: این‌گونه مسیر از روی زمین بالا می‌رود و در پایان
        # می‌نشیند و هزینه صعود/فرود را هم می‌پردازد. در غیر این صورت مسیر مقید
        # با نداشتن صعود، «ارزان‌تر» از مسیر آزاد به‌نظر می‌رسید که نادرست بود.
        try:
            routes[spec.key] = router.find_optimal_path(
                origin, destination, layers=(layer,)
            )
        except ValueError:
            # این سطح در این کریدور قابل پرواز نیست (قله سر راه). مسیر حذف
            # می‌شود تا جدول عددی را نشان ندهد که به آن نمی‌رسد.
            continue
    return routes


def build_wind_riding_route(
    fields: list[LayerField],
    config: CostModelConfig,
    origin: tuple[float, float] = DEMO_ORIGIN,
    destination: tuple[float, float] = DEMO_DESTINATION,
    *,
    effort_config: MotorEffortConfig | None = None,
    vertical_config: VerticalCostConfig | None = None,
    criterion: str = "time",
    planner_config: WindRidingConfig | None = None,
    ground_elevation_at: Callable[[float, float], float] | None = None,
) -> RouteResult | None:
    """مسیر «بادسواری» را روی میدان باد پیوسته می‌سازد (نه روی گراف).

    ایده: به یک لایه صعود کن، یک سمت هوایی ثابت نگه دار، بگذار باد مسیر روی
    زمین را ببرد، و در پایان ارتفاع را تدریجا کم کن تا مقصد پیش بیاید. مقدار
    برگشتی همان ``RouteResult`` است تا در همان جدول/همان راهنما با مسیرهای
    گرافی قابل مقایسه باشد؛ تفاوت‌های مدل‌سازی (که در ``wind_riding`` مستند
    شده‌اند) عوض نمی‌شوند.

    پارامتر ``fields`` میدان باد همهٔ لایه‌ها است؛ از هر میدان یک نمونه‌بردار
    دوبعدی ساخته می‌شود و به برنامه‌ریز تزریق می‌شود تا لایهٔ ``pathfinding``
    به لایهٔ نمایش وابسته نشود.

    برمی‌گرداند
    ----------
    RouteResult | None
        ``None`` اگر هیچ لایه/سمتی به مقصد (در حد خطای مجاز) نرسد — در آن حالت
        مسیر در صحنه و جدول نمایش داده نمی‌شود و در یادداشت صحنه هم گفته می‌شود.
    """
    plan = plan_wind_riding_route(
        origin,
        destination,
        _layer_samplers(fields),
        aircraft=config,
        # همان فرض‌های مدل سوخت به برنامه‌ریز هم داده می‌شود: نسبت گلاید (که
        # نقطهٔ شروع فرود را تعیین می‌کند) و کسر توان دور آرام. اگر این‌جا رد
        # نشود، برنامه‌ریز با پیش‌فرض دیگری فرود را شروع می‌کند و اعداد سوخت با
        # هندسهٔ مسیر ناسازگار می‌شوند.
        effort=effort_config,
        config=planner_config,
    )
    if plan is None:
        return None
    return wind_riding_route_result(
        plan,
        aircraft=config,
        effort=effort_config,
        vertical=vertical_config,
        criterion=criterion,
        ground_elevation_at=ground_elevation_at,
    )


def _layer_samplers(
    fields: list[LayerField],
) -> list[tuple[float, Callable[[float, float], tuple[float, float]]]]:
    """هر میدان باد را به یک نمونه‌بردار ``(lat, lon) -> (speed, direction)`` بدل می‌کند."""
    layers: list[tuple[float, Callable[[float, float], tuple[float, float]]]] = []
    for field in fields:
        speed_at, direction_at = _interpolators(field)

        def sampler(
            lat: float,
            lon: float,
            speed_at: RegularGridInterpolator = speed_at,
            direction_at: RegularGridInterpolator = direction_at,
        ) -> tuple[float, float]:
            """باد یک نقطه: ``(سرعت m/s، جهت درجه از شمال)`` در همان لایه."""
            point = np.array([[lat, lon]], dtype=float)
            return (
                float(speed_at(point)[0]),
                float(direction_at(point)[0]) % 360.0,
            )

        layers.append((field.altitude, sampler))
    return layers


@dataclass(frozen=True)
class WindRidingLayerReport:
    """کارنامهٔ بادسواری در **یک** لایه — تا «چرا این لایه؟» قابل حسابرسی شود.

    پارامترها
    ----------
    altitude_m : float
        ارتفاع AGL لایه.
    wind_speed_mps, wind_offset_deg : float
        سرعت باد و **زاویهٔ آن با کریدور** در میانهٔ مسیر. ``wind_offset_deg``
        همان قطعهٔ گمشدهٔ بحث «چرا بالا نرود؟» است: اگر بادِ لایه‌های بالا به
        کریدور نزدیک‌تر شود، صعود بُرد دارد؛ اگر دورتر شود، ندارد — و این عدد
        همان را با یک نگاه نشان می‌دهد.
    climb_time_hours, ride_time_hours, glide_time_hours : float
        تفکیک زمان پرواز. فاز سوم **گلاید** است: موتور دور آرام و ارتفاع از
        گرانش خرج می‌شود.
    glide_km : float
        مسافت روی زمین در فاز فرود — روی شیبی که ``descent_slope_ratio``
        می‌گوید، نه گلاید بیشینه.
    glide_range_km : float
        بُرد گلاید بیشینهٔ همین ارتفاع (`h · L/D`). این عدد *کوتاه‌ترین* فرود
        ممکن است؛ فرود واقعی شیب ملایم‌تری دارد و همان جا مسافتش می‌آید.
    descent_slope_ratio, descent_power_fraction : float
        شیب واقعی فرود («۱ به N») و کسر توان موتور در آن فاز.
    total_time_hours, fuel_kg : float
        زمان کل و سوخت کل (کیلوگرم، مدل نه اندازه‌گیری).
    turns : int
        تعداد خمش‌های بیش از آستانه در سمت *مسیر روی زمین*.
    result : RouteResult
        همان مسیر، برای جدول/راهنما.
    """

    altitude_m: float
    wind_speed_mps: float
    wind_offset_deg: float
    climb_time_hours: float
    ride_time_hours: float
    glide_time_hours: float
    glide_km: float
    glide_range_km: float
    descent_slope_ratio: float
    descent_power_fraction: float
    total_time_hours: float
    fuel_kg: float
    turns: int
    result: RouteResult
    min_clearance_m: float | None = None
    # دالانی که این کارنامه با آن ساخته شده (``WindRidingPlan.corridor_fraction``).
    # لازم است تا «گونهٔ هم‌خانواده»ای که با دالان *یکسان* ساخته می‌شود رسم نشود
    # (وگرنه دو مسیر نقطه‌به‌نقطه یکی روی هم می‌افتند).
    corridor_fraction: float = 0.5


def wind_riding_layer_reports(
    fields: list[LayerField],
    config: CostModelConfig,
    origin: tuple[float, float] = DEMO_ORIGIN,
    destination: tuple[float, float] = DEMO_DESTINATION,
    *,
    effort_config: MotorEffortConfig | None = None,
    criterion: str = "time",
    planner_config: WindRidingConfig | None = None,
    vertical_config: VerticalCostConfig | None = None,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    min_clearance_m: float = 0.0,
) -> list[WindRidingLayerReport]:
    """بادسواری را **روی تک‌تک لایه‌ها** حساب می‌کند و کارنامهٔ هر کدام را می‌دهد.

    این تابع همان کاری را می‌کند که کاربر برای پرسیدن «چرا صعود نمی‌کند؟» لازم
    دارد: برنامه‌ریز بادسواری لایه را بر اساس *زمان کل* انتخاب می‌کند، ولی
    این‌جا برای هر لایه جداگانه — صعود، سواری، گلاید و سوختش — گزارش می‌شود تا
    اگر لایهٔ کم‌مصرف‌تر جای دیگری بود، دیده شود. خروجی به ترتیب صعودی ارتفاع
    است و لایه‌هایی که هیچ سمت ثابتی به مقصد نمی‌رسد حذف می‌شوند.
    """
    effort_settings = effort_config or MotorEffortConfig()
    samplers = _layer_samplers(fields)
    reports: list[WindRidingLayerReport] = []
    for altitude_m, sampler in samplers:
        # **تمام پروفیل داده می‌شود، فقط کروز قید می‌شود.** باد در هر لحظه از
        # لایه‌ای خوانده می‌شود که هواپیما واقعاً در آن ارتفاع است؛ اگر رشته‌کوه
        # سر راه باشد و صعود لازم شود، هواپیما از این‌جا به بعد بادِ همان ارتفاع
        # را می‌بیند. قید ``cruise_altitudes`` فقط یعنی «ارتفاع کروز این کارنامه
        # همین یک سطح است»، تا بتوان لایه‌ها را با هم مقایسه کرد.
        plan = plan_wind_riding_route(
            origin,
            destination,
            samplers,
            aircraft=config,
            effort=effort_settings,
            config=planner_config,
            ground_elevation_at=ground_elevation_at,
            min_clearance_m=min_clearance_m,
            cruise_altitudes=[altitude_m],
        )
        if plan is None:
            continue
        result = wind_riding_route_result(
            plan,
            aircraft=config,
            effort=effort_settings,
            vertical=vertical_config,
            criterion=criterion,
            ground_elevation_at=ground_elevation_at,
        )
        effort = result.effort
        mid = ((origin[0] + destination[0]) / 2.0, (origin[1] + destination[1]) / 2.0)
        speed, direction = sampler(*mid)
        corridor = initial_bearing_deg(origin[0], origin[1], destination[0], destination[1])
        # جهت «به‌سوی» باد، منهای سمت کریدور: ۰ = باد کاملاً هم‌راستای کریدور.
        wind_toward = (direction + 180.0) % 360.0
        offset = abs((wind_toward - corridor + 180.0) % 360.0 - 180.0)
        reports.append(
            WindRidingLayerReport(
                altitude_m=altitude_m,
                wind_speed_mps=speed,
                wind_offset_deg=offset,
                climb_time_hours=plan.climb_time_hours,
                ride_time_hours=plan.ride_time_hours,
                glide_time_hours=plan.descent_time_hours,
                glide_km=plan.descent_distance_km,
                descent_slope_ratio=plan.descent_slope_ratio,
                descent_power_fraction=plan.descent_power_fraction,
                # بُرد گلاید از سطح پرواز تا **ارتفاع زمین مقصد**، نه تا سطح دریا.
                glide_range_km=effort_settings.glide_range_km(plan.climb_m),
                min_clearance_m=plan.min_terrain_clearance_m,
                total_time_hours=result.estimated_time_hours,
                fuel_kg=effort.total_fuel_kg if effort is not None else 0.0,
                turns=result.heading_changes,
                corridor_fraction=plan.corridor_fraction,
                result=result,
            )
        )
    return reports


def build_wind_riding_routes(
    fields: list[LayerField],
    config: CostModelConfig,
    origin: tuple[float, float] = DEMO_ORIGIN,
    destination: tuple[float, float] = DEMO_DESTINATION,
    *,
    effort_config: MotorEffortConfig | None = None,
    vertical_config: VerticalCostConfig | None = None,
    criterion: str = "time",
    planner_config: WindRidingConfig | None = None,
    ground_elevation_at: Callable[[float, float], float] | None = None,
    min_clearance_m: float = 0.0,
    variant_specs: tuple[RouteSpec, ...] = WIND_RIDING_VARIANT_SPECS,
) -> tuple[dict[str, RouteResult], list[RouteSpec], list[WindRidingLayerReport]]:
    """مسیر بادسواری **و گونه‌های هم‌خانواده‌اش** را می‌سازد.

    چرا چند مسیر و نه یکی؟ بادسواری یک مسیر یکتا ندارد: «دالان» تعیین می‌کند
    هواپیما تا کجا اجازه دارد از خط مبدأ–مقصد دور شود تا موازی باد بماند و این
    یک *مبادله* است. مسیر اصلی (R5) دالانش را با هدف «بیشترین مسافت موازی»
    انتخاب می‌کند؛ گونه‌ها روی *همان* سطح پرواز و با دالان‌های صریح ساخته
    می‌شوند، پس تفاوتشان فقط استراتژی است، نه ارتفاع — و همین باعث می‌شود کنار
    هم گذاشتنشان معنادار باشد (نه مقایسهٔ سیب و پرتقال).

    گونه‌ای که دالانش با دالان انتخاب‌شدهٔ مسیر اصلی یکی شود ساخته نمی‌شود:
    خروجی‌اش نقطه‌به‌نقطه همان مسیر است و رسم دوباره فقط یک خط روی خط است.

    برمی‌گرداند
    ----------
    (routes, specs, reports)
        ``routes`` نگاشت کلید → نتیجه، ``specs`` فهرست گونه‌هایی که واقعاً ساخته
        شدند (شامل خود مسیر اصلی)، و ``reports`` کارنامهٔ تک‌تک سطوح پرواز که
        جدول «چرا این سطح؟» را می‌سازد.
    """
    reports = wind_riding_layer_reports(
        fields,
        config,
        origin=origin,
        destination=destination,
        effort_config=effort_config,
        criterion=criterion,
        planner_config=planner_config,
        vertical_config=vertical_config,
        ground_elevation_at=ground_elevation_at,
        min_clearance_m=min_clearance_m,
    )

    routes: dict[str, RouteResult] = {}
    built: list[RouteSpec] = []
    base_spec = WIND_RIDING_SPECS[0] if WIND_RIDING_SPECS else None
    best = min(reports, key=lambda item: item.total_time_hours) if reports else None
    if best is None:
        return routes, built, reports
    if base_spec is not None:
        routes[base_spec.key] = best.result
        built.append(base_spec)

    settings = planner_config or WindRidingConfig()
    samplers = _layer_samplers(fields)
    for spec in variant_specs:
        fraction = spec.wind_corridor_fraction
        if fraction is None:
            continue
        if math.isclose(fraction, best.corridor_fraction, abs_tol=1e-6):
            continue
        plan = plan_wind_riding_route(
            origin,
            destination,
            samplers,
            aircraft=config,
            effort=effort_config,
            config=replace(settings, corridor_override=fraction),
            ground_elevation_at=ground_elevation_at,
            min_clearance_m=min_clearance_m,
            # همان سطح پرواز مسیر اصلی: تفاوت گونه‌ها باید «دالان» باشد، نه
            # ارتفاع. اگر این‌جا ارتفاع آزاد می‌ماند، یک گونه می‌توانست خودش هم
            # سطح دیگری انتخاب کند و مقایسه دو عامل را قاطی می‌کرد.
            cruise_altitudes=[best.altitude_m],
        )
        if plan is None:
            continue
        routes[spec.key] = wind_riding_route_result(
            plan,
            aircraft=config,
            effort=effort_config,
            vertical=vertical_config,
            criterion=criterion,
            ground_elevation_at=ground_elevation_at,
        )
        built.append(spec)
    return routes, built, reports


def _interpolators(field: LayerField) -> tuple[RegularGridInterpolator, RegularGridInterpolator]:
    """درون‌یاب دوبعدی روی شبکه میدان باد (همان میدان، نمونه‌برداری ریزتر)."""
    speed = RegularGridInterpolator(
        (field.lats, field.lons), field.speed_mps, bounds_error=False, fill_value=None
    )
    direction = RegularGridInterpolator(
        (field.lats, field.lons), field.direction_deg, bounds_error=False, fill_value=None
    )
    return speed, direction


def _ground_best_layer(
    fields: list[LayerField],
    config: CostModelConfig,
    destination: tuple[float, float],
    n_lat: int = 25,
    n_lon: int = 61,
    terrain: TerrainModel | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """برای هر سلول زمین، بهترین لایه ارتفاعی را با مدل هزینه واقعی می‌سنجد.

    معیار سنجش: هزینه پرواز روی خط مستقیم همان سلول به مقصد، با باد همان لایه.
    اگر پرواز روی آن لایه ممکن نباشد (باد جانبی بیش از سرعت هوایی)، هزینه بی‌نهایت
    در نظر گرفته می‌شود.

    برمی‌گرداند
    ----------
    (ground_lats, ground_lons, best_layer_index, costs)
    """
    ground_lats = np.linspace(CORRIDOR_BBOX["lat_min"], CORRIDOR_BBOX["lat_max"], n_lat)
    ground_lons = np.linspace(CORRIDOR_BBOX["lon_min"], CORRIDOR_BBOX["lon_max"], n_lon)

    costs = np.full((len(fields), n_lat, n_lon), np.inf)

    for layer_index, field in enumerate(fields):
        speed_at, direction_at = _interpolators(field)
        points = np.array(
            [[la, lo] for la in ground_lats for lo in ground_lons], dtype=float
        )
        speeds = speed_at(points)
        directions = direction_at(points)

        # سلول‌هایی که این سطح پرواز در آن‌ها زیر زمین است (یا فاصلهٔ ایمنی را
        # ندارد) قابل‌پرواز نیستند. بدون این شرط، لایهٔ رنگی هر سلول را در سطحی
        # نشان می‌داد که هواپیما در آن‌جا داخل کوه است — و با مدل زمین، چنین
        # سطحی دیگر «بهترین سطح» نیست، «سطح ناموجود» است.
        if terrain is not None and field.level_kind == "msl":
            local_ground = np.atleast_1d(
                terrain.elevation_at(points[:, 0], points[:, 1])
            )
            blocked = field.altitude - local_ground < MIN_TERRAIN_CLEARANCE_M
        else:
            blocked = np.zeros(len(points), dtype=bool)

        for index, (lat, lon) in enumerate(points):
            if blocked[index]:
                continue
            distance = haversine_km(lat, lon, destination[0], destination[1])
            if distance < 1e-9:
                costs[layer_index].ravel()[index] = 0.0
                continue
            try:
                result = compute_edge_cost(
                    lat,
                    lon,
                    destination[0],
                    destination[1],
                    float(speeds[index]),
                    float(directions[index]),
                    config=config,
                    criterion="time",
                )
                costs[layer_index].ravel()[index] = result.cost
            except InfeasibleEdgeError:
                costs[layer_index].ravel()[index] = np.inf

    best_layer = np.argmin(costs, axis=0)
    # سلول‌هایی که هیچ لایه‌ای قابل پرواز نیست، در جدول رنگی نامشخص می‌مانند.
    unreachable = ~np.isfinite(costs).any(axis=0)
    best_layer = np.where(unreachable, -1, best_layer)
    return ground_lats, ground_lons, best_layer, costs


def _smooth_route(x: np.ndarray, y: np.ndarray, z: np.ndarray, samples: int = 600) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """هموارسازی مسیر با اسپلاین درجه سه (کاملاً نمایشی).

    این منحنی از روی گره‌های مسیریابی‌شده می‌گذرد ولی *ممکن است* بین دو گره از
    داخل سلول‌های شبکه بیرون بزند؛ پس هندسه معتبر همان گره‌هاست که در صحنه هم
    به‌صورت نقاط نمایش داده می‌شوند.

    پارامترسازی با *طول کمان* است و تعداد نمونه‌ها هم بالا نگه داشته می‌شود.
    دلیلش یک ایراد دیده‌شده است: با ۱۶۰ نمونه روی یک مسیر ۱۷۴ کیلومتری هر
    پارهٔ خط روی صفحه حدود یک کیلومتر و روی نمایشگر چند پیکسل می‌شد و منحنی
    «تکه‌تکه» دیده می‌شد، به‌ویژه در فرودی که نقطه‌هایش هر ۲۰ ثانیه (≈۱۰۰ متر)
    ساخته شده‌اند: بخش‌های پرنقطه و کم‌نقطه، طول کمان را ناهمگون می‌کردند و
    دانه‌دانگی فقط در بخش کروز به چشم می‌آمد. پارامترسازی طول‌کمانی + ۶۰۰ نمونه
    فاصلهٔ نمونه‌ها را در کل مسیر یکنواخت می‌کند.
    """
    points = np.column_stack([x, y, z])
    # حذف نقاط تکراری: اسپلاین پارامتریک با گام صفر کار نمی‌کند.
    keep = np.concatenate([[True], np.any(np.diff(points, axis=0) != 0.0, axis=1)])
    points = points[keep]
    if len(points) < 3:
        return points[:, 0], points[:, 1], points[:, 2]

    t = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    t /= t[-1]
    # نمونه‌برداری یکنواخت روی *کمان* انجام می‌شود، نه روی شمارهٔ نمونه‌های
    # ورودی؛ وگرنه بخش‌های پرنقطه (فرود) سهم بیشتری از منحنی می‌گیرند.
    span = np.linspace(0.0, 1.0, samples)
    spline = make_interp_spline(t, points, k=min(3, len(points) - 1))
    smooth = spline(span)
    return smooth[:, 0], smooth[:, 1], smooth[:, 2]



def _route_tube(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    *,
    radius_km: float = ROUTE_TUBE_RADIUS_KM,
    sides: int = ROUTE_TUBE_SIDES,
    stride: int = ROUTE_TUBE_STRIDE,
) -> dict[str, list[float]] | None:
    """لولهٔ مشبکِ دور مسیر — همان منحنی، این بار به‌صورت هندسهٔ واقعی.

    چرا لوله و نه فقط ``line``؟
    ---------------------------
    Plotly خط سه‌بعدی کلفت را با «نوار» می‌کشد: برای هر پاره یک چهارضلعی و برای
    هر گوشه یک قطعهٔ میتر. وقتی پاره در صفحهٔ نمایش کوتاه‌تر از عرض خط شود
    (حالت پیش‌فرض صحنه: ۶۰۰ نمونه روی ۱۷۷ کیلومتر و عرض ۹ پیکسل)، آن قطعه‌ها
    یک‌پیکسلی می‌شوند و خط به یک زنجیر **مهره‌مهره** تبدیل می‌شود — همان چیزی که
    کاربر «گسسته» می‌دید. با عرض ۱ پیکسل (خط مویی) زنجیر نمی‌شود ولی مسیر بی‌ضخامت
    و بی‌حضور می‌شود. راه‌حل: **هندسهٔ واقعی**. لوله یک مش است، پس شکافِ گوشه
    ندارد؛ ضخامتش در فضای داده تعریف می‌شود، یعنی مثل پیکان‌های باد با زوم
    بزرگ و کوچک می‌شود؛ و چون با گرادیان نرم سایه می‌خورد، به چشم یک «رسن» می‌آید.

    چرا قابِ *انتقال موازی* و نه یک بالابر ثابت؟
    ------------------------------------------
    اگر برای هر مقطع یک «بالا»ی ثابت (مثلاً محور z) بگیریم، جایی که مماس مسیر
    موازی آن بالا شود قاب واژگون می‌شود و لوله می‌پیچد. انتقال موازی قاب را در
    طول مسیر می‌چرخاند تا هرگز واژگون نشود — همان روش استاندارد لوله‌کشی.

    پارامتر ``radius_km`` شعاع *نمایشی* است (کیلومتر در فضای صحنه، یعنی همان
    واحدی که z با بزرگ‌نمایی عمودی در آن است)، نه یک پوشش فیزیکی: به‌ازای هر
    متر ارتفاع واقعی، محور z مقدار ``VERTICAL_EXAGGERATION / 1000`` کیلومتر
    جلو می‌رود، پس همین عدد در z حدود چند ده متر ارتفاع واقعی است. این عمداً
    مستند می‌شود تا با «فاصلهٔ ایمنی از زمین» قاطی نشود.

    برمی‌گرداند
    ----------
    dict | None
        آرایه‌های ``x, y, z, i, j, k`` برای ``go.Mesh3d``؛ یا ``None`` اگر مسیر
        کم‌تر از دو نقطه داشته باشد.
    """
    points = np.column_stack(
        [np.asarray(x, dtype=float), np.asarray(y, dtype=float), np.asarray(z, dtype=float)]
    )
    if len(points) < 2:
        return None
    # نمونه‌برداری یکی‌درمیان: حلقه‌های کمتر = مش سبک‌تر، بدون تغییر شکل (نقاط
    # حذف‌شده روی همان منحنی می‌نشینند).
    if stride > 1 and len(points) > 2 * stride:
        kept = points[::stride]
        if not np.allclose(kept[-1], points[-1]):
            kept = np.vstack([kept, points[-1]])
        points = kept
    if len(points) < 2:
        return None

    # مماس هر گره از تفاضل مرکزی؛ دو سر یک‌طرفه.
    tangents = np.gradient(points, axis=0)
    norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    # **گره تکراری.** مسیرهای بازنمونه‌شده و مسیرهای آزمون می‌توانند دو نقطهٔ
    # روی‌هم‌افتاده داشته باشند؛ آن‌جا مماس صفر می‌شود و بدون این اصلاح، حلقه به
    # یک نقطه فرو می‌ریزد (لوله سوراخ می‌شود). مماس گره تکراری از همسایهٔ نزدیک
    # گرفته می‌شود تا هر گره همان حلقهٔ خودش را داشته باشد.
    flat = norms[:, 0] < 1e-12
    if flat.any() and not flat.all():
        first_valid = int(np.flatnonzero(~flat)[0])
        last_valid_tangent = tangents[first_valid]
        for index in range(len(tangents)):
            if flat[index]:
                tangents[index] = last_valid_tangent
            else:
                last_valid_tangent = tangents[index]
        norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    norms[norms < 1e-12] = 1.0
    tangents = tangents / norms

    # قاب اولیه: هر بردار عمود بر مماس اول.
    reference = np.array([0.0, 0.0, 1.0])
    normal = np.cross(tangents[0], reference)
    if float(np.linalg.norm(normal)) < 1e-6:
        normal = np.cross(tangents[0], np.array([0.0, 1.0, 0.0]))
    normal = normal / max(float(np.linalg.norm(normal)), 1e-12)

    ring_x: list[float] = []
    ring_y: list[float] = []
    ring_z: list[float] = []
    previous_tangent = tangents[0]
    for index in range(len(points)):
        tangent = tangents[index]
        if index > 0:
            # انتقال موازی: نرمالِ قبلی به اندازهٔ زاویهٔ بین دو مماس حول محور
            # عمود بر آن دو، چرخانده می‌شود (فرمول رودریگز).
            axis = np.cross(previous_tangent, tangent)
            sine = float(np.linalg.norm(axis))
            cosine = float(np.dot(previous_tangent, tangent))
            if sine > 1e-9:
                unit_axis = axis / sine
                angle = math.atan2(sine, cosine)
                projection = float(np.dot(unit_axis, normal))
                rotated = np.cross(unit_axis, normal)
                normal = (
                    normal * math.cos(angle)
                    + rotated * math.sin(angle)
                    + unit_axis * projection * (1.0 - math.cos(angle))
                )
                normal = normal / max(float(np.linalg.norm(normal)), 1e-12)
            previous_tangent = tangent
        binormal = np.cross(tangent, normal)
        binormal = binormal / max(float(np.linalg.norm(binormal)), 1e-12)
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            offset = radius_km * (math.cos(angle) * normal + math.sin(angle) * binormal)
            ring_x.append(float(points[index][0] + offset[0]))
            ring_y.append(float(points[index][1] + offset[1]))
            ring_z.append(float(points[index][2] + offset[2]))

    faces_i: list[int] = []
    faces_j: list[int] = []
    faces_k: list[int] = []
    for index in range(len(points) - 1):
        base = index * sides
        nxt = (index + 1) * sides
        for side in range(sides):
            a = base + side
            b = base + (side + 1) % sides
            c = nxt + (side + 1) % sides
            d = nxt + side
            faces_i.extend([a, a])
            faces_j.extend([b, c])
            faces_k.extend([c, d])
    return {
        "x": ring_x,
        "y": ring_y,
        "z": ring_z,
        "i": faces_i,
        "j": faces_j,
        "k": faces_k,
    }


def build_scene_figure(
    fields: list[LayerField],
    multi_graph: MultiLayerWindGraph,
    routes: dict[str, RouteResult],
    terrain: TerrainModel,
    specs: tuple[RouteSpec, ...] = ROUTE_SPECS,
    config: CostModelConfig | None = None,
    origin: tuple[float, float] = DEMO_ORIGIN,
    destination: tuple[float, float] = DEMO_DESTINATION,
    station_labels: dict[str, tuple[float, float]] | None = None,
    plot_origin: tuple[float, float] = PLOT_ORIGIN,
    arrow_stride: int = ARROW_STRIDE,
    ground_n_lat: int = 25,
    ground_n_lon: int = 61,
) -> go.Figure:
    """شکل Plotly صحنه سه‌بعدی را می‌سازد (بدون نوشتن فایل).

    پارامتر ``terrain`` مدل ارتفاع زمین است. عمداً پیش‌فرض ندارد: بدون مدل
    ارتفاع، صحنه یک صفحه تخت صفر متری می‌شود که هم شکل زمین را پنهان می‌کند و
    هم محل واقعی هواپیما را غلط نشان می‌دهد، پس صحنه بدون DEM ساخته نمی‌شود.
    پارامترهای ``ground_n_lat``/``ground_n_lon`` دقت شبکه لایه «بهترین لایه» را
    تعیین می‌کنند؛ کم کردن آن‌ها ساخت صحنه را برای آزمون‌ها سریع می‌کند.

    این تابع فقط *هندسه سه‌بعدی* را می‌سازد: سطح زمین، پیکان‌های باد، مسیرها و
    نشانگرها. عنوان، زیرنویس و جدول مقایسه عمداً این‌جا نیستند و در پوستهٔ HTML
    (``_html_document``) به‌صورت متن و جدول واقعی رندر می‌شوند؛ دلیل آن در
    ``write_scene`` توضیح داده شده است.
    """
    aircraft = config or VIZ_AIRCRAFT
    origin_lat, origin_lon = plot_origin

    # حالت «بازی»: یک صحنهٔ تمام‌صفحه، نه چیدمان ساب‌پلات. چیدمان قبلی ۸۰/۲۰
    # بود: یک‌پنجم پنجره همیشه جدول و فضای سفید بود. حالا صحنه کل پنجره را
    # می‌گیرد و جدول بعداً به‌صورت HUD شناور با ``domain`` روی صحنه می‌نشیند.
    fig = go.Figure()

    # ------------------------------------------------------------------
    # ۱) زمین واقعی (DEM) + لایه رنگی «بهترین لایه ارتفاعی» (پیش‌فرض خاموش)
    # ------------------------------------------------------------------
    exag_scale = VERTICAL_EXAGGERATION / 1000.0
    terrain_lon_mesh, terrain_lat_mesh = np.meshgrid(terrain.lons, terrain.lats)
    terrain_x, terrain_y = lonlat_to_km(
        terrain_lat_mesh, terrain_lon_mesh, origin_lat, origin_lon,
        ref_lat=PLOT_SCALE_LAT,
    )
    terrain_text = np.empty(terrain_lat_mesh.shape, dtype=object)
    for row_index in range(terrain_lat_mesh.shape[0]):
        for col_index in range(terrain_lat_mesh.shape[1]):
            terrain_text[row_index, col_index] = (
                f"ارتفاع زمین: {terrain.elevation_m[row_index, col_index]:.0f} متر"
                f"<br>مختصات: {terrain_lat_mesh[row_index, col_index]:.3f}, "
                f"{terrain_lon_mesh[row_index, col_index]:.3f}"
            )

    fig.add_trace(
        go.Surface(
            x=terrain_x,
            y=terrain_y,
            z=terrain.elevation_m * exag_scale,
            surfacecolor=terrain.elevation_m,
            cmin=terrain.min_elevation_m,
            cmax=terrain.max_elevation_m,
            colorscale=TERRAIN_COLORSCALE,
            # رنگ‌نما افقی و پایین صحنه است. حالت عمودی (x=1.005) عرض زیادی از
            # بوم سه‌بعدی را می‌گرفت (عنوان چرخیده + برچسب تیک‌ها) و بوم WebGL
            # باریک‌تر از قاب می‌شد، پس صحنه ناهم‌تراز و بریده دیده می‌شد.
            colorbar=dict(
                orientation="h",
                title=dict(text="ارتفاع زمین (m)", side="top", font=dict(size=11)),
                len=0.5,
                thickness=10,
                x=0.5,
                y=-0.03,
                xanchor="center",
                yanchor="top",
                tickfont=dict(size=10),
            ),
            opacity=1.0,
            text=terrain_text,
            hovertemplate="%{text}<extra></extra>",
            lighting=dict(ambient=0.72, diffuse=0.62, roughness=0.92, specular=0.05),
            name=f"زمین — دامنه ارتفاع {terrain.relief_m:.0f} متر",
            # راهنمای Plotly خاموش است؛ راهنما در پوستهٔ HTML به‌صورت چیپ‌های
            # خوانا با همین ``meta`` ساخته می‌شود (به ``_legend_entries``).
            showlegend=False,
            meta=dict(
                legend=f"زمین (DEM) — دامنه {terrain.relief_m:.0f} متر",
                color="#8bc34a",
                # زمین هرگز پنهان نمی‌شود: با «تنها کردن» یک مسیر باید زمین بماند
                # تا مسیر در فضا معلق به‌نظر نرسد.
                always=True,
            ),
        ),
    )

    # ۱.ب) لایه رنگی «بهترین لایه ارتفاعی» — پیش‌فرض خاموش تا شکل زمین دیده شود.
    ground_lats, ground_lons, best_layer, _ = _ground_best_layer(
        fields,
        aircraft,
        destination,
        n_lat=ground_n_lat,
        n_lon=ground_n_lon,
        terrain=terrain,
    )
    lon_mesh, lat_mesh = np.meshgrid(ground_lons, ground_lats)
    overlay_x, overlay_y = lonlat_to_km(lat_mesh, lon_mesh, origin_lat, origin_lon, ref_lat=PLOT_SCALE_LAT)
    overlay_z = terrain.elevation_at(lat_mesh, lon_mesh) * exag_scale + BEST_LAYER_OVERLAY_OFFSET_KM

    layer_altitudes = [field.altitude for field in fields]
    # مقادیر -1 (بدون لایه قابل پرواز) را به بیرون بازه نگاشت می‌کنیم.
    surface_color = best_layer.astype(float)
    surface_color[best_layer < 0] = np.nan

    overlay_text = np.empty(best_layer.shape, dtype=object)
    for row_index in range(best_layer.shape[0]):
        for col_index in range(best_layer.shape[1]):
            index = best_layer[row_index, col_index]
            label = (
                "نامشخص (هیچ لایه‌ای پروازپذیر نیست)"
                if index < 0
                else f"{layer_altitudes[index]:.0f} متر"
            )
            overlay_text[row_index, col_index] = (
                f"بهترین لایه ارتفاعی: {label}"
                f"<br>مختصات: {ground_lats[row_index]:.3f}, {ground_lons[col_index]:.3f}"
            )

    if bool(np.isfinite(surface_color).any()):
        fig.add_trace(
            go.Surface(
                x=overlay_x,
                y=overlay_y,
                z=overlay_z,
                surfacecolor=surface_color,
                cmin=-0.5,
                cmax=len(layer_altitudes) - 0.5,
                colorscale=[
                    [i / max(len(layer_altitudes) - 1, 1), _LAYER_COLORS.get(alt, "#b2bec3")]
                    for i, alt in enumerate(layer_altitudes)
                ],
                showscale=False,
                opacity=0.75,
                text=overlay_text,
                hovertemplate="%{text}<extra></extra>",
                visible="legendonly",
                name="لایه رنگی: بهترین لایه هر ناحیه",
                showlegend=False,
                meta=dict(legend="بهترین لایه هر ناحیه", color="#f2f0ec"),
            ),
        )

    # ------------------------------------------------------------------
    # ۲) پیکان‌های باد — یک trace برای هر لایه، روی گره‌های خود گراف
    # ------------------------------------------------------------------
    for field in fields:
        altitude = field.altitude
        graph = multi_graph.get_layer(altitude)
        if graph is None:
            continue

        node_ids = list(graph.nodes)
        if not node_ids:
            continue

        node_lats = np.array([graph.get_node(nid).lat for nid in node_ids])
        node_lons = np.array([graph.get_node(nid).lon for nid in node_ids])
        speeds = np.array([graph.get_node(nid).wind_speed_mps for nid in node_ids])
        directions = np.array([graph.get_node(nid).wind_direction_deg for nid in node_ids])

        # نمونه‌برداری یکی‌درمیان شبکه برای خوانایی و hover روان.
        keep = _arrow_indices(len(node_ids), len(field.lons), arrow_stride)
        node_lats = node_lats[keep]
        node_lons = node_lons[keep]
        speeds = speeds[keep]
        directions = directions[keep]

        # پیکان یک سطح، روی صفحهٔ همان سطح می‌نشیند (نه روی زمین محلی)؛ ولی
        # ارتفاع *بالای زمین* همان گره از تفاضل سطح و زمین می‌آید و در hover
        # گفته می‌شود، چون باد همان میدانِ ارتفاع‌بالای‌زمین است.
        node_ground_m = np.atleast_1d(terrain.elevation_at(node_lats, node_lons))
        cone_x, cone_y = lonlat_to_km(node_lats, node_lons, origin_lat, origin_lon, ref_lat=PLOT_SCALE_LAT)
        # پیکان‌ها روی یک **صفحهٔ افقی در سطح پرواز** می‌نشینند، نه روی نسخهٔ
        # موازی زمین. دو دلیل:
        #   ۱) مسیرها هم در همین صفحه‌اند، پس «آیا مسیر موازی باد است؟» با یک
        #      نگاه به همان صفحه پاسخ داده می‌شود. پیش‌تر پیکان‌ها روی سطحی
        #      به‌موازات کوه‌ها بودند و مقایسهٔ هندسی فقط حدس بود.
        #   ۲) باد در ارتفاع *مطلق* تعریف می‌شود؛ باد لایه‌ای که از روی قله و
        #      از روی دشت می‌گذرد یک باد نیست، دو باد مختلف است.
        cone_z = np.full(len(node_lats), altitude) * exag_scale
        # ارتفاع واقعی بالای زمین در هر گره (زمین زیر پیکان + سطح پرواز).
        node_agl = (np.full(len(node_lats), altitude) - node_ground_m)

        # بردار باد: جهت «به‌سوی» = جهت هواشناسی + ۱۸۰ درجه
        to_deg = np.radians(directions + 180.0)
        vector_scale = np.minimum(speeds * ARROW_KM_PER_MS, ARROW_MAX_LENGTH_KM)
        cone_u = vector_scale * np.sin(to_deg)
        cone_v = vector_scale * np.cos(to_deg)

        hover = [
            (
                f"<b>سطح پرواز {altitude:.0f} متر (MSL)</b><br>"
                f"سرعت باد: {speeds[i]:.1f} m/s ({speeds[i] * 3.6:.1f} km/h)<br>"
                f"طول پیکان: {vector_scale[i]:.2f} کیلومتر "
                f"({ARROW_KM_PER_MS:g} km به ازای هر m/s — پس باد تندتر، پیکان بلندتر)<br>"
                f"جهت (از): {directions[i]:.0f}° — {_compass_point(directions[i])}<br>"
                f"ارتفاع بالای زمین: {node_agl[i]:.0f} متر "
                f"(زمین محلی {node_ground_m[i]:.0f} — {node_agl[i]:.0f} = {altitude:.0f})<br>"
                f"مختصات: {node_lats[i]:.3f}, {node_lons[i]:.3f}<br>"
                f"<i>داده سنتزی (مقیاس اکمان از باد سطح ۱۰ متر)</i>"
            )
            for i in range(len(node_lats))
        ]

        # پیکان از دو قطعهٔ *کاملاً کیلومتری* (فضای داده) ساخته می‌شود:
        #   ۱) بدنه: خطی از گره تا نوک، با طول ∝ سرعت باد.
        #   ۲) سر: مخروطی که در *نوک* بدنه می‌نشیند و اندازهٔ آن کسری از طول
        #      همان بدنه است.
        # چون هر دو قطعه در مختصات داده تعریف شده‌اند (نه پیکسل)، با زوم‌کردن
        # صحنه هم‌زمان با زمین بزرگ/کوچک می‌شوند و اندازهٔ ثابت روی صفحه ندارند.
        tip_x = cone_x + cone_u
        tip_y = cone_y + cone_v


        shaft_x: list[float | None] = []
        shaft_y: list[float | None] = []
        shaft_z: list[float | None] = []
        shaft_text: list[str] = []
        for i in range(len(cone_x)):
            shaft_x.extend([float(cone_x[i]), float(tip_x[i]), None])
            shaft_y.extend([float(cone_y[i]), float(tip_y[i]), None])
            shaft_z.extend([float(cone_z[i]), float(cone_z[i]), None])
            shaft_text.extend([hover[i], hover[i], ""])

        fig.add_trace(
            go.Scatter3d(
                x=shaft_x,
                y=shaft_y,
                z=shaft_z,
                mode="lines",
                line=dict(color=_LAYER_COLORS.get(altitude, "#636e72"), width=3),
                text=shaft_text,
                hoverinfo="text",
                name=f"باد سطح {altitude:.0f} متر ({len(cone_x)} پیکان)",
                showlegend=False,
                meta=dict(
                    legend=f"باد سطح {altitude:.0f} متر ({len(cone_x)} پیکان)",
                    color=_LAYER_COLORS.get(altitude, "#636e72"),
                    # هر دو trace پیکان (بدنه + سر) یک گروه نمایشی‌اند، پس
                    # خاموش/تنها کردن یک سطح هر دو جز را با هم می‌برد.
                    group=f"level-{altitude:.0f}",
                ),
                legendgroup=f"level-{altitude:.0f}",
                # پیکان‌ها روشن‌اند: بدون دیدن میدان باد، مقایسه مسیرها فقط
                # ادعا است. هر لایه در راهنما ورودی جداگانه دارد و می‌توان
                # لایه‌های دیگر را خاموش کرد تا hover و خواندن تک‌لایه ساده شود.
                visible=True,
            ),
        )

        # سرِ پیکان در نوک بدنه (نه روی گره): اگر روی گره بنشیند، بدنه را
        # کامل می‌پوشاند و تفاوت طول پیکان‌ها — یعنی همان چیزی که سرعت باد را
        # نشان می‌دهد — دیده نمی‌شود.
        fig.add_trace(
            go.Cone(
                x=tip_x,
                y=tip_y,
                z=cone_z,
                u=cone_u,
                v=cone_v,
                w=np.zeros_like(cone_u),
                text=hover,
                hoverinfo="skip",
                colorscale=[[0.0, _LAYER_COLORS.get(altitude, "#636e72")],
                            [1.0, _LAYER_COLORS.get(altitude, "#636e72")]],
                showscale=False,
                showlegend=False,
                visible=True,
                legendgroup=f"level-{altitude:.0f}",
                meta=dict(
                    legend=f"باد سطح {altitude:.0f} متر ({len(cone_x)} پیکان)",
                    color=_LAYER_COLORS.get(altitude, "#636e72"),
                    group=f"level-{altitude:.0f}",
                    chip=False,
                ),
                # ``absolute`` یعنی ``sizeref`` در واحد داده (کیلومتر) است، پس
                # سر با زوم بزرگ/کوچک می‌شود؛ مقدار پیکسلی ثابت وجود ندارد.
                sizemode="absolute",
                sizeref=ARROW_HEAD_KM,
                anchor="tail",
                name=f"باد سطح {altitude:.0f} م",
            ),
        )

    # ------------------------------------------------------------------
    # ۳) مسیرها: منحنی هموار + گره‌های واقعی
    # ------------------------------------------------------------------
    # گسترهٔ *واقعی* خطوط رسم‌شده جمع می‌شود تا محورها بر پایهٔ آن و کریدور
    # بسته شوند. دلیلش یک ایراد دیده‌شده است: مسیری که از کریدور بیرون می‌رفت
    # (بادسواری موازی باد، تا شمال مرز DEM) از کادر صحنه بیرون می‌زد و «بخشی
    # از مسیر دیده نمی‌شد». محورها باید هر هندسهٔ رسم‌شدهٔ را در بر بگیرند، نه
    # فقط جعبهٔ داده را.
    drawn_x: list[float] = []
    drawn_y: list[float] = []
    drawn_z: list[float] = []

    for spec in specs:
        result = routes.get(spec.key)
        if result is None or len(result.node_ids) < 2:
            continue

        node_lats = np.array([lat for lat, _lon in result.path])
        node_lons = np.array([lon for _lat, lon in result.path])
        # ارتفاع **مطلق** هر گره (MSL). برای گره زمینِ مبدأ/مقصد، ارتفاع صفر
        # یعنی «روی زمین»، پس ارتفاع واقعی زمین همان‌جا جایگزین می‌شود؛ بدون
        # این جایگزینی مسیر از سطح دریا شروع و به آن برمی‌گشت.
        node_msl = np.asarray(result.node_altitudes, dtype=float)
        if node_msl.shape != node_lats.shape:
            node_msl = np.full(node_lats.shape, result.layer_altitude, dtype=float)
        node_elev_m = np.atleast_1d(terrain.elevation_at(node_lats, node_lons))
        node_msl = np.where(node_msl > 0.0, node_msl, node_elev_m)
        node_x, node_y = lonlat_to_km(node_lats, node_lons, origin_lat, origin_lon, ref_lat=PLOT_SCALE_LAT)
        # کلید تغییر: z = ارتفاع *پرواز*، نه ارتفاع زمین + ارتفاع لایه. پیش‌تر
        # مسیر روی نسخهٔ موازی کوه‌ها کشیده می‌شد و هر مسیر چند کیلومتری صعود و
        # فرود بی‌دلیل (و «تیز روی دامنه‌ها») نشان می‌داد، درحالی که یک
        # هواپیما در سطح پرواز خود *تراز* پرواز می‌کند.
        node_z = node_msl * exag_scale
        altitudes_text = "، ".join(f"{alt:.0f}" for alt in result.altitudes_used)
        # یک‌بار حساب می‌شود و هم در hover و هم (در جدول) به‌کار می‌رود؛ فهرست
        # قطعه‌ها می‌تواند هزاران عضو داشته باشد و سه بار پیمودنش فقط کندی است.
        alignment = wind_alignment_profile(result.leg_samples)

        smooth_x, smooth_y, smooth_z = _smooth_route(node_x, node_y, node_z)
        drawn_x.extend(float(value) for value in smooth_x)
        drawn_y.extend(float(value) for value in smooth_y)
        drawn_z.extend(float(value) for value in smooth_z)

        fig.add_trace(
            go.Scatter3d(
                x=smooth_x,
                y=smooth_y,
                z=smooth_z,
                mode="lines",
                # خط مویی: پیوسته در هر زوم (به ``ROUTE_LINE_WIDTH`` نگاه کنید).
                # این trace «هسته» و حامل hover است؛ ضخامت ظاهری از لوله می‌آید.
                line=dict(color=spec.color, width=ROUTE_LINE_WIDTH),
                name=spec.label,
                showlegend=False,
                meta=dict(
                    legend=f"{spec.key} — {spec.short}",
                    color=spec.color,
                    group=spec.key,
                ),
                legendgroup=spec.key,
                hovertemplate=(
                    f"<b>{spec.label}</b><br>"
                    f"مسافت افقی: {result.total_distance_km:.1f} کیلومتر<br>"
                    f"زمان پرواز: {result.estimated_time_hours:.3f} ساعت<br>"
                    f"سطوح پرواز پیموده‌شده: {altitudes_text} متر (MSL)<br>"
                    f"صعود/فرود: {result.total_climb_m:.0f} / {result.total_descent_m:.0f} متر<br>"
                    f"شاخص انرژی: {result.total_energy_index:.3f} (نسبی)<br>"
                    f"باد پشت در {result.tailwind_leg_fraction * 100:.0f}٪ قطعات "
                    f"(میانگین |زاویه مسیر با باد| "
                    f"{wind_alignment_deg(result):.0f}°)<br>"
                    # سنجهٔ *کلی* هم‌راستایی: تفاوت «باد پشت» (فقط علامت مؤلفهٔ
                    # هم‌راستا) و «موازی در حد ۳ درجه» در همین خط روشن می‌شود.
                    f"موازی با باد (≤۳°): {alignment.aligned_share * 100:.0f}٪ "
                    f"— برچسب ترکیبی {alignment.label}<br>"
                    f"تصحیح انتهایی: {alignment.final_correction_km:.1f} "
                    f"کیلومتر آخر<br>"
                    + (
                        f"کمینه فاصله از زمین: {result.min_clearance_m:.0f} متر<br>"
                        if result.min_clearance_m is not None
                        else ""
                    )
                    + f"تعداد تغییر جهت: {result.heading_changes}<br>"
                    # خط ترسیم‌شده با بزرگ‌نمایی عمودی بلندتر از مسافت افقی
                    # است؛ همین خطِ hover توضیح می‌دهد چرا شکل و عدد جدول
                    # یکی به‌نظر نمی‌رسند.
                    f"طول خط روی صفحه (بزرگ‌نمایی ×{VERTICAL_EXAGGERATION:.0f}): "
                    f"{drawn_polyline_km(result, terrain):.0f} کیلومتر"
                    f"{_effort_hover_lines(result)}<extra></extra>"
                ),
            ),
        )

        # **لولهٔ مش روی همان منحنی.** هندسهٔ *واقعی* (مش مثلثی) هیچ گوشه‌ای
        # ندارد که بشکند، پس مسیر در هر زوم یک منحنی پیوسته دیده می‌شود — نه
        # زنجیر مهره‌مهره‌ای که خط کلفتِ plotly در فاصله می‌سازد. ``hoverinfo``
        # خاموش است (خواندن اعداد از خود خط انجام می‌شود) و ``meta`` همان گروه
        # مسیر را می‌گیرد تا خاموش/تنها کردن چیپ و دوبار کلیک، لوله و خط را با
        # هم ببرند.
        tube = _route_tube(smooth_x, smooth_y, smooth_z)
        if tube is not None:
            fig.add_trace(
                go.Mesh3d(
                    **tube,
                    color=spec.color,
                    opacity=1.0,
                    flatshading=False,
                    lighting=dict(ambient=0.82, diffuse=0.5, specular=0.06, roughness=0.9),
                    hoverinfo="skip",
                    showlegend=False,
                    legendgroup=spec.key,
                    name=spec.label,
                    meta=dict(
                        legend=f"{spec.key} — {spec.short}",
                        color=spec.color,
                        group=spec.key,
                        chip=False,
                    ),
                ),
            )

        # **هر مسیر یک منحنی است، نه یک زنجیر.** پیش‌تر هر مسیر *دو* trace داشت:
        # خط (۶۰۰ نمونهٔ اسپلاین) به‌علاوهٔ یک خرده‌نشانگر روی گره‌های خام؛ آن
        # دومی خط را «مهره‌مهره» نشان می‌داد. حالا مسیر یک منحنی پیوسته است
        # (خط مویی + لولهٔ مش روی همان هندسه) و هیچ نشانگر میانی‌ای رسم نمی‌شود.

    # ------------------------------------------------------------------
    # ۴) نشانگر ایستگاه‌ها، مبدأ و مقصد
    # ------------------------------------------------------------------
    if station_labels:
        st_lat = np.array([coords[0] for coords in station_labels.values()])
        st_lon = np.array([coords[1] for coords in station_labels.values()])
        st_x, st_y = lonlat_to_km(st_lat, st_lon, origin_lat, origin_lon, ref_lat=PLOT_SCALE_LAT)
        # ایستگاه‌ها روی *سطح واقعی زمین* می‌نشینند، نه روی صفحه z=0. با فرض
        # صفر، نشانگر ایستگاه‌های روی دامنه‌ها زیر زمین پنهان می‌شد.
        st_z = terrain.elevation_at(st_lat, st_lon) * exag_scale
        st_hover = [
            f"<b>{name}</b><br>ارتفاع زمین: {elev:.0f} متر"
            f"<br>مختصات: {lat:.3f}, {lon:.3f}"
            for name, (lat, lon), elev in zip(
                station_labels,
                zip(st_lat, st_lon, strict=True),
                terrain.elevation_at(st_lat, st_lon),
                strict=True,
            )
        ]
        fig.add_trace(
            go.Scatter3d(
                x=st_x,
                y=st_y,
                z=st_z,
                mode="markers+text",
                marker=dict(color="#2d3436", size=5, symbol="diamond"),
                text=list(station_labels),
                textposition="top center",
                textfont=dict(size=10, color="#2d3436"),
                hovertext=st_hover,
                hoverinfo="text",
                name="ایستگاه هواشناسی",
                showlegend=False,
                # عضوی از گروه «ایستگاه‌ها»ست: چیپ جدا نمی‌گیرد (chip=False) ولی در
                # حالت «تنها کردن» پنهان می‌شود و با «نمایش همه» برمی‌گردد.
                meta=dict(
                    legend="ایستگاه‌های هواشناسی", color="#95a5a6", group="stations", chip=False
                ),
            ),
        )

    for label, (lat, lon), color in (
        ("مبدأ: مشهد", origin, "#00b894"),
        ("مقصد: سبزوار", destination, "#d63031"),
    ):
        x_km, y_km = lonlat_to_km(lat, lon, origin_lat, origin_lon, ref_lat=PLOT_SCALE_LAT)
        # مبدأ/مقصد روی زمین می‌نشینند: مسیر از گره زمین شروع می‌شود و به گره
        # زمین ختم می‌شود، پس نشانگر هم باید همان‌جا باشد. مقدار ثابت قبلی
        # (۲ کیلومتر × بزرگ‌نمایی) نشانگرها را در آسمان معلق می‌کرد.
        ground_m = float(np.atleast_1d(terrain.elevation_at(lat, lon))[0])
        fig.add_trace(
            go.Scatter3d(
                x=[float(x_km)],
                y=[float(y_km)],
                z=[ground_m * exag_scale],
                mode="markers+text",
                marker=dict(color=color, size=8, symbol="x"),
                text=[label],
                textposition="top center",
                textfont=dict(size=11, color=color),
                hovertemplate=(
                    f"<b>{label}</b><br>ارتفاع زمین: {ground_m:.0f} متر"
                    f"<br>مختصات: {lat:.3f}, {lon:.3f}<extra></extra>"
                ),
                name=label,
                showlegend=False,
                # مبدأ و مقصد مثل زمین هرگز پنهان نمی‌شوند: چارچوب مقایسهٔ مسیرها
                # همین دو نقطه است و با «تنها کردن» یک مسیر هم باید دیده شوند.
                meta=dict(always=True),
            ),
        )

    # ------------------------------------------------------------------
    # ۵) مقیاس محورها — از گسترهٔ واقعی کیلومتری، نه از بازهٔ داده
    # ------------------------------------------------------------------
    # مبدأ مختصات نمودار همان گوشهٔ جنوب‌غربی محدوده است، پس گسترهٔ کریدور
    # مستقیماً از خود کریدور می‌آید. محور z هم از کمینه/بیشینهٔ ارتفاع زمین و
    # بالاترین لایهٔ پروازی ساخته می‌شود.
    bbox = CORRIDOR_BBOX
    x_min_km, y_min_km = (
        float(value) for value in lonlat_to_km(bbox["lat_min"], bbox["lon_min"], origin_lat, origin_lon, ref_lat=PLOT_SCALE_LAT)
    )
    x_max_km, y_max_km = (
        float(value) for value in lonlat_to_km(bbox["lat_max"], bbox["lon_max"], origin_lat, origin_lon, ref_lat=PLOT_SCALE_LAT)
    )
    # سطوح پرواز مطلق‌اند، پس سقف محور ارتفاع = ارتفاع‌ترین سطح (نه ارتفاع زمین
    # + ارتفاع لایه). همین تغییر، «آسمان خالی» بالای صحنه را هم برمی‌دارد.
    highest_level_m = max((field.altitude for field in fields), default=0.0)
    z_min_km = float(terrain.min_elevation_m) * exag_scale
    z_max_km = max(
        float(highest_level_m), float(terrain.max_elevation_m)
    ) * exag_scale

    # **کریدور ∪ هندسهٔ رسم‌شده، به‌علاوهٔ یک حاشیهٔ کوچک.** دلیلش یک ایراد
    # دیده‌شده است: مسیری که از جعبهٔ DEM بیرون می‌رفت (بادسواری موازی باد،
    # که تا شمال مرز کریدور دریفت می‌کند) از کادر صحنه بیرون می‌زد و «بخشی از
    # مسیر دیده نمی‌شد». محور باید هر هندسهٔ رسم‌شده را در بر بگیرد، نه فقط
    # جعبهٔ دادهٔ زمین و باد.
    # هندسهٔ رسم‌شده فقط همان خط نیست: لولهٔ نمایشی به شعاع ``ROUTE_TUBE_RADIUS_KM``
    # دور خط می‌پیچد، پس مرز واقعی هر مسیر یک شعاع بیرون‌تر از خود خط است. اندازه‌گیری
    # روی همین صحنه نشان داد مسیری که خطش روی لبهٔ جنوبی کریدور تمام می‌شد (R4 در
    # ``y = 0``) با لوله‌اش ۰.۴۵ کیلومتر بیرون می‌زد. پس حاشیهٔ لوله هم به گستره
    # اضافه می‌شود، وگرنه «بخشی از مسیر بیرون کادر است» باقی می‌ماند.
    if drawn_x:
        tube_margin_km = ROUTE_TUBE_RADIUS_KM
        x_min_km = min(x_min_km, min(drawn_x) - tube_margin_km)
        x_max_km = max(x_max_km, max(drawn_x) + tube_margin_km)
        y_min_km = min(y_min_km, min(drawn_y) - tube_margin_km)
        y_max_km = max(y_max_km, max(drawn_y) + tube_margin_km)
        z_min_km = min(z_min_km, min(drawn_z) - tube_margin_km)
        z_max_km = max(z_max_km, max(drawn_z) + tube_margin_km)
    # حاشیهٔ ۲٪ به سمت بیرون داده، **نه به سمت منفیِ خالی**: مبدأ مختصات
    # گوشهٔ جنوب‌غربی محدوده است و بازهٔ منفیِ بی‌داده فقط ۴ کیلومتر فضای خالی
    # به ابتدای محور اضافه می‌کرد. پس فقط سمتی که هندسه‌ای دارد حاشیه می‌گیرد، و
    # سمت منفی تنها اگر لولهٔ یک مسیر واقعاً زیر صفر برود (R4 در یال جنوبی).
    pad_x = 0.02 * abs(x_max_km - x_min_km)
    pad_y = 0.02 * abs(y_max_km - y_min_km)
    x_min_km = min(x_min_km, 0.0) - (pad_x if x_min_km < 0.0 else 0.0)
    y_min_km = min(y_min_km, 0.0) - (pad_y if y_min_km < 0.0 else 0.0)
    x_max_km += pad_x
    y_max_km += pad_y
    x_extent_km = abs(x_max_km - x_min_km)
    y_extent_km = abs(y_max_km - y_min_km)
    z_extent_km = max(z_max_km - z_min_km, 1e-6)
    # بزرگ‌ترین گستره = ۱؛ باقی نسبت به آن. برای x و y این کار مقیاس یکسان
    # (کیلومتر مساوی در هر دو جهت) می‌دهد.
    aspect_scale = max(x_extent_km, y_extent_km, z_extent_km)
    # گام تیک هر دو محور افقی یکی است تا «هم‌مقیاس بودن» با چشم هم قابل کنترل
    # باشد (گذشته از اثبات عددی در آزمون).
    axis_dtick_km = _nice_km_step(x_extent_km, target_ticks=7)

    # ------------------------------------------------------------------
    # ۶) جدول مقایسه و عنوان: عمداً *داخل* شکل نیستند
    # ------------------------------------------------------------------
    # پیش‌تر جدول با ``go.Table`` و ``domain`` روی صحنه کشیده می‌شد و عنوان هم
    # به‌صورت متن Plotly با کارت نیمه‌شفاف می‌آمد. هر دو مشکل داشتند:
    #   ۱) یک trace از نوع ``table`` سهم صحنه از چیدمان را می‌گیرد و صحنه را
    #      باریک می‌کند.
    #   ۲) متن و جدول داخل canvas سه‌بعدی با ابعاد ثابت رندر می‌شوند؛ با تغییر
    #      اندازه پنجره درشت نمی‌شوند و ریز/ناخوانا می‌مانند.
    # پس هر دو به پوستهٔ HTML واقعی منتقل شدند؛ به ``_html_document`` و
    # ``route_table_rows`` نگاه کنید.

    # ------------------------------------------------------------------
    # ۶) چیدمان «بازی»: صحنهٔ تمام‌صفحه + کارت‌های نیمه‌شفاف روی آن
    # ------------------------------------------------------------------
    exag = f"{VERTICAL_EXAGGERATION:.0f}"
    fig.update_layout(
        scene=dict(
            # پس‌زمینهٔ صحنه آسمان تیره است تا زمین و مسیرها برجسته شوند.
            xaxis=dict(
                title="شرق — کیلومتر",
                range=[x_min_km, x_max_km],
                dtick=axis_dtick_km,
                backgroundcolor="rgba(0,0,0,0)",
                gridcolor="rgba(255,255,255,0.10)",
            ),
            yaxis=dict(
                title="شمال — کیلومتر",
                range=[y_min_km, y_max_km],
                dtick=axis_dtick_km,
                backgroundcolor="rgba(0,0,0,0)",
                gridcolor="rgba(255,255,255,0.10)",
            ),
            zaxis=dict(
                title=f"ارتفاع — کیلومتر × {exag}",
                range=[z_min_km, z_max_km],
                dtick=None if z_max_km - z_min_km < 2.0 * axis_dtick_km else axis_dtick_km,
                backgroundcolor="rgba(0,0,0,0)",
                gridcolor="rgba(255,255,255,0.10)",
            ),
            # مقیاس صریح (نه ``aspectmode="data"``). در حالت ``data``، Plotly
            # نسبت اندازه محورها را از *بازه* داده می‌سازد؛ ولی بازهٔ محورها را
            # سر پیکان‌های باد بزرگ می‌کنند و آن‌ها هم در دو جهت متفاوت بیرون
            #می‌زنند. نتیجه این بود که مقیاس شرق و شمال عملاً یکی نمی‌شد و
            # سطح زمین کشیده به‌نظر می‌رسید. این‌جا ``aspectratio`` مستقیماً از
            # گسترهٔ واقعی کیلومتری محاسبه می‌شود، پس هر کیلومتر در شرق و شمال
            # دقیقاً یک طول روی صفحه دارد.
            aspectmode="manual",
            aspectratio=dict(
                x=x_extent_km / aspect_scale,
                y=y_extent_km / aspect_scale,
                z=z_extent_km / aspect_scale,
            ),
            # مسیر یک نوار باریک و بلند است (≈۲۱۶ کیلومتر شرق‌غرب در برابر ۴۴
            # کیلومتر شمال‌جنوب)، پس دوربین از جنوب با شیب کم تنظیم می‌شود تا کل
            # کریدور در کادر بیاید و تفاوت ارتفاع لایه‌ها هم دیده شود.
            # زاویه دید نسبتاً مرتفع انتخاب شده تا سطح زمین پیکان‌های لایه‌های
            # پایین را نپوشاند (با دید کم‌شیب، صفحه زمین همه‌چیز را پشت خود
            # پنهان می‌کرد).
            # کریدور یک نوار ۲۱۶×۴۵ کیلومتری است. برای پرکردن قاب، دوربین
            # کمی از جنوب به سمت شرق چرخیده و از فاصله‌ای که هر دو انتهای مسیر
            # را در کادر نگه دارد تنظیم شده است.
            camera=dict(
                eye=dict(x=0.78, y=-0.92, z=0.52),
                center=dict(x=0.0, y=0.0, z=0.0),
                up=dict(x=0.0, y=0.0, z=1.0),
            ),
            dragmode="orbit",
        ),
        # راهنمای Plotly کاملاً خاموش است. در پنجرهٔ باریک، راهنمای عمودی با
        # برچسبهای بلند فارسی نیمی از عرض صحنه را می‌پوشاند و زمین و مسیرها را
        # پنهان می‌کرد. جای آن، راهنمای HTML (چیپ‌های رنگ‌دار بالای صفحه) با
        # همان قابلیت روشن/خاموش‌کردن هر trace ساخته می‌شود.
        showlegend=False,
        # حاشیه‌ها صفر: صحنه تا لبهٔ فضای خودش می‌رود (پوستهٔ HTML فاصله‌ها را
        # مدیریت می‌کند).
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0b1220",
        # ارتفاع سیال: اندازه را از پوستهٔ HTML می‌گیرد (۱۰۰٪ قاب صحنه)، نه
        # ارتفاع ثابت ۱۰۰۰ پیکسلی.
        autosize=True,
        template=pio.templates["plotly_dark"],
        font=dict(family="Vazirmatn, Tahoma, DejaVu Sans, sans-serif"),
    )

    return fig


# ======================================================================
# پوستهٔ HTML — عنوان، زیرنویس و جدول به‌صورت متن/جدول واقعی
# ======================================================================
# چرا این‌قدر مهم است: هر متنی که داخل شکل Plotly بماند، داخل canvas سه‌بعدی
# با اندازهٔ *ثابت* رندر می‌شود؛ با بزرگ شدن پنجره درشت نمی‌شود و روی زمین و
# مسیرها ریز و ناخوانا می‌ماند. یک trace از نوع ``table`` هم فقط سهم صحنه از
# چیدمان را می‌خورد و ستون‌های باریکش خواندنی نیستند. پس هر سه در یک سند HTML
# واقعی ساخته می‌شوند.
#
# قالب با ``string.Template`` نوشته شده (نه f-string) چون CSS پرِ آکولاد است و
# این‌جا هیچ آکولادی نیاز به دو برابر شدن ندارد.
_HTML_TEMPLATE = Template(
    """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>$title</title>
<style>
:root {
  --bg: #0b1220;
  --panel: #101a2b;
  --line: rgba(255, 255, 255, 0.14);
  --text: #eef2f7;
  --muted: #a7b4c7;
}
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: Vazirmatn, Tahoma, "DejaVu Sans", "Segoe UI", sans-serif;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* عنوان، هشدار و راهنما *روی* صحنه می‌نشینند (overlay) و ارتفاع صحنه را
   نمی‌خورند. کادر خودش ارتفاع محدود و اسکرول عمودی دارد، پس در پنجرهٔ کوتاه
   همهٔ متن خوانده می‌شود بدون این‌که صحنهٔ سه‌بعدی کوچک شود. */
section.labels {
  position: absolute;
  top: 8px;
  inset-inline-start: 8px;
  width: min(320px, 62%);
  max-height: calc(100% - 16px);
  overflow-y: auto;
  overscroll-behavior: contain;
  background: rgba(9, 14, 26, 0.90);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  z-index: 6;
  scrollbar-width: thin;
}
section.labels::-webkit-scrollbar { width: 8px; }
section.labels::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.22); border-radius: 8px; }
body.labels-hidden section.labels { display: none; }
#toggle-labels {
  position: absolute;
  top: 8px;
  inset-inline-end: 8px;
  z-index: 7;
  background: rgba(9, 14, 26, 0.90);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 5px 11px;
  font: inherit;
  font-size: 12.5px;
  cursor: pointer;
}
section.labels h1 { margin: 0 0 5px; font-size: clamp(15px, 1.3vw, 20px); line-height: 1.4; }
p.warn { margin: 0 0 5px; font-size: clamp(11.5px, 0.9vw, 13px); line-height: 1.6; color: #f6c177; }
details.info > summary {
  cursor: pointer;
  font-size: clamp(12px, 0.95vw, 14px);
  color: var(--text);
  padding: 2px 0;
  user-select: none;
}
ul.chips { display: flex; flex-wrap: wrap; gap: 6px 8px; margin: 8px 0; padding: 0; list-style: none; }
ul.chips li {
  font-size: clamp(12px, 0.95vw, 14px);
  background: rgba(127, 209, 192, 0.13);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 11px;
  white-space: nowrap;
}
p.notes { margin: 0; font-size: clamp(12.5px, 0.95vw, 14.5px); line-height: 1.85; color: var(--muted); }
p.notes b { color: var(--text); }
p.legend-hint { margin: 0 0 6px; font-size: clamp(11.5px, 0.9vw, 13px); line-height: 1.7; color: var(--muted); }
p.legend-hint b { color: var(--text); }
#show-all {
  background: rgba(127, 209, 192, 0.15);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 5px 12px;
  font: inherit;
  font-size: 12.5px;
  margin: 0 0 8px;
  cursor: pointer;
}
#show-all:hover { background: rgba(127, 209, 192, 0.30); }
/* در حالت «تنها کردن»، یک نوار باریک نشان می‌دهد بقیهٔ عناصر پنهانند. */
body.isolated #show-all { background: rgba(246, 193, 119, 0.28); border-color: rgba(246, 193, 119, 0.6); }

/* راهنمای HTML: چیپ‌های رنگ‌دار با همان قابلیت روشن/خاموش‌کردن راهنمای
   Plotly، اما بیرون از بوم سه‌بعدی و با فونت واقعی صفحه. */
.legend { display: flex; flex-wrap: wrap; gap: 6px 7px; margin: 0 0 6px; }
.legend .lg {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--text);
  font: inherit;
  font-size: clamp(11.5px, 0.9vw, 13px);
  padding: 4px 11px;
  cursor: pointer;
  white-space: nowrap;
}
.legend .lg:hover { background: rgba(255, 255, 255, 0.12); }
.legend .lg.off { opacity: 0.5; }
.legend .lg.off .swatch { filter: grayscale(1); }
/* صحنه کل فضای باقی‌مانده را می‌گیرد؛ متن‌ها روی آن شنـاورند. */
main.stage { position: relative; flex: 1 1 auto; min-height: 0; background: var(--bg); }
main.stage .plotly-graph-div { width: 100% !important; height: 100% !important; }
main.stage .main-svg { max-width: 100%; }
footer.cmp {
  flex: 0 1 auto;
  display: flex;
  flex-direction: column;
  max-height: 34vh;
  background: var(--panel);
  border-top: 1px solid var(--line);
}
.cmp-bar { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 14px; padding: 8px 14px; }
.cmp-bar h2 { margin: 0; font-size: clamp(13.5px, 1.05vw, 16px); }
.cmp-bar .hint { flex: 1 1 100%; font-size: clamp(11.5px, 0.9vw, 13px); line-height: 1.65; color: var(--muted); }
.cmp-bar button {
  background: rgba(127, 209, 192, 0.15);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 6px 14px;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.cmp-bar button:hover { background: rgba(127, 209, 192, 0.28); }
.table-wrap { flex: 1 1 auto; min-height: 0; overflow: auto; padding: 0 14px 12px; }
body.collapsed .table-wrap { display: none; }
table { width: 100%; border-collapse: collapse; font-size: clamp(12.5px, 0.95vw, 14.5px); }
th, td { padding: 9px 12px; text-align: center; white-space: nowrap; }
thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #17233a;
  color: var(--text);
  border-bottom: 1px solid var(--line);
  font-weight: 700;
}
tbody tr:nth-child(even) { background: rgba(255, 255, 255, 0.04); }
tbody td:first-child { text-align: start; font-weight: 700; }
td.num { font-variant-numeric: tabular-nums; }
.swatch { display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-inline-end: 8px; vertical-align: -1px; }
/* جدول کوچک شواهد لایه‌ها (چرا مسیر آزاد ارتفاع را عوض نمی‌کند؟) */
table.mini { width: auto; margin: 8px 0 0; font-size: clamp(11.5px, 0.9vw, 13px); }
table.mini th, table.mini td { padding: 5px 10px; text-align: center; }
table.mini caption { caption-side: top; text-align: start; font-size: inherit; color: var(--muted); padding-bottom: 4px; }
table.mini tr.best td { color: #7fd1c0; font-weight: 700; }
</style>
</head>
<body>
<main class="stage">
  <button id="toggle-labels" type="button">پنهان‌کردن متن‌ها</button>
  <section class="labels" id="labels">
    <h1>$heading</h1>
    <p class="warn">باد لایه‌ها سنتزی است • «شاخص انرژی» نسبی است، نه ژول • زمین در مدل مسیریابی مانع نیست</p>
    <div class="legend" role="group" aria-label="راهنمای نمایش لایه‌ها و مسیرها">$legend</div>
    <p class="legend-hint">
      <b>کلیک</b> = روشن/خاموش کردن • <b>دوبار کلیک</b> (روی چیپ یا روی خود مسیر) =
      تنها کردن همان مورد و پنهان‌کردن بقیه • <b>Esc</b> = نمایش همه
    </p>
    <button id="show-all" type="button">نمایش همهٔ عناصر</button>
    <details class="info">
      <summary>جزئیات سناریو، مقیاس‌ها و راهنمای خواندن صحنه</summary>
      <ul class="chips">$chips</ul>
      <p class="notes">$notes</p>
      $layer_evidence
      $gravity_evidence
      $fuel_model
    </details>
  </section>
$plotly
</main>
<footer class="cmp">
  <div class="cmp-bar">
    <h2>$table_title</h2>
    <span class="hint">$table_hint</span>
    <button id="toggle-table" type="button">پنهان‌کردن جدول</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr>$table_head</tr></thead>
      <tbody>$table_body</tbody>
    </table>
  </div>
</footer>
<script>
(function () {
  var btn = document.getElementById('toggle-table');
  if (btn) {
    btn.addEventListener('click', function () {
      var collapsed = document.body.classList.toggle('collapsed');
      btn.textContent = collapsed ? 'نمایش جدول' : 'پنهان‌کردن جدول';
      window.dispatchEvent(new Event('resize'));
    });
  }
  // Plotly با ``responsive:true`` فقط به رویداد resize پنجره گوش می‌دهد؛ اگر
  // سربرگ/جدول بعد از رندر اولیه باز یا بسته شوند، قاب صحنهٔ سه‌بعدی عوض می‌شود
  // و canvases با اندازهٔ قدیم می‌مانند (بخش پایین صحنه بریده می‌شد). این
  // ResizeObserver همان قاب را زیر نظر می‌گیرد و Plotly را دوباره اندازه می‌کند.
  var stage = document.querySelector('main.stage');
  var scene = document.getElementById('scene');
  // عمداً *بی‌قید و شرط* صدا زده می‌شود: اندازهٔ CSS قاب از اول درست است،
  // اما Plotly صحنه را با ارتفاعی که در لحظهٔ رندر اولیه دیده رندر کرده و
  // بوم WebGL را دوباره نمی‌سازد؛ ``Plots.resize`` همان اندازه‌گیری دوباره
  // را انجام می‌دهد (وگرنه پایین صحنه بریده می‌شد).
  function fit() {
    if (!scene || typeof Plotly === 'undefined') { return; }
    if (scene.clientWidth > 0 && scene.clientHeight > 0) {
      Plotly.Plots.resize(scene);
    }
  }
  if (window.ResizeObserver && stage) {
    new ResizeObserver(fit).observe(stage);
  }
  window.addEventListener('resize', fit);
  window.addEventListener('load', fit);
  document.querySelectorAll('details.info').forEach(function (d) {
    d.addEventListener('toggle', fit);
  });
  // متن‌های روی صحنه را می‌توان کامل پنهان کرد تا کل پنجره صحنه باشد.
  var lblBtn = document.getElementById('toggle-labels');
  if (lblBtn) {
    lblBtn.addEventListener('click', function () {
      var hidden = document.body.classList.toggle('labels-hidden');
      lblBtn.textContent = hidden ? 'نمایش متن‌ها' : 'پنهان‌کردن متن‌ها';
    });
  }
  // ------------------------------------------------------------------
  // کنترل نمایش: هر گروه یک trace یا چند trace است (خط مسیر + گره‌هایش،
  // بدنهٔ پیکان + سرش). کلیک = روشن/خاموش، دوبار کلیک = تنها کردن آن گروه و
  // پنهان‌کردن بقیه، دکمهٔ «نمایش همه» یا Esc = بازگشت به وضعیت اولیه.
  // پیش‌تر دوبار کلیک روی مسیر هیچ کاری نمی‌کرد (راهنمای Plotly خاموش بود و
  // رویداد دوبار کلیک هم مدیریت نمی‌شد).
  // ------------------------------------------------------------------
  var GROUPS = $groups_json;
  var ALL_TRACES = $all_traces_json;
  var ALWAYS_VISIBLE = $always_traces_json;
  var chips = Array.prototype.slice.call(document.querySelectorAll('.legend .lg'));

  // هر چیپ گروهش را با نام پیدا می‌کند، نه با ترتیب: نه همهٔ گروه‌ها چیپ دارند
  // (مثلاً «ایستگاه‌ها») و نه تضمینی هست که ترتیب چیپ‌ها با ترتیب گروه‌ها یکی
  // بماند. تطبیق با نام، خطای خاموشِ «کلیک روی چیپ اشتباه» را غیرممکن می‌کند.
  function chipGroupIndex(chip) {
    var id = chip.getAttribute('data-group');
    for (var i = 0; i < GROUPS.length; i++) {
      if (GROUPS[i].group === id) { return i; }
    }
    return -1;
  }

  function restyle(indices, visible) {
    if (!indices.length || typeof Plotly === 'undefined') { return; }
    Plotly.restyle('scene', { visible: visible }, indices);
  }

  function paint() {
    chips.forEach(function (chip) {
      var group = GROUPS[chipGroupIndex(chip)];
      if (!group) { return; }
      chip.setAttribute('data-on', group.on ? '1' : '0');
      chip.classList.toggle('off', !group.on);
    });
    document.body.classList.toggle(
      'isolated',
      GROUPS.some(function (g) { return g.on && g.only; })
    );
  }

  function setGroup(index, on) {
    var group = GROUPS[index];
    if (!group) { return; }
    group.on = on;
    group.only = false;
    restyle(group.traces, on ? true : 'legendonly');
    paint();
  }

  function isolate(index) {
    var group = GROUPS[index];
    if (!group) { return; }
    var keep = group.traces;
    var hide = ALL_TRACES.filter(function (trace) {
      return keep.indexOf(trace) < 0 && ALWAYS_VISIBLE.indexOf(trace) < 0;
    });
    restyle(hide, 'legendonly');
    restyle(keep, true);
    GROUPS.forEach(function (g, i) {
      g.on = (i === index);
      g.only = (i === index);
    });
    paint();
  }

  // گروهی که یک trace عضو آن است (-۱ اگر عضو هیچ گروهی نباشد).
  function groupOf(traceIndex) {
    for (var i = 0; i < GROUPS.length; i++) {
      if (GROUPS[i].traces.indexOf(traceIndex) >= 0) { return i; }
    }
    return -1;
  }

  function showAll() {
    GROUPS.forEach(function (group) {
      group.on = !!group.default;
      group.only = false;
      restyle(group.traces, group.default ? true : 'legendonly');
    });
    paint();
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var index = chipGroupIndex(chip);
      if (index >= 0) { setGroup(index, !GROUPS[index].on); }
    });
    chip.addEventListener('dblclick', function (event) {
      event.preventDefault();
      var index = chipGroupIndex(chip);
      if (index >= 0) { isolate(index); }
    });
  });

  var allBtn = document.getElementById('show-all');
  if (allBtn) { allBtn.addEventListener('click', showAll); }
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { showAll(); }
  });

  // دوبار کلیک روی خود صحنهٔ سه‌بعدی: trace کلیک‌شده پیدا و گروهش تنها می‌شود.
  var plotEl = document.getElementById('scene');
  if (plotEl && plotEl.on) {
    var lastClick = { trace: -1, when: 0 };
    plotEl.on('plotly_click', function (event) {
      if (!event.points || !event.points.length) { return; }
      var trace = event.points[0].curveNumber;
      var now = Date.now();
      if (trace === lastClick.trace && (now - lastClick.when) < 450) {
        var index = groupOf(trace);
        if (index >= 0) { isolate(index); }
        lastClick = { trace: -1, when: 0 };
        return;
      }
      lastClick = { trace: trace, when: now };
    });
  }
  paint();
  setTimeout(fit, 60);
  setTimeout(fit, 400);
})();
</script>
</body>
</html>
"""
)

# ستون‌های جدول مقایسه. ترتیب از راست به چپ است (سند ``dir="rtl"``).
_TABLE_HEADER: tuple[str, ...] = (
    "مسیر",
    "معیار",
    "الگوریتم",
    "سطح پرواز (m MSL)",
    "مسافت افقی (km)",
    "صعود / فرود (m)",
    "کمینه فاصله از زمین (m)",
    "مسافت سه‌بعدی (km)",
    "زمان پرواز (h)",
    "شاخص انرژی",
    "باد پشت",
    "|زاویه با باد| (°)",
    "تغییر جهت (مسیر)",
)

# ستون‌های هم‌راستایی با باد — همه از ``pathfinding.alignment`` می‌آیند و همه
# *مسافت‌وزن*اند.
#
# چرا جدا از ستون «|زاویه با باد| (°)»؟ آن یکی میانگین |زاویهٔ مسیر با جهت
# وزش| است (بدون علامت)، پس مسیر کاملاً رو-به-رو و مسیر کاملاً بادپشت هر دو
# صفر می‌دهند و «بادسواری» را نمی‌شود از آن خواند. این پنج ستون همان را
# می‌گویند: چه سهمی از مسیر در حد ۳ درجه موازی جهت *به‌سوی* باد بود، انحراف
# میانگین در همان بخش، برچسب ترکیبی «درجه – سهم»، مسافت تصحیح *انتهایی*، و
# سهمی که واقعاً با باد جنگید (بیش از ۹۰ درجه).
_ALIGNMENT_HEADER: tuple[str, ...] = (
    "موازی با باد (≤۳°)",
    "انحراف میانگین بخش موازی (°)",
    "ترکیبی (درجه – سهم)",
    "تصحیح انتهایی (km)",
    "جنگ با باد (>۹۰°)",
)

# ستون‌های تلاش موتوری و سوخت — همه از ``pathfinding.effort`` می‌آیند و همه
# «مدل»اند نه اندازه‌گیری (فرض‌ها در جدول مدل زیر همان صحنه اعلام می‌شوند).
_EFFORT_HEADER: tuple[str, ...] = (
    "تصحیح مسیر با موتور (بار)",
    "جمع تغییر سمت (°)",
    "زمان دور (s)",
    "توان اضافهٔ دور (W)",
    "سوخت (kg)",
    "سوخت / ۱۰۰km (kg)",
)


def wind_alignment_deg(result: RouteResult) -> float:
    """میانگین |زاویهٔ بین سمت مسیر روی زمین و جهت *وزش* باد| (درجه).

    این همان عددی است که به چشم نمی‌آید وقتی هندسهٔ صحنه سه‌بعدی است: «مسیر
    چند درجه نسبت به باد کج است؟» ۰ = کاملاً هم‌راستا (باد پشت یا رو-به-رو)،
    ۹۰ = کاملاً عمود. تفاوتش با ``tailwind_leg_fraction`` این است که آن یکی فقط
    *علامت* مؤلفهٔ هم‌راستا را می‌شمارد؛ این یکی *اندازهٔ* ناهم‌راستایی را.

    اگر قطعه‌ای باد نداشته باشد (مثل گذار عمودی)، در میانگین نمی‌آید.
    """
    angles: list[float] = []
    for leg in result.leg_samples:
        distance = float(getattr(leg, "distance_km", 0.0))
        if distance <= 1e-9:
            continue
        wind_toward = (float(leg.wind_direction_from_deg) + 180.0) % 360.0
        diff = abs((float(leg.track_bearing_deg) - wind_toward + 180.0) % 360.0 - 180.0)
        angles.extend([diff] * max(1, int(round(distance))))
    if not angles:
        return float("nan")
    return float(np.mean(angles))


def drawn_polyline_km(result: RouteResult, terrain: TerrainModel) -> float:
    """طول خط مسیر **همان‌طور که در صحنه کشیده می‌شود** (کیلومتر).

    این عدد با هیچ‌یک از اعداد دیگر یکی نیست و عمداً ساخته شده تا تصویر با جدول
    قابل مقایسه باشد. تنها تفاوت این است که مختصات z صحنه ``ارتفاع پرواز ×
    بزرگ‌نمایی عمودی`` است، پس با ضریب ``VERTICAL_EXAGGERATION`` هر کیلومتر
    ارتفاع واقعی به همان تعداد کیلومتر روی صفحه تبدیل می‌شود (مقدار در محور z
    اعلام می‌شود و این عدد از همان ثابت خوانده می‌شود، نه از یک مقدار تکرارشده).

    پیش‌تر این عدد چند ده کیلومتر از «مسافت سه‌بعدی» جدول بیشتر بود، چون مسیر
    روی نسخهٔ موازی کوه‌ها کشیده می‌شد و ناهمواری زمین در طول خط جمع می‌شد. حالا
    مسیر در سطح پرواز خود *تراز* است و مازاد فقط از بزرگ‌نمایی عمودی می‌آید —
    یعنی همان چیزی که روی صفحه دیده می‌شود.
    """
    lats = np.array([lat for lat, _lon in result.path], dtype=float)
    lons = np.array([lon for _lat, lon in result.path], dtype=float)
    if len(lats) < 2:
        return 0.0
    msl = np.asarray(result.node_altitudes, dtype=float)
    if msl.shape != lats.shape:
        msl = np.full(lats.shape, result.layer_altitude, dtype=float)
    elevation = np.atleast_1d(terrain.elevation_at(lats, lons))
    msl = np.where(msl > 0.0, msl, elevation)
    # همان تبدیل مختصات و همان بزرگ‌نمایی‌ای که ``build_scene_figure`` استفاده
    # می‌کند؛ اگر آن تغییر کند این عدد هم با آن عوض می‌شود.
    x, y = lonlat_to_km(lats, lons, *PLOT_ORIGIN)
    z = msl * (VERTICAL_EXAGGERATION / 1000.0)
    return float(
        sum(
            math.dist((x[i], y[i], z[i]), (x[i + 1], y[i + 1], z[i + 1]))
            for i in range(len(x) - 1)
        )
    )


def route_table_rows(
    routes: dict[str, RouteResult],
    specs: tuple[RouteSpec, ...] = ROUTE_SPECS,
    drawn_km: dict[str, float] | None = None,
) -> tuple[list[str], list[list[str]]]:
    """سطرهای جدول مقایسه به‌صورت *متن خام* (بدون HTML).

    برمی‌گرداند ``(سرستون‌ها, سطرها)`` و همان اعداد موتور مسیریابی را گزارش
    می‌کند؛ هیچ عددی دوباره از هندسه ساخته نمی‌شود، جز دو استثنای مستند:

    - ستون «مسافت سه‌بعدی» = مسافت افقی + (صعود + فرود). ``total_distance_km``
      عمداً فقط مسافت *افقی* است، پس این ستون لازم است (دو مسیر با مسافت افقی
      یکسان می‌توانند در ارتفاع ۵۰۰ و ۲۰۰۰ متر باشند).
    - ستون «طول خط روی صفحه» فقط اگر ``drawn_km`` داده شود می‌آید و همان طول
      خط سه‌بعدیِ *ترسیم‌شده* با بزرگ‌نمایی عمودی و ناهمواری زمین است (به
      ``drawn_polyline_km`` نگاه کنید).
    """
    header = list(_TABLE_HEADER) + list(_ALIGNMENT_HEADER) + list(_EFFORT_HEADER)
    if drawn_km is not None:
        header.append("طول خط روی صفحه (km)")

    rows: list[list[str]] = []
    for spec in specs:
        result = routes.get(spec.key)
        if result is None:
            continue
        vertical_km = (result.total_climb_m + result.total_descent_m) / 1000.0
        alignment = wind_alignment_deg(result)
        row = [
            spec.key,
            result.criterion,
            result.algorithm,
            f"{result.layer_altitude:.0f}",
            f"{result.total_distance_km:.1f}",
            f"{result.total_climb_m:.0f} / {result.total_descent_m:.0f}",
            (
                f"{result.min_clearance_m:.0f}"
                if result.min_clearance_m is not None
                else "—"
            ),
            f"{result.total_distance_km + vertical_km:.1f}",
            f"{result.estimated_time_hours:.3f}",
            f"{result.total_energy_index:.3f}",
            f"{result.tailwind_leg_fraction * 100:.0f}٪",
            f"{alignment:.0f}" if alignment == alignment else "—",
            str(result.heading_changes),
        ]
        row.extend(_alignment_cells(result))
        row.extend(_effort_cells(result))
        if drawn_km is not None:
            row.append(f"{drawn_km.get(spec.key, float('nan')):.1f}")
        rows.append(row)
    return header, rows


def _alignment_cells(result: RouteResult) -> list[str]:
    """سلول‌های هم‌راستایی یک مسیر (هم‌ترتیب با ``_ALIGNMENT_HEADER``).

    همه از ``leg_samples`` خود مسیر ساخته می‌شوند — همان قطعه‌هایی که الگوریتم
    تولید کرده — پس «بادسواری» یک ادعای نمایشی نیست که کسی نتواند رد کند.
    """
    profile = wind_alignment_profile(result.leg_samples)
    if profile.total_km <= 0.0:
        return ["—"] * len(_ALIGNMENT_HEADER)
    return [
        f"{profile.aligned_share * 100:.0f}٪",
        f"{profile.parallel_mean_deg:.0f}" if profile.parallel_mean_deg == profile.parallel_mean_deg else "—",
        profile.label,
        f"{profile.final_correction_km:.1f}",
        f"{profile.fighting_share * 100:.0f}٪",
    ]


def _effort_cells(result: RouteResult) -> list[str]:
    """سلول‌های تلاش موتوری یک مسیر (هم‌ترتیب با ``_EFFORT_HEADER``)."""
    effort = result.effort
    if effort is None:
        return ["—"] * len(_EFFORT_HEADER)
    return [
        str(effort.powered_course_changes),
        f"{effort.course_change_deg_total:.1f}",
        f"{effort.turn_time_s:.1f}",
        f"{effort.turn_extra_power_w:.0f}",
        f"{effort.total_fuel_kg:.2f}",
        f"{effort.fuel_per_100km_kg:.2f}",
    ]


def _effort_hover_lines(result: RouteResult) -> str:
    """خطوط hover مربوط به تلاش موتوری و سوخت یک مسیر."""
    effort = result.effort
    if effort is None:
        return ""
    return (
        "<br>"
        f"<b>تلاش موتوری (مدل، نه اندازه‌گیری):</b><br>"
        f"تصحیح مسیر با موتور: {effort.powered_course_changes} بار "
        f"(جمع {effort.course_change_deg_total:.1f}° سمت هوایی)<br>"
        f"زمان دورها: {effort.turn_time_s:.1f} ثانیه • توان اضافهٔ هر دور: "
        f"{effort.turn_extra_power_w:.0f} وات "
        f"(انرژی دور {effort.turn_extra_energy_kj:.2f} کیلوژول)<br>"
        f"انرژی شافت: کروز {effort.cruise_shaft_energy_kj:.0f} + صعود/فرود "
        f"{effort.climb_energy_kj + effort.descent_energy_kj:.0f} کیلوژول<br>"
        f"سوخت: {effort.total_fuel_kg:.2f} کیلوگرم "
        f"({effort.fuel_per_100km_kg:.2f} kg/100 km) — "
        f"کروز {effort.cruise_fuel_kg:.2f} + صعود/فرود {effort.climb_fuel_kg:.2f} "
        f"+ دور {effort.turn_fuel_kg:.4f}"
    )


def _clearance_cell(value: float | None) -> str:
    """سلول «کمینه فاصله از زمین»: عدد یا خط تیره — بدون عدد جعلی."""
    return "—" if value is None else f"{value:.0f}"


def _gravity_evidence_html(
    reports: Sequence[WindRidingLayerReport],
    effort: MotorEffortConfig,
    fields: Sequence[LayerField] | None = None,
) -> str:
    """جدول «گرانش، صعود و فرود» — پاسخ عددی به «چرا بالا نرود؟».

    برای هر لایه، همان مسیر بادسواری جداگانه حساب شده و اجزایش تفکیک می‌شود:
    زمان صعود، زمان سواری، زمان فرود، مسافت و شیب و توان فرود، خمش خط، زمان کل
    و سوخت.
    ستون ``offset`` همان چیز کلیدی است: **زاویهٔ باد با کریدور**. صعود وقتی
    می‌ارزد که این زاویه با ارتفاع کوچک شود (باد هم‌راستاتر) و بزرگ‌ترشدن سرعت
    باد آن را جبران کند؛ اگر باد لایه‌های بالا از کریدور *دورتر* شود، صعود فقط
    زمان و سوخت خرج می‌کند — و این جدول همان را عدد به عدد نشان می‌دهد.

    ``glide_km`` هم مسافت فرود است و ``descent_slope_ratio`` شیب آن؛ فرود روی
    یک شیب *ملایم و ثابت* («۱ به N») انجام و با توان جزئی موتور پرواز می‌شود،
    پس مابه‌ازای گرانش در سوخت حساب می‌شود ولی مسافتش رایگان نیست. دو ستون
    ``شیب فرود`` و ``توان فرود`` همان قرارداد را قابل‌بازبینی می‌کنند: هر شیبی
    که ملایم‌تر از ``۱ به L/D`` باشد یعنی توان موتور بیشتر، و هر شیب تندتر
    یعنی دور آرام کف کار.

    سطوح بدون برنامه هم ردیف می‌شوند و دلیلشان از هندسهٔ همان سطح می‌آید: اگر
    کمینهٔ فاصلهٔ آن سطح از زمین روی کل شبکه زیر آستانه باشد، دلیل «سطح زیر
    رشته‌کوه» است — یک واقعیت قابل‌بررسی، نه یک حدس — و در غیر آن صورت دلیل
    این است که هیچ سمت ثابتی در حد خطای مجاز به مقصد نرسید.
    """
    if not reports:
        return ""

    best_time = min(reports, key=lambda item: item.total_time_hours)
    best_fuel = min(reports, key=lambda item: item.fuel_kg)
    by_level = {report.altitude_m: report for report in reports}
    # سطوحی که برنامه‌ای نگرفتند هم ردیف می‌شوند. حذف‌شدنشان یک *نتیجهٔ داده*
    # است (نه خطا) و - مثل جدول سطح‌های گراف - دلیلش باید کنار عدد بیاید؛
    # وگرنه جدولی که فقط یک ردیف دارد به جای «کدام سطح بهتر است؟» جواب می‌دهد
    # «بقیه نمی‌شود» و دلیلش را نمی‌گوید.
    missing_reasons: dict[float, str] = {}
    if fields is not None:
        for field in fields:
            if field.altitude in by_level:
                continue
            minimum_clearance = float(np.min(field.clearance_m))
            missing_reasons[field.altitude] = (
                "سطح زیر رشته‌کوه: مسیر تراز از گردنه نمی‌گذرد "
                f"(کمینه فاصلهٔ ممکن {minimum_clearance:.0f} متر)"
                if minimum_clearance < MIN_TERRAIN_CLEARANCE_M - 1e-9
                else "هیچ سمت ثابتی به مقصد نرسید (خطای رسیدن بیش از حد مجاز)"
            )
    levels = (
        sorted(field.altitude for field in fields)
        if fields is not None
        else [report.altitude_m for report in reports]
    )
    body_rows: list[str] = []
    for level in levels:
        report = by_level.get(level)
        if report is None:
            # تعداد سلول‌های خالی باید برابر تعداد ستون‌های عددی باشد، وگرنه
            # ردیف «بدون برنامه» یک ستون جابه‌جا می‌شود و یادداشت زیر «سوخت»
            # می‌افتد. قبلاً ۱۲ بود در حالی که ۱۳ ستون عددی وجود داشت.
            body_rows.append(
                f'<tr><td class="num">{level:.0f}</td>'
                + '<td class="num">—</td>' * 14
                + f'<td>{missing_reasons.get(level, "بدون برنامه")}</td></tr>'
            )
            continue
        # ردیف‌های برنده با همان کلاس ``best`` موجود در CSS سبز می‌شوند؛ معنای
        # هر کدام در زیرنویس جدول گفته می‌شود تا نشانهٔ رنگی بدون راهنما نماند.
        best = report is best_time or report is best_fuel
        # همان سنجهٔ هم‌راستاییِ جدول مسیرها، این‌بار سطر‌به‌سطر برای هر سطح:
        # «چند درصد از همین مسیر موازی باد بود» تا مقایسهٔ سطح‌ها فقط بر پایهٔ
        # زمان کل و باد میانه نباشد.
        level_alignment = wind_alignment_profile(report.result.leg_samples)
        body_rows.append(
            f'<tr class="{"best" if best else ""}">'
            f'<td class="num">{report.altitude_m:.0f}</td>'
            f'<td class="num">{report.wind_speed_mps:.1f}</td>'
            f'<td class="num">{report.wind_offset_deg:.0f}°</td>'
            f'<td class="num">{level_alignment.aligned_share * 100:.0f}٪</td>'
            f'<td class="num">{report.climb_time_hours * 60:.1f}</td>'
            f'<td class="num">{report.ride_time_hours * 60:.1f}</td>'
            f'<td class="num">{report.glide_time_hours * 60:.1f}</td>'
            f'<td class="num">{report.glide_km:.1f}</td>'
            f'<td class="num">۱ به {report.descent_slope_ratio:.0f}</td>'
            f'<td class="num">{report.descent_power_fraction * 100:.0f}٪</td>'
            f'<td class="num">{report.turns}</td>'
            f'<td class="num">{_clearance_cell(report.min_clearance_m)}</td>'
            f'<td class="num">{report.total_time_hours:.3f}</td>'
            # چهار رقم اعشار: تفاوت سوخت لایه‌ها بعد از تسویهٔ گرانش فقط در همین
            # رقم‌هاست، پس اگر سه‌رقمی گرد شود دو مقدار متفاوت *یکی* دیده
            # می‌شوند و حکم زیر جدول بی‌پشتوانه به نظر می‌رسد.
            f'<td class="num">{report.fuel_kg:.4f}</td>'
            "<td></td></tr>"
        )

    head = (
        "<tr><th>سطح (m MSL)</th><th>باد (m/s)</th><th>زاویهٔ باد با کریدور</th>"
        "<th>موازی با باد (≤۳°)</th>"
        "<th>صعود (دقیقه)</th><th>سواری (دقیقه)</th><th>فرود (دقیقه)</th>"
        "<th>مسافت فرود (km)</th><th>شیب فرود</th><th>توان فرود</th>"
        "<th>خمش خط</th><th>کمینه فاصله از زمین (m)</th>"
        "<th>زمان کل (h)</th><th>سوخت (kg)</th><th>یادداشت</th></tr>"
    )

    if best_time is best_fuel:
        verdict = (
            f"در این ساعت و این کریدور، یک سطح هم کم‌زمان‌ترین است و هم "
            f"کم‌مصرف‌ترین: <b>{best_time.altitude_m:.0f} متر</b> "
            f"({best_time.total_time_hours:.3f} ساعت، {best_time.fuel_kg:.4f} kg)."
        )
    else:
        extra_minutes = (best_fuel.total_time_hours - best_time.total_time_hours) * 60.0
        saved = best_time.fuel_kg - best_fuel.fuel_kg
        verdict = (
            f"دو سطح مختلف برنده دارند: کم‌زمان‌ترین <b>{best_time.altitude_m:.0f} متر</b> "
            f"({best_time.total_time_hours:.3f} ساعت، {best_time.fuel_kg:.4f} kg) و "
            f"کم‌مصرف‌ترین <b>{best_fuel.altitude_m:.0f} متر</b> "
            f"({best_fuel.total_time_hours:.3f} ساعت، {best_fuel.fuel_kg:.4f} kg). "
            f"یعنی بالاتررفتن {extra_minutes:.1f} دقیقه زمان می‌گیرد و "
            f"{saved:.4f} kg سوخت صرفه‌جویی می‌کند — پس «صعود می‌ارزد یا نه» به "
            f"این بستگی دارد که معیار زمان باشد یا سوخت."
        )

    return (
        '<table class="mini">'
        "<caption>گرانش، صعود و فرود: هر <b>سطح پرواز</b> جداگانه با همان "
        "برنامه‌ریز بادسواری حساب شده. صعود `mgh/η` می‌سوزاند و فرود همان ذخیرهٔ "
        "ارتفاع را خرج می‌کند. فرود روی یک شیب *ملایم* و ثابت انجام می‌شود (ستون "
        "«شیب فرود» = «۱ به N»)، نه روی گلاید بیشینهٔ "
        f"۱ به {effort.lift_to_drag:.0f} — چون یک شیب ملایمتر اختیاری است و نتیجه‌اش "
        "پروفایل تدریجی است، ولی چیز مجانی نیست: موتور باید کمبود رانش را بدهد و "
        "ستون «توان فرود» همان کسر توان کروز است (از توازن `T = D − m·g·sinγ`). "
        "مجموع مسافت و سوخت تقریباً بی‌تغییر می‌ماند چون مسافت بیشترِ فرود، مسافت "
        "کروز را کم می‌کند. ستون «بُرد گلاید بیشینه» = ارتفاع بالای زمین × L/D "
        "است؛ فرود واقعی از آن نقطه شروع می‌شود یا دیرتر. سطح‌هایی که هیچ سمت "
        "ثابتی به مقصدشان نمی‌رساند حذف نمی‌شوند: با خط تیره و ستون «یادداشت» می‌آیند، "
        "چون در این کریدور پاسخ «چرا بالا نرفت؟» بیشتر وقت‌ها همین است که آن سطح از "
        "گردنه رد نمی‌شود. "
        "رایف سبز = بهترین زمان (و اگر جدا باشد) بهترین سوخت. "
        f"{verdict}</caption>"
        f"<thead>{head}</thead><tbody>{''.join(body_rows)}</tbody></table>"
    )


def _fuel_model_html(aircraft: CostModelConfig, effort: MotorEffortConfig) -> str:
    """جدول کوچک «فرض‌های مدل سوخت» تا اعداد سوخت قابل بازبینی باشند.

    ستون سوخت جدول اصلی، خروجی مدل ``pathfinding.effort`` است. اگر فرض‌های آن
    کنار اعداد نباشند، خواننده هیچ راهی برای سنجیدن‌شان ندارد؛ این جدول همان
    فرض‌ها را بالا می‌گذارد و صریح می‌گوید عدد «اندازه‌گیری» نیست.
    """
    rows = [
        ("جرم وسیله", f"{effort.mass_kg:.0f} kg"),
        ("نسبت برآر به پسار (L/D)", f"{effort.lift_to_drag:.1f}"),
        ("پسار کروز", f"{effort.drag_force_n:.1f} N"),
        ("توان شافت کروز", f"{effort.shaft_power_w(aircraft.airspeed_mps) / 1000.0:.2f} kW"),
        ("سهم پسار القایی", f"{effort.induced_drag_fraction * 100:.0f}%"),
        ("کرنش دور / ضریب بار", f"{effort.bank_angle_deg:.0f}° / {effort.load_factor:.2f}"),
        ("راندمان رانش × حرارتی", f"{effort.propulsive_efficiency:.2f} × {effort.thermal_efficiency:.2f}"),
        ("ارزش حرارتی سوخت", f"{effort.fuel_lhv_mj_per_kg:.0f} MJ/kg"),
        ("آستانهٔ «تصحیح مسیر»", f"{effort.course_change_threshold_deg:.1f}° سمت هوایی"),
    ]
    body = "".join(
        f"<tr><th>{name}</th><td class=\"num\">{value}</td></tr>" for name, value in rows
    )
    return (
        "<table class=\"mini\">"
        "<caption>تلاش موتوری و سوخت: <b>فرض‌های مدل</b> (نه اندازه‌گیری). سوخت از "
        "انرژی شافت تقسیم بر ``راندمان حرارتی × LHV`` می‌آید؛ «تصحیح مسیر با "
        "موتور» یعنی تغییر سمت هوایی بیش از آستانه که برای حفظ مسیر روی زمین "
        "لازم است.</caption>"
        f"<tbody>{body}</tbody></table>"
    )


def _layer_evidence_html(
    router: WindRouter,
    origin: tuple[float, float],
    destination: tuple[float, float],
    aircraft: CostModelConfig,
) -> str:
    """جدول کوچک «تک‌تک سطوح پرواز چه می‌گویند؟».

    برای هر سطح، مسیر مقید به همان سطح محاسبه می‌شود و این اعداد کنار هم
    می‌آیند: زمان پرواز، مسافت، صعود لازم و **کمینه فاصله از زمین**. سطحی که
    نتواند از رشته‌کوه رد شود اصلاً مسیر ندارد و با خط تیره می‌آید — همان
    عددی که می‌گوید «چرا همهٔ مسیرها روی سطح پایین نمی‌مانند». مدل زمین این
    جدول را از یک مقایسهٔ باد به یک مقایسهٔ **امکان‌پذیری** بدل می‌کند.
    """
    comparison = router.compare_layers(origin, destination)
    if not comparison.results:
        return ""

    best_altitude = min(
        comparison.results, key=lambda alt: comparison.results[alt].estimated_time_hours
    )
    rows: list[str] = []
    for altitude in router.available_layers:
        result = comparison.results.get(altitude)
        css = ' class="best"' if altitude == best_altitude else ""
        if result is None:
            rows.append(
                f"<tr{css}><td>{altitude:.0f}</td>"
                '<td class="num">—</td><td class="num">—</td>'
                '<td class="num">—</td><td class="num">—</td>'
                '<td>مسیر ندارد: رشته‌کوه بالاتر از این سطح است</td></tr>'
            )
            continue
        clearance = (
            f"{result.min_clearance_m:.0f}"
            if result.min_clearance_m is not None
            else "—"
        )
        rows.append(
            f"<tr{css}><td>{altitude:.0f}</td>"
            f'<td class="num">{result.estimated_time_hours:.3f}</td>'
            f'<td class="num">{result.total_distance_km:.1f}</td>'
            f'<td class="num">{result.total_climb_m:.0f}</td>'
            f'<td class="num">{clearance}</td>'
            f'<td>{"کم‌زمان‌ترین سطح" if altitude == best_altitude else ""}</td></tr>'
        )

    return (
        "<table class=\"mini\">"
        "<caption>هر سطح پرواز جداگانه: مسیر مقید به همان سطح. سطحی که از "
        "رشته‌کوه بین مشهد و نیشابور رد نشود مسیر ندارد — نه اینکه بد باشد. "
        f"(سرعت هوایی {aircraft.airspeed_mps:.0f} m/s)</caption>"
        "<thead><tr><th>سطح (m MSL)</th><th>زمان پرواز (h)</th><th>مسافت (km)</th>"
        "<th>صعود (m)</th><th>کمینه فاصله از زمین (m)</th><th>توضیح</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _legend_entries(figure: go.Figure) -> list[dict[str, object]]:
    """گروه‌های راهنمای HTML را از ``meta`` هر trace می‌سازد.

    هر *گروه* یک چیپ رنگ‌دار می‌گیرد، نه هر trace. گروه با ``meta[\"group\"]``
    تعریف می‌شود و همهٔ traceهایی که کلید گروه یکسان دارند با هم روشن/خاموش
    می‌شوند — بدنهٔ پیکان و سرِ آن، یا خطِ مسیر و نشانگرهای گره‌های آن.
    traceهایی که ``chip=False`` دارند عضوی از گروه‌اند ولی چیپ جدا نمی‌گیرند؛
    پیش‌تر هر trace یک چیپ می‌ساخت و راهنما دو بار هر لایه را نشان می‌داد.

    ``on`` وضعیت اولیه است (لایهٔ «بهترین لایه» با ``legendonly`` شروع می‌شود و
    چیپش خاموش دیده می‌شود) و در صفحه به‌عنوان وضعیت بازنشانی هم استفاده می‌شود.
    """
    groups: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for index, trace in enumerate(figure.data):
        meta = getattr(trace, "meta", None)
        if not isinstance(meta, dict) or "legend" not in meta:
            continue
        key = str(meta.get("group") or meta["legend"])
        entry = groups.get(key)
        if entry is None:
            visible = getattr(trace, "visible", None)
            entry = {
                "group": key,
                "label": str(meta["legend"]),
                "color": str(meta.get("color", "#b2bec3")),
                "traces": [],
                "chip": bool(meta.get("chip", True)),
                "on": visible is not False and visible != "legendonly",
            }
            groups[key] = entry
            order.append(key)
        traces = entry["traces"]
        assert isinstance(traces, list)
        traces.append(index)
    return [groups[key] for key in order]


def _always_traces(figure: go.Figure) -> list[int]:
    """اندیس traceهایی که در حالت «تنها کردن» هم باید بمانند.

    زمین و نشانگرهای مبدأ/مقصد با ``meta[\"always\"]=True`` علامت می‌خورند؛
    بدون آن‌ها مسیر تنها‌شده در فضای خالی شناور به‌نظر می‌رسد.
    """
    always: list[int] = []
    for index, trace in enumerate(figure.data):
        meta = getattr(trace, "meta", None)
        if isinstance(meta, dict) and meta.get("always"):
            always.append(index)
    return always


def _html_document(
    figure: go.Figure,
    *,
    heading: str,
    chips: Sequence[str],
    notes: str,
    table_header: Sequence[str],
    table_rows: Sequence[Sequence[str]],
    table_colors: Sequence[str],
    table_title: str,
    table_hint: str,
    layer_evidence: str = "",
    gravity_evidence: str = "",
    fuel_model: str = "",
) -> str:
    """شکل سه‌بعدی + سربرگ و جدول خوانا را به یک سند HTML خودکفا تبدیل می‌کند.

    ``include_plotlyjs=True`` کتابخانه را *درون* فایل جاسازی می‌کند، پس صفحه
    آفلاین و بدون CDN باز می‌شود.
    """
    plotly_div = pio.to_html(
        figure,
        include_plotlyjs=True,
        full_html=False,
        div_id="scene",
        config={
            "responsive": True,
            # زوم با چرخ ماوس. پیش‌فرض Plotly برای چرخ ماوس خاموش است، پس
            # کاربر نمی‌توانست زوم کند و «بزرگ‌شدن پیکان‌ها با زوم» را ببیند.
            "scrollZoom": True,
            "displaylogo": False,
            # دوبار کلیک نباید زوم/اندازه صحنه را ریست کند؛ در این صفحه همان
            # دوبار کلیک کار «تنها کردن» را انجام می‌دهد.
            "doubleClick": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
    )

    groups = _legend_entries(figure)
    legend_html = "".join(
        (
            f'<button class="lg{"" if entry["on"] else " off"}" type="button"'
            f' data-group="{entry["group"]}"'
            f' data-on="{1 if entry["on"] else 0}"'
            f' title="کلیک: روشن/خاموش • دوبار کلیک: تنها کردن">'
            f'<span class="swatch" style="background:{entry["color"]}"></span>'
            f'{entry["label"]}</button>'
        )
        for entry in groups
        if entry["chip"]
    )
    groups_json = json.dumps(
        [
            {
                "group": entry["group"],
                "label": entry["label"],
                "traces": entry["traces"],
                "on": entry["on"],
                "default": entry["on"],
                "only": False,
            }
            for entry in groups
        ],
        ensure_ascii=False,
    )
    all_traces_json = json.dumps(list(range(len(figure.data))))
    always_traces_json = json.dumps(_always_traces(figure))

    head_cells = "".join(f"<th>{cell}</th>" for cell in table_header)
    body_rows: list[str] = []
    for row, color in zip(table_rows, table_colors, strict=True):
        cells: list[str] = []
        for index, cell in enumerate(row):
            if index == 0:
                cells.append(
                    f'<td><span class="swatch" style="background:{color}"></span>{cell}</td>'
                )
            else:
                cells.append(f'<td class="num">{cell}</td>')
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    return _HTML_TEMPLATE.safe_substitute(
        title=heading,
        heading=heading,
        chips="".join(f"<li>{chip}</li>" for chip in chips),
        legend=legend_html,
        groups_json=groups_json,
        all_traces_json=all_traces_json,
        always_traces_json=always_traces_json,
        notes=notes,
        plotly=plotly_div,
        table_title=table_title,
        table_hint=table_hint,
        table_head=head_cells,
        table_body="".join(body_rows),
        layer_evidence=layer_evidence,
        gravity_evidence=gravity_evidence,
        fuel_model=fuel_model,
    )


def write_scene(
    output_path: str | Path,
    data_path: str | Path,
    config: CostModelConfig | None = None,
    origin: tuple[float, float] = DEMO_ORIGIN,
    destination: tuple[float, float] = DEMO_DESTINATION,
    criterion: str = "time",
    timestamp: str | pd.Timestamp | None = None,
    terrain_path: str | Path = TERRAIN_PATH,
    effort_config: MotorEffortConfig | None = None,
    ground_n_lat: int = 25,
    ground_n_lon: int = 61,
) -> tuple[Path, dict[str, RouteResult]]:
    """صحنه را می‌سازد و به‌صورت یک فایل HTML خودکفا می‌نویسد.

    پارامتر ``config`` مشخصات هواپیمای نمایشی است؛ در صورت ``None`` از
    ``VIZ_AIRCRAFT`` استفاده می‌شود (۲۰ متر بر ثانیه، مستند در همان ماژول).
    پارامتر ``timestamp`` ساعت سناریو است؛ در صورت ``None`` ساعتی انتخاب
    می‌شود که میانگین سرعت باد ایستگاه‌ها بیشینه است (به ``select_scene_hour``
    مراجعه کنید).
    پارامتر ``terrain_path`` فایل DEM است. صحنه **بدون** مدل ارتفاع ساخته
    نمی‌شود: با فرض زمین تخت صفر متری، محل واقعی هواپیما و مبدأ/مقصد غلط
    نمایش داده می‌شود. فایل با ``scripts/fetch_terrain_data.py`` ساخته می‌شود.
    پارامترهای ``ground_n_lat``/``ground_n_lon`` دقت شبکهٔ لایهٔ «بهترین لایه»
    را می‌دهند. این شبکه گران‌ترین بخش ساخت صحنه است (برای هر سلول × هر لایه
    یک ``compute_edge_cost``) و *هیچ* تأثیری روی مسیرها، پیکان‌ها یا جدول
    ندارد؛ پس آزمون‌ها مقدار درشت می‌دهند تا اجرای کل مجموعه چند دقیقه نشود.

    برمی‌گرداند
    ----------
    (مسیر فایل, دیکشنری نتایج مسیرها)
    """
    aircraft = config or VIZ_AIRCRAFT
    effort_model = effort_config or MotorEffortConfig()
    # یک نمونهٔ *مشترک* از نرخ‌های عمودی برای هر سه مصرف‌کننده: روتر گرافی (که
    # زمان گذر را با آن حساب می‌کند) و پروفیل عمودیِ مسیرها (که مسافت رمپ را با
    # همان نرخ می‌سازد). اگر دو جای مختلف ساخته شود، ممکن است شیب گزارش‌شده با
    # شیبی که هزینه پرداخت کرده یکی نباشد.
    vertical_model = VerticalCostConfig()

    terrain = load_terrain(terrain_path)
    raw = pd.read_csv(data_path)
    hour = select_scene_hour(raw) if timestamp is None else pd.Timestamp(timestamp)

    stations = load_station_winds(data_path, timestamp=hour)

    # میدان باد روی **سطوح پرواز MSL** ساخته می‌شود، با ارتفاع بالای زمین در هر
    # گره از تفاضل سطح پرواز و زمین همان گره. دو چیز از همین الگوی شبکه به دست
    # می‌آید که پیش‌تر نبود: مسیر در سطح خود *تراز* است و نمی‌تواند از داخل کوه
    # بگذرد، چون گره‌هایی که فاصلهٔ ایمنی ندارند اصلاً در گراف ساخته نمی‌شوند.
    graph_lats, graph_lons = corridor_lattice(stations)
    level_lon_mesh, level_lat_mesh = np.meshgrid(graph_lons, graph_lats)
    corridor_ground = terrain.elevation_at(level_lat_mesh, level_lon_mesh).reshape(
        level_lat_mesh.shape
    )
    fields = build_level_fields(stations, corridor_ground)

    def ground_elevation_at(lat: float, lon: float) -> float:
        """ارتفاع زمین زیر یک نقطه (متر) — نمونه‌بردار تزریقی به گراف و روتر."""
        return float(np.atleast_1d(terrain.elevation_at(lat, lon))[0])

    multi_graph = build_multi_layer_graph(
        fields,
        config=aircraft,
        criterion=criterion,
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
        edge_terrain_sampler=ground_elevation_at,
    )

    routes = build_routes(
        multi_graph,
        aircraft,
        origin=origin,
        destination=destination,
        effort_config=effort_model,
        vertical_config=vertical_model,
        specs=GRAPH_SPECS,
        ground_elevation_at=ground_elevation_at,
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
    )

    # مسیر بادسواری روی همان میدان بادِ لایه‌ها حساب می‌شود ولی روی گراف نه:
    # یک سمت هوایی ثابت با باد مسیر را می‌برد. اگر باد این کریدور را نبرد،
    # مسیری وجود ندارد و صریح گفته می‌شود.
    #
    # کارنامهٔ همهٔ لایه‌ها همین‌جا ساخته می‌شود و *همان* شیء برای جدول و برای
    # مسیر R5 استفاده می‌شود. اگر R5 را جدا حساب کنیم، دو جست‌وجوی کامل انجام
    # می‌شود (چند دقیقه) و — مهم‌تر — ممکن است ردیفی که جدول «کم‌زمان‌ترین»
    # می‌نامد با خطی که در صحنه کشیده می‌شود یکی نباشد.
    riding_routes, riding_specs, riding_reports = build_wind_riding_routes(
        fields,
        aircraft,
        origin=origin,
        destination=destination,
        effort_config=effort_model,
        criterion=WIND_RIDING_SPECS[0].criterion if WIND_RIDING_SPECS else "time",
        vertical_config=vertical_model,
        ground_elevation_at=ground_elevation_at,
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
    )
    routes.update(riding_routes)
    riding_best = (
        min(riding_reports, key=lambda item: item.total_time_hours)
        if riding_reports
        else None
    )
    riding_key = WIND_RIDING_SPECS[0].key if WIND_RIDING_SPECS else None
    riding_result = riding_routes.get(riding_key) if riding_key is not None else None

    # فهرست کاملِ چیزی که *رسم می‌شود*: مسیرهای گرافی + مسیر بادسواری + گونه‌های
    # هم‌خانوادهٔ آن که واقعاً ساخته شدند. جدول، راهنما و محورها همه از همین
    # فهرست می‌آیند تا یک گونهٔ حذف‌شده (تکراری) در جدول بی‌خط بماند.
    draw_specs: list[RouteSpec] = list(ROUTE_SPECS)
    for spec in riding_specs:
        if spec not in ROUTE_SPECS:
            draw_specs.append(spec)

    station_labels = {
        str(row.station): (float(row.lat), float(row.lon))
        for row in stations.itertuples()
    }

    # سطوحی که مسیر قابل پرواز ندارند — یا باد جانبی بیش از سرعت هوایی، یا
    # رشته‌کوه سر راه. اعلام صریح آن‌ها از سکوت گمراه‌کننده بهتر است.
    time_router = WindRouter(
        multi_graph,
        config=aircraft,
        criterion="time",
        vertical_cost=vertical_model,
        ground_elevation_at=ground_elevation_at,
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
    )
    routable = set(time_router.compare_layers(origin, destination).results)
    unflyable = [alt for alt in multi_graph.available_layers if alt not in routable]

    scenario_note = (
        f"زمان سناریو: {hour:%Y-%m-%d %H:%M} UTC — "
        "ساعتی با بیشینه میانگین سرعت باد ایستگاه‌ها (نه میانگین چندروزه)"
    )
    if unflyable:
        layers_text = "، ".join(f"{alt:.0f}" for alt in unflyable)
        scenario_note += (
            f" • سطوح بدون مسیر قابل پرواز در این کریدور: {layers_text} متر "
            f"(فاصلهٔ ایمنی {MIN_TERRAIN_CLEARANCE_M:.0f} متری از زمین برقرار "
            "نمی‌شود: رشته‌کوه سر راه بالاتر از سطح پرواز است)"
        )

    # R1..R3 روی گراف سه‌بعدی ادغام‌شده (با هزینه صعود/فرود) مسیریابی می‌شوند.
    # اگر هیچ‌کدام ارتفاع را عوض نکنند، این یک *نتیجه* است نه خرابی — و باید
    # صریح گفته شود، وگرنه بیننده یا فکر می‌کند مسیریابی سه‌بعدی کار نمی‌کند یا
    # فکر می‌کند مسیرها واقعاً چندلایه‌اند.
    free_keys = [spec.key for spec in GRAPH_SPECS if not spec.restrict_to_single_layer]
    switching = [
        key for key in free_keys if routes.get(key) is not None and routes[key].is_multilayer
    ]
    if free_keys and not switching:
        scenario_note += (
            " • مسیرهای آزاد "
            f'({"، ".join(free_keys)})'
            " روی گراف سه‌بعدی ادغام‌شده و با پرداخت هزینه صعود/فرود حساب شده‌اند، "
            "اما بهینه‌شان در یک سطح می‌ماند: زمان صعود به سطح بالاتر از سود باد "
            "بیشتر است."
        )
    elif switching:
        switching_text = "، ".join(switching)
        scenario_note += (
            f" • مسیرهای چندسطحی (تغییر سطح پرواز در میانهٔ راه): {switching_text} — "
            "یعنی صعود یکجا و فرود جای دیگری، نه پرواز در یک تراز ثابت."
        )

    # مسیر بادسواری (R5): اگر ساخته شده باشد، اعدادش گفته می‌شود. این مسیر
    # عمداً «تصحیح مسیر» ندارد — تفاوت اصلی‌اش با گراف همین است — ولی اگر
    # نمرسد/قطعهٔ پایانی لازم داشته باشد، صریح نوشته می‌شود.
    if riding_result is not None and riding_key is not None:
        riding_effort = riding_result.effort
        steering = (
            f"{riding_effort.powered_course_changes} بار"
            if riding_effort is not None
            else "—"
        )
        scenario_note += (
            f" • {riding_key} (بادسواری) روی گراف حساب نشده است: یک سمت هوایی ثابت "
            f"با میدان باد پیوسته انتگرال گرفته شده، پس مسیر از *گره‌های گراف* نمی‌گذرد و "
            f"هندسه‌اش با بقیه متفاوت است — ولی مسافت/زمان/سوختش با همان مدل هزینه و "
            f"همان مدل سوخت سنجیده شده تا در همین جدول قابل مقایسه باشد. تصحیح مسیر با "
            f"موتور: {steering} (سمت ثابت)؛ جمع سوخت "
            f"{riding_effort.total_fuel_kg:.2f} kg "
            f"({riding_effort.fuel_per_100km_kg:.2f} kg/100 km)."
            if riding_effort is not None
            else f" • {riding_key} (بادسواری) روی گراف حساب نشده است: یک سمت هوایی ثابت."
        )
        # **گرانش، صعود و فرود.** این بند جای یک تبصرهٔ قدیمی را گرفته است که
        # می‌گفت «فرود R5 با مسیرهای گرافی هم‌قرارداد نیست». آن حرف درست بود ولی
        # منشأ اشکال بود، نه توضیحش: هر سه جا قرارداد فرود را عوض کردیم، پس حالا
        # هر دو نوع مسیر (۱) صعودشان رنج می‌برد، (۲) فرودشان با گرانش انجام و
        # در سوخت تسویه می‌شود. فرق R5 با بقیه دیگر «رایگان‌بودن فرود» نیست،
        # بلکه *شیب* فرود است: مسیرهای گرافی فرود عمودی دارند (یک گذار بی‌مسافت)
        # و R5 یک شیب ملایم و طولانی.
        if riding_effort is not None and riding_best is not None:
            # شماره‌های فرود از همان کارنامه‌ای می‌آید که مسیر رسم‌شده را ساخته،
            # پس متن و شکل نمی‌توانند از هم جدا شوند.
            slope = riding_best.descent_slope_ratio
            power_pct = riding_best.descent_power_fraction * 100.0
            max_glide = effort_model.lift_to_drag
            scenario_note += (
                f" فرود R5 روی یک شیب <b>ملایم و ثابت</b> انجام می‌شود: از "
                f"{riding_best.glide_km:.1f} کیلومتری مقصد (شیب ۱ به {slope:.0f}) "
                f"ارتفاع {riding_result.total_descent_m:.0f} متری‌اش را خرج می‌کند "
                f"و روی همان شیب به زمین مقصد می‌رسد. این شیب از بُرد گلاید "
                f"بیشینهٔ هواپیما (۱ به {max_glide:.0f}) *ملایم‌تر* است، پس موتور "
                f"نمی‌تواند خاموش باشد: با توازن رانش `T = D − m·g·sinγ` کسر توان "
                f"کروز در این فاز حدود {power_pct:.0f}٪ می‌شود و همین عدد هم در "
                "مدل سوخت ادا می‌شود. چرا مسیر ملایم‌تر *گزارش* می‌شود ولی "
                "سوختش تقریباً همان است؟ چون مسافت بیشترِ فرود، مسافت کروز را کم "
                "می‌کند و در مسیری که از زمین شروع و روی زمین تمام می‌شود تنها "
                "هزینهٔ واقعی، کار پسار در طول مسیر است — شکل پروفیل ارتفاع جایش "
                "را عوض می‌کند، نه مقدارش را. بُرد گلاید بیشینه از همین ارتفاع "
                f"{riding_effort.glide_range_km:.1f} کیلومتر است (یعنی با موتور "
                "خاموش هم می‌رسید، ولی به شکل یک شیرجهٔ ۲۷ درجه‌ای روی صفحه)."
            )
        if riding_result.heading_changes:
            scenario_note += (
                f" خط روی زمین {riding_result.heading_changes} بار بیش از آستانه خم می‌شود؛ "
                "این خمش از تغییر باد در طول مسیر می‌آید، نه از فرمانی که خلبان بدهد."
            )
        scenario_note += (
            f" فازهای R5: صعود {riding_result.total_climb_m:.0f} متر، سواری با یک سمت "
            f"ثابت تا {riding_result.layer_altitude:.0f} متر MSL = تراز مسیر، و "
            f"فرود {riding_best.glide_km:.1f} کیلومتری تا زمین. "
            "جدول «گرانش، صعود و فرود» همین مسیر را روی هر سطح جداگانه حساب "
            "کرده است؛ اگر سطح کم‌مصرف‌تری وجود داشته باشد، همان‌جا با عدد دیده "
            "می‌شود."
        )
    elif riding_key is not None:
        scenario_note += (
            f" • {riding_key} (بادسواری) در این ساعت ساخته نشد: هیچ لایه/سمت ثابتی "
            "مقصد را در حد خطای مجاز نگرفت. این یک نتیجهٔ داده است، نه خرابی — "
            "و همان چیزی است که دلیل وجود مسیرهای گرافی‌ست."
        )

    # **خانوادهٔ بادسواری.** چند مسیر بادسواری فقط وقتی کنار هم معنا دارند که
    # تفاوتشان *گفته* شود. تفاوت این‌ها فقط دالان است (تا کجا اجازه دارد از خط
    # مستقیم دور شود تا موازی باد بماند)، و همین یک عدد سهم موازی و زمان را
    # عوض می‌کند. اعداد از خود همان مسیرهای رسم‌شده خوانده می‌شوند، نه از یک
    # جدول دستی.
    variant_keys = [spec.key for spec in riding_specs if spec.key != riding_key]
    if variant_keys:
        pieces = []
        for spec in riding_specs:
            variant_result = riding_routes.get(spec.key)
            if variant_result is None:
                continue
            variant_profile = wind_alignment_profile(variant_result.leg_samples)
            corridor = (
                "خودکار"
                if spec.wind_corridor_fraction is None
                else f"{spec.wind_corridor_fraction:.2f}"
            )
            pieces.append(
                f"{spec.key} (دالان {corridor}): "
                f"{variant_profile.aligned_share * 100:.0f}٪ موازی باد، "
                f"{variant_result.estimated_time_hours:.3f} ساعت"
            )
        scenario_note += (
            " • خانوادهٔ بادسواری روی یک سطح پرواز و با دالان‌های متفاوت: "
            + "؛ ".join(pieces)
            + ". دالان تنگ‌تر = انحراف کمتر از خط مستقیم و دورهٔ کوتاه‌تر، دالان "
            "بازتر = مسافت بیشترِ موازی باد. هر سه، یک مبادله‌اند نه یک برندهٔ "
            "مطلق؛ جدول ستون‌های سوخت و هم‌راستایی را برای همین دارد."
        )
        # گونه‌ای که دالانش همان دالان انتخاب‌شدهٔ مسیر اصلی است، رسم نمی‌شود.
        # این را صریح می‌گوییم تا «چرا R8 نیست؟» یک ابهام نماند.
        duplicates = [
            spec.key
            for spec in WIND_RIDING_VARIANT_SPECS
            if spec.key not in riding_routes
            and spec.wind_corridor_fraction is not None
            and riding_best is not None
            and math.isclose(
                spec.wind_corridor_fraction, riding_best.corridor_fraction, abs_tol=1e-6
            )
        ]
        if duplicates:
            scenario_note += (
                " گونه‌های "
                + "، ".join(duplicates)
                + " رسم نشدند چون دالانشان همان دالان انتخاب‌شدهٔ مسیر اصلی است "
                "(نقطه‌به‌نقطه یک مسیر می‌شدند و خط روی خط می‌افتاد)."
            )

    # اگر دو مسیر کاملاً یکسان شدند، صریح گفته می‌شود؛ دیدن دو خط روی هم بدون
    # توضیح شبیه اشتباه به نظر می‌رسد.
    by_path: dict[tuple[str, ...], list[str]] = {}
    for spec in draw_specs:
        result = routes.get(spec.key)
        if result is None:
            continue
        by_path.setdefault(tuple(result.node_ids), []).append(spec.key)
    coincident = [keys for keys in by_path.values() if len(keys) > 1]
    if coincident:
        groups = "، ".join(" = ".join(keys) for keys in coincident)
        scenario_note += (
            f" • در این میدان باد این مسیرها به یک مسیر یکسان می‌رسند: {groups} "
            "(نقطه‌به‌نقطه یکی هستند، پس روی هم کشیده می‌شوند)"
        )

    # چرا مسیرها تا این حد به هم نزدیک‌اند؟ این سؤال طبیعی است و باید در خود
    # صفحه عدد داشته باشد، نه توضیح شفاهی. جواب در دو ویژگی همین داده است:
    # (۱) جهت باد ایستگاه‌ها کمی فرق می‌کند ولی میدان درون‌یابی‌شده (IDW با
    # نمای ۲) بین ایستگاه‌ها کاملاً صاف می‌شود، پس «ناحیهٔ مطلوب باد» وجود ندارد
    # که مسیر به‌خاطرش منحرف شود؛ (۲) جریمهٔ باد جانبی در مدل انرژی حداکثر چند
    # درصد است (باد ≤ ۸ m/s در برابر سرعت هوایی ۲۰ m/s)، پس معیار زمان و انرژی
    # عملاً یک ترتیب می‌دهند. نتیجه: هم چهار مسیر تقریباً یکی می‌شوند و هم
    # تفاوت مسافت R3 با R1 بسیار کوچک است.
    station_dirs = np.asarray(stations["direction_deg"], dtype=float)
    station_speeds = np.asarray(stations["speed_mps"], dtype=float)
    distances = [result.total_distance_km for result in routes.values()]
    if distances:
        scenario_note += (
            f" • بازهٔ مسافت افقی {len(distances)} مسیر: {min(distances):.1f} تا "
            f"{max(distances):.1f} کیلومتر (تفاوت {max(distances) - min(distances):.2f} "
            "کیلومتر). در این میدان باد جهت تقریباً یکنواخت است "
            f"(جهت ایستگاه‌ها {station_dirs.min():.0f}° تا {station_dirs.max():.0f}°، "
            f"سرعت {station_speeds.min():.1f} تا {station_speeds.max():.1f} m/s) و "
            "درون‌یابی IDW بین ایستگاه‌ها را صاف می‌کند، پس هیچ معیاری از انحراف "
            "از خط مستقیم سود نمی‌برد و همهٔ مسیرها روی یک کریدور می‌افتند؛ "
            "تفاوتشان در زمان/انرژی/ارتفاع است، نه در شکل."
        )

    figure = build_scene_figure(
        fields,
        multi_graph,
        routes,
        terrain,
        specs=tuple(draw_specs),
        config=aircraft,
        origin=origin,
        destination=destination,
        station_labels=station_labels,
        ground_n_lat=ground_n_lat,
        ground_n_lon=ground_n_lon,
    )

    # طول خط ترسیم‌شده هر مسیر (با بزرگ‌نمایی عمودی و ناهمواری زمین). ستون جدول
    # همین است تا شکل صحنه و عدد جدول قابل مقایسه باشند؛ بدون آن، بیننده دو
    # مسیر با مسافت افقی یکسان ولی ارتفاع متفاوت را «متفاوت در مسافت» می‌بیند.
    drawn_km = {
        spec.key: drawn_polyline_km(result, terrain)
        for spec in draw_specs
        if (result := routes.get(spec.key)) is not None
    }
    table_header, table_rows = route_table_rows(
        routes, specs=tuple(draw_specs), drawn_km=drawn_km
    )
    table_colors = [spec.color for spec in draw_specs if spec.key in routes]
    layer_evidence = _layer_evidence_html(time_router, origin, destination, aircraft)
    # جدولی که «چرا مسیر بالاتر نمی‌رود؟» را با عدد جواب می‌دهد. اگر لایهٔ
    # کم‌مصرف‌تر جای دیگری باشد، در همین جدول دیده می‌شود.
    gravity_evidence = _gravity_evidence_html(riding_reports, effort_model, fields)
    fuel_model = _fuel_model_html(aircraft, effort_model)

    notes = (
        "هشدار صداقت: باد لایه‌های ارتفاعی <b>سنتزی</b> است (نمایه اکمان‌مانند از "
        "باد سطح ۱۰ متر)؛ «شاخص انرژی» یک عدد <b>نسبی</b> است نه ژول؛ و زمین در "
        "مدل مسیریابی <b>مانع نیست</b> (بررسی برخورد یا حداقل فاصلهٔ ایمن وجود "
        "ندارد).<br>" + "<br>".join(scenario_note.split(" • "))
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # کل صفحه یک سند HTML واقعی است: عنوان/زیرنویس به‌صورت متن HTML (سایز
    # ``clamp`` که با پنجره درشت می‌شود) و جدول مقایسه به‌صورت <table> واقعی با
    # ``position: sticky`` روی سرستون. دلیل بیرون کشیدن این‌ها از شکل Plotly در
    # بالای همین فایل توضیح داده شده است.
    path.write_text(
        _html_document(
            figure,
            heading="مسیریابی باد — مشهد به سبزوار",
            chips=[
                f"سرعت هوایی {aircraft.airspeed_mps:.0f} m/s "
                f"({aircraft.airspeed_mps * 3.6:.0f} km/h)",
                f"بزرگ‌نمایی عمودی ×{VERTICAL_EXAGGERATION:.0f}",
                f"پیکان‌ها روی گره‌های گراف (گام {ARROW_STRIDE})",
                f"طول پیکان: {ARROW_KM_PER_MS:g} کیلومتر به ازای هر m/s "
                f"(سقف {ARROW_MAX_LENGTH_KM:.0f} کیلومتر)",
                f"زمان سناریو: {hour:%Y-%m-%d %H:%M} UTC",
            ],
            notes=notes,
        table_header=table_header,
        table_rows=table_rows,
            table_colors=table_colors,
            table_title=f"مقایسهٔ {len(table_rows)} مسیر",
            table_hint=(
                "«مسافت افقی» فاصلهٔ روی نقشه است؛ «مسافت سه‌بعدی» صعود/فرود را هم "
                "دارد. دو مسیر می‌توانند مسافت افقی یکسان ولی ارتفاع پرواز متفاوت "
                "داشته باشند. ستون آخر (طول خط روی صفحه) "
                "طول همان خطی است که در صحنه می‌بینید: مسافت افقی + ارتفاع‌ها × "
                f"{VERTICAL_EXAGGERATION:.0f} "
                "+ ناهمواری زمین؛ پس عمداً از بقیه اعداد بزرگ‌تر است. ستون‌های "
                "هم‌راستایی با باد (``pathfinding.alignment``) از خود قطعه‌های مسیر "
                "ساخته می‌شوند و مسافت‌وزن‌اند: «موازی با باد (≤۳°)» یعنی چه سهمی از "
                "مسافت، سمت مسیرش در حد ۳ درجه روی جهت *به‌سوی* باد بود، و «ترکیبی"
                "» آن را در یک عبارت می‌گوید (میانگین انحراف بخش موازی – سهم آن). "
                "«تصحیح انتهایی» یعنی چند کیلومتر آخر مسیر خارج از آن رواداری بود. "
                "این ستون‌ها تفاوت «باد پشت» (فقط علامت مؤلفهٔ هم‌راستا) با "
                "«موازی بودن» را نشان می‌دهند: مسیر می‌تواند باد پشت داشته باشد "
                "(۱۰۰٪) و در عین حال ده‌ها درجه از جهت باد کج باشد (۰٪ موازی). "
                "ستون‌های سوخت از مدل ``pathfinding.effort`` می‌آیند و «مدل»اند نه "
                "اندازه‌گیری (فرض‌ها در «فرض‌های مدل سوخت» بالا نوشته شده‌اند)."
            ),
            layer_evidence=layer_evidence,
            gravity_evidence=gravity_evidence,
            fuel_model=fuel_model,
        ),
        encoding="utf-8",
    )
    return path, routes


def routes_dataframe(
    routes: dict[str, RouteResult],
    specs: tuple[RouteSpec, ...] = ROUTE_SPECS,
) -> pd.DataFrame:
    """جدول خلاصهٔ مسیرها (برای گزارش/آزمون)."""
    rows = []
    for spec in specs:
        result = routes.get(spec.key)
        if result is None:
            continue
        row = result.summary_row()
        row["route"] = spec.key
        row["label"] = spec.label
        rows.append(row)
    return pd.DataFrame(rows)
