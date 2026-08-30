# درونیابی پیشرفته Kriging — گام ۲

**تاریخ:** [Persian Date]  
**مسئول:** آرمان احمدی  
**وضعیت:** در انتظار پیادهسازی  
**تسک ClickUp:** [Task ID/URL]  
**اولویت:** High  
**ددلاین:** [Persian Date, 17:00 Iran Time]

---

## خلاصه پیادهسازی

پیادهسازی درونیابی Kriging (Ordinary Kriging) برای برآورد احتمالاتی و بهینه دادههای باد. برخلاف IDW، Kriging واریوگرام را مدلسازی کرده و خطای برآورد را به حداقل میرساند.

---

## چکلیست تسک (Items to Check)

| آیتم | وضعیت | توضیحات |
|------|--------|-----------|
| **۱.** طراحی کلاس KrigingInterpolator | ☐ انتظار | واریوگرام، مدل واریوگرام (spherical/exponential/gaussian) |
| **۲.** محاسبه و برازش واریوگرام تجربی | ☐ انتظار | باندها، لگ‌ها، برازش مدل |
| **۳.** پیادهسازی Ordinary Kriging system | ☐ انتظار | حل دستگاه معادلات خطی برای وزنها |
| **۴.** متد interpolate برای نقاط تکی و شبکه | ☐ انتظار | با محاسبه واریانس برآورد (Kriging variance) |
| **۵.** مقایسه با IDW و اعتبارسنجی | ☐ انتظار | Cross-validation، RMSE |
| **۶.** مستندات کامل با مثال | ☐ انتظار | در docs/task_kriging_interpolation.md |

---

## خروجیهای تولیدشده

### ۱. کد پیادهسازی
- فایل: `src/preprocessing/kriging.py`
- کلاس: `KrigingInterpolator`
- پارامترها:
  - `variogram_model: str = "spherical"` — spherical, exponential, gaussian
  - `nugget: float = 0.0` — اثر نوگت
  - `sill: float | None = None` — سیل (برآورد میشود)
  - `range: float | None = None` — برد واریوگرام

### ۲. تستها
- فایل: `tests/preprocessing/test_kriging.py`
- پوشش:
  - محاسبه واریوگرام تجربی
  - برازش مدل واریوگرام
  - درونیابی Kriging
  - محاسبه واریانس برآورد
  - Cross-validation

### ۳. مستندات
- فایل: `docs/task_kriging_interpolation.md`

---

## وابستگیها

- **پیشنیاز:** IDW Interpolation (برای مقایسه)، WindDataCache
- **وابسته به:** Data Prep for Pathfinding

---

## نکات فنی

- استفاده از `scipy.optimize` برای برازش واریوگرام
- حل دستگاه خطی: `scipy.linalg.solve`
- واریانس برآورد برای عدم قطعیت
- عملکرد بهتر در دادههای پراکنده با همبستگی مکانی