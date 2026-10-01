import { render } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it, vi } from 'vitest'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Checkbox } from '../components/ui/Checkbox'
import { TextField } from '../components/ui/TextField'
import { WindSpeedLegend } from '../components/features/layers/WindSpeedLegend'
import { WindLayerControls } from '../components/features/layers/WindLayerControls'
import { AlgorithmSelector } from '../components/features/routing/AlgorithmSelector'

/**
 * بررسی خودکار دسترسی‌پذیری (axe-core) روی UI primitives و کامپوننت‌های
 * کلیدی کنترل مسیریابی — چک‌لیست آیتم ۷ (WCAG AA).
 * این جایگزین ممیزی دستی کامل نیست، اما رگرسیون‌های رایج (کنتراست، نبود
 * label، نقش ARIA نادرست) را زود می‌گیرد.
 */
describe('accessibility (axe)', () => {
  it('Button has no violations', async () => {
    const { container } = render(<Button>محاسبه مسیر</Button>)
    expect(await axe(container)).toHaveNoViolations()
  })

  it('Card has no violations', async () => {
    const { container } = render(<Card>محتوا</Card>)
    expect(await axe(container)).toHaveNoViolations()
  })

  it('Checkbox (with label) has no violations', async () => {
    const { container } = render(<Checkbox label="سطحی (۰ تا ۵۰ متر)" checked onChange={() => {}} />)
    expect(await axe(container)).toHaveNoViolations()
  })

  it('TextField (with label) has no violations', async () => {
    const { container } = render(<TextField label="ایمیل" type="email" />)
    expect(await axe(container)).toHaveNoViolations()
  })

  it('WindSpeedLegend has no violations', async () => {
    const { container } = render(<WindSpeedLegend />)
    expect(await axe(container)).toHaveNoViolations()
  })

  it('WindLayerControls has no violations', async () => {
    const { container } = render(
      <WindLayerControls value={{ surface: true, mid: true, high: true }} onChange={vi.fn()} />,
    )
    expect(await axe(container)).toHaveNoViolations()
  })

  it('AlgorithmSelector has no violations', async () => {
    const { container } = render(<AlgorithmSelector value="a_star" onChange={vi.fn()} />)
    expect(await axe(container)).toHaveNoViolations()
  })
})
