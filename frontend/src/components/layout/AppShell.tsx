import { Map, Info, Settings, User } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const NAV_ITEMS = [
  { to: '/', labelKey: 'nav.map', icon: Map },
  { to: '/settings', labelKey: 'nav.settings', icon: Settings },
  { to: '/about', labelKey: 'nav.about', icon: Info },
]

// پروفایل در mockup نیامده، ولی برای دسترسی به تاریخچه مسیرها/حساب کاربری
// لازم است؛ جدا از ناوبری اصلی نگه داشته شده (پایین sidebar).
const PROFILE_ITEM = { to: '/profile', labelKey: 'nav.profile', icon: User }

/**
 * چیدمان پایه: sidebar باریک سمت چپ (لوگو + ناوبری Map/Settings/About) +
 * ناحیه محتوا — دقیقاً الگوی mockup. در موبایل (< md) sidebar به یک نوار
 * پایین/drawer تبدیل می‌شود (پیاده‌سازی کامل واکنش‌گرا در فاز ۳).
 */
export function AppShell() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full">
      <aside className="hidden w-56 flex-col border-e border-border bg-surface p-4 md:flex">
        <div className="mb-6 text-lg font-bold text-text-primary">{t('app.name')}</div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? 'bg-accent/10 text-accent'
                    : 'text-text-secondary hover:bg-surface-raised hover:text-text-primary'
                }`
              }
            >
              <Icon size={18} aria-hidden />
              {t(labelKey)}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto border-t border-border pt-2">
          <NavLink
            to={PROFILE_ITEM.to}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-accent/10 text-accent'
                  : 'text-text-secondary hover:bg-surface-raised hover:text-text-primary'
              }`
            }
          >
            <User size={18} aria-hidden />
            {t('nav.profile')}
          </NavLink>
        </div>
      </aside>
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
