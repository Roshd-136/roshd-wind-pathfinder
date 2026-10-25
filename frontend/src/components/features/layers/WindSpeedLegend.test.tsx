import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import i18n from '../../../i18n'
import { WindSpeedLegend } from './WindSpeedLegend'

describe('WindSpeedLegend', () => {
  it('renders the default 0–20 m/s spectrum when no range is given', () => {
    render(<WindSpeedLegend />)
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('20 m/s')).toBeInTheDocument()
  })

  it('labels the spectrum with the actual field range — colors on the map are relative', () => {
    // رنگ‌آمیزی نقشه نسبی است (کمینه → آبی، بیشینه → قرمز)؛ برچسب ثابت
    // ۰-۲۰ قبلی با آن نمی‌خواند.
    render(<WindSpeedLegend range={[4.2, 13.8]} />)
    expect(screen.getByText('4.2')).toBeInTheDocument()
    expect(screen.getByText('9')).toBeInTheDocument()
    expect(screen.getByText('13.8 m/s')).toBeInTheDocument()
    expect(screen.queryByText('20 m/s')).not.toBeInTheDocument()
  })

  it('falls back to the default range for degenerate input', () => {
    render(<WindSpeedLegend range={[7, 7]} />)
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('20 m/s')).toBeInTheDocument()
  })

  it('labels speed in Persian metres-per-second in fa («م/ث»)', async () => {
    await i18n.changeLanguage('fa')
    try {
      render(<WindSpeedLegend range={[4.2, 13.8]} />)
      expect(screen.getByText('13.8 م/ث')).toBeInTheDocument()
      expect(screen.queryByText('13.8 m/s')).not.toBeInTheDocument()
    } finally {
      await i18n.changeLanguage('en')
    }
  })
})
