import { create } from 'zustand'
import type {
  Algorithm,
  Checkpoint,
  Coordinate,
  LayerVisibility,
  RouteConstraints,
  RouteResult,
} from '../types/routing'
import { useSettingsStore } from './useSettingsStore'

interface RouteState {
  origin: Coordinate | null
  destination: Coordinate | null
  checkpoints: Checkpoint[]
  algorithm: Algorithm
  constraints: RouteConstraints
  layerVisibility: LayerVisibility
  result: RouteResult | null
  /** مسیرهای جایگزین (معیارهای دیگر) — مثل صحنهٔ مسیریابی */
  alternatives: RouteResult[]
  /** گامِ فعال ویزارد — تعیین می‌کند کلیک بعدی روی نقشه چه چیزی را عوض می‌کند. */
  wizardStep: 1 | 2 | 3
  setOrigin: (c: Coordinate | null) => void
  setDestination: (c: Coordinate | null) => void
  addCheckpoint: (c: Coordinate) => void
  removeCheckpoint: (index: number) => void
  setCheckpointCoord: (index: number, coord: Coordinate) => void
  moveCheckpoint: (index: number, direction: -1 | 1) => void
  setAlgorithm: (a: Algorithm) => void
  setConstraints: (c: RouteConstraints) => void
  setLayerVisibility: (v: LayerVisibility) => void
  setResult: (r: RouteResult | null) => void
  setAlternatives: (r: RouteResult[]) => void
  setWizardStep: (n: 1 | 2 | 3) => void
  reset: () => void
}

/**
 * انتخاب مبدأ/مقصد و تنظیمات مسیریابی — عمداً جدا از useUiStore، چون این
 * داده باید هنگام جابه‌جایی بین صفحات Map2D/Map3D (دو route جدا، طبق
 * mockup) حفظ شود، نه صرفاً حالت موقتی یک کامپوننت.
 *
 * رفتار بازگشت: گامِ عقب انتخابِ همان گام را پاک می‌کند (مقصد در گام ۲،
 * نتیجه در گام ۳) — تا کاربر مجبور شود دوباره انتخاب کند و «بعدی» تا
 * ورودی تازه قفل بماند.
 */
export const useRouteStore = create<RouteState>((set) => ({
  origin: null,
  destination: null,
  checkpoints: [],
  // همگام‌سازی با ترجیحات کاربر — الگوریتم/معیارِ انتخابی در صفحهٔ
  // Settings (استور پایدار) حالا نقطهٔ شروع مسیریابی هم هستند؛ قبلاً دو
  // منبع مستقل بودند و تنظیمات صفحهٔ Settings هرگز اعمال نمی‌شد.
  algorithm: useSettingsStore.getState().defaultAlgorithm,
  constraints: {
    criterion: useSettingsStore.getState().defaultCriterion,
    // ``max_wind_speed_mps`` تا وقتی موتور مسیریابی آن را اعمال نکند فرستاده
    // نمی‌شود: مقدار جعلی یعنی «قیدی که هست ولی نیست». بک‌اند درخواستی که
    // این قید را داشته باشد را صریحاً با ۴۰۰ رد می‌کند.
    max_wind_speed_mps: null,
  },
  layerVisibility: { surface: true, mid: true, high: true, top: true },
  result: null,
  alternatives: [],
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
  // جابه‌جایی مکان چک‌پوینت (گیمبال سه‌بعدی یا ویرایش ۲بعدی) — ترتیب دست‌نخورده
  setCheckpointCoord: (index, coord) =>
    set((s) => ({
      checkpoints: s.checkpoints.map((cp, i) => (i === index ? { ...cp, ...coord } : cp)),
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
  setAlternatives: (alternatives) => set({ alternatives }),
  setWizardStep: (wizardStep) => set({ wizardStep }),
  reset: () => set({ origin: null, destination: null, checkpoints: [], result: null, alternatives: [], wizardStep: 1 }),
}))
