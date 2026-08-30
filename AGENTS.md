# AGENTS.md — قوانین AI Agents در این ریپو

> این فایل بهطور خودکار در کانتکست هر AI coding agent (Hermes, Claude Code,
> Cursor, Copilot, Codex و...) که روی این ریپو کار میکند بارگذاری میشود.
> اگر شما یک AI agent هستید، **باید** قبل از هر کاری این قوانین را کامل بخوانید
> و پیروی کنید.

---

## ۱. نمای کلی پروژه

**Roshd Wind Pathfinder** — پایپلاین پیشپردازش دادههای باد و مسیریابی برای یک
پروژه هواشناسی (تیم فارسیزبان). پروژه بهصورت مرحلهای (گام) ساخته میشود:
- **گام ۱:** منابع داده و کلیدهای API (انجام شد)
- **گام ۲:** پیشپردازش و درونیابی (در حال انجام)
- **گام ۳+:** مسیریابی (آینده)

**تیم:**
- **آرمان (مالک پروژه)** — بررسی و ادغام همهچیز. هرگز او را دور نزنید.
- **مهدی** — همکار (تسکهای QC و آمادهسازی داده)
- **امیرعلی** — همکار (تسکهای پیوستگی و مستندات)

**قانون زبان:** تمام محتوای کاربرمحور (مستندات، توضیح PR، پیام کامیت، نظرات کد)
به **فارسی** با نیمفاصله صحیح (ZWNJ) نوشته میشود. شناسههای فنی به انگلیسی میمانند.

---

## ۲. منبع تسک — ClickUp

**همه تسکها در ClickUp تعریف میشوند، نه در این ریپو.** هر تسک دارای:
- عنوان (فارسی + انگلیسی در پرانتز)
- توضیح با ۵ بخش: **Purpose / Items to Check / Required Output / Deadline / Priority**
- چکلیست (۷ آیتم)
- وابستگیها به تسکهای دیگر

### نحوه خواندن یک تسک

1. **آدرس تسک را از انسان بگیرید.** مثال:
   `https://app.clickup.com/t/86bb9vt6d`
2. **تسک را با API ClickUp** بگیرید یا از انسان بخواهید توضیح را paste کند.
3. **۵ بخش را تحلیل کنید:**
   - **Purpose** ← این تسک چه کاری انجام میدهد
   - **Items to Check** ← چکلیستی که باید پیادهسازی شود (همه آیتمها باید انجام شود)
   - **Required Output** ← چه فایلها/توابع/آرتیفکتهایی باید تولید کنید
   - **Deadline** ← تاریخ فارسی + ساعت (۱۷:۰۰ ایران)
   - **Priority** ← High (1-2) یا Normal (3-4)
4. **وابستگیها را بررسی کنید** ← اگر تسک وابسته است، مطمئن شوید آن تسکها اول ادغام شوند.

---

## ۳. قوانین طلایی (غیرقابل مذاکره)

1. **هرگز مستقیم روی `main` push یا commit نکنید.** همه کارها روی برنچ فیچر
   انجام میشود؛ `main` فقط از طریق Pull Request که مالک تأیید و ادغام میکند تغییر میکند.
2. **قبل از شروع کار، آخرین `main` را pull کنید** و `origin/main` را قبل از باز کردن
   PR در برنچ خود merge/rebase کنید.
3. **هر تسک یک برنچ.** نام برنچ: `task/<short-slug>` (مثلاً `task/idw-interpolation`).
4. **هرگز راز (secret) کامیت نکنید.** هیچ API key، token، رمز عبور یا اعتبارنامهای —
   نه در کد، نه در config، نه در مستندات. رازها فقط در environment variables /
   GitHub Secrets زندگی میکنند.
5. **واقعیت نسازید.** اگر چیزی را نمیدانید (رفتار API، یک کتابخانه، یک الزام)،
   منبع واقعی را بررسی کنید یا بپرسید. هرگز حدس نزنید.
6. **فایلهای خارج از حیطه تسک خود را بدون اعلام تغییر ندهید.**
7. **داده ساختگی نسازید.** اگر داده لازم دارید، از ماژول cache یا API واقعی بگیرید.

---

## ۴. گردش کار تسک (معنای «انجام تسک»)

1. **توضیح تسک و چکلیست آن را کامل بخوانید.** اگر چیزی مبهم است، از مالک بپرسید —
   حدس نزنید.
2. **برنچ بسازید:** `git checkout -b task/<slug>`.
3. **فقط آیتمهای چکلیست را پیادهسازی کنید.** ویژگی اضافه نسازید.
4. **کد را در پوشه صحیح بگذارید.** فایل [`docs/AGENT_ROUTING.md`](docs/AGENT_ROUTING.md)
   را بخوانید — جدول مسیریابی آنجا است (کد در `src/<module>/`،
   تست در `tests/<module>/`، مستند در `docs/task_*.md`).
5. **قبل از push، کل تستها و لینتر را اجرا کنید** (ببینید §۶). همه باید پاس شوند.
6. **برنچ را push کنید و PR باز کنید** با استفاده از قالب PR ریپو. توضیح PR **باید:**
   - هدف تسک را در یک پاراگراف بازنویسی کند.
   - **آیتمهای بررسی** (Items to Check) را بهصورت چکلیست (`- [ ]`) تکرار کند و
     آیتمهای انجامشده را تیک بزند.
   - **شواهد** بدهد: خروجی واقعی تستها/لینتری که اجرا کردید.
   - ددلاین و اولویت تسک را ذکر کند.
   - لینک تسک ClickUp را بگذارد (آدرس را paste کنید).
7. **هرگز PR خودتان را merge نکنید.** ادغام فقط کار مالک است. اگر مالک تغییراتی
   خواست، اصلاح کنید و دوباره review درخواست کنید.
8. **اگر CI روی PR شما قرمز شد، آن را درست کنید** — PR قرمز یعنی PR ناتمام.
9. **در پایان، بخش جدید به `docs/PROJECT_PROGRESS.md` اضافه کنید** — بخشهای قبلی
   را دست نزنید (این فایل append-only است).

---

## ۵. ساختار ریپو

```
roshd-wind-pathfinder/
├── AGENTS.md                  # این فایل — قوانین AI agents
├── CONTRIBUTING.md            # راهنمای همکاران انسانی (فارسی)
├── README.md                  # نمای کلی پروژه + معماری
├── pyproject.toml             # تنظیمات پروژه + ruff/pytest
├── .github/
│   ├── PROMPT.md              # ⚡ استاندارد پرامپت برای AI agents
│   ├── pull_request_template.md
│   └── workflows/ci.yml       # روی هر PR و push اجرا میشود
├── docs/                      # ⚡ مرجع پروژه
│   ├── PROJECT_PROGRESS.md    # پیشرفت پروژه (append-only — قبل از هر کار بخوان)
│   ├── AGENT_ROUTING.md       # مسیریابی کد — کجا چه بگذارم
│   └── task_*.md              # مستندات تک-تسک
├── tasks/                     # الگوها و وضعیت تسکها
│   ├── templates/task_template.md
│   ├── active/
│   └── completed/
├── src/                       # پکیج پایتون (src-layout)
│   ├── __init__.py
│   ├── data/                  # گام ۱ — دریافت و کش داده
│   │   ├── __init__.py
│   │   └── cache.py           # WindDataCache
│   ├── preprocessing/         # گام ۲ — پیشپردازش و درونیابی
│   │   ├── __init__.py
│   │   ├── idw.py             # (آینده)
│   │   ├── kriging.py         # (آینده)
│   │   ├── qc.py              # (آینده)
│   │   ├── consistency.py     # (آینده)
│   │   └── data_prep.py       # (آینده)
│   └── pathfinding/           # گام ۳ — مسیریابی (آینده)
│       ├── __init__.py
│       ├── graph.py           # (آینده)
│       ├── algorithms.py      # (آینده)
│       └── routing.py         # (آینده)
├── tests/
│   ├── data/
│   │   ├── test_cache.py
│   │   └── test_cache_no_pandas.py
│   ├── preprocessing/         # (آینده)
│   └── pathfinding/           # (آینده)
└── data/                      # دادههای نمونه/آزمایشی
    ├── khorasan_wind_qc_cleaned.csv
    ├── khorasan_qc_report.json
    └── khorasan_pathfinding_ready.csv
```

> ⚠️ **ساختار واقعی پکیج:** ماژولها در `src/` قرار دارند (نه `src/roshd_wind_pathfinder/`):
> `src/data/`، `src/preprocessing/`، `src/pathfinding/`. ایمپورت مانند `from data.cache
> import WindDataCache` است. مسیر صحیح فایل cache: `src/data/cache.py`.

### مسیریابی کد (خلاصه)

> فایل کامل: [`docs/AGENT_ROUTING.md`](docs/AGENT_ROUTING.md)

| تسک | کد | تست | مستند |
|-----|-----|------|-------|
| کش داده | `src/data/cache.py` | `tests/data/test_cache.py` | `docs/task_data_caching.md` |
| درونیابی IDW | `src/preprocessing/idw.py` | `tests/preprocessing/test_idw.py` | `docs/task_idw_interpolation.md` |
| درونیابی Kriging | `src/preprocessing/kriging.py` | `tests/preprocessing/test_kriging.py` | `docs/task_kriging_interpolation.md` |
| کنترل کیفیت | `src/preprocessing/qc.py` | `tests/preprocessing/test_qc.py` | `docs/task_wind_qc.md` |
| پیوستگی | `src/preprocessing/consistency.py` | `tests/preprocessing/test_consistency.py` | `docs/task_spatiotemporal_consistency.md` |
| آمادهسازی داده | `src/preprocessing/data_prep.py` | `tests/preprocessing/test_data_prep.py` | `docs/task_data_prep_pathfinding.md` |
| ساخت گراف | `src/pathfinding/graph.py` | `tests/pathfinding/test_graph.py` | — |
| الگوریتمها | `src/pathfinding/algorithms.py` | `tests/pathfinding/test_algorithms.py` | — |
| بهینهسازی مسیر | `src/pathfinding/routing.py` | `tests/pathfinding/test_routing.py` | — |

### مالکیت ماژول (who owns which files)

| ماژول | مسئول | فایلها |
|-------|-------|--------|
| `src/data/` | آرمان | API clients, caching |
| `src/preprocessing/` | مشترک | IDW, Kriging, QC, consistency, data_prep |
| `src/pathfinding/` | آینده | — |

**قانون:** اگر فایلی توسط تسک شخص دیگری ساخته شده، میتوانید بخوانید ولی بازنویسی
نکنید — از طریق PR هماهنگ کنید.

---

## ۶. دستورات

```bash
# نصب وابستگیهای dev
python -m pip install -e ".[dev]" --break-system-packages

# لینتر (ruff)
ruff check .

# تستها
pytest -q

# تست با coverage
pytest --cov=src
```

**تعریف انجامشدن:** `ruff check .` پاس میشود **و** `pytest -q` پاس میشود **و**
هر آیتم چکلیست یا پیادهسازی شده یا با دلیل صریحاً not-applicable علامت خورده.

---

## ۷. سبک کد

- **Python 3.10+** با type hints در جای ممکن.
- **Docstringها** به فارسی برای توابع/کلاسهای عمومی.
- **Importها:** stdlib → third-party → local، الفبایی در هر گروه.
- **طول خط:** حداکثر ۱۰۰ کاراکتر (توسط ruff اعمال میشود).
- **تشکیل تست:** هر ماژول `*.py` یک فایل `test_*.py` متناظر در پوشه tests دارد.

### کتابخانههای مجاز (وابستگیها)

```toml
# Core
numpy>=1.24
pandas>=2.0
xarray>=2023.1     # در صورت لزوم
scipy>=1.11        # در صورت لزوم (درونیابی)

# Data fetching
requests>=2.31
aiohttp>=3.8       # در صورت لزوم async

# Testing
pytest>=7.4
pytest-cov>=4.0

# Dev
ruff>=0.4
```

**بدون تأیید مالک، وابستگی جدید اضافه نکنید.**

---

## ۸. سبک پیام کامیت

- به فارسی، حالت امری، یک خط زیر ۷۲ کاراکتر، بهعلاوه یک بدنه کوتاه اگر لازم بود.
- پیشوند با حوزه تسک: `data: ...`، `preprocess: ...`، `interp: ...`، `qc: ...`،
  `pathfinding: ...`، `docs: ...`، `test: ...`، `ci: ...`.

مثالها:
```
interp: پیادهسازی درونیابی IDW با پارامتر توان قابل تنظیم
```
```
qc: افزودن اعتبارسنجی بازه معتبر برای دادههای باد
```

---

## ۹. آداب PR

- **عنوان PR = عنوان تسک** (فارسی اول، انگلیسی در پرانتز اگر هست).
- PRها را کوچک و متمرکز بر یک تسک نگه دارید. اگر لازم است کد مشترک را لمس کنید،
  در توضیح PR ذکر کنید.
- قبل از درخواست دوباره review، conflictها را در برنچ خود رفع کنید.
- مودب و مختصر باشید؛ مالک به فارسی review میکند.

---

## ۱۰. اگر گیر کردید

1. **تسک را دوباره بخوانید** — جواب معمولاً در Items to Check است.
2. **کد موجود را در `src/` بررسی کنید** برای الگوها و قراردادها.
3. **مستندات را بخوانید:** `docs/PROJECT_PROGRESS.md` (وضعیت)،
   `docs/AGENT_ROUTING.md` (مسیریابی).
4. **از مالک بپرسید** — بهتر است بپرسید تا اشتباه حدس بزنید.
5. **موانع را در PR مستند کنید** اگر نتوانستید ادامه دهید.