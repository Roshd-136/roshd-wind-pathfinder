"""تازگی دادههای باد — رفع کامنت ۱۰ «کامنت‌های نرم‌افزار».

کاربر: «داده‌ها را از چند ساعت پیش استفاده می‌کند؛ بهتر است بنویسد داده‌ها
از چند ساعت پیش است.» فرانت برای بنرِ «داده‌های باد مربوط به X روز پیش»
روی ``data_age_hours`` پاسخ ``GET /wind-layers`` تکیه میکند — سن در
بک‌اند و در همان قابِ مهرِ CSV (بدون منطقهٔ زمانی) حساب میشود تا هیچ
فرضِ بی‌مبنای timezone‌ای ساخته نشود (بیشترین خطای ممکن ±۳٫۵ ساعت است که
در مقیاس «چند روز پیش» بیاثر).
"""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_wind_layers_expose_data_age() -> None:
    """data_age_hours عدد صحیح >= 0 است و مهر لایهها قابل‌پارس."""
    response = client.get("/v1/wind-layers")
    assert response.status_code == 200
    body = response.json()
    layers = body["layers"]
    assert layers, "no wind layers returned"

    age = body["data_age_hours"]
    assert isinstance(age, int)
    assert age >= 0

    # مهر زمانی مشاهدات — قابل‌پارس (حتی بدون منطقهٔ زمانی)
    datetime.fromisoformat(body["latest_timestamp"])
    for layer in layers:
        datetime.fromisoformat(layer["timestamp"])


def test_data_age_matches_recorded_hour() -> None:
    """عمر حسابشده با فاصلهٔ مهر CSV تا الان همخوان است (±۳٫۵ ساعت گرانش)."""
    from pathlib import Path

    import pandas as pd

    from viz.wind_field import select_scene_hour

    root = Path(__file__).resolve().parents[2]
    raw = pd.read_csv(root / "data" / "iran_wind_qc_cleaned.csv")
    hour = select_scene_hour(raw)

    body = client.get("/v1/wind-layers").json()
    expected = int((pd.Timestamp.now() - hour).total_seconds() // 3600)
    assert abs(body["data_age_hours"] - max(0, expected)) <= 1
