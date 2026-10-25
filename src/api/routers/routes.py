"""
Routes Router — POST /routes, GET /routes/{routeId}, GET /routes/jobs/{jobId}, GET /routes/jobs/{jobId}/compare-layers.

Implements the routing endpoints per api/openapi.yaml.
"""
import math
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pathfinding.cost import CostModelConfig

router = APIRouter(prefix="/routes", tags=["routing"])


# Global pathfinding state
_multi_graph = None
_wind_fields = None
# مدل زمینِ گراف — مسیریابی و بادسواری هر دو باید زمین را از یک منبع بخوانند.
_terrain_model = None
# سطوح پرواز و کف فاصلهٔ ایمنی که گراف با آن‌ها ساخته شده؛ نگه‌داشتنشان این‌جا
# باعث می‌شود لایه‌های درخواستی کاربر و کف زمین همیشه با خودِ گراف هم‌خوان باشند.
_flight_levels_msl: tuple[float, ...] = ()
_min_clearance_m = 0.0
# مواد اولیهٔ لایهٔ تازه: ایستگاه‌ها و شبکهٔ گراف و ارتفاع زمینِ همان شبکه.
# با نمایهٔ پیوستهٔ باد می‌شود سطح پرواز در *هر* ارتفاعی ساخت — نه فقط
# چهار سطح استاندارد؛ پس چک‌پوینت می‌تواند واردِ دل لایه‌ها قرار بگیرد.
_stations_df = None
_lattice_lats = None
_lattice_lons = None
_lattice_ground = None
# کش غلافِ محدودِ لایه‌های سر-الاکلپی (کلید = ارتفاع گردشده) — ساخت گراف یک
# لایه کوتاه است اما بی‌جهت تکرارش گران می‌شود؛ آستانه را می‌چرخانیم.
_adhoc_field_cache: dict[float, object] = {}
_ADHOC_CACHE_MAX = 24
_pathfinding_initialized = False
_BAND_EPS = 1e-6


# ---- Request/Response Models (mirroring api/openapi.yaml schemas) ----

class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class Coordinate3D(Coordinate):
    alt: float = Field(..., description="Altitude in meters MSL")


class Checkpoint(Coordinate):
    order: int | None = None
    # ارتفاع اجباری (متر MSL) — از کشیدن محور «ارتفاع» گیمبال در صحنهٔ سه‌بعدی.
    # قطعه‌ای که به این چک‌پوینت می‌رسد دقیقاً در این سطح کروز می‌کند.
    alt: float | None = Field(None, gt=0)


class AvoidZone(BaseModel):
    type: Literal["circle"] = "circle"
    center: Coordinate
    radius_km: float = Field(..., gt=0)


class RouteConstraints(BaseModel):
    max_wind_speed_mps: float | None = Field(None, gt=0)
    altitude_range_m: list[float] | None = Field(None, min_length=2, max_length=2)
    avoid_zones: list[AvoidZone] | None = None
    criterion: Literal["time", "energy", "balanced", "distance", "safety"] | None = "balanced"
    weights: dict | None = Field(None, description="{time: float, energy: float}")
    # Vessel/aircraft configuration for cost model
    vessel: dict | None = Field(None, description="{type: string, airspeed_mps: float, induced_drag_coeff: float, headwind_penalty_coeff: float}")


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    checkpoints: list[Checkpoint] | None = None
    layer_mode: Literal["auto", "manual"] | None = "auto"
    altitude_m: float | None = Field(None, gt=0)
    algorithm: Literal["a_star", "dijkstra", "smooth", "wind_riding"] | None = "a_star"
    constraints: RouteConstraints | None = None
    async_mode: bool | None = Field(False, alias="async")


class RouteResult(BaseModel):
    route_id: str
    path: list[Coordinate]
    path_3d: list[Coordinate3D] | None = None  # [lat, lon, altitude_msl] for 3D rendering
    layer_altitude_m: float
    algorithm: Literal["a_star", "dijkstra", "smooth", "wind_riding"]
    criterion: Literal["time", "energy", "balanced", "distance", "safety"]
    total_distance_km: float
    estimated_time_hours: float
    total_cost: float
    created_at: str
    is_saved: bool = False
    # Additional metrics from WindRouter
    total_energy_index: float | None = None
    tailwind_leg_fraction: float | None = None
    heading_changes: int | None = None
    total_climb_m: float | None = None
    total_descent_m: float | None = None
    climb_legs: int | None = None
    altitudes_used: list[float] | None = None


class RouteJobAccepted(BaseModel):
    job_id: str
    status: Literal["pending"] = "pending"
    estimated_duration_seconds: int | None = None


class RouteJobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: int | None = Field(None, ge=0, le=100)
    result: RouteResult | None = None
    error: str | None = None


class LayerComparisonRow(BaseModel):
    layer_altitude_m: float
    estimated_time_hours: float
    total_distance_km: float
    total_cost: float
    tailwind_leg_fraction: float
    heading_changes: int


class LayerComparison(BaseModel):
    layers: list[LayerComparisonRow]
    best_layer_altitude_m: float


# ---- In-memory job store (replace with Redis/DB in production) ----
_jobs: dict[str, RouteJobStatus] = {}


# ---- Helper: call pathfinding core ----
# We'll initialize this lazily on first use to avoid import issues during startup


def _init_pathfinding() -> None:
    """Initialize the WindRouter with real data from Khorasan stations."""
    global _pathfinding_initialized, _multi_graph, _terrain_model, _wind_fields
    global _flight_levels_msl, _min_clearance_m
    global _stations_df, _lattice_lats, _lattice_lons, _lattice_ground

    if _pathfinding_initialized:
        return

    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[3]  # /opt/shared/projects/roshd
    sys.path.insert(0, str(ROOT / "src"))

    import numpy as np
    import pandas as pd

    from viz.terrain import load_terrain
    from viz.wind_field import (
        CORRIDOR_BBOX,
        FLIGHT_LEVELS_MSL,
        GRAPH_LAT_STEP,
        GRAPH_LON_STEP,
        MIN_TERRAIN_CLEARANCE_M,
        build_level_fields,
        build_multi_layer_graph,
        corridor_lattice,
        load_station_winds,
        select_scene_hour,
    )

    # Load wind data
    DATA_PATH = ROOT / "data" / "khorasan_wind_qc_cleaned.csv"
    hour = select_scene_hour(pd.read_csv(DATA_PATH))
    station_winds = load_station_winds(DATA_PATH, timestamp=hour)

    # Build graph lattice
    lats, lons = corridor_lattice(
        station_winds,
        lat_step=GRAPH_LAT_STEP,
        lon_step=GRAPH_LON_STEP,
        bbox=CORRIDOR_BBOX
    )

    # Load terrain model and interpolate onto the same lattice
    terrain_model = load_terrain(ROOT / "data" / "khorasan_terrain.csv")
    lon_mesh, lat_mesh = np.meshgrid(lons, lats)
    ground = terrain_model.elevation_at(lat_mesh.ravel(), lon_mesh.ravel()).reshape(lat_mesh.shape)

    # Build level fields (wind fields at each flight level)
    fields = build_level_fields(
        stations=station_winds,
        terrain_elevation=ground,
        levels=FLIGHT_LEVELS_MSL,
        lat_step=GRAPH_LAT_STEP,
        lon_step=GRAPH_LON_STEP,
        bbox=CORRIDOR_BBOX,
        terrain_lats=terrain_model.lats,
        terrain_lons=terrain_model.lons,
    )

    # Build multi-layer graph
    # **فیلتر زمین روی یال‌ها — همان کاری که صحنهٔ مرجع می‌کند.** سازندهٔ گراف
    # فقط *گره‌های* بی‌فاصله را حذف می‌کند؛ یالی که از روی یک قله می‌گذرد ولی دو
    # سرش پایین است بی‌فیلتر می‌ماند. نتیجه: مسیر باند از روی آن قله رد می‌شد و
    # رمپ ایمنی برای نگه‌داشتن فاصلهٔ ۳۰۰ متری، هواپیما را *بالاتر از سقف باند*
    # می‌برد (اندازه‌گیری: باند [۱۵۰۰,۲۲۰۰] تا ۲۷۳۰ متر بالا می‌رفت). صحنهٔ مرجع
    # (``viz/scene3d.py``) از ابتدا ``edge_terrain_sampler`` را می‌دهد؛ رابط API
    # نمی‌داد و همین تفاوت، علت «احترام‌نشدن باند» بود. حالا هر دو یک گراف
    # می‌سازند: باند یا مسیر از کنارِ کوه پیدا می‌کند یا صادقانه می‌گوید نمی‌شود.
    _multi_graph = build_multi_layer_graph(
        fields=fields,
        config=None,
        criterion="balanced",  # will be overridden per request
        max_edge_distance_km=20.0,
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
        edge_terrain_sampler=terrain_model.elevation_at,
    )

    # Store fields globally for wind_riding algorithm
    global _wind_fields
    _wind_fields = fields

    # مواد لایه‌های سر-الاکلپی: ایستگاه‌ها، شبکهٔ گراف و زمینِ همان شبکه.
    _stations_df = station_winds
    _lattice_lats = lats
    _lattice_lons = lons
    _lattice_ground = ground

    # نگه‌داشتن مدل زمین و پارامترهای گراف برای تزریق به مسیریاب. پیش‌تر این‌جا
    # یک ``IDWInterpolator`` ساخته می‌شد که هیچ‌وقت fit نمی‌شد (کد مرده)؛ زمین
    # واقعی همان ``terrain_model`` است که چند خط بالاتر بارگذاری شده.
    _terrain_model = terrain_model
    _flight_levels_msl = tuple(float(level) for level in FLIGHT_LEVELS_MSL)
    _min_clearance_m = float(MIN_TERRAIN_CLEARANCE_M)

    _pathfinding_initialized = True


def _ground_elevation_at(lat: float, lon: float) -> float:
    """ارتفاع زمین (متر MSL) در یک مختصات — همان مدل زمینی که گراف با آن ساخته شد.

    مسیریابی گراف (کف زمین و رمپ‌های عمودی) و بادسواری (شبیه‌سازی و فرود) هر دو
    از این تابع زمین را می‌خوانند، پس «فاصله از زمین» در همه‌جا یک معنا دارد.
    """
    _init_pathfinding()
    if _terrain_model is None:
        return 0.0
    return float(_terrain_model.elevation_at(lat, lon))


def _level_field_for(altitude_m: float):
    """میدان باد در ارتفاع دلخواه MSL — با همان مدلِ نمایهٔ پیوستهٔ باد.

    سطوح ۱۵۰۰/۲۲۰۰/۲۹۰۰/۳۶۰۰ «استاندارد» گراف‌اند، ولی نمایهٔ باد
    (``profile_at``) پیوسته است: باد هر گره در ارتفاع واقعی خودش بالای زمین
    نمونه‌برداری می‌شود. پس برای چک‌پوینتی که کاربر آن را وسطِ دل لایه‌ها
    گذاشته (مثلاً ۱۸۰۰ متر)، با همان مدلِ بقیهٔ لایه‌ها یک لایهٔ واقعی
    می‌سازیم — نه نزدیک‌ترین سطح و نه درون‌یابی سادهٔ بین دو لایه.
    کش بر اساس ارتفاع گردشده است و اندازه‌اش چرخان محدود می‌ماند.
    """
    from viz.wind_field import interpolate_level_field

    key = float(round(altitude_m, 1))
    cached = _adhoc_field_cache.get(key)
    if cached is not None:
        return cached
    if len(_adhoc_field_cache) >= _ADHOC_CACHE_MAX:
        _adhoc_field_cache.pop(next(iter(_adhoc_field_cache)))
    field = interpolate_level_field(
        _stations_df, key, _lattice_lats, _lattice_lons, _lattice_ground
    )
    _adhoc_field_cache[key] = field
    return field


def _is_standard_level(altitude_m: float) -> bool:
    """آیا این ارتفاع یکی از سطوح استاندارد گراف است (خطای ممیز tolerated)?"""
    return any(
        abs(level - altitude_m) <= _BAND_EPS for level in _flight_levels_msl
    )


def _sampler_for_level(altitude_m: float):
    """نمونه‌بردار باد «(lat, lon) → (سرعت، جهت)» در ارتفاع دلخواه MSL.

    همان قرارداد ``_layer_samplers`` صحنه را رعایت می‌کند تا بادسواری با
    بادِ ارتفاع قفل واقعاً نمونه‌برداری کند (نه بادِ پله‌ایِ لایهٔ پایین‌تر).
    """
    from viz.scene3d import _layer_samplers

    samplers = _layer_samplers([_level_field_for(altitude_m)])
    return samplers[0][1]


def _check_lock_within_band(locked_alt: float, band_levels) -> None:
    """تعارض قفل چک‌پوینت با باند ارتفاعی انتخابی را صریحاً رد می‌کند.

    باند یعنی «فقط در همین سطوح پرواز کن». اگر قفل چک‌پوینت بیرون باند
    باشد و مسیر بی‌سروصدا در سطح دیگری (نزدیک‌ترین باند) بگذرد، نتیجه
    از خواستهٔ کاربر خیلی دور می‌شود؛ به‌جای آن خطای گویا می‌دهیم تا
    کاربر یکی را عوض کند: یا باند را گشادتر، یا ارتفاع چک‌پوینت را
    هم‌تراز باند.
    """
    if band_levels is None:
        return
    inside = any(
        abs(level - locked_alt) <= _BAND_EPS for level in band_levels
    )
    if not inside:
        band_text = "، ".join(f"{level:.0f} متر" for level in band_levels)
        raise ValueError(
            f"ارتفاع قفل‌شدهٔ چک‌پوینت ({locked_alt:.0f} متر) بیرون از باند "
            f"ارتفاعی انتخابی ({band_text}) است؛ باند را گشادتر کنید یا "
            "ارتفاع چک‌پوینت را هم‌تراز باند کنید."
        )


def _router_for_locked_level(altitude_m: float, criterion: str, algorithm: str, aircraft_config=None):
    """روتری که مسیر را **دقیقاً در ارتفاع قفل** می‌سازد.

    برای سطح استاندارد همین گراف اصلی کار می‌کند؛ برای ارتفاع میانیِ دل
    لایه‌ها یک گراف تک‌لایهٔ واقعی با همان پارامترهای گراف اصلی (کف ایمنی،
    پیمانه‌گیری زمینِ یال‌ها، طول بیشینهٔ یال) ساخته می‌شود تا «عبور در
    ۱۸۰۰ متر» یعنی همان چیزی که کاربر خواسته، نه کنارکشی به نزدیک‌ترین سطح.
    """
    from viz.wind_field import build_multi_layer_graph

    if _is_standard_level(altitude_m):
        return _get_router(criterion, algorithm, aircraft_config=aircraft_config)

    field = _level_field_for(altitude_m)
    single = build_multi_layer_graph(
        fields=[field],
        config=None,
        criterion="balanced",
        max_edge_distance_km=20.0,
        min_clearance_m=_min_clearance_m,
        edge_terrain_sampler=_terrain_model.elevation_at,
    )
    return _get_router(
        criterion,
        algorithm,
        multi_graph=single,
        aircraft_config=aircraft_config,
    )


def _resolve_altitude_band(request: RouteRequest) -> list[float] | None:
    """بازهٔ ارتفاع درخواست را به فهرست **سطوح پرواز واقعی گراف** ترجمه می‌کند.

    رابط کاربری به‌جای یک سطح، یک *بازه* می‌فرستد (``altitude_range_m``): مثلاً
    نیمه‌بالا ``[1500, 2200]`` یا سطحی ``[0, 1500]``. مسیریاب با سطح پرواز کار
    می‌کند، پس بازه روی ``FLIGHT_LEVELS_MSL`` نگاشت می‌شود. بازگشت ``None``
    یعنی «همهٔ لایه‌ها» — همان حالت آزادی چندلایه.
    """
    constraints = request.constraints
    if constraints is None or constraints.altitude_range_m is None:
        return None
    _init_pathfinding()
    low, high = sorted(float(value) for value in constraints.altitude_range_m)
    levels = [
        level
        for level in _flight_levels_msl
        if low - _BAND_EPS <= level <= high + _BAND_EPS
    ]
    if not levels:
        raise ValueError(
            f"داخل بازهٔ ارتفاعی [{low}, {high}] هیچ سطح پروازی نیست؛ "
            f"سطوح موجود: {list(_flight_levels_msl)}."
        )
    return levels


def _route_on_band(router, origin, destination, band_levels):
    """مسیریابی گراف با محدودیت باند؛ خطای گویا وقتی مسیری در باند نیست.

    اگر باندی انتخاب نشده باشد (``None``)، همان مسیریابی آزاد چندلایه است و خطای
    ``WindRouter`` دست‌نخورده می‌ماند. در حالت باند، نبودِ مسیر یعنی «در این
    ارتفاع نمی‌شود از این کوه/زمین رد شد» — پیامی که کاربر بفهمد، نه یک خطای خشک.
    """
    try:
        return router.find_optimal_path(origin, destination, layers=band_levels)
    except ValueError as exc:
        if band_levels is None:
            raise
        raise ValueError(
            f"در باند ارتفاعی {band_levels} متری مسیر پروازپذیری پیدا نشد "
            f"(زمین یا رشته‌کوه مانع است)؛ باند ارتفاعی بالاتر را امتحان کنید."
        ) from exc


def _get_router(criterion: str, algorithm: str, multi_graph=None, aircraft_config=None):
    """Create a WindRouter with the given criterion and algorithm.

    ``multi_graph``/``aircraft_config`` پیش‌فرض به گراف اصلی و پیکان‌های
    خط‌مشی می‌خورند؛ لایهٔ سر-الاکلپی قفل چک‌پوینت همین سازنده را با گراف
    تک‌لایهٔ خودش و همان پیکان‌های درخواست صدا می‌زند — تا «مسیر گراف» و
    «مسیر قفل» با یک‌دست مدل هزینه ساخته شوند.
    """
    from pathfinding.cost import CostModelConfig
    from pathfinding.routing import WindRouter

    global _multi_graph

    # Map API algorithm names to backend algorithm names
    algorithm_map = {
        "a_star": "astar",
        "dijkstra": "dijkstra",
        "smooth": "smooth",
        "wind_riding": "wind_riding",
    }
    backend_algorithm = algorithm_map.get(algorithm, "astar")

    # پیکان‌های خط‌مشی — مگر درخواست پیکان خودش را داده باشد (کشتی/پهپاد).
    if aircraft_config is None:
        aircraft_config = CostModelConfig(
            airspeed_mps=20.0,
            induced_drag_coeff=0.3,
            headwind_penalty_coeff=0.25,
        )

    # Wind riding is planned outside ``WindRouter``; the router is still built
    # (with graph A* semantics, which is the fallback when no wind-riding plan
    # fits the selected `band`) so a band-locked request still gets a route.
    if backend_algorithm == "wind_riding":
        backend_algorithm = "astar"

    return WindRouter(
        multi_graph=multi_graph if multi_graph is not None else _multi_graph,
        config=aircraft_config,
        criterion=criterion,
        algorithm=backend_algorithm,
        allow_layer_changes=True,
        # **زمین.** بدون این دو پارامتر، روتر هیچ مدل زمینی نداشت: کف زمین و
        # رمپ‌های عمودی زمین را «صفر» فرض می‌کردند، مسیر «فاصله از زمین» را
        # نمی‌سنجید، و ارتفاع گره زمین صفر (سطح دریا) گزارش می‌شد — همان چیزی
        # که در صحنه به‌شکل شیرجه تا زمین و «چسبیدن به زمین» دیده می‌شد.
        ground_elevation_at=_ground_elevation_at,
        min_clearance_m=_min_clearance_m,
    )


def compute_route_sync(request: RouteRequest) -> RouteResult:
    """
    Call the actual pathfinding engine using WindRouter.
    Supports multi-segment routing through checkpoints.
    """
    _init_pathfinding()

    # Map API request to WindRouter parameters
    criterion = request.constraints.criterion if request.constraints else "balanced"
    algorithm = request.algorithm or "a_star"
    altitude = request.altitude_m
    # بازهٔ ارتفاع انتخابی کاربر → سطوح پرواز؛ ``None`` یعنی «همهٔ لایه‌ها».
    band_levels = _resolve_altitude_band(request)

    # **صداقت قیدها.** قیدهایی که موتور مسیریابی هنوز اعمال نمی‌کند، به‌جای
    # «نادیده‌گرفتن خاموش» صریحاً رد می‌شوند: اگر بک‌اند قیدی را بپذیرد و
    # نادیده بگیرد، نتیجهٔ مسیر با آنچه کاربر خواسته فرق می‌کند و کاربر هرگز
    # نمی‌فهمد قیدش بی‌اثر بوده است (پیش‌تر ``max_wind_speed_mps`` تماماً
    # بی‌اثر ارسال می‌شد). رابط کاربری تا پیاده‌شدن موتور، این قیدها را
    # نمی‌فرستد؛ ردکردن صریح فقط مصرف‌کنندهٔ مستقیم API را هدایت می‌کند.
    if request.constraints is not None:
        if request.constraints.max_wind_speed_mps is not None:
            raise ValueError(
                "قید «حداکثر سرعت باد» هنوز در موتور مسیریابی اعمال نمی‌شود؛ "
                "لطفاً درخواست را بدون این قید بفرستید."
            )
        if request.constraints.avoid_zones:
            raise ValueError(
                "مناطق ممنوعه هنوز در موتور مسیریابی پشتیبانی نمی‌شود؛ "
                "لطفاً درخواست را بدون ممنوعه بفرستید."
            )

    # Map API algorithm names to backend algorithm names
    algorithm_map = {
        "a_star": "astar",
        "dijkstra": "dijkstra",
        "smooth": "smooth",
        "wind_riding": "wind_riding",
    }
    backend_algorithm = algorithm_map.get(algorithm, "astar")

    # Use vessel config from request if provided, otherwise default
    if request.constraints and request.constraints.vessel:
        v = request.constraints.vessel
        aircraft_config = CostModelConfig(
            airspeed_mps=v.get("airspeed_mps", 20.0),
            induced_drag_coeff=v.get("induced_drag_coeff", 0.3),
            headwind_penalty_coeff=v.get("headwind_penalty_coeff", 0.25),
        )
    else:
        aircraft_config = CostModelConfig(
            airspeed_mps=20.0,
            induced_drag_coeff=0.3,
            headwind_penalty_coeff=0.25,
        )

    # Build list of all waypoints: origin -> checkpoints -> destination
    waypoints = [request.origin] + (request.checkpoints or []) + [request.destination]

    if len(waypoints) < 2:
        raise ValueError("At least origin and destination are required")

    router = _get_router(criterion, algorithm)

    # Route between consecutive waypoints and concatenate results
    all_path_coords = []
    all_path_3d = []
    total_distance_km = 0.0
    total_time_hours = 0.0
    total_cost = 0.0
    all_altitudes_used = []
    layer_altitude = None
    last_result = None

    for i in range(len(waypoints) - 1):
        origin = (waypoints[i].lat, waypoints[i].lon)
        destination = (waypoints[i + 1].lat, waypoints[i + 1].lon)

        # قفل ارتفاع چک‌پوینت (کشیدن محور «ارتفاع» گیمبال در ۳بعدی): نقطه‌های
        # میانی (چک‌پوینت‌ها) می‌توانند ارتفاعِ عبور داشته باشند؛
        # مبدأ/مقصد همیشه روی زمین‌اند و قفل ندارند. مبدأ/مقصدِ هر قطعه از
        # چک‌پوینت‌ها می‌آید، پس این دو قفل صرفاً روی مرزهای چک‌پوینتی
        # غیر از None می‌شوند.
        start_lock = getattr(waypoints[i], "alt", None)
        end_lock = getattr(waypoints[i + 1], "alt", None)
        locked_alt = end_lock if end_lock is not None else start_lock
        if (
            start_lock is not None
            and end_lock is not None
            and abs(start_lock - end_lock) > 1e-6
        ):
            raise ValueError(
                f"ارتفاع قفل‌شدهٔ چک‌پوینت‌های دو سر این قطعه یکی نیست "
                f"({start_lock:.0f} و {end_lock:.0f} متر)؛ تغییر ارتفاع در میانهٔ "
                "یک قطعه هنوز پشتیبانی نمی‌شود — ارتفاع هر دو چک‌پوینت را هم‌سطح کنید."
            )

        # Skip if waypoints are too close (same H3 cell)
        dist_km = math.hypot(
            (origin[0] - destination[0]) * 111.0,
            (origin[1] - destination[1]) * 111.0 * math.cos(math.radians(origin[0]))
        )
        if dist_km < 1.0:  # less than 1km apart
            continue

        try:
            # Wind riding algorithm - uses continuous wind fields, not graph
            if backend_algorithm == "wind_riding":
                from dataclasses import replace as dc_replace

                from pathfinding.effort import MotorEffortConfig
                from pathfinding.graph import VerticalCostConfig
                from pathfinding.wind_riding import (
                    WindRidingConfig,
                    plan_wind_riding_route,
                    wind_riding_route_result,
                )
                from viz.scene3d import _layer_samplers

                # Build layer samplers from stored fields
                global _wind_fields
                if _wind_fields is None:
                    raise ValueError("Wind fields not initialized")
                fields = _wind_fields
                all_layers = [
                    (level, sampler) for level, sampler in _layer_samplers(fields)
                ]
                # باند انتخابی کاربر روی بادسواری هم اعمال می‌شود: «ارتفاع
                # انتخابی» یعنی «فقط در همین سطوح». حالت «همه» همهٔ سطوح را
                # می‌دهد و هواپیما آزاد است.
                layers = (
                    all_layers
                    if band_levels is None
                    else [
                        item for item in all_layers if item[0] in set(band_levels)
                    ]
                )

                # Create planner config (criterion is used internally for optimization)
                planner_config = WindRidingConfig()
                # در حالت باند، سقف باند به برنامه‌ریز می‌رود: صعود برای رد شدن از
                # کوه فقط تا همین سقف مجاز است؛ هر برنامه‌ای که از آن بالاتر برود
                # «غیرقابل‌پرواز» شمرده و رد می‌شود. حالت «همه» بدون سقف است.
                if band_levels is not None:
                    planner_config = dc_replace(
                        planner_config, max_altitude_msl_m=max(band_levels)
                    )
                # «سریع‌ترین» (criterion=time) روی استراتژی R7 صحنه سوار است:
                # بادسواری با دالان تنگ — کمترین انحراف از خط مستقیم. همان روش و
                # سیاست ``routing_scene`` (WIND_RIDING_VARIANT_SPECS → R7 با
                # دالان ۰.۲۰): به‌جای جست‌وجوی چنددالانی، یک دالان صریح.
                if criterion == "time":
                    from viz.scene3d import WIND_RIDING_VARIANT_SPECS

                    r7_spec = next(
                        (spec for spec in WIND_RIDING_VARIANT_SPECS if spec.key == "R7"),
                        None,
                    )
                    if r7_spec is not None and r7_spec.wind_corridor_fraction is not None:
                        planner_config = dc_replace(
                            planner_config,
                            corridor_override=r7_spec.wind_corridor_fraction,
                        )

                # چک‌پوینت با ارتفاع اجباری (کشیدن محور «ارتفاع» گیمبال).
                # قرارداد قفل: فقط «رسیدن» سخت است —
                # * قطعه‌ای که به چک‌پوینت قفل‌شده می‌رسد دقیقاً در همان سطح
                #   کروز می‌کند و **فرود نمی‌گیرد** (حالت عبوری)؛ کاربر مسئله
                #   را همین می‌دید: «چک‌پوینت را بالا بردم، مسیر همان‌جا روی
                #   زمین بود» — عاملِ اصلی، کروزِ قفل‌شده *به‌همراه* فرودِ مجاز
                #   بود که خط را در انتهای قطعه به زمین می‌پیچاند.
                # * قطعه‌ای که *از* چک‌پوینت قفل‌شده آغاز می‌شود از همان ارتفاع
                #   در-هوا آغاز می‌شود تا مسیر پیوسته باشد، ولی کروزش آزاد است:
                #   اجبارِ کروزِ آن قطعه به همان سطح، برنامه‌ای که «دقیقاً در
                #   همان سطح به مقصد برسد» می‌جست و اغلب واقعاً هم چنین
                #   برنامه‌ای بادسواری‌پذیر نیست — درحالی‌که گذار بعدی
                #   (صعود/فرود به سطح منتخب باند) کاملاً فیزیکی است.
                #
                # باد در ارتفاع قفل هم واقعی است: اگر قفل وسطِ دل لایه‌ها باشد
                # (مثلاً ۱۸۰۰)، با نمایهٔ پیوستهٔ باد یک لایهٔ واقعی همان ارتفاع
                # به فهرست لایه‌ها اضافه می‌شود — نمونه‌بردار بادسواری بادِ
                # همان ارتفاع را می‌خواند، نه بادِ «نزدیک‌ترین لایه» را.
                land_at_end = end_lock is None
                start_altitude_m = start_lock
                if end_lock is not None:
                    _check_lock_within_band(locked_alt, band_levels)
                    exact_lock_layer = any(
                        abs(level_altitude - locked_alt) <= _BAND_EPS
                        for level_altitude, _ in layers
                    )
                    if not exact_lock_layer:
                        layers = layers + [
                            (float(locked_alt), _sampler_for_level(locked_alt))
                        ]
                    cruise_altitudes: list[float] | None = [end_lock]
                elif band_levels:
                    cruise_altitudes = list(band_levels)
                else:
                    cruise_altitudes = None
                plan = plan_wind_riding_route(
                    origin, destination, layers,
                    aircraft=aircraft_config,
                    effort=MotorEffortConfig(),
                    vertical=VerticalCostConfig(),
                    config=planner_config,
                    # **زمین.** بدون این دو، ارتفاع‌های برنامه AGL تفسیر
                    # می‌شدند و صحنه — که آن‌ها را MSL می‌کشد — مسیری می‌دید
                    # که روی دامنهٔ کوه «چسبیده به زمین» است.
                    ground_elevation_at=_ground_elevation_at,
                    min_clearance_m=_min_clearance_m,
                    cruise_altitudes=cruise_altitudes,
                    land_at_end=land_at_end,
                    start_altitude_m=start_altitude_m,
                )
                if plan is None:
                    # هیچ برنامهٔ بادسواری در باند انتخابی جا نمی‌شود (کوه سر راه
                    # است). مسیریابی گراف روی *همان* باند مسیر را دور کوه می‌برد،
                    # پس همان جای‌گزین می‌شود؛ در حالت «همهٔ لایه‌ها» نبودِ برنامه
                    # یعنی هیچ مسیری برای این باد/سرعت نیست.
                    # با قفل ارتفاع، جای‌گزینِ گراف قفل را بی‌احترامی نقض می‌کند
                    # (مسیر دور کوه در سطح دیگر می‌گذرد، نه در ارتفاع چک‌پوینت)
                    # — پس به‌جای سکوت، رد صریح با پیام گویا.
                    if locked_alt is not None:
                        raise ValueError(
                            f"سطح قفل‌شدهٔ چک‌پوینت ({locked_alt:.0f} متر) در این زمینه "
                            "قابل پرواز نیست (زمین سر راه است)؛ ارتفاع چک‌پوینت را "
                            "کمی تغییر دهید یا باند بالاتر را امتحان کنید."
                        )
                    if band_levels is None:
                        raise ValueError("Wind riding route could not be planned")
                    result = _route_on_band(router, origin, destination, band_levels)
                else:
                    result = wind_riding_route_result(
                        plan,
                        aircraft=aircraft_config,
                        effort=MotorEffortConfig(),
                        vertical=VerticalCostConfig(),
                        criterion=criterion,
                        ground_elevation_at=_ground_elevation_at,
                    )
            elif altitude is not None:
                # Single layer mode
                result = router.route_on_single_layer(origin, destination, altitude)
            else:
                # Auto layer selection mode — با باند انتخابی محدود به همان سطوح.
                # قفل ارتفاع چک‌پوینت در گراف: مسیر **دقیقاً در همان ارتفاع قفل**
                # می‌گذرد. برای سطح استاندارد لایه‌های موجود؛ برای ارتفاع میانیِ
                # دل لایه‌ها (مثلاً ۱۸۰۰) یک لایهٔ واقعی با همان مدل نمایهٔ باد
                # ساخته می‌شود — کاربر دیگر مجبور نیست چک-پوینتش به «نزدیک‌ترین
                # سطح» بچسبد. لنگر هوایی سرِ قفل‌شده هم (ساختار گراف) پا برجاست:
                # مسیر به‌جای گره زمین از گره هوایی همان مختصات/همان ارتفاع
                # می‌گذرد، یعنی هنگام عبور از چک-پوینت، همان‌جا در ارتفاع قفل است
                # و به زمین نمی‌خورد.
                if locked_alt is not None:
                    _check_lock_within_band(locked_alt, band_levels)
                    locked_router = _router_for_locked_level(
                        locked_alt, criterion, backend_algorithm, aircraft_config
                    )
                    try:
                        result = locked_router.find_optimal_path(
                            origin,
                            destination,
                            layers=[locked_alt],
                            endpoint_altitudes=(start_lock, end_lock),
                        )
                    except ValueError as exc:
                        raise ValueError(
                            f"پرواز در ارتفاع قفل‌شدهٔ چک‌پوینت "
                            f"({locked_alt:.0f} متر) مسیر پروازپذیری ندارد "
                            "(زمین مانع است)؛ ارتفاع چک‌پوینت را تغییر دهید یا "
                            "باند دیگری را انتخاب کنید."
                        ) from exc
                else:
                    result = _route_on_band(router, origin, destination, band_levels)
        except ValueError as e:
            if "same ground node" in str(e):
                # Waypoints too close, skip this segment
                continue
            raise

        # Accumulate path coordinates (skip first point of subsequent segments to avoid duplicates)
        segment_coords = [(lat, lon) for lat, lon in result.path]
        if not all_path_coords:
            all_path_coords.extend(segment_coords)
        else:
            all_path_coords.extend(segment_coords[1:])

        # Build 3D path with altitudes from node_altitudes (includes ground nodes at 0)
        if hasattr(result, 'node_altitudes') and result.node_altitudes:
            segment_3d = list(zip(
                [lat for lat, lon in result.path],
                [lon for lat, lon in result.path],
                result.node_altitudes,
                strict=True,
            ))
            if not all_path_3d:
                all_path_3d.extend(segment_3d)
            else:
                all_path_3d.extend(segment_3d[1:])
        elif hasattr(result, 'path_3d') and result.path_3d:
            segment_3d = [(lat, lon, alt) for lat, lon, alt in result.path_3d]
            if not all_path_3d:
                all_path_3d.extend(segment_3d)
            else:
                all_path_3d.extend(segment_3d[1:])
        elif hasattr(result, 'altitudes_used') and result.altitudes_used:
            # Use per-point altitudes if available
            segment_3d = list(zip(
                [lat for lat, lon in result.path],
                [lon for lat, lon in result.path],
                result.altitudes_used,
                strict=True,
            ))
            if not all_path_3d:
                all_path_3d.extend(segment_3d)
            else:
                all_path_3d.extend(segment_3d[1:])
        else:
            # Fallback: use layer_altitude for all points
            segment_3d = [(lat, lon, result.layer_altitude) for lat, lon in result.path]
            if not all_path_3d:
                all_path_3d.extend(segment_3d)
            else:
                all_path_3d.extend(segment_3d[1:])

        # Accumulate metrics
        total_distance_km += result.total_distance_km
        total_time_hours += result.estimated_time_hours
        total_cost += result.total_cost

        if hasattr(result, 'altitudes_used') and result.altitudes_used:
            all_altitudes_used.extend(result.altitudes_used)

        if layer_altitude is None:
            layer_altitude = result.layer_altitude

        last_result = result

    if not all_path_coords:
        raise ValueError("Could not compute route — waypoints may be too close together")

    # Convert to API format
    path_coords = [Coordinate(lat=lat, lon=lon) for lat, lon in all_path_coords]
    # ``path_3d`` عمداً ارتفاع **MSL** می‌خواهد (صحنه سه‌بعدی همین را می‌کشد)،
    # ولی قرارداد ``RouteResult`` برای «گره زمین» ارتفاع صفر می‌گذارد — یعنی
    # «روی زمین»، نه «سطح دریا». بدون ترجمه، خط سه‌بعدی در دو سر مسیر و روی هر
    # چک‌پوینت تا سطح دریا شیرجه می‌زد (روی زمین ۲۰۰۰ متری، دو کیلومتر زیر
    # زمین!). پس هر ارتفاع صفرِ گره زمین به ارتفاع واقعی زمین همان نقطه بدل می‌شود.
    path_3d = (
        [
            Coordinate3D(
                lat=lat,
                lon=lon,
                alt=alt if alt > 0.0 else _ground_elevation_at(lat, lon),
            )
            for lat, lon, alt in all_path_3d
        ]
        if all_path_3d
        else None
    )

    # نقاط شروع/پایان مسیر باید *دقیقاً* همان مختصاتی باشند که کاربر داده —
    # گراف به نزدیک‌ترین گره جهش می‌کند (اسنپ) و اگر همان‌جا رها شود، اولین
    # و آخرین نقطهٔ مسیر چند صد متر از انتخاب کاربر فاصله دارد. درج صریح:
    # اگر نقطهٔ اسنپ‌شده برابر مبدأ/مقصد است همان می‌ماند؛ وگرنه جایگزین و
    # نقطهٔ دقیق کاربر سر جایش می‌نشیند.
    exact_origin = request.origin
    exact_dest = request.destination
    if path_coords:
        first, last = path_coords[0], path_coords[-1]
        eps = 1e-6
        if abs(first.lat - exact_origin.lat) > eps or abs(first.lon - exact_origin.lon) > eps:
            path_coords[0] = Coordinate(lat=exact_origin.lat, lon=exact_origin.lon)
        if abs(last.lat - exact_dest.lat) > eps or abs(last.lon - exact_dest.lon) > eps:
            path_coords[-1] = Coordinate(lat=exact_dest.lat, lon=exact_dest.lon)
        # همین قرارداد در مسیر سه‌بعدی — ارتفاع نقطهٔ اتصال حفظ می‌شود
        if path_3d:
            if abs(path_3d[0].lat - exact_origin.lat) > eps or abs(path_3d[0].lon - exact_origin.lon) > eps:
                path_3d[0] = Coordinate3D(
                    lat=exact_origin.lat, lon=exact_origin.lon, alt=path_3d[0].alt
                )
            if abs(path_3d[-1].lat - exact_dest.lat) > eps or abs(path_3d[-1].lon - exact_dest.lon) > eps:
                path_3d[-1] = Coordinate3D(
                    lat=exact_dest.lat, lon=exact_dest.lon, alt=path_3d[-1].alt
                )

    return RouteResult(
        route_id=uuid4().hex,
        path=path_coords,
        path_3d=path_3d,
        layer_altitude_m=layer_altitude or (altitude or 0.0),
        algorithm=request.algorithm or "a_star",
        criterion=criterion,
        total_distance_km=total_distance_km,
        estimated_time_hours=total_time_hours,
        total_cost=total_cost,
        created_at=datetime.now(timezone.utc).isoformat(),
        is_saved=False,
        # Additional metrics from WindRouter
        total_energy_index=getattr(last_result, 'total_energy_index', None),
        tailwind_leg_fraction=getattr(last_result, 'tailwind_leg_fraction', None),
        heading_changes=getattr(last_result, 'heading_changes', None),
        total_climb_m=getattr(last_result, 'total_climb_m', None),
        total_descent_m=getattr(last_result, 'total_descent_m', None),
        climb_legs=getattr(last_result, 'climb_legs', None),
        altitudes_used=all_altitudes_used if all_altitudes_used else None,
    )


# ---- Endpoints ----

@router.post(
    "",
    response_model=RouteResult | RouteJobAccepted,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Immediate result (sync mode)"},
        202: {"description": "Job accepted (async mode)"},
        400: {"description": "Bad request"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limited"},
    },
)
async def calculate_route(request: RouteRequest):
    """
    Calculate optimal route.

    - Sync mode (default): returns RouteResult directly.
    - Async mode (async=true): returns RouteJobAccepted, poll /routes/jobs/{jobId}.
    """
    if request.async_mode:
        job_id = str(uuid4())
        _jobs[job_id] = RouteJobStatus(
            job_id=job_id,
            status="pending",
            progress=0,
        )
        # In production: enqueue background task (Celery, RQ, etc.)
        # قرارداد اسپک: پذیرش کار = ۲۰۲ (نه ۲۰۰) — کلاینت از وضعیت متمایز می‌فهمد
        # که پاسخ «نتیجه» نیست و باید polling کند.
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=RouteJobAccepted(
                job_id=job_id,
                estimated_duration_seconds=30,
            ).model_dump(),
        )

    # Sync mode
    return compute_route_sync(request)


@router.get("/{route_id}", response_model=RouteResult)
async def get_route(route_id: str):
    """Get a previously calculated route by ID."""
    # TODO: Implement persistence lookup
    raise HTTPException(status_code=404, detail="Route not found")


@router.get("/jobs/{job_id}", response_model=RouteJobStatus)
async def get_job_status(job_id: str):
    """Get status of an async routing job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/compare-layers", response_model=LayerComparison)
async def compare_layers(job_id: str):
    """Compare all altitude layers for a completed job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Job not completed yet")

    # مقایسهٔ واقعی لایه‌ها هنوز پیاده‌سازی نشده است. ردیف‌های جعلی قبلی
    # (لایه‌های ۵۰۰/۱۰۰۰/۲۰۰۰ که اصلاً سطوح پرواز پروژه نیستند) حذف شدند:
    # دادهٔ ساختگی معتبرتر از خطای شفاف نیست. تا پیاده‌سازی، پاسخ صادقانهٔ
    # ۵۰۱ بدهید تا مصرف‌کننده روی دادهٔ دموی بی‌ربط به لایه‌های واقعی تصمیم
    # نگیرد.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="مقایسهٔ لایه‌ها هنوز پیاده‌سازی نشده است.",
    )
