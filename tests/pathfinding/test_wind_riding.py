"""تست‌های واحد برای برنامه‌ریزی مسیر «بادسواری» ``pathfinding.wind_riding``."""

from __future__ import annotations

import pytest

from pathfinding.wind_riding import (
    WindRidingConfig,
    plan_wind_riding_route,
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
