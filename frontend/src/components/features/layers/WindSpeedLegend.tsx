const STOPS = [
  { value: 0, color: 'var(--wind-speed-0)' },
  { value: 5, color: 'var(--wind-speed-5)' },
  { value: 10, color: 'var(--wind-speed-10)' },
  { value: 15, color: 'var(--wind-speed-15)' },
  { value: 20, color: 'var(--wind-speed-20)' },
]

/**
 * Legend سرعت باد — گرادیان آبی→سبز→زرد→قرمز با برچسب‌های 0/5/10/15/20+ m/s،
 * دقیقاً مطابق mockup. رنگ‌ها از توکن‌های `--wind-speed-*` در tokens.css.
 */
export function WindSpeedLegend() {
  const gradient = `linear-gradient(to var(--legend-direction, right), ${STOPS.map((s) => s.color).join(', ')})`

  return (
    <div className="ltr-only text-xs text-text-muted">
      <div className="h-2 w-full rounded-full" style={{ background: gradient }} />
      <div className="mt-1 flex justify-between">
        {STOPS.map((s, i) => (
          <span key={s.value}>
            {s.value}
            {i === STOPS.length - 1 ? '+' : ''}
          </span>
        ))}
      </div>
    </div>
  )
}
