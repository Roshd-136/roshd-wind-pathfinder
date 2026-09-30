"""مدل رقومی ارتفاع (DEM) کریدور مسیریابی برای صحنه سه‌بعدی.

چرا جدا از داده باد؟
---------------------
داده باد این پروژه فقط سرعت/جهت باد است و هیچ ارتفاع زمینی در آن نیست. اما
صحنه سه‌بعدی بدون شکل زمین **گمراه‌کننده** است: پرواز «در ارتفاع ۵۰۰ متر» تنها
وقتی معنا دارد که معلوم باشد ۵۰۰ متر *بالای زمین* است. ارتفاع سطح زمین در
کریدور مشهد–سبزوار بین حدود ۸۸۰ تا ۱۶۰۰ متر تغییر می‌کند؛ پس نمایش ارتفاع
لایه‌ها روی یک صفحه تخت صفر متری، هم شکل زمین را حذف می‌کند و هم محل واقعی
هواپیما را غلط نشان می‌دهد.

منبع داده
---------
ارتفاع‌ها از سرویس Elevation اوپن‌متیو (بر پایه DEM کپرنیکوس GLO-90) خوانده و
در ``data/khorasan_terrain.csv`` ذخیره می‌شوند؛ فایل ذخیره‌شده مرجع است تا
ساخت صحنه آفلاین و تکرارپذیر بماند. بازتولید فایل با
``python scripts/fetch_terrain_data.py`` انجام می‌شود.

هشدار صداقت
-----------
این مدل ارتفاع فقط برای **نمایش** است. مدل مسیریابی این پروژه زمین را
مانع/عوارض در نظر نمی‌گیرد (هیچ بررسی برخورد با زمین یا حداقل فاصله ایمن وجود
ندارد)، پس مسیر محاسبه‌شده از روی کوه و دره بدون تفاوت عبور می‌کند. این نکته
در متن صحنه هم اعلام می‌شود.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from viz.wind_field import CORRIDOR_BBOX, lonlat_to_km

__all__ = [
    "TERRAIN_CELL_KM",
    "TERRAIN_CSV_PATH",
    "TerrainModel",
    "terrain_grid",
    "load_terrain",
    "write_terrain_csv",
]

# اندازهٔ سلول شبکهٔ نمایش زمین (کیلومتر).
#
# سلول‌ها باید *مربع بر حسب کیلومتر* باشند، نه یک تعداد نقطهٔ ثابت. شبکهٔ قبلی
# (۱۹×۳۷ نقطه روی کریدور ۴۴×۲۱۶ کیلومتری) سلول‌های ۲.۵×۶ کیلومتری می‌ساخت،
# یعنی رزولوشن در جهت شرق–غرب ۲.۴ برابر کم‌تر بود. صحنه یک کیلومتر را در شرق و
# شمال با طول یکسان می‌کشد، پس آن شبکه رشته‌کوه‌ها و دره‌ها را به‌صورت نوارهای
# پهن و محوشده در جهت شرق–غرب نشان می‌داد — ارتفاع‌ها درست بودند ولی *شکل*
# زمین غلط دیده می‌شد.
TERRAIN_CELL_KM = 2.5

# مسیر پیش‌فرض فایل ارتفاع زمین (مرجع ساخت صحنه). مسیر نسبت به ریشه پروژه
# حساب می‌شود تا صحنه از هر پوشه‌ای قابل ساخت باشد.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TERRAIN_CSV_PATH = PROJECT_ROOT / "data" / "khorasan_terrain.csv"

# پیشوند خط توضیح در فایل CSV (مرجع منبع داده).
TERRAIN_COMMENT_PREFIX = "# "


@dataclass(frozen=True)
class TerrainModel:
    """ارتفاع زمین روی یک شبکه منظم از مختصات.

    پارامترها
    ----------
    lats, lons : ndarray
        محورهای شبکه (درجه، صعودی).
    elevation_m : ndarray, شکل (n_lat, n_lon)
        ارتفاع زمین از سطح دریا (متر) روی شبکه.
    source : str
        توضیح منبع داده (یا خالی اگر نامعلوم).
    """

    lats: np.ndarray
    lons: np.ndarray
    elevation_m: np.ndarray
    source: str = ""

    @property
    def min_elevation_m(self) -> float:
        """کمترین ارتفاع شبکه (متر)."""
        return float(np.min(self.elevation_m))

    @property
    def max_elevation_m(self) -> float:
        """بیشترین ارتفاع شبکه (متر)."""
        return float(np.max(self.elevation_m))

    @property
    def relief_m(self) -> float:
        """دامنه ارتفاع شبکه (متر) — صفر یعنی زمین تخت است."""
        return self.max_elevation_m - self.min_elevation_m

    @cached_property
    def _interpolator(self) -> RegularGridInterpolator:
        """درون‌یاب ``RegularGridInterpolator`` (فقط برای مقایسه/کارهای برداری).

        مسیر داغ محاسبات از این کلاس استفاده نمی‌کند: ``_bilinear`` همان
        میان‌یابی دوخطی را با چهار مقایسهٔ ایندکس انجام می‌دهد. هر فراخوانی
        ``RegularGridInterpolator`` حتی با یک نقطه، ده‌ها کیلوبایت آرایهٔ موقت
        می‌سازد؛ در انتگرال بادسواری و در آزمون زمین هر یال، این تابع صدها هزار
        بار صدا زده می‌شود و همان تفاوت چند دقیقه است.
        """
        return RegularGridInterpolator(
            (self.lats, self.lons),
            self.elevation_m,
            bounds_error=False,
            fill_value=None,
        )

    @cached_property
    def _axis_lists(self) -> tuple[list[float], list[float]]:
        """محورهای شبکه به‌صورت لیست پایتون، برای مسیر سریع تک‌نقطه‌ای."""
        return (
            [float(value) for value in self.lats],
            [float(value) for value in self.lons],
        )

    def _bilinear_scalar(self, lat: float, lon: float) -> float:
        """میان‌یابی دوخطی **تک‌نقطه‌ای** با حساب پایتون (بدون سربارهٔ numpy).

        این تابع در داغ‌ترین مسیر برنامه است: هر گام انتگرال بادسواری و هر
        نمونهٔ زمین روی یال‌های گراف از این‌جا می‌گذرد (صدها هزار فراخوانی با
        یک نقطه). با numpy، هر فراخوانی برای همان یک نقطه چندین آرایهٔ موقت
        می‌سازد و هزینهٔ ساخت از خود میان‌یابی بیشتر می‌شود.
        """
        lats, lons = self._axis_lists
        i = self._cell_index(lats, lat)
        j = self._cell_index(lons, lon)
        wy = (lat - lats[i]) / (lats[i + 1] - lats[i])
        wx = (lon - lons[j]) / (lons[j + 1] - lons[j])
        elevation = self.elevation_m
        top = elevation[i, j] * (1.0 - wx) + elevation[i, j + 1] * wx
        bottom = elevation[i + 1, j] * (1.0 - wx) + elevation[i + 1, j + 1] * wx
        return float(top * (1.0 - wy) + bottom * wy)

    @staticmethod
    def _cell_index(axis: list[float], value: float) -> int:
        """اندیس سلول شبکه برای یک مقدار محور (محدود به بازهٔ سلول‌های موجود)."""
        return min(max(bisect_right(axis, value) - 1, 0), len(axis) - 2)

    def _bilinear(self, lat_arr: np.ndarray, lon_arr: np.ndarray) -> np.ndarray:
        """میان‌یابی دوخطی روی سلول شبکه، با برون‌یابی خطی در همان سلول لبه.

        بیرون از شبکه، همان رفتار ``RegularGridInterpolator`` با
        ``fill_value=None`` را دارد (خطی از داخل سلول لبه ادامه می‌دهد)، ولی با
        ایندکس‌گذاری مستقیم روی آرایه و بدون ساخت هیچ شیء میان‌یابی‌کننده.
        """
        lats = self.lats
        lons = self.lons
        i = np.clip(np.searchsorted(lats, lat_arr) - 1, 0, lats.size - 2)
        j = np.clip(np.searchsorted(lons, lon_arr) - 1, 0, lons.size - 2)
        wy = (lat_arr - lats[i]) / (lats[i + 1] - lats[i])
        wx = (lon_arr - lons[j]) / (lons[j + 1] - lons[j])
        elevation = self.elevation_m
        return (
            elevation[i, j] * (1.0 - wx) * (1.0 - wy)
            + elevation[i, j + 1] * wx * (1.0 - wy)
            + elevation[i + 1, j] * (1.0 - wx) * wy
            + elevation[i + 1, j + 1] * wx * wy
        )

    def elevation_at(
        self,
        lat: np.ndarray | float,
        lon: np.ndarray | float,
    ) -> np.ndarray:
        """ارتفاع زمین در مختصات دلخواه (میان‌یابی دوخطی، برون‌یابی لبه‌ای).

        برای نقاط بیرون شبکه، ``RegularGridInterpolator`` مقدار ``None`` را با
        نزدیک‌ترین سلول پر می‌کند؛ یعنی ارتفاع لبه‌ای برگردانده می‌شود، نه صفر.

        درون‌یاب **یک‌بار** ساخته و ذخیره می‌شود. پیش‌تر در هر فراخوانی از نو
        ساخته می‌شد و ساختن آن (بررسی محورها، مرتب‌سازی، ساخت درخت) از خود
        میان‌یابی گران‌تر بود؛ حالا که مدل زمین در هر گام انتگرال مسیر و در هر
        یال گراف صدا زده می‌شود، این تفاوت بین «چند ثانیه» و «چند دقیقه» است.
        """
        if np.ndim(lat) == 0 and np.ndim(lon) == 0:
            return self._bilinear_scalar(float(lat), float(lon))
        lat_arr = np.atleast_1d(np.asarray(lat, dtype=float))
        lon_arr = np.atleast_1d(np.asarray(lon, dtype=float))
        shape = np.broadcast_shapes(lat_arr.shape, lon_arr.shape)
        values = np.asarray(
            self._bilinear(lat_arr.ravel(), lon_arr.ravel()), dtype=float
        )
        # شکل ورودی حفظ می‌شود: برای شبکه دوبعدی (n_lat, n_lon) نتیجه هم
        # دوبعدی برمی‌گردد، نه تخت. ``column_stack`` روی ورودی دوبعدی ماتریس
        # (n_lat, ۲*n_lon) می‌سازد که همان اشتباه قبلی بود، پس این‌جا قبل از
        # ساخت نقاط، ورودی تخت می‌شود.
        return values.reshape(shape)


def terrain_grid(
    bbox: dict[str, float] | None = None,
    cell_km: float = TERRAIN_CELL_KM,
) -> tuple[np.ndarray, np.ndarray]:
    """شبکه منظم ارتفاع زمین با سلول‌های مربع بر حسب کیلومتر.

    تعداد نقاط از *گسترهٔ کیلومتری* کادر حساب می‌شود (نه از یک عدد ثابت)، تا
    گام شمالی–جنوبی و شرقی–غربی هم‌اندازه بماند.
    """
    if cell_km <= 0.0:
        raise ValueError("cell_km must be positive.")

    box = CORRIDOR_BBOX if bbox is None else bbox
    origin = (box["lat_min"], box["lon_min"])
    x_min, y_min = (
        float(value)
        for value in lonlat_to_km(box["lat_min"], box["lon_min"], *origin)
    )
    x_max, y_max = (
        float(value)
        for value in lonlat_to_km(box["lat_max"], box["lon_max"], *origin)
    )
    height_km = abs(y_max - y_min)
    width_km = abs(x_max - x_min)
    n_lat = max(int(round(height_km / cell_km)) + 1, 2)
    n_lon = max(int(round(width_km / cell_km)) + 1, 2)

    lats = np.linspace(box["lat_min"], box["lat_max"], n_lat)
    lons = np.linspace(box["lon_min"], box["lon_max"], n_lon)
    return lats, lons


def write_terrain_csv(
    path: str | Path,
    terrain: TerrainModel,
) -> Path:
    """مدل ارتفاع را در قالب CSV طولانی (``lat,lon,elevation_m``) ذخیره می‌کند."""
    lon_mesh, lat_mesh = np.meshgrid(terrain.lons, terrain.lats)
    frame = pd.DataFrame(
        {
            "lat": lat_mesh.ravel(),
            "lon": lon_mesh.ravel(),
            "elevation_m": terrain.elevation_m.ravel(),
        }
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        handle.write(f"{TERRAIN_COMMENT_PREFIX}source: {terrain.source}\n")
        handle.write(
            f"{TERRAIN_COMMENT_PREFIX}grid: {len(terrain.lats)}x{len(terrain.lons)}\n"
        )
        frame.to_csv(handle, index=False)
    return target


def load_terrain(path: str | Path) -> TerrainModel:
    """مدل ارتفاع را از فایل CSV می‌خواند (خطوط ``#`` به‌عنوان منبع/فراداده).

    استثناها
    --------
    FileNotFoundError
        اگر فایل موجود نباشد (راه‌حل: ``scripts/fetch_terrain_data.py``).
    ValueError
        اگر ستون‌های لازم موجود نباشند یا شبکه کامل نباشد.
    """
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(
            f"Terrain file not found: {source_path}. "
            "Run `python scripts/fetch_terrain_data.py` to fetch it."
        )

    source = ""
    with source_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith(TERRAIN_COMMENT_PREFIX):
                break
            if "source:" in line:
                source = line.split("source:", 1)[1].strip()

    frame = pd.read_csv(source_path, comment="#")
    required = {"lat", "lon", "elevation_m"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Terrain file is missing columns: {sorted(missing)}")

    lats = np.sort(frame["lat"].unique())
    lons = np.sort(frame["lon"].unique())
    if len(lats) * len(lons) != len(frame):
        raise ValueError(
            "Terrain file is not a complete regular grid "
            f"({len(lats)}x{len(lons)} axes vs {len(frame)} rows)."
        )

    elevation = (
        frame.pivot(index="lat", columns="lon", values="elevation_m")
        .sort_index()
        .sort_index(axis=1)
        .to_numpy(dtype=float)
    )
    return TerrainModel(lats=lats, lons=lons, elevation_m=elevation, source=source)
