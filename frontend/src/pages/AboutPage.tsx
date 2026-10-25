import { useTranslation } from 'react-i18next'

export function AboutPage() {
  const { t } = useTranslation()
  return (
    <div className="p-6 text-text-secondary">{t('about.text')}</div>
  )
}
