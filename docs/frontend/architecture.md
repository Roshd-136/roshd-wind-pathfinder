# معماری فنی رابط کاربری — Roshd Wind Pathfinder (گام ۴)

**تاریخ:** ۶ مهر ۱۴۰۵
**مسئول:** امیرعلی
**وضعیت:** در حال انجام (فاز ۱ از ۳)
**اولویت:** بالا (High)
**ددلاین:** ۷ مهر ۱۴۰۵، ساعت ۲۰:۰۰ به وقت ایران
**برچسب:** گام ۴

> این سند بخش «معماری فنی» (آیتم ۱) و به‌همراه `api/openapi.yaml` بخش
> «قرارداد API» (آیتم ۲) از تسک `86bc860cq` را پوشش می‌دهد — فاز ۱ از پلن
> سه‌فازی توافق‌شده (۱- معماری+API، ۲- اسکلت React+سیستم طراحی، ۳-
> صفحات/کامپوننت‌ها). فازهای ۲ و ۳ در PRهای بعدی همین تسک تکمیل می‌شوند.

---

## مرجع بصری (mockup)

فایل `ui_mockup.png` (پیوست تسک ClickUp) یک اسلاید مفهومی/pitch است، نه
یک فایل Figma کامل برای تک‌تک صفحات — صفحات Settings کامل، Auth، Profile و
Onboarding در آن نیامده‌اند. آنچه از آن استخراج و در فاز ۲/۳ به‌عنوان
Design Tokens استفاده می‌شود:

- **تم:** تیره (dark) به‌صورت پیش‌فرض؛ پس‌زمینه navy تیره، کارت‌ها با
  پس‌زمینه کمی روشن‌تر و حاشیه ظریف آبی-خاکستری، گوشه‌های گرد.
- **رنگ accent:** آبی روشن (اطراف `#3B82F6`–`#4F9CFF`) برای دکمه اصلی
  («Calculate Path»)، آیکون‌های فعال، و نشانگرهای انتخاب.
- **Legend سرعت باد:** گرادیان آبی (کم) → سبز → زرد → قرمز (زیاد)، با
  برچسب‌های عددی `0/5/10/15/20+ m/s` — این دقیقاً همان قرارداد رنگی است
  که باید در `WindLayerControls` و روی نقشه استفاده شود.
- **الگوی چیدمان:** sidebar چپ باریک (لوگو/نام برنامه + Map/Settings/About)
  + ناحیه نقشه در وسط با toggle دوحالته 2D/3D بالا + پنل کنترل سمت راست
  (Algorithm، Wind Layer Filter با چک‌باکس هر لایه، Constraints با اسلایدر،
  legend، دکمه CTA ثابت پایین پنل).
- **پاپ‌آپ Point Info:** کارت کوچک روی نقشه با لیست لایه‌ها و سرعت هر کدام.
- **دسکتاپ/موبایل:** همان ساختار در قاب پنجره دسکتاپ و صفحه موبایل باریک‌تر
  تکرار می‌شود؛ طبق متن تسک، در موبایل sidebar باید به drawer و نتایج به
  bottom sheet تبدیل شوند (در تصویر مستقیماً نشان داده نشده، اما با الگوی
  عمومی PWAهای موبایل سازگار است).

صفحاتی که در mockup نیامده‌اند (Settings مستقل، Auth، Profile، Onboarding)
در فاز ۳ با همین Design Tokens و همان الگوی کارت/پنل طراحی می‌شوند تا
یکدست بمانند؛ چون مرجع تصویری مستقیمی ندارند، «پیکسل‌به‌پیکسل» برایشان
معنا ندارد — معیار برایشان تبعیت کامل از سیستم طراحی استخراج‌شده است.

---

## معماری یک کدبیس (آیتم ۱)

```
                        ┌─────────────────────────┐
                        │   src/ (React + TS)      │
                        │   یک کدبیس واحد          │
                        └───────────┬─────────────┘
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                   ▼
         ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐
         │  Web / PWA     │  │  Desktop       │  │  Mobile           │
         │  Vite build    │  │  Tauri wrapper │  │  Capacitor wrapper│
         │  + Service     │  │  (Windows/     │  │  (iOS/Android)    │
         │  Worker        │  │  macOS/Linux)  │  │                   │
         └───────────────┘  └───────────────┘  └──────────────────┘
```

- **یک کدبیس، سه خروجی:** هیچ شاخه‌بندی کد بر اساس پلتفرم وجود ندارد.
  تفاوت پلتفرم‌ها فقط در لایه بسته‌بندی (`tauri.conf.json`،
  `capacitor.config.ts`) و یک لایه نازک تشخیص پلتفرم (`src/platform/`)
  برای قابلیت‌های native (مثل file system یا notifications) است.
- **Web/PWA:** خروجی مستقیم `vite build`؛ manifest.json + service worker
  (`vite-plugin-pwa`) برای نصب‌پذیری و کش آفلاین.
- **Desktop (Tauri):** همان build وب داخل یک shell سبک Rust؛ در آینده
  (تسک بک‌اند) سرور FastAPI به‌صورت Tauri sidecar کنار اپ دسکتاپ اجرا
  می‌شود.
- **Mobile (Capacitor):** همان build وب داخل WebView بومی iOS/Android.

### پشته فنی (مطابق mockup + تسک)
| لایه | انتخاب | دلیل |
|---|---|---|
| UI | React 18 + TypeScript | مطابق mockup و تسک |
| Build | Vite | سرعت dev/build |
| استایل | Tailwind CSS | مطابق mockup؛ توکن‌های طراحی در فاز ۲ |
| مسیریابی صفحات | React Router | مطابق mockup |
| نقشه | Mapbox GL JS | 2D/3D، مطابق mockup |
| Server state / کش API | TanStack Query | کش، retry، invalidation خودکار برای `services/api` |
| Client state سبک | Zustand | حالت UI (پنل باز/بسته، لایه انتخابی، تم) بدون boilerplate رداکس |
| فرم‌ها + اعتبارسنجی | React Hook Form + Zod | فرم‌های Auth/Settings؛ Zod schemaها از OpenAPI قابل اشتقاق‌اند |
| i18n / RTL | i18next + react-i18next | فارسی (RTL) و انگلیسی، مطابق آیتم ۷ |
| تست واحد/کامپوننت | Vitest + React Testing Library | سریع، سازگار با Vite |
| تست E2E | Playwright | جریان‌های کامل (انتخاب مبدأ/مقصد → مسیر) |
| بسته‌بندی دسکتاپ | Tauri 2 | سبک‌تر از Electron |
| بسته‌بندی موبایل | Capacitor 6 | همان کدبیس وب |

---

## ساختار پروژه (آیتم ۳ — برای فاز ۲)

ترکیب ساختار پیشنهادی mockup با جزئیات کامل‌تر متن تسک (که Auth/Profile/
types/workers را هم می‌خواهد):

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── ui/                  # پریمیتیوها: Button, Card, Slider, Checkbox, Dropdown...
│   │   └── features/
│   │       ├── map/             # MapView, LayerLegend, PointInfoPopup
│   │       ├── routing/         # AlgorithmSelector, PathInfoPanel, RouteFiltersPanel
│   │       ├── layers/          # WindLayerControls
│   │       ├── settings/
│   │       ├── auth/
│   │       └── profile/
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   ├── Map2DPage.tsx
│   │   ├── Map3DPage.tsx
│   │   ├── SettingsPage.tsx
│   │   ├── ResultsPage.tsx
│   │   ├── AuthPage.tsx         # login/register/reset (تب‌بندی‌شده)
│   │   ├── ProfilePage.tsx
│   │   └── OnboardingPage.tsx
│   ├── hooks/
│   │   ├── useWindData.ts
│   │   ├── usePathfinding.ts
│   │   ├── useSettings.ts
│   │   ├── useAuth.ts
│   │   └── useProfile.ts
│   ├── services/
│   │   └── api/                 # typed client — تولیدشده/هم‌راستا با api/openapi.yaml
│   │       ├── client.ts        # instance fetch/axios + auth interceptor
│   │       ├── routing.ts
│   │       ├── windLayers.ts
│   │       └── auth.ts
│   ├── types/                   # types مشترک با بک‌اند (از schemaهای OpenAPI)
│   ├── workers/                 # Web Worker برای محاسبات سنگین کلاینت (مثلاً رندر میدان بردار)
│   ├── platform/                # تشخیص Tauri/Capacitor/Web + قابلیت‌های native
│   ├── store/                   # Zustand stores
│   ├── i18n/                    # فارسی/انگلیسی
│   └── assets/styles/
├── tauri.conf.json
├── capacitor.config.ts
├── package.json
└── vite.config.ts
```

نام‌گذاری کامپوننت‌های کلیدی (`MapView`, `WindLayerControls`,
`AlgorithmSelector`, `PathInfoPanel`, `MobileBottomSheet`) دقیقاً مطابق
mockup نگه داشته شده تا هیچ ابهامی بین سند و تصویر مرجع نباشد.

---

## قرارداد API (آیتم ۲)

فایل کامل: [`api/openapi.yaml`](../../api/openapi.yaml) (OpenAPI 3.0،
اعتبارسنجی‌شده با `openapi-spec-validator`).

خلاصه endpointها:

| گروه | Endpointها |
|---|---|
| مسیریابی | `POST /routes` (sync/async)، `GET /routes/jobs/{jobId}` (پیشرفت)، `GET /routes/jobs/{jobId}/compare-layers`، `GET/DELETE /routes/{routeId}` |
| لایه‌های باد | `GET /wind-layers`، `GET /wind-layers/{altitude}/field`، `GET /wind-layers/{altitude}/point`، `GET /wind-layers/point-all` |
| نقاط | `GET/POST /points/favorites`، `DELETE /points/favorites/{id}` |
| الگوریتم‌ها | `GET /algorithms` |
| احراز هویت | `register`, `login`, `refresh`, `logout`, `password-reset/*`, `verify-email/*`, `oauth/{provider}/*` |
| حساب کاربری | `GET/PATCH /me`, `GET/PUT /me/preferences`, `GET /me/routes` |

نکات طراحی قرارداد:
- **sync/async مسیریابی:** با گراف فعلی (۳ ایستگاه) پاسخ همیشه sync و
  فوری است؛ فیلد `async: true` در `RouteRequest` مسیر ۲۰۲+polling/WS را
  برای گراف‌های بزرگ‌تر آینده از هم‌اکنون در قرارداد باز می‌گذارد، تا
  بک‌اند مجبور به breaking change نشود.
- **چک‌پوینت‌های اجباری:** آرایه `checkpoints` در `RouteRequest`، هرکدام
  با `order` برای ترتیب عبور اجباری.
- **فیلترهای پیشرفته:** `RouteConstraints` شامل `max_wind_speed_mps`،
  `altitude_range_m`، `avoid_zones`، `criterion` (زمان/انرژی/متعادل) و
  `weights`.
- **خطاها:** همه پاسخ‌های خطا یک `Error`/`ValidationErrorBody` یکسان با
  `request_id` برمی‌گردانند تا لاگ‌ها بین فرانت و بک قابل ردیابی باشند؛
  `429` هدرهای rate-limit استاندارد دارد.
- **امنیت:** `bearerAuth` (JWT) پیش‌فرض روی همه endpointها؛ مسیرهای عمومی
  (auth، مشاهده لایه‌های باد، محاسبه مسیر مهمان) با `security: []`
  صریحاً override شده‌اند — یعنی محاسبه مسیر بدون لاگین هم کار می‌کند
  (تجربه mockup: مستقیم روی نقشه کلیک و مسیر گرفتن)، ولی ذخیره در
  تاریخچه/علاقه‌مندی‌ها نیاز به احراز هویت دارد.

---

## دسترسی‌پذیری، RTL، تم (آیتم ۷ — پایه‌ریزی، تکمیل در فاز ۳)

- **RTL:** `dir="rtl"` پیش‌فرض برای فارسی (i18next + Tailwind `rtl:` variants)؛ Mapbox و آیکون‌های جهت‌دار (فلش لایه‌ها) به‌صورت جداگانه mirror نمی‌شوند (جهت جغرافیایی معنا دارد).
- **تم تاریک/روشن:** توکن‌های رنگ CSS variables؛ پیش‌فرض تاریک (مطابق mockup)، سوییچ به روشن از طریق `Preferences.theme`.
- **WCAG AA:** کنتراست رنگ حداقل ۴.۵:۱ برای متن، فوکوس قابل‌مشاهده روی همه عناصر تعاملی، برچسب `aria-label` برای دکمه‌های فقط-آیکون (zoom، 2D/3D toggle).

---

## وضعیت فاز‌بندی

| فاز | محتوا | وضعیت |
|---|---|---|
| ۱ | معماری فنی + قرارداد API (این PR) | ✅ |
| ۲ | اسکلت React + سیستم طراحی (Design Tokens + Primitive Components) | ⏳ PR بعدی |
| ۳ | همه صفحات/جریان‌ها/کامپوننت‌های تعاملی + راهنمای اتصال بک‌اند نهایی | ⏳ PR بعدی |

## پیوست
- `api/openapi.yaml`
- `docs/frontend/architecture.md` (همین سند)
- منبع بصری: `ui_mockup.png` (پیوست تسک ClickUp `86bc860cq`)
