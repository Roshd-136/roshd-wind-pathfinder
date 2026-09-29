import { useTranslation } from 'react-i18next'
import { Checkbox } from '../../ui/Checkbox'
import { WindSpeedLegend } from './WindSpeedLegend'

export interface LayerVisibility {
  surface: boolean
  mid: boolean
  high: boolean
}

interface WindLayerControlsProps {
  value: LayerVisibility
  onChange: (value: LayerVisibility) => void
}

/**
 * فیلتر لایه باد — سه چک‌باکس (سطحی ۰-۵۰، میانی ۵۰-۲۰۰، بالا ۲۰۰-۵۰۰ متر)
 * + legend سرعت باد، دقیقاً مطابق پنل کنترل mockup.
 */
export function WindLayerControls({ value, onChange }: WindLayerControlsProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-text-primary">{t('routing.windLayerFilter')}</h3>
      <div className="space-y-2">
        <Checkbox
          label={t('routing.layerSurface')}
          checked={value.surface}
          onChange={(e) => onChange({ ...value, surface: e.target.checked })}
        />
        <Checkbox
          label={t('routing.layerMid')}
          checked={value.mid}
          onChange={(e) => onChange({ ...value, mid: e.target.checked })}
        />
        <Checkbox
          label={t('routing.layerHigh')}
          checked={value.high}
          onChange={(e) => onChange({ ...value, high: e.target.checked })}
        />
      </div>
      <WindSpeedLegend />
    </div>
  )
}
