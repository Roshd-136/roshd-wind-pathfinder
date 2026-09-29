import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { Coordinate } from '../../../types/routing'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined

interface MapViewProps {
  mode: '2d' | '3d'
  origin: Coordinate | null
  destination: Coordinate | null
  path: Coordinate[] | null
  onMapClick: (coord: Coordinate) => void
  onPointInfoRequest?: (coord: Coordinate) => void
}

const ROUTE_SOURCE_ID = 'route-line'
const ROUTE_LAYER_ID = 'route-line-layer'

/**
 * نقشه اصلی (Mapbox GL JS) — مطابق mockup: کلیک اول = مبدأ (پین سبز)،
 * کلیک دوم = مقصد (پین قرمز)، و اگر `path` موجود باشد رسم مسیر.
 * حالت 3D با `map.setPitch`/`setTerrain` فعال می‌شود (نیازمند DEM tiles).
 *
 * بدون توکن Mapbox، به‌جای رندر شکسته یا mock، پیام واضح نشان می‌دهد —
 * توکن باید در `.env.local` به‌عنوان `VITE_MAPBOX_TOKEN` تنظیم شود.
 */
export function MapView({ mode, origin, destination, path, onMapClick }: MapViewProps) {
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const originMarkerRef = useRef<mapboxgl.Marker | null>(null)
  const destinationMarkerRef = useRef<mapboxgl.Marker | null>(null)

  useEffect(() => {
    if (!MAPBOX_TOKEN || !containerRef.current || mapRef.current) return

    mapboxgl.accessToken = MAPBOX_TOKEN
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [58.8, 36.2], // مرکز تقریبی ایستگاه‌های خراسان
      zoom: 6,
    })
    map.addControl(new mapboxgl.NavigationControl(), 'bottom-right')

    map.on('click', (e) => {
      onMapClick({ lat: e.lngLat.lat, lon: e.lngLat.lng })
    })

    map.on('load', () => {
      map.addSource(ROUTE_SOURCE_ID, {
        type: 'geojson',
        data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: [] } },
      })
      map.addLayer({
        id: ROUTE_LAYER_ID,
        type: 'line',
        source: ROUTE_SOURCE_ID,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#3b82f6', 'line-width': 4 },
      })
    })

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- init once
  }, [])

  // pitch/bearing برای toggle حالت 3D
  useEffect(() => {
    mapRef.current?.easeTo({ pitch: mode === '3d' ? 60 : 0, duration: 400 })
  }, [mode])

  // نشانگر مبدأ
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (origin) {
      if (!originMarkerRef.current) {
        originMarkerRef.current = new mapboxgl.Marker({ color: '#22c55e' })
      }
      originMarkerRef.current.setLngLat([origin.lon, origin.lat]).addTo(map)
    } else {
      originMarkerRef.current?.remove()
    }
  }, [origin])

  // نشانگر مقصد
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (destination) {
      if (!destinationMarkerRef.current) {
        destinationMarkerRef.current = new mapboxgl.Marker({ color: '#ef4444' })
      }
      destinationMarkerRef.current.setLngLat([destination.lon, destination.lat]).addTo(map)
    } else {
      destinationMarkerRef.current?.remove()
    }
  }, [destination])

  // رسم خط مسیر
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const source = map.getSource(ROUTE_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    source?.setData({
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'LineString',
        coordinates: (path ?? []).map((c) => [c.lon, c.lat]),
      },
    })
  }, [path])

  if (!MAPBOX_TOKEN) {
    return (
      <div className="flex h-full items-center justify-center bg-bg p-6 text-center text-text-muted">
        <p>
          {t('common.error')}: VITE_MAPBOX_TOKEN تنظیم نشده — نقشه بارگذاری نمی‌شود.
          <br />
          یک توکن Mapbox در فایل <code>.env.local</code> قرار دهید.
        </p>
      </div>
    )
  }

  return <div ref={containerRef} className="h-full w-full" role="application" aria-label="map" />
}
