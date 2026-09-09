"""تست‌های واحد برای مدل هزینه دینامیکی یال‌ها (``pathfinding.cost``)."""

from __future__ import annotations

import math

import pytest

from pathfinding.cost import (
    CostModelConfig,
    InfeasibleEdgeError,
    compute_edge_cost,
    decompose_wind,
    ground_speed_mps,
    initial_bearing_deg,
)

# Real Khorasan station coordinates (data/khorasan_wind_qc_cleaned.csv).
MASHHAD = (36.297, 59.606)
NEYSHABUR = (36.213, 58.795)
SABZEVAR = (36.215, 57.678)


def test_initial_bearing_due_east_is_90() -> None:
    # Same latitude, moving to a higher longitude -> bearing should be ~east (90 deg).
    bearing = initial_bearing_deg(36.0, 58.0, 36.0, 59.0)
    assert 85.0 < bearing < 95.0


def test_initial_bearing_due_north_is_0() -> None:
    bearing = initial_bearing_deg(35.0, 59.0, 36.0, 59.0)
    assert bearing == pytest.approx(0.0, abs=1e-6)


def test_decompose_wind_pure_tailwind() -> None:
    # Wind blowing FROM the south (180 deg) blows TOWARD the north (bearing 0).
    # Traveling due north (path_bearing=0) means this wind is a pure tailwind.
    along, cross = decompose_wind(10.0, wind_direction_from_deg=180.0, path_bearing_deg=0.0)
    assert along == pytest.approx(10.0, abs=1e-6)
    assert cross == pytest.approx(0.0, abs=1e-6)


def test_decompose_wind_pure_headwind() -> None:
    # Wind blowing FROM the north (0 deg) blows TOWARD the south; traveling due
    # north means this wind directly opposes travel (pure headwind).
    along, cross = decompose_wind(10.0, wind_direction_from_deg=0.0, path_bearing_deg=0.0)
    assert along == pytest.approx(-10.0, abs=1e-6)
    assert cross == pytest.approx(0.0, abs=1e-6)


def test_decompose_wind_pure_crosswind() -> None:
    # Wind from the west (270 deg) blows toward the east; traveling due north
    # means this wind is entirely a crosswind (no along-track component).
    along, cross = decompose_wind(10.0, wind_direction_from_deg=270.0, path_bearing_deg=0.0)
    assert along == pytest.approx(0.0, abs=1e-6)
    assert cross == pytest.approx(10.0, abs=1e-6)


def test_decompose_wind_rejects_negative_speed() -> None:
    with pytest.raises(ValueError):
        decompose_wind(-1.0, wind_direction_from_deg=0.0, path_bearing_deg=0.0)


def test_ground_speed_adds_tailwind() -> None:
    gs = ground_speed_mps(airspeed_mps=50.0, along_track_mps=10.0, cross_track_mps=0.0)
    assert gs == pytest.approx(60.0, abs=1e-6)


def test_ground_speed_crosswind_reduces_forward_progress() -> None:
    # Pure crosswind (no along component): ground speed should drop below
    # airspeed because part of the airspeed is spent countering drift.
    gs = ground_speed_mps(airspeed_mps=50.0, along_track_mps=0.0, cross_track_mps=30.0)
    assert gs < 50.0
    assert gs == pytest.approx(math.sqrt(50.0**2 - 30.0**2), abs=1e-6)


def test_ground_speed_infeasible_when_crosswind_exceeds_airspeed() -> None:
    with pytest.raises(InfeasibleEdgeError):
        ground_speed_mps(airspeed_mps=20.0, along_track_mps=0.0, cross_track_mps=25.0)


def test_compute_edge_cost_headwind_costs_more_than_tailwind() -> None:
    # Same edge, opposite wind directions: headwind must cost strictly more
    # time than tailwind.
    headwind = compute_edge_cost(
        *MASHHAD,
        *NEYSHABUR,
        wind_speed_mps=8.0,
        wind_direction_from_deg=initial_bearing_deg(*MASHHAD, *NEYSHABUR),
        criterion="time",
    )
    tailwind = compute_edge_cost(
        *MASHHAD,
        *NEYSHABUR,
        wind_speed_mps=8.0,
        wind_direction_from_deg=(initial_bearing_deg(*MASHHAD, *NEYSHABUR) + 180.0) % 360.0,
        criterion="time",
    )
    assert headwind.time_hours > tailwind.time_hours


def test_compute_edge_cost_no_wind_all_criteria_equal_no_wind_baseline() -> None:
    # With zero wind speed, along/cross are both zero regardless of direction,
    # so ground speed equals airspeed and time/energy/balanced all collapse
    # to the same no-wind baseline value.
    config = CostModelConfig(airspeed_mps=50.0)
    result = compute_edge_cost(
        *MASHHAD, *SABZEVAR, wind_speed_mps=0.0, wind_direction_from_deg=123.0, config=config
    )
    distance_km = result.distance_km
    expected_hours = distance_km / (50.0 * 3.6)
    assert result.time_hours == pytest.approx(expected_hours, rel=1e-9)
    assert result.energy_hours == pytest.approx(expected_hours, rel=1e-9)
    assert result.balanced_hours == pytest.approx(expected_hours, rel=1e-9)


def test_compute_edge_cost_crosswind_makes_energy_exceed_time() -> None:
    bearing = initial_bearing_deg(*MASHHAD, *SABZEVAR)
    crosswind_from = (bearing + 90.0) % 360.0
    result = compute_edge_cost(
        *MASHHAD,
        *SABZEVAR,
        wind_speed_mps=15.0,
        wind_direction_from_deg=crosswind_from,
        config=CostModelConfig(airspeed_mps=50.0, induced_drag_coeff=0.3),
        criterion="energy",
    )
    assert result.energy_hours > result.time_hours


def test_compute_edge_cost_balanced_is_between_time_and_energy() -> None:
    bearing = initial_bearing_deg(*MASHHAD, *SABZEVAR)
    crosswind_from = (bearing + 90.0) % 360.0
    result = compute_edge_cost(
        *MASHHAD,
        *SABZEVAR,
        wind_speed_mps=15.0,
        wind_direction_from_deg=crosswind_from,
        criterion="balanced",
        time_weight=0.5,
    )
    lo, hi = sorted((result.time_hours, result.energy_hours))
    assert lo <= result.balanced_hours <= hi


def test_compute_edge_cost_time_weight_override_shifts_balanced_toward_time() -> None:
    bearing = initial_bearing_deg(*MASHHAD, *SABZEVAR)
    crosswind_from = (bearing + 90.0) % 360.0
    mostly_time = compute_edge_cost(
        *MASHHAD,
        *SABZEVAR,
        wind_speed_mps=15.0,
        wind_direction_from_deg=crosswind_from,
        criterion="balanced",
        time_weight=0.9,
    )
    mostly_energy = compute_edge_cost(
        *MASHHAD,
        *SABZEVAR,
        wind_speed_mps=15.0,
        wind_direction_from_deg=crosswind_from,
        criterion="balanced",
        time_weight=0.1,
    )
    assert mostly_time.balanced_hours < mostly_energy.balanced_hours


def test_compute_edge_cost_rejects_invalid_criterion() -> None:
    with pytest.raises(ValueError):
        compute_edge_cost(
            *MASHHAD, *SABZEVAR, wind_speed_mps=5.0, wind_direction_from_deg=90.0, criterion="fastest"
        )


def test_compute_edge_cost_rejects_invalid_time_weight() -> None:
    with pytest.raises(ValueError):
        compute_edge_cost(
            *MASHHAD,
            *SABZEVAR,
            wind_speed_mps=5.0,
            wind_direction_from_deg=90.0,
            time_weight=1.5,
        )


def test_compute_edge_cost_raises_infeasible_for_extreme_headwind() -> None:
    # Airspeed well below a direct headwind of the same magnitude cannot
    # produce positive ground speed.
    bearing = initial_bearing_deg(*MASHHAD, *SABZEVAR)
    headwind_from = bearing
    with pytest.raises(InfeasibleEdgeError):
        compute_edge_cost(
            *MASHHAD,
            *SABZEVAR,
            wind_speed_mps=60.0,
            wind_direction_from_deg=headwind_from,
            config=CostModelConfig(airspeed_mps=50.0),
        )


def test_cost_model_config_rejects_invalid_airspeed() -> None:
    with pytest.raises(ValueError):
        CostModelConfig(airspeed_mps=0.0)


def test_cost_model_config_rejects_invalid_time_weight() -> None:
    with pytest.raises(ValueError):
        CostModelConfig(time_weight=1.2)
