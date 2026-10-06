import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MapView } from './MapView'

// maplibre-gl فقط در مرورگر واقعی (WebGL) قابل اجراست؛ در jsdom حتی import
// آن هم شکست می‌خورد. چون این تست فقط رندر کانتینر را بررسی می‌کند، ماژول
// با یک stub کلاس‌محور جایگزین می‌شود — معادل استاندارد mock کردن
// ResizeObserver/matchMedia در تست کامپوننت است.
vi.mock('maplibre-gl', () => {
  class Map {
    addControl = vi.fn()
    on = vi.fn()
    once = vi.fn()
    easeTo = vi.fn()
    setTerrain = vi.fn()
    triggerRepaint = vi.fn()
    remove = vi.fn()
    isStyleLoaded = vi.fn(() => false)
    loaded = vi.fn(() => false)
    getSource = vi.fn()
    addSource = vi.fn()
    addLayer = vi.fn()
    addImage = vi.fn()
    hasImage = vi.fn()
    setLayoutProperty = vi.fn()
    moveLayer = vi.fn()
    fitBounds = vi.fn()
  }
  class Marker {
    setLngLat = vi.fn().mockReturnThis()
    addTo = vi.fn()
    remove = vi.fn()
  }
  class LngLatBounds {}
  class NavigationControl {}
  return { default: { Map, Marker, NavigationControl, AttributionControl: class {}, LngLatBounds } }
})
vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))

describe('MapView', () => {
  it('renders the map container without any token requirement', () => {
    // MapLibre GL آزاد است — برخلاف mapbox نیازی به VITE_MAPBOX_TOKEN ندارد؛
    // نقشه در هر محیطی رندر می‌شود.
    render(
      <MapView
        mode="2d"
        origin={null}
        destination={null}
        path={null}
        viewport={{ mapStyle: 'simple', showArrows: true, showHeatmap: true, showHillshade: true }}
        onMapClick={() => {}}
      />,
    )
    expect(screen.getByRole('application', { name: 'map' })).toBeInTheDocument()
  })
})
