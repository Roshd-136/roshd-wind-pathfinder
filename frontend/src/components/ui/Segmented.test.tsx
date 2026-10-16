import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Segmented } from './Segmented'

describe('Segmented', () => {
  it('گزینهٔ فعال علامت‌خورده است و انتخاب گزارش می‌شود', async () => {
    const onChange = vi.fn()
    render(
      <Segmented
        ariaLabel="معیار"
        value="time"
        onChange={onChange}
        options={[
          { value: 'time', label: 'سریع‌ترین' },
          { value: 'energy', label: 'کم‌مصرف' },
        ]}
      />,
    )
    expect(screen.getByRole('radio', { name: 'سریع‌ترین' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'کم‌مصرف' })).not.toBeChecked()
    await userEvent.click(screen.getByRole('radio', { name: 'کم‌مصرف' }))
    expect(onChange).toHaveBeenCalledWith('energy')
  })
})
