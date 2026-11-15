import { Menu, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useUiStore } from '../../store/useUiStore'
import { SidebarMenu } from './SidebarMenu'

/**
 * دکمهٔ منوی موبایل — در ردیف جستجوی ویزارد، سمتِ مقابلِ ذره‌بین
 * («طرف دیگر آیکون جستجو») — قبلاً دکمهٔ سه‌خط شناور در `start-4 top-4`
 * روی گوشی روی گوشهٔ قاب ویزارد و ورودی جستجو می‌افتاد (بازخورد تست
 * موبایل). فقط زیر md دیده میشود؛ دسکتاپ همان دکمهٔ شناور AppShell را دارد.
 */
export function MobileMenuButton() {
  const { t } = useTranslation()
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)

  return (
    <button
      type="button"
      onClick={toggleSidebar}
      aria-label={t('nav.menu')}
      title={t('nav.menu')}
      data-testid="mobile-menu-trigger"
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-surface-raised hover:text-text-primary md:hidden"
    >
      <Menu size={16} aria-hidden />
    </button>
  )
}

/**
 * پنل منوی موبایل — مستقیم زیر قاب ویزارد باز میشود (فرزندِ بعدی در
 * پوشش ویزارد) بهجای کشوی تمام‌صفحه؛ خودش دکمهٔ بستن دارد («دکمهٔ بستن
 * روی خود سایدبار») و کلیک بیرون هم می‌بندد. فقط زیر md.
 */
export function MobileMenuPanel() {
  const { t } = useTranslation()
  const isOpen = useUiStore((s) => s.isSidebarOpen)
  const closeSidebar = useUiStore((s) => s.closeSidebar)

  if (!isOpen) return null

  return (
    <>
      {/* کلیک بیرون پنل → بستن؛ لایه زیر پنل و بالای نقشه (md:hidden) */}
      <div aria-hidden onClick={closeSidebar} className="fixed inset-0 z-[15] md:hidden" />
      <div
        role="dialog"
        aria-label={t('nav.menu')}
        data-testid="mobile-menu-panel"
        className="relative z-20 w-full max-w-[24rem] rounded-2xl border border-border bg-surface/95 p-2 shadow-[var(--shadow-card)] backdrop-blur-sm md:hidden"
      >
        <div className="mb-1 flex items-center justify-between px-2 pt-1">
          <span className="text-xs font-semibold text-text-primary">{t('app.name')}</span>
          <button
            type="button"
            onClick={closeSidebar}
            aria-label={t('common.close')}
            title={t('common.close')}
            data-testid="mobile-menu-close"
            className="flex h-7 w-7 items-center justify-center rounded-lg text-text-muted transition-colors hover:text-text-primary"
          >
            <X size={16} aria-hidden />
          </button>
        </div>
        <SidebarMenu onNavigate={closeSidebar} />
      </div>
    </>
  )
}
