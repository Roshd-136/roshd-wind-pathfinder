"""پیام‌های خطای گویا — رفع کامنت ۱۳ «کامنت‌های نرم‌افزار».

رگرسیون واقعی: کاربر دو خطای خام می‌دید و علت را نمی‌شناخت —
``Wind riding route could not be planned`` (ValueError خام موتور) و
``Input should be less than or equal to 180`` (پیام انگلیسیِ Pydantic روی
دامنهٔ طول جغرافیایی). این آزمون‌ها قفل می‌کنند که:

۱. خطای دامنهٔ عرض/طول جغرافیایی پیام فارسیِ خوانا با ذکر مقدار واردشده بدهد؛
۲. ساختار استاندارد ۴۲۲ (فهرستِ ``detail`` با ``loc``/``type``) نشکند و
   پیام خطاهای بی‌ربط دست‌نخورده بماند؛
۳. ``ValueError`` موتور ۴۰۰ با متنِ خود موتور برگرداند (نه ۵۰۰).
"""

from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient
from starlette.requests import Request

from api.main import app, validation_error_handler, value_error_handler

client = TestClient(app)

# دالان آزمایشی پروژه — مشهد به سبزوار (همان جفتِ ROADMAP).
ROUTE_BODY = {
    "origin": {"lat": 36.297, "lon": 59.606},
    "destination": {"lat": 36.215, "lon": 57.678},
}


def _post_route(**overrides: object):
    body = {**ROUTE_BODY, **overrides}
    return client.post("/v1/routes", json=body)


def test_lon_out_of_range_gets_persian_message() -> None:
    """طول جغرافیایی بیرون از بازه — پیام فارسیِ خوانا با همان ساختار ۴۲۲."""
    response = _post_route(origin={"lat": 36.297, "lon": 241.0})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list) and detail
    first = detail[0]
    assert "طول جغرافیایی" in first["msg"]
    assert "241" in first["msg"]
    assert "ترتیب عرض/طول" in first["msg"]
    # ساختار استاندارد FastAPI حفظ شده تا کلاینت‌ها نشکنند.
    assert first["type"] == "less_than_equal"
    assert first["loc"][-1] == "lon"


def test_lat_out_of_range_gets_persian_message() -> None:
    """عرض جغرافیایی بیرون از بازه — همان رفتار، برای lat."""
    response = _post_route(origin={"lat": 99.0, "lon": 59.606})
    assert response.status_code == 422
    first = response.json()["detail"][0]
    assert "عرض جغرافیایی" in first["msg"]
    assert "99" in first["msg"]
    assert first["loc"][-1] == "lat"


def test_unrelated_validation_keeps_standard_shape() -> None:
    """خطای بی‌ربط با مختصات — پیام استاندارد Pydantic دست‌نخورده بماند."""
    response = _post_route(checkpoints=[{"order": 1}])  # lat/lon چک‌پوینت غایب
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list) and detail
    assert any(entry["msg"] == "Field required" for entry in detail)


def test_value_error_becomes_400_with_engine_message() -> None:
    """ValueError موتور مسیریابی ۴۰۰ با متنِ خودِ موتور برگرداند، نه ۵۰۰."""
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    response = asyncio.run(
        value_error_handler(
            Request(scope),
            ValueError("در این باند مسیر پروازپذیری نیست"),
        )
    )
    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "در این باند مسیر پروازپذیری نیست"
    }


def test_validation_handler_translates_only_coordinate_errors() -> None:
    """ترجمهٔ پیام فقط برای lat/lon؛ سایر خطاها در خروجی دست‌نخورده."""
    from fastapi.exceptions import RequestValidationError

    exc = RequestValidationError(
        [
            {"type": "less_than_equal", "loc": ("body", "origin", "lon"),
             "msg": "Input should be less than or equal to 180", "input": 241.0},
            {"type": "missing", "loc": ("body", "destination"),
             "msg": "Field required", "input": None},
        ]
    )
    response = asyncio.run(
        validation_error_handler(Request({"type": "http", "headers": []}), exc)
    )
    detail = json.loads(response.body)["detail"]
    assert response.status_code == 422
    assert "طول جغرافیایی" in detail[0]["msg"]
    assert detail[1]["msg"] == "Field required"
