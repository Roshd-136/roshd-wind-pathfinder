import type { InputHTMLAttributes } from 'react'

interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
}

/**
 * چک‌باکس پایه — برای WindLayerControls (هر لایه ارتفاعی یک ردیف).
 * برچسب با دربرگرفتنِ input ارتباط برقرار می‌کند؛ «htmlFor + id» همزمان
 * با دربرگرفتن، باعث نام دسترس‌پذیری تکراری می‌شود (نقض WCAG).
 */
export function Checkbox({ label, className = '', ...rest }: CheckboxProps) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-2 text-sm text-text-secondary ${className}`}
    >
      <input
        type="checkbox"
        className="h-4 w-4 rounded border-border accent-accent"
        {...rest}
      />
      {label}
    </label>
  )
}
