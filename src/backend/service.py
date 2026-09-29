"""سرویس مسیریابی — واسط یکپارچه بین API و موتور مسیریابی (Dijkstra / A* آگاه به باد).

این ماژول درخواست اعتبارسنجی‌شده (``RouteRequest``) را به فراخوانی موتور تبدیل می‌کند و
خروجی استاندارد (مسیر، زمان سفر، لایه بهینه) با ساختار ``RouteResult`` در OpenAPI برمی‌گرداند.
"""

from __future__ import annotations

import math
import threading
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

from backend.errors import ApiError, NoFeasiblePath, NotFound, ValidationFailed
from backend.events import (
    ROUTE_FAILED,
    ROUTE_QUEUED,
    ROUTE_RUNNING,
    ROUTE_SUCCEEDED,
    Event,
    EventBus,
)
from backend.provider import WindDataProvider
from backend.schemas import ALGORITHMS, Constraints, Coordinate, RouteRequest
from pathfinding.algorithms import a_star, dijkstra
from pathfinding.graph import WindGraph
from preprocessing.consistency import haversine_km

__all__ = ["RoutingService", "Job"]

_MAX_STORED_ROUTES = 500

_ALGORITHM_LABELS = {"a_star": "A* (wind-aware)", "dijkstra": "Dijkstra (wind-aware)"}
_CRITERIA_LABELS = {"time": "Minimum time", "energy": "Minimum energy", "balanced": "Balanced"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    job_id: str
    status: str = "queued"  # queued | running | succeeded | failed
    progress_pct: float = 0.0
    result: dict | None = None
    error: dict | None = None

    def to_status(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress_pct": self.progress_pct,
            "result": self.result,
            "error": self.error,
        }


# ---------------------------------------------------------------- فیلتر قیود
def _segment_distance_km(a: tuple[float, float], b: tuple[float, float], c: Coordinate) -> float:
    """کمینه فاصله مرکز ``c`` تا پاره‌خط a-b (تقریب صفحه‌ای محلی، کافی برای مقیاس منطقه‌ای)."""
    lat0 = c.lat
    kx = 111.32 * math.cos(math.radians(lat0))
    ky = 110.574

    def proj(p: tuple[float, float]) -> tuple[float, float]:
        return ((p[1] - c.lon) * kx, (p[0] - lat0) * ky)

    ax, ay = proj(a)
    bx, by = proj(b)
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    t = 0.0 if seg2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / seg2))
    return math.hypot(ax + t * dx, ay + t * dy)


def _apply_constraints(graph: WindGraph, constraints: Constraints) -> tuple[WindGraph, set[str]]:
    """گراف فیلترشده (بدون گره/یال ممنوعه) و مجموعه گره‌های حذف‌شده را برمی‌گرداند."""
    if constraints.max_wind_speed_mps is None and not constraints.avoid_zones:
        return graph, set()

    excluded: set[str] = set()
    for nid, node in graph.nodes.items():
        if (
            constraints.max_wind_speed_mps is not None
            and node.wind_speed_mps > constraints.max_wind_speed_mps
        ):
            excluded.add(nid)
            continue
        for z in constraints.avoid_zones:
            if haversine_km(node.lat, node.lon, z.center.lat, z.center.lon) <= z.radius_km:
                excluded.add(nid)
                break

    filtered = WindGraph(graph.altitude, graph.max_edge_distance_km)
    for nid, node in graph.nodes.items():
        if nid not in excluded:
            filtered.add_node(node)
    for u in filtered.nodes:
        for v in graph.get_neighbors(u):
            if v in excluded:
                continue
            edge = graph.get_edge(u, v)
            if edge is None:
                continue
            nu, nv = graph.nodes[u], graph.nodes[v]
            crosses = any(
                _segment_distance_km((nu.lat, nu.lon), (nv.lat, nv.lon), z.center) <= z.radius_km
                for z in constraints.avoid_zones
            )
            if not crosses:
                filtered.add_edge(edge)
    return filtered, excluded


class RoutingService:
    """هماهنگ‌کننده: اعتبارسنجی‌شده → موتور → خروجی استاندارد + ذخیره مسیر + jobهای async."""

    def __init__(
        self,
        provider: WindDataProvider,
        bus: EventBus | None = None,
        max_workers: int = 2,
    ) -> None:
        self.provider = provider
        self.bus = bus or EventBus()
        self._routes: OrderedDict[str, dict] = OrderedDict()
        self._comparisons: dict[str, dict] = {}
        self._jobs: dict[str, Job] = {}
        self._job_route: dict[str, str] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="route")

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)

    # ------------------------------------------------------------- فهرست گزینه‌ها
    def algorithm_options(self) -> dict:
        return {
            "algorithms": [
                {"id": a, "label": _ALGORITHM_LABELS[a], "is_default": a == "a_star"}
                for a in ALGORITHMS
            ],
            "criteria": [{"id": c, "label": _CRITERIA_LABELS[c]} for c in _CRITERIA_LABELS],
        }

    # ------------------------------------------------------------------ مسیریابی
    def submit(self, request: RouteRequest) -> tuple[int, dict]:
        """sync → ``(200, RouteResult)``؛ async → ``(202, RouteJobAccepted)``."""
        self.provider._require_data()
        if not request.is_async:
            return 200, self._run_sync(request)

        job = Job(job_id="job_" + uuid.uuid4().hex[:16])
        with self._lock:
            self._jobs[job.job_id] = job
        self.bus.publish(Event(ROUTE_QUEUED, {"job_id": job.job_id}))
        self._executor.submit(self._run_job, job, request)
        return 202, {
            "job_id": job.job_id,
            "status": "queued",
            "poll_url": f"/v1/routes/jobs/{job.job_id}",
        }

    def _run_sync(self, request: RouteRequest) -> dict:
        self.bus.publish(Event(ROUTE_RUNNING, {"job_id": None, "progress_pct": 0.0}))
        try:
            result = self.compute(request)
        except ApiError as exc:
            self.bus.publish(Event(ROUTE_FAILED, {"job_id": None, "code": exc.code}))
            raise
        self.bus.publish(
            Event(ROUTE_SUCCEEDED, {"job_id": None, "route_id": result["route_id"]})
        )
        return result

    def _run_job(self, job: Job, request: RouteRequest) -> None:
        def progress(pct: float) -> None:
            job.progress_pct = round(pct, 1)
            self.bus.publish(
                Event(ROUTE_RUNNING, {"job_id": job.job_id, "progress_pct": job.progress_pct})
            )

        job.status = "running"
        progress(0.0)
        try:
            result = self.compute(request, progress=progress)
        except ApiError as exc:
            job.error = {"code": exc.code, "message": exc.message}
            job.status = "failed"
            self.bus.publish(Event(ROUTE_FAILED, {"job_id": job.job_id, "code": exc.code}))
        except Exception as exc:  # noqa: BLE001 - job نباید بی‌صدا از بین برود
            job.error = {"code": "internal_error", "message": str(exc)}
            job.status = "failed"
            self.bus.publish(Event(ROUTE_FAILED, {"job_id": job.job_id, "code": "internal_error"}))
        else:
            with self._lock:
                self._job_route[job.job_id] = result["route_id"]
            job.result = result
            job.progress_pct = 100.0
            job.status = "succeeded"
            self.bus.publish(
                Event(ROUTE_SUCCEEDED, {"job_id": job.job_id, "route_id": result["route_id"]})
            )

    def compute(self, request: RouteRequest, progress=None) -> dict:
        """اجرای محاسبه مسیر؛ خروجی مطابق ``RouteResult`` (و ذخیره در حافظه)."""
        c = request.constraints
        layers = list(self.provider.altitudes)
        if c.altitude_range_m is not None:
            lo, hi = c.altitude_range_m
            layers = [a for a in layers if lo <= a <= hi]
        if request.layer_mode == "manual":
            alt = request.altitude_m
            if alt is None or not self.provider.has_layer(alt):
                raise ValidationFailed(
                    [("altitude_m", f"no such layer; available: {list(self.provider.altitudes)}")]
                )
            if alt not in layers:
                raise ValidationFailed([("altitude_m", "is outside constraints.altitude_range_m")])
            layers = [alt]
        if not layers:
            raise NoFeasiblePath("No altitude layer satisfies the altitude range constraint.")

        multi = self.provider.multi_graph(
            c.criterion, c.time_weight if c.criterion == "balanced" else None
        )
        waypoints = [request.origin, *request.checkpoints, request.destination]
        outcomes: dict[float, dict] = {}
        for i, alt in enumerate(layers):
            graph = multi.get_layer(alt)
            if graph is not None:
                outcome = self._route_layer(graph, waypoints, request, c)
                if outcome is not None:
                    outcomes[alt] = outcome
            if progress:
                progress(90.0 * (i + 1) / len(layers))

        if not outcomes:
            raise NoFeasiblePath(
                "No feasible path between the given points on the selected layers "
                "(check constraints, avoid zones and max wind speed)."
            )
        best_alt = min(outcomes, key=lambda a: (outcomes[a]["total_cost"], a))
        best = outcomes[best_alt]
        route_id = "route_" + uuid.uuid4().hex[:16]
        result = {
            "route_id": route_id,
            "path": [{"lat": lat, "lon": lon} for lat, lon in best["path"]],
            "layer_altitude_m": best_alt,
            "algorithm": request.algorithm,
            "criterion": c.criterion,
            "total_distance_km": round(best["distance_km"], 3),
            "estimated_time_hours": round(best["time_hours"], 4),
            "total_cost": round(best["total_cost"], 4),
            "created_at": _now(),
            "is_saved": False,
        }
        comparison = {
            "best_altitude_m": best_alt,
            "rows": [
                {
                    "layer_altitude_m": a,
                    "estimated_time_hours": round(o["time_hours"], 4),
                    "total_distance_km": round(o["distance_km"], 3),
                    "total_cost": round(o["total_cost"], 4),
                    "is_best": a == best_alt,
                }
                for a, o in sorted(outcomes.items())
            ],
        }
        with self._lock:
            self._routes[route_id] = result
            self._comparisons[route_id] = comparison
            while len(self._routes) > _MAX_STORED_ROUTES:
                old, _ = self._routes.popitem(last=False)
                self._comparisons.pop(old, None)
        return result

    def _route_layer(
        self,
        graph: WindGraph,
        waypoints: list[Coordinate],
        request: RouteRequest,
        constraints: Constraints,
    ) -> dict | None:
        """مسیر عبوری از همه waypointها روی یک لایه؛ ``None`` اگر غیرممکن باشد."""
        snapped: list[str] = []
        for w in waypoints:
            nid = graph.find_nearest_node(w.lat, w.lon)
            if nid is None:
                return None
            if not snapped or snapped[-1] != nid:
                snapped.append(nid)
        if len(snapped) < 2:
            raise ValidationFailed(
                [("destination", "resolves to the same wind-station node as origin")]
            )

        work, excluded = _apply_constraints(graph, constraints)
        if any(n in excluded for n in snapped):
            return None

        node_ids: list[str] = []
        total_cost = 0.0
        for a, b in zip(snapped, snapped[1:], strict=False):
            if request.algorithm == "a_star":
                ids, cost = a_star(work, a, b, airspeed_mps=self.provider.config.airspeed_mps)
            else:
                ids, cost = dijkstra(work, a, b)
            if not ids or math.isinf(cost):
                return None
            node_ids.extend(ids if not node_ids else ids[1:])
            total_cost += cost

        distance = 0.0
        time_h = 0.0
        for u, v in zip(node_ids, node_ids[1:], strict=False):
            edge = work.get_edge(u, v)
            if edge is None:
                return None
            distance += edge.distance_km
            time_h += edge.cost_result.time_hours if edge.cost_result else edge.weight
        path = [(work.nodes[n].lat, work.nodes[n].lon) for n in node_ids]
        return {
            "path": path,
            "total_cost": total_cost,
            "distance_km": distance,
            "time_hours": time_h,
        }

    # ------------------------------------------------------------ بازیابی/حذف
    def get_route(self, route_id: str) -> dict:
        with self._lock:
            r = self._routes.get(route_id)
        if r is None:
            raise NotFound(f"Route {route_id!r} not found.")
        return r

    def delete_route(self, route_id: str) -> None:
        with self._lock:
            if route_id not in self._routes:
                raise NotFound(f"Route {route_id!r} not found.")
            del self._routes[route_id]
            self._comparisons.pop(route_id, None)

    def get_job(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise NotFound(f"Job {job_id!r} not found.")
        return job.to_status()

    def get_comparison(self, job_or_route_id: str) -> dict:
        """جدول مقایسه لایه‌ها؛ شناسه می‌تواند job یا route باشد (مسیر sync شناسه job ندارد)."""
        with self._lock:
            route_id = self._job_route.get(job_or_route_id, job_or_route_id)
            cmp_ = self._comparisons.get(route_id)
        if cmp_ is None:
            raise NotFound(f"No layer comparison for {job_or_route_id!r}.")
        return cmp_
