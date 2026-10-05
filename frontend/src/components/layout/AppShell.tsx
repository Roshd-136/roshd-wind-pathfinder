import { Map, Info, Menu, Moon, Settings, Sun, User } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useUiStore } from '../../store/useUiStore'
import { useSettingsStore } from '../../store/useSettingsStore'

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
  const isSidebarOpen = useUiStore((s) => s.isSidebarOpen)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)
  const theme = useSettingsStore((s) => s.theme)
  const setTheme = useSettingsStore((s) => s.setTheme)
  const isDark = theme !== 'light'

  return (
    <div className="flex h-full">
      {/* دکمهٔ سه‌خط — وقتی سایدبار بسته است تنها راه بازکردن آن */}
      {!isSidebarOpen && (
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={t('nav.menu')}
          title={t('nav.menu')}
          className="absolute start-4 top-4 z-30 flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface/95 text-text-secondary shadow-[var(--shadow-card)] backdrop-blur-sm transition-colors hover:text-text-primary"
        >
          <Menu size={20} aria-hidden />
        </button>
      )}
      {isSidebarOpen && (
      <aside className="relative hidden w-56 shrink-0 flex-col border-e border-border bg-surface p-4 md:flex">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={t('nav.menu')}
          title={t('nav.menu')}
          className="absolute end-3 top-3 flex h-8 w-8 items-center justify-center rounded-lg text-text-muted transition-colors hover:text-text-primary"
        >
          <Menu size={18} aria-hidden />
        </button>
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
        {/* کلید تم — در سایدبار (سمت راست در RTL) */}
        <div className="mt-auto border-t border-border pt-2">
          <button
            type="button"
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            aria-label={t('settings.theme')}
            title={t('settings.theme')}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary"
          >
            {isDark ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}
            {t('settings.theme')}
          </button>
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
      )}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
