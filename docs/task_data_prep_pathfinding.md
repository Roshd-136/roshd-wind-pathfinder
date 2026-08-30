# آماده‌سازی داده برای مسیریابی (Data Prep for Pathfinding) — گام ۲

**تاریخ:** [Persian Date]  
**مسئول:** مهدی  
**وضعیت:** در انتظار پیادهسازی  
**تسک ClickUp:** [Task ID/URL]  
**اولویت:** High  
**ددلاین:** [Persian Date, 17:00 Iran Time]

---

## خلاصه پیادهسازی

تبدیل دادههای پیشپردازش شده (QC، درونیابی، پیوستگی) به فرمت مناسب برای الگوریتم‌های مسیریابی. شامل ساخت گراف بادی، نرمالسازی، و تولید فایل‌های ورودی مسیریاب.

---

## چکلیست تسک (Items to Check)

| آیتم | وضعیت | توضیحات |
|------|--------|-----------|
| **۱.** ساخت گراف از نقاط داده (nodes + edges) | ☐ انتظار | گره‌ها: نقاط شبکه، یال‌ها: مجاورت |
| **۲.** محاسبه وزن یال‌ها بر اساس باد | ☐ انتظار | هزینه = فاصله / سرعت موثر باد |
| **۳.** نرمالسازی مؤلفه‌های u/v برای مسیریابی | ☐ انتظار | مقیاس یکسان برای الگوریتم |
| **۴.** صادرات به فرمت‌های گراف (GraphML, JSON, pickle) | ☐ انتظار | سازگار با NetworkX |
| **۵.** تولید داده pathfinding_ready.csv | ☐ انتظار | شامل u_normalized, v_normalized |
| **۶.** تست و مستندات | ☐ انتظار | در docs/task_data_prep_pathfinding.md |

---

## خروجیهای تولیدشده

### ۱. کد پیادهسازی
- فایل: `src/preprocessing/data_prep.py`
- توابع:
  - `build_wind_graph(data, grid_resolution)` — ساخت گراف
  - `compute_edge_weights(graph, u_field, v_field)` — وزن یال‌ها
  - `normalize_components(u, v)` — نرمالسازی
  - `export_graph(graph, format="graphml")` — صادرات

### ۲. تستها
- فایل: `tests/preprocessing/test_data_prep.py`
- پوشش:
  - ساخت گراف
  - محاسبه وزن
  - نرمالسازی
  - صادرات فرمت‌ها

### ۳. مستندات
- فایل: `docs/task_data_prep_pathfinding.md`

---

## وابستگیها

- **پیشنیاز:** Spatiotemporal Consistency، IDW/Kriging Interpolation
- **وابسته به:** Pathfinding (گام ۳)

---

## نکات فنی

- استفاده از `networkx` برای گراف
- وزن یال: `cost = distance / (1 + wind_assist)` — کمکی باد
- نودها: مختصات (lat, lon, altitude) + داده باد
- خروجی: `khorasan_pathfinding_ready.csv` (نمونه موجود در data/)