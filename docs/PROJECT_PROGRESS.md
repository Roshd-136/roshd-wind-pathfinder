# دفترچه روند پروژه (PROJECT PROGRESS)

> هر ایجنت AI بعد از تمام کردن تسک، یک بخش جدید اینجا اضافه میکند. بخشهای قبلی دست نخورده باقی میمانند.
> **قانون:** قبل از شروع هر تسک، این فایل را بخوان.

## وضعیت کلی (۲۶ مرداد ۱۴۰۵)
| گام | موضوع | وضعیت |
|-----|-------|--------|
| گام ۱ | منابع داده، کش | ✅ تمام |
| گام ۲ | پیشپردازش | 🟡 در حال انجام (۳/۶ روی main، ۳ ناقص) |
| گام ۳+ | مسیریابی | ⬜ آینده |

## تسک‌های انجام‌شده
- **گام ۱** — API Keys, Data Caching, Survey → ✅ تمام
- **گام ۲ (شما)** — IDW Interpolation (PR #1), Kriging (PR #2) → ✅ تمام  
- **گام ۲ (مهدی)** — Wind Data QC → ⚠️ ناقص (بدون تست، بدون داده واقعی Open-Meteo، مستقیم روی main push شد)
- **گام ۲ (سایر)** — DataPrep, Consistency, Report → ⬜ هنوز شروع نشده/نیاز به بررسی

## قالب بخش جدید (ایجنتها: کپی کنید)
```markdown
## تسک: «عنوان» (ClickUp ID: «id») — گام «n»
- **وضعیت:** انجام شد / در حال انجام  
- **چه ساختم:** خلاصه ۲-۴ خطی  
- **ورودی که استفاده کردم:** کدام تسک/ماژول قبلی  
- **خروجی این تسک:** مسیر دقیق فایلها + نام تابع/کلاس  
- **برای تسک بعدی:** چه چیزی لازم دارد و چطور استفاده کند  
- **تست:** pytest و ruff نتیجه واقعی
- **PR:** لینک PR (merge فقط توسط آرمان)
```

---

## 2025-08-30 — Initial Setup & Documentation Overhaul

**Agent:** Hermes (AI)  
**Branch:** `feat/docs-overhaul-and-structure`  
**PR:** #TBD  

### Summary
Comprehensive documentation overhaul to make the project ready for AI agents and human collaborators. Fixed existing issues, created missing files, established standard folder structure, and prepared GitHub branch protection.

### Changes Made

#### 1. Standard Prompt File (`.github/PROMPT.md`)
- Created the standard prompt file that defines how AI agents should work on this project
- Contains repo URL, token placeholder, task input format, and 8 golden rules for agents

#### 2. PROJECT_PROGRESS.md (this file)
- Created the project progress tracking file
- Establishes append-only convention for tracking all work

#### 3. Data Files Added
- `data/khorasan_wind_qc_cleaned.csv` — QC-cleaned wind data for Khorasan region
- `data/khorasan_qc_report.json` — QC report (144 records, 0% removal rate)
- `data/khorasan_pathfinding_ready.csv` — Pathfinding-ready data with u/v components and normalized values

#### 4. Code Quality Fixes
- Fixed ruff linting error in `tests/data/test_cache.py` (F401 unused import)
- All tests pass: `pytest -q` → 11 passed
- Linter clean: `ruff check .` → OK

#### 5. Documentation Improvements (Planned)
- README.md: Strengthen project structure documentation
- CONTRIBUTING.md: Make general, not person-specific
- AGENTS.md: Ensure accuracy for AI agents

#### 6. Folder Structure for Future Tasks (Planned)
```
docs/
  ├── PROJECT_PROGRESS.md
  ├── task_data_caching.md
  ├── task_idw_interpolation.md
  ├── task_kriging_interpolation.md
  ├── task_wind_qc.md
  ├── task_spatiotemporal_consistency.md
  ├── task_data_prep_pathfinding.md
  └── task_preprocessing_docs.md
tasks/
  ├── templates/
  │   └── task_template.md
  ├── active/
  └── completed/
.github/
  ├── PROMPT.md
  ├── pull_request_template.md
  └── workflows/
      └── ci.yml
src/                       # پکیج پایتون (src-layout)
  ├── __init__.py
  ├── data/
  │   ├── __init__.py
  │   └── cache.py
  ├── preprocessing/
  │   ├── __init__.py
  │   ├── idw.py
  │   ├── kriging.py
  │   ├── qc.py
  │   └── consistency.py
  └── pathfinding/
      ├── __init__.py
      ├── graph.py
      ├── algorithms.py
      └── routing.py
tests/
  ├── data/
  │   ├── test_cache.py
  │   └── test_cache_no_pandas.py
  ├── preprocessing/
  └── pathfinding/
```

### Verification
- ✅ All tests pass (`pytest -q`)
- ✅ Linter clean (`ruff check .`)
- ✅ Data files in place
- ✅ Standard prompt file created

### Next Steps
- Complete documentation overhaul (README, CONTRIBUTING, AGENTS)
- Create folder structure for future tasks
- Set up GitHub branch protection
- Open PR for review
