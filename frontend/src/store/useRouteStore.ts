import { create } from 'zustand'
import type { LayerVisibility } from '../components/features/layers/WindLayerControls'
import type { Algorithm, Coordinate, RouteResult } from '../types/routing'

interface RouteState {
  origin: Coordinate | null
  destination: Coordinate | null
  algorithm: Algorithm
  maxWindSpeed: number
  layerVisibility: LayerVisibility
  result: RouteResult | null
  setOrigin: (c: Coordinate | null) => void
  setDestination: (c: Coordinate | null) => void
  setAlgorithm: (a: Algorithm) => void
  setMaxWindSpeed: (v: number) => void
  setLayerVisibility: (v: LayerVisibility) => void
  setResult: (r: RouteResult | null) => void
  reset: () => void
}

/**
 * انتخاب مبدأ/مقصد و تنظیمات مسیریابی — عمداً جدا از useUiStore، چون این
 * داده باید هنگام جابه‌جایی بین صفحات Map2D/Map3D (دو route جدا، طبق
 * mockup) حفظ شود، نه صرفاً حالت موقتی یک کامپوننت.
 */
export const useRouteStore = create<RouteState>((set) => ({
  origin: null,
  destination: null,
  algorithm: 'a_star',
  maxWindSpeed: 20,
  layerVisibility: { surface: true, mid: true, high: true },
  result: null,
  setOrigin: (origin) => set({ origin }),
  setDestination: (destination) => set({ destination }),
  setAlgorithm: (algorithm) => set({ algorithm }),
  setMaxWindSpeed: (maxWindSpeed) => set({ maxWindSpeed }),
  setLayerVisibility: (layerVisibility) => set({ layerVisibility }),
  setResult: (result) => set({ result }),
  reset: () => set({ origin: null, destination: null, result: null }),
}))
