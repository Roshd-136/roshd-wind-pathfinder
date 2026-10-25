import type { InputHTMLAttributes } from 'react'

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

/** فیلد متنی پایه با نمایش خطای اعتبارسنجی — برای فرم‌های Auth/Settings. */
export function TextField({ label, error, id, className = '', ...rest }: TextFieldProps) {
  const inputId = id ?? label.replace(/\s+/g, '-')
  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-1 block text-sm text-text-secondary">
        {label}
      </label>
      <input
        id={inputId}
        className={`w-full rounded-md border bg-surface-raised px-3 py-2 text-text-primary ${
          error ? 'border-danger' : 'border-border'
        }`}
        aria-invalid={Boolean(error)}
        {...rest}
      />
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  )
}
