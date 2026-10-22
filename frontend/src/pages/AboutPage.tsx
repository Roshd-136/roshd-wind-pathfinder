import { useTranslation } from 'react-i18next'

/**
 * صفحهٔ درباره — شبیه راهنمای محصول: سرآیندِ وسط‌چینِ بزرگ، سکشن‌های شماره‌دار
 * با خط جداکننده، تصاویرِ شماره‌دار با شرح، و متن‌محورِ بدون تزئین. اسکرول در
 * همین صفحه انجام میشود — `main` اپ برای نقشهها `overflow-hidden` دارد.
 */
export function AboutPage() {
  const { t } = useTranslation()

  const figures = [
    { src: '/img/about/route-2d.png', titleKey: 'about.fig1Title', captionKey: 'about.fig1Caption' },
    { src: '/img/about/scene-3d.png', titleKey: 'about.fig2Title', captionKey: 'about.fig2Caption' },
    { src: '/img/about/fight-3d.png', titleKey: 'about.fig3Title', captionKey: 'about.fig3Caption' },
  ]
  const steps = ['about.how1', 'about.how2', 'about.how3', 'about.how4', 'about.how5']
  const paragraphs = ['about.what1', 'about.what2', 'about.what3']
  const sections = [
    { titleKey: 'about.whatTitle', body: paragraphs as string[] },
    { titleKey: 'about.howTitle', body: steps as string[] },
  ]

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-6 pb-20 pt-14">
        {/* سرآیند — وسط‌چین و بزرگ */}
        <header className="mx-auto max-w-2xl space-y-5 text-center">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-text-muted">
            {t('about.kicker')}
          </div>
          <h1 className="text-4xl font-bold leading-[1.25] text-text-primary md:text-5xl">
            {t('about.title')}
          </h1>
          <p className="text-base leading-8 text-text-secondary md:text-lg md:leading-9">
            {t('about.lead')}
          </p>
        </header>

        <div className="mt-14 space-y-14">
          {sections.map(({ titleKey, body }) => (
            <section key={titleKey}>
              <h2 className="border-b border-border pb-4 text-2xl font-semibold text-text-primary">
                {t(titleKey)}
              </h2>
              <div className="mt-6 space-y-5 text-base leading-8 text-text-secondary">
                {body.map((key) => (
                  <p key={key}>{t(key)}</p>
                ))}
              </div>
            </section>
          ))}

          {/* نماهای محصول — تصاویر شماره‌دار */}
          <section>
            <h2 className="border-b border-border pb-4 text-2xl font-semibold text-text-primary">
              {t('about.figuresTitle')}
            </h2>
            <div className="mt-6 space-y-8">
              {figures.map((fig) => (
                <figure
                  key={fig.src}
                  className="overflow-hidden rounded-xl border border-border bg-surface-raised"
                >
                  <img src={fig.src} alt={t(fig.captionKey)} className="block w-full" loading="lazy" />
                  <figcaption className="space-y-2 px-4 py-4">
                    <div className="text-base font-semibold text-text-primary">{t(fig.titleKey)}</div>
                    <p className="text-sm leading-7 text-text-secondary">{t(fig.captionKey)}</p>
                  </figcaption>
                </figure>
              ))}
            </div>
          </section>

          {/* فناوری‌ها — پایانی */}
          <section>
            <h2 className="border-b border-border pb-4 text-2xl font-semibold text-text-primary">
              {t('about.stackTitle')}
            </h2>
            <p className="mt-6 text-base leading-8 text-text-secondary">{t('about.stackText')}</p>
          </section>

          {/* دادهٔ مبنایی */}
          <section>
            <h2 className="border-b border-border pb-4 text-2xl font-semibold text-text-primary">
              {t('about.dataTitle')}
            </h2>
            <p className="mt-6 text-base leading-8 text-text-secondary">{t('about.dataText')}</p>
          </section>
        </div>
      </div>
    </div>
  )
}
