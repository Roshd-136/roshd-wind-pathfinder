import { describe, expect, it } from 'vitest'
import { altitudeBandRange } from './routing'

/**
 * باندهای ارتفاعی نیمه‌بازِ (پیشین، کنونی]‌اند — هر حالت دقیقاً یک سطح پرواز
 * برمی‌دارد. پیش‌تر باند بستهٔ [پیشین، کنونی] فرستاده می‌شد و «میانی» سطح
 * ۱۵۰۰ متری (سطحی) را هم شامل می‌شد؛ یعنی مسیرِ «میانی» می‌توانست در لایهٔ
 * سطحی پرواز کند.
 */
describe('altitudeBandRange', () => {
  it('«همه» بدون محدودیت است', () => {
    expect(altitudeBandRange('all')).toBeNull()
  })

  it('هر باند دقیقاً یک سطح پرواز می‌گیرد', () => {
    // سطحی: [۰، ۱۵۰۰] → فقط ۱۵۰۰
    expect(altitudeBandRange('surface')).toEqual([0, 1500])
    // میانی: (۱۵۰۰، ۲۲۰۰] → فقط ۲۲۰۰ — نه ۱۵۰۰
    expect(altitudeBandRange('mid')).toEqual([1501, 2200])
    // بالا: (۲۲۰۰، ۲۹۰۰] → فقط ۲۹۰۰
    expect(altitudeBandRange('high')).toEqual([2201, 2900])
    // بالاترین: (۲۹۰۰، ۳۶۰۰] → فقط ۳۶۰۰ — این باند پیش‌تر اصلاً انتخاب‌شدنی نبود
    expect(altitudeBandRange('top')).toEqual([2901, 3600])
  })
})
