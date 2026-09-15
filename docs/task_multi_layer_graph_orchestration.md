# گراف باد چندلایه و لایه ارکستراسیون نهایی — Schema و معماری

**تاریخ:** ۲۴ شهریور ۱۴۰۵
**مسئول:** امیرعلی
**وضعیت:** انجام شده
**اولویت:** بالا (High)
**ددلاین:** ۲۳ شهریور ۱۴۰۵، ۲۰:۰۰ به وقت ایران
**برچسب:** گام ۳

---

> **زمینه مهم (باید قبل از خواندن بقیه سند در نظر گرفته شود):** این دقیقاً
> همان تسکی است که آرمان (owner) یک‌بار با عنوان یکسان در PR #19 پیاده‌سازی
> و merge کرد، اما خودش ۴ دقیقه بعد بدون توضیح revert کرد. محتوای عملاً
> معادل آن (ساخت `WindGraph`/`MultiLayerWindGraph` در `graph.py` و
> `WindRouter` در `routing.py`) بعداً زیر یک تسک ClickUp **متفاوت**
> (`86bbw32kw`، تسک الگوریتم‌ها) در PR #20 دوباره نوشته و merge شد و الان
> روی `main` است. این سند، مستندسازی رسمی schema/معماری همان کد را — که تا
> امروز به‌عنوان یک فایل مستقل وجود نداشت — کامل می‌کند و شکاف‌های باقی‌مانده
> (تست‌های end-to-end و همین سند) را می‌بندد؛ کد `graph.py`/`routing.py` را
> از نو پیاده‌سازی نکرده است تا کار تکراری/متناقض تولید نشود.

---

## چک‌لیست تسک (Items to Check)

| # | آیتم | وضعیت | جزئیات |
|---|------|--------|--------|
| ۱ | گراف باد برای همه لایه‌های جوی موجود ساخته شود | ✅ | `MultiLayerWindGraph` (از قبل، PR #20) |
| ۲ | لیست تمام لایه‌های موجود قابل دریافت باشد | ✅ | `available_layers` property (از قبل، PR #20) |
| ۳ | لایه ارکستراسیون مدل هزینه و الگوریتم‌ها را متصل کند | ✅ | `WindRouter` (از قبل، PR #20) |
| ۴ | مسیر بهینه با در نظر گرفتن لایه انتخابی محاسبه شود | ✅ | `WindRouter.find_optimal_path` (از قبل، PR #20) |
| ۵ | حداقل ۵ تست واحد + ۳ تست end-to-end، کل پوشه سبز | ✅ | ۱۱۱ تست واحد از قبل (PR #20) + **۳ تست end-to-end جدید** (این PR): `tests/pathfinding/test_end_to_end.py` — از خواندن فایل CSV واقعی تا خروجی نهایی مسیر |
| ۶ | Schema گراف و مستند معماری تهیه شود | ✅ | **همین سند** (تازه اضافه شد — قبلاً مفقود بود) |
| ۷ | جدول مقایسه زمان سفر روی لایه‌های مختلف | ✅ | `docs/task_routing_benchmark.md` (از قبل، PR #20) |

---

## Schema گراف

### `GraphNode` — گره
| فیلد | نوع | توضیح |
|---|---|---|
| `node_id` | `str` | شناسه یکتا، فرمت `"lat,lon"` |
| `lat`, `lon` | `float` | مختصات جغرافیایی (درجه) |
| `wind_speed_mps` | `float` | سرعت باد در این نقطه/لایه (m/s) |
| `wind_direction_deg` | `float` | جهت باد (درجه، قرارداد هواشناسی) |
| `altitude` | `float` | ارتفاع لایه (متر) |

### `EdgeData` — یال
| فیلد | نوع | توضیح |
|---|---|---|
| `distance_km` | `float` | فاصله haversine بین دو گره |
| `cost_result` | `EdgeCostResult \| None` | خروجی کامل `compute_edge_cost` (سرعت زمینی، زمان، انرژی) |
| `weight` | `float` | وزن نهایی یال طبق `criterion` انتخابی (`time`/`energy`/`balanced`) |

**نکته مهم فیزیکی:** وزن یال جهت‌دار است — `weight(A→B) != weight(B→A)`،
چون تأثیر باد موافق/مخالف به جهت حرکت بستگی دارد؛ این یک ویژگی صحیح مدل
است، نه باگ.

### `WindGraph` — گراف تک‌لایه
- ساخته می‌شود از `DataFrame` با ستون‌های `lat, lon, wind_speed, wind_direction` (یا نام‌های جایگزین `speed, direction`) برای یک `altitude` مشخص.
- یال بین هر دو گره‌ای ایجاد می‌شود که فاصله‌شان ≤ `max_edge_distance_km` (پیش‌فرض ۲۰۰ کیلومتر) باشد.
- وزن یال از `pathfinding.cost.compute_edge_cost` می‌آید (ماژول مستقل، PR #18).

### `MultiLayerWindGraph` — گراف چندلایه
- نگاشت `altitude → WindGraph`.
- `available_layers` → لیست مرتب ارتفاعات موجود.
- `layer_count` → تعداد لایه‌ها.
- `get_layer(altitude)` → دسترسی به گراف یک لایه مشخص.

```
MultiLayerWindGraph
├── 500m  → WindGraph(nodes=[Mashhad, Neyshabur, Sabzevar], edges=...)
├── 1000m → WindGraph(...)
├── 1500m → WindGraph(...)
└── 2000m → WindGraph(...)
```

---

## معماری لایه ارکستراسیون (`WindRouter`)

```
      origin, destination
             │
             ▼
   ┌─────────────────────┐
   │   WindRouter         │
   │  .find_optimal_path  │
   └─────────┬────────────┘
             │  for each altitude in multi_graph.available_layers:
             ▼
   ┌─────────────────────┐      ┌──────────────────────┐
   │ algorithms.a_star /  │◀────▶│  cost.compute_edge_   │
   │ algorithms.dijkstra  │      │  cost (وزن هر یال)    │
   └─────────┬────────────┘      └──────────────────────┘
             │  RouteResult (per layer)
             ▼
   ┌─────────────────────┐
   │  LayerComparison      │  → best_altitude, best_result,
   │  .to_comparison_table │     to_comparison_table()
   └─────────┬────────────┘
             ▼
        RouteResult نهایی
   (path, layer_altitude, total_distance_km,
    estimated_time_hours, total_cost, criterion)
```

جریان داده:
1. `WindRouter.compare_layers(origin, destination)` روی **هر** لایه موجود، نزدیک‌ترین گره به مبدأ/مقصد را پیدا می‌کند و `a_star`/`dijkstra` را روی گراف همان لایه اجرا می‌کند (وزن یال‌ها از قبل توسط `compute_edge_cost` هنگام ساخت گراف محاسبه شده).
2. نتیجه هر لایه در `LayerComparison.results[altitude]` ذخیره می‌شود.
3. لایه با کمترین هزینه به‌صورت خودکار به‌عنوان `best_altitude`/`best_result` انتخاب می‌شود.
4. `find_optimal_path` مستقیماً `best_result` را برمی‌گرداند؛ `compare_layers` جدول کامل مقایسه را هم می‌دهد.

هیچ placeholder یا mock در این زنجیره نیست: `compute_edge_cost` تابع واقعی
فیزیکی (تجزیه بردار باد، سرعت زمینی، هزینه زمان/انرژی) است، و `a_star`/`dijkstra`
پیاده‌سازی الگوریتمی واقعی روی گراف واقعی هستند.

---

## شواهد اجرا

```
$ ruff check .
All checks passed!

$ pytest
114 passed   (111 قبلی + ۳ تست end-to-end جدید)
```

## پیوست: کدها و مستندات مرتبط

- `src/pathfinding/graph.py` — `GraphNode`, `EdgeData`, `WindGraph`, `MultiLayerWindGraph`
- `src/pathfinding/routing.py` — `RouteResult`, `LayerComparison`, `WindRouter`
- `src/pathfinding/algorithms.py` — `a_star`, `dijkstra`
- `src/pathfinding/cost.py` — `compute_edge_cost` (مدل هزینه بادی، PR #18)
- `tests/pathfinding/test_graph.py`, `test_routing.py`, `test_algorithms.py`, `test_cost.py` — تست‌های واحد (از قبل)
- `tests/pathfinding/test_end_to_end.py` — **۳ تست end-to-end جدید (این تسک)**
- `docs/task_routing_benchmark.md` — جدول مقایسه زمان سفر لایه‌ها + بنچمارک A*/Dijkstra
- `docs/assets/pathfinding_best_layer_map.png`, `pathfinding_optimized_route.png` — تصویرسازی روی داده واقعی

## یافته باقی‌مانده برای تیم

فایل نمونه چندلایه واقعی `data/khorasan_pathfinding_ready.csv` هنوز تماماً
NaN است (نگاه کنید به `docs/preprocessing_report.md`، بخش ۱). به همین
دلیل، لایه‌های ارتفاعی بالاتر از ۵۰۰ متر در تست‌ها و بنچمارک‌ها با مقیاس‌دهی
مستند بر پایه داده واقعی سطحی ساخته شده‌اند، نه داده اندازه‌گیری‌شده واقعی
در ارتفاع. وقتی آن فایل با داده واقعی بازتولید شد، گراف‌های چندلایه باید
مستقیماً از آن ساخته شوند.
