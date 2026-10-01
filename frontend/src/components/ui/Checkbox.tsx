import type { InputHTMLAttributes } from 'react'

interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
}

/** چک‌باکس پایه — برای WindLayerControls (هر لایه ارتفاعی یک ردیف). */
export function Checkbox({ label, className = '', id, ...rest }: CheckboxProps) {
  const inputId = id ?? label.replace(/\s+/g, '-')
  return (
    <label
      htmlFor={inputId}
      className={`flex cursor-pointer items-center gap-2 text-sm text-text-secondary ${className}`}
    >
      <input
        id={inputId}
        type="checkbox"
        className="h-4 w-4 rounded border-border accent-accent"
        {...rest}
      />
      {label}
    </label>
  )
}
