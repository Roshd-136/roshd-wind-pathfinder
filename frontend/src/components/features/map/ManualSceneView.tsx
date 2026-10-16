import { useEffect, useRef } from 'react'
import type { Coordinate, Coordinate3D, WindField } from '../../../types/routing'
import { Manual3DScene, type EditTarget } from '../../../three/manual/scene-gl'

interface ManualSceneViewProps {
  origin: Coordinate | null
  destination: Coordinate | null
  /** چک‌پوینت‌ها — ممکن است alt (ارتفاع MSL متر) داشته باشند. */
  checkpoints?: Array<Coordinate & { alt?: number }>
  path3d?: Coordinate3D[] | null
  windFields?: WindField[]
  /** کلید «پیکان‌های باد» تنظیمات نما — در صحنهٔ دستی هم محترم است. */
  showArrows?: boolean
  /** صحنه مخفی است (کاربر در ۲بعدی است): حلقهٔ رندر متوقف ولی داده‌ها زنده. */
  paused?: boolean
  /** هدف فعال گیمبال ویرایش نقطه — null = گیمبال پنهان. */
  editTarget?: EditTarget | null
  /** حالت «افزودن چک‌پوینت» — کلیک بعدی روی دشت زمین نقطه را ثبت می‌کند. */
  placingPoint?: boolean
  /** جابه‌جایی نقطه از گیمبال — در رهاکردن پیکان. */
  onPointEdit?: (target: EditTarget, coord: Coordinate) => void
  /** کلیک روی گوی نشانگر (انتخاب نقطه) — null = کلیک خالی (بستن گیمبال). */
  onPointPick?: (target: EditTarget | null) => void
  onMapClick: (coord: Coordinate) => void
}

/**
 * بوم صحنهٔ سه‌بعدی دست‌ساز (WebGL خام — بدون MapLibre/three.js؛ خواستهٔ
 * کاربر: «کل صحنهٔ ۳بعدی را دستی بکش»). فقط در حالت ۳بعدی mount می‌شود:
 * زمین لندپالی از DEM پروژه، لایه‌های باد معلق در ارتفاع خودشان با پیکان‌های
 * سرعت‌رنگ، لولهٔ مسیر اسپلاین از path_3d و ستون‌های نشانگر مبدأ/مقصد.
 * زمین کاشی‌بندی شده و فقط بخشِ داخل مخروط دید draw می‌شود — ناوبری روان.
 */
export function ManualSceneView({
  origin,
  destination,
  checkpoints = [],
  path3d,
  windFields = [],
  showArrows = true,
  paused = false,
  editTarget = null,
  placingPoint = false,
  onPointEdit,
  onPointPick,
  onMapClick,
}: ManualSceneViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const sceneRef = useRef<Manual3DScene | null>(null)
  // آخرین داده‌ها در ref — boot ناهمگام پس از initTerrain آخرین وضعیت را
  // می‌گیرد و اثر داده هم هر تغییر را به صحنهٔ آماده اعمال می‌کند.
  const dataRef = useRef({ origin, destination, checkpoints, path3d, windFields, showArrows, paused })
  const handlersRef = useRef({ onMapClick, onPointEdit, onPointPick, editTarget })
  useEffect(() => {
    dataRef.current = { origin, destination, checkpoints, path3d, windFields, showArrows, paused }
    handlersRef.current = { onMapClick, onPointEdit, onPointPick, editTarget }
  })

  const applyData = (): void => {
    const scene = sceneRef.current
    if (!scene) return
    const d = dataRef.current
    scene.rebuildDynamic({
      path3d: d.path3d ?? null,
      windFields: d.showArrows ? d.windFields : [],
      origin: d.origin,
      destination: d.destination,
      checkpoints: d.checkpoints,
    })
  }

  // ساخت صحنه — فقط یک‌بار در mount بوم. نگه‌داشته‌شده زنده: وقتی کاربر به
  // ۲بعدی می‌رود کامپوننت mount می‌ماند و فقط حلقهٔ رندر pause می‌شود؛
  // داده‌ها (مسیر/میدان باد) هم‌چنان به rebuildDynamic می‌رسند تا با
  // بازگشت، صحنه به‌روز و بدون ری‌ست باشد.
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    let cancelled = false
    const scene = new Manual3DScene(canvas)
    sceneRef.current = scene
    scene.onMapClick = (lat, lon) => handlersRef.current.onMapClick({ lat, lon })
    scene.onPointEdit = (target, coord) => handlersRef.current.onPointEdit?.(target, coord)
    scene.onPointPick = (target) => handlersRef.current.onPointPick?.(target)
    const boot = async (): Promise<void> => {
      try {
        await scene.initTerrain()
        if (cancelled) return
        applyData()
        // گیمبال اگر پیش از آماده‌شدن صحنه درخواست شده — اعمال
        const h = handlersRef.current
        if (h.editTarget) {
          scene.setEditTarget(h.editTarget, editCoordOf(h.editTarget, dataRef.current))
        }
        if (!dataRef.current.paused) scene.start()
      } catch (err) {
        // زمین/CSV یا WebGL ناموفق — بوم خالی می‌ماند ولی برنامه نمی‌شکند
        console.error('manual 3d scene init failed', err)
      }
    }
    void boot()
    return () => {
      cancelled = true
      scene.dispose()
      sceneRef.current = null
    }
     
  }, [])

  // توقف/ازسرگیری حلقهٔ رندر — مخفی بودن صحنه، بدون دور ریختن هیچ چیز
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene) return
    if (paused) scene.pause()
    else scene.start()
  }, [paused])

  // داده‌های پویا — هر تغییر مسیر/میدان باد/نشانگر بدون بازسازی صحنه
  useEffect(() => {
    applyData()
     
  }, [origin, destination, checkpoints, path3d, windFields, showArrows])

  // هدف گیمبال — هر تغییر (نقطهٔ دیگر یا پنهان‌شدن) مستقیم به صحنه
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene) return
    scene.setEditTarget(editTarget, editCoordOf(editTarget, { origin, destination, checkpoints }))
  }, [editTarget, origin, destination, checkpoints])

  // وضعیت «افزودن چک‌پوینت» — نشانگر موس صحنه را هم نگه‌دار می‌کند.
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene) return
    scene.placingPoint = placingPoint
  }, [placingPoint])

  return <canvas ref={canvasRef} className="h-full w-full touch-none" aria-label="3d scene" role="application" />
}

/** مختصات (و ارتفاع ذخیره‌شده) هدف گیمبال از دادهٔ فعلی صفحه. */
function editCoordOf(
  target: EditTarget | null,
  d: {
    origin: Coordinate | null
    destination: Coordinate | null
    checkpoints: Array<Coordinate & { alt?: number }>
  },
): { lat: number; lon: number; alt?: number } | null {
  if (!target) return null
  if (target.kind === 'origin') return d.origin
  if (target.kind === 'destination') return d.destination
  return d.checkpoints[target.index] ?? null
}
