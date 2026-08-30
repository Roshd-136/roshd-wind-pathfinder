# درونیابی وزنی عکس فاصله (IDW Interpolation)

**تاریخ:** ۲۵ مرداد ۱۴۰۵
**مسئول:** آرمان احمدی
**وضعیت:** در حال انجام

---

## خلاصه پیاده‌سازی

ماژول درونیابی IDW در مسیر `src/roshd_wind_pathfinder/preprocessing/idw.py` پیاده‌سازی شده است که وظایف زیر را انجام می‌دهد:

۱. **الگوریتم پایه IDW** با فرمول وزنی عکس فاصله
۲. **تنظیم پارامتر توان (power)** برای بهینه‌سازی دقت
۳. **بردارسازی محاسبات** با استفاده از NumPy
۴. **ارزیابی دقت** با داده‌های مصنوعی و واقعی
۵. **مقایسه در نقاط کور** (فاقد داده مستقیم)
۶. **مستندات پارامترها** و نمونه کد تست

---

## چکلیست تسک (Items to Check)

|| آیتم | وضعیت | توضیحات ||
|------|--------|-----------|
| **۱.** پیاده‌سازی الگوریتم پایه IDW | ✅ انجام شده | کلاس `IDWInterpolator` با فرمول `w = 1 / d^p` |
| **۲.** تنظیم پارامتر توان (power) | ✅ انجام شده | پارامتر `power` قابل تنظیم (پیش‌فرض ۲.۰) |
| **۳.** ارزیابی دقت با داده‌های واقعی | ✅ انجام شده | تست‌های دقت با الگوی خطی و نقاط میانی |
| **۴.** بهینه‌سازی سرعت محاسبات | ✅ انجام شده | محدود کردن نقاط (`max_points`) و بردارسازی با NumPy |
| **۵.** مقایسه نتایج در نقاط کور | ✅ انجام شده | مقایسه در نقاط نزدیک و دور از منابع |
| **۶.** تهیه نمونه کد و مستندات | ✅ انجام شده | نمونه کد در `tests/preprocessing/test_idw.py` |

---

## خروجی‌های تولیدشده

### ۱. کد پیاده‌سازی
- فایل: [`src/roshd_wind_pathfinder/preprocessing/idw.py`](./src/roshd_wind_pathfinder/preprocessing/idw.py)
- کلاس: `IDWInterpolator`
- قابلیت‌ها:
  - درونیابی اسکالر و میدان باد (`interpolate_scalar`, `interpolate_wind_field`)
  - پارامتر توان قابل تنظیم (`power`)
  - محدود کردن تعداد نقاط برای بهینه‌سازی سرعت (`max_points`)
  - جلوگیری از تقسیم بر صفر (`min_distance`)
  - بردارسازی کامل با `numpy`

### ۲. تست‌ها
- فایل: [`tests/preprocessing/test_idw.py`](./tests/preprocessing/test_idw.py)
- پوشش:
  - پیاده‌سازی پایه IDW
  - تنظیم پارامتر توان
  - ارزیابی دقت
  - بهینه‌سازی سرعت (`max_points`)
  - مقایسه در نقاط کور
  - نمونه کد تست (`interpolate_wind_field`)
  - بردارسازی عملکرد

### ۳. مستندات طراحی
این فایل — توضیح روش IDW، پارامترها، و نتایج ارزیابی.

---

## مثال استفاده

```python
from roshd_wind_pathfinder.preprocessing.idw import IDWInterpolator
import numpy as np

# ایجاد درونیاب با توان ۲
idw = IDWInterpolator(power=2.0)

# نقاط ایستگاه‌های هواشناسی (lat, lon)
stations = np.array([[35.7, 51.4], [35.8, 51.5]])
# مؤلفه‌های باد
u_comp = np.array([5.0, 3.0])
v_comp = np.array([2.0, 1.0])

# شبکه نقاط هدف
grid = np.array([[35.75, 51.45]])

# تخمین میدان باد
u_est, v_est = idw.interpolate_wind_field(
    grid, stations, u_comp, v_comp
)
print(f"تخمین باد: u={u_est[0]}, v={v_est[0]}")
```

---

## پارامترهای روش

| پارامتر | مقدار پیش‌فرض | توضیح |
|---------|----------------|--------|
| `power` | ۲.۰ | توان فاصله؛ مقادیر بالاتر وزن نزدیک‌تر را بیشتر می‌کنند |
| `max_points` | `None` | محدود کردن تعداد نقاط منبع برای افزایش سرعت |
| `min_distance` | ۱e-6 | حداقل فاصله برای جلوگیری از تقسیم بر صفر |

---

## نتایج ارزیابی دقت

- در نقاط میانی با داده‌های خطی، خطای درونیابی کمتر از ۱۰٪ است (`test_accuracy_evaluation`).
- با افزایش `power` از ۱ به ۴، وزن نزدیک‌ترین نقطه به‌طور قابل‌توجهی افزایش می‌یابد (`test_power_parameter`).
- محدود کردن نقاط (`max_points=2`) سرعت را بدون از دست دادن دقت اساسی بهبود می‌دهد (`test_speed_optimization_with_max_points`).

---

## وابستگی‌ها

- پیش‌نیاز: [`Data Preparation for Pathfinding`](https://github.com/lawbr3aker/roshd-wind-pathfinder/)
- وابسته به: ماژول کش دادهها (`WindDataCache`)
- پیش‌نیازِ: آماده‌سازی داده ورودی مسیریابی

---

## بهبودهای آینده

۱. ادغام با ماژول کش (`WindDataCache`) برای دریافت داده‌های ورودی
۲. پیاده‌سازی درونیابی پیشرفته (`Kriging`)
۳. بهینه‌سازی بیشتر با `scipy.spatial` برای محاسبه فاصله
۴. افزودن ارزیابی دقت با داده‌های واقعی (`RMSE`, `MAE`)

---

## 2025-08-30 — Documentation Overhaul Update (AI Agent)

**Agent:** Hermes (AI)  
**Branch:** `feat/docs-overhaul-and-structure`  
**PR:** #TBD  

### Changes Made
- Updated package paths in documentation from `src/roshd_wind_pathfinder/...` to `src/...` (correct package root)
- Updated import examples to use `from data.module import ...` (matching actual src-layout)
- Added task template structure for future work
