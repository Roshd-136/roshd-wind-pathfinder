import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MapView } from './MapView'

// mapbox-gl فقط در مرورگر واقعی (WebGL) قابل اجراست؛ در jsdom حتی import
// آن هم شکست می‌خورد. چون این تست فقط مسیر «بدون توکن» را بررسی می‌کند
// (که اصلاً از mapbox-gl استفاده نمی‌کند)، ماژول را با یک stub جایگزین
// می‌کنیم — این معادل استاندارد mock کردن ResizeObserver/matchMedia در
// تست کامپوننت است، نه mock کردن منطق تجاری خودمان.
vi.mock('mapbox-gl', () => ({
  default: { accessToken: '', Map: vi.fn(), Marker: vi.fn(), NavigationControl: vi.fn() },
}))
vi.mock('mapbox-gl/dist/mapbox-gl.css', () => ({}))

// بدون VITE_MAPBOX_TOKEN در محیط تست، MapView باید پیام واضح نشان دهد
// نه این‌که تلاش کند یک نقشه WebGL بسازد (که در jsdom ممکن نیست).
describe('MapView', () => {
  it('shows a clear message when no Mapbox token is configured', () => {
    render(
      <MapView mode="2d" origin={null} destination={null} path={null} onMapClick={() => {}} />,
    )
    expect(screen.getByText(/VITE_MAPBOX_TOKEN/)).toBeInTheDocument()
  })
})
