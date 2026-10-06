import {
  Map as MapIcon,
  Minus,
  Mountain,
  PanelRightClose,
  PanelRightOpen,
  Plus,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useUiStore } from '../../../store/useUiStore'

interface MapToolsProps {
  /** جمع/بازکردن پنل شناور (آیکون فلش وقتی پنل باز است). */
  panelOpen: boolean
  onTogglePanel: () => void
  onZoomIn: () => void
  onZoomOut: () => void
}

/**
 * نوار ابزار عمودی — هم‌تراز با لبهٔ بیرونی پنل شناور: کلید نمایش/جمع‌کردن
 * پنل (فلش)، ۲بعدی/۳بعدی (آیکون) و زوم (+/−). همه آیکونی، بدون متن.
 */
export function MapTools({ panelOpen, onTogglePanel, onZoomIn, onZoomOut }: MapToolsProps) {
  const { t } = useTranslation()
  const mode = useUiStore((s) => s.mapMode)
  const setMapMode = useUiStore((s) => s.setMapMode)

  const btn =
    'flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface/95 text-text-secondary shadow-[var(--shadow-card)] backdrop-blur-sm transition-colors hover:text-text-primary'
  const activeBtn = 'flex h-10 w-10 items-center justify-center rounded-lg border border-accent bg-accent text-white shadow-[var(--shadow-card)]'

  return (
    // با جمع‌شدن پنل، نوار ابزار به لبهٔ نقشه می‌لغزد (transition هماهنگ با پنل)
    <div
      className={`absolute top-4 z-10 flex flex-col gap-1.5 transition-all duration-300 ${
        panelOpen ? 'end-[21.5rem]' : 'end-4'
      }`}
    >
      {/* نمایش/جمع‌کردن پنل — فلش جمع‌شدن وقتی پنل باز است */}
      <button
        type="button"
        onClick={onTogglePanel}
        aria-label={panelOpen ? t('routing.collapsePanel') : t('routing.openPanel')}
        title={panelOpen ? t('routing.collapsePanel') : t('routing.openPanel')}
        className={btn}
      >
        {panelOpen ? <PanelRightClose size={18} aria-hidden /> : <PanelRightOpen size={18} aria-hidden />}
      </button>

      <button
        type="button"
        onClick={() => setMapMode('2d')}
        aria-label={t('map.toggle2d')}
        title={t('map.toggle2d')}
        aria-pressed={mode === '2d'}
        className={mode === '2d' ? activeBtn : btn}
      >
        <MapIcon size={18} aria-hidden />
      </button>
      <button
        type="button"
        onClick={() => setMapMode('3d')}
        aria-label={t('map.toggle3d')}
        title={t('map.toggle3d')}
        aria-pressed={mode === '3d'}
        className={mode === '3d' ? activeBtn : btn}
      >
        <Mountain size={18} aria-hidden />
      </button>

      <div className="my-1 h-px bg-border" aria-hidden />
      <button type="button" onClick={onZoomIn} aria-label="Zoom in" title="Zoom in" className={btn}>
        <Plus size={18} aria-hidden />
      </button>
      <button type="button" onClick={onZoomOut} aria-label="Zoom out" title="Zoom out" className={btn}>
        <Minus size={18} aria-hidden />
      </button>
    </div>
  )
}
