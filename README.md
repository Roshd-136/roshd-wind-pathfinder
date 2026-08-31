# Roshd Wind Pathfinder — پروژه رشد

پایپلاین پیشپردازش دادههای باد و مسیریابی — پروژه دانشگاهی/تحقیقاتی با تیم فارسیزبان.

---

## فهرست

- [معماری پروژه](#معماری-پروژه)
- [مراحل پروژه](#مراحل-پروژه)
- [ساختار ریپو](#ساختار-ریپو)
- [شروع کار — برای AI Agent](#شروع-کار--برای-ai-agent)
- [شروع کار — برای همکار انسانی](#شروع-کار--برای-همکار-انسانی)
- [قوانین همکاری](#قوانین-همکاری)
- [توسعه و تست](#توسعه-و-تست)
- [وضعیت فعلی](#وضعیت-فعلی)

---

## معماری پروژه

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Roshd Wind Pathfinder                            │
├─────────────────────────────────────────────────────────────────────┤
│  GitHub: https://github.com/Roshd-136/roshd-wind-pathfinder     │
│  ClickUp Workspace: Roshd (Space: Data & Meteorology)              │
│  استاندارد پرامپت: مراجعه به .github/PROMPT.md                     │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    گام ۱:        │────▶│    گام ۲:        │────▶│    گام ۳+:       │
│  منابع داده     │     │  پیشپردازش و     │     │  مسیریابی       │
│  و کلیدهای API  │     │  درونیابی       │     │  (آینده)        │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ • Open-Meteo     │     │ • IDW Interp.    │     │ • Graph Build    │
│ • NOMADS/GFS     │     │ • Kriging Interp.│     │ • A* / Dijkstra  │
│ • ECMWF          │     │ • QC / Consist.  │     │ • Wind Routing   │
│ • API Keys Test  │     │ • Data Prep      │     │ • Optimization   │
└──────────────────┘     │ • Documentation  │     └──────────────────┘
                         └──────────────────┘
```

### جریان داده (Data Flow)

```
داده خام API/Source
    │
    ▼
WindDataCache (src/data/cache.py)
    │
    ▼
QC — کنترل کیفیت (src/qc/wind_qc.py)
    │
    ▼
IDW / Kriging درونیابی (src/preprocessing/idw.py, kriging.py)
    │
    ▼
پیوستگی مکانی-زمانی (src/preprocessing/consistency.py — آینده)
    │
    ▼
آمادهسازی داده مسیریابی (src/preprocessing/pathfinding_preparation.py)
    │
    ▼
data/khorasan_pathfinding_ready.csv  ──▶  مسیریابی (گام ۳)
```

---

## مراحل پروژه

| گام | موضوع | وضعیت | تسکهای کلیدی | ClickUp List |
|-----|-------|--------|--------------|--------------|
| **گام ۱** | **منابع داده و کلیدهای API** | ✅ انجام شد | • بررسی و انتخاب سرویسهای هواشناسی (Survey)<br>• دریافت کلیدهای API و تست اتصال (API Keys)<br>• تست اتصال NOMADS/GFS<br>• تست اتصال Open-Meteo<br>• ارزیابی و انتخاب نهایی ECMWF | `Data Sources` |
| **گام ۲** | **پیشپردازش و درونیابی** | 🔄 **در حال انجام** | • درونیابی IDW (آرمان) ✅<br>• درونیابی پیشرفته Kriging (آرمان) ✅<br>• کنترل کیفیت دادههای باد (مهدی) ✅<br>• آمادهسازی داده ورودی مسیریابی (مهدی) ✅<br>• بررسی پیوستگی زمانی و مکانی (امیرعلی) ❌ (آینده)<br>• مستندات و گزارش پیشپردازش (امیرعلی) ❌ (آینده) | `Preprocessing & Interpolation` |
| **گام ۳+** | **مسیریابی** | 🔮 آینده | • ساخت گراف بادی<br>• الگوریتم A* / Dijkstra<br>• بهینهسازی مسیر با جریان باد<br>• UI تحت وب (React + FastAPI) | — |

---

## ساختار ریپو

```
roshd-wind-pathfinder/
│
├── AGENTS.md                 # قوانین اجباری برای AI agents (خودکار بارگذاری)
├── CONTRIBUTING.md           # راهنمای همکاری برای همکاران انسانی (فارسی)
├── README.md                 # این فایل — نمای کلی پروژه
├── pyproject.toml            # تنظیمات Python، وابستگیها، CI
├── .gitignore
│
├── .github/                  # GitHub settings
│   ├── PROMPT.md             # استاندارد پرامپت برای AI agents
│   ├── pull_request_template.md  # قالب PR (همسو با قالب تسک ClickUp)
│   └── workflows/
│       └── ci.yml            # GitHub Actions: pytest + ruff روی هر PR
│
├── docs/                     # مستندات — مرجع واحد پروژه
│   ├── PROJECT_PROGRESS.md   # ⚡ پیشرفت پروژه — برای هر AI agent الزامی
│   ├── AGENT_ROUTING.md      # ⚡ راهنمای مسیریابی کد — کجا چه بگذارم؟
│   ├── task_data_caching.md  # مستندات تسک گام ۲ (انجام شد)
│   ├── task_idw_interpolation.md          # قالب تسک IDW (آینده)
│   ├── task_kriging_interpolation.md      # قالب تسک Kriging (آینده)
│   ├── task_wind_qc.md                    # قالب تسک QC (آینده)
│   ├── task_spatiotemporal_consistency.md # قالب تسک پیوستگی (آینده)
│   ├── task_data_prep_pathfinding.md      # قالب تسک آمادهسازی (آینده)
│   └── task_preprocessing_docs.md         # قالب تسک مستندات (آینده)
│
├── tasks/                    # الگو و وضعیت تسکها
│   ├── templates/
│   │   └── task_template.md  # الگوی استاندارد مستند تسک
│   ├── active/               # تسکهای در حال انجام (خالی — جای خالی)
│   └── completed/            # تسکهای تکمیلشده (خالی — جای خالی)
│
├── src/                       # پکیج پایتون (src-layout)
│   ├── __init__.py
│   ├── data/                  # گام ۱ — دریافت و کش داده
│   │   ├── __init__.py
│   │   └── cache.py           # WindDataCache
│   ├── preprocessing/         # گام ۲ — پیشپردازش و درونیابی
│   │   ├── __init__.py
│   │   ├── idw.py             # IDWInterpolator
│   │   ├── kriging.py         # KrigingInterpolator
│   │   ├── pathfinding_preparation.py  # آمادهسازی داده مسیریابی
│   │   └── consistency.py     # (آینده) پیوستگی مکانی-زمانی
│   ├── qc/                    # گام ۲ — کنترل کیفیت داده
│   │   ├── __init__.py
│   │   └── wind_qc.py         # WindQualityControl
│   └── pathfinding/           # گام ۳ — مسیریابی (آینده)
│       ├── __init__.py
│       ├── graph.py           # (آینده)
│       ├── algorithms.py      # (آینده)
│       └── routing.py         # (آینده)
│
├── tests/                    # تستها
│   ├── data/
│   │   ├── test_cache.py
│   │   └── test_cache_no_pandas.py
│   ├── preprocessing/
│   │   ├── test_idw.py
│   │   └── test_kriging.py
│   ├── test_pathfinding_preparation.py
│   └── test_wind_qc.py
│
└── data/                     # دادههای نمونه/آزمایشی
    ├── khorasan_wind_qc_cleaned.csv       # داده QC شده خراسان
    ├── khorasan_qc_report.json            # گزارش QC
    └── khorasan_pathfinding_ready.csv     # داده آماده مسیریابی
```

### راهنمای مسیریابی کد

> فایل کامل: [`docs/AGENT_ROUTING.md`](docs/AGENT_ROUTING.md)

برای هر تسک، کد را در **پوشه مشخص** بگذارید. خلاصه:

| تسک | کد `*.py` | تست `test_*.py` | مستند `docs/task_*.md` |
|-----|-----------|-----------------|------------------------|
| کش داده | `src/data/cache.py` | `tests/data/test_cache.py` | `task_data_caching.md` |
| درونیابی IDW | `src/preprocessing/idw.py` | `tests/preprocessing/test_idw.py` | `task_idw_interpolation.md` |
| درونیابی Kriging | `src/preprocessing/kriging.py` | `tests/preprocessing/test_kriging.py` | `task_kriging_interpolation.md` |
| کنترل کیفیت | `src/preprocessing/qc.py` | `tests/preprocessing/test_qc.py` | `task_wind_qc.md` |
| پیوستگی مکانی-زمانی | `src/preprocessing/consistency.py` | `tests/preprocessing/test_consistency.py` | `task_spatiotemporal_consistency.md` |
| آمادهسازی مسیریابی | `src/preprocessing/data_prep.py` | `tests/preprocessing/test_data_prep.py` | `task_data_prep_pathfinding.md` |
| ساخت گراف | `src/pathfinding/graph.py` | `tests/pathfinding/test_graph.py` | — |
| الگوریتمها | `src/pathfinding/algorithms.py` | `tests/pathfinding/test_algorithms.py` | — |
| بهینهسازی مسیر | `src/pathfinding/routing.py` | `tests/pathfinding/test_routing.py` | — |

---

## شروع کار — برای AI Agent

> اگر شما یک AI agent هستید که تازه به این پروژه اضافه شدهاید، این مراحل را **به ترتیب** انجام دهید:

1. **خودکار:** `AGENTS.md` در کانتکست شما بارگذاری شده — آن را کامل بخوانید.
2. **ریپو را کلون کنید:**
   ```bash
   git clone https://github.com/Roshd-136/roshd-wind-pathfinder.git
   cd roshd-wind-pathfinder
   ```
3. **معماری را بفهمید:** این `README.md` + `docs/PROJECT_PROGRESS.md` را بخوانید.
4. **مسیریابی را یاد بگیرید:** `docs/AGENT_ROUTING.md` را بخوانید — کجا کد بگذارید.
5. **تسک خود را پیدا کنید:** در ClickUp تسک مربوطه را باز کنید و شناسه/لینک را کپی کنید.
6. **برنچ بسازید:**
   ```bash
   git checkout -b task/<task-id>-<short-name>
   ```
7. **وابستگیها را نصب کنید:**
   ```bash
   python -m pip install -e ".[dev]" --break-system-packages
   ```
8. **کد موجود را بررسی کنید:** ماژولهای موجود در `src/` را بخوانید (`src/data/`، `src/preprocessing/`، `src/pathfinding/`).
9. **تست را ابتدا بنویسید (TDD)** — قرمز، سپس پیادهسازی، سپس سبز.
10. **پیادهسازی کنید:** طبق چکلیست تسک (Items to Check) در ClickUp.
11. **تستها را اجرا کنید:** `pytest -q`
12. **لینتر را اجرا کنید:** `ruff check .` — هر دو باید بدون خطا باشند.
13. **مستندات را آپدیت کنید:** بخش جدید به `docs/PROJECT_PROGRESS.md` اضافه کنید + مستند تسک در `docs/task_*.md`.
14. **PR باز کنید:** به `main` با قالب کامل PR (`.github/pull_request_template.md`).
15. **منتظر تأیید بمانید:** ادغام فقط توسط آرمان انجام میشود. PR خودتان را merge نکنید.

---

## شروع کار — برای همکار انسانی

> فایل کامل: [`CONTRIBUTING.md`](CONTRIBUTING.md)

1. اکانت GitHub بسازید و به پروژه دعوت شوید (Write permission).
2. **توکن (PAT)** بسازید: Settings → Developer settings → Fine-grained tokens.
   - Repository access: فقط `roshd-wind-pathfinder`
   - Permissions: Contents (R/W)، Pull requests (R/W)، Issues (R/W)
   - Expiration: ۹۰ روز
3. توکن را به AI model خود بهعنوان متغیر محیطی `GH_TOKEN` بدهید (نه در فایل).
4. **پرامپت استاندارد** را از `.github/PROMPT.md` کپی کنید، توکن و تسک را بگذارید، به AI بدهید.
5. AI بر اساس `AGENTS.md`، `docs/PROJECT_PROGRESS.md` و `docs/AGENT_ROUTING.md` کار میکند.
6. شما PR را باز میکنید، آرمان بررسی و merge میکند.

---

## قوانین همکاری

### ۱. استراتژی Branch
- **هرگز مستقیم روی `main` کار نکنید** — قفل است و push مستقیم غیرفعال است.
- برای هر تسک یک برنچ: `task/<task-id>-<short-name>`
- مثال: `task/86bba36de-idw-interpolation`

### ۲. Pull Request Workflow
```
AI/Developer creates branch
        │
        ▼
Implement + Test locally (pytest + ruff)
        │
        ▼
Push branch + Open PR against main
        │
        ▼
CI runs automatically (pytest + ruff)
        │
        ▼
PR Template filled (Purpose / Items / Output / Evidence)
        │
        ▼
Project Owner reviews + Approves
        │
        ▼
Merge to main (Squash + Merge)
```

### ۳. Definition of Done (هر تسک)
- [ ] کد پیادهسازی شده و در **پوشه صحیح** است (مطابق `AGENT_ROUTING.md`)
- [ ] تستها نوشته و پاس میشوند (`pytest -q`)
- [ ] لینتر بدون خطا (`ruff check .`)
- [ ] `docs/PROJECT_PROGRESS.md` آپدیت شده (فقط append — بخشهای قبلی دست نخورده)
- [ ] مستند تسک در `docs/task_*.md` ایجاد/آپدیت شده
- [ ] قالب PR تکمیل شده (Purpose, Items, Output, Evidence)
- [ ] CI سبز است
- [ ] تسک ClickUp به `Closed` تغییر کرده + چکلیست تکمیل شده

### ۴. امنیت
- **هیچ رازی (Token، API Key، Password) در کد/گیت/مستندات قرار نمیگیرد.**
- توکنها در Environment Variables یا GitHub Secrets مدیریت میشوند.
- اگر تصادفاً رازی ثبت شد، فوراً به آرمان اطلاع دهید — چرخش (rotate) لازم است.

### ۵. اختیار ادغام (Merge Authority)
- **فقط مالک پروژه (آرمان) میتواند PR را ادغام کند.**
- AI agents و همکاران فقط PR باز میکنند، ادغام نمیکنند.

---

## توسعه و تست

```bash
# کلون و تنظیم
git clone https://github.com/Roshd-136/roshd-wind-pathfinder.git
cd roshd-wind-pathfinder

# نصب وابستگیها
python -m pip install -e ".[dev]" --break-system-packages

# لینتر
ruff check .

# تمام تستها
pytest -q

# تست یک ماژول
pytest -q tests/data/

# با coverage
pytest --cov=src tests/
```

---

## وضعیت فعلی

> بهروزترین وضعیت در [`docs/PROJECT_PROGRESS.md`](docs/PROJECT_PROGRESS.md)

| ماژول | وضعیت | فایل اصلی | تست | مستندات |
|-------|--------|-----------|-----|---------|
| **WindDataCache** | ✅ کامل | `src/data/cache.py` | ✅ ۱۱ پاس | `docs/task_data_caching.md` |
| **IDW Interpolation** | ✅ کامل | `src/preprocessing/idw.py` | ✅ ۷ پاس | `docs/task_idw_interpolation.md` |
| **Kriging Interpolation** | ✅ کامل | `src/preprocessing/kriging.py` | ✅ ۱۱ پاس | `docs/task_kriging_interpolation.md` |
| **Wind Data QC** | ✅ کامل | `src/qc/wind_qc.py` | ✅ ۲ پاس | `docs/task_wind_qc.md` |
| **Data Prep for Pathfinding** | ✅ کامل | `src/preprocessing/pathfinding_preparation.py` | ✅ ۱ پاس | `docs/task_data_prep_pathfinding.md` |
| **Spatio-temporal Consistency** | 🔄 در انتظار | `src/preprocessing/consistency.py` (آینده) | — | `docs/task_spatiotemporal_consistency.md` |
| **Preprocessing Docs** | 🔄 در انتظار | `docs/preprocessing_guide.md` (آینده) | — | `docs/task_preprocessing_docs.md` |

---

**مالک پروژه:** آرمان احمدی (Arman Ahmadi)  
**GitHub:** [lawbr3aker](https://github.com/lawbr3aker)  
**ریپو:** [roshd-wind-pathfinder](https://github.com/Roshd-136/roshd-wind-pathfinder)  
**ClickUp:** Roshd Workspace → Space: Data & Meteorology  
**استاندارد پرامپت AI:** [`.github/PROMPT.md`](.github/PROMPT.md)