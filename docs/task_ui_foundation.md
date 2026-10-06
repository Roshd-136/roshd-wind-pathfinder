# تسک: زیربنای رابط کاربری و معماری فنی (UI Foundation & Technical Architecture)

> شناسه ClickUp: `86bc860cq` · اولویت: **High** · ددلاین: ۷ مهر ۱۴۰۵ ساعت ۲۰:۰۰ (به وقت ایران)
> شاخه: `task/ui-foundation` · برچسب PR: `ui-foundation`

## ۱. هدف (Purpose)

طراحی کامل سیستم رابط کاربری، معماری فنی و قراردادهای داده (API Contract) برای
نرم‌افزار مسیریاب جریان‌های هوایی. یک کدبیس واحد React (TypeScript، Vite،
Tailwind، Mapbox GL JS) که به‌عنوان وب‌اپلیکیشن (PWA) طراحی می‌شود و با
Capacitor (موبایل) و Tauri (دسکتاپ) بسته‌بندی می‌شود. ظاهر برنامه باید
هم‌تراز با طرح مرجع (mockup) باشد.

## ۲. پشته فنی

| لایه | فناوری |
|---|---|
| کتابخانه UI | React 19 + TypeScript |
| باندلر | Vite |
| استایل | Tailwind CSS v4 (Design Tokens با `@theme`) |
| نقشه | MapLibre GL (انشعاب آزاد Mapbox — بدون توکن، کاشی OSM، ترن ۳بعدی DEM آزاد) |
| مسیریابی | React Router |
| حالت سراسری | Zustand (`useRouteStore`، `useUiStore`، `useSettingsStore`) |
| داده/کش | TanStack Query |
| فرم/اعتبارسنجی | react-hook-form + Zod |
| چندزبانگی | i18next (فارسی پیش‌فرض، RTL) |
| تست | Vitest + Testing Library + vitest-axe |
| بسته‌بندی دسکتاپ | Tauri 2 (`src-tauri/`) |
| بسته‌بندی موبایل | Capacitor 8 (`capacitor.config.ts`) |

## ۳. ساختار پروژه (فرانت‌اند)

```
frontend/
├── capacitor.config.ts            # بسته‌بندی موبایل (iOS/Android)
├── src-tauri/                     # بسته‌بندی دسکتاپ (Tauri 2)
│   ├── tauri.conf.json
│   ├── Cargo.toml
│   └── src/{main.rs, lib.rs}
├── src/
│   ├── components/
│   │   ├── ui/                    # Primitive: Button, Card, Checkbox, Select, Slider, TextField
│   │   ├── layout/                # AppShell، MobileBottomSheet
│   │   └── features/
│   │       ├── map/               # MapView، MapModeToggle، PointInfoPopup
│   │       ├── routing/           # RoutingMapScreen، PathInfoPanel، AlgorithmSelector،
│   │       │                      # CheckpointManager، AdvancedFiltersPanel
│   │       ├── layers/            # WindLayerControls، WindSpeedLegend
│   │       ├── auth/              # Login/Register/Forgot/Reset/Verify + authSchemas
│   │       └── profile/
│   ├── pages/                     # Home(Map2D), Map3D, Settings, Results, Auth, Profile, Onboarding, About
│   ├── hooks/                     # useAuth، usePathfinding، useWindData، useProfile، useThemeSync، useLanguageDirection
│   ├── services/api/              # کلاینت تایپ‌دار + auth، routing، windLayers، account
│   ├── store/                     # useRouteStore، useUiStore، useSettingsStore
│   ├── types/                     # تایپ‌های مشترک (routing، …)
│   ├── i18n/                      # fa.json، en.json
│   └── assets/styles/             # global.css، tokens.css
└── index.html
```

## ۴. جریان کاربری

```
انتخاب مبدأ/مقصد روی نقشه (۲بعدی)
        ↓
انتخاب لایه و معیار (پنل کنار نقشه)
        ↓
چک‌پوینت‌های اجباری (long-press روی نقشه)
        ↓
اجرای مسیریابی → نمایش مسیر + پروفایل باد
        ↓
ذخیره/اشتراک‌گذاری (Results)
```

- **کلیک اول** روی نقشه = مبدأ (پین سبز).
- **کلیک دوم** = مقصد (پین قرمز).
- **کلیک‌های بعدی** = نمایش اطلاعات باد آن نقطه (پاپ‌آپ «Wind Layers»).
- **long-press (۵۰۰ms)** = افزودن چک‌پوینت اجباری با شماره ترتیب.

## ۵. موارد بررسی (Items to Check)

- [x] ۱. معماری فنی یک کدبیس (Web/PWA، Desktop/Tauri، Mobile/Capacitor) تثبیت و مستند شود.
- [x] ۲. قرارداد API کامل (OpenAPI 3.0) با همه endpointها، schemaها، events و Errorها تعریف شود.
- [x] ۳. اسکلت پروژه React با ساختار پوشه‌بندی استاندارد و toolchain ساخته شود.
- [x] ۴. سیستم طراحی (Design Tokens، Primitive Components، Feature Components) پیاده‌سازی شود.
- [x] ۵. تمام صفحات و جریان‌ها (Map2D، Map3D، Settings، Results، Auth، Profile، Onboarding) طراحی و پیاده‌سازی شوند.
- [x] ۶. کامپوننت‌های تعاملی: انتخاب مبدأ/مقصد/چک‌پوینت، کنترل لایه‌ها، انتخاب‌گر الگوریتم، پروفایل مسیر، فیلترهای پیشرفته، bottom sheet.
- [x] ۷. طراحی واکنش‌گرا کامل، دسترسی‌پذیری (WCAG AA)، تم تاریک/روشن، RTL، مستندات اتصال بک‌اند.
- [ ] ۸. ظاهر برنامه پیکسل‌به‌پیکسل با طرح مرجع (mockup) هم‌تراز باشد.
- [x] ۹. فرم‌های احراز هویت (ورود، ثبت‌نام، بازیابی رمز، تایید ایمیل) و صفحه پروفایل کاربری طراحی شوند.
- [x] ۱۰. مدیریت چک‌پوینت‌های اجباری روی نقشه (افزودن، حذف، جابجایی، نمایش ترتیب) پیاده‌سازی شود.
- [x] ۱۱. پنل فیلترهای پیشرفته مسیر (محدودیت سرعت، ارتفاع، اجتناب از مناطق، بهینه‌سازی انرژی/زمان) طراحی شود.

> **آیتم ۸** تنها مورد باز است: بدون `VITE_MAPBOX_TOKEN` نقشه رندر نمی‌شود و
> بررسی چشمی/پیکسلی ممکن نیست. پیاده‌سازی بر اساس mockup انجام شده است.

## ۶. مستندات مرتبط

- [`docs/frontend_architecture.md`](frontend_architecture.md) — معماری یک کدبیس و بسته‌بندی سه‌گانه.
- [`docs/ui_design_system.md`](ui_design_system.md) — Design Tokens و کامپوننت‌ها.
- [`docs/accessibility_wcag_aa.md`](accessibility_wcag_aa.md) — چک‌لیست دسترسی‌پذیری و RTL.
- [`api/openapi.yaml`](../api/openapi.yaml) — قرارداد API (OpenAPI 3.0).
