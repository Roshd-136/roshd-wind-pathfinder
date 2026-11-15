"""درصد پیشرفت واقعی مسیریابی — رفع کامنت ۱۲ «کامنت‌های نرم‌افزار».

رگرسیون واقعی: حالت ناهمگام فقط «کارِ پذیرفتهشده» برمی‌گرداند و هیچ اجرایی
در کار نبود — وضعیت برای همیشه ``pending`` و ``progress`` برای همیشه ``۰``
بود، پس کلاینت هرگز درصد پیشرفت واقعی نداشت. این آزمونها قفل میکنند که:

۱. کار ناهمگام واقعاً در پسزمینه اجرا و کامل میشود (``progress=100`` + نتیجه)؛
۲. نقاط عطفِ پیشرفت صعودیاند (۵٪ آغاز، گزارش هر قطعه، ۹۵٪ پیش از نتیجه)؛
۳. خطای موتور (پیام فارسی) به ``status=failed`` + ``error`` کار میرسد تا
   کلاینتِ polling همان را نشان دهد، نه ۵۰۰ یا سکوت.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# دالان آزمایشی پروژه — مشهد به سبزوار (همان جفتِ ROADMAP).
ROUTE_BODY = {
    "origin": {"lat": 36.297, "lon": 59.606},
    "destination": {"lat": 36.215, "lon": 57.678},
}


def test_async_job_completes_with_real_progress() -> None:
    """کار ناهمگام کامل میشود: progress=100 و نتیجهٔ واقعی مسیر."""
    response = client.post("/v1/routes", json={**ROUTE_BODY, "async": True})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"

    job = client.get(f"/v1/routes/jobs/{body['job_id']}").json()
    assert job["status"] == "completed"
    assert job["progress"] == 100
    result = job["result"]
    assert result is not None
    # دالان مشهد→سبزوار — خط مستقیم حدود ۱۶۵ ک.م است
    assert result["total_distance_km"] > 100


def test_progress_milestones_are_ascending() -> None:
    """نقاط عطف: ۵٪ آغاز، گزارش هر قطعه، ۹۵٪ پیش از ساخت نتیجه."""
    from api.routers.routes import RouteRequest, compute_route_sync

    seen: list[int] = []
    request = RouteRequest(**ROUTE_BODY)
    result = compute_route_sync(request, report=seen.append)
    assert seen[0] == 5
    assert seen[-1] == 95
    assert seen == sorted(seen)
    assert result.total_distance_km > 100


def test_failed_job_carries_persian_engine_error() -> None:
    """خطای موتور → status=failed با پیام فارسی، نه ۵۰۰ یا سکوت.

    همهٔ نقاط در کمتر از یک کیلومترند — هیچ قطعهای مسیریابی نمیشود و
    موتور با پیام «نقاط بسیار نزدیک» شکست میدهد (سریع و قطعی).
    """
    body = {
        "origin": {"lat": 36.297, "lon": 59.606},
        "destination": {"lat": 36.298, "lon": 59.607},
        "checkpoints": [{"lat": 36.2975, "lon": 59.6065}],
        "async": True,
    }
    job_id = client.post("/v1/routes", json=body).json()["job_id"]
    job = client.get(f"/v1/routes/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "بسیار نزدیک" in (job["error"] or "")
    assert job["result"] is None
    assert job["progress"] is None or job["progress"] < 100
