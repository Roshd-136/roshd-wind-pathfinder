import { describe, expect, it } from 'vitest'
import {
  formatAltitudeM,
  formatDistanceKm,
  formatDurationHours,
  formatSpeedMps,
  toFaDigits,
} from './format'

describe('toFaDigits', () => {
  it('all Latin digits become Persian (digits only — dot stays)',
    () => {
      expect(toFaDigits('0123456789')).toBe('۰۱۲۳۴۵۶۷۸۹')
      expect(toFaDigits('80.5 km')).toBe('۸۰٫۵ km'.replace('٫', '.'))
    })
})

describe('formatDistanceKm', () => {
  it('Persian: kilometre with Persian digits and half-space', () => {
    expect(formatDistanceKm(80.45, 'fa')).toBe('۸۰٫۵ ک.م')
    expect(formatDistanceKm(0, 'fa')).toBe('۰٫۰ ک.م')
  })

  it('English keeps the Latin unit', () => {
    expect(formatDistanceKm(80.45, 'en')).toBe('80.5 km')
  })
})

describe('formatDurationHours', () => {
  it('Persian: 1.02 h → «۱س۱د»', () => {
    expect(formatDurationHours(1.02, 'fa')).toBe('۱س۱د')
  })

  it('Persian: the classic example 1 h 20 min', () => {
    expect(formatDurationHours(1 + 20 / 60, 'fa')).toBe('۱س۲۰د')
  })

  it('Persian: round hour drops minutes, sub-hour stays minutes only', () => {
    expect(formatDurationHours(2.0, 'fa')).toBe('۲س')
    expect(formatDurationHours(0.5, 'fa')).toBe('۳۰د')
  })

  it('Persian: 59.8 min rounds to «۱س» — never «۱س۶۰د»', () => {
    expect(formatDurationHours(59.8 / 60, 'fa')).toBe('۱س')
  })

  it('English: keeps h/min', () => {
    expect(formatDurationHours(1 + 20 / 60, 'en')).toBe('1 h 20 min')
    expect(formatDurationHours(0.5, 'en')).toBe('30 min')
  })
})

describe('formatSpeedMps', () => {
  it('Persian: metres per second', () => {
    expect(formatSpeedMps(7.24, 'fa')).toBe('۷٫۲ م/ث')
    expect(formatSpeedMps(7.24, 'en')).toBe('7.2 m/s')
  })
})

describe('formatAltitudeM', () => {
  it('Persian: metres with Persian digits', () => {
    expect(formatAltitudeM(3600, 'fa')).toBe('۳٬۶۰۰ متر')
    expect(formatAltitudeM(3600, 'en')).toBe('3,600 m')
  })
})
