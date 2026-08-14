# Roshd Wind Pathfinder — پروژه رشد

پایپلاین پیشپردازش دادههای باد و مسیریابی — پروژه دانشگاهی/تحقیقاتی با تیم فارسیزبان.

## معماری کلی پروژه

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Roshd Wind Pathfinder                            │
├─────────────────────────────────────────────────────────────────────┤
│  GitHub: https://github.com/lawbr3aker/roshd-wind-pathfinder       │
│  ClickUp Workspace: Roshd (Space: Data & Meteorology)              │
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

## مراحل پروژه

| گام | موضوع | وضعیت | تسکهای کلیدی | ClickUp List |
|-----|-------|--------|--------------|--------------|
| **گام ۱** | **منابع داده و کلیدهای API** | ✅ انجام شد | • بررسی و انتخاب سرویسهای هواشناسی (Survey)<br>• دریافت کلیدهای API و تست اتصال (API Keys)<br>• تست اتصال NOMADS/GFS<br>• تست اتصال Open-Meteo<br>• ارزیابی و انتخاب نهایی ECMWF | `Data Sources` |
| **گام ۲** | **پیشپردازش و درونیابی** | ✅ انجام شده (کد کامل، در انتظار چکلیست) | • درونیابی IDW (آرمان)<br>• درونیابی پیشرفته Kriging (آرمان)<br>• کنترل کیفیت دادههای باد (مهدی)<br>• بررسی پیوستگی زمانی و مکانی (امیرعلی)<br>• آمادهسازی داده ورودی مسیریابی (مهدی)<br>• مستندات و گزارش پیشپردازش (امیرعلی) | `Preprocessing & Interpolation` |
| **گام ۳+** | **مسیریابی** | 🔮 آینده | • ساخت گراف بادی<br>• الگوریتم A* / Dijkstra<br>• بهینه‌سازی مسیر با جریان باد<br>• UI تحت وب (React + FastAPI) | — |

## ساختار ریپو

```
roshd-wind-pathfinder/
├── AGENTS.md                 # دستورالعمل الزامی برای هر AI agent (خودکار بارگذاری میشود)
├── CONTRIBUTING.md           # راهنمای همکاری برای همکاران انسانی (فارسی)
├── README.md                 # این فایل — مرجع کامل پروژه
├── pyproject.toml            # تنظیمات Python، وابستگیها، CI
├── .github/
│   ├── workflows/
│   │   └── ci.yml            # GitHub Actions: pytest + ruff روی هر PR
│   └── PULL_REQUEST_TEMPLATE.md  # قالب PR (همسو با قالب تسک ClickUp)
├── src/
│   └── roshd_wind_pathfinder/
│       ├── __init__.py
│       └── data/
│           ├── __init__.py
│           └── cache.py      # WindDataCache — ذخیرهسازی و کش دادههای باد
├── tests/
│   └── data/
│       └── test_cache_no_pandas.py  # ۵ تست پاس شده
├── docs/
│   └── task_data_caching.md  # مستندات کامل تسک گام ۲
├── .gitignore
└── LICENSE
```

## قوانین همکاری (لازم برای هر AI/انسان)

### ۱. **Bernch Strategy**
- **هرگز مستقیم روی `main` کار نکنید.**
- برای هر تسک یک برنچ بسازید: `task/<clickup-task-id>-<short-name>`
- مثال: `task/86bba36de-idw-interpolation`

### ۲. **Pull Request Workflow**
```
Developer/AI creates branch
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

### ۳. **Definition of Done (هر تسک)**
- [ ] کد پیادهسازی شده و در `src/` قرار دارد
- [ ] تستها نوشته شده و در `tests/` پاس میشوند (`pytest -q`)
- [ ] لینتر بدون خطا (`ruff check .`)
- [ ] مستندات در `docs/` به‌روزرسانی شده
- [ ] قالب PR تکمیل شده (Purpose, Items, Output, Evidence)
- [ ] CI سبز است
- [ ] تسک ClickUp به `Closed` تغییر کرده + چکلیست تکمیل شده

### ۴. **Security**
- **هیچ رازی (Token، API Key، Password) در کد/گیت/مستندات قرار نمیگیرد.**
- توکنها در Environment Variables یا `.env` (در `.gitignore`) مدیریت میشوند.

### ۵. **Merge Authority**
- **فقط مالک پروژه (Arman) میتواند PR را ادغام کند.**
- AI agents و همکاران فقط PR باز میکنند، ادغام نمیکنند.

## راهنمای سریع برای AI Agent جدید (بدون حافظه قبلی)

> **اگر شما یک AI agent هستید که تازه به این پروژه اضافه شده‌اید، این مراحل را انجام دهید:**

1. **خودکار:** فایل `AGENTS.md` در کانتکست شما بارگذاری شده — آن را کامل بخوانید.
2. **ریپو را کلون کنید:** `git clone https://github.com/lawbr3aker/roshd-wind-pathfinder.git`
3. **معماری را بفهمید:** این `README.md` را بخوانید (معماری، مراحل، قوانین).
4. **تسک خود را پیدا کنید:**
   - در ClickUp تسک مربوطه را باز کنید (لیست `Preprocessing & Interpolation` برای گام ۲)
   - شناسه تسک (مثل `86bba36de`) و لینک آن را کپی کنید
5. **برنچ بسازید:** `git checkout -b task/<task-id>-<name>`
6. **وابستگیها را نصب کنید:**
   ```bash
   cd roshd-wind-pathfinder
   python -m pip install -e ".[dev]"
   ```
7. **کد موجود را بررسی کنید:** ماژولهای موجود در `src/roshd_wind_pathfinder/` را بخوانید.
8. **پیادهسازی کنید:** طبق چکلیست تسک (Items to Check) در ClickUp.
9. **تست بنویسید/اجرا کنید:** `pytest -q tests/`
10. **لینتر اجرا کنید:** `ruff check .`
11. **مستندات به‌روزرسانی کنید:** فایل مربوطه در `docs/` را ویرایش کنید.
12. **PR باز کنید:** به `main` با قالب PR کامل.
13. **منتظر تأیید بمانید:** مالک پروژه review و merge میکند.

## راهنمای سریع برای همکار انسانی

> فایل کامل: [CONTRIBUTING.md](CONTRIBUTING.md)

1. اکانت GitHub بسازید و به پروژه 초대 شوید (Write permission).
2. Fine-grained PAT بسازید (Repository access: only this repo, Contents: R/W, PR: R/W).
3. توکن را به AI model خود بدهید (Environment Variable: `GH_TOKEN`).
4. AI بر اساس `AGENTS.md` و این `README` کار میکند.
5. شما PR را باز میکنید، مالک پروژه merge میکند.

## توسعه و اجرای تستها

```bash
# کلون و تنظیم
git clone https://github.com/lawbr3aker/roshd-wind-pathfinder.git
cd roshd-wind-pathfinder

# نصب وابستگیها (dev dependencies شامل pytest، ruff، pandas)
python -m pip install -e ".[dev]"

# اجرای لینتر
ruff check .

# اجرای تمام تستها
pytest -q

# اجرای تستهای خاص ماژول data
pytest -q tests/data/

# اجرای با coverage
pytest --cov=src/roshd_wind_pathfinder tests/
```

## CI/CD Pipeline (GitHub Actions)

فایل: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

**Triggers:** Push به `main`، Pull Request به `main`

**Jobs:**
- `quality` — روی `ubuntu-latest`
  1. Checkout code
  2. Setup Python 3.10+
  3. Install dependencies (`pip install -e ".[dev]"`)
  4. Run `ruff check .` (linter)
  5. Run `pytest -q` (tests)
  6. **Required برای merge** (Branch Protection)

**Branch Protection Rules on `main`:**
- Require PR review (1 approval)
- Require CI to pass
- Require branches to be up-to-date
- No direct pushes

## ClickUp Integration

### Workspace Structure
```
Space: Data & Meteorology
├── Folder: Wind Data
│   ├── List: Data Sources - Open-Meteo, ECMWF, NOMADS (گام ۱)
│   └── List: Preprocessing & Interpolation (گام ۲)
```

### Task Template (v3 — هر تسک)
 هر تسک شامل ۶ بخش است:
1. **Purpose - هدف**
2. **Items to Check - موارد بررسی** (شماره‌گذاری ۱-۷)
3. **Required Output - خروجی مدنظر**
4. **Deadline - مهلت تحویل** (ساعت ۱۷:۰۰ ایران، `due_date_time: true`)
5. **Priority - اولویت** (High/Normal)
6. **Dependencies - وابستگی‌ها** (پیشنیازها + بلاک‌کننده‌ها)

### Automation
- **GitHub Commit → ClickUp Comment:** هر کامیت با فرمت `feat(data): ... تسک <id>` به تسک ClickUp لینک میشود.
- **PR Template:** قالب PR در `.github/PULL_REQUEST_TEMPLATE.md` دقیقاً با قالب تسک ClickUp همسو است.

## وضعیت فعلی (به‌روز: ۱۴ آبان ۱۴۰۵ / ۱۴ آگوست ۲۰۲۶)

| ماژول | وضعیت | فایل اصلی | تست | مستندات |
|-------|--------|-----------|-----|---------|
| **WindDataCache** (گام ۲) | ✅ کامل | `src/roshd_wind_pathfinder/data/cache.py` | ۵/۵ پاس | `docs/task_data_caching.md` |
| **IDW Interpolation** | 🔄 در انتظار پیادهسازی | — | — | — |
| **Kriging Interpolation** | 🔄 در انتظار پیادهسازی | — | — | — |
| **Wind Data QC** | 🔄 در انتظار پیادهسازی | — | — | — |
| **Temporal/Spatial Consistency** | 🔄 در انتظار پیادهسازی | — | — | — |
| **Data Prep for Pathfinding** | 🔄 در انتظار پیادهسازی | — | — | — |
| **Preprocessing Docs** | 🔄 در انتظار پیادهسازی | — | — | — |

## ملاقات بعدی / Next Steps

1. **گام ۲ — پیادهسازی ۶ تسک باقیمانده** در لیست `Preprocessing & Interpolation`
2. **هر تسک:** برنچ → پیادهسازی → تست → PR → Review → Merge
3. **گام ۳ — طراحی معماری مسیریابی** (گراف، الگوریتم، UI)

---

**مالک پروژه:** آرمان احمدی (Arman Ahmadi)  
**GitHub:** [lawbr3aker](https://github.com/lawbr3aker)  
**ریپو:** [roshd-wind-pathfinder](https://github.com/lawbr3aker/roshd-wind-pathfinder)  
**ClickUp:** Roshd Workspace → Space: Data & Meteorology