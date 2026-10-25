"""قرارداد هم‌ترازی لایه‌های باد: پیکربندی فرانت ↔ سطوح پرواز بک‌اند ↔ فیکسچر dev.

رگرسیون واقعی: باندهای نمایش باد فرانت‌اند به سطوح پرواز MSL تغییر کردند ولی
فیکسچرهای ``frontend/public/mock`` بازتولید نشدند. واکشی هر لایه در حالت dev
به صفحهٔ HTML (fallback اپ) می‌خورد و ``response.json()`` سقوط می‌کرد، پس
``useWindFields`` هیچ میدانی برنمی‌گرداند — لایهٔ پیکان‌های باد و راهنمای سرعت
از نقشه ناپدید می‌شدند. این آزمون آن هم‌ترازی را قفل می‌کند.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from viz.wind_field import FLIGHT_LEVELS_MSL

ROOT = Path(__file__).resolve().parents[1]
MOCK_DIR = ROOT / "frontend" / "public" / "mock"
ROUTING_CONFIG = ROOT / "frontend" / "src" / "config" / "routing.ts"


def _frontend_band_altitudes() -> list[float]:
    """ارتفاع میدان هر باند نمایش را از پیکربندی تایپ‌اسکریپت فرانت می‌خواند."""
    text = ROUTING_CONFIG.read_text(encoding="utf-8")
    values = [float(m) for m in re.findall(r"fieldAltitude:\s*([0-9.]+)", text)]
    assert values, "no `fieldAltitude` entries found in frontend routing config"
    return values


def test_frontend_bands_match_backend_flight_levels() -> None:
    """باندهای نمایش فرانت باید دقیقاً سطوح پرواز بک‌اند باشند (با همان ترتیب)."""
    backend_levels = [float(level) for level in FLIGHT_LEVELS_MSL]
    assert _frontend_band_altitudes() == backend_levels


@pytest.mark.parametrize("level", FLIGHT_LEVELS_MSL)
def test_wind_field_fixture_exists_for_each_flight_level(level: float) -> None:
    """برای هر سطح پرواز یک فیکسچر بادِ dev با همان ارتفاع لازم است."""
    path = MOCK_DIR / f"wind-field-{int(level)}.json"
    assert path.exists(), f"missing dev wind fixture: {path.name}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["altitude_m"] == float(level)
    assert payload["vectors"], "wind fixture has no vectors"


def test_wind_layers_fixture_lists_flight_levels() -> None:
    """خروجی ``GET /wind-layers`` فیکسچر همان سطوح پرواز را اعلام کند."""
    payload = json.loads((MOCK_DIR / "wind-layers.json").read_text(encoding="utf-8"))
    altitudes = sorted(entry["altitude_m"] for entry in payload)
    assert altitudes == sorted(float(level) for level in FLIGHT_LEVELS_MSL)
