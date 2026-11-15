import { afterEach, describe, expect, it, vi } from 'vitest'
import { getWindLayersSnapshot } from './windLayers'

/**
 * نرمالسازی پاسخ `/wind-layers` — کامنت ۱۰ «کامنت‌های نرم‌افزار» (بنر
 * «داده‌های باد مربوط به X روز پیش»). پیشتر تایپ فرانت فقط شکلِ فیکسچر
 * (آرایه) را میخواند و پاسخ واقعی بک‌اند (آبجکت) غلط تفسیر میشد.
 */

afterEach(() => {
  vi.unstubAllGlobals()
})

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: true,
    status,
    json: async () => body,
  } as unknown as Response
}

const NOW = Date.parse('2026-11-15T12:00:00Z')
const HOUR_MS = 3_600_000

describe('getWindLayersSnapshot', () => {
  it('reads the real backend object shape (layers/available/age)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(
      jsonResponse({
        layers: [{ altitude_m: 1500, timestamp: '2026-08-29T12:00:00' }],
        available_altitudes_m: [1500, 2200],
        latest_timestamp: '2026-08-29T12:00:00',
        data_age_hours: 1872,
      }),
    ))
    const snap = await getWindLayersSnapshot()
    expect(snap.altitudes).toEqual([1500, 2200])
    expect(snap.dataAgeHours).toBe(1872)
    expect(snap.latestTimestamp).toBe('2026-08-29T12:00:00')
  })

  it('normalizes the legacy fixture array shape (last_updated → age)', async () => {
    vi.useFakeTimers()
    try {
      vi.setSystemTime(NOW)
      vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('backend down')).mockResolvedValueOnce(
        jsonResponse([
          { altitude_m: 1500, last_updated: new Date(NOW - 2 * HOUR_MS).toISOString() },
          { altitude_m: 2200, last_updated: new Date(NOW - 5 * HOUR_MS).toISOString() },
        ]),
      ))
      const snap = await getWindLayersSnapshot()
      expect(snap.altitudes).toEqual([1500, 2200])
      // جدیدترین مهر (۲ ساعت پیش) مبنای عمر است
      expect(snap.dataAgeHours).toBeCloseTo(2, 5)
    } finally {
      vi.useRealTimers()
    }
  })

  it('returns a null age when the fixture carries no timestamps', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('backend down')).mockResolvedValueOnce(
      jsonResponse([{ altitude_m: 1500, last_updated: 'not-a-date' }]),
    ))
    const snap = await getWindLayersSnapshot()
    expect(snap.dataAgeHours).toBeNull()
    expect(snap.latestTimestamp).toBeNull()
  })
})
