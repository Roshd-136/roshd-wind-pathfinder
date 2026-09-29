import type { ReactNode } from 'react'
import { useUiStore } from '../../store/useUiStore'

interface MobileBottomSheetProps {
  children: ReactNode
}

/**
 * Bottom sheet موبایل — جایگزین پنل کنترل سمت راست دسکتاپ روی صفحات باریک
 * (< md)؛ طبق تسک: «sidebar در موبایل → drawer، نتایج → bottom sheet».
 * فقط زیر md نمایش داده می‌شود (پنل دسکتاپ در AppShell/صفحات با `md:flex`
 * مخفی نگه داشته می‌شود).
 */
export function MobileBottomSheet({ children }: MobileBottomSheetProps) {
  const { isMobileSheetOpen, closeMobileSheet } = useUiStore()

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-20 rounded-t-lg border-t border-border bg-surface p-4 shadow-[var(--shadow-card)] transition-transform md:hidden ${
        isMobileSheetOpen ? 'translate-y-0' : 'translate-y-[calc(100%-3rem)]'
      }`}
    >
      <button
        onClick={closeMobileSheet}
        aria-label="toggle sheet"
        className="mx-auto mb-3 block h-1 w-10 rounded-full bg-border"
      />
      {children}
    </div>
  )
}
