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
  /**
   * `horizontal` — نوار افقی با سه برچسب (پیشفرض، دسکتاپ). `vertical` —
   * نوار عمودی با کمینه بالا و بیشینه پایین (موبایل): نوار افقیِ عریضِ
   * ‏۲۰rem روی گوشی جا نمی‌شد و زیر شیت جمعشده پنهان میشد (بازخورد تست
   * موبایل).
   */
  orientation?: 'horizontal' | 'vertical'
}

export function WindSpeedLegend({ range = [0, 20], orientation = 'horizontal' }: WindSpeedLegendProps) {
  const lang = useFormatLang()
  const isVertical = orientation === 'vertical'
  const gradient = isVertical
    ? `linear-gradient(to bottom, ${STOPS.map((s) => s.color).join(', ')})`
    : `linear-gradient(to var(--legend-direction, right), ${STOPS.map((s) => s.color).join(', ')})`
  const [min, max] =
    Number.isFinite(range[0]) && Number.isFinite(range[1]) && range[1] > range[0]
      ? range
      : [0, 20]
  const mid = (min + max) / 2
  const format = (value: number) => (Math.round(value * 10) / 10).toString()
  // واحد سرعت — فارسی «م/ث»، انگلیسی m/s
  const unit = lang === 'fa' ? 'م/ث' : 'm/s'

  if (isVertical) {
    // عمودی — نوار باریک بلند؛ کمینه بالا، بیشینه پایین، واحد «م/ث» کنارِ
    // نوار (نه زیر آن — بازخورد تست موبایل). اعداد لاتین‌اند؛ با dir=ltr
    // ترتیب کمینه→بیشینه از بالا به پایین ثابت است.
    return (
      <div className="flex flex-col items-center gap-1 text-[10px] leading-none text-text-muted" dir="ltr">
        <span>{format(min)}</span>
        <div className="flex items-center gap-1">
          <div className="h-24 w-2 rounded-full" style={{ background: gradient }} />
          <span className="[writing-mode:vertical-rl] text-text-muted">{unit}</span>
        </div>
        <span>{format(max)}</span>
      </div>
    )
  }

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
