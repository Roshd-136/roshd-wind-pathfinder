"""تست‌های واحد برای برنامه‌ریزی مسیر «بادسواری» ``pathfinding.wind_riding``."""

from __future__ import annotations

import pytest

from pathfinding.wind_riding import (
    WindRidingConfig,
    plan_wind_riding_route,
    wind_riding_route_result,
)
from preprocessing.consistency import haversine_km

ORIGIN = (36.250, 59.250)
DESTINATION = (36.100, 58.950)  # ~26 km to the south-west


def _constant_sampler(speed_mps: float, direction_from_deg: float):
    """نمونه‌بردار باد ساده که در همه‌جا یک مقدار برمی‌گرداند."""
    return lambda _lat, _lon: (speed_mps, direction_from_deg)


def _flat_ground(_lat: float, _lon: float) -> float:
    return 0.0


def _plan(**kwargs):
    layers = [
        (1000.0, _constant_sampler(5.0, 240.0)),
        (2000.0, _constant_sampler(10.0, 240.0)),
    ]
    options = dict(
        ground_elevation_at=_flat_ground,
        min_clearance_m=300.0,
        cruise_altitudes=[1000.0, 2000.0],
    )
    options.update(kwargs)
    return plan_wind_riding_route(ORIGIN, DESTINATION, layers, **options)


# ---------------------------------------------------------------------------
# Band ceiling: ``max_altitude_msl_m``
# ---------------------------------------------------------------------------


def test_config_rejects_non_positive_band_ceiling() -> None:
    """سقف باند باید مثبت باشد؛ صفر یا منفی خطای صریح است."""
    with pytest.raises(ValueError, match="max_altitude_msl_m"):
        WindRidingConfig(max_altitude_msl_m=0.0)


def test_band_ceiling_rejects_a_plan_forced_above_it() -> None:
    """سقف باند باید برنامه‌ای را که برای رد شدن از کف زمین باید از باند بالا برود رد کند.

    زمین صاف با ارتفاع صفر و کف فاصلهٔ ۳۰۰ متر یعنی کف پرواز ۳۰۰ متر MSL است.
    با سقف باند ۲۰۰ متر هیچ سطحی نمی‌تواند هم باند را نگه دارد و هم از کف رد شود،
    پس باید ``None`` برگردد — نه اینکه مسیر از کوه رد شود.
    """
    plan = _plan(config=WindRidingConfig(max_altitude_msl_m=200.0))
    assert plan is None


def test_band_ceiling_allows_a_plan_that_fits_under_it() -> None:
    """سقفی که از کف زمین بالاتر است نباید مسیر مشروع را رد کند."""
    plan = _plan(config=WindRidingConfig(max_altitude_msl_m=1000.0))
    assert plan is not None
    assert plan.min_terrain_clearance_m is not None


def test_config_rejects_non_positive_band_ceiling_when_planning() -> None:
    """حتی اگر باند از مسیر API نیاید، مقدار نامعتبر باید همان‌جا رد شود."""
    with pytest.raises(ValueError, match="max_altitude_msl_m"):
        _plan(config=WindRidingConfig(max_altitude_msl_m=-1.0))


# ---------------------------------------------------------------------------
# Endpoint geometry: start and end are exact, no fold / overshoot
# ---------------------------------------------------------------------------


def test_plan_starts_and_ends_exactly_at_the_requested_points() -> None:
    plan = _plan()
    assert plan is not None
    assert haversine_km(*plan.path[0], *ORIGIN) < 1e-6
    assert haversine_km(*plan.path[-1], *DESTINATION) < 1e-6


def test_plan_never_overshoots_the_destination_and_folds_back() -> None:
    """نزدیک‌ترین نقطهٔ مسیر به مقصد باید *آخرین* نقطه باشد.

    اگر برنامه از مقصد بگذرد و برگردد، نزدیک‌ترین نقطه جایی در میانه می‌مانَد و
    نقاط بعدی دوباره دور می‌شوند؛ همان «قلّاب انتهایی» که کاربر دید.
    """
    plan = _plan()
    assert plan is not None
    distances = [haversine_km(lat, lon, *DESTINATION) for lat, lon in plan.path]
    closest = min(range(len(distances)), key=distances.__getitem__)
    assert closest == len(plan.path) - 1, distances


# ---------------------------------------------------------------------------
# حالت عبوری چک‌پوینت قفل‌شدهٔ ارتفاعی (``land_at_end=False``)
# ---------------------------------------------------------------------------


def test_pass_through_ends_at_cruise_altitude_not_on_the_ground() -> None:
    """قطعه‌ای که به چک‌پوینتِ قفل‌شده می‌رسد باید **در ارتفاع** به آن برسد.

    باگ گزارش‌شدهٔ کاربر: ارتفاع چک‌پوینت در صحنه بالا برده می‌شد، ولی مسیر
    رندرشده همان‌جا روی زمین می‌نشست؛ چون هر قطعه در انتهایش فرود می‌گرفت و
    پروفایل تا زمین شیرجه می‌رفت. در حالت عبوری، نقطهٔ پایانی در ارتفاع کروز
    (همان «بودن» در چک‌پوینتِ در-هوا) می‌ماند و هیچ فاز فرودی در کار نیست.
    """
    plan = _plan(cruise_altitudes=[2000.0], land_at_end=False)
    assert plan is not None
    # هنوز مقصد قطعه همان نقطه است — فقط «ارتفاع» آن نقطه تغییر نکنده
    assert haversine_km(*plan.path[-1], *DESTINATION) < 1e-6
    # ارتفاع می‌اوست کروز بماند؛ شیرجه به زمین (صفر) ممنوع
    assert plan.node_altitudes[-1] == pytest.approx(2000.0, abs=1.0)
    # بدون فاز فرود: مسافت فرود صفر
    assert plan.descent_distance_km == 0.0


def test_result_report_keeps_in_air_endpoints_unanchored() -> None:
    """گزارش نهایی دو سرِ در-هوا را صفر (روی زمین) نکند.

    قرارداد ``RouteResult``: صفر یعنی «روی زمین همان نقطه». سرِ در-هوای
    چک‌پوینتِ قفل‌شده نباید صفر شود، وگرنه ``routes.py`` آن را به‌طرف
    ``path_3d`` با ارتفاع زمین همان نقطه پر می‌کند و باز هم شیرجه تا زمین
    دیده می‌شود.
    """
    plan = _plan(
        cruise_altitudes=[2000.0],
        land_at_end=False,
        start_altitude_m=2000.0,
    )
    assert plan is not None
    result = wind_riding_route_result(plan, ground_elevation_at=_flat_ground)
    assert result.node_altitudes[0] == pytest.approx(2000.0, abs=1.0)
    assert result.node_altitudes[-1] == pytest.approx(2000.0, abs=1.0)


def test_start_altitude_avoids_reclimbing_from_the_ground() -> None:
    """قطعه‌ای که از چک‌پوینتِ قفل‌شده می‌گذرد، صعود از زمین را دوباره نمی‌پردازد.

    قطعهٔ قبل در همان ارتفاع به چک‌پوینت رسیده؛ حساب‌کردن صعود ۲۰۰۰ متری از
    زمین در قطعهٔ بعد، بعلاوه‌شدن یک هزینهٔ پرداخت‌شده است. نخستین نقطهٔ
    پروفایل هم باید همان ارتفاعِ رسیدن باشد، نه زمینِ زیرش.
    """
    with_start = _plan(cruise_altitudes=[2000.0], start_altitude_m=2000.0)
    without_start = _plan(cruise_altitudes=[2000.0])
    assert with_start is not None and without_start is not None
    assert without_start.climb_m > 0.0
    assert with_start.climb_m == pytest.approx(0.0, abs=1.0)
    assert with_start.node_altitudes[0] == pytest.approx(2000.0, abs=1.0)
