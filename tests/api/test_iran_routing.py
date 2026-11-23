"""مسیریابی سراسری — دیگر مبدأ/مقصد خارج از خراسان نباید به دالان بچسبد.

پیش از این گراف فقط روی ``CORRIDOR_BBOX`` (مشهد–سبزوار) ساخته میشد؛ هر
درخواست خارج از آن به نزدیکترین گرهٔ شرقی اسنپ میشد و مسیر تهران→اصفهان
از کنار مشهد میگذشت. این آزمون قفل میکند که مسیر درون کادر خودش بماند.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_route_outside_khorasan_stays_in_its_own_region() -> None:
    """تهران→اصفهان نباید از طولِ دالان مشهد–سبزوار (>۵۷°) عبور کند."""
    response = client.post(
        "/v1/routes",
        json={
            "origin": {"lat": 35.6892, "lon": 51.389},
            "destination": {"lat": 32.4279, "lon": 53.688},
        },
    )
    assert response.status_code == 200, response.text
    path = response.json()["path"]
    assert path, "مسیر خالی است"
    assert max(point["lon"] for point in path) < 56.0
    assert min(point["lon"] for point in path) >= 51.0
    assert min(point["lat"] for point in path) >= 32.0
    assert max(point["lat"] for point in path) <= 36.5
