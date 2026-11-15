import { CountUp } from './CountUp'
import { firstTemperature, monthLong, monthShort, num, rainAnalog, signed } from './predictionsData'
import type { Predictions } from './predictionsData'
import { t } from './i18n'

/** Sección de la página de inicio: lo esencial de las predicciones y un enlace a la página completa. */
export function PredictionsTeaser({ data, openPredictions }: { data?: Predictions; openPredictions: () => void }) {
  const enso = data?.enso
  const analog = enso?.analog
  const heat = data && firstTemperature(data, 'CR')
  const month = data?.variables.PRECTOTCORR.regions.CR.rows[0]?.target_month
  const rain = data && month ? rainAnalog(data, 'CR', month) : undefined

  return <section className="section" id="predicciones" aria-labelledby="pred-title">
    <div className="section-head reveal">
      <span className="eyebrow">{t('Lo que viene', 'What is coming')}</span>
      <h2 id="pred-title">{t('Predicciones', 'Predictions')}</h2>
      <p className="lead">{t('Cuánto podría durar El Niño, cuánto más caliente se espera y qué se sabe de la lluvia, con sus límites a la vista. Son estimaciones regionales y experimentales.', 'How long El Niño could last, how much warmer it is expected to be and what is known about the rain, with its limits in plain sight. These are regional, experimental estimates.')}</p>
    </div>
    {!data && <p className="empty">{t('Cargando las predicciones…', 'Loading the predictions…')}</p>}
    {data && <div className="pred-top teaser">
      {enso?.status === 'active' && enso.start && <article className="pred-card nino reveal" style={{ '--i': 0 } as React.CSSProperties}>
        <span className="eyebrow"><span className="pulse-dot" aria-hidden="true" /> {t('El Niño en curso', 'El Niño under way')}</span>
        <p className="pred-big">{monthLong(enso.start)}<small>{analog ? t(`empezó el episodio. Fin esperado entre ${monthShort(analog.end_window.earliest)} y ${monthShort(analog.end_window.latest)} (lo más típico: ${monthLong(analog.end_window.typical)})`, `the episode began. Expected end between ${monthShort(analog.end_window.earliest)} and ${monthShort(analog.end_window.latest)} (most typical: ${monthLong(analog.end_window.typical)})`) : `RONI ${t('de', 'of')} ${num(enso.latest.value)}`}</small></p>
      </article>}
      {heat && <article className="pred-card heat reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <span className="eyebrow">{t('Temperatura', 'Temperature')} · {monthLong(heat.row.target_month)}</span>
        <p className="pred-big"><CountUp value={heat.anomaly} format={value => `${signed(value)}`} /><small>{t('°C sobre lo normal en todo el país (pronóstico experimental)', '°C above normal across the country (experimental forecast)')}</small></p>
      </article>}
      {rain && <article className="pred-card rain reveal" style={{ '--i': 2 } as React.CSSProperties}>
        <span className="eyebrow">{t('Lluvia', 'Rain')} · {monthLong(rain.month)}</span>
        <p className="pred-big"><CountUp value={rain.anomaly_pct} format={value => `${signed(value, 0)} %`} /><small>{t(`frente a lo normal en ${rain.n_years} años parecidos de El Niño. No es un pronóstico validado`, `compared with normal in ${rain.n_years} similar El Niño years. It is not a validated forecast`)}</small></p>
      </article>}
    </div>}
    <div className="teaser-cta reveal">
      <a className="pill pill-primary hero-cta" href="?pagina=predicciones" onClick={event => { event.preventDefault(); openPredictions() }}>{t('Ver todas las predicciones', 'See all the predictions')} <span aria-hidden="true">→</span></a>
    </div>
  </section>
}
