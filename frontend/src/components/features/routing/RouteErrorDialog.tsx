import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { X } from 'lucide-react'
import { Button } from '../../ui/Button'

interface RouteErrorDialogProps {
  /** پیام خطا — معمولاً پیام فارسی موتور مسیریابی از `detail` سرور. */
  message: string
  onClose: () => void
}

/**
 * خطای محاسبهٔ مسیر در **فریم جدای مودال** — نه بنر داخل صفحه.
 *
 * پیش‌تر خطا یک بنر کوچک بالای نقشه بود؛ کاربر گزارش کرد که خطا باید کادر
 * مستقل بگیرد تا از شلوغی نقشه پنهان نشود و حتماً دیده شود. مودال با Escape
 * و کلیک روی زمینه هم بسته می‌شود و دکمهٔ بستن فوکوس اولیه را می‌گیرد.
 */
export function RouteErrorDialog({ message, onClose }: RouteErrorDialogProps) {
  const { t } = useTranslation()
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeButtonRef.current?.focus()
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4"
      onClick={onClose}
      data-testid="route-error-overlay"
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={t('routing.routeErrorTitle')}
        onClick={(event) => event.stopPropagation()}
        data-testid="route-error-dialog"
        className="w-full max-w-sm rounded-2xl border border-danger/40 bg-surface p-4 shadow-[var(--shadow-card)] outline-none"
      >
        <div className="flex items-start justify-between gap-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-text-primary">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-danger/15 text-danger">
              !
            </span>
            {t('routing.routeErrorTitle')}
          </h2>
          <Button
            ref={closeButtonRef}
            variant="outline"
            className="shrink-0 !px-2 !py-1.5"
            onClick={onClose}
            aria-label={t('routing.close')}
          >
            <X size={14} aria-hidden />
          </Button>
        </div>
        <p className="mt-3 text-xs leading-5 text-text-secondary">{message}</p>
        <p className="mt-2 text-xs text-text-muted">{t('routing.routeErrorHint')}</p>
      </div>
    </div>
  )
}
