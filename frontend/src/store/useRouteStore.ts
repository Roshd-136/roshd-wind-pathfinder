import { create } from 'zustand'
import type { LayerVisibility } from '../components/features/layers/WindLayerControls'
import type { Algorithm, Checkpoint, Coordinate, RouteConstraints, RouteResult } from '../types/routing'

interface RouteState {
  origin: Coordinate | null
  destination: Coordinate | null
  checkpoints: Checkpoint[]
  algorithm: Algorithm
  constraints: RouteConstraints
  layerVisibility: LayerVisibility
  result: RouteResult | null
  /** گامِ فعال ویزارد — تعیین می‌کند کلیک بعدی روی نقشه چه چیزی را عوض می‌کند. */
  wizardStep: 1 | 2 | 3
  setOrigin: (c: Coordinate | null) => void
  setDestination: (c: Coordinate | null) => void
  addCheckpoint: (c: Coordinate) => void
  removeCheckpoint: (index: number) => void
  moveCheckpoint: (index: number, direction: -1 | 1) => void
  setAlgorithm: (a: Algorithm) => void
  setConstraints: (c: RouteConstraints) => void
  setLayerVisibility: (v: LayerVisibility) => void
  setResult: (r: RouteResult | null) => void
  setWizardStep: (n: 1 | 2 | 3) => void
  reset: () => void
}

/**
 * انتخاب مبدأ/مقصد و تنظیمات مسیریابی — عمداً جدا از useUiStore، چون این
 * داده باید هنگام جابه‌جایی بین صفحات Map2D/Map3D (دو route جدا، طبق
 * mockup) حفظ شود، نه صرفاً حالت موقتی یک کامپوننت.
 *
 * رفتار بازگشت: گامِ عقب داده را پاک **نمی‌کند** — انتخاب فعلی سر جایش
 * می‌ماند و کلیک بعدی روی نقشه همان گام، آن انتخاب را «جایگزین» می‌کند.
 */
export const useRouteStore = create<RouteState>((set) => ({
  origin: null,
  destination: null,
  checkpoints: [],
  algorithm: 'a_star',
  constraints: { criterion: 'time', max_wind_speed_mps: 20 },
  layerVisibility: { surface: true, mid: true, high: true },
  result: null,
  wizardStep: 1,
  setOrigin: (origin) => set({ origin }),
  setDestination: (destination) => set({ destination }),
  addCheckpoint: (c) =>
    set((s) => ({
      checkpoints: [...s.checkpoints, { ...c, order: s.checkpoints.length }],
    })),
  removeCheckpoint: (index) =>
    set((s) => ({
      checkpoints: s.checkpoints.filter((_, i) => i !== index).map((cp, i) => ({ ...cp, order: i })),
    })),
  moveCheckpoint: (index, direction) =>
    set((s) => {
      const target = index + direction
      if (target < 0 || target >= s.checkpoints.length) return s
      const next = [...s.checkpoints]
      ;[next[index], next[target]] = [next[target], next[index]]
      return { checkpoints: next.map((cp, i) => ({ ...cp, order: i })) }
    }),
  setAlgorithm: (algorithm) => set({ algorithm }),
  setConstraints: (constraints) => set({ constraints }),
  setLayerVisibility: (layerVisibility) => set({ layerVisibility }),
  setResult: (result) => set({ result }),
  setWizardStep: (wizardStep) => set({ wizardStep }),
  reset: () => set({ origin: null, destination: null, checkpoints: [], result: null, wizardStep: 1 }),
}))
