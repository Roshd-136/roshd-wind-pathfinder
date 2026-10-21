import { describe, expect, it } from 'vitest'
import type { WindField } from '../types/routing'
import {
  bearingFromDeltaRad,
  computeFightProfile,
  cumulativeFractions,
  fightAtFraction,
  fightPercent,
  nearestField,
  rgbCss,
  segmentBearingRad,
  whiteToRed,
  whiteToRed01,
} from './windFight'

/** میدان همگن — همهٔ بردارها یک جهت/سرعت دارند (تست‌های خوانا). */
function uniformField(altitudeM: number, directionDeg: number): WindField {
  const vectors = [] as WindField['vectors']
  for (let r = 0; r < 5; r += 1) {
    for (let c = 0; c < 5; c += 1) {
      vectors.push({
        lat: 36 + r * 0.03,
        lon: 58 + c * 0.05,
        speed_mps: 10,
        direction_deg: directionDeg,
      })
    }
  }
  return {
    altitude_m: altitudeM,
    unit: 'm/s',
    bbox: [36, 58, 37.12, 58.2],
    last_updated: '2026-01-01T00:00:00Z',
    vectors,
  }
}

describe('fightPercent', () => {
  it('باد از پشت (همسو با جریان) => ۰٪', () => {
    // مسیر به سمت شرق؛ جریان هم به سمت شرق — یعنی باد «از» غرب می‌وزد (270)
    const bearing = bearingFromDeltaRad(0, 1, 36) // شرق
    expect(fightPercent(bearing, 270)).toBeCloseTo(0, 6)
  })

  it('روبه‌بادِ کامل => ۱۰۰٪', () => {
    // مسیر به سمت شرق؛ جریان به سمت غرب — باد «از» شرق می‌وزد (90)
    const bearing = bearingFromDeltaRad(0, 1, 36)
    expect(fightPercent(bearing, 90)).toBeCloseTo(100, 6)
  })

  it('باد جانبی => ~۵۰٪', () => {
    const bearing = bearingFromDeltaRad(0, 1, 36)
    expect(fightPercent(bearing, 180)).toBeCloseTo(50, 6)
    expect(fightPercent(bearing, 0)).toBeCloseTo(50, 6)
  })

  it('بازتابانه — جهتِ اتصال (تقارن سمت راست/چپ)', () => {
    const bearing = bearingFromDeltaRad(0, 1, 36)
    expect(fightPercent(bearing, 45)).toBeCloseTo(fightPercent(bearing, 135), 6)
  })
})

describe('bearing', () => {
  it('شمال = صفر، شرق = حدود +۹۰°، جنوب = حدود ۱۸۰°', () => {
    expect(segmentBearingRad(36, 58, 36.5, 58)).toBeCloseTo(0, 6)
    expect((segmentBearingRad(36, 58, 36, 58.5) * 180) / Math.PI).toBeCloseTo(90, 1)
    expect((segmentBearingRad(36.5, 58, 36, 58) * 180) / Math.PI).toBeCloseTo(180, 1)
  })
})

describe('nearestField', () => {
  const fields = [uniformField(1500, 0), uniformField(2200, 0), uniformField(2900, 0)]
  it('نزدیک‌ترین ارتفاع برمی‌گردد', () => {
    expect(nearestField(2100, fields)?.altitude_m).toBe(2200)
    expect(nearestField(3600, fields)?.altitude_m).toBe(2900)
  })
  it('با میدان خالی null می‌دهد', () => {
    expect(nearestField(2000, [])).toBeNull()
  })
})

describe('computeFightProfile', () => {
  const field = uniformField(2200, 90) // باد از شرق → جریان به سمت غرب
  it('شمال یکنواخت — همه نقاط روبه‌بادِ کامل (۱۰۰)', () => {
    // جریان به غرب می‌وزد؛ خطِ شمالی جریانِ جانبی می‌شود (۵۰) — خط شرقی؟
    // مسیر شمالی با جریانِ غربی: عمود => ~۵۰
    const profile = computeFightProfile(
      [
        { lat: 36, lon: 58.1, alt: 2200 },
        { lat: 36.2, lon: 58.1, alt: 2200 },
        { lat: 36.4, lon: 58.1, alt: 2200 },
      ],
      [field],
    )
    expect(profile).not.toBeNull()
    profile!.forEach((p) => expect(p).toBeCloseTo(50, 2))
  })

  it('مسیر همسو با جریان (غرب) => ۰٪، روبه‌جریان (شرق) => ۱۰۰٪', () => {
    const west = computeFightProfile(
      [
        { lat: 36.2, lon: 58.2, alt: 2200 },
        { lat: 36.2, lon: 58.05, alt: 2200 },
      ],
      [field],
    )
    expect(west![0]).toBeCloseTo(0, 4)
    expect(west![1]).toBeCloseTo(0, 4)
    const east = computeFightProfile(
      [
        { lat: 36.2, lon: 58.05, alt: 2200 },
        { lat: 36.2, lon: 58.2, alt: 2200 },
      ],
      [field],
    )
    expect(east![0]).toBeCloseTo(100, 4)
    expect(east![1]).toBeCloseTo(100, 4)
  })

  it('بدون میدان => null', () => {
    const profile = computeFightProfile(
      [
        { lat: 36, lon: 58 },
        { lat: 36.1, lon: 58 },
      ],
      [],
    )
    expect(profile).toBeNull()
  })

  it('نقطه‌های هم‌مکان (قطعهٔ صفر) مسیر را نمی‌شکند', () => {
    const profile = computeFightProfile(
      [
        { lat: 36.2, lon: 58.2, alt: 2200 },
        { lat: 36.2, lon: 58.2, alt: 2200 }, // تکراری
        { lat: 36.2, lon: 58.05, alt: 2200 },
      ],
      [field],
    )
    // جریان به غرب می‌وزد و مسیر غربی است — همه ≈ ۰٪ (همسو با باد)
    expect(profile![0]).toBeCloseTo(0, 4)
    expect(profile![2]).toBeCloseTo(0, 4)
  })
})

describe('whiteToRed', () => {
  it('دو سرِ رمپ سفید و سرخ است', () => {
    expect(whiteToRed(0)).toEqual([255, 255, 255])
    expect(whiteToRed(100)).toEqual([220, 38, 38])
  })
  it('میانه ≈ میانگینِ خطی', () => {
    expect(whiteToRed(50)).toEqual([238, 147, 147])
  })
  it('خارج از بازه کلیپ می‌شود', () => {
    expect(whiteToRed(-5)).toEqual([255, 255, 255])
    expect(whiteToRed(140)).toEqual([220, 38, 38])
  })
  it('rgbCss رشتهٔ رنگ می‌سازد', () => {
    expect(rgbCss([10, 20, 30])).toBe('rgb(10, 20, 30)')
  })
  it('whiteToRed01 برای GL خروجی ۰..۱ می‌دهد', () => {
    expect(whiteToRed01(0)).toEqual([1, 1, 1])
    expect(whiteToRed01(100)[0]).toBeCloseTo(220 / 255, 6)
    expect(whiteToRed01(100)[1]).toBeCloseTo(38 / 255, 6)
  })
})

describe('cumulativeFractions', () => {
  it('صعودی از ۰ تا ۱', () => {
    const fr = cumulativeFractions([
      { lat: 36, lon: 58 },
      { lat: 36, lon: 58.1 },
      { lat: 36, lon: 58.3 },
    ])
    expect(fr[0]).toBe(0)
    expect(fr[2]).toBeCloseTo(1, 6)
    expect(fr[1]).toBeGreaterThan(0)
    expect(fr[1]).toBeLessThan(1)
    // قطعه دوم دوبرابرِ اول → کسرش نزدیک ۱/۳
    expect(fr[1]).toBeGreaterThan(0.3)
    expect(fr[1]).toBeLessThan(0.37)
  })
  it('با یک نقطه [۰] و با هیچ []', () => {
    expect(cumulativeFractions([{ lat: 36, lon: 58 }])).toEqual([0])
    expect(cumulativeFractions([])).toEqual([])
  })
})

describe('fightAtFraction', () => {
  it('دقیقاً روی نقاط، مقدار نقطه؛ بین‌شان درون‌یابی', () => {
    const profile = [0, 100]
    const fr = [0, 1]
    expect(fightAtFraction(profile, fr, 0)).toBe(0)
    expect(fightAtFraction(profile, fr, 1)).toBe(100)
    expect(fightAtFraction(profile, fr, 0.5)).toBeCloseTo(50, 6)
  })
  it('بیرون از بازه کلیپ', () => {
    expect(fightAtFraction([10, 30], [0.2, 0.8], -1)).toBe(10)
    expect(fightAtFraction([10, 30], [0.2, 0.8], 2)).toBe(30)
  })
})
