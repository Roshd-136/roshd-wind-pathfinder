# تحلیل کامل کدبیس — Roshd Wind Pathfinder

> تاریخ: اکتبر ۲۰۲۶ · شاخهٔ بررسی‌شده: `task/ui-foundation` (کامیت `f8d85a4` + تغییرات کاری)
> این سند فقط تحلیل است — هیچ فایل کدی تغییر نکرده.

---

## ۱. روش بررسی

- خواندن مستقیم ماژول‌های اصلی بک‌اند (~۱۳٫۳ هزار خط Python) و فرانت‌اند (~۹٫۳ هزار خط TS/TSX شامل `src/three/`).
- راستی‌آزمایی هر یافته با `grep` و ارجاع `file:line` بلافاصله پیش از ثبت.
- مقایسهٔ قراردادها: `api/openapi.yaml` ↔ روترهای بک‌اند ↔ سرویس‌های فرانت‌اند.
- بررسی ساختار تست (۱۳ فایل pytest با ~۱۸۸ تست، ۱۰ فایل vitest با ~۴۰ تست) و CI (`.github/workflows/ci.yml`).
- تطبیق قواعد `AGENTS.md` (زبان فارسی، ساختار `src/`، سبک کامیت) با وضعیت واقعی مخزن.

---

## ۲. نقشهٔ معماری

```
دادهٔ خام (Open-Meteo، DEM)                فرانت‌اند (React 19 + Vite)
        │                                          │
        ▼                                          ▼
scripts/fetch_khorasan_data.py            صفحات: Map2D / Map3D / Auth /
        │                                  Settings / Profile / Onboarding
        ▼                                          │
src/preprocessing (IDW، Kriging،        ┌──────────┴──────────┐
  consistency، pathfinding_preparation) │                     │
        │                               ▼                     ▼
        ▼                          MapLibre 2D          صحنهٔ 3D دست‌ساز
src/qc/wind_qc.py                  (windFieldLayer:      (src/three/manual:
        │                           میدان رنگی + جریان    scene.ts + scene-gl.ts
        ▼                           ذرات باد)             WebGL خام، بدون three.js)
src/pathfinding (graph، routing،          │                     ▲
  algorithms، cost، wind_riding،          ▼                     │
  effort، geometry، profile،         usePathfinding ──► POST /v1/routes
  alignment)                              │
        │                                 ▼
        ▼                          services/api/* (apiFetch + refresh توکن)
src/viz (scene3d برای خروجی HTML،
  wind_field برای لایه‌های API)           بک‌اند (FastAPI)
        │                                          ▲
        └──► src/api/routers:                      │
             routes · wind_layers · points ────────┘
             algorithms · auth · account
```

**جریان دادهٔ اصلی:** CSVهای پاک‌شدهٔ خراسان (`data/*.csv`) → ساخت میدان باد چندلایه در
`src/viz/wind_field.py` (نمایهٔ توانی + چرخش اکمان روی باد سطح ۱۰م) → کش در روتر
`wind_layers` → فرانت‌اند سه لایهٔ UI (سطحی ۰–۵۰، میانی ۵۰–۲۰۰، بالای ۲۰۰–۵۰۰ متر AGL)
→ درخواست مسیر با مبدأ/مقصد/الگوریتم/معیار → موتور `pathfinding` → نتیجه روی نقشه/صحنه.

**نکتهٔ صداقت داده (مستندشده در `src/viz/wind_field.py`):** پروژه فقط باد سطح (۱۰ متر)
را دارد؛ لایه‌های ارتفاعی سنتزی‌اند (power-law با نمای ≈۰٫۲۵ + چرخش اکمان ۲۰–۴۵ درجه).
این در ماژول viz صادقانه برچسب خورده — اما لایهٔ API این برچسب را به کلاینت نمی‌رساند
(بخش یافتهٔ ۱۵).

---

## ۳. فهرست ماژول‌ها

### بک‌اند (Python — ~۱۳٫۳k خط)

| مسیر | خط | نقش |
|---|---|---|
| `src/pathfinding/graph.py` | ۱۲۳۴ | گراف چندلایهٔ باد (`MultiLayerWindGraph`) |
| `src/pathfinding/wind_riding.py` | ۱۵۴۰ | خانوادهٔ مسیرهای بادسواری (خارج از گراف) |
| `src/pathfinding/routing.py` | ۱۰۴۸ | `WindRouter` و نتایج مسیر |
| `src/pathfinding/geometry.py` | ۸۴۰ | هندسهٔ مسیر |
| `src/pathfinding/effort.py` | ۴۸۹ | مدل زحمت موتور |
| `src/pathfinding/algorithms.py` | ۴۷۸ | A*، Dijkstra، … |
| `src/pathfinding/cost.py` | ۳۲۵ | مدل هزینه — ۵ معیار: time/energy/balanced/distance/safety |
| `src/pathfinding/profile.py` | ۴۵۰ | پروفایل ارتفاع/انرژی |
| `src/pathfinding/alignment.py` | ۲۱۳ | زاویهٔ هم‌راستایی با باد |
| `src/viz/scene3d.py` | ۳۱۳۴ | صحنهٔ تعاملی HTML خودکفا (خروجی ~۷MB) |
| `src/viz/wind_field.py` | ~۶۰۰ | میدان باد لایه‌ای + گراف برای صحنه‌ها |
| `src/viz/terrain.py` | ~۳۰۰ | مدل ارتفاع DEM |
| `src/api/routers/routes.py` | ۵۹۱ | مسیریابی همگام/غیرهمگام + jobs |
| `src/api/routers/auth.py` | ۱۷۶ | JWT login/register/refresh/logout |
| `src/api/routers/account.py` | ۱۳۸ | پروفایل/ترجیحات/تاریخچه |
| `src/api/routers/wind_layers.py` | ۱۵۵ | لایه‌های باد + نقطه‌ای |
| `src/api/routers/points.py` | ۱۰۳ | CRUD نقاط ذخیره‌شده (mock) |
| `src/api/routers/algorithms.py` | ۹۰ | متادیتای الگوریتم/معیار |
| `src/api/main.py` | ۶۱ | مونتاژ روترها با پیشوند `/v1` |
| `src/preprocessing` | ۹۱۳ | IDW، Kriging، سازگاری زمانی-مکانی |
| `src/data/cache.py` | ۲۰۶ | کش واکشی داده |
| `src/qc/wind_qc.py` | ۱۱۶ | پاک‌سازی QC باد |

### فرانت‌اند (TypeScript/React — ~۹٫۳k خط)

| مسیر | خط | نقش |
|---|---|---|
| `src/three/manual/scene-gl.ts` | ۱۰۶۹ | موتور WebGL خام صحنهٔ 3D |
| `src/three/manual/scene.ts` | ۷۰۸ | محاسبات صحنه (smooth، tube، mesh) |
| `src/three/manual/mat4.ts` | ۱۶۴ | ریاضیات ماتریس |
| `src/components/features/map/windFieldLayer.ts` | ~۵۰۰ | میدان رنگی + جریان ذرات باد (سبک windy) |
| `src/components/features/map/route3dLayer.ts` | ۵۱۹ | لایهٔ 3D روی MapLibre — **کد مرده** (یافتهٔ ۵) |
| `src/components/features/map/MapView.tsx` | ~۶۰۰ | سیم‌کشی نقشهٔ 2D/3D |
| `src/components/features/map/ManualSceneView.tsx` | ۱۴۴ | پوشش React صحنهٔ 3D |
| `src/components/features/routing/*` | ~۱٫۵k | پنل اطلاعات، ویزارد مراحل، انتخاب الگوریتم |
| `src/store/*` | ~۳۰۰ | zustand: مسیر، تنظیمات، UI |
| `src/services/api/*` | ۲۷۵ | apiFetch + ۵ سرویس + refresh توکن |
| `src/hooks/*` | ~۲۰۰ | usePathfinding، useWindData، useAuth، useProfile |
| `src/i18n/locales/{fa,en}.json` | ۱۳۱ کلید در ۱۶ فضای نام | برابری کامل fa/en (مثبت — بدون انحراف) |

---

## ۴. یافته‌ها

### شدت: بالا

**۱. شکاف قرارداد API — سه شکل همزمان** (`api/openapi.yaml` ↔ `src/api/routers/*` ↔ `frontend/src/services/api/*`)

- **مسیرهای حساب:** اسپک `/me`، `/me/preferences`، `/me/routes` (openapi.yaml:473,501,529) —
  بک‌اند `/account`، `/account/preferences`، `/account/history` (account.py:12) —
  فرانت‌اند `/v1/account/*` (account.ts:31,35). کار می‌کند، اما اسپک از واقعیت عقب است.
- **فرانت‌اند بدون پیشوند `/v1`:** سه فراخوانی `requestPasswordReset`/`confirmPasswordReset`/`verifyEmail`
  به `/auth/password-reset/*` و `/auth/verify-email/confirm` می‌روند **بدون** `/v1`
  (auth.ts:33,38,46) — برخلاف بقیهٔ فراخوانی‌ها (auth.ts:20,25,52).
- **اندپوینت‌های اسپک‌شده که در بک‌اند وجود ندارند:** `password-reset`، `verify-email`،
  `oauth/{provider}`، `points/favorites` — هیچ‌کدام در روترها پیاده نشده‌اند
  (grep روی `src/api/` خالی است). یعنی فرم‌های «فراموشی رمز»، «بازنشانی» و «تأیید ایمیل»
  (`ForgotPasswordForm.tsx`، `ResetPasswordForm.tsx`، `VerifyEmailPanel.tsx`) همیشه 404 می‌گیرند.

**توصیه:** یکی کردن منبع حقیقت — اسپک را از کد بازتولید کنید (FastAPI خودش `/openapi.json`
می‌سازد) یا قرارداد را قفل کنید؛ پیشوند `/v1` سه فراخوانی فوراً اصلاح شود؛ برای
password-reset/verify-email یا پیاده‌سازی یا حذف از UI تا فاز بعد.

**۲. احراز هویت mock با رمزِ هاردکد** (`src/api/routers/auth.py`)

- `JWT_SECRET = "dev-secret-change-in-production"` (auth.py:16) — در کد.
- رمزها **بدون هش** در دیکشنری حافظه ذخیره می‌شوند (auth.py:125، کامنت «In production:
  hash with bcrypt»)؛ استور `_users` با ری‌استارت خالی می‌شود (auth.py:36).
- هیچ وابستگی به DB یا `Depends` برای محافظت از اندپوینت‌ها نیست؛
  `account.py` و `points.py` هم کاملاً بدون احراز کار می‌کنند.

**توصیه:** تا قبل از هر استقرار واقعی: secret از محیط، هش با bcrypt (وابستگی جدید
نیاز به تأیید مالک دارد)، و `Depends(get_current_user)` روی `/account/*` و `/points/*`.

**۳. قیدهای UI بی‌اثر روی محاسبهٔ مسیر** (`src/api/routers/routes.py`)

فرانت‌اند `max_wind_speed_mps`، `altitude_range_m` و `avoid_zones` را می‌فرستد
(`RouteConstraints` در types/routing.ts:40-54) و بک‌اند آن‌ها را در مدل می‌پذیرد
(routes.py:50-52) — اما `compute_route_sync` فقط `criterion` را می‌خواند (routes.py:258)
و بقیهٔ قیدها در هیچ‌جای محاسبه استفاده نمی‌شوند. کاربر فیلتر می‌گذارد، نتیجه تغییری نمی‌کند.

**توصیه:** یا اعمال کردن در موتور (فیلتر لبه‌های گراف بر باد/ارتفاع، جریمهٔ avoid_zones)
یا غیرفعال‌سازی صریح آن فیلترها در UI با برچسب «به‌زودی» — صداقت رفتاری.

**۴. `node_modules` ریشهٔ مخزن در گیت کامیت شده** (۱۰۸۴ فایل ردیابی‌شده)

`git ls-files node_modules | wc -l` → ۱۰۸۴ فایل؛ `.gitignore` ریشه (`30` خط) **هیچ**
مدخلی برای `node_modules` ندارد (فقط `frontend/.gitignore` دارد). `package.json` ریشه
فقط `maplibre-gl` را اعلام می‌کند و هیچ کدی از آن import نمی‌گیرد — نصب تصادفی در ریشه
بوده و همراه با `.bin/` کامیت شده است.

**توصیه:** `git rm -r --cached node_modules` + افزودن `node_modules/` به `.gitignore` ریشه
+ حذف `package.json`/`package-lock.json` بی‌استفادهٔ ریشه (اگر چیزی به آن وابسته نیست).

### شدت: متوسط

**۵. کد مرده: `route3dLayer.ts` هرگز داده نمی‌گیرد** (۵۱۹ خط)

در `MapView.tsx:304` ساخته می‌شود، در `:309-310` حذف می‌شود و **هیچ** `setData`ای
در کل فایل روی `route3dRef.current` صدا زده نمی‌شود؛ ورودی `path3d` در `:224` با
`void path3d` عمداً دور انداخته می‌شود. رندر واقعی 3D مسیر در `ManualSceneView3D`
(`src/three/manual/`) است.

**توصیه:** حذف کامل `route3dLayer.ts` + ref‌هایش، یا اتصال واقعی — نگه‌داشتنِ نیمه‌وصل
باعث دوقلو شدن ریاضیات می‌شود (یافتهٔ ۶).

**۶. ریاضیات سه‌بار تکرار شده** (`smoothRoute` + tube)

- `src/viz/scene3d.py:901` (`_smooth_route`) و `:934` (`_route_tube`)
- `frontend/src/three/manual/scene.ts:275-430`
- `frontend/src/components/features/map/route3dLayer.ts:86-262` (کد مرده)

سه پیاده‌سازی مستقل از یک الگوریتم یعنی هر اصلاح باید سه‌جا اعمال شود.

**توصیه:** مرجع واحد: بک‌اند مسیر هموارشده را بفرستد، یا یک ماژول مشترک TS برای هر دو
لایهٔ فرانت. حذف route3dLayer یکی از سه نسخه را رایگان حذف می‌کند.

**۷. وابستگی بلااستفاده: `mapbox-gl`** (`frontend/package.json:23,42`)

`mapbox-gl ^3.31.0` و `@types/mapbox-gl ^3.4.1` هیچ importی ندارند (تنها اشاره،
کامنت در `MapView.test.tsx:58`). کتابخانهٔ واقعی `maplibre-gl` است (fork آزاد mapbox).

**توصیه:** حذف هر دو مدخل از `package.json` (هم وزن نصب، هم ریسک لایسنس/سوءتفاهم).

**۸. انحراف فهرست معیارها بین چهار لایه**

- موتور هزینه: ۵ معیار (`cost.py:39` — time/energy/balanced/distance/safety)
- مدل API و متادیتا: ۳ معیار (`routes.py:53` «literal 5تایی» ولی `algorithms.py:26`
  فقط ۳ تا، `openapi.yaml:691` فقط ۳ تا)
- تایپ فرانت: ۵ معیار (`types/routing.ts:17`)
- UI (PathInfoPanel): فقط زیرمجموعه

یعنی `distance` و `safety` از موتور قابل استفاده‌اند ولی هیچ مسیر رسمی به کاربر نمی‌رسد.

**توصیه:** هم‌تراز کردن `algorithms.py` و `openapi.yaml` با موتور (یا تصمیم صریح برای
مخفی‌نگه‌داشتن دو معیار)، و افزودنشان به `CriterionInfo`.

**۹. پیکربندی «وسیله» جزیره است** (`defaultVessel`)

تنظیم در `SettingsPage.tsx:91-93` و ذخیره در `useSettingsStore` — اما هیچ کد مسیریابی
آن را نمی‌خواند: `RouteRequest.constraints.vessel` در types تعریف شده (routing.ts:48-53)
و بک‌اند هم می‌پذیرد (routes.py:56, 268-270)، ولی هیچ UIای آن را پر نمی‌کند
(grep «defaultVessel» خارج از settings خالی). انتخاب کاربر هرگز به محاسبه نمی‌رسد.

**توصیه:** هنگام ساخت `constraints` در `RoutingMapScreen.tsx:97`، `defaultVessel`
را از استور تنظیمات به پیکربندی vessel نگاشت کنید.

**۱۰. همگام‌سازی ترجیحات وعده داده شده ولی وصل نشده** (`useSettingsStore`، `useProfile.ts`)

داک‌استور `useSettingsStore.ts:27-29` می‌گوید «وقتی کاربر لاگین است با
`GET/PUT /me/preferences` همگام می‌شود (فاز ۳)». `useProfile.ts` هر دو کوئری/موتیشن را
دارد، اما هیچ پلی بین پاسخ سرور و استور تنظیمات نیست — `useProfile.ts` و
`ProfilePage.tsx` هرگز `useSettingsStore` را صدا نمی‌زنند.

**توصیه:** یک `useEffect` پل در `ProfilePage` یا داخل `usePreferences` که موفقیت
واکشی را در استور بنویسد (و برعکس، تغییر استور را PUT کند).

**۱۱. تست‌های 3D و CI فرانت‌اند غایب‌اند**

- هیچ تستی برای `src/three/manual/*` (۲٬۰۸۵ خط WebGL) و `route3dLayer.ts` نیست؛
  ۱۰ سوییت vitest فقط UI/utils را پوشش می‌دهند. داک‌استور `scene.ts` ادعای
  «هر تابع خالص تا در تست قابل بررسی باشد» دارد — محقق نشده.
- `ci.yml` فقط ruff+pytest پایتون را اجرا می‌کند؛ `vitest`، `eslint` و `tsc -b`
  فرانت‌اند هرگز در CI نمی‌روند.

**توصیه:** جاب فرانت‌اند در ci.yml (npm ci → lint → typecheck → test)؛ برای `scene.ts`
تستِ خروجی توابع خالص (smooth/tube) با fixture کوچک.

**۱۲. ذخیره‌گاه‌های mock بدون پایداری** (`_users` auth.py:36، `_points` points.py:45)

هر دو دیکشنری در حافظه‌اند؛ با ری‌استارت پروسه پاک می‌شوند. ضمناً API نقاط
(`points.py`) توسط فرانت‌اند صدا زده نمی‌شود (grep روی `services/api/` خالی) —
کد و نگهداری بدون مصرف‌کننده.

**توصیه:** اگر نقاط ذخیره‌شده در نقشهٔ محصول است، به DB وصل شود؛ وگرنه روتر تا فاز
مربوطه حذف یا خاموش شود.

### شدت: کم

**۱۳. بارگذاری گرید O(n²)** — `frontend/src/three/manual/scene.ts:120-131`:
`lats.indexOf(c.lat)` و `lons.indexOf(c.lon)` به‌ازای هر سلول. برای شبکهٔ خراسان
قابل تحمل است، ولی با `Map` از `lat→index` خطی می‌شود.

**۱۴. هک‌های `sys.path` و پکیجینگ ناقص** — `wind_layers.py:15`، `routes.py:143`،
اسکریپت‌ها `sys.path.insert` می‌کنند و importها به شکل `from pathfinding…`، `from viz…`
(نه `src.pathfinding…`) هستند. در عین حال `[tool.setuptools.packages.find]`
در `pyproject.toml` فقط `data*/preprocessing*/pathfinding*/qc*` را شامل می‌شود —
`api*` و `viz*` جا مانده‌اند؛ یعنی `pip install -e .` نصب ناقص می‌دهد و همه‌چیز به
هک sys.path تکیه دارد. `pytest --import-mode=append` هم این را پنهان می‌کند.

**۱۵. برچسب سنتز بودن لایه‌ها به کلاینت API نمی‌رسد** — `viz/wind_field.py` در
داک‌استور صادقانه می‌گوید لایه‌های ارتفاعی سنتزی‌اند، ولی `wind_layers.py`
خودش را «real station data and interpolation» معرفی می‌کند (wind_layers.py:5-6)
و هیچ فیلدی مثل `synthetic: true` یا یادداشت مدل در پاسخ `/wind-layers` نیست.

**۱۶. کش ادعاشده اما غیرفعال در روتر باد** — `wind_layers.py:31-33` متغیرهای
`_station_cache` و غیره را تعریف می‌کند ولی کامنت می‌گوید «For now, recompute each
time» (wind_layers.py:42)؛ هر GET میدان، خواندن CSV + IDW + ساخت لایه‌ها را از نو انجام می‌دهد.

**۱۷. دو هدف پکیج همزمان: Tauri و Capacitor** — `src-tauri/` (دسکتاپ) و
`capacitor.config.ts` + اسکریپت `cap:sync` (موبایل) هر دو فعال‌اند. اگر هر دو مقصودند
اشکالی ندارد؛ فقط باید در داک مستند شود چون نگهداری دوخطی دارد.

**۱۸. آرتیفکت ۷MB و پرتغییر در گیت** — `docs/assets/routing_scene.html`
(۷٬۰۲۸٬۶۹۵ بایت، plotly جاسازی‌شده) ردیابی شده و همین الان هم `modified` است؛
هر بازتولید یک diff چندمگابایتی در تاریخچه می‌گذارد.

**۱۹. بقایای `tests/api` حذف‌شده** — سورس تست‌های API فقط روی شاخهٔ
`task/86bc860cr-backend-layer` (کامیت `10be71c`) وجود دارد؛ در شاخهٔ فعلی حذف شده‌اند
ولی `tests/api/__pycache__/*.pyc` محلی باقی مانده. فرصت: آن تست‌ها (auth/account/
routing/wind-layers — ۵۱۰ خط) هنوز نوشته نشده‌اند و برای یافتهٔ ۱ و ۲ لازم‌اند.

### نقاط قوت مشاهده‌شده

- **فرهنگ صداقت داده:** برچسب صریح «سنتزی» در `viz/wind_field.py`، برچسب
  «مسیر نمایشی» روی فال‌بک dev در `RoutingMapScreen.tsx:105-119`.
- **برابری کامل fa/en** در i18n (۱۳۱/۱۳۱ کلید، بدون انحراف).
- **پوشش تست خوب در موتور:** ~۱۸۸ تست pytest شامل end-to-end مسیریابی.
- **تفکیک تمیز لایه‌ها** در هر دو سمت (روترها مستقل، سرویس‌های فرانت نازک).
- **ریاضیات ماتریس دست‌ساز بدون وابستگی three.js** — کنترل کامل روی خروجی WebGL.

---

## ۵. ریسک‌ها

| ریسک | اثر | رابطه |
|---|---|---|
| استقرار با auth mock | هر کسی هر حسابی می‌سازد؛ توکن با secret عمومی قابل جعل | یافتهٔ ۲ |
| بی‌اثری فیلترها | اعتماد کاربر به خروجی مسیر آسیب می‌بیند | یافتهٔ ۳ |
| drift قرارداد | هر تغییری در یکی از سه لایه بقیه را می‌شکند؛ تست قراردادی وجود ندارد | یافتهٔ ۱ |
| پکیجینگ ناقص | استقرار با `pip install` در محیط تمیز شکست می‌خورد | یافتهٔ ۱۴ |
| تورم تاریخچه گیت | آرتیفکت‌های چندمگابایتی clone/checkout را سنگین می‌کنند | یافتهٔ ۱۸ |
| نبود CI فرانت‌اند | رگرسیون UI بدون هیچ گیت merge می‌شود | یافتهٔ ۱۱ |

---

## ۶. توصیه‌های اولویت‌بندی‌شده

**P1 — پیش از هر استقرار/دموی بیرونی**
1. اصلاح پیشوند `/v1` در سه فراخوانی auth (`frontend/src/services/api/auth.ts:33,38,46`).
2. تصمیم دربارهٔ password-reset/verify-email: پیاده‌سازی یا حذف فرم‌ها تا فاز بعد.
3. Secret محیطی + هش bcrypt + گارد `/account/*` و `/points/*`.
4. پاک‌سازی `node_modules` ریشه از گیت + `.gitignore`.

**P2 — کیفیت و اعتماد**
5. اعمال یا غیرفعال‌سازی صریح قیدهای `max_wind_speed_mps`/`altitude_range_m`/`avoid_zones`.
6. اتصال `defaultVessel` به درخواست مسیر.
7. بازتولید/هم‌ترازسازی `api/openapi.yaml` با بک‌اند (ترجیحاً از `/openapi.json`).
8. جاب CI فرانت‌اند + تست برای `src/three/manual/scene.ts`.
9. حذف `route3dLayer.ts` (کد مرده) و با آن یک نسخه از تکرار ریاضیات.

**P3 — بهداشت بلندمدت**
10. تکمیل `pyproject.toml` (افزودن `api*`، `viz*`) و حذف تدریجی هک‌های sys.path.
11. فیلد `synthetic`/یادداشت مدل در پاسخ `/wind-layers`.
12. فعال‌کردن کش واقعی در `wind_layers.py`.
13. پیاده‌سازی پل ترجیحات سرور ↔ استور محلی (یافتهٔ ۱۰).
14. تصمیم مستند دربارهٔ Tauri/Capacitor و محل آرتیفکت‌های سنگین (LFS یا release asset).

---

## ۷. جمع‌بندی

کدبیس از نظر معماری سالم و خواناست: تفکیک لایه‌ها تمیز است، موتور مسیریابی
پوشش تست خوبی دارد و فرهنگ مستندسازی فارسی رعایت می‌شود. ریسک‌های اصلی
همه در **لبه‌ها** هستند: قرارداد API سه‌شکافه، احراز هویت نمایشی، قیدهای UI بی‌اثر،
و بهداشت مخزن (node_modules و آرتیفکت‌های سنگین). هیچ‌یک از این‌ها بازنویسی
می‌خواهد — همه با کارهای کوچکِ فهرست P1/P2 بسته می‌شوند.
