"""لایه HTTP بک‌اند — endpointهای ``api/openapi.yaml`` روی کتابخانه استاندارد پایتون.

هسته (``ApiApp.handle``) مستقل از سرور است و مستقیم قابل تست است؛ ``serve`` آن را روی
``ThreadingHTTPServer`` اجرا می‌کند. وابستگی جدیدی اضافه نشده است (FastAPI در فهرست کتابخانه‌های
مجاز نیست)؛ چون قرارداد HTTP یکسان است، جایگزینی بعدی با FastAPI بدون تغییر UI ممکن است.
"""

from __future__ import annotations

import json
import math
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from backend.errors import ApiError, NotFound, ValidationFailed
from backend.events import EventBus
from backend.provider import WindDataProvider
from backend.schemas import parse_route_request
from backend.service import RoutingService

__all__ = ["ApiApp", "serve", "IMPLEMENTED_OPERATIONS", "DEFERRED_OPERATIONS"]

API_PREFIX = "/v1"
MAX_BODY_BYTES = 1_000_000

# عملیات‌های پیاده‌سازی‌شده در این تسک (متد، مسیر OpenAPI)
IMPLEMENTED_OPERATIONS = (
    ("POST", "/routes"),
    ("GET", "/routes/jobs/{jobId}"),
    ("GET", "/routes/jobs/{jobId}/compare-layers"),
    ("GET", "/routes/{routeId}"),
    ("DELETE", "/routes/{routeId}"),
    ("GET", "/wind-layers"),
    ("GET", "/wind-layers/{altitudeM}/field"),
    ("GET", "/wind-layers/{altitudeM}/point"),
    ("GET", "/wind-layers/point-all"),
    ("GET", "/algorithms"),
)

# عملیات‌های نیازمند دیتابیس/JWT — خارج از دامنه این تسک؛ پاسخ 501 صریح می‌دهند.
DEFERRED_OPERATIONS = (
    ("GET", "/points/favorites"),
    ("POST", "/points/favorites"),
    ("DELETE", "/points/favorites/{pointId}"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("POST", "/auth/refresh"),
    ("POST", "/auth/logout"),
    ("POST", "/auth/password-reset/request"),
    ("POST", "/auth/password-reset/confirm"),
    ("POST", "/auth/verify-email/confirm"),
    ("GET", "/auth/oauth/{provider}/authorize"),
    ("GET", "/auth/oauth/{provider}/callback"),
    ("GET", "/me"),
    ("PATCH", "/me"),
    ("GET", "/me/preferences"),
    ("PUT", "/me/preferences"),
    ("GET", "/me/routes"),
)


@dataclass
class _Ctx:
    params: dict[str, str]
    query: dict[str, str]
    body: Any


def _template_to_regex(template: str) -> re.Pattern[str]:
    return re.compile("^" + re.sub(r"\{[^/}]+\}", r"([^/]+)", template) + "$")


def _float_query(query: dict[str, str], name: str, issues: list[tuple[str, str]]) -> float | None:
    raw = query.get(name)
    if raw is None:
        issues.append((name, "is required"))
        return None
    try:
        val = float(raw)
    except ValueError:
        issues.append((name, "must be a number"))
        return None
    if not math.isfinite(val):
        issues.append((name, "must be a finite number"))
        return None
    return val


def _lat_lon(query: dict[str, str]) -> tuple[float, float]:
    issues: list[tuple[str, str]] = []
    lat = _float_query(query, "lat", issues)
    lon = _float_query(query, "lon", issues)
    if lat is not None and not -90 <= lat <= 90:
        issues.append(("lat", "must be within [-90, 90]"))
    if lon is not None and not -180 <= lon <= 180:
        issues.append(("lon", "must be within [-180, 180]"))
    if issues:
        raise ValidationFailed(issues)
    assert lat is not None and lon is not None
    return lat, lon


class ApiApp:
    """مسیریاب درخواست‌ها + نگاشت خطا به پاسخ JSON استاندارد."""

    def __init__(self, provider: WindDataProvider, bus: EventBus | None = None) -> None:
        self.bus = bus or EventBus()
        self.provider = provider
        self.service = RoutingService(provider, self.bus)
        handlers: dict[tuple[str, str], Callable[[_Ctx], tuple[int, Any]]] = {
            ("POST", "/routes"): self._post_route,
            ("GET", "/routes/jobs/{jobId}"): lambda c: (200, self.service.get_job(c.params["jobId"])),
            ("GET", "/routes/jobs/{jobId}/compare-layers"): lambda c: (
                200,
                self.service.get_comparison(c.params["jobId"]),
            ),
            ("GET", "/routes/{routeId}"): lambda c: (200, self.service.get_route(c.params["routeId"])),
            ("DELETE", "/routes/{routeId}"): self._delete_route,
            ("GET", "/wind-layers"): lambda c: (200, provider.layers_meta()),
            ("GET", "/wind-layers/{altitudeM}/field"): self._get_field,
            ("GET", "/wind-layers/{altitudeM}/point"): self._get_point,
            ("GET", "/wind-layers/point-all"): self._get_point_all,
            ("GET", "/algorithms"): lambda c: (200, self.service.algorithm_options()),
        }
        assert set(handlers) == set(IMPLEMENTED_OPERATIONS)
        # مسیرهای ثابت باید قبل از مسیرهای پارامتری بیایند (مثلاً point-all).
        self._routes = [
            (m, t, _template_to_regex(t), h)
            for (m, t), h in sorted(handlers.items(), key=lambda kv: "{" in kv[0][1])
        ]
        self._deferred = [(m, _template_to_regex(t)) for m, t in DEFERRED_OPERATIONS]

    # -------------------------------------------------------------- handlerها
    def _post_route(self, ctx: _Ctx) -> tuple[int, Any]:
        return self.service.submit(parse_route_request(ctx.body))

    def _delete_route(self, ctx: _Ctx) -> tuple[int, Any]:
        self.service.delete_route(ctx.params["routeId"])
        return 204, None

    def _altitude(self, ctx: _Ctx) -> float:
        try:
            alt = float(ctx.params["altitudeM"])
        except ValueError:
            raise ValidationFailed([("altitudeM", "must be a number")]) from None
        if not self.provider.has_layer(alt):
            raise NotFound(f"No wind layer at altitude {alt:g} m; available: {list(self.provider.altitudes)}")
        return alt

    def _get_point(self, ctx: _Ctx) -> tuple[int, Any]:
        self.provider._require_data()
        alt = self._altitude(ctx)
        lat, lon = _lat_lon(ctx.query)
        return 200, self.provider.sample(alt, lat, lon)

    def _get_point_all(self, ctx: _Ctx) -> tuple[int, Any]:
        lat, lon = _lat_lon(ctx.query)
        return 200, self.provider.sample_all(lat, lon)

    def _get_field(self, ctx: _Ctx) -> tuple[int, Any]:
        self.provider._require_data()
        alt = self._altitude(ctx)
        issues: list[tuple[str, str]] = []
        bbox = None
        if "bbox" in ctx.query:
            try:
                bbox = [float(x) for x in ctx.query["bbox"].split(",")]
                if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                    raise ValueError
            except ValueError:
                issues.append(("bbox", "must be 'min_lon,min_lat,max_lon,max_lat' with min < max"))
        res = 0.05
        if "resolutionDeg" in ctx.query:
            try:
                res = float(ctx.query["resolutionDeg"])
                if not (math.isfinite(res) and res > 0):
                    raise ValueError
            except ValueError:
                issues.append(("resolutionDeg", "must be a positive number"))
        if issues:
            raise ValidationFailed(issues)
        try:
            return 200, self.provider.field(alt, bbox, res)
        except ValueError as exc:
            raise ValidationFailed([("resolutionDeg", str(exc))]) from None

    # --------------------------------------------------------------- هسته
    def handle(self, method: str, target: str, body: bytes = b"") -> tuple[int, dict[str, str], bytes]:
        """یک درخواست HTTP را پردازش می‌کند: ``(status, headers, body_bytes)``."""
        request_id = uuid.uuid4().hex[:12]
        headers = {
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
        try:
            status, payload = self._dispatch(method.upper(), target, body)
        except ApiError as exc:
            status, payload = exc.status, exc.to_body(request_id)
        except Exception:  # noqa: BLE001 - هرگز stack trace به کلاینت نمی‌دهیم
            status = 500
            payload = {
                "code": "internal_error",
                "message": "Unexpected server error.",
                "request_id": request_id,
            }
        raw = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        return status, headers, raw

    def _dispatch(self, method: str, target: str, body: bytes) -> tuple[int, Any]:
        if method == "OPTIONS":
            return 204, None
        parts = urlsplit(target)
        path = unquote(parts.path)
        if not path.startswith(API_PREFIX + "/"):
            raise ApiError("Not found.", code="not_found", status=404)
        path = path[len(API_PREFIX) :].rstrip("/") or "/"
        query = {k: v[-1] for k, v in parse_qs(parts.query).items()}

        allowed: list[str] = []
        for m, template, rx, handler in self._routes:
            match = rx.match(path)
            if not match:
                continue
            if m != method:
                allowed.append(m)
                continue
            names = re.findall(r"\{([^/}]+)\}", template)
            params = dict(zip(names, match.groups(), strict=False))
            payload = _parse_body(body) if method == "POST" else None
            return handler(_Ctx(params, query, payload))
        for m, rx in self._deferred:
            if rx.match(path):
                if m == method:
                    raise ApiError(
                        "This endpoint (auth/account/favorites) is not implemented yet.",
                        code="not_implemented",
                        status=501,
                    )
                allowed.append(m)
        if allowed:
            raise ApiError("Method not allowed.", code="method_not_allowed", status=405)
        raise ApiError("Not found.", code="not_found", status=404)

    def close(self) -> None:
        self.service.shutdown()


def _parse_body(body: bytes) -> Any:
    if len(body) > MAX_BODY_BYTES:
        raise ApiError("Request body too large.", code="payload_too_large", status=413)
    if not body.strip():
        raise ApiError("Request body is required.", code="invalid_json", status=400)
    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ApiError("Request body is not valid JSON.", code="invalid_json", status=400) from None


def serve(host: str = "127.0.0.1", port: int = 8000, provider: WindDataProvider | None = None):
    """سرور توسعه را می‌سازد (``serve_forever`` را خود فراخواننده صدا می‌زند)."""
    app = ApiApp(provider or WindDataProvider.from_csv())

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(min(length, MAX_BODY_BYTES + 1)) if length else b""
            status, headers, raw = app.handle(method, self.path, body)
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            self._respond("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._respond("POST")

        def do_DELETE(self) -> None:  # noqa: N802
            self._respond("DELETE")

        def do_PATCH(self) -> None:  # noqa: N802
            self._respond("PATCH")

        def do_PUT(self) -> None:  # noqa: N802
            self._respond("PUT")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._respond("OPTIONS")

        def log_message(self, *args) -> None:  # سکوت لاگ پیش‌فرض
            return

    server = ThreadingHTTPServer((host, port), Handler)
    server.app = app  # type: ignore[attr-defined]
    return server
