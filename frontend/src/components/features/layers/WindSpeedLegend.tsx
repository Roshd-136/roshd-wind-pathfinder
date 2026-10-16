/**
 * Legend سرعت باد — گرادیان آبی→سبز→زرد→قرمز. رنگ‌آمیزی نقشه **نسبی** است
 * (کمینهٔ میدان → آبی، بیشینه → قرمز؛ `colorForFieldSpeed`)، پس برچسب‌های
 * طیف هم باید بازهٔ *واقعی* میدان‌های نمایان باشند — پیش‌تر برچسب ثابت
 * ۰/۵/۱۰/۱۵/۲۰+ م/ث بود و با رنگ‌های روی نقشه نمی‌خواند.
 */

import { useFormatLang } from '../../../hooks/useFormatLang'

const STOPS = [
  { value: 0, color: 'var(--wind-speed-0)' },
  { value: 5, color: 'var(--wind-speed-5)' },
  { value: 10, color: 'var(--wind-speed-10)' },
  { value: 15, color: 'var(--wind-speed-15)' },
  { value: 20, color: 'var(--wind-speed-20)' },
]

interface WindSpeedLegendProps {
  /** بازهٔ [کمینه، بیشینه] سرعت میدان‌های نمایان (م/ث). */
  range?: [number, number]
}

export function WindSpeedLegend({ range = [0, 20] }: WindSpeedLegendProps) {
  const lang = useFormatLang()
  const gradient = `linear-gradient(to var(--legend-direction, right), ${STOPS.map((s) => s.color).join(', ')})`
  const [min, max] =
    Number.isFinite(range[0]) && Number.isFinite(range[1]) && range[1] > range[0]
      ? range
      : [0, 20]
  const mid = (min + max) / 2
  const format = (value: number) => (Math.round(value * 10) / 10).toString()
  // واحد سرعت — فارسی «م/ث»، انگلیسی m/s
  const unit = lang === 'fa' ? 'م/ث' : 'm/s'

  return (
    <div className="ltr-only text-xs text-text-muted">
      <div className="h-2 w-full rounded-full" style={{ background: gradient }} />
      {/* برچسب‌ها لاتین‌اند (اعداد) — بازهٔ واقعی میدان: کمینه / میانه / بیشینه */}
      <div className="mt-1 flex justify-between" dir="ltr">
        <span>{format(min)}</span>
        <span>{format(mid)}</span>
        <span>
          {format(max)} {unit}
        </span>
      </div>
    </div>
  )
}
