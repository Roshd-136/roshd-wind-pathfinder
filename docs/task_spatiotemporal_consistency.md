# پیوستگی مکانی-زمانی (Spatiotemporal Consistency) — گام ۲

**تاریخ:** [Persian Date]  
**مسئول:** امیرعلی  
**وضعیت:** در انتظار پیادهسازی  
**تسک ClickUp:** [Task ID/URL]  
**اولویت:** Normal  
**ددلاین:** [Persian Date, 17:00 Iran Time]

---

## خلاصه پیادهسازی

بررسی و اطمینان از پیوستگی دادههای باد در ابعاد مکانی (شبکه جغرافیایی) و زمانی (سری‌های زمانی). شناسایی شکاف‌ها، پر کردن با استراتژی مناسب، و اعتبارسنجی همبستگی.

---

## چکلیست تسک (Items to Check)

| آیتم | وضعیت | توضیحات |
|------|--------|-----------|
| **۱.** بررسی 網格 مکانی (grid coverage) | ☐ انتظار | پوشش کامل منطقه هدف |
| **۲.** بررسی سری زمانی (temporal gaps) | ☐ انتظار | فواصل زمانی ثابت، گمشدگی ساعت‌ها |
| **۳.** همبستگی مکانی (Moran's I / variogram) | ☐ انتظار | سنجش خودهمبستگی مکانی |
| **۴.** همبستگی خودهمبستگی زمانی (ACF/PACF) | ☐ انتظار | الگوهای روزانه/فصلی |
| **۵.** استراتژی پر کردن شکاف‌ها | ☐ انتظار | تکرار، درونیابی، مدل‌سازی |
| **۶.** تست و مستندات | ☐ انتظار | در docs/task_spatiotemporal_consistency.md |

---

## خروجیهای تولیدشده

### ۱. کد پیادهسازی
- فایل: `src/preprocessing/consistency.py`
- توابع:
  - `check_spatial_coverage(data, grid_spec)` — پوشش مکانی
  - `check_temporal_continuity(data, freq="1H")` — پیوستگی زمانی
  - `compute_spatial_autocorrelation(data)` — همبستگی مکانی
  - `compute_temporal_autocorrelation(data)` — خودهمبستگی زمانی
  - `fill_gaps(data, strategy="interpolate")` — پر کردن شکاف

### ۲. تستها
- فایل: `tests/preprocessing/test_consistency.py`
- پوشش:
  - تست پوشش مکانی
  - تست پیوستگی زمانی
  - تست همبستگی مکانی/زمانی
  - تست پر کردن شکاف

### ۳. مستندات
- فایل: `docs/task_spatiotemporal_consistency.md`

---

## وابستگیها

- **پیشنیاز:** Wind Data QC (داده پاکسازی شده)
- **وابسته به:** Data Prep for Pathfinding

---

## نکات فنی

- استفاده از `scipy.stats` برای ACF/PACF
- `pysal` یا `scipy.spatial` برای Moran's I
- Grid specification: lat/lon bounds + resolution