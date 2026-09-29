"""مدیریت حالت (state) رابط کاربری و اتصال کنترل‌ها به فراخوانی‌های بک‌اند.

هر کنترل UI (انتخاب مبدأ/مقصد، الگوریتم، معیار، فیلترها، دکمه اجرا، پاپ‌آپ نقطه) یک
«اکشن» نام‌دار در ``RoutingSession`` دارد. اکشن‌ها ورودی را اعتبارسنجی می‌کنند، حالت را
به‌روز می‌کنند، رویداد ``state.changed`` منتشر می‌کنند و ``calculate`` حالت را به یک
``RouteRequest`` تبدیل و از ``RoutingService`` اجرا می‌کند.
"""

from __future__ import annotations

import copy
from typing import Any

from backend.errors import ApiError, ValidationFailed
from backend.events import Event, EventBus
from backend.schemas import (
    ALGORITHMS,
    CRITERIA,
    parse_coordinate,
    parse_route_request,
)
from backend.service import RoutingService

__all__ = ["RoutingSession", "STATE_CHANGED"]

STATE_CHANGED = "state.changed"


def _initial_state() -> dict[str, Any]:
    return {
        "origin": None,
        "destination": None,
        "checkpoints": [],
        "layer_mode": "auto",
        "altitude_m": None,
        "algorithm": "a_star",
        "criterion": "time",
        "time_weight": 0.5,
        "max_wind_speed_mps": None,
        "altitude_range_m": None,
        "avoid_zones": [],
        "visible_layers": [],
        "last_result": None,
        "last_error": None,
    }


class RoutingSession:
    """حالت یک نشست UI. ایمن‌سازی چندنخی برعهده فراخواننده است (یک نشست = یک کاربر)."""

    def __init__(self, service: RoutingService, bus: EventBus | None = None) -> None:
        self.service = service
        self.bus = bus or service.bus
        self._state = _initial_state()

    # --------------------------------------------------------------- نمای حالت
    @property
    def state(self) -> dict[str, Any]:
        """کپی عمیق حالت جاری (UI نباید مستقیم آن را تغییر دهد)."""
        return copy.deepcopy(self._state)

    def dispatch(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """اجرای یک اکشن نام‌دار؛ خروجی برای اکشن‌های پرس‌وجو نتیجه، برای بقیه حالت جدید."""
        handler = self.ACTIONS.get(action)
        if handler is None:
            raise ValidationFailed([("action", f"unknown action {action!r}")])
        return getattr(self, handler)(payload or {})

    def _changed(self, action: str) -> dict[str, Any]:
        snap = self.state
        self.bus.publish(Event(STATE_CHANGED, {"action": action, "state": snap}))
        return snap

    # ------------------------------------------------------------- مبدأ/مقصد
    def _coord(self, payload: dict[str, Any], key: str) -> dict[str, float]:
        issues: list[tuple[str, str]] = []
        c = parse_coordinate(payload, key, issues)
        if issues or c is None:
            raise ValidationFailed(issues)
        return {"lat": c.lat, "lon": c.lon}

    def set_origin(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._state["origin"] = self._coord(payload, "origin")
        return self._changed("set_origin")

    def set_destination(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._state["destination"] = self._coord(payload, "destination")
        return self._changed("set_destination")

    def swap_endpoints(self, payload: dict[str, Any]) -> dict[str, Any]:
        s = self._state
        s["origin"], s["destination"] = s["destination"], s["origin"]
        return self._changed("swap_endpoints")

    def add_checkpoint(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._state["checkpoints"].append(self._coord(payload, "checkpoint"))
        return self._changed("add_checkpoint")

    def remove_checkpoint(self, payload: dict[str, Any]) -> dict[str, Any]:
        idx = payload.get("index")
        cps = self._state["checkpoints"]
        if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < len(cps):
            raise ValidationFailed([("index", "must be a valid checkpoint index")])
        cps.pop(idx)
        return self._changed("remove_checkpoint")

    # ------------------------------------------------ الگوریتم/معیار/لایه‌ها
    def set_algorithm(self, payload: dict[str, Any]) -> dict[str, Any]:
        algo = payload.get("algorithm")
        if algo not in ALGORITHMS:
            raise ValidationFailed([("algorithm", f"must be one of {list(ALGORITHMS)}")])
        self._state["algorithm"] = algo
        return self._changed("set_algorithm")

    def set_criterion(self, payload: dict[str, Any]) -> dict[str, Any]:
        crit = payload.get("criterion")
        if crit not in CRITERIA:
            raise ValidationFailed([("criterion", f"must be one of {list(CRITERIA)}")])
        self._state["criterion"] = crit
        if "time_weight" in payload:
            self._set_time_weight(payload["time_weight"])
        return self._changed("set_criterion")

    def _set_time_weight(self, value: Any) -> None:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0.0 <= value <= 1.0
        ):
            raise ValidationFailed([("time_weight", "must be a number within [0, 1]")])
        self._state["time_weight"] = float(value)

    def set_time_weight(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._set_time_weight(payload.get("time_weight"))
        return self._changed("set_time_weight")

    def set_layer_mode(self, payload: dict[str, Any]) -> dict[str, Any]:
        mode = payload.get("layer_mode")
        if mode not in ("auto", "manual"):
            raise ValidationFailed([("layer_mode", "must be 'auto' or 'manual'")])
        self._state["layer_mode"] = mode
        if mode == "auto":
            self._state["altitude_m"] = None
        return self._changed("set_layer_mode")

    def set_altitude(self, payload: dict[str, Any]) -> dict[str, Any]:
        alt = payload.get("altitude_m")
        if not isinstance(alt, (int, float)) or isinstance(alt, bool):
            raise ValidationFailed([("altitude_m", "must be a number")])
        if not self.service.provider.has_layer(float(alt)):
            raise ValidationFailed(
                [("altitude_m", f"no such layer; available: {list(self.service.provider.altitudes)}")]
            )
        self._state["altitude_m"] = float(alt)
        self._state["layer_mode"] = "manual"
        return self._changed("set_altitude")

    def toggle_layer_visibility(self, payload: dict[str, Any]) -> dict[str, Any]:
        alt = payload.get("altitude_m")
        if not isinstance(alt, (int, float)) or not self.service.provider.has_layer(float(alt)):
            raise ValidationFailed([("altitude_m", "must be an existing layer altitude")])
        vis = self._state["visible_layers"]
        alt = float(alt)
        if alt in vis:
            vis.remove(alt)
        else:
            vis.append(alt)
            vis.sort()
        return self._changed("toggle_layer_visibility")

    # ------------------------------------------------------------------ فیلترها
    def set_max_wind_speed(self, payload: dict[str, Any]) -> dict[str, Any]:
        v = payload.get("max_wind_speed_mps")
        if v is not None and (
            not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0
        ):
            raise ValidationFailed([("max_wind_speed_mps", "must be a positive number or null")])
        self._state["max_wind_speed_mps"] = None if v is None else float(v)
        return self._changed("set_max_wind_speed")

    def set_altitude_range(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = payload.get("altitude_range_m")
        if r is not None:
            if (
                not isinstance(r, (list, tuple))
                or len(r) != 2
                or not all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in r)
                or r[0] > r[1]
            ):
                raise ValidationFailed(
                    [("altitude_range_m", "must be [min, max] with min <= max, or null")]
                )
            r = [float(r[0]), float(r[1])]
        self._state["altitude_range_m"] = r
        return self._changed("set_altitude_range")

    def add_avoid_zone(self, payload: dict[str, Any]) -> dict[str, Any]:
        issues: list[tuple[str, str]] = []
        center = parse_coordinate(payload.get("center"), "center", issues)
        radius = payload.get("radius_km")
        if not isinstance(radius, (int, float)) or isinstance(radius, bool) or radius < 0:
            issues.append(("radius_km", "must be a non-negative number"))
        if issues or center is None:
            raise ValidationFailed(issues)
        self._state["avoid_zones"].append(
            {
                "type": "circle",
                "center": {"lat": center.lat, "lon": center.lon},
                "radius_km": float(radius),
            }
        )
        return self._changed("add_avoid_zone")

    def remove_avoid_zone(self, payload: dict[str, Any]) -> dict[str, Any]:
        idx = payload.get("index")
        zones = self._state["avoid_zones"]
        if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < len(zones):
            raise ValidationFailed([("index", "must be a valid avoid-zone index")])
        zones.pop(idx)
        return self._changed("remove_avoid_zone")

    def reset_filters(self, payload: dict[str, Any]) -> dict[str, Any]:
        s = self._state
        s["max_wind_speed_mps"] = None
        s["altitude_range_m"] = None
        s["avoid_zones"] = []
        return self._changed("reset_filters")

    def reset(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._state = _initial_state()
        return self._changed("reset")

    # ------------------------------------------------------- فراخوانی موتور
    def build_request(self, is_async: bool = False) -> dict[str, Any]:
        """بدنه JSON درخواست ``POST /routes`` را از حالت جاری می‌سازد."""
        s = self._state
        body: dict[str, Any] = {
            "origin": s["origin"],
            "destination": s["destination"],
            "checkpoints": [dict(c, order=i) for i, c in enumerate(s["checkpoints"])],
            "layer_mode": s["layer_mode"],
            "altitude_m": s["altitude_m"],
            "algorithm": s["algorithm"],
            "async": is_async,
            "constraints": {
                "criterion": s["criterion"],
                "max_wind_speed_mps": s["max_wind_speed_mps"],
                "altitude_range_m": s["altitude_range_m"],
                "avoid_zones": s["avoid_zones"],
            },
        }
        if s["criterion"] == "balanced":
            body["constraints"]["weights"] = {
                "time": s["time_weight"],
                "energy": round(1.0 - s["time_weight"], 10),
            }
        return body

    def calculate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """دکمه «Calculate Path»: حالت → موتور → نتیجه در ``last_result`` (یا ``last_error``)."""
        try:
            request = parse_route_request(self.build_request(bool(payload.get("async", False))))
            status, body = self.service.submit(request)
        except ApiError as exc:
            self._state["last_result"] = None
            self._state["last_error"] = {"code": exc.code, "message": exc.message}
            self._changed("calculate")
            raise
        self._state["last_error"] = None
        self._state["last_result"] = body if status == 200 else None
        if status == 202:
            self._state["pending_job_id"] = body["job_id"]
        snap = self._changed("calculate")
        return snap

    def compare_layers(self, payload: dict[str, Any]) -> dict[str, Any]:
        """دکمه «Compare layers» برای آخرین مسیر محاسبه‌شده."""
        res = self._state["last_result"]
        if res is None:
            raise ValidationFailed([("route", "no calculated route yet; run calculate first")])
        return self.service.get_comparison(res["route_id"])

    # --------------------------------------------------------- پاپ‌آپ‌های نقشه
    def point_info(self, payload: dict[str, Any]) -> dict[str, Any]:
        """پاپ‌آپ Point Info: باد درون‌یابی‌شده یک نقطه روی یک لایه."""
        issues: list[tuple[str, str]] = []
        c = parse_coordinate(payload, "point", issues)
        alt = payload.get("altitude_m")
        if not isinstance(alt, (int, float)) or isinstance(alt, bool):
            issues.append(("altitude_m", "must be a number"))
        elif not self.service.provider.has_layer(float(alt)):
            issues.append(("altitude_m", "no such layer"))
        if issues or c is None:
            raise ValidationFailed(issues)
        return self.service.provider.sample(float(alt), c.lat, c.lon)

    def point_info_all(self, payload: dict[str, Any]) -> dict[str, Any]:
        """پاپ‌آپ Wind Layers: باد یک نقطه روی همه لایه‌ها."""
        issues: list[tuple[str, str]] = []
        c = parse_coordinate(payload, "point", issues)
        if issues or c is None:
            raise ValidationFailed(issues)
        return {"samples": self.service.provider.sample_all(c.lat, c.lon)}

    ACTIONS = {
        "set_origin": "set_origin",
        "set_destination": "set_destination",
        "swap_endpoints": "swap_endpoints",
        "add_checkpoint": "add_checkpoint",
        "remove_checkpoint": "remove_checkpoint",
        "set_algorithm": "set_algorithm",
        "set_criterion": "set_criterion",
        "set_time_weight": "set_time_weight",
        "set_layer_mode": "set_layer_mode",
        "set_altitude": "set_altitude",
        "toggle_layer_visibility": "toggle_layer_visibility",
        "set_max_wind_speed": "set_max_wind_speed",
        "set_altitude_range": "set_altitude_range",
        "add_avoid_zone": "add_avoid_zone",
        "remove_avoid_zone": "remove_avoid_zone",
        "reset_filters": "reset_filters",
        "reset": "reset",
        "calculate": "calculate",
        "compare_layers": "compare_layers",
        "point_info": "point_info",
        "point_info_all": "point_info_all",
    }
