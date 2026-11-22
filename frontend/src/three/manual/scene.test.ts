import { describe, expect, it } from 'vitest'
import type { WindField } from '../../types/routing'
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
  it('کل شبکهٔ نمایش را می‌کشد، نه زیرنمونهٔ ۹×۱۴', () => {
    const mesh = buildWindArrows(nationwideField(), FRAME, FLAT_TERRAIN, 0)
    // هر پیکان ۹ رأس است؛ ۱۲۴۰ پیکان یعنی ۱۱۱۶۰ رأس.
    expect(mesh.count).toBe(31 * 40 * 9)
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
