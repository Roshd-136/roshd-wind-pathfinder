export interface SegmentedOption<T extends string> {
  value: T
  label: string
}

interface SegmentedProps<T extends string> {
  value: T
  options: ReadonlyArray<SegmentedOption<T>>
  onChange: (value: T) => void
  /** برچسب دسترس‌پذیری گروه — برای نقش radiogroup. */
  ariaLabel: string
}

/**
 * کنترل سگمنتی تک‌انتخاب — برای معیار بهینه‌سازی و باند ارتفاع در پنل مسیر.
 * نقش radiogroup/radio معادل انتخاب تک‌گزینه است؛ چیدمان با flex است تا در
 * RTL و LTR هر دو جهت درست بنشیند (بدون translate جهت‌مند).
 */
export function Segmented<T extends string>({ value, options, onChange, ariaLabel }: SegmentedProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="flex gap-1 rounded-lg border border-border bg-surface-raised p-0.5 shadow-[inset_0_1px_3px_rgba(0,0,0,0.22),inset_0_-1px_2px_rgba(255,255,255,0.04)]"
    >
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-all duration-200 ${
              active
                ? 'm-0.5 bg-accent text-white shadow-[inset_0_1px_3px_rgba(0,0,0,0.35)]'
                : 'm-0 text-text-secondary hover:text-text-primary'
            }`}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
