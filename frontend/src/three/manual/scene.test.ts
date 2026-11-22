import { describe, expect, it } from 'vitest'
import type { WindField } from '../../types/routing'
import { isInsideIran } from '../../utils/iranMask'
import { buildWindArrows, makeFrame, type TerrainData } from './scene'

// کادر سراسری ایران و زمین تخت — همان چیزی که نمای کشور می‌بیند.
const FRAME = makeFrame([44, 25, 63.5, 40])
const FLAT_TERRAIN: TerrainData = {
  lats: [25, 40],
  lons: [44, 63.5],
  elev: new Float32Array([0, 0, 0, 0]),
  rows: 2,
  cols: 2,
}

/** میدان ۳۱×۴۰ با گام ۰٫۵° — همان شبکهٔ نمایش سراسری. */
function nationwideField(): WindField {
  const vectors = []
  for (let row = 0; row < 31; row += 1) {
    for (let col = 0; col < 40; col += 1) {
      vectors.push({
        lat: 25 + row * 0.5,
        lon: 44 + col * 0.5,
        speed_mps: 5 + (row % 4) * 5,
        direction_deg: 270,
      })
    }
  }
  return { altitude_m: 3600, vectors }
}

describe('buildWindArrows — تراکم نمای سراسری', () => {
  it('فقط پیکان‌های داخل مرز ایران را می‌کشد، نه کل مستطیل', () => {
    const mesh = buildWindArrows(nationwideField(), FRAME, FLAT_TERRAIN, 0)
    // انتظار را از همان چندضلعی می‌شماریم؛ تعداد باید *کمتر* از کل شبکه
    // مستطیلی باشد (باد روی عراق/افغانستان/دریا کشیده نمی‌شود) ولی هنوز
    // صدها پیکان سراسر کشور را بپوشاند.
    let inside = 0
    for (let row = 0; row < 31; row += 1) {
      for (let col = 0; col < 40; col += 1) {
        if (isInsideIran(25 + row * 0.5, 44 + col * 0.5)) inside += 1
      }
    }
    expect(inside).toBeGreaterThan(550)
    expect(inside).toBeLessThan(31 * 40)
    // هر پیکان ۹ رأس است
    expect(mesh.count).toBe(inside * 9)
  })

  it('سلول بیرون مرز (عراق) هیچ پیکانی نمی‌گیرد', () => {
    const twoPoints: WindField = {
      altitude_m: 3600,
      vectors: [
        { lat: 35.7, lon: 51.4, speed_mps: 8, direction_deg: 270 }, // تهران
        { lat: 33.3, lon: 44.4, speed_mps: 8, direction_deg: 270 }, // بغداد
      ],
    }
    const mesh = buildWindArrows(twoPoints, FRAME, FLAT_TERRAIN, 0)
    expect(mesh.count).toBe(9) // فقط پیکان تهران
  })

  it('طول پیکان با فاصلهٔ شبکه مقیاس می‌گیرد (نه سقف ثابت ۵ کیلومتر)', () => {
    const mesh = buildWindArrows(nationwideField(), FRAME, FLAT_TERRAIN, 0)
    const spacingKm = Math.max(FRAME.widthKm, FRAME.heightKm) / 39
    let widest = 0
    for (let arrow = 0; arrow < mesh.count; arrow += 9) {
      let minX = Infinity
      let maxX = -Infinity
      let minY = Infinity
      let maxY = -Infinity
      for (let vertex = arrow; vertex < arrow + 9; vertex += 1) {
        const x = mesh.positions[vertex * 3]
        const y = mesh.positions[vertex * 3 + 1]
        minX = Math.min(minX, x)
        maxX = Math.max(maxX, x)
        minY = Math.min(minY, y)
        maxY = Math.max(maxY, y)
      }
      widest = Math.max(widest, maxX - minX, maxY - minY)
    }
    expect(widest).toBeGreaterThan(spacingKm * 0.3)
    expect(widest).toBeLessThanOrEqual(spacingKm * 0.95)
  })
})
