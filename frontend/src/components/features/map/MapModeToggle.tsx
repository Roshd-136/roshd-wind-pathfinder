import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router-dom'

/**
 * سوییچ ۲بعدی/۳بعدی — پیل بالای نقشه، دقیقاً مطابق mockup. چون
 * Map2DPage/Map3DPage دو route جدا هستند (طبق ساختار پروژه mockup)، این
 * ناوبری واقعی است، نه صرفاً تغییر state محلی؛ انتخاب مبدأ/مقصد/مسیر از
 * طریق useRouteStore هنگام جابه‌جایی حفظ می‌شود.
 */
export function MapModeToggle() {
  const { t } = useTranslation()
  const base = 'rounded-md px-3 py-1 text-xs font-medium transition-colors'
  const active = 'bg-accent text-white'
  const inactive = 'text-text-secondary hover:text-text-primary'

  return (
    <div className="absolute start-4 top-4 z-10 flex gap-1 rounded-lg border border-border bg-surface p-1">
      <NavLink to="/" end className={({ isActive }) => `${base} ${isActive ? active : inactive}`}>
        {t('map.toggle2d')}
      </NavLink>
      <NavLink
        to="/map-3d"
        className={({ isActive }) => `${base} ${isActive ? active : inactive}`}
      >
        {t('map.toggle3d')}
      </NavLink>
    </div>
  )
}
