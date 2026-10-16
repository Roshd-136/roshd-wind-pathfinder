import type { AltitudeMode } from '../types/routing'

/**
 * تنظیمات مشترک مسیریابی و باندهای ارتفاعی باد — منبع یکسان برای واکشی
 * میدان‌ها (`useWindData`)، فیلتر نمایش لایه‌ها (`RoutingMapScreen`) و
 * محدودهٔ ارتفاعِ درخواست مسیر (پنل تنظیمات)؛ قبلاً همین مقادیر در سه‌جا
 * به‌صورت هاردکد تکرار شده بود.
 */

export interface WindLayerBand {
  /** ارتفاع نمایندهٔ میدان باد این باند (متر MSL) — واکشی و نمایش */
  fieldAltitude: number
  /** مرز بالایی باند (متر MSL) — محدودهٔ ارتفاع درخواست مسیر */
  rangeMax: number
}

/** باندهای ارتفاعی رابط کاربری لایه‌های باد (MSL) — هم‌راستا با FLIGHT_LEVELS_MSL در routing_scene. */
export const WIND_LAYER_BANDS: readonly WindLayerBand[] = [
  { fieldAltitude: 1500, rangeMax: 1500 },
  { fieldAltitude: 2200, rangeMax: 2200 },
  { fieldAltitude: 2900, rangeMax: 2900 },
  { fieldAltitude: 3600, rangeMax: 3600 },
]

/** بیشینهٔ ارتفاع پرواز (متر MSL) — مرز بالای بالاترین باند. */
export const WIND_ALTITUDE_MAX = WIND_LAYER_BANDS[WIND_LAYER_BANDS.length - 1].rangeMax

/**
 * نزدیک‌ترین سطحِ پرواز واقعی به یک ارتفاع آزاد — برای قفل ارتفاع چک‌پوینت.
 *
 * گیمبال صحنهٔ ۳بعدی ارتفاع پیوسته گزارش می‌کند، ولی موتور مسیریابی روی
 * سطح‌های معلوم پرواز می‌کند؛ درِ گزارش (رهاکردن محور «ارتفاع») ارتفاع به
 * همین رده‌ها اسنپ می‌شود تا کاربر دقیقاً بفهمد مسیر «در ارتفاعِ قفل» از
 * چک‌پوینت می‌گذرد. ``minM`` کف مطلق است (زمین + فاصلهٔ امن)؛ اگر هیچ رده
 * از آن بالاتر نرفت، فهرست کامل ملاک است تا اسنپِ زیر زمین نشود.
 */
export function nearestLayerAltitude(altM: number, minM = 0): number {
  const values = WIND_LAYER_BANDS.map((band) => band.fieldAltitude)
  const valid = values.filter((value) => value >= minM)
  const universe = valid.length > 0 ? valid : values
  return universe.reduce((best, value) =>
    Math.abs(value - altM) < Math.abs(best - altM) ? value : best,
  )
}

/**
 * قید «حداکثر سرعت باد» هنوز در موتور مسیریابی اعمال نمی‌شود؛ تا آن روز
 * مقدار آن در درخواست فرستاده نمی‌شود (بک‌اند درخواست حامل این قید را
 * صریحاً رد می‌کند). ثابتی که پیش‌تر به‌عنوان «پیش‌فرض مؤثر» ارسال می‌شد
 * حذف شد — قید جعلی، نتیجهٔ جعلی می‌سازد.
 */
/**
 * بازهٔ ارتفاع متناظر هر باند — برای `altitude_range_m` درخواست مسیر.
 * باندها **نیمه‌بازِ** (پیشین، کنونی]‌اند: هر باند دقیقاً یک سطح پرواز بر
 * می‌دارد (سطحی → ۱۵۰۰، میانی → ۲۲۰۰، بالا → ۲۹۰۰، بالاترین → ۳۶۰۰)، پس
 * «تغییر لایهٔ باد پرواز» واقعاً مسیر همان لایه را می‌سازد. پیش‌تر باند
 * بستهٔ [پیشین، کنونی] فرستاده می‌شد و «میانی» هر دو سطح ۱۵۰۰ و ۲۲۰۰ را
 * می‌گرفت — یعنی مسیر می‌توانست در لایهٔ سطحی هم پرواز کند.
 * «همه» یعنی بدون محدودیت ارتفاع (null).
 */
export function altitudeBandRange(mode: AltitudeMode): [number, number] | null {
  if (mode === 'all') return null
  const index = ALTITUDE_MODES.indexOf(mode)
  const min = index === 0 ? 0 : WIND_LAYER_BANDS[index - 1].rangeMax + BAND_GAP_M
  return [min, WIND_LAYER_BANDS[index].rangeMax]
}

/** گپ یک‌متری مرز باندها — نیمه‌بازکردن (پیشین، کنونی] بدون اعشار. */
export const BAND_GAP_M = 1

/** ترتیب باندها — از ایندکس به باند `WIND_LAYER_BANDS` نگاشت می‌شود. */
export const ALTITUDE_MODES: readonly Exclude<AltitudeMode, 'all'>[] = [
  'surface',
  'mid',
  'high',
  'top',
]
