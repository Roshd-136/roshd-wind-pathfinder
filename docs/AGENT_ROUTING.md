# Agent Routing Guide — کجا کد بگذارم؟

> **AI agents:** When you receive a task, route your code to the **correct folder** by matching the task topic to the categories below. Putting code in the wrong folder will cause merge conflicts and will not pass PR review.

---

## Decision Tree — فلوچارت تصمیم

```
تسک شما چیست؟
│
├── دریافت/ذخیره/کش داده
│   └── src/data/
│       Tests → tests/data/
│       Docs → docs/task_data_caching.md
│
├── پیش‌پردازش داده
│   ├── درونیابی IDW
│   │   └── src/preprocessing/idw.py
│   │       Tests → tests/preprocessing/test_idw.py
│   │       Docs → docs/task_idw_interpolation.md
│   │
│   ├── درونیابی Kriging
│   │   └── src/preprocessing/kriging.py
│   │       Tests → tests/preprocessing/test_kriging.py
│   │       Docs → docs/task_kriging_interpolation.md
│   │
│   ├── کنترل کیفیت
│   │   └── src/preprocessing/qc.py
│   │       Tests → tests/preprocessing/test_qc.py
│   │       Docs → docs/task_wind_qc.md
│   │
│   ├── پیوستگی مکانی-زمانی
│   │   └── src/preprocessing/consistency.py
│   │       Tests → tests/preprocessing/test_consistency.py
│   │       Docs → docs/task_spatiotemporal_consistency.md
│   │
│   └── آماده‌سازی داده مسیریابی
│       └── src/preprocessing/data_prep.py
│           Tests → tests/preprocessing/test_data_prep.py
│           Docs → docs/task_data_prep_pathfinding.md
│
├── مسیریابی (گام ۳)
│   ├── ساخت گراف
│   │   └── src/pathfinding/graph.py
│   │       Tests → tests/pathfinding/test_graph.py
│   │
│   ├── الگوریتم‌ها (A*, Dijkstra)
│   │   └── src/pathfinding/algorithms.py
│   │       Tests → tests/pathfinding/test_algorithms.py
│   │
│   └── بهینه‌سازی مسیر
│       └── src/pathfinding/routing.py
│           Tests → tests/pathfinding/test_routing.py
│
└── مستندات / CI / ساختار پروژه
    └── docs/ یا .github/
```

---

## قوانین کلی

1. **هر تسک فقط یک فایل `*.py` ایجاد می‌کند** در ماژول مربوطه — نه هیچ‌کجا دیگر.
2. **هر ماژول `*.py` یک فایل `test_*.py` جداگانه دارد** در پوشه تست متناظر.
3. **هر تسک یک مستند طراحی دارد** در `docs/task_*.md` — از فایل `tasks/templates/task_template.md` استفاده کنید.
4. **`__init__.py` فقط آن ماژولهایی را import می‌کند که واقعاً وجود دارند** — ماژولهای آینده (tbd) را import نکنید.
5. **فایل داده خام (`data/*.csv`, `data/*.json`) را تغییر ندهید** — اینها input ثابت هستند.
6. **`docs/PROJECT_PROGRESS.md` را فقط append کنید** — بخشهای قبلی را دست نزنید.

---

## نامگذاری شاخه و PR

```
task/<clickup-task-id>-<short-slug>
```

مثال: `task/86bba36de-idw-interpolation`

- اسلگ انگلیسی، با خط تیره
- شناسه تسک ClickUp (اگر دارید)
- حداکثر ۴۰ کاراکتر