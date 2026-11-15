import { Menu } from 'lucide-react'
import { Outlet, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useUiStore } from '../../store/useUiStore'
import { SidebarMenu } from './SidebarMenu'

/**
 * چیدمان پایه: sidebar باریک سمت چپ (لوگو + ناوبری Map/Settings/About) +
 * ناحیهٔ محتوا — دقیقاً الگوی mockup. در موبایل (< md) روی مسیر نقشه،
 * دکمهٔ منو داخل ویزارد است (سمتِ مقابل ذره‌بین جستجو) و پنل منو زیر
 * ویزارد باز میشود؛ دکمهٔ سه‌خطِ شناور فقط در دسکتاپ یا صفحه‌های دیگر
 * بدون ویزارد دیده میشود تا روی گوشی گوشهٔ ویزارد را نپوشاند.
 */
export function AppShell() {
  const { t } = useTranslation()
  const isSidebarOpen = useUiStore((s) => s.isSidebarOpen)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)
  const { pathname } = useLocation()
  const isMapRoute = pathname === '/'

  return (
    <div className="flex h-full">
      {/* دکمهٔ سه‌خط — وقتی سایدبار بسته است تنها راه بازکردن آن؛ روی مسیر
          نقشه در موبایل مخفی (تریگر داخل ویزارد است) */}
      {!isSidebarOpen && (
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={t('nav.menu')}
          title={t('nav.menu')}
          className={`absolute start-4 top-4 z-30 h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface/95 text-text-secondary shadow-[var(--shadow-card)] backdrop-blur-sm transition-colors hover:text-text-primary ${
            isMapRoute ? 'hidden md:flex' : 'flex'
          }`}
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
          <div className="flex min-h-0 flex-1 flex-col">
            <SidebarMenu />
          </div>
        </aside>
      )}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
