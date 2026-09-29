import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import fa from './locales/fa.json'

/**
 * راه‌اندازی i18next با فارسی (پیش‌فرض، RTL) و انگلیسی.
 * تغییر زبان باید `document.documentElement.dir` را هم به‌روز کند —
 * این کار در هوک `useLanguageDirection` (src/hooks) انجام می‌شود.
 */
void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      fa: { translation: fa },
      en: { translation: en },
    },
    fallbackLng: 'fa',
    interpolation: { escapeValue: false },
  })

export default i18n
