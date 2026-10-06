import { Undo2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import type { Coordinate } from '../../../types/routing'
import { reverseGeocode } from '../../../utils/geocode'
import { useSettingsStore } from '../../../store/useSettingsStore'
import { Button } from '../../ui/Button'

/** نام مکان یک نقطه (استان/شهر/خیابان) — ژئوکدینگ معکوس آزاد OSM. */
function PlaceLabel({ point }: { point: Coordinate }) {
  const language = useSettingsStore((s) => s.language)
  const { data } = useQuery({
    queryKey: ['geocode', point.lat.toFixed(3), point.lon.toFixed(3), language],
    queryFn: () => reverseGeocode(point.lat, point.lon, language),
    staleTime: Infinity,
  })
  const fallback = `${point.lat.toFixed(3)}, ${point.lon.toFixed(3)}`
  return <>{data ?? fallback}</>
}

interface StepsWizardProps {
  origin: Coordinate | null
  destination: Coordinate | null
  hasResult: boolean
  onBack: () => void
  canBack: boolean
  onCalculate: () => void
  canCalculate: boolean
  isCalculating: boolean
}

/**
 * ویزارد مراحل — قاب شناور بالای نقشه (وسط) با **اسلاید افقی**: با تکمیل هر
 * گام، نوار گام‌ها به‌صورت افقی به گام بعدی می‌لغزد (در RTL برعکس). گام‌ها:
 * ۱. انتخاب مبدأ، ۲. انتخاب مقصد، ۳. محاسبهٔ مسیر.
 */
export function StepsWizard({
  origin,
  destination,
  hasResult,
  onBack,
  canBack,
  onCalculate,
  canCalculate,
  isCalculating,
}: StepsWizardProps) {
  const { t } = useTranslation()
  const step = origin === null ? 1 : destination === null ? 2 : 3
  const isRtl = document.documentElement.dir === 'rtl'
  const slideSign = isRtl ? 1 : -1

  const slides = [
    {
      n: 1,
      title: t('routing.stepOrigin'),
      done: origin !== null,
      placeLabel: origin !== null ? t('routing.stepOriginDone') : null,
      point: origin,
    },
    {
      n: 2,
      title: t('routing.stepDestination'),
      done: destination !== null,
      placeLabel: destination !== null ? t('routing.stepDestinationDone') : null,
      point: destination,
    },
    {
      n: 3,
      title: t('routing.stepCompute'),
      done: hasResult,
      placeLabel: hasResult ? t('routing.stepComputeDone') : null,
      point: null,
    },
  ]

  return (
    <div
      className="absolute top-4 left-1/2 z-10 w-[22rem] max-w-[92vw] -translate-x-1/2 rounded-2xl border border-border bg-surface/95 shadow-[var(--shadow-card)] backdrop-blur-sm"
      role="status"
      aria-label={t('routing.stepsTitle')}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2">
        <span className="text-xs font-medium text-text-muted">{t('routing.stepsTitle')}</span>
        <button
          type="button"
          onClick={onBack}
          disabled={!canBack}
          aria-label={t('routing.back')}
          title={t('routing.back')}
          className="flex h-7 w-7 items-center justify-center rounded-full border border-border bg-surface-raised text-text-secondary transition-colors hover:text-text-primary disabled:opacity-30"
        >
          <Undo2 size={13} aria-hidden />
        </button>
      </div>

      {/* نوار افقی گام‌ها — با تغییر گام به سمت بعدی می‌لغزد */}
      <div className="overflow-hidden px-3 py-2">
        <div
          className="flex transition-transform duration-500 ease-out"
          style={{ transform: `translateX(${slideSign * (step - 1) * 100}%)` }}
        >
          {slides.map((s) => (
            <div key={s.n} className="w-full shrink-0 px-1">
              <p className="truncate text-center text-2xl font-extrabold leading-tight text-text-primary">
                {s.title}
              </p>
              {s.done && s.placeLabel && (
                <p className="step-swap mt-1 truncate text-center text-sm text-text-secondary">
                  {s.placeLabel}
                  {s.point ? <>: <PlaceLabel point={s.point} /></> : null}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* نشانگر پیشرفت */}
      <div className="flex items-center justify-center gap-1.5 pb-2">
        {slides.map((s) => (
          <span
            key={s.n}
            aria-hidden
            className={`h-1.5 rounded-full transition-all ${
              s.n === step ? 'w-6 bg-accent' : s.done ? 'w-3 bg-success/70' : 'w-3 bg-border'
            }`}
          />
        ))}
      </div>
      <Button className="w-full" onClick={onCalculate} disabled={!canCalculate || isCalculating}>
        {isCalculating ? t('common.loading') : t('routing.calculatePath')}
      </Button>
    </div>
  )
}
