import { useTranslation } from 'react-i18next'

/**
 * صفحهٔ درباره — شبیه راهنمای محصول: سرآیندِ وسط‌چینِ بزرگ، سکشن‌های شماره‌دار،
 * تصاویر «در جای لازم» متن (کراپِ پنل با عدسیِ بزرگ‌نمایی، جفتِ نمای ۲بعدی/۳بعدی
 * کنار هم و تصویرِ عریضِ گذر رنگ). اسکرول در همین صفحه انجام میشود — `main`
 * اپ برای نقشهها `overflow-hidden` دارد.
 */
export function AboutPage() {
  const { t } = useTranslation()

  const steps = ['about.how1', 'about.how2', 'about.how3', 'about.how4', 'about.how5']
  const paragraphs = ['about.what1', 'about.what2', 'about.what3']

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
          <section>
            <h2 className="border-b border-border pb-4 text-2xl font-semibold text-text-primary">
              {t('about.whatTitle')}
            </h2>
            <div className="mt-6 space-y-5 text-base leading-8 text-text-secondary">
              {paragraphs.map((key) => (
                <p key={key}>{t(key)}</p>
              ))}
            </div>
            {/* تصویر ۱ — کراپِ پنل تنظیمات با عدسی روی طیف‌نما + متنِ کناری */}
            <figure className="mt-8 flex flex-col gap-6 md:flex-row md:items-start">
              <div className="relative w-64 shrink-0">
                <div className="overflow-hidden rounded-xl border border-border bg-surface-raised">
                  <img
                    src="/img/about/panel-detail.png"
                    alt={t('about.fig1Caption')}
                    className="block w-full"
                    loading="lazy"
                  />
                </div>
                {/* عدسی — بزرگ‌نمایی ×۳ طیف‌نمای مقاومت */}
                <div className="absolute -bottom-9 -end-4 h-40 w-40 overflow-hidden rounded-full border border-border bg-surface-raised shadow-[var(--shadow-card)] ring-4 ring-surface">
                  <img
                    src="/img/about/panel-legend-zoom.png"
                    alt=""
                    className="h-full w-full object-cover object-left"
                    loading="lazy"
                  />
                </div>
              </div>
              <div className="min-w-0 flex-1 space-y-4 pt-2">
                <div className="text-base font-semibold text-text-primary">{t('about.fig1Title')}</div>
                <p className="text-sm leading-7 text-text-secondary">{t('about.fig1Caption')}</p>
                <div className="rounded-xl border border-border bg-surface-raised px-4 py-3 text-sm leading-7 text-text-secondary">
                  {t('about.fig1Magnifier')}
                </div>
              </div>
            </figure>
          </section>

          <section>
            <h2 className="border-b border-border pb-4 text-2xl font-semibold text-text-primary">
              {t('about.howTitle')}
            </h2>
            <div className="mt-6 space-y-2 text-base leading-8 text-text-secondary">
              {steps.map((key) => (
                <p key={key}>{t(key)}</p>
              ))}
            </div>
          </section>

          {/* نماهای محصول — جفت کنار هم، سپس تصویر عریضِ گذر رنگ */}
          <section>
            <h2 className="border-b border-border pb-4 text-2xl font-semibold text-text-primary">
              {t('about.figuresTitle')}
            </h2>
            <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
              <figure className="overflow-hidden rounded-xl border border-border bg-surface-raised">
                <img
                  src="/img/about/route-2d.png"
                  alt={t('about.fig2Caption')}
                  className="block h-52 w-full object-cover object-bottom"
                  loading="lazy"
                />
                <figcaption className="space-y-2 px-4 py-4">
                  <div className="text-base font-semibold text-text-primary">{t('about.fig2Title')}</div>
                  <p className="text-sm leading-7 text-text-secondary">{t('about.fig2Caption')}</p>
                </figcaption>
              </figure>
              <figure className="overflow-hidden rounded-xl border border-border bg-surface-raised">
                <img
                  src="/img/about/scene-3d.png"
                  alt={t('about.fig3Caption')}
                  className="block h-52 w-full object-cover object-bottom"
                  loading="lazy"
                />
                <figcaption className="space-y-2 px-4 py-4">
                  <div className="text-base font-semibold text-text-primary">{t('about.fig3Title')}</div>
                  <p className="text-sm leading-7 text-text-secondary">{t('about.fig3Caption')}</p>
                </figcaption>
              </figure>
            </div>
            <figure className="mt-8 overflow-hidden rounded-xl border border-border bg-surface-raised">
              <img
                src="/img/about/fight-3d.png"
                alt={t('about.fig4Caption')}
                className="block w-full"
                loading="lazy"
              />
              <figcaption className="space-y-2 px-4 py-4">
                <div className="text-base font-semibold text-text-primary">{t('about.fig4Title')}</div>
                <p className="text-sm leading-7 text-text-secondary">{t('about.fig4Caption')}</p>
              </figcaption>
            </figure>
          </section>

          <section>
            <h2 className="border-b border-border pb-4 text-2xl font-semibold text-text-primary">
              {t('about.stackTitle')}
            </h2>
            <p className="mt-6 text-base leading-8 text-text-secondary">{t('about.stackText')}</p>
          </section>

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
