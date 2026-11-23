import { describe, expect, it } from 'vitest'
import { insideGridMask, isInsideIran, pointInRing } from './iranMask'

describe('pointInRing — آزمون even-odd', () => {
  const square: ReadonlyArray<readonly [number, number]> = [
    [0, 0],
    [10, 0],
    [10, 10],
    [0, 10],
  ]

  it('داخل و بیرون مربع را درست تشخیص می‌دهد', () => {
    expect(pointInRing(5, 5, square)).toBe(true)
    expect(pointInRing(11, 5, square)).toBe(false)
    expect(pointInRing(5, -1, square)).toBe(false)
  })
})

describe('isInsideIran — مرز واقعی کشور', () => {
  it('شهرهای داخل ایران را می‌پذیرد', () => {
    expect(isInsideIran(35.689, 51.389)).toBe(true) // تهران
    expect(isInsideIran(36.297, 59.606)).toBe(true) // مشهد
    expect(isInsideIran(32.654, 51.667)).toBe(true) // اصفهان
    expect(isInsideIran(38.08, 46.291)).toBe(true) // تبریز
    expect(isInsideIran(26.85, 55.9)).toBe(true) // قشم
  })

  it('کشورهای همسایه را رد می‌کند', () => {
    expect(isInsideIran(33.315, 44.361)).toBe(false) // بغداد
    expect(isInsideIran(34.555, 69.207)).toBe(false) // کابل
    expect(isInsideIran(37.95, 58.383)).toBe(false) // عشق‌آباد
    expect(isInsideIran(25.204, 55.296)).toBe(false) // دبی
    expect(isInsideIran(40.409, 49.867)).toBe(false) // باکو
  })
})

describe('insideGridMask — ماسک ردیف‌محور', () => {
  it('طول ماسک برابر rows × cols است', () => {
    const mask = insideGridMask([35, 36], [51, 52, 53])
    expect(mask).toHaveLength(6)
    expect(mask.every(Boolean)).toBe(true)
  })
})
