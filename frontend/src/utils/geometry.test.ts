import { describe, expect, it } from 'vitest'
import { chaikinSmoothLine, chaikinSmoothXYZ } from './geometry'

describe('chaikinSmoothLine', () => {
  it('نقطهٔ اول و آخر را دقیقاً حفظ می‌کند', () => {
    const pts: [number, number][] = [
      [0, 0],
      [10, 0],
      [10, 10],
    ]
    const out = chaikinSmoothLine(pts, 2)
    expect(out[0]).toEqual([0, 0])
    expect(out[out.length - 1]).toEqual([10, 10])
  })

  it('خطِ کمتر از سه نقطه بدون تغییر بازمی‌گردد', () => {
    const pts: [number, number][] = [
      [0, 0],
      [10, 10],
    ]
    const out = chaikinSmoothLine(pts)
    expect(out).toEqual(pts)
    expect(out).not.toBe(pts) // نسخهٔ تازه — ورودی معیوب نشود
  })

  it('با صفر تکرار همان ورودی را برمی‌گرداند', () => {
    const pts: [number, number][] = [
      [0, 0],
      [5, 5],
      [10, 0],
    ]
    expect(chaikinSmoothLine(pts, 0)).toEqual(pts)
  })

  it('گوشهٔ قائمه را داخل می‌کشد (چرخش نرم به‌جای شکست تیز)', () => {
    // گوشهٔ تیز مسیر L شکل در رأس [10,0] است — برش گوشه باید از رأس فاصله بگیرد
    const pts: [number, number][] = [
      [0, 0],
      [10, 0],
      [10, 10],
    ]
    const out = chaikinSmoothLine(pts, 2)
    // نقاط میانی (بدون سر و ته که دقیق حفظ می‌شوند) نباید روی رأس گوشه باشند
    const interior = out.slice(1, -1)
    const minDist = Math.min(...interior.map(([x, y]) => Math.hypot(x - 10, y)))
    expect(minDist).toBeGreaterThan(0.5)
    expect(out.length).toBeGreaterThan(pts.length)
  })

  it(' نقاط هم‌خط را روی همان خط نگه می‌دارد (حداکثر انحراف صفر)', () => {
    const pts: [number, number][] = [
      [0, 0],
      [4, 4],
      [8, 8],
      [12, 12],
    ]
    const out = chaikinSmoothLine(pts, 3)
    for (const [x, y] of out) {
      expect(Math.abs(y - x)).toBeLessThan(1e-9)
    }
  })
})

describe('chaikinSmoothXYZ', () => {
  it('سر و ته را نگه می‌دارد و رأس گوشه را از نقاط میانی می‌کَند', () => {
    const pts = [
      { x: 0, y: 0, z: 0 },
      { x: 10, y: 0, z: 100 },
      { x: 10, y: 10, z: 0 },
    ]
    const out = chaikinSmoothXYZ(pts, 2)
    expect(out[0]).toEqual({ x: 0, y: 0, z: 0 })
    expect(out[out.length - 1]).toEqual({ x: 10, y: 10, z: 0 })
    expect(out.length).toBeGreaterThan(pts.length)
    // رأس گوشه {x:10, y:0, z} در نقاط میانی نیست — از آن فاصله گرفته شده
    const interior = out.slice(1, -1)
    const minDist = Math.min(...interior.map((p) => Math.hypot(p.x - 10, p.y)))
    expect(minDist).toBeGreaterThan(0.5)
  })
})
