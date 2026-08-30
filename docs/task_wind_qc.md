# کنترل کیفیت دادههای باد (Wind Data QC) — گام ۲

**تاریخ:** [Persian Date]  
**مسئول:** مهدی  
**وضعیت:** در انتظار پیادهسازی  
**تسک ClickUp:** [Task ID/URL]  
**اولویت:** High  
**ددلاین:** [Persian Date, 17:00 Iran Time]

---

## خلاصه پیادهسازی

پیادهسازی ماژول کنترل کیفیت (Quality Control) برای دادههای باد خام. شامل اعتبارسنجی بازه، تشخیص ناهنجاری، حذف/جایگزینی مقادیر نامعتبر، و گزارش‌گیری.

---

## چکلیست تسک (Items to Check)

| آیتم | وضعیت | توضیحات |
|------|--------|-----------|
| **۱.** اعتبارسنجی بازه‌های فیزیکی (speed، direction، u، v) | ☐ انتظار | speed: 0-100 m/s، direction: 0-360° |
| **۲.** تشخیص ناهنجاری آماری (Z-score، IQR) | ☐ انتظار | با آستانه قابل تنظیم |
| **۳.** مدیریت دادههای گمشده (interpolation/forward-fill) | ☐ انتظار | استراتژی قابل انتخاب |
| **۴.** حذف/جایگزینی رکوردهای نامعتبر | ☐ انتظار | با لاگ و گزارش |
| **۵.** تولید گزارش QC (JSON) | ☐ انتظار | total، valid، removed، removal_rate |
| **۶.** تست واحد و مستندات | ☐ انتظار | در docs/task_wind_qc.md |

---

## خروجیهای تولیدشده

### ۱. کد پیادهسازی
- فایل: `src/preprocessing/qc.py`
- کلاس: `WindDataQC`
- توابع:
  - `validate_range(data)` — بازه فیزیکی
  - `detect_outliers(data, method="zscore", threshold=3.0)` — ناهنجاری
  - `clean_data(data, strategy="interpolate")` — پاکسازی
  - `generate_report(data_before, data_after)` — گزارش JSON

### ۲. تستها
- فایل: `tests/preprocessing/test_qc.py`
- پوشش:
  - اعتبارسنجی بازه
  - تشخیص ناهنجاری (Z-score، IQR)
  - استراتژی‌های پاکسازی
  - گزارش‌گیری

### ۳. مستندات
- فایل: `docs/task_wind_qc.md`

---

## وابستگیها

- **پیشنیاز:** WindDataCache (داده خام)
- **وابسته به:** Spatiotemporal Consistency، IDW/Kriging Interpolation

---

## نکات فنی

- داده ورودی: DataFrame با ستون‌های timestamp, lat, lon, speed, direction, u, v
- حفظ timestamp برای پیوستگی زمانی
- گزارش QC ذخیره می‌شود برای ردیابی