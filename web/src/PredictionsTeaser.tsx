import { CountUp } from './CountUp'
import { firstTemperature, monthLong, monthShort, num, rainAnalog, signed } from './predictionsData'
import type { Predictions } from './predictionsData'

/** Sección de la página de inicio: lo esencial de las predicciones y un enlace a la página completa. */
export function PredictionsTeaser({ data, openPredictions }: { data?: Predictions; openPredictions: () => void }) {
  const enso = data?.enso
  const analog = enso?.analog
  const heat = data && firstTemperature(data, 'CR')
  const month = data?.variables.PRECTOTCORR.regions.CR.rows[0]?.target_month
  const rain = data && month ? rainAnalog(data, 'CR', month) : undefined

  return <section className="section" id="predicciones" aria-labelledby="pred-title">
    <div className="section-head reveal">
      <span className="eyebrow">Lo que viene</span>
      <h2 id="pred-title">Predicciones</h2>
      <p className="lead">Cuánto podría durar El Niño, cuánto más caliente se espera y qué se sabe de la lluvia, con sus límites a la vista. Son estimaciones regionales y experimentales.</p>
    </div>
    {!data && <p className="empty">Cargando las predicciones…</p>}
    {data && <div className="pred-top teaser">
      {enso?.status === 'active' && enso.start && <article className="pred-card nino reveal" style={{ '--i': 0 } as React.CSSProperties}>
        <span className="eyebrow"><span className="pulse-dot" aria-hidden="true" /> El Niño en curso</span>
        <p className="pred-big">{monthLong(enso.start)}<small>{analog ? `empezó el episodio. Fin esperado entre ${monthShort(analog.end_window.earliest)} y ${monthShort(analog.end_window.latest)} (lo más típico: ${monthLong(analog.end_window.typical)})` : `RONI de ${num(enso.latest.value)}`}</small></p>
      </article>}
      {heat && <article className="pred-card heat reveal" style={{ '--i': 1 } as React.CSSProperties}>
        <span className="eyebrow">Temperatura · {monthLong(heat.row.target_month)}</span>
        <p className="pred-big"><CountUp value={heat.anomaly} format={value => `${signed(value)}`} /><small>°C sobre lo normal en todo el país (pronóstico experimental)</small></p>
      </article>}
      {rain && <article className="pred-card rain reveal" style={{ '--i': 2 } as React.CSSProperties}>
        <span className="eyebrow">Lluvia · {monthLong(rain.month)}</span>
        <p className="pred-big"><CountUp value={rain.anomaly_pct} format={value => `${signed(value, 0)} %`} /><small>frente a lo normal en {rain.n_years} años parecidos de El Niño. No es un pronóstico validado</small></p>
      </article>}
    </div>}
    <div className="teaser-cta reveal">
      <a className="pill pill-primary hero-cta" href="?pagina=predicciones" onClick={event => { event.preventDefault(); openPredictions() }}>Ver todas las predicciones <span aria-hidden="true">→</span></a>
    </div>
  </section>
}
