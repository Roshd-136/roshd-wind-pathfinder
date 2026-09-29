import { useTranslation } from 'react-i18next'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'

/**
 * صفحه نقشه ۲بعدی — این نسخه فعلاً یک اسکلت است که چیدمان (نقشه + پنل
 * کنترل) را طبق mockup برقرار می‌کند. ادغام واقعی Mapbox GL JS،
 * AlgorithmSelector، WindLayerControls و PathInfoPanel در فاز ۳ تکمیل
 * می‌شود (به docs/frontend/architecture.md مراجعه کنید).
 */
export function Map2DPage() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full">
      <div className="relative flex-1 bg-bg">
        <div className="absolute inset-0 flex items-center justify-center text-text-muted">
          {t('map.selectHint')} — Mapbox GL JS (فاز ۳)
        </div>
      </div>
      <Card className="m-4 w-72 shrink-0">
        <h2 className="mb-3 text-sm font-semibold text-text-primary">{t('routing.algorithm')}</h2>
        <p className="mb-4 text-xs text-text-muted">AlgorithmSelector — فاز ۳</p>
        <h2 className="mb-3 text-sm font-semibold text-text-primary">
          {t('routing.windLayerFilter')}
        </h2>
        <p className="mb-4 text-xs text-text-muted">WindLayerControls — فاز ۳</p>
        <Button className="w-full">{t('routing.calculatePath')}</Button>
      </Card>
    </div>
  )
}
