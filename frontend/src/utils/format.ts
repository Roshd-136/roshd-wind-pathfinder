/**
 * فرمت‌های نمایش — واحدهای فارسی.
 *
 * کاربر اعداد را با واحدهای فارسی می‌خواند: مسافت «ک.م» (کیلومتر) و زمان به
 * شکل «۱س۲۰د» (۱ ساعت ۲۰ دقیقه). پیش‌تر همه‌جا مقدار خام با «km» و «h» لاتین
 * نمایش داده می‌شد. زبان انگلیسی همان قالب لاتین خودش را دارد.
 */

const FA_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']

/** همهٔ ارقام لاتین یک رشته را به ارقام فارسی تبدیل می‌کند. */
export function toFaDigits(text: string): string {
  return text.replace(/[0-9]/g, (digit) => FA_DIGITS[Number(digit)])
}

/** امتیاز اعشار لاتین به ممیز فارسی. */
function withFaDecimal(value: string): string {
  return value.replace('.', '٫')
}

function faNumber(value: number, fractionDigits = 0): string {
  const text = value.toFixed(fractionDigits)
  return toFaDigits(withFaDecimal(text))
}

export type DisplayLang = 'fa' | 'en'

/**
 * مسافت (کیلومتر) — فارسی: «۸۰٫۵ ک.م»، انگلیسی: «80.5 km».
 */
export function formatDistanceKm(km: number, lang: DisplayLang = 'fa'): string {
  if (lang === 'fa') return `${faNumber(km, 1)} ک.م`
  return `${km.toFixed(1)} km`
}

/**
 * زمان (ساعت اعشاری) — فارسی: «۱س۲۰د» / «۱س» / «۵د»، انگلیسی: «1 h 20 min».
 *
 * دقایق گرد می‌شوند؛ اگر گردشدن به ۶۰ رسید به ساعت برمی‌گردد تا «۱س۶۰د»
 * هرگز نمایش داده نشود.
 */
export function formatDurationHours(hours: number, lang: DisplayLang = 'fa'): string {
  const totalMinutes = Math.max(Math.round(hours * 60), 0)
  let h = Math.floor(totalMinutes / 60)
  let m = totalMinutes - h * 60
  if (m === 60) {
    h += 1
    m = 0
  }
  if (lang === 'fa') {
    if (h > 0 && m > 0) return `${faNumber(h)}س${faNumber(m)}د`
    if (h > 0) return `${faNumber(h)}س`
    return `${faNumber(m)}د`
  }
  if (h > 0 && m > 0) return `${h} h ${m} min`
  if (h > 0) return `${h} h`
  return `${m} min`
}

/**
 * سرعت باد (متر بر ثانیه) — فارسی: «۷٫۲ م/ث»، انگلیسی: «7.2 m/s».
 */
export function formatSpeedMps(mps: number, lang: DisplayLang = 'fa'): string {
  if (lang === 'fa') return `${faNumber(mps, 1)} م/ث`
  return `${mps.toFixed(1)} m/s`
}

/**
 * ارتفاع (متر) — فارسی: «۳٬۶۰۰ متر»، انگلیسی: «3,600 m».
 */
export function formatAltitudeM(meters: number, lang: DisplayLang = 'fa'): string {
  const rounded = Math.round(meters)
  if (lang === 'fa') return `${toFaDigits(rounded.toLocaleString('en-US').replace(/,/g, '٬'))} متر`
  return `${rounded.toLocaleString('en-US')} m`
}
