import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useSettingsStore } from '../store/useSettingsStore'

const RTL_LANGUAGES = new Set(['fa'])

/**
 * زبان انتخاب‌شده در ترجیحات کاربر را با i18next و جهت سند (`dir`) هماهنگ
 * نگه می‌دارد. باید یک‌بار در ریشه اپ (`App.tsx`) فراخوانی شود.
 */
export function useLanguageDirection() {
  const { i18n } = useTranslation()
  const language = useSettingsStore((s) => s.language)

  useEffect(() => {
    void i18n.changeLanguage(language)
    document.documentElement.lang = language
    document.documentElement.dir = RTL_LANGUAGES.has(language) ? 'rtl' : 'ltr'
  }, [language, i18n])
}
