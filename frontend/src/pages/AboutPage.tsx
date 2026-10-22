import { useTranslation } from 'react-i18next'
import { Card } from '../components/ui/Card'

/** صفحهٔ درباره — معرفی محصول، تصاویرِ دو نما و فرایند؛ متن‌محور و بدون تزئین. */
export function AboutPage() {
  const { t } = useTranslation()

  const figures = [
    { src: '/img/about/route-2d.png', titleKey: 'about.fig1Title', captionKey: 'about.fig1Caption' },
    { src: '/img/about/scene-3d.png', titleKey: 'about.fig2Title', captionKey: 'about.fig2Caption' },
    { src: '/img/about/fight-3d.png', titleKey: 'about.fig3Title', captionKey: 'about.fig3Caption' },
  ]
  const steps = ['about.how1', 'about.how2', 'about.how3', 'about.how4', 'about.how5']
  const paragraphs = ['about.what1', 'about.what2', 'about.what3']

  return (
    <div className="mx-auto max-w-3xl space-y-10 p-6">
      <header className="space-y-3">
        <h1 className="text-xl font-semibold text-text-primary">{t('about.title')}</h1>
        <p className="text-sm leading-7 text-text-secondary">{t('about.lead')}</p>
      </header>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-text-primary">{t('about.whatTitle')}</h2>
        {paragraphs.map((key) => (
          <p key={key} className="text-sm leading-7 text-text-secondary">
            {t(key)}
          </p>
        ))}
      </section>

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-text-primary">{t('about.howTitle')}</h2>
        <ol className="list-decimal space-y-2 ps-6 text-sm leading-7 text-text-secondary">
          {steps.map((key) => (
            <li key={key}>{t(key)}</li>
          ))}
        </ol>
      </section>

      <section className="space-y-4">
        {figures.map((fig) => (
          <figure
            key={fig.src}
            className="overflow-hidden rounded-xl border border-border bg-surface-raised"
          >
            <img src={fig.src} alt={t(fig.captionKey)} className="block w-full" loading="lazy" />
            <figcaption className="space-y-1 p-3">
              <div className="text-sm font-medium text-text-primary">{t(fig.titleKey)}</div>
              <p className="text-xs leading-6 text-text-secondary">{t(fig.captionKey)}</p>
            </figcaption>
          </figure>
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-text-primary">{t('about.stackTitle')}</h2>
        <Card className="p-4">
          <p className="text-sm leading-7 text-text-secondary">{t('about.stackText')}</p>
        </Card>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-text-primary">{t('about.dataTitle')}</h2>
        <p className="text-sm leading-7 text-text-secondary">{t('about.dataText')}</p>
      </section>
    </div>
  )
}
