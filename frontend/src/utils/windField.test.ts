import { describe, expect, it } from 'vitest'
import type { WindField } from '../types/routing'
import {
  arrowFeatures,
  colorForFieldSpeed,
  colorForSpeed,
  gridMeta,
  sampleWindAtPoint,
  speedBucket,
} from './windField'

// میدان ۳×۳ منظم برای تست — همان قالب قرارداد WindField؛ ترتیب ردیف‌ها
// صعودی در عرض (جنوب → شمال)، همان قرارداد خروجی اسکریپت فیکسچر.
const FIELD: WindField = {
  altitude_m: 200,
  vectors: [
    { lat: 35.9, lon: 58.0, speed_mps: 6, direction_deg: 150 },
    { lat: 35.9, lon: 58.05, speed_mps: 10, direction_deg: 160 },
    { lat: 35.9, lon: 58.1, speed_mps: 14, direction_deg: 170 },
    { lat: 35.95, lon: 58.0, speed_mps: 4, direction_deg: 120 },
    { lat: 35.95, lon: 58.05, speed_mps: 8, direction_deg: 130 },
    { lat: 35.95, lon: 58.1, speed_mps: 12, direction_deg: 140 },
    { lat: 36.0, lon: 58.0, speed_mps: 2, direction_deg: 90 },
    { lat: 36.0, lon: 58.05, speed_mps: 6, direction_deg: 100 },
    { lat: 36.0, lon: 58.1, speed_mps: 10, direction_deg: 110 },
  ],
}

describe('colorForSpeed', () => {
  it('returns ramp stop colors at the anchors', () => {
    expect(colorForSpeed(0)).toEqual([37, 99, 235])
    expect(colorForSpeed(5)).toEqual([34, 197, 94])
    expect(colorForSpeed(20)).toEqual([239, 68, 68])
  })

  it('clips outside the ramp', () => {
    expect(colorForSpeed(-3)).toEqual([37, 99, 235])
    expect(colorForSpeed(99)).toEqual([239, 68, 68])
  })

  it('interpolates midpoints', () => {
    const [r, , b] = colorForSpeed(2.5)
    expect(r).toBeGreaterThan(30)
    expect(r).toBeLessThan(40)
    expect(b).toBeGreaterThan(150)
  })
})

describe('speedBucket', () => {
  it('maps speeds to legend buckets', () => {
    expect(speedBucket(0)).toBe('0')
    expect(speedBucket(4.9)).toBe('0')
    expect(speedBucket(5)).toBe('5')
    expect(speedBucket(21)).toBe('20')
  })
})

describe('sampleWindAtPoint', () => {
  it('returns exact grid values at nodes', () => {
    const s = sampleWindAtPoint(FIELD, 36.0, 58.05)
    expect(s.speed_mps).toBe(6)
    expect(s.direction_deg).toBe(100)
  })

  it('bilinearly interpolates between nodes', () => {
    const s = sampleWindAtPoint(FIELD, 35.975, 58.025)
    expect(s.speed_mps).toBeGreaterThan(2)
    expect(s.speed_mps).toBeLessThan(10)
  })

  it('clips outside the field bbox', () => {
    const s = sampleWindAtPoint(FIELD, 40, 60)
    expect(s.speed_mps).toBe(10) // نزدیک‌ترین گوشه شمال‌شرقی
  })
})

describe('arrowFeatures', () => {
  it('sub-samples the grid by stride', () => {
    const arrows = arrowFeatures(FIELD, 2)
    expect(arrows).toHaveLength(4)
    expect(arrows[0].speed_mps).toBe(6) // گوشه جنوب‌غربی (ردیف ۰ = جنوب)
  })
})

describe('gridMeta', () => {
  it('extracts sorted unique axes', () => {
    const meta = gridMeta(FIELD)
    expect(meta.lats).toEqual([35.9, 35.95, 36.0])
    expect(meta.lons).toEqual([58.0, 58.05, 58.1])
    expect(meta.latStep).toBeCloseTo(0.05)
    expect(meta.lonStep).toBeCloseTo(0.05)
  })
})

describe('colorForFieldSpeed (relative coloring — like the routing scene)', () => {
  // بازهٔ سرعت خود میدان — همان دادهٔ واقعی کریدور (حدود ۵ تا ۷٫۹ m/s)
  const range: [number, number] = [4.98, 7.86]

  it('maps field minimum to the blue stop and maximum to the red stop', () => {
    const low = colorForFieldSpeed(range[0], range)
    const high = colorForFieldSpeed(range[1], range)
    // آبی (37،99،235) و قرمز (239،68،68)
    expect(low[2]).toBeGreaterThan(200)
    expect(high[0]).toBeGreaterThan(200)
    expect(low[0]).toBeLessThan(high[0])
  })

  it('produces distinct colors across the field (no single-color field)', () => {
    const a = colorForFieldSpeed(5.0, range)
    const b = colorForFieldSpeed(6.4, range)
    const c = colorForFieldSpeed(7.8, range)
    expect(a).not.toEqual(b)
    expect(b).not.toEqual(c)
  })
})
