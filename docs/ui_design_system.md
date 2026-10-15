# سیستم طراحی (Design System) — Roshd Wind Pathfinder

> بخشی از تسک `86bc860cq` — آیتم ۴. منبع مقادیر: `ui_mockup.png`.

## ۱. Design Tokens

توکن‌ها در `frontend/src/assets/styles/tokens.css` تعریف و در
`frontend/src/assets/styles/global.css` با `@theme` به Tailwind v4 نگاشت
می‌شوند (کلاس‌هایی مثل `bg-surface`، `text-text-primary`، `border-border`).

| گروه | توکن‌ها |
|---|---|
| سطوح | `--color-bg`, `--color-surface`, `--color-surface-raised`, `--color-border` |
| متن | `--color-text-primary`, `--color-text-secondary`, `--color-text-muted` |
| Accent | `--color-accent`, `--color-accent-hover`, `--color-accent-fg` |
| وضعیت | `--color-success`, `--color-danger`, `--color-warning` |
| Legend باد | `--wind-speed-{0,5,10,15,20}` (آبی→سبز→زرد→نارنجی→قرمز) |
| پین نقشه | `--color-origin-pin` (سبز)، `--color-destination-pin` (قرمز) |
| شعاع | `--radius-sm/md/lg` |
| فاصله | `--space-1..8` (مقیاس ۴px) |
| فونت | `--font-sans` = Vazirmatn |

**تم تاریک پیش‌فرض** است (مطابق mockup) و تم روشن با
`:root[data-theme="light"]` تعریف شده. انتخاب تم در `useSettingsStore` است و
هوک `useThemeSync` مقدار `data-theme` را روی `document.documentElement`
اعمال می‌کند (`system` = بدون override، پیروی از `prefers-color-scheme`).

## ۲. Primitive Components — `components/ui/`

| کامپوننت | نقش |
|---|---|
| `Button` | سه variant: `primary` (accent)، `secondary`، `ghost` |
| `Card` | پنل پایه: `bg-surface` + `border-border` + `radius-lg` + سایه |
| `Checkbox` | برچسب‌دار (label واقعی → دسترسی‌پذیری) |
| `Select` | dropdown با label |
| `Slider` | با نمایش مقدار و واحد؛ `aria-label` |
| `TextField` | با label، حالت خطا (`aria-invalid`) و پیام خطا |

## ۳. Feature Components — `components/features/`

| حوزه | کامپوننت‌ها |
|---|---|
| `map/` | `MapView` (Mapbox GL، 2D/3D)، `MapModeToggle`، `PointInfoPopup` |
| `routing/` | `RoutingMapScreen`، `PathInfoPanel`، `AlgorithmSelector`، `CheckpointManager`، `AdvancedFiltersPanel` |
| `layers/` | `WindLayerControls`، `WindSpeedLegend` |
| `auth/` | `LoginForm`، `RegisterForm`، `ForgotPasswordForm`، `ResetPasswordForm`، `VerifyEmailPanel` + `authSchemas` (Zod) |
| `layout/` | `AppShell` (sidebar)، `MobileBottomSheet` |

## ۴. الگوهای تعاملی

- **انتخاب مبدأ/مقصد:** کلیک اول/دوم روی نقشه؛ پین سبز/قرمز.
- **اطلاعات نقطه:** کلیک‌های بعدی یا دکمه «مشاهده لایه‌های باد در نقطه» → پاپ‌آپ.
- **چک‌پوینت اجباری:** long-press (۵۰۰ms) روی نقشه؛ مارکر شماره‌دار؛ جابجایی/حذف در پنل.
- **کنترل لایه‌ها:** سه لایه ارتفاعی (سطحی ۰–۵۰، میانی ۵۰–۲۰۰، بالا ۲۰۰–۵۰۰ متر).
- **فیلترهای پیشرفته:** بازه ارتفاع (دو اسلایدر)، معیار بهینه‌سازی (زمان/انرژی/متعادل)، اجتناب از مناطق.
- **واکنش‌گرایی:** در دسکتاپ پنل کنار نقشه؛ در موبایل (`< md`) به bottom sheet تبدیل می‌شود.

## ۵. قواعد نگارش کد

- فقط Tailwind + توکن‌ها؛ رنگ هاردکدشده در کامپوننت‌ها نیست.
- متن‌های کاربرپسند از i18next می‌آیند (`fa.json` / `en.json`).
- کامپوننت‌ها تابعی و تایپ‌دارند؛ props با interface مشخص می‌شوند.
