import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MapTools } from './MapTools'
import { useUiStore } from '../../../store/useUiStore'

/**
 * آزمون نوار ابزار نقشه در دو چیدمان — عمودی (دسکتاپ، با دکمهٔ پنل) و
 * افقی (موبایل، ردیف قابل کشش زیر ویزارد بدون دکمهٔ پنل). رگرسیونِ
 * همپوشانی ابزار با ویزارد موبایل را میبندد: ستون دسکتاپ باید زیر md
 * مخفی باشد و پاپآور «نمای نقشه» در ردیف موبایل زیر دکمه باز شود.
 */

const initialUiState = useUiStore.getState()

describe('MapTools', () => {
  beforeEach(() => {
    useUiStore.setState(initialUiState, true)
  })

  it('vertical layout keeps the panel-toggle button (desktop)', () => {
    const onTogglePanel = vi.fn()
    const { container } = render(
      <MapTools panelOpen={false} onTogglePanel={onTogglePanel} onZoomIn={vi.fn()} onZoomOut={vi.fn()} />,
    )
    // ستون دسکتاپ فقط از md به بالا دیده میشود — روی موبایل مخفی است
    expect(container.firstElementChild?.className).toContain('hidden')
    const toggle = screen.getByRole('button', { name: 'Show control panel' })
    fireEvent.click(toggle)
    expect(onTogglePanel).toHaveBeenCalledTimes(1)
  })

  it('vertical layout switches 2D/3D through the store', () => {
    render(<MapTools panelOpen={false} onTogglePanel={vi.fn()} onZoomIn={vi.fn()} onZoomOut={vi.fn()} />)
    const threeDee = screen.getByRole('button', { name: '3D' })
    expect(threeDee).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(threeDee)
    expect(useUiStore.getState().mapMode).toBe('3d')
    expect(threeDee).toHaveAttribute('aria-pressed', 'true')
  })

  it('vertical layout opens the viewport popover beside the column (side placement)', () => {
    render(<MapTools panelOpen={false} onTogglePanel={vi.fn()} onZoomIn={vi.fn()} onZoomOut={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Map display' }))
    const dialog = screen.getByRole('dialog', { name: 'Map display' })
    expect(dialog.className).toContain('end-full')
  })

  it('horizontal layout drops the panel-toggle button (mobile row under the wizard)', () => {
    const { container } = render(<MapTools layout="horizontal" onZoomIn={vi.fn()} onZoomOut={vi.fn()} />)
    // ردیف موبایل فقط زیر md دیده میشود و دکمهٔ پنلِ شناور در آن بیمعناست
    expect(container.firstElementChild?.className).toContain('md:hidden')
    expect(screen.queryByRole('button', { name: 'Show control panel' })).toBeNull()
  })

  it('horizontal layout wires zoom and 2D/3D like the desktop column', () => {
    const onZoomIn = vi.fn()
    render(<MapTools layout="horizontal" onZoomIn={onZoomIn} onZoomOut={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }))
    expect(onZoomIn).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: '3D' }))
    expect(useUiStore.getState().mapMode).toBe('3d')
  })

  it('horizontal layout opens the viewport popover below the row (no clipping into the sheet)', () => {
    render(<MapTools layout="horizontal" onZoomIn={vi.fn()} onZoomOut={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Map display' }))
    const dialog = screen.getByRole('dialog', { name: 'Map display' })
    expect(dialog.className).toContain('top-full')
    expect(dialog.className).toContain('start-0')
    expect(dialog.className).not.toContain('end-full')
  })
})
