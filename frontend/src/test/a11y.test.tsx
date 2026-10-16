import { render } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it, vi } from 'vitest'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Checkbox } from '../components/ui/Checkbox'
import { TextField } from '../components/ui/TextField'
import { Switch } from '../components/ui/Switch'
import { Segmented } from '../components/ui/Segmented'
import { WindSpeedLegend } from '../components/features/layers/WindSpeedLegend'
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

  it('Switch (with label) has no violations', async () => {
    const { container } = render(
      <Switch label="جریان باد" description="ردّ جریان باد روی نقشه" checked onChange={() => {}} />,
    )
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

  it('Segmented (radiogroup) has no violations', async () => {
    const { container } = render(
      <Segmented
        ariaLabel="معیار بهینه‌سازی"
        value="time"
        onChange={vi.fn()}
        options={[
          { value: 'time', label: 'سریع‌ترین' },
          { value: 'energy', label: 'کم‌مصرف' },
          { value: 'balanced', label: 'متعادل' },
        ]}
      />,
    )
    expect(await axe(container)).toHaveNoViolations()
  })

  it('AlgorithmSelector has no violations', async () => {
    const { container } = render(<AlgorithmSelector value="a_star" onChange={vi.fn()} />)
    expect(await axe(container)).toHaveNoViolations()
  })
})
