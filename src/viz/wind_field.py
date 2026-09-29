"""ساخت میدان باد لایه‌ای و گراف چندلایه برای صحنه‌های مسیریابی.

هشدار صداقت داده
-----------------
این پروژه داده باد در ارتفاع‌های ۵۰۰ تا ۲۰۰۰ متر **ندارد**.
``scripts/fetch_khorasan_data.py`` فقط باد سطح (۱۰ متر) را از Open-Meteo می‌گیرد.
نمایه لایه‌ای این ماژول با ضریب‌های مقیاس/چرخش دستی (اکمان‌مانند) از همان باد
سطح ساخته می‌شود؛ پس هر پیکان و هر میدانی که از این ماژول بیرون می‌آید
**سنتزی** است و باید در خروجی هم همین‌طور برچسب بخورد.

برای باد واقعی چندسطحی باید درخواست به سطح‌های فشاری Open-Meteo
(۹۲۵/۸۵۰/۷۰۰ هکتوپاسکال ≈ ۸۰۰/۱۵۰۰/۳۰۰۰ متر) تغییر کند.

نکته درباره ضریب‌های نمایه
---------------------------
``LAYER_PROFILES`` یک نمایه توانی (power law) با نمای ≈۰.۲۵ به‌علاوه چرخش
اکمان است: سرعت باد **با ارتفاع یکنوا زیاد می‌شود** و جهت با ارتفاع به سمت راست
می‌چرخد. پیش‌تر این اعداد دستی و نایکنوا بودند (باد ۱۰۰۰ و ۱۵۰۰ متر کند‌تر از
۵۰۰ متر)، و همین باعث می‌شد مسیریابی سه‌بعدی هیچ‌وقت ارزش صعود نداشته باشد و
هر چهار مسیر در یک لایه بمانند. با نمایه یکنوا، صعود به لایه بالاتر واقعاً
سرعت زمینی را زیاد می‌کند و بهایش زمان و انرژی صعود است؛ پس خروجی گراف
سه‌بعدی به داده بستگی پیدا می‌کند، نه به انتخاب دستی.

مرجع: نمایه توانی استاندارد برای لایه مرزی خنثی/ناپایدار با نمای ۰.۱۴–۰.۳۴ و
چرخش اکمان ۲۰–۴۵ درجه در ضخامت لایه مرزی. ضرایب این‌جا در محدوده همان مراجع‌اند
و صرفاً یک «فرض مدل» اعلام‌شده‌اند، نه اندازه‌گیری.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pathfinding.cost import CostModelConfig
from pathfinding.graph import MultiLayerWindGraph
from preprocessing.idw import IDWInterpolator
from preprocessing.pathfinding_preparation import (
    speed_direction_to_uv,
    uv_to_speed_direction,
)

__all__ = [
    "LAYER_PROFILES",
    "PROFILE_ANCHORS_AGL",
    "PROFILE_TOP_AGL_M",
    "FLIGHT_LEVELS_MSL",
    "MIN_TERRAIN_CLEARANCE_M",
    "CORRIDOR_BBOX",
    "DEMO_ORIGIN",
    "DEMO_DESTINATION",
    "VIZ_AIRCRAFT",
    "LayerField",
    "load_station_winds",
    "select_scene_hour",
    "profile_at",
    "interpolate_layer_field",
    "build_layer_fields",
    "interpolate_level_field",
    "build_level_fields",
    "corridor_lattice",
    "build_multi_layer_graph",
    "layer_dataframe",
    "lonlat_to_km",
]

# کادر محدوده خراسان (کمی بزرگ‌تر از سه ایستگاه).
#
# **چرا مرز جنوبی ۰.۱۵ درجه عقب‌تر از شمالی‌ها است.** این کادر هم "کادر داده"
# است و هم "کادر مسیریابی": گراف روی همین کادر ساخته می‌شود. کریدور مشهد–سبزوار
# از جنوب رشته‌کوه بینالود می‌گذرد، و پیشانی جنوبی این رشته‌کوه دقیقاً در همین
# عرض‌های ۳۶.۰۵–۳۶.۱۵ قرار دارد: ارتفاع زمین از ۱۹۸۰ متر روی ردیف ۳۶.۰۵ به
# ۱۴۸۴ متر روی ۳۶.۰۰ و ۱۴۱۷ متر روی ۳۵.۹۰ می‌افتد. با مرز قبلی (۳۶.۰۵) تنها
# **یک** ردیف از شبکه گراف فاصلهٔ ایمنی ۳۰۰ متری را در شرق کریدور داشت، پس
# مسیر مقید به پایین‌ترین سطح (R4) ناچار بود روی همان ردیفِ چسبیده به لبهٔ داده
# پرواز کند — و چون آن ردیف یک خط عرض ثابت است، صد کیلومتر خط صاف روی مرز صحنه
# می‌شد. مرز عقب‌تر یعنی داده واقعی دشت جنوبی هم وارد می‌شود و مسیر آزادی دارد
# که از پیشانی کوه فاصله بگیرد، نه اینکه به لبهٔ داده تکیه کند.
CORRIDOR_BBOX = {"lat_min": 35.90, "lat_max": 36.45, "lon_min": 57.45, "lon_max": 59.85}

# مسیر نمایشی: مشهد → سبزوار (۱۷۳.۱ کیلومتر، طولانی‌ترین جفت ایستگاه موجود).
DEMO_ORIGIN = (36.297, 59.606)
DEMO_DESTINATION = (36.215, 57.678)

# نمایه عمودی باد: لنگرهای (ارتفاع *بالای زمین*، ضریب سرعت، چرخش جهت).
# یکنوا در هر دو مؤلفه: هرچه بالاتر، باد تندتر و چرخیده‌تر به راست.
#
# سطر ۱۰ متر همان باد سطح است که این نمایه از آن ساخته می‌شود، پس ضریب ۱ و
# چرخش صفر دارد — نه یک انتخاب، بلکه *تعریف* مبدأ نمایه. حضور همین لنگر باعث
# می‌شود نمایه در ارتفاع‌های کم (مثلاً ۴۰۰ متر بالای یک قله) به‌جای اکstrapolation
# دلبخواه، به باد سطح متصل بماند.
PROFILE_ANCHORS_AGL: tuple[tuple[float, float, float], ...] = (
    (10.0, 1.00, 0.0),
    (500.0, 1.18, 8.0),
    (1000.0, 1.30, 16.0),
    (1500.0, 1.40, 23.0),
    (2000.0, 1.48, 30.0),
)

# بالاتر از این ارتفاع، سرعت و چرخش **ثابت** می‌مانند.
#
# دلیل فیزیکی: نمایه توانی/اکمان فقط داخل لایه مرزی معتبر است و در بالای آن باد
# به مقدار ژئوستروفیک می‌رسد و دیگر با ارتفاع تند‌تر نمی‌شود. دلیل عملی: در این
# کریدور اختلاف ارتفاع زمین ۲.۳ کیلومتر است، پس پرواز با فاصلهٔ ایمن از قله
# ناچار به ارتفاعی می‌رسد که بالای لایه مرزی است؛ اگر آن‌جا هم باد تند‌تر می‌شد،
# «صعود برای باد» پاداش ساختگی می‌گرفت. این سقف صریح، همان پاداش را حذف می‌کند
# و صعود را فقط به قیمت زمان و انرژی سوختش می‌ارزد.
PROFILE_TOP_AGL_M = 2000.0

# لایه‌های نمایشی روی گراف: همان لنگرهای بالای زمین (بدون سطر سطح).
LAYER_PROFILES: tuple[tuple[float, float, float], ...] = tuple(
    anchor for anchor in PROFILE_ANCHORS_AGL if anchor[0] > PROFILE_ANCHORS_AGL[0][0]
)

# سطوح پرواز مسیریابی، **بالای سطح دریا (MSL)** — نه بالای زمین.
#
# این تصمیم همان چیزی است که «مسیر مستقیم» را می‌شکند. وقتی سطح پرواز نسبت به
# زمین تعریف شود، هر مسیر خودبه‌خود از خط‌الارض کوه‌ها «کپی» می‌کند: بر فراز
# قله ۳۱۷۵ متری، ۵۰۰ متر هم بالا می‌رود. آن حرکت واقعی است ولی هزینه‌اش در مدل
# هیچ‌جا حساب نمی‌شد و نتیجه این بود که همهٔ مسیرها روی خط‌الرضای کوه می‌خوابیدند
# و مسیریابی هیچ دلیلی برای دور زدن کوه یا صعود یکجا نداشت. با سطح پرواز MSL:
#   * مسیر در یک سطح، *تراز* است (خط صاف، همان چیزی که به چشم می‌آید)،
#   * گذر از یک قله فقط از سطحی ممکن است که فاصلهٔ ایمنی زیرش را داشته باشد،
#   * و انتخاب «از روی کوه» یا «از گردنهٔ کم‌ارتفاع جنوبی» یک معاوضهٔ واقعی است.
FLIGHT_LEVELS_MSL: tuple[float, ...] = (1500.0, 2200.0, 2900.0, 3600.0)

# کمترین فاصلهٔ مجاز عمودی با زمین در برنامه‌ریزی مسیر (متر).
#
# گره‌ها و یال‌هایی که زیر این آستانه باشند از گراف حذف می‌شوند، پس هیچ مسیری
# نمی‌تواند از داخل زمین رد شود. عدد یک فرض برنامه‌ریزی اعلام‌شده است (≈۱۰۰۰ فوت).
MIN_TERRAIN_CLEARANCE_M = 300.0

# دقت شبکه گراف: ۹ گره در عرض و ۲۵ گره در طول → ۲۲۵ گره در هر لایه.
GRAPH_LAT_STEP = 0.05
GRAPH_LON_STEP = 0.10
# فاصله حداکثر یال: بدون این محدودیت گراف «کامل» می‌شود و ساخت آن غیرعملی است.
GRAPH_MAX_EDGE_KM = 20.0

# تبدیل درجه به کیلومتر (تقریب استاندارد در عرض جغرافیایی خراسان).
_KM_PER_DEG_LAT = 111.32

# هواپیمای نمایشی صحنه‌ها.``CostModelConfig`` پیش‌فرض ۵۰ متر بر ثانیه
# (≈۱۸۰ کیلومتر بر ساعت) دارد؛ اسکریپت‌های بصری‌سازی این پروژه از ابتدا با
# ۲۰ متر بر ثانیه (≈۷۲ کیلومتر بر ساعت) کار می‌کردند، یعنی یک پهپاد کوچک‌تر.
# این تصمیم واقعی است و باید یک‌جا گرفته شود: با ۵۰ متر بر ثانیه، بادهای ۸ تا
# ۱۷ متر بر ثانیه این منطقه بسیار ضعیف‌اند و هر چهار معیار به یک مسیر یکسان
# می‌رسند؛ با ۲۰ متر بر ثانیه باد نسب به سرعت هواپیما مهم می‌شود و تفاوت
# معیارها و لایه‌ها واقعاً دیده می‌شود. مقدار در متن صحنه اعلام می‌شود.
VIZ_AIRCRAFT = CostModelConfig(
    airspeed_mps=20.0,
    induced_drag_coeff=0.3,
    headwind_penalty_coeff=0.25,
)


@dataclass(frozen=True)
class LayerField:
    """میدان باد یک لایه ارتفاعی روی یک شبکه منظم.

    پارامترها
    ----------
    altitude : float
        ارتفاع لایه (متر).
    lats, lons : ndarray
        محورهای شبکه (درجه).
    speed_mps : ndarray, شکل (n_lat, n_lon)
        سرعت باد روی شبکه.
    direction_deg : ndarray, شکل (n_lat, n_lon)
        جهت باد (قرارداد هواشناسی: از کجا می‌وزد).
    scale, rotation_deg : float
        ضریب‌های نمایه لایه‌ای که این میدان با آن‌ها ساخته شده است.
    synthetic : bool
        همیشه ``True`` در وضعیت فعلی داده: این میدان از باد سطح ۱۰ متر با نمایه
        اکمان‌مانند ساخته شده و باد اندازه‌گیری‌شده در آن ارتفاع نیست.
    station_coords, station_speed_mps, station_direction_deg : ndarray
        داده ایستگاه‌ها در همین لایه (ورودی درون‌یابی)، برای صحنه.
    """

    altitude: float
    lats: np.ndarray
    lons: np.ndarray
    speed_mps: np.ndarray
    direction_deg: np.ndarray
    scale: float
    rotation_deg: float
    station_coords: np.ndarray
    station_speed_mps: np.ndarray
    station_direction_deg: np.ndarray
    synthetic: bool = True
    ground_elevation_m: np.ndarray | None = None
    agl_m: np.ndarray | None = None
    scale_grid: np.ndarray | None = None
    rotation_grid: np.ndarray | None = None
    level_kind: str = "agl"

    @property
    def ground_m(self) -> np.ndarray:
        """ارتفاع زمین زیر هر گره (متر). برای میدان‌های قدیمی صفر است."""
        if self.ground_elevation_m is None:
            return np.zeros_like(self.speed_mps)
        return self.ground_elevation_m

    @property
    def agl(self) -> np.ndarray:
        """ارتفاع واقعی این میدان **بالای زمین** در هر گره (متر).

        در میدان‌های لایه‌ای قدیمی همهٔ گره‌ها روی یک ارتفاع ثابت بالای زمین
        هستند؛ در میدان‌های سطح پرواز، ارتفاع بالای زمین از تفاضل سطح پرواز و
        زمین *در هر گره* می‌آید و در طول مسیر تغییر می‌کند.
        """
        if self.agl_m is None:
            return np.full_like(self.speed_mps, self.altitude)
        return self.agl_m

    @property
    def clearance_m(self) -> np.ndarray:
        """فاصلهٔ عمودی هر گره از زمین زیر خودش (متر)."""
        if self.level_kind != "msl":
            return np.full_like(self.speed_mps, self.altitude)
        return self.altitude - self.ground_m

    def legal_mask(self, min_clearance_m: float) -> np.ndarray:
        """گره‌هایی که فاصلهٔ ایمنی از زمین را رعایت می‌کنند."""
        return self.clearance_m >= min_clearance_m - 1e-9


def profile_at(
    agl_m: np.ndarray | float,
) -> tuple[np.ndarray, np.ndarray]:
    """نمایه عمودی باد در یک ارتفاع **بالای زمین**: ``(ضریب سرعت، چرخش جهت)``.

    درون‌یابی خطی روی لگاریتم ارتفاع بین لنگرها (نمایهٔ توانی در آن فضا یک خط
    است) و **ثابت‌ماندن** بیرون از بازهٔ لنگرها. به همین دلیل ``profile_at``
    روی مقدارهای لنگر—از باد سطح ۱۰ متر تا ۲۰۰۰ متر—دقیقاً همان ضرایب
    ``LAYER_PROFILES`` را برمی‌گرداند و چیزی جز «تعمیم پیوستهٔ همان نمایه» نیست.

    پیش‌تر باد فقط روی چهار ارتفاع گسسته وجود داشت، پس هر پروازی ناچار بود یکی
    از همان چهار عدد ثابت را استفاده کند. حالا ارتفاع پرواز یک متغیر پیوستهٔ
    مستقیم از زمین است و باد هر گره در ارتفاع *واقعی خودش* نمونه‌برداری می‌شود.
    """
    agl = np.asarray(agl_m, dtype=float)
    anchor_agl = np.array([anchor[0] for anchor in PROFILE_ANCHORS_AGL], dtype=float)
    anchor_scale = np.array([anchor[1] for anchor in PROFILE_ANCHORS_AGL], dtype=float)
    anchor_rotation = np.array([anchor[2] for anchor in PROFILE_ANCHORS_AGL], dtype=float)

    clipped = np.clip(agl, anchor_agl[0], PROFILE_TOP_AGL_M)
    log_agl = np.log(clipped)
    scale = np.interp(log_agl, np.log(anchor_agl), anchor_scale)
    rotation = np.interp(log_agl, np.log(anchor_agl), anchor_rotation)
    return scale, rotation


def select_scene_hour(df: pd.DataFrame) -> pd.Timestamp:
    """ساعتی را انتخاب می‌کند که میانگین سرعت باد ایستگاه‌ها بیشینه است.

    صحنه باید یک «پرواز در یک زمان مشخص» را نشان دهد، نه یک اقلیم میانگین:
    باد این منطقه در طول ۴۸ ساعت به‌شدت می‌چرخد (جهت‌ها از ۱۱ تا ۳۵۲ درجه)، پس
    یک میدان میانگین‌گیری‌شده روی زمان یک میدان ضعیف و کم‌معنا می‌سازد. انتخاب
    ساعت با یک معیار صریح انجام می‌شود (قوی‌ترین باد میانگین) تا سلیقه‌ای نباشد،
    و زمان انتخاب‌شده در متن صحنه اعلام می‌شود.
    """
    if "timestamp" not in df.columns:
        raise ValueError("Wind data has no 'timestamp' column to select an hour from.")
    per_hour = df.assign(_ts=pd.to_datetime(df["timestamp"])).groupby("_ts")["speed"].mean()
    if per_hour.empty:
        raise ValueError("Wind data has no records to select an hour from.")
    return pd.Timestamp(per_hour.idxmax())


def load_station_winds(
    csv_path: str | Path,
    timestamp: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """باد هر ایستگاه را برمی‌گرداند: برای یک ساعت مشخص، یا میانگین وکتوری.

    پارامتر ``timestamp`` اگر داده شود، فقط همان ساعت استفاده می‌شود (هر ایستگاه
    یک رکورد) که فیزیکی‌ترین حالت برای یک سناریوی پرواز است. اگر ``None`` باشد،
    باد روی زمان میانگین گرفته می‌شود — اما **میانگین وکتوری** روی مؤلفه‌های
    ``u``/``v``، نه میانگین حسابی روی درجه (میانگین حسابی جهت‌های دایره‌ای
    نادرست است).
    """
    df = pd.read_csv(csv_path)
    required = {"station", "lat", "lon", "speed", "direction"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Wind data is missing required columns: {sorted(missing)}")

    df = df.assign(timestamp=pd.to_datetime(df["timestamp"] if "timestamp" in df.columns else None))

    if timestamp is not None:
        selected = pd.Timestamp(timestamp)
        df = df[df["timestamp"] == selected]
        if df.empty:
            raise ValueError(f"No wind records found at timestamp {selected}.")

    u_series, v_series = speed_direction_to_uv(df["speed"], df["direction"])
    df = df.assign(_u=u_series, _v=v_series)

    aggregated = df.groupby("station", as_index=False).agg(
        lat=("lat", "first"),
        lon=("lon", "first"),
        _u=("_u", "mean"),
        _v=("_v", "mean"),
    )

    speed, direction = uv_to_speed_direction(aggregated["_u"], aggregated["_v"])
    return (
        aggregated.assign(speed_mps=speed, direction_deg=direction)
        .drop(columns=["_u", "_v"])
        .sort_values("station")
        .reset_index(drop=True)
    )


def corridor_lattice(
    stations: pd.DataFrame,
    lat_step: float = GRAPH_LAT_STEP,
    lon_step: float = GRAPH_LON_STEP,
    bbox: dict[str, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """شبکه گراف کریدور: ``(lats, lons)`` — همان شبکه‌ای که میدان‌های باد روی آن
    نمونه‌برداری می‌شوند. صحنه باید **دقیقاًً** همین شبکه را برای ارتفاع زمین
    بگیرد؛ یک شبکه ۱ سلول جابجا، ارتفاع هر گره را ۱ گره جابجا می‌کند.
    """
    box = CORRIDOR_BBOX if bbox is None else bbox
    extra = stations[["lat", "lon"]].to_numpy(dtype=float)
    return _bbox_lattice(box, lat_step, lon_step, extra_coords=extra)


def _bbox_lattice(
    bbox: dict[str, float],
    lat_step: float,
    lon_step: float,
    extra_coords: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """شبکه منظم داخل کادر محدوده (شامل هر دو لبه).

    مختصات ``extra_coords`` (مثلاً ایستگاه‌ها) به محورها اضافه می‌شوند تا خودِ
    ایستگاه‌ها هم گره گراف باشند. بدون این کار، ``find_nearest_node`` مبدأ/مقصد
    را با اختلاف چند کیلومتر جابجا می‌کند و مسافت مسیر با فاصله واقعی دو شهر
    یکی در نمی‌آید.
    """
    lats = np.arange(bbox["lat_min"], bbox["lat_max"] + lat_step / 2, lat_step)
    lons = np.arange(bbox["lon_min"], bbox["lon_max"] + lon_step / 2, lon_step)

    if extra_coords is not None and len(extra_coords) > 0:
        coords = np.asarray(extra_coords, dtype=float)
        inside = (
            (coords[:, 0] >= bbox["lat_min"])
            & (coords[:, 0] <= bbox["lat_max"])
            & (coords[:, 1] >= bbox["lon_min"])
            & (coords[:, 1] <= bbox["lon_max"])
        )
        if inside.any():
            lats = np.unique(np.concatenate([lats, coords[inside, 0]]))
            lons = np.unique(np.concatenate([lons, coords[inside, 1]]))

    return lats, lons


def interpolate_layer_field(
    stations: pd.DataFrame,
    profile: tuple[float, float, float],
    lats: np.ndarray,
    lons: np.ndarray,
    power: float = 2.0,
) -> LayerField:
    """میدان باد یک لایه را با IDW از داده ایستگاه‌ها روی شبکه می‌سازد.

    مؤلفه‌های ``u`` و ``v`` جداگانه درون‌یابی می‌شوند (نه سرعت و جهت)، چون
    درون‌یابی مستقیم زاویه در محل گِردشدن ۰/۳۶۰ درجه خطا می‌دهد.
    """
    altitude, scale, rotation_deg = profile

    coords = stations[["lat", "lon"]].to_numpy(dtype=float)
    station_speed = stations["speed_mps"].to_numpy(dtype=float) * scale
    station_direction = (stations["direction_deg"].to_numpy(dtype=float) + rotation_deg) % 360.0

    u, v = speed_direction_to_uv(
        pd.Series(station_speed), pd.Series(station_direction)
    )

    lon_mesh, lat_mesh = np.meshgrid(lons, lats)
    targets = np.column_stack([lat_mesh.ravel(), lon_mesh.ravel()])

    interpolator = IDWInterpolator(power=power)
    u_est = interpolator.interpolate_scalar(targets, coords, u.to_numpy(dtype=float))
    v_est = interpolator.interpolate_scalar(targets, coords, v.to_numpy(dtype=float))

    speed_est = np.sqrt(u_est**2 + v_est**2)
    direction_est = (np.degrees(np.arctan2(-u_est, -v_est)) + 360.0) % 360.0

    return LayerField(
        altitude=altitude,
        lats=lats,
        lons=lons,
        speed_mps=speed_est.reshape(lat_mesh.shape),
        direction_deg=direction_est.reshape(lat_mesh.shape),
        scale=scale,
        rotation_deg=rotation_deg,
        station_coords=coords,
        station_speed_mps=station_speed,
        station_direction_deg=station_direction,
    )


def build_layer_fields(
    stations: pd.DataFrame,
    lat_step: float = GRAPH_LAT_STEP,
    lon_step: float = GRAPH_LON_STEP,
    bbox: dict[str, float] | None = None,
    power: float = 2.0,
) -> list[LayerField]:
    """میدان باد همه لایه‌های ``LAYER_PROFILES`` را می‌سازد."""
    box = CORRIDOR_BBOX if bbox is None else bbox
    station_coords = stations[["lat", "lon"]].to_numpy(dtype=float)
    lats, lons = _bbox_lattice(box, lat_step, lon_step, extra_coords=station_coords)
    return [
        interpolate_layer_field(stations, profile, lats, lons, power=power)
        for profile in LAYER_PROFILES
    ]


def _surface_grid(
    stations: pd.DataFrame,
    lats: np.ndarray,
    lons: np.ndarray,
    power: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """میدان *سطح* (۱۰ متر) روی شبکه: ``(سرعت، جهت، شکل شبکه)``.

    باد همهٔ ارتفاع‌ها از همین یک میدان ساخته می‌شود: نمایهٔ عمودی فقط یک ضریب
    سرعت و یک چرخش جهت روی آن اعمال می‌کند. این دقیقاً همان چیزی است که
    ``LAYER_PROFILES`` انجام می‌داد، ولی یک‌بار برای همهٔ ارتفاع‌ها.
    """
    coords = stations[["lat", "lon"]].to_numpy(dtype=float)
    u, v = speed_direction_to_uv(stations["speed_mps"], stations["direction_deg"])

    lon_mesh, lat_mesh = np.meshgrid(lons, lats)
    targets = np.column_stack([lat_mesh.ravel(), lon_mesh.ravel()])
    interpolator = IDWInterpolator(power=power)
    u_surface = interpolator.interpolate_scalar(targets, coords, u.to_numpy(dtype=float))
    v_surface = interpolator.interpolate_scalar(targets, coords, v.to_numpy(dtype=float))

    speed = np.sqrt(u_surface**2 + v_surface**2)
    direction = (np.degrees(np.arctan2(-u_surface, -v_surface)) + 360.0) % 360.0
    return speed, direction, lat_mesh.shape


def interpolate_level_field(
    stations: pd.DataFrame,
    level_msl: float,
    lats: np.ndarray,
    lons: np.ndarray,
    ground_elevation: np.ndarray,
    power: float = 2.0,
) -> LayerField:
    """میدان باد یک **سطح پرواز MSL** را می‌سازد.

    تفاوت کلیدی با ``interpolate_layer_field``: ارتفاع *بالای زمین* این‌جا ثابت
    نیست. باد هر گره در ارتفاع واقعی خودش بالای زمین نمونه‌برداری می‌شود، یعنی
    ``level_msl - elevation(lat, lon)``. روی دشت باد سطح پایین و روی قله باد
    چند هزار متر بالاتر را می‌بیند — همان فیزیکی که به آن برمی‌خوریم.
    """
    ground = np.asarray(ground_elevation, dtype=float)
    if ground.shape != (len(lats), len(lons)):
        raise ValueError(
            f"ground_elevation shape {ground.shape} does not match the "
            f"{len(lats)}x{len(lons)} lattice."
        )

    surface_speed, surface_direction, grid_shape = _surface_grid(stations, lats, lons, power)
    agl = level_msl - ground.ravel()
    scale, rotation = profile_at(agl)

    speed = (surface_speed * scale).reshape(grid_shape)
    direction = ((surface_direction + rotation) % 360.0).reshape(grid_shape)

    return LayerField(
        altitude=level_msl,
        lats=lats,
        lons=lons,
        speed_mps=speed,
        direction_deg=direction,
        scale=float(np.mean(scale)),
        rotation_deg=float(np.mean(rotation)),
        station_coords=stations[["lat", "lon"]].to_numpy(dtype=float),
        # ایستگاه‌ها روی زمین خودشان می‌نشینند؛ ارتفاع بادشان همان ارتفاع لایه
        # نیست، پس مقدار «سطح» را نگه می‌داریم تا نمایش/آزمون آن را اشتباه نخواند.
        station_speed_mps=stations["speed_mps"].to_numpy(dtype=float),
        station_direction_deg=stations["direction_deg"].to_numpy(dtype=float),
        ground_elevation_m=ground,
        agl_m=agl,
        scale_grid=np.asarray(scale, dtype=float),
        rotation_grid=np.asarray(rotation, dtype=float),
        level_kind="msl",
    )


def build_level_fields(
    stations: pd.DataFrame,
    terrain_elevation: np.ndarray,
    levels: tuple[float, ...] = FLIGHT_LEVELS_MSL,
    lat_step: float = GRAPH_LAT_STEP,
    lon_step: float = GRAPH_LON_STEP,
    bbox: dict[str, float] | None = None,
    power: float = 2.0,
    terrain_lats: np.ndarray | None = None,
    terrain_lons: np.ndarray | None = None,
) -> list[LayerField]:
    """میدان باد همهٔ سطوح پرواز MSL را می‌سازد.

    ``terrain_elevation`` یک آرایهٔ ``(n_lat, n_lon)`` روی **همان شبکه** است که
    گراف روی آن ساخته می‌شود (خروجی ``RegularGridInterpolator`` روی شبکهٔ زمین).
    """
    box = CORRIDOR_BBOX if bbox is None else bbox
    station_coords = stations[["lat", "lon"]].to_numpy(dtype=float)
    lats, lons = _bbox_lattice(box, lat_step, lon_step, extra_coords=station_coords)
    return [
        interpolate_level_field(stations, level, lats, lons, terrain_elevation, power=power)
        for level in levels
    ]


def layer_dataframe(field: LayerField) -> pd.DataFrame:
    """``LayerField`` را به DataFrame موردانتظار ``WindGraph`` تبدیل می‌کند.

    برای میدان‌های MSL، فاصلهٔ هر گره از زمین هم منتقل می‌شود تا سازندهٔ گراف
    بتواند گره‌های داخل زمین را حذف کند و مسیری از میان کوه رد نشود.
    """
    lon_mesh, lat_mesh = np.meshgrid(field.lons, field.lats)
    frame = pd.DataFrame(
        {
            "lat": lat_mesh.ravel(),
            "lon": lon_mesh.ravel(),
            "altitude": field.altitude,
            "wind_speed": field.speed_mps.ravel(),
            "wind_direction": field.direction_deg.ravel(),
        }
    )
    if field.level_kind == "msl":
        frame["ground_elevation"] = field.ground_m.ravel()
    return frame


def build_multi_layer_graph(
    fields: list[LayerField],
    config: CostModelConfig | None = None,
    criterion: str = "time",
    max_edge_distance_km: float = GRAPH_MAX_EDGE_KM,
    min_clearance_m: float = 0.0,
    edge_terrain_sampler: object | None = None,
) -> MultiLayerWindGraph:
    """گراف چندلایه را از میدان‌های باد ساخته‌شده روی شبکه گراف می‌سازد.

    همان میدانی که پیکان‌های صحنه را می‌سازد این‌جا وزن یال‌ها را تعیین می‌کند،
    پس مسیرها و پیکان‌ها هر دو از یک میدان می‌آیند. تنها تفاوت این است که
    گره‌های گراف روی همان شبکه‌ای نمونه‌برداری شده‌اند که پیکان‌ها روی آن رسم
    می‌شوند، بنابراین در محل هر پیکان مقدار باد دقیقاً همان مقدار گره گراف است.

    ``min_clearance_m`` فاصلهٔ ایمنی از زمین است؛ سازندهٔ گراف گره‌های زیر این
    آستانه و یال‌هایی که زمین زیرشان بالاتر از سطح پرواز می‌شود را حذف می‌کند.
    ``edge_terrain_sampler`` یک ``Callable[[float, float], float]`` است که ارتفاع
    زمین را بین دو سر یال نمونه‌برداری می‌کند تا یالی که از روی یک قله می‌گذرد
    ولی دو سرش پایین‌ترند حذف شود.
    """
    frames = [layer_dataframe(field) for field in fields]
    data = pd.concat(frames, ignore_index=True)
    return MultiLayerWindGraph.build_from_dataframe(
        data,
        config=config,
        criterion=criterion,
        max_edge_distance_km=max_edge_distance_km,
        min_clearance_m=min_clearance_m,
        edge_terrain_sampler=edge_terrain_sampler,
        layer_altitudes=tuple(field.altitude for field in fields),
    )


def lonlat_to_km(
    lat: np.ndarray | float,
    lon: np.ndarray | float,
    origin_lat: float,
    origin_lon: float,
    ref_lat: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """تبدیل مختصات جغرافیایی به مختصات تخت کیلومتری نسبت به یک مبدأ.

    برای صحنه سه‌بعدی لازم است تا محورها واحد یکسان (کیلومتر) داشته باشند و
    بزرگ‌نمایی عمودی قابل‌اعلام باشد. این تصویر تخت فقط برای *نمایش* است؛
    همه محاسبات مسیریابی روی مختصات جغرافیایی انجام می‌شود.

    ``origin_lat``/``origin_lon`` فقط **جابجایی** مبدأ هستند (تا محورها منفی
    نشوند). عرضی که ضریب کیلومتر بر درجهٔ شرق–غرب روی آن حساب می‌شود
    ``ref_lat`` است و اگر داده نشود همان ``origin_lat`` می‌ماند. تفکیک این دو
    لازم است چون کادر از سه ایستگاه ساخته می‌شود و ارتفاع کادر می‌تواند به چند
    ده کیلومتر برسد: با گرفتن مقیاس روی گوشهٔ کادر (نه عرض میانه)، محور
    شرق–غرب به‌طور سیستماتیک چند دهم درصد خطا می‌دهد و «تصویر، جدول را اثبات
    می‌کند» از دست می‌رود.
    """
    lat_arr = np.asarray(lat, dtype=float)
    lon_arr = np.asarray(lon, dtype=float)
    scale_lat = origin_lat if ref_lat is None else ref_lat
    y_km = (lat_arr - origin_lat) * _KM_PER_DEG_LAT
    x_km = (lon_arr - origin_lon) * _KM_PER_DEG_LAT * np.cos(np.radians(scale_lat))
    return x_km, y_km
