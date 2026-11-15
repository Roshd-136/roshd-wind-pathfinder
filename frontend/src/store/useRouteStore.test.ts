import { beforeEach, describe, expect, it } from 'vitest'
import { useRouteStore } from './useRouteStore'

/**
 * آزمون اکشنهای چک‌پوینتِ استور مسیر — مخصوصاً `setCheckpointAltitude`
 * (کامنت ۸ «کامنت‌های نرم‌افزار»): ارتفاع اجباری باید روی همان ایندکس
 * بنشیند و با null برداشته شود؛ بکاند `Checkpoint.alt` را با gt=0 میخواند
 * و مسیر را دقیقاً در آن ارتفاع قفل میکند.
 */
describe('useRouteStore — checkpoints', () => {
  beforeEach(() => {
    useRouteStore.getState().reset()
    useRouteStore.getState().addCheckpoint({ lat: 36.2, lon: 58.6 })
    useRouteStore.getState().addCheckpoint({ lat: 36.3, lon: 58.9 })
  })

  it('sets the altitude of the right checkpoint only', () => {
    useRouteStore.getState().setCheckpointAltitude(1, 2200)
    const [first, second] = useRouteStore.getState().checkpoints
    expect(first.alt).toBeUndefined()
    expect(second.alt).toBe(2200)
  })

  it('clears the altitude with null (free crossing again)', () => {
    useRouteStore.getState().setCheckpointAltitude(0, 1500)
    useRouteStore.getState().setCheckpointAltitude(0, null)
    expect(useRouteStore.getState().checkpoints[0].alt).toBeUndefined()
  })

  it('keeps the altitude through reordering (order indices are rebuilt)', () => {
    useRouteStore.getState().setCheckpointAltitude(0, 1500)
    useRouteStore.getState().moveCheckpoint(0, 1)
    const [first, second] = useRouteStore.getState().checkpoints
    expect(first.alt).toBeUndefined()
    expect(second.alt).toBe(1500)
    expect(second.order).toBe(1)
  })
})
