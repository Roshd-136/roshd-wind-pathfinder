import { useTranslation } from 'react-i18next'
import type { WindPointSample } from '../../../types/routing'
import { formatAltitudeM, formatSpeedMps } from '../../../utils/format'
import { useFormatLang } from '../../../hooks/useFormatLang'
import { Card } from '../../ui/Card'

interface PointInfoPopupProps {
  samples: WindPointSample[]
  onClose: () => void
}

/**
 * پاپ‌آپ «Wind Layers» — لیست سرعت باد در همه لایه‌های ارتفاعی برای نقطه
 * کلیک‌شده، دقیقاً مطابق کارت "Point Info" در قدم ۴ mockup.
 */
export function PointInfoPopup({ samples, onClose }: PointInfoPopupProps) {
  const { t } = useTranslation()
  const lang = useFormatLang()

  return (
    <Card className="absolute end-4 top-4 w-56 text-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-semibold text-text-primary">{t('windLayers.pointInfo')}</h3>
        <button
          onClick={onClose}
          aria-label="close"
          className="text-text-muted hover:text-text-primary"
        >
          ✕
        </button>
      </div>
      <h4 className="mb-1 text-xs text-text-muted">{t('windLayers.title')}</h4>
      <ul className="space-y-1">
        {samples.map((s) => (
          <li key={s.altitude_m} className="flex items-center justify-between text-text-secondary">
            <span>{formatAltitudeM(s.altitude_m, lang)}</span>
            <span className="text-text-primary">{formatSpeedMps(s.speed_mps, lang)}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}
