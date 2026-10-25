import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MapView } from './MapView'

// maplibre-gl only works in real browser (WebGL); even import fails in jsdom.
// Since this test only checks container rendering, we replace the module
// with a stub class — equivalent to standard mocking of ResizeObserver/matchMedia.
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
    getLayer = vi.fn()
    resize = vi.fn()
    getCanvas = vi.fn(() => ({
      getContext: () => null, // jsdom has no WebGL
    }))
  }
  class Marker {
    setLngLat = vi.fn().mockReturnThis()
    addTo = vi.fn()
    remove = vi.fn()
  }
  class LngLatBounds {}
  class NavigationControl {}
  class MercatorCoordinate {
    static fromLngLat = vi.fn(() => ({
      x: 0,
      y: 0,
      z: 0,
      meterInMercatorCoordinateUnits: () => 1,
    }))
  }
  return {
    default: { Map, Marker, NavigationControl, AttributionControl: class {}, LngLatBounds },
    MercatorCoordinate,
  }
  
})
vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))

describe('MapView', () => {
  it('renders the map container without any token requirement', () => {
    // MapLibre GL is free — unlike mapbox no VITE_MAPBOX_TOKEN needed;
    // map renders in any environment.
    render(
      <MapView
        mode="2d"
        origin={null}
        destination={null}
        path={null}
        viewport={{
          mapStyle: 'simple',
          showArrows: true,
          showParticles: true,
          showHeatmap: true,
          showHillshade: true,
          animateWind: true,
        }}
        onMapClick={() => {}}
      />,
    )
    expect(screen.getByRole('application', { name: 'map' })).toBeInTheDocument()
  })
})
