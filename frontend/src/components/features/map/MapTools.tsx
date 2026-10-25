import {
  Map as MapIcon,
  Minus,
  Mountain,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  SlidersHorizontal,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useUiStore } from '../../../store/useUiStore'
import { ViewportSettings } from './ViewportSettings'

interface MapToolsProps {
  /** جمع/بازکردن پنل شناور (آیکون فلش وقتی پنل باز است). */
  panelOpen: boolean
  onTogglePanel: () => void
  onZoomIn: () => void
  onZoomOut: () => void
}

/**
 * نوار ابزار عمودی — هم‌تراز با لبهٔ بیرونی پنل شناور: کلید نمایش/جمع‌کردن
 * پنل (فلش)، تنظیمات «نمای نقشه» (قاب کناری با نقشهٔ پایه و کلیدهای
 * نمایش)، ۲بعدی/۳بعدی (آیکون) و زوم (+/−). همه آیکونی، بدون متن.
 */
export function MapTools({ panelOpen, onTogglePanel, onZoomIn, onZoomOut }: MapToolsProps) {
  const { t } = useTranslation()
  const mode = useUiStore((s) => s.mapMode)
  const setMapMode = useUiStore((s) => s.setMapMode)
  const isViewportSettingsOpen = useUiStore((s) => s.isViewportSettingsOpen)
  const toggleViewportSettings = useUiStore((s) => s.toggleViewportSettings)

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
      {/* کلیک بیرون پاپ‌آور → فقط بستن؛ کلیک به نقشه/سایر عناصر عبور نمی‌کند */}
      {isViewportSettingsOpen && (
        <div
          aria-hidden
          className="fixed inset-0 z-[15]"
          onClick={toggleViewportSettings}
        />
      )}
      {/* قاب تنظیمات نمای نقشه — کنار نوار ابزار باز می‌شود */}
      {isViewportSettingsOpen && <ViewportSettings />}

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


      {/* ۲بعدی/۳بعدی — گروه عمودی هم‌عرض دکمه‌های تکی نوار ابزار: ظرفِ
          باحاشیه با padding داخلی، دکمه‌های بدون حاشیه و هم‌اندازه (۴۰×۴۰)،
          گوشهٔ ظرف هم‌شعاع بقیه، سایهٔ inset برای عمق. */}
      <div
        role="group"
        aria-label={t('map.toggle2d')}
        className="flex w-10 flex-col items-center rounded-lg border border-border bg-surface/95 p-1 shadow-[var(--shadow-card),inset_0_1px_2px_rgba(255,255,255,0.06),inset_0_-1px_2px_rgba(0,0,0,0.18)] backdrop-blur-sm"
      >
        <button
          type="button"
          onClick={() => setMapMode('2d')}
          aria-label={t('map.toggle2d')}
          title={t('map.toggle2d')}
          aria-pressed={mode === '2d'}
          className={`flex h-8 w-full items-center justify-center rounded-md transition-colors ${
            mode === '2d'
              ? 'bg-accent text-white shadow-[inset_0_1px_3px_rgba(0,0,0,0.35)]'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <MapIcon size={16} aria-hidden />
        </button>
        <button
          type="button"
          onClick={() => setMapMode('3d')}
          aria-label={t('map.toggle3d')}
          title={t('map.toggle3d')}
          aria-pressed={mode === '3d'}
          className={`flex h-8 w-full items-center justify-center rounded-md transition-colors ${
            mode === '3d'
              ? 'bg-accent text-white shadow-[inset_0_1px_3px_rgba(0,0,0,0.35)]'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Mountain size={16} aria-hidden />
        </button>
      </div>

      <div className="h-px bg-border" aria-hidden />

      {/* تنظیمات «نمای نقشه» — زیر جداکننده و بالای زوم */}
      <button
        type="button"
        onClick={toggleViewportSettings}
        aria-label={t('viewport.title')}
        title={t('viewport.title')}
        aria-pressed={isViewportSettingsOpen}
        className={isViewportSettingsOpen ? activeBtn : btn}
      >
        <SlidersHorizontal size={18} aria-hidden />
      </button>

      <button type="button" onClick={onZoomIn} aria-label="Zoom in" title="Zoom in" className={btn}>
        <Plus size={18} aria-hidden />
      </button>
      <button type="button" onClick={onZoomOut} aria-label="Zoom out" title="Zoom out" className={btn}>
        <Minus size={18} aria-hidden />
      </button>
    </div>
  )
}
