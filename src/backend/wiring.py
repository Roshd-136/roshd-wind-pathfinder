"""رجیستری اتصال کنترل‌های UI به اکشن‌های حالت و endpointهای API.

هر کنترل تعاملی طراحی‌شده در ``docs/frontend/architecture.md`` یک ردیف دارد. تست
``tests/backend/test_wiring.py`` تضمین می‌کند هیچ کنترلی بدون اکشن/endpoint معتبر نباشد و هر
endpoint پیاده‌سازی‌شده حداقل یک نتیجه قابل‌نمایش در UI داشته باشد.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app import IMPLEMENTED_OPERATIONS
from backend.session import RoutingSession

__all__ = ["Control", "UI_CONTROLS", "verify_wiring"]


@dataclass(frozen=True)
class Control:
    control_id: str
    component: str  # نام کامپوننت React در معماری فرانت‌اند
    action: str | None  # اکشن RoutingSession (None = فقط سمت کلاینت)
    operation: tuple[str, str] | None  # (متد, مسیر OpenAPI) که نتیجه‌اش را نمایش می‌دهد
    displays: str  # نتیجه‌ای که در UI نمایش داده می‌شود


UI_CONTROLS: tuple[Control, ...] = (
    Control("map.click.origin", "MapView", "set_origin", None, "origin marker"),
    Control("map.click.destination", "MapView", "set_destination", None, "destination marker"),
    Control("route.swap", "RouteFiltersPanel", "swap_endpoints", None, "swapped markers"),
    Control("route.checkpoint.add", "RouteFiltersPanel", "add_checkpoint", None, "checkpoint marker"),
    Control("route.checkpoint.remove", "RouteFiltersPanel", "remove_checkpoint", None, "marker removed"),
    Control("algorithm.select", "AlgorithmSelector", "set_algorithm", ("GET", "/algorithms"), "algorithm list"),
    Control("criterion.select", "AlgorithmSelector", "set_criterion", ("GET", "/algorithms"), "criteria list"),
    Control("criterion.weight", "AlgorithmSelector", "set_time_weight", None, "balanced weight"),
    Control("layer.mode", "RouteFiltersPanel", "set_layer_mode", None, "auto/manual toggle"),
    Control("layer.altitude", "RouteFiltersPanel", "set_altitude", ("GET", "/wind-layers"), "layer list"),
    Control("layer.visibility", "LayerLegend", "toggle_layer_visibility", ("GET", "/wind-layers/{altitudeM}/field"), "wind vector field"),
    Control("filter.max_wind", "RouteFiltersPanel", "set_max_wind_speed", None, "max wind slider"),
    Control("filter.altitude_range", "RouteFiltersPanel", "set_altitude_range", None, "altitude range slider"),
    Control("filter.avoid_zone.add", "RouteFiltersPanel", "add_avoid_zone", None, "avoid zone circle"),
    Control("filter.avoid_zone.remove", "RouteFiltersPanel", "remove_avoid_zone", None, "zone removed"),
    Control("filter.reset", "RouteFiltersPanel", "reset_filters", None, "cleared filters"),
    Control("cta.calculate", "PathInfoPanel", "calculate", ("POST", "/routes"), "path, time, distance, best layer"),
    Control("route.compare_layers", "PathInfoPanel", "compare_layers", ("GET", "/routes/jobs/{jobId}/compare-layers"), "layer comparison table"),
    Control("popup.point_info", "PointInfoPopup", "point_info", ("GET", "/wind-layers/{altitudeM}/point"), "speed/direction"),
    Control("popup.wind_layers", "PointInfoPopup", "point_info_all", ("GET", "/wind-layers/point-all"), "per-layer wind table"),
    Control("route.reset", "PathInfoPanel", "reset", None, "cleared session"),
    Control("route.load", "PathInfoPanel", None, ("GET", "/routes/{routeId}"), "saved route"),
    Control("route.delete", "PathInfoPanel", None, ("DELETE", "/routes/{routeId}"), "route removed"),
    Control("route.job_status", "PathInfoPanel", None, ("GET", "/routes/jobs/{jobId}"), "progress bar"),
    Control("map.toggle_2d_3d", "MapView", None, None, "client-only view mode"),
)


def verify_wiring() -> list[str]:
    """فهرست مشکلات اتصال؛ خالی یعنی همه کنترل‌ها و endpointها کامل متصل‌اند."""
    problems: list[str] = []
    seen: set[str] = set()
    for c in UI_CONTROLS:
        if c.control_id in seen:
            problems.append(f"duplicate control id: {c.control_id}")
        seen.add(c.control_id)
        if c.action is not None and c.action not in RoutingSession.ACTIONS:
            problems.append(f"{c.control_id}: unknown action {c.action!r}")
        if c.operation is not None and c.operation not in IMPLEMENTED_OPERATIONS:
            problems.append(f"{c.control_id}: operation {c.operation} is not implemented")
        if c.action is None and c.operation is None and c.control_id != "map.toggle_2d_3d":
            problems.append(f"{c.control_id}: dead control (no action and no operation)")
    used_ops = {c.operation for c in UI_CONTROLS if c.operation}
    used_actions = {c.action for c in UI_CONTROLS if c.action}
    for op in IMPLEMENTED_OPERATIONS:
        if op not in used_ops:
            problems.append(f"operation {op} has no UI control displaying its result")
    for act in RoutingSession.ACTIONS:
        if act not in used_actions:
            problems.append(f"action {act!r} is not bound to any UI control")
    return problems
