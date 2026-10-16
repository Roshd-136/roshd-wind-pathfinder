import { useTranslation } from 'react-i18next'
import type { DisplayLang } from '../utils/format'

/**
 * زبان نمایش برای فرمت اعداد — «fa» برای هر زبانی که با fa شروع می‌شود،
 * بقیه «en». فرمت فارسی: «۸۰٫۵ ک.م» و «۱س۲۰د»؛ لاتین همان km/h خودش.
 */
export function useFormatLang(): DisplayLang {
  const { i18n } = useTranslation()
  return i18n.language?.startsWith('fa') ? 'fa' : 'en'
}
