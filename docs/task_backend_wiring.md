# لایه بک‌اند و اتصال دکمه‌ها (Backend Layer & Button Wiring)

ClickUp: `86bc860cr` — وابسته به `86bc860cq` (قرارداد `api/openapi.yaml` و `docs/frontend/architecture.md`).

## معماری

```
UI (React) ──HTTP /v1──▶ backend.app.ApiApp ──▶ backend.service.RoutingService ──▶ pathfinding (A* / Dijkstra)
     │                        │  اعتبارسنجی: backend.schemas          ▲
     │                        └─ خطاها: backend.errors               │
     └─ اکشن‌ها ▶ backend.session.RoutingSession ─▶ (همان سرویس)   backend.provider.WindDataProvider ◀── data/*.csv
                          رویدادها: backend.events.EventBus
```

| ماژول | نقش |
|---|---|
| `schemas.py` | اعتبارسنجی `RouteRequest` (مختصات، قیدها، الگوریتم، معیار، وزن‌ها) |
| `provider.py` | داده واقعی ایستگاه‌ها → گراف چندلایه (کش بر اساس معیار/وزن)، نمونه‌برداری IDW، میدان برداری |
| `service.py` | فراخوانی موتور، اعمال قیدها، مقایسه لایه‌ها، ذخیره مسیر، jobهای async |
| `session.py` | مدیریت حالت UI؛ هر کنترل یک اکشن نام‌دار |
| `events.py` | `route.queued/running/succeeded/failed` و `state.changed` |
| `app.py` | endpointهای OpenAPI روی کتابخانه استاندارد (بدون وابستگی جدید) |
| `wiring.py` | جدول کنترل UI ← اکشن ← endpoint و `verify_wiring()` |

اجرا: `python -m backend --port 8000` (پایه: `http://localhost:8000/v1`).

## اتصال پارامترها به موتور

| ورودی UI | رفتار در موتور |
|---|---|
| مبدأ/مقصد/checkpoint | نزدیک‌ترین گره ایستگاه (snap)؛ مسیر از همه waypointها به ترتیب `order` می‌گذرد |
| الگوریتم | `a_star` یا `dijkstra` |
| معیار / وزن‌ها | `time` / `energy` / `balanced` (وزن `time+energy=1`)؛ گراف مربوط ساخته و کش می‌شود |
| حالت لایه | `auto`: بهترین لایه؛ `manual`: فقط `altitude_m` |
| `altitude_range_m` | فقط لایه‌های داخل بازه |
| `max_wind_speed_mps` | گره‌های با باد بیشتر حذف می‌شوند |
| `avoid_zones` (دایره) | گره‌های داخل دایره و یال‌هایی که از دایره می‌گذرند حذف می‌شوند |
| `async: true` | پاسخ `202` + `poll_url`؛ وضعیت و درصد پیشرفت با `GET /routes/jobs/{id}` |

## مدیریت خطا

`422 validation_error` (با `details[{field,issue}]`)، `422 no_feasible_path`، `404 not_found`،
`400 invalid_json`، `413 payload_too_large`، `405`، `501 not_implemented`،
`503 wind_data_unavailable` (نبود داده/فایل)، `500 internal_error` (بدون stack trace).
هر پاسخ `request_id` دارد.

## محدودیت‌ها و کارهای باقی‌مانده

- **خارج از دامنه (پاسخ 501):** favorites، auth، me — نیازمند پایگاه داده و JWT؛ تسک جدا لازم است.
- **FastAPI:** طبق AGENTS.md وابستگی جدید بدون تأیید Arman ممکن نیست؛ قرارداد HTTP یکسان است و جایگزینی بعدی بدون تغییر UI ممکن است.
- **WebSocket:** `websocket_url` در OpenAPI پیاده نشده؛ UI فعلاً با polling روی job پیشرفت را می‌گیرد (رویدادها درون‌فرایندی‌اند).
- **Rate limiting (429):** پیاده نشده.
- **مقایسه لایه‌ها:** `compare-layers` هم شناسه job و هم شناسه route را می‌پذیرد (مسیر sync شناسه job ندارد).
- **موتور:** این PR روی موتور موجود در شاخه `task/ui-foundation` (PR #20/#21) ساخته شده است.
  `main` فعلاً `cost.py` ندارد و import موتور در آن می‌شکند؛ پس از اصلاح، فقط از API پایدار
  (`build_from_dataframe`, `get_layer`, `a_star`, `dijkstra`) استفاده می‌شود.
- داده لایه‌های ارتفاعی با مقیاس مستند‌شده از داده سطحی واقعی ساخته می‌شود (همان رویکرد e2e موجود).
