interface SwitchProps {
  label: string
  /** توضیح کوتاه زیر برچسب — اختیاری. */
  description?: string
  checked: boolean
  onChange: (checked: boolean) => void
}

/**
 * کلید سوئیچی با برچسب — برای تنظیمات دودویی «نمایش نقشه».
 * دسته با پس‌عنصر (after) ساخته می‌شود تا در RTL و LTR بدون translate
 * جهت‌مند درست کار کند؛ حرکت با inset-inline-start است.
 * aria-label روی input برچسب دربرگیرنده را بازنویسی می‌کند تا نام
 * دسترس‌پذیری تکراری نشود (نقض WCAG).
 */
export function Switch({ label, description, checked, onChange }: SwitchProps) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3">
      <span className="min-w-0">
        <span className="block text-xs font-medium text-text-secondary">{label}</span>
        {description && (
          <span className="block text-[0.6875rem] leading-4 text-text-muted">{description}</span>
        )}
      </span>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={label}
        className="peer relative h-4.5 w-8 shrink-0 cursor-pointer appearance-none rounded-full border border-border bg-surface-raised transition-colors checked:border-accent checked:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent after:absolute after:top-1/2 after:start-[3px] after:h-3 after:w-3 after:-translate-y-1/2 after:rounded-full after:bg-text-muted after:transition-[inset-inline-start] after:content-[''] checked:after:start-[calc(100%-0.9375rem)] checked:after:bg-white"
      />
    </label>
  )
}
