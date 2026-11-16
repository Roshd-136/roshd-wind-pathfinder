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
  /**
   * `vertical` — ستون کنار پنل شناور دسکتاپ (پیشفرض). `horizontal` —
   * ردیف افقی قابل کشش زیر ویزارد در موبایل: قبلاً ستونِ `top-4 end-4`
   * روی موبایل هم رندر میشد و با ویزارد همپوشانی می‌ساخت (بازخورد تست
   * موبایل)؛ حالا ستون فقط از md به بالا دیده میشود و ردیف فقط زیر md.
   */
  layout?: 'vertical' | 'horizontal'
  /** جمع/بازکردن پنل شناور (آیکون فلش وقتی پنل باز است) — فقط حالت عمودی. */
  panelOpen?: boolean
  onTogglePanel?: () => void
  onZoomIn: () => void
  onZoomOut: () => void
}

export function MapTools({
  layout = 'vertical',
  panelOpen = false,
  onTogglePanel,
  onZoomIn,
  onZoomOut,
}: MapToolsProps) {
  const { t } = useTranslation()
  const mode = useUiStore((s) => s.mapMode)
  const setMapMode = useUiStore((s) => s.setMapMode)
  const isViewportSettingsOpen = useUiStore((s) => s.isViewportSettingsOpen)
  const toggleViewportSettings = useUiStore((s) => s.toggleViewportSettings)
  const isHorizontal = layout === 'horizontal'

  const btn = isHorizontal
    ? 'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface/95 text-text-secondary shadow-[var(--shadow-card)] backdrop-blur-sm transition-colors hover:text-text-primary'
    : 'flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface/95 text-text-secondary shadow-[var(--shadow-card)] backdrop-blur-sm transition-colors hover:text-text-primary'
  const activeBtn = isHorizontal
    ? 'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-accent bg-accent text-white shadow-[var(--shadow-card)]'
    : 'flex h-10 w-10 items-center justify-center rounded-lg border border-accent bg-accent text-white shadow-[var(--shadow-card)]'

  const modeBtn = (mapMode: '2d' | '3d') =>
    `flex ${isHorizontal ? 'h-9 w-9' : 'h-8 w-full'} items-center justify-center rounded-md transition-colors ${
      mode === mapMode
        ? 'bg-accent text-white shadow-[inset_0_1px_3px_rgba(0,0,0,0.35)]'
        : 'text-text-secondary hover:text-text-primary'
    }`

  return (
    // با جمع‌شدن پنل، ستون ابزار به لبهٔ نقشه می‌لغزد (transition هماهنگ با پنل).
    // ردیف موبایل در پوشش ویزاردِ RoutingMapScreen جا میگیرد و موضع خودش را ندارد.
    <div
      className={
        isHorizontal
          ? 'relative z-10 w-full md:hidden'
          : `absolute top-4 z-10 hidden transition-all duration-300 md:flex ${
              panelOpen ? 'end-[21.5rem]' : 'end-4'
            }`
      }
    >
      {/* کلیک بیرون پاپ‌آور → فقط بستن؛ کلیک به نقشه/سایر عناصر عبور نمی‌کند */}
      {isViewportSettingsOpen && (
        <div aria-hidden className="fixed inset-0 z-[15]" onClick={toggleViewportSettings} />
      )}
      {/* قاب تنظیمات نمای نقشه — کنار ستون (دسکتاپ) یا زیر دکمه (موبایل) */}
      {isViewportSettingsOpen && (
        <ViewportSettings placement={isHorizontal ? 'below' : 'side'} />
      )}

      {/* ردیف دکمه‌ها — عمودی در دسکتاپ؛ در موبایل افقی و قابل کشش افقی.
          `justify-between` لبهٔ اولین/آخرین دکمه را به لبهٔ ویزارد
          میرساند (لبه‌های موازی — بازخورد تست موبایل روی آیفون).
          پاپ‌آور بیرونِ این ردیف رندر میشود تا کِشش `overflow-x-auto` آن را
          نَبُرد. */}
      <div
        className={
          isHorizontal
            ? 'flex w-full flex-row items-center justify-between gap-1.5 overflow-x-auto pb-1'
            : 'flex flex-col gap-1.5'
        }
      >
        {/* نمایش/جمع‌کردن پنل — فلش جمع‌شدن وقتی پنل باز است (فقط دسکتاپ؛
            در موبایل پنل شناور وجود ندارد و شیت پایین صفحه جایگزین آن است) */}
        {!isHorizontal && onTogglePanel && (
          <button
            type="button"
            onClick={onTogglePanel}
            aria-label={panelOpen ? t('routing.collapsePanel') : t('routing.openPanel')}
            title={panelOpen ? t('routing.collapsePanel') : t('routing.openPanel')}
            className={btn}
          >
            {panelOpen ? (
              <PanelRightClose size={18} aria-hidden />
            ) : (
              <PanelRightOpen size={18} aria-hidden />
            )}
          </button>
        )}

        {/* ۲بعدی/۳بعدی — گروه هم‌اندازهٔ دکمه‌های تکی نوار ابزار: ظرفِ
            باحاشیه با padding داخلی، دکمه‌های بدون حاشیه، سایهٔ inset برای
            عمق. در ردیف موبایل افقی میشود (دو دکمه کنار هم). */}
        <div
          role="group"
          aria-label={t('map.toggle2d')}
          className={
            isHorizontal
              ? 'flex w-auto shrink-0 flex-row items-center rounded-lg border border-border bg-surface/95 p-1 shadow-[var(--shadow-card),inset_0_1px_2px_rgba(255,255,255,0.06),inset_0_-1px_2px_rgba(0,0,0,0.18)] backdrop-blur-sm'
              : 'flex w-10 flex-col items-center rounded-lg border border-border bg-surface/95 p-1 shadow-[var(--shadow-card),inset_0_1px_2px_rgba(255,255,255,0.06),inset_0_-1px_2px_rgba(0,0,0,0.18)] backdrop-blur-sm'
          }
        >
          <button
            type="button"
            onClick={() => setMapMode('2d')}
            aria-label={t('map.toggle2d')}
            title={t('map.toggle2d')}
            aria-pressed={mode === '2d'}
            className={modeBtn('2d')}
          >
            <MapIcon size={16} aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => setMapMode('3d')}
            aria-label={t('map.toggle3d')}
            title={t('map.toggle3d')}
            aria-pressed={mode === '3d'}
            className={modeBtn('3d')}
          >
            <Mountain size={16} aria-hidden />
          </button>
        </div>

        <div
          className={isHorizontal ? 'w-px shrink-0 self-stretch bg-border' : 'h-px bg-border'}
          aria-hidden
        />

        {/* تنظیمات «نمای نقشه» — بعد از جداکننده */}
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
        <button
          type="button"
          onClick={onZoomOut}
          aria-label="Zoom out"
          title="Zoom out"
          className={btn}
        >
          <Minus size={18} aria-hidden />
        </button>
      </div>
    </div>
  )
}
