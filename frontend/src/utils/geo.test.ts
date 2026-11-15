import { describe, expect, it } from 'vitest'
import { greatCircleDistanceKm } from './geo'

describe('greatCircleDistanceKm', () => {
  it('یک‌چهارم استوا = πR/2 ≈ ۱۰۰۰۷٫۵ ک.م', () => {
    const d = greatCircleDistanceKm({ lat: 0, lon: 0 }, { lat: 0, lon: 90 })
    expect(d).toBeGreaterThan(10007)
    expect(d).toBeLessThan(10008)
  })

  it('یک درجهٔ عرض جغرافیایی ≈ ۱۱۱٫۲ ک.م', () => {
    const d = greatCircleDistanceKm({ lat: 0, lon: 0 }, { lat: 1, lon: 0 })
    expect(d).toBeGreaterThan(111.0)
    expect(d).toBeLessThan(111.4)
  })

  it('همان نقطه = صفر', () => {
    const p = { lat: 36.297, lon: 59.606 }
    expect(greatCircleDistanceKm(p, p)).toBe(0)
  })

  it('متقارن است (الف→ب = ب→الف)', () => {
    const a = { lat: 36.297, lon: 59.606 }
    const b = { lat: 36.215, lon: 57.678 }
    expect(greatCircleDistanceKm(a, b)).toBeCloseTo(greatCircleDistanceKm(b, a), 9)
  })

  it('دالان آزمایشی مشهد→سبزوار در بازهٔ معقول ۱۵۰ تا ۲۰۰ ک.م', () => {
    // جفت مرجع ROADMAP — مسیر گرافِ ۱۷۳٫۱ ک.م باید به خط مستقیم نزدیک باشد.
    const d = greatCircleDistanceKm(
      { lat: 36.297, lon: 59.606 },
      { lat: 36.215, lon: 57.678 },
    )
    expect(d).toBeGreaterThan(150)
    expect(d).toBeLessThan(200)
  })
})
