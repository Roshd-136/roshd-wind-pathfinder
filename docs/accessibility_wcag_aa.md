# دسترسی‌پذیری (WCAG AA) و RTL

> بخشی از تسک `86bc860cq` — آیتم ۷.

## ۱. پشتیبانی RTL

- زبان پیش‌فرض فارسی است و `document.documentElement.dir = "rtl"` در هوک
  `useLanguageDirection` تنظیم می‌شود.
- از کلاس‌های منطقی Tailwind استفاده می‌شود: `start-*`/`end-*` به‌جای
  `left-*`/`right-*` (مثلاً `MapModeToggle` با `start-4`).
- برای اعداد/شناسه‌های لاتین درون متن فارسی، کلاس `.ltr-only` با
  `unicode-bidi: isolate` تعریف شده است.
- فونت Vazirmatn برای خوانایی فارسی.

## ۲. معیارهای WCAG AA اعمال‌شده

| معیار | پیاده‌سازی |
|---|---|
| کنتراست متن (۴.۵:۱) | رنگ‌های `text-primary`/`text-secondary` روی `bg`/`surface` با کنتراست کافی |
| نام قابل‌دسترس (۴.۱.۲) | هر ورودی label واقعی دارد (`Checkbox`، `Select`، `TextField`، `Slider` با `aria-label`) |
| تمرکز قابل‌مشاهده (۲.۴.۷) | `:focus-visible` با outline accent در `global.css` |
| هدف کلیک | دکمه‌ها/آیکون‌های تعاملی با اندازه کافی و `aria-label` برای آیکون‌ها |
| معنای غیررنگی | خطاها علاوه بر رنگ، پیام متنی دارند (`aria-invalid` + متن) |
| ناوبری کیبورد | همه کنترل‌ها با Tab قابل دسترسی؛ پاپ‌آپ دکمه بستن دارد |

## ۳. بررسی خودکار (axe-core)

تست `frontend/src/test/a11y.test.tsx` با `vitest-axe` روی کامپوننت‌های کلیدی
اجرا می‌شود و رگرسیون‌های رایج (کنتراست، نبود label، نقش ARIA نادرست) را
می‌گیرد:

```
$ npm test
Test Files  6 passed (6)
     Tests  19 passed (19)
```

پوشش axe در حال حاضر: `Button`، `Card`، `Checkbox`، `TextField`،
`WindSpeedLegend`، `WindLayerControls`، `AlgorithmSelector`.

> این بررسی خودکار جایگزین ممیزی دستی کامل نیست؛ در فازهای بعدی برای صفحات
> کامل (Map، Settings، Auth) هم گسترش می‌یابد.

## ۴. تم تاریک/روشن

هر دو تم از یک مجموعه توکن تغذیه می‌کنند، بنابراین افزودن تم جدید نیازی به
تغییر کامپوننت‌ها ندارد. تم روشن با کنتراست AA طراحی شده است.
