import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WindSpeedLegend } from './WindSpeedLegend'

describe('WindSpeedLegend', () => {
  it('renders all 5 scale labels from the mockup legend (0/5/10/15/20+)', () => {
    render(<WindSpeedLegend />)
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('20+')).toBeInTheDocument()
  })
})
