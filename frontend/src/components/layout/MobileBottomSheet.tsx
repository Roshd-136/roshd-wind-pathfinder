import type { ReactNode } from 'react'
import { useUiStore } from '../../store/useUiStore'

interface MobileBottomSheetProps {
  children: ReactNode
  /** عنوان بالای شیت — مثل «تنظیمات سفر» در اپ‌های ناوبری. */
  title?: string
}

/**
 * Bottom sheet موبایل — جایگزین پنل کنترل سمت راست دسکتاپ روی صفحات باریک
 * (< md)؛ به سبک Uber/Snapp: نقشهٔ تمام‌صفحه و شیت تنظیمات سفر پایین صفحه
 * با دستهٔ کشیدنی. فقط زیر md نمایش داده می‌شود (پنل دسکتاپ در
 * AppShell/صفحات با `md:flex` مخفی نگه داشته می‌شود).
 */
export function MobileBottomSheet({ children, title }: MobileBottomSheetProps) {
  const { isMobileSheetOpen, closeMobileSheet } = useUiStore()

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-20 max-h-[80dvh] overflow-y-auto rounded-t-2xl border-t border-border bg-surface p-4 shadow-[var(--shadow-card)] transition-transform duration-300 md:hidden ${
        isMobileSheetOpen ? 'translate-y-0' : 'translate-y-[calc(100%-4.5rem)]'
      }`}
    >
      <button
        onClick={closeMobileSheet}
        aria-label="toggle sheet"
        className="mx-auto mb-3 block h-1.5 w-12 rounded-full bg-border"
      />
      {title && (
        <h2 className="mb-3 text-center text-sm font-semibold text-text-primary">{title}</h2>
      )}
      {children}
    </div>
  )
}
