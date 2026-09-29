"""فیکسچرهای مشترک تست‌های بک‌اند (ایستگاه‌های مصنوعی کوچک برای تست‌های منطقی)."""

import json

import pandas as pd
import pytest

from backend import ApiApp, EventBus, RoutingService, RoutingSession, WindDataProvider

# چهار ایستگاه روی یک خط؛ B با باد بسیار شدید (برای تست max_wind و avoid_zone)
STATIONS = pd.DataFrame(
    {
        "lat": [36.0, 36.0, 36.0, 36.0],
        "lon": [57.0, 58.0, 59.0, 60.0],
        "speed": [5.0, 20.0, 6.0, 7.0],
        "direction": [90.0, 90.0, 90.0, 90.0],
    }
)


@pytest.fixture()
def provider():
    return WindDataProvider(STATIONS.copy(), last_updated="2026-01-01T00:00:00+00:00")


@pytest.fixture()
def bus():
    return EventBus()


@pytest.fixture()
def service(provider, bus):
    svc = RoutingService(provider, bus)
    yield svc
    svc.shutdown()


@pytest.fixture()
def session(service):
    return RoutingSession(service)


@pytest.fixture()
def app(provider, bus):
    a = ApiApp(provider, bus)
    yield a
    a.close()


@pytest.fixture()
def call(app):
    def _call(method, path, body=None):
        raw = b"" if body is None else json.dumps(body).encode()
        status, headers, out = app.handle(method, path, raw)
        return status, (json.loads(out) if out else None), headers

    return _call


def pt(lon, lat=36.0):
    return {"lat": lat, "lon": lon}
