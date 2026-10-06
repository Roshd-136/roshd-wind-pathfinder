import { useTranslation } from 'react-i18next'
import { useUiStore } from '../../../store/useUiStore'

/**
 * قاب تنظیمات «نمای نقشه» — قابی کناری که کنار نوار ابزار باز می‌شود:
 * نقشهٔ پایه (ساده/ماهواره‌ای) و کلیدهای نمایش پیکان‌ها، نقشهٔ رنگی باد و
 * سایهٔ کوهستان. همه در `useUiStore` نگه داشته می‌شود و MapView مستقیماً
 * به آن واکنش نشان می‌دهد.
 */
export function ViewportSettings() {
  const { t } = useTranslation()
  const viewport = useUiStore((s) => s.viewport)
  const setViewport = useUiStore((s) => s.setViewport)
  const toggleViewportSettings = useUiStore((s) => s.toggleViewportSettings)

  const row = 'flex items-center justify-between gap-3 text-xs text-text-secondary'
  const toggle =
    'peer h-4.5 w-8 shrink-0 cursor-pointer appearance-none rounded-full border border-border bg-surface-raised transition-colors checked:border-accent checked:bg-accent relative'
  const styleBtn = (active: boolean) =>
    `flex-1 rounded-lg border px-2 py-1.5 text-xs font-medium transition-colors ${
      active
        ? 'border-accent bg-accent/15 text-accent'
        : 'border-border bg-surface-raised text-text-secondary hover:text-text-primary'
    }`

  return (
    <div
      role="dialog"
      aria-label={t('viewport.title')}
      className="absolute top-0 z-10 w-56 rounded-2xl border border-border bg-surface/95 p-3 shadow-[var(--shadow-card)] backdrop-blur-sm start-[calc(100%+0.5rem)]"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-text-primary">{t('viewport.title')}</span>
        <button
          type="button"
          onClick={toggleViewportSettings}
          aria-label={t('common.close')}
          title={t('common.close')}
          className="text-text-muted transition-colors hover:text-text-primary"
        >
          ✕
        </button>
      </div>

      <p className="mb-1 text-xs text-text-secondary">{t('viewport.mapStyle')}</p>
      <div className="mb-3 flex gap-1.5">
        <button
          type="button"
          onClick={() => setViewport({ mapStyle: 'simple' })}
          aria-pressed={viewport.mapStyle === 'simple'}
          className={styleBtn(viewport.mapStyle === 'simple')}
        >
          {t('viewport.styleSimple')}
        </button>
        <button
          type="button"
          onClick={() => setViewport({ mapStyle: 'satellite' })}
          aria-pressed={viewport.mapStyle === 'satellite'}
          className={styleBtn(viewport.mapStyle === 'satellite')}
        >
          {t('viewport.styleSatellite')}
        </button>
      </div>

      <div className="space-y-2.5">
        <div className={row}>
          <span>{t('viewport.showArrows')}</span>
          <input
            type="checkbox"
            role="switch"
            checked={viewport.showArrows}
            onChange={(e) => setViewport({ showArrows: e.target.checked })}
            aria-label={t('viewport.showArrows')}
            className={toggle}
          />
        </div>
        <div className={row}>
          <span>{t('viewport.showHeatmap')}</span>
          <input
            type="checkbox"
            role="switch"
            checked={viewport.showHeatmap}
            onChange={(e) => setViewport({ showHeatmap: e.target.checked })}
            aria-label={t('viewport.showHeatmap')}
            className={toggle}
          />
        </div>
        <div className={row}>
          <span>{t('viewport.showHillshade')}</span>
          <input
            type="checkbox"
            role="switch"
            checked={viewport.showHillshade}
            onChange={(e) => setViewport({ showHillshade: e.target.checked })}
            aria-label={t('viewport.showHillshade')}
            className={toggle}
          />
        </div>
      </div>
    </div>
  )
}
