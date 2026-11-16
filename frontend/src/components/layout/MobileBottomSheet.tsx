import { useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react'
import { useUiStore } from '../../store/useUiStore'

interface MobileBottomSheetProps {
  children: ReactNode
  /** عنوان بالای شیت — مثل «تنظیمات سفر» در اپ‌های ناوبری. */
  title?: string
}

/**
 * Bottom sheet موبایل کشیدنی — جایگزین پنل کنارِ دسکتاپ روی صفحات باریک
 * (< md). دو حالت سنجاق دارد: جمع‌شده (فقط دسته و عنوان، پایین صفحه) و
 * باز (به سمت بالا، با فاصلهٔ ~۴rem از سقف تا نقشه دیده بماند).
 *
 * خودِ شیت عنصر `fixed` است (بدون غلاف) تا جابهجایی transform ناحیهٔ
 * کلیک آن را هم جابهجا کند — قبلاً یک غلافِ ثابتِ تمام‌ارتفاع دور شیت
 * بود که با شیتِ جمعشده هم جعبه‌اش روی نقشه می‌ماند و تک‌لمسِ نقشه
 * (جابهجایی/انتخاب/چک‌پوینت) را میخورد (بازخورد تست موبایل).
 *
 * هنگام باز بودن، پسزمینه با پردهٔ نیمهتیره تار میشود تا تمرکز روی شیت
 * باشد؛ کلیک روی پرده می‌بندد. دستهٔ بالایی با PointerEvent کشیده میشود
 * و در پایان به نزدیک‌ترین سنجاق می‌نشیند؛ کلیک روی دسته و کیبورد هم
 * حالت را عوض میکند. محتوای جمعشده با `inert` از ترتیب تب و درخت
 * دسترسپذیری خارج میشود.
 */
export function MobileBottomSheet({ children, title }: MobileBottomSheetProps) {
  const isOpen = useUiStore((s) => s.isMobileSheetOpen)
  const openMobileSheet = useUiStore((s) => s.openMobileSheet)
  const closeMobileSheet = useUiStore((s) => s.closeMobileSheet)

  const sheetRef = useRef<HTMLDivElement | null>(null)
  const headerRef = useRef<HTMLDivElement | null>(null)
  /** جابهجایی زندهٔ شیت در حین کشش — null یعنی خارج از کشش (کلاس CSS). */
  const [dragY, setDragY] = useState<number | null>(null)
  const drag = useRef<{ startY: number; peekY: number; lastY: number } | null>(null)
  /** آیا در این کشش واقعاً جابهجایی رخ داد — برای ساکت‌کردن clickِ پس از رهاکردن. */
  const movedRef = useRef(false)

  function handlePointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    const sheet = sheetRef.current
    const header = headerRef.current
    if (!sheet || !header) return
    const peekY = Math.max(0, sheet.offsetHeight - header.offsetHeight)
    drag.current = { startY: e.clientY, peekY, lastY: isOpen ? 0 : peekY }
    movedRef.current = false
    try {
      header.setPointerCapture(e.pointerId)
    } catch {
      // محیط بدون setPointerCapture — کشش بدون قفلِ اشارهگر ادامه می‌یابد
    }
    setDragY(drag.current.lastY)
  }

  function handlePointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    const d = drag.current
    if (!d) return
    if (Math.abs(e.clientY - d.startY) > 6) movedRef.current = true
    const y = Math.min(d.peekY, Math.max(0, d.lastY + (e.clientY - d.startY)))
    d.lastY = y
    setDragY(y)
  }

  function settle() {
    const d = drag.current
    if (!d) return
    const goOpen = d.lastY < d.peekY / 2
    drag.current = null
    setDragY(null)
    if (goOpen) openMobileSheet()
    else closeMobileSheet()
  }

  function handleToggleClick() {
    // بعد از کشیدن، مرورگر یک click مصنوعی میدهد — اگر واقعاً کشیده شده
    // بود، سنجاقِ pointerup را خراب نکند.
    if (movedRef.current) {
      movedRef.current = false
      return
    }
    if (isOpen) closeMobileSheet()
    else openMobileSheet()
  }

  const whileDragging = dragY != null

  return (
    <>
      {/* پردهٔ مودال — فقط وقتی باز؛ نقشه پشت آن دیده ولی غیرفعال میشود
          (تمرکز روی شیت، طبق بازخورد تست موبایل). md:hidden: فقط موبایل. */}
      {isOpen && (
        <div
          aria-hidden
          data-testid="mobile-sheet-backdrop"
          onClick={closeMobileSheet}
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
        />
      )}
      <div
        ref={sheetRef}
        data-testid="mobile-sheet"
        style={whileDragging ? { transform: `translateY(${dragY}px)`, transition: 'none' } : undefined}
        className={`fixed inset-x-0 bottom-0 z-40 flex max-h-[calc(100dvh-4rem)] flex-col rounded-t-2xl border-t border-border bg-surface shadow-[var(--shadow-card)] md:hidden ${
          whileDragging
            ? ''
            : isOpen
              ? 'translate-y-0 transition-transform duration-300'
              : 'translate-y-[calc(100%-3.5rem)] transition-transform duration-300'
        }`}
      >
        {/* دسته + عنوان — نوار بالای شیت؛ در حالت جمع فقط همین باریکه
            (۳٫۵rem) از پایین صفحه دیده میشود. touch-none کشش را از
            اسکرول/پULL-تو‌رفرش مرورگر جدا میکند. */}
        <div
          ref={headerRef}
          data-testid="mobile-sheet-grab"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={settle}
          onPointerCancel={() => {
            // رهاکردن اشارهگر بدون تصمیم (مثلاً تماس قطع شد) — برگشت به
            // حالت قبل، بدون تغییر سنجاق
            drag.current = null
            setDragY(null)
          }}
          className="h-14 shrink-0 touch-none select-none"
        >
          <button
            type="button"
            onClick={handleToggleClick}
            aria-expanded={isOpen}
            aria-controls="mobile-sheet-content"
            aria-label={title ?? 'toggle sheet'}
            className="mx-auto mt-2 flex h-6 w-24 items-center justify-center rounded-full"
          >
            <span className="block h-1.5 w-12 rounded-full bg-border" aria-hidden />
          </button>
          {title && (
            <h2 className="text-center text-sm font-semibold text-text-primary">{title}</h2>
          )}
        </div>
        {/* محتوا — همیشه در DOM (اندازهٔ کامل شیت برای ریاضیاتِ کشش)،
            فقط در حالت باز دیده/در دسترس است. سقف محتوا ۴rem از سقفِ
            نمایشگر فاصله میگذارد تا نقشه بالا سرش دیده بماند. */}
        <div
          id="mobile-sheet-content"
          className="min-h-0 overflow-y-auto overscroll-contain px-4 pb-4"
          aria-hidden={!isOpen}
          inert={!isOpen}
        >
          {children}
        </div>
      </div>
    </>
  )
}
