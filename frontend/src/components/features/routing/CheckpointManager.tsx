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
}

/**
 * مدیریت چک‌پوینت‌های اجباری — افزودن با کلیک روی نقشه (بعد از انتخاب
 * مبدأ/مقصد)، حذف، جابجایی ترتیب، و نمایش شماره ترتیب هر کدام
 * (چک‌لیست آیتم ۱۰).
 */
export function CheckpointManager({
  checkpoints,
  onRemove,
  onMove,
  adding = false,
  onToggleAdd,
  canAdd = true,
}: CheckpointManagerProps) {
  const { t } = useTranslation()

  const addButton = (
    <button
      type="button"
      onClick={onToggleAdd}
      disabled={!canAdd}
      aria-pressed={adding}
      className={`w-full rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
        adding
          ? 'border-accent bg-accent/15 text-accent'
          : 'border-border bg-surface-raised text-text-secondary hover:text-text-primary disabled:opacity-40'
      }`}
    >
      {adding ? t('routing.addingCheckpoint') : t('routing.addCheckpoint')}
    </button>
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
          className="flex items-center justify-between rounded-md border border-border bg-surface-raised px-2 py-1 text-xs"
        >
          <span className="text-text-secondary">
            #{i + 1} — {cp.lat.toFixed(3)}, {cp.lon.toFixed(3)}
          </span>
          <span className="flex gap-1">
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
    </div>
  )
}
