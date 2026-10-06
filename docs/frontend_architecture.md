# معماری فرانت‌اند — یک کدبیس، سه بستر توزیع

> بخشی از تسک `86bc860cq` (UI Foundation & Technical Architecture) — آیتم ۱.

## ۱. یک کدبیس، سه بستر

کل رابط کاربری یک اپلیکیشن React است و از سه مسیر توزیع می‌شود. هیچ کدی برای
هر بستر تکرار یا شاخه‌شاخه نمی‌شود؛ تفاوت‌ها فقط در لایه بسته‌بندی و چند
قابلیت بومی است.

```
                    ┌────────────────────────────┐
                    │   React + TypeScript UI    │
                    │  (frontend/src — یک کدبیس) │
                    └─────────────┬──────────────┘
                                  │  npm run build → frontend/dist
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   ┌─────────────┐        ┌─────────────┐         ┌──────────────┐
   │  Web / PWA  │        │   Desktop   │         │    Mobile    │
   │  (استاتیک)  │        │   (Tauri 2) │         │ (Capacitor 8)│
   └─────────────┘        └─────────────┘         └──────────────┘
   هر مرورگری        Windows/macOS/Linux       Android/iOS
```

### دستورهای هر بستر

| بستر | توسعه | ساخت |
|---|---|---|
| Web/PWA | `npm run dev` | `npm run build` |
| Desktop (Tauri) | `npm run tauri dev` | `npm run tauri build` |
| Mobile (Capacitor) | `npm run build && npx cap sync && npx cap open android` | `npx cap sync` + Android Studio / Xcode |

## ۲. تشخیص بستر در زمان اجرا

`src/platform/index.ts` پلتفرم فعلی را تشخیص می‌دهد (`isNative`، `getPlatform`).
کد مشترک از این لایه استفاده می‌کند و به APIهای بومی مستقیماً وابسته نمی‌شود؛
اگر بومی نبود، پیاده‌سازی وب (fallback) اجرا می‌شود.

## ۳. بسته‌بندی دسکتاپ — Tauri 2

- پیکربندی: `frontend/src-tauri/tauri.conf.json` (شناسه `com.roshd.windpath`).
- نقطه ورود Rust: `src-tauri/src/main.rs` → `windpath_lib::run()`.
- `frontendDist` به `../dist` اشاره می‌کند؛ `beforeBuildCommand` خودش
  `npm run build` را اجرا می‌کند.
- خروجی: بسته‌های `.msi`/`.exe` (ویندوز)، `.dmg` (مک)، `.deb`/`.AppImage` (لینوکس).

> نکته: برای ساخت واقعی بسته، زنجیره Rust (`cargo`/`rustc`) لازم است. در CI
> فقط اعتبارسنجی پیکربندی انجام می‌شود.

## ۴. بسته‌بندی موبایل — Capacitor 8

- پیکربندی: `frontend/capacitor.config.ts` (`appId: com.roshd.windpath`، `webDir: dist`).
- خروجی: پروژه‌های بومی Android/iOS که با `npx cap add android|ios` ساخته می‌شوند.

## ۵. قرارداد API

قرارداد کامل در [`api/openapi.yaml`](../api/openapi.yaml) (OpenAPI 3.0) است و
شامل ۲۳ endpoint در حوزه‌های مسیریابی، لایه‌های باد، نقاط، احراز هویت و
پروفایل کاربری است. کلاینت تایپ‌دار در `src/services/api/` قرار دارد و دقیقاً
همین schemaها را آینه می‌کند.

| حوزه | نمونه endpointها | ماژول کلاینت |
|---|---|---|
| مسیریابی | `POST /routes`, `GET /routes/{routeId}`, `GET /routes/jobs/{jobId}/compare-layers` | `services/api/routing.ts` |
| لایه‌های باد | `GET /wind-layers`, `GET /wind-layers/point-all` | `services/api/windLayers.ts` |
| نقاط | `GET/POST/DELETE /points/favorites` | `services/api/account.ts` |
| الگوریتم | `GET /algorithms` | `services/api/routing.ts` |
| احراز هویت | `POST /auth/{register,login,refresh,logout}`, `password-reset/{request,confirm}`, `verify-email/confirm` | `services/api/auth.ts` |
| پروفایل | `GET /me`, `GET/PUT /me/preferences`, `GET /me/routes` | `services/api/account.ts` |

## ۶. لایه داده و حالت

- **TanStack Query** برای درخواست‌های سرور (کش، retry، loading/error).
- **Zustand** برای حالت کلاینت:
  - `useRouteStore` — مبدأ/مقصد/چک‌پوینت/الگوریتم/محدودیت‌ها/نتیجه. عمداً
    جدا نگه داشته شده تا هنگام جابه‌جایی بین Map2D و Map3D حفظ شود.
  - `useUiStore` — باز/بسته بودن پنل و bottom sheet، حالت نقشه.
  - `useSettingsStore` — تم، زبان، واحد، پیش‌فرض‌های الگوریتم/معیار.
