import { Info, Map, Moon, Settings, Sun, User } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSettingsStore } from '../../store/useSettingsStore'

const NAV_ITEMS = [
  { to: '/', labelKey: 'nav.map', end: true, icon: Map },
  { to: '/settings', labelKey: 'nav.settings', end: false, icon: Settings },
  { to: '/about', labelKey: 'nav.about', end: false, icon: Info },
]

// پروفایل در mockup نیامده، ولی برای دسترسی به تاریخچه مسیرها/حساب کاربری
// لازم است؛ جدا از ناوبری اصلی نگه داشته شده (پایین sidebar).
const PROFILE_ITEM = { to: '/profile', labelKey: 'nav.profile' }

interface SidebarMenuProps {
  /** بعد از انتخاب آیتم صدا میشود — در پنل کشویی موبایل برای بستن پنل. */
  onNavigate?: () => void
}

/**
 * محتوای منو (ناوبری + کلید تم + پروفایل) — مشترک بین سایدبار دسکتاپ
 * (AppShell) و پنل کشویی موبایل (زیر ویزارد). قبلاً همین فهرست فقط در
 * AppShell بود و منوی موبایل عملاً وجود نداشت (aside زیر md مخفی است).
 */
export function SidebarMenu({ onNavigate }: SidebarMenuProps) {
  const { t } = useTranslation()
  const theme = useSettingsStore((s) => s.theme)
  const setTheme = useSettingsStore((s) => s.setTheme)
  const isDark = theme !== 'light'

  return (
    <>
      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map(({ to, labelKey, end, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
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
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
              isActive
                ? 'bg-accent/10 text-accent'
                : 'text-text-secondary hover:bg-surface-raised hover:text-text-primary'
            }`
          }
        >
          <User size={18} aria-hidden />
          {t(PROFILE_ITEM.labelKey)}
        </NavLink>
      </div>
    </>
  )
}
