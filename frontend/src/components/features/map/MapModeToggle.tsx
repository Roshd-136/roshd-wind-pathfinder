import { useTranslation } from 'react-i18next'
import { useUiStore } from '../../../store/useUiStore'

/**
 * سوییچ ۲بعدی/۳بعدی — فقط تغییر حالت روی «همین نقشه» است (بدون ناوبری و
 * بدون بازسازی نقشه): در ۳بعدی ترن واقعی روشن و کاشی خیابان خاموش می‌شود.
 * حالت در `useUiStore.mapMode` نگه داشته می‌شود تا مبدأ/مقصد/مسیر چیزی از
 * دست ندهد.
 */
export function MapModeToggle() {
  const { t } = useTranslation()
  const mode = useUiStore((s) => s.mapMode)
  const setMapMode = useUiStore((s) => s.setMapMode)

  const base = 'rounded-md px-3 py-1 text-xs font-medium transition-colors'
  const active = 'bg-accent text-white'
  const inactive = 'text-text-secondary hover:text-text-primary'

  return (
    <div
      role="tablist"
      aria-label={t('map.title')}
      className="absolute bottom-4 end-4 z-10 flex flex-col gap-1 rounded-lg border border-border bg-surface p-1"
    >
      <button
        type="button"
        role="tab"
        aria-selected={mode === '2d'}
        onClick={() => setMapMode('2d')}
        className={`${base} ${mode === '2d' ? active : inactive}`}
      >
        {t('map.toggle2d')}
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === '3d'}
        onClick={() => setMapMode('3d')}
        className={`${base} ${mode === '3d' ? active : inactive}`}
      >
        {t('map.toggle3d')}
      </button>
    </div>
  )
}
