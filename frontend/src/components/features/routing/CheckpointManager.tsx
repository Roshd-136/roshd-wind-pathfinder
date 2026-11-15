import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Checkpoint } from '../../../types/routing'

interface CheckpointManagerProps {
  checkpoints: Checkpoint[]
  onRemove: (index: number) => void
  onMove: (index: number, direction: -1 | 1) => void
  /** حالت افزودن با کلیک (به‌جای long-press). */
  adding?: boolean
  onToggleAdd?: () => void
  canAdd?: boolean
  /** دلیل روشن قطع‌بودن دکمه (مثلاً «فقط در نمایش ۲بعدی») — به‌جای
   * سکوتِ دکمهٔ کم‌رنگ که کاربر را گیج می‌کرد. */
  disabledHint?: string
  /** ثبت ارتفاع اجباری چک‌پوینت (کامنت ۸) — null یعنی عبور آزاد. */
  onSetAltitude?: (index: number, alt: number | null) => void
}

/**
 * ورودی ارتفاع اجباری یک چک‌پوینت (متر MSL) — مقدار مثبت = مسیر دقیقاً در
 * همین ارتفاع عبور میکند؛ خالی = عبور آزاد. پیشنویسِ متنی با مقایسهٔ
 * «مقدار ثبتشده» همگام میشود تا نقطهٔ اعشارِ میانی خورده نشود و مقدارِ
 * بیرونی (جابهجایی ردیف، رست) پیشنویس را باطل کند — بدون setState-in-effect.
 */
function AltitudeInput({
  value,
  onChange,
  label,
}: {
  value: number | null
  onChange: (alt: number | null) => void
  label: string
}) {
  const [draft, setDraft] = useState<{ text: string; committed: number | null } | null>(null)
  const text =
    draft && draft.committed === value
      ? draft.text
      : value != null
        ? String(value)
        : ''
  function handle(next: string) {
    const trimmed = next.trim()
    if (trimmed === '') {
      setDraft({ text: next, committed: null })
      onChange(null)
      return
    }
    const parsed = Number(trimmed)
    if (Number.isFinite(parsed) && parsed > 0) {
      setDraft({ text: next, committed: parsed })
      onChange(parsed)
      return
    }
    // نیمهکاره/نامعتبر (۰، منفی، حروف): پیشنویس تا وقتی مقدار عوض نشده میماند
    setDraft({ text: next, committed: value ?? null })
  }
  return (
    <input
      type="text"
      inputMode="decimal"
      value={text}
      placeholder="—"
      aria-label={label}
      data-testid="checkpoint-altitude-input"
      onChange={(event) => handle(event.target.value)}
      className={`w-16 shrink-0 rounded border px-1.5 py-0.5 text-end text-xs text-text-primary focus:outline-none ${
        value != null
          ? 'border-accent/60 bg-accent/10'
          : 'border-border bg-surface'
      }`}
    />
  )
}

/**
 * مدیریت چک‌پوینت‌های اجباری — افزودن با کلیک روی نقشه (بعد از انتخاب
 * مبدأ/مقصد)، حذف، جابجایی ترتیب، نمایش شماره ترتیب هر کدام
 * (چک‌لیست آیتم ۱۰) و ورودی ارتفاع اجباری هر ردیف (کامنت ۸ «کامنت‌های
 * نرم‌افزار» — پیشتر ارتفاع فقط با گیمبال سه‌بعدی قابل گذاشتن بود).
 */
export function CheckpointManager({
  checkpoints,
  onRemove,
  onMove,
  adding = false,
  onToggleAdd,
  canAdd = true,
  disabledHint,
  onSetAltitude,
}: CheckpointManagerProps) {
  const { t } = useTranslation()

  const addButton = (
    <div className="space-y-1">
      <button
        type="button"
        onClick={onToggleAdd}
        disabled={!canAdd}
        aria-pressed={adding}
        aria-describedby={disabledHint ? 'checkpoint-disabled-hint' : undefined}
        className={`w-full rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
          adding
            ? 'border-accent bg-accent/15 text-accent'
            : 'border-border bg-surface-raised text-text-secondary hover:text-text-primary disabled:opacity-40'
        }`}
      >
        {adding ? t('routing.addingCheckpoint') : t('routing.addCheckpoint')}
      </button>
      {!canAdd && disabledHint && (
        <p id="checkpoint-disabled-hint" className="text-xs text-amber-500">
          {disabledHint}
        </p>
      )}
    </div>
  )

  if (checkpoints.length === 0) {
    return (
      <div className="space-y-2">
        {addButton}
        <p className="text-xs text-text-muted">{t('routing.checkpointHint')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {addButton}
      <ul className="space-y-1">
      {checkpoints.map((cp, i) => (
        <li
          key={`${cp.lat}-${cp.lon}-${i}`}
          className="flex items-center justify-between gap-1.5 rounded-md border border-border bg-surface-raised px-2 py-1 text-xs"
        >
          <span className="min-w-0 truncate text-text-secondary">
            #{i + 1} — {cp.lat.toFixed(3)}, {cp.lon.toFixed(3)}
          </span>
          {onSetAltitude && (
            <AltitudeInput
              value={cp.alt ?? null}
              onChange={(alt) => onSetAltitude(i, alt)}
              label={t('routing.checkpointAltitudeAria', { n: i + 1 })}
            />
          )}
          <span className="flex shrink-0 gap-1">
            <button
              type="button"
              onClick={() => onMove(i, -1)}
              disabled={i === 0}
              aria-label={t('routing.moveUp')}
              className="text-text-muted hover:text-text-primary disabled:opacity-30"
            >
              ↑
            </button>
            <button
              type="button"
              onClick={() => onMove(i, 1)}
              disabled={i === checkpoints.length - 1}
              aria-label={t('routing.moveDown')}
              className="text-text-muted hover:text-text-primary disabled:opacity-30"
            >
              ↓
            </button>
            <button
              type="button"
              onClick={() => onRemove(i)}
              aria-label={t('routing.remove')}
              className="text-danger hover:opacity-80"
            >
              ✕
            </button>
          </span>
        </li>
      ))}
      </ul>
      {onSetAltitude && (
        <p className="text-xs text-text-muted">{t('routing.checkpointAltitudeHint')}</p>
      )}
    </div>
  )
}
