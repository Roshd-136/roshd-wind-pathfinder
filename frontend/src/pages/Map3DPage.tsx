import { useTranslation } from 'react-i18next'

/** نمای سه‌بعدی — ادغام Mapbox GL JS در حالت 3D در فاز ۳. */
export function Map3DPage() {
  const { t } = useTranslation()
  return (
    <div className="flex h-full items-center justify-center text-text-muted">
      {t('map.toggle3d')} — Mapbox GL JS 3D (فاز ۳)
    </div>
  )
}
