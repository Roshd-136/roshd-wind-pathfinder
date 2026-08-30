# درونیابی Kriging با محاسبه واریوگرام (Variogram)

**تاریخ:** ۲۶ مرداد ۱۴۰۵  
**مسئول:** آرمان احمدی  
**وضعیت:** در حال انجام

---

## خلاصه پیاده‌سازی

ماژول درونیابی Kriging در مسیر `src/preprocessing/kriging.py` پیاده‌سازی شده است که وظایف زیر را انجام می‌دهد:

۱. **محاسبه واریوگرام تجربی** از همبستگی فضایی داده‌ها
۲. **برازش مدل‌های واریوگرام** (کروی، نمایی، گاوسی، خطی)
۳. **پیاده‌سازی درونیابی Kriging** با استفاده از ماتریس کوواریانس
۴. **مقایسه دقت** Kriging با روش IDW
۵. **مستندات کامل** پارامترها و نتایج

---

## چکلیست تسک (Items to Check)

|| آیتم | وضعیت | توضیحات ||
||------|--------|----------||
|| **۱.** مطالعه مبانی Kriging و واریوگرام | ✅ انجام شده | مطالعه نظریه و انتخاب مدل‌های استاندارد ||
|| **۲.** پیاده‌سازی محاسبه واریوگرام تجربی | ✅ انجام شده | کلاس `EmpiricalVariogram` با روش باین‌های فاصله ||
|| **۳.** برازش مدل واریوگرام | ✅ انجام شده | کلاس `VariogramFitter` با مدل‌های کروی/نمایی/گاوسی/خطی ||
|| **۴.** پیاده‌سازی درونیابی Kriging | ✅ انجام شده | کلاس `KrigingInterpolator` با بردارسازی ||
|| **۵.** مقایسه دقت Kriging با IDW | ✅ انجام شده | تست‌های مقایسه RMSE در داده‌های ساختگی ||
|| **۶.** تهیه نمونه کد و مستندات | ✅ انجام شده | نمونه کد در `tests/preprocessing/test_kriging.py` ||

---

## خروجی‌های تولیدشده

### ۱. کد پیاده‌سازی

#### فایل: `src/preprocessing/kriging.py`

#### ماژول‌ها:

**الف) `EmpiricalVariogram`** — محاسبه واریوگرام تجربی
- محاسبه نیمه‌واریانس تجربی از جفت‌های داده
- تقسیم فاصله به بازه‌های یکنواخت (bins)
- استفاده از `scipy.spatial.distance.pdist` برای محاسبه کارا

**ب) `VariogramFitter`** — برازش مدل واریوگرام
- برازش مدل با روش حداقل مربعات (Nelder-Mead)
- مدل‌های پشتیبانی: `spherical`, `exponential`, `gaussian`, `linear`
- محاسبه ناگت (nugget) و SSE (خطای مجموع مربعات)

**ج) `KrigingInterpolator`** — درونیابی Kriging
- محاسبه ماتریس کوواریانس از مدل واریوگرام
- محاسبه معکوس ماتریس کوواریانس برای پیش‌بینی
- اضافه کردن ناگت برای پایداری عددی
- درونیابی دقیق در نقاط منبع (exact interpolator)

### ۲. تست‌ها

- فایل: [`tests/preprocessing/test_kriging.py`](./tests/preprocessing/test_kriging.py)
- پوشش:
  - محاسبه واریوگرام تجربی
  - برازش مدل‌های مختلف
  - درونیابی Kriging
  - مقایسه دقت با IDW
  - دقیق‌بودن در نقاط منبع

### ۳. مستندات طراحی

این فایل — توضیح روش Kriging، پارامترها، و نتایج ارزیابی.

---

## مثال استفاده

```python
from preprocessing.kriging import (
    EmpiricalVariogram,
    VariogramFitter,
    KrigingInterpolator,
)
import numpy as np

# ۱. داده‌های ایستگاه‌های هواشناسی
coords = np.array([[35.7, 51.4], [35.8, 51.5], [35.75, 51.45]])
values = np.array([5.0, 3.0, 4.0])  # سرعت باد (m/s)

# ۲. محاسبه واریوگرام تجربی
emp = EmpiricalVariogram(coords, values, n_lags=10)
emp.compute()

# ۳. برازش مدل واریوگرام (کروی)
fitter = VariogramFitter(emp)
result = fitter.fit(model_name="spherical")
print(f"سیل: {result.sill:.3f}, برد: {result.range_:.3f}, ناگت: {result.nugget:.3f}")

# ۴. درونیابی Kriging در نقاط جدید
krig = KrigingInterpolator(coords, values, variogram_model="spherical")
target = np.array([[35.72, 51.42]])
prediction = krig.predict(target)
print(f"تخمین باد: {prediction[0]:.2f} m/s")
```

---

## پارامترهای روش

| پارامتر | مقدار پیش‌فرض | توضیح |
|---------|----------------|--------|
| `n_lags` | ۲۰ | تعداد بازه‌های فاصله برای محاسبه واریوگرام |
| `max_lag` | `None` | حداکثر فاصله لحاظ (پیش‌فرض: ۵۰٪ percentile فاصله‌ها) |
| `variogram_model` | `"spherical"` | مدل واریوگرام (`spherical`, `exponential`, `gaussian`, `linear`) |
| `nugget` | محاسبه‌شده | نشت در فاصله صفر (توارance در فاصله صفر) |
| `sill` | محاسبه‌شده | هامش (plateau) واریوگرام |
| `range_` | محاسبه‌شده | برد اثر همبستگی (فاصله تا سیل) |

---

## مقایسه دقت Kriging با IDW

### روش مقایسه

- **داده:** ۳۰ نقطه ساختگی با رابطه خطی + نویز گاوسی
- **مقیاس دقت:** RMSE (خطای ریشه دوم میانگین مربعات)
- **نقاط تست:** ۱۰ نقطه مصنوعی

### نتایج

| روش | RMSE (مقادیر ساختگی) | توضیح |
|-----|----------------------|--------|
| **Kriging** | < ۰.۵ | درونیابی دقیق‌تر با در نظر گرفتن ساختار همبستگی فضایی |
| **IDW (power=۲)** | ~۰.۵-۱.۰ | درونیابی ساده‌تر، بدون استفاده از واریوگرام |

#### نکات کلیدی:

- **Kriging** با استفاده از واریوگرام، ساختار همبستگی فضایی داده‌ها را مدل می‌کند و دقت بهتر به特に بر روی داده‌های ساختگی خطی دارد.
- **IDW** محاسبات سریع‌تری دارد و برای داده‌های با همبستگی قوی مناسب است، اما ساختار فضایی را در نظر نمی‌گیرد.
- در داده‌های واقعی میدان باد، Kriging معمولاً RMSE کمتری در نقاط میانی ارائه می‌دهد.

---

## ساختار کد

```
src/preprocessing/
├── idw.py          # پیاده‌سازی IDW (تسک قبلی)
└── kriging.py      # پیاده‌سازی Kriging + واریوگرام (تسک جدید)
    ├── EmpiricalVariogram
    ├── VariogramFitter
    └── KrigingInterpolator
```

---

## مراجع

- Wackernagel, H. (2003). *Multivariate Geostatistics*. Springer.
- Chilès, J. P., & Delfiner, P. (2012). *Geostatistics: Modeling Spatial Uncertainty*. Wiley.
- Deutsch, C. V., & Journel, A. G. (1998). *GSLIB: Geostatistical Software Library and User's Guide*.