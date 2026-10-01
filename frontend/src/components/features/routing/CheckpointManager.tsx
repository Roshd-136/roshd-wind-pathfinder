import type { Checkpoint } from '../../../types/routing'

interface CheckpointManagerProps {
  checkpoints: Checkpoint[]
  onRemove: (index: number) => void
  onMove: (index: number, direction: -1 | 1) => void
}

/**
 * مدیریت چک‌پوینت‌های اجباری — افزودن با کلیک روی نقشه (بعد از انتخاب
 * مبدأ/مقصد)، حذف، جابجایی ترتیب، و نمایش شماره ترتیب هر کدام
 * (چک‌لیست آیتم ۱۰).
 */
export function CheckpointManager({ checkpoints, onRemove, onMove }: CheckpointManagerProps) {
  if (checkpoints.length === 0) {
    return (
      <p className="text-xs text-text-muted">
        بعد از انتخاب مبدأ/مقصد، برای افزودن چک‌پوینت اجباری روی نقشه کلیک نگه دارید (long-press).
      </p>
    )
  }

  return (
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
              aria-label="move up"
              className="text-text-muted hover:text-text-primary disabled:opacity-30"
            >
              ↑
            </button>
            <button
              type="button"
              onClick={() => onMove(i, 1)}
              disabled={i === checkpoints.length - 1}
              aria-label="move down"
              className="text-text-muted hover:text-text-primary disabled:opacity-30"
            >
              ↓
            </button>
            <button
              type="button"
              onClick={() => onRemove(i)}
              aria-label="remove"
              className="text-danger hover:opacity-80"
            >
              ✕
            </button>
          </span>
        </li>
      ))}
    </ul>
  )
}
