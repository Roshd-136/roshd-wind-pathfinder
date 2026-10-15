interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  label?: string
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
}

/** Dropdown پایه — برای AlgorithmSelector. */
export function Select({ label, value, options, onChange }: SelectProps) {
  return (
    <label className="block text-sm">
      {label && <span className="mb-1 block text-text-secondary">{label}</span>}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-border bg-surface-raised px-3 py-2 text-text-primary"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  )
}
