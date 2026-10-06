import { ChevronLeft, ChevronRight, Search, Undo2 } from 'lucide-react'
import { useState } from 'react'
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
  /** گام قبلی (فلش راست) — دادهٔ گام‌های بعدی پاک می‌شود تا «تغییر» ممکن باشد. */
  onBack: () => void
  canBack: boolean
  onCalculate: () => void
  canCalculate: boolean
  isCalculating: boolean
}

/**
 * ویزارد مراحل — قاب شناور وسطِ بالای نقشه: جستجوی مکان (فقط رابط) در بالا،
 * عنوان بزرگ گامِ فعال با اسلاید افقی، و دو فلش **در دو سو** قاب: راست =
 * گام قبل (برای تغییر انتخاب‌ها)، چپ = گام بعد (بازتولید مسیر). بدون
 * هم‌پوشانی: عنوان در ناحیهٔ میانی می‌لغزد و فلش‌ها بیرون از آن‌اند.
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
  const achieved = origin === null ? 1 : destination === null ? 2 : 3
  // گام انتخابی هرگز جلوتر از گام «به‌دست‌آمده» نمی‌رود (حالت مشتق — بدون effect)
  const [selectedStep, setSelectedStep] = useState<1 | 2 | 3>(3)
  const step = Math.min(selectedStep, achieved) as 1 | 2 | 3
  const isRtl = document.documentElement.dir === 'rtl'
  const slideSign = isRtl ? 1 : -1
  const NextIcon = isRtl ? ChevronLeft : ChevronRight

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

  const arrowBtn =
    'absolute top-1/2 z-[1] flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-surface-raised text-text-secondary shadow-[var(--shadow-card)] transition-colors hover:border-accent hover:text-accent disabled:pointer-events-none disabled:opacity-30'

  return (
    <div
      className="absolute top-4 left-1/2 z-10 w-[24rem] max-w-[94vw] -translate-x-1/2 rounded-2xl border border-border bg-surface/95 shadow-[var(--shadow-card)] backdrop-blur-sm"
      role="status"
      aria-label={t('routing.stepsTitle')}
    >
      {/* جستجوی مکان — فقط رابط کاربری (منطق جستجو بعداً وصل می‌شود) */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
        <Search size={15} aria-hidden className="shrink-0 text-text-muted" />
        <input
          type="search"
          placeholder={t('wizard.searchPlaceholder')}
          aria-label={t('wizard.searchPlaceholder')}
          className="w-full bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
        />
      </div>

      {/* ناحیهٔ گام — فلش‌ها در دو سو، عنوان میانی بدون هم‌پوشانی می‌لغزد */}
      <div className="relative px-12 py-3">
        <button
          type="button"
          onClick={() => {
            setSelectedStep(Math.max(1, step - 1) as 1 | 2 | 3)
            onBack()
          }}
          disabled={!canBack}
          aria-label={t('routing.back')}
          title={t('routing.back')}
          className={`${arrowBtn} start-2`}
        >
          <Undo2 size={15} aria-hidden />
        </button>
        <button
          type="button"
          onClick={() => setSelectedStep(Math.min(3, step + 1) as 1 | 2 | 3)}
          disabled={step >= achieved}
          aria-label={t('routing.next')}
          title={t('routing.next')}
          className={`${arrowBtn} end-2`}
        >
          <NextIcon size={16} aria-hidden />
        </button>

        <div className="overflow-hidden">
          <div
            className="flex transition-transform duration-500 ease-out"
            style={{ transform: `translateX(${slideSign * (step - 1) * 100}%)` }}
          >
            {slides.map((s) => (
              <div key={s.n} className="w-full shrink-0">
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
      <div className="-mx-px -mb-px overflow-hidden rounded-b-2xl">
        <Button
          className="!w-full !rounded-none !border-0 !shadow-none"
          onClick={onCalculate}
          disabled={!canCalculate || isCalculating}
        >
          {isCalculating ? t('common.loading') : t('routing.calculatePath')}
        </Button>
      </div>
    </div>
  )
}
