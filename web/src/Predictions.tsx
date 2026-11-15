import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { CountUp } from './CountUp'
import type { MapMode } from './copy'
import { EnsoTimeline, RainChart, TemperatureChart } from './PredictionCharts'
import { REGIONS, REGION_SHORT, firstTemperature, getAlerts, getPredictions, monthLong, monthOnly, monthShort, num, rainAnalog, signed } from './predictionsData'
import type { Predictions as PredictionsData, RegionId, TelegramAlert } from './predictionsData'
import { useReveal, useScrollToHash } from './useReveal'

const img = (name: string) => `${import.meta.env.BASE_URL}img/${name}`
const stagger = (index: number) => ({ '--i': index }) as CSSProperties
const meter = (percent: number) => ({ '--w': `${Math.max(0, Math.min(100, percent))}%` }) as CSSProperties

const KIND_LABEL: Record<TelegramAlert['kind'], string> = { heat: 'Calor', rain: 'Lluvia', nino: 'El Niño' }
const KIND_ICON: Record<TelegramAlert['kind'], string> = { heat: '🌡️', rain: '🌧️', nino: '⚠️' }
const STATUS_LABEL: Record<TelegramAlert['status'], string> = { preview: 'Vista previa', sent: 'Enviado por Telegram', pending: 'Pendiente: falta que la persona abra el bot', failed: 'No se pudo enviar' }

function RegionTabs({ value, onChange, label }: { value: RegionId; onChange: (region: RegionId) => void; label: string }) {
  return <div className="segmented pred-tabs" role="group" aria-label={label}>
    {REGIONS.map(region => <button key={region} aria-pressed={value === region} onClick={() => onChange(region)}>{REGION_SHORT[region]}</button>)}
  </div>
}

// ------------------------------------------------------------------ Lo más importante

function NinoCard({ data }: { data: PredictionsData }) {
  const { enso } = data
  const analog = enso.analog
  if (enso.status !== 'active' || !enso.start) {
    return <article className="pred-card reveal" style={stagger(0)}>
      <span className="eyebrow">El Niño</span>
      <p className="pred-big">{num(enso.latest.value)}<small> RONI · {monthShort(enso.latest.month)}</small></p>
      <p>Ahora no hay un episodio de El Niño en curso: el RONI está por debajo de 0,5.</p>
    </article>
  }
  const phases = [
    { name: 'Inicio', value: monthLong(enso.start), note: `confirmado: ${enso.months_so_far} meses con RONI ≥ 0,5` },
    ...(analog?.peak_window ? [{ name: 'Pico', value: `${monthShort(analog.peak_window.earliest)} – ${monthShort(analog.peak_window.latest)}`, note: `lo más típico: ${monthLong(analog.peak_window.typical)}` }] : []),
    ...(analog ? [{ name: 'Fin', value: `${monthShort(analog.end_window.earliest)} – ${monthShort(analog.end_window.latest)}`, note: `lo más típico: ${monthLong(analog.end_window.typical)}` }] : []),
  ]
  return <article className="pred-card nino reveal" style={stagger(0)}>
    <span className="eyebrow"><span className="pulse-dot" aria-hidden="true" /> El Niño en curso · rango de fechas</span>
    <p className="pred-big"><CountUp value={enso.latest.value} format={value => num(value)} /><small> RONI en {monthShort(enso.latest.month)} · {enso.category}{enso.rising ? ' y subiendo' : ''}</small></p>
    <ol className="phases">
      {phases.map((phase, index) => <li key={phase.name} style={stagger(index)}>
        <span>{phase.name}</span><strong>{phase.value}</strong><em>{phase.note}</em>
      </li>)}
    </ol>
    {analog && <p className="muted">Pico y fin salen de {analog.n} episodios fuertes anteriores. Es una comparación histórica, no un pronóstico del océano.</p>}
  </article>
}

function TemperatureCard({ data }: { data: PredictionsData }) {
  const national = firstTemperature(data, 'CR')
  if (!national) return null
  const regions = REGIONS.map(region => ({ region, found: firstTemperature(data, region) })).filter(item => item.found)
  return <article className="pred-card heat reveal" style={stagger(1)}>
    <span className="eyebrow">Temperatura · {monthLong(national.row.target_month)}</span>
    <p className="pred-big"><CountUp value={national.anomaly} format={value => `${value < 0 ? '−' : '+'}${num(Math.abs(value))}`} /><small> °C sobre lo normal en todo el país</small></p>
    <div className="meters">
      {regions.map(({ region, found }, index) => <div key={region} className="meter-row" style={stagger(index)}>
        <span>{REGION_SHORT[region]}</span>
        <div className="meter heat"><span style={meter((found!.anomaly / 2) * 100)} /></div>
        <strong>{signed(found!.anomaly)} °C</strong>
      </div>)}
    </div>
    <p className="muted">Pronóstico experimental. Estimación del país: {num(national.estimate)} °C (banda de 90 %: {num(national.low)} a {num(national.high)}), frente a {num(national.normal)} °C normales.</p>
  </article>
}

function RainCard({ data }: { data: PredictionsData }) {
  const month = data.variables.PRECTOTCORR.regions.CR.rows[0]?.target_month
  const national = month ? rainAnalog(data, 'CR', month) : undefined
  if (!month || !national) return null
  return <article className="pred-card rain reveal" style={stagger(2)}>
    <span className="eyebrow">Lluvia · {monthLong(month)}</span>
    <p className="pred-big"><CountUp value={national.anomaly_pct} format={value => `${value < 0 ? '−' : '+'}${num(Math.abs(value), 0)} %`} /><small> en años parecidos de El Niño</small></p>
    <div className="meters">
      {REGIONS.map((region, index) => {
        const found = rainAnalog(data, region, month)
        return found && <div key={region} className="meter-row" style={stagger(index)}>
          <span>{REGION_SHORT[region]}</span>
          <div className="meter rain"><span style={meter(Math.abs(found.anomaly_pct))} /></div>
          <strong>{signed(found.anomaly_pct, 0)} %</strong>
        </div>
      })}
    </div>
    <p className="tag">Sin pronóstico validado de lluvia</p>
    <p className="muted">Es lo que pasó en {national.n_years} años con un Niño como el actual, frente a lo normal. Describe el pasado; no asegura lo que va a llover.</p>
  </article>
}

function Suggestions({ data }: { data: PredictionsData }) {
  const month = data.variables.PRECTOTCORR.regions.CR.rows[0]?.target_month
  const national = month ? rainAnalog(data, 'CR', month) : undefined
  const heat = firstTemperature(data, 'CR')
  const items = [
    ...(data.enso.status === 'active' && national && national.anomaly_pct <= -20 ? [{
      tone: 'agua', title: 'Preparate para menos lluvia', text: `En años parecidos llovió cerca de ${num(Math.abs(national.anomaly_pct), 0)} % menos en ${monthLong(national.month)}. Guardá agua limpia, revisá fugas y confirmá con tu ASADA si habrá racionamientos.` }] : []),
    ...(heat && heat.anomaly >= 0.5 ? [{
      tone: 'calor', title: 'Calor sobre lo normal', text: `Se espera cerca de ${num(heat.anomaly)} °C más que lo normal en ${monthLong(heat.row.target_month)}. Hidratate seguido, evitá el sol de 10 a. m. a 2 p. m. y cuidá a niños y personas mayores.` }] : []),
    { tone: 'info', title: 'Verificá antes de decidir', text: 'Son cifras regionales y experimentales, no avisos oficiales. Para tu zona seguí el boletín ENOS del IMN y los avisos de tu ASADA o del AyA.' },
  ]
  return <div className="pred-tips">
    {items.map((item, index) => <article key={item.title} className={`pred-tip ${item.tone} reveal`} style={stagger(index)}>
      <span className="chip">{item.tone === 'agua' ? 'Agua' : item.tone === 'calor' ? 'Calor' : 'Información'}</span>
      <h3>{item.title}</h3><p>{item.text}</p>
    </article>)}
  </div>
}

// ------------------------------------------------------------------ Detalle

function TemperatureSection({ data }: { data: PredictionsData }) {
  const [region, setRegion] = useState<RegionId>('CR_PN')
  const block = data.variables.T2M
  const rows = block.regions[region].rows
  const validation = data.temperature_validation[`CDS/${region}/T2M`]
  const best = validation ? validation.horizons['1'] : undefined
  return <section className="section" id="temperatura" aria-labelledby="temp-title">
    <div className="section-head reveal">
      <span className="eyebrow">Predicción experimental</span>
      <h2 id="temp-title">Temperatura de los próximos meses</h2>
      <p className="lead">La única variable con pronóstico: promedio mensual de cada sector, con su banda de 90 % de confianza. Solo se publica donde la prueba con datos pasados lo respaldó.</p>
    </div>
    <div className="pred-panel reveal">
      <div className="pred-panel-head"><RegionTabs value={region} onChange={setRegion} label="Sector de la predicción de temperatura" />
        <div className="legend-inline"><span><i className="sw band" />Lo normal (1991–2020, 8 de cada 10 años)</span><span><i className="sw amber" />Estimación y banda de 90 %</span></div></div>
      <TemperatureChart key={region} rows={rows} unit={block.unit} />
    </div>
    <div className="table-wrap reveal"><table className="pred-table">
      <caption>{REGION_SHORT[region]} · temperatura media mensual (°C)</caption>
      <thead><tr><th>Mes</th><th>Estimación</th><th>Banda de 90 %</th><th>Lo normal (P10–P90)</th><th>Diferencia</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.target_month}>
        <th scope="row">{monthLong(row.target_month)}</th>
        <td>{row.estimate === null ? <span className="muted">Sin pronóstico validado</span> : num(row.estimate)}</td>
        <td>{row.estimate === null ? '—' : `${num(row.lower90!)} a ${num(row.upper90!)}`}</td>
        <td>{num(row.reference.mean)} ({num(row.reference.p10)}–{num(row.reference.p90)})</td>
        <td>{row.estimate === null ? '—' : `${signed(Math.round(row.estimate * 10) / 10 - Math.round(row.reference.mean * 10) / 10)} °C`}</td>
      </tr>)}</tbody>
    </table></div>
    {best && <p className="muted note reveal">En la prueba con años pasados, para el mes siguiente este modelo se equivocó {num(best.test_skill * 100, 0)} % menos que simplemente repetir el clima normal, y su banda de 90 % acertó {num(best.coverage90_recent * 100, 0)} % de las veces. Más allá de {validation.max_contiguous_horizon} {validation.max_contiguous_horizon === 1 ? 'mes' : 'meses'} la prueba no justifica publicar un pronóstico.</p>}
  </section>
}

function RainSection({ data }: { data: PredictionsData }) {
  const [region, setRegion] = useState<RegionId>('CR_CAR')
  const rows = data.variables.PRECTOTCORR.regions[region].rows
  const analog = data.rain_analog[region]
  return <section className="section band" id="lluvia" aria-labelledby="rain-title">
    <div className="section-head reveal">
      <span className="eyebrow">Referencia histórica</span>
      <h2 id="rain-title">Lluvia de los próximos meses</h2>
      <p className="lead">Todavía no hay un pronóstico de lluvia que haya pasado la validación. Lo que sí se puede mostrar es cuánto llueve normalmente cada mes y cuánto llovió en los años en que El Niño estaba como ahora.</p>
    </div>
    <div className="pred-panel reveal">
      <div className="pred-panel-head"><RegionTabs value={region} onChange={setRegion} label="Sector de la referencia de lluvia" />
        <div className="legend-inline"><span><i className="sw rain" />Lo normal (8 de cada 10 años)</span><span><i className="sw tickmark" />Promedio normal</span><span><i className="sw diamond" />Años parecidos de El Niño (rojo: llovió más de 5 % menos)</span></div></div>
      <RainChart key={region} rows={rows} analog={analog?.months ?? []} />
    </div>
    <div className="table-wrap reveal"><table className="pred-table">
      <caption>{REGION_SHORT[region]} · lluvia mensual (mm)</caption>
      <thead><tr><th>Mes</th><th>Lo normal (P10–P90)</th><th>En años parecidos de El Niño</th><th>Años con 100 mm o más</th></tr></thead>
      <tbody>{rows.map(row => {
        const found = analog?.months.find(item => item.month === row.target_month)
        return <tr key={row.target_month}>
          <th scope="row">{monthLong(row.target_month)}</th>
          <td>{num(row.reference.mean, 0)} ({num(row.reference.p10, 0)}–{num(row.reference.p90, 0)})</td>
          <td>{found ? `${num(found.mean_mm, 0)} mm (${signed(found.anomaly_pct, 0)} %)` : '—'}</td>
          <td>{found ? `${Math.round(found.share_above_100mm * found.n_years)} de ${found.n_years}` : '—'}</td>
        </tr>
      })}</tbody>
    </table></div>
    {analog && <p className="muted note reveal">Años parecidos: {analog.criterion.charAt(0).toLowerCase() + analog.criterion.slice(1)} ({analog.years.join(', ')}). Son pocos años y no hay una prueba de significancia: sirve como contexto, no como promesa de lluvia.</p>}
  </section>
}

function MoreData({ data }: { data: PredictionsData }) {
  const analog = data.enso.analog
  const reference = (variable: 'RH2M' | 'UV') => data.variables[variable]
  return <section className="section" id="mas-datos" aria-labelledby="more-title">
    <div className="section-head reveal">
      <span className="eyebrow">Datos secundarios</span>
      <h2 id="more-title">Más datos para quien quiere profundizar</h2>
      <p className="lead">Referencias de humedad y radiación UV, qué tan confiable es la temperatura y los episodios de El Niño que sirvieron de comparación.</p>
    </div>
    <div className="more-grid">
      {(['RH2M', 'UV'] as const).map((variable, index) => {
        const block = reference(variable)
        return <article key={variable} className="card more-card reveal" style={stagger(index)}>
          <h3>{variable === 'RH2M' ? 'Humedad relativa del aire' : 'Radiación UV (NASA POWER)'}</h3>
          <p className="muted">{variable === 'RH2M' ? 'Referencia 1991–2020 (%)' : 'Índice UV medio de 24 horas, 2001–2024. Incluye la noche: no es el índice del mediodía.'} Sin pronóstico validado.</p>
          <div className="table-wrap"><table className="pred-table compact">
            <thead><tr><th>Mes</th>{REGIONS.map(region => <th key={region}>{REGION_SHORT[region]}</th>)}</tr></thead>
            <tbody>{block.regions.CR.rows.map((row, i) => <tr key={row.target_month}>
              <th scope="row">{monthOnly(row.target_month)} {row.target_month.slice(2, 4)}</th>
              {REGIONS.map(region => { const ref = block.regions[region].rows[i].reference; return <td key={region}>{num(ref.mean, variable === 'UV' ? 2 : 1)}</td> })}
            </tr>)}</tbody>
          </table></div>
        </article>
      })}
      <article className="card more-card reveal" style={stagger(2)}>
        <h3>Qué tan confiable es la temperatura</h3>
        <p className="muted">Mejora frente a repetir el clima normal, en la prueba con años pasados (cuanto más a la derecha, mejor).</p>
        <div className="meters">
          {REGIONS.flatMap(region => Object.entries(data.temperature_validation[`CDS/${region}/T2M`]?.horizons ?? {}).map(([horizon, info]) => ({ region, horizon, info })))
            .map(({ region, horizon, info }, index) => <div key={`${region}${horizon}`} className="meter-row" style={stagger(index)}>
              <span>{REGION_SHORT[region]} · mes {horizon}</span>
              <div className="meter good"><span style={meter(info.test_skill * 100)} /></div>
              <strong>{num(info.test_skill * 100, 0)} %</strong>
            </div>)}
        </div>
      </article>
      {analog && <article className="card more-card reveal" style={stagger(3)}>
        <h3>Episodios fuertes que sirvieron de comparación</h3>
        <p className="muted">Cuánto duraron los {analog.n} episodios de El Niño con RONI máximo de 1,5 o más (en meses).</p>
        <div className="meters">
          {analog.events.map((event, index) => <div key={event.start} className="meter-row" style={stagger(index)}>
            <span>{event.start.slice(0, 4)} – {event.end.slice(0, 4)}</span>
            <div className="meter nino"><span style={meter((event.months / 20) * 100)} /></div>
            <strong>{event.months}</strong>
          </div>)}
        </div>
      </article>}
    </div>
  </section>
}

function TelegramSection({ alerts, failed }: { alerts?: TelegramAlert[]; failed: boolean }) {
  return <section className="section band" id="alertas" aria-labelledby="tg-title">
    <div className="section-head reveal">
      <span className="eyebrow">Avisos de prueba</span>
      <h2 id="tg-title">Alertas por Telegram</h2>
      <p className="lead">Con estas predicciones se arman avisos cortos para personas de prueba según su zona: uno de calor, uno de probabilidad de lluvia y uno de zona afectada por El Niño.</p>
    </div>
    {failed && <p className="empty">Los avisos de prueba todavía no se generaron. Se crean con <code>python -m src.telegram_alerts preview</code>.</p>}
    {!alerts && !failed && <p className="empty">Cargando los avisos…</p>}
    <div className="bubbles">
      {alerts?.map((alert, index) => <article key={alert.kind} className="bubble-card reveal" style={stagger(index)}>
        <header><span aria-hidden="true">{KIND_ICON[alert.kind]}</span><strong>{KIND_LABEL[alert.kind]}</strong><span className={`chip status ${alert.status}`}>{STATUS_LABEL[alert.status]}</span></header>
        <p className="bubble-place">📍 {alert.canton === alert.province ? alert.canton : `${alert.canton}, ${alert.province}`} · {alert.zone}</p>
        <div className="bubble" role="note" aria-label={`Texto del aviso de ${KIND_LABEL[alert.kind]}`}>{alert.text}</div>
      </article>)}
    </div>
    <p className="muted note reveal">Un bot de Telegram solo puede escribirle a quien primero lo abrió y le envió /start. Son avisos de prueba para tres cuentas y no reemplazan los avisos oficiales.</p>
  </section>
}

// ------------------------------------------------------------------ Página

function Body({ data, alerts, alertsFailed, openMap }: { data: PredictionsData; alerts?: TelegramAlert[]; alertsFailed: boolean; openMap: (mode: MapMode) => void }) {
  useReveal([alerts])
  useScrollToHash()
  return <>
    <header className="hero pred-hero" id="inicio">
      <img className="hero-img" src={img('nino.jpg')} alt="Quebrada con pozas y rocas cubiertas de musgo dentro de un bosque verde en Guanacaste" fetchPriority="high" />
      <div className="hero-veil" aria-hidden="true" />
      <div className="hero-inner">
        <span className="hero-eyebrow pred-rise" style={stagger(0)}>Predicciones · experimentales</span>
        <h1 className="pred-rise" style={stagger(1)}>Lo que viene para el clima de Costa Rica</h1>
        <p className="pred-rise" style={stagger(2)}>Cuándo podría durar El Niño, cuánto más caliente será y qué se sabe de la lluvia, con sus límites a la vista.</p>
        <div className="hero-actions pred-rise" style={stagger(3)}>
          <a className="pill pill-primary hero-cta" href="#resumen">Ver lo más importante</a>
          <button className="pill hero-cta" onClick={() => openMap('grid')}>Abrir el mapa</button>
        </div>
        <p className="hero-meta pred-rise" style={stagger(4)}>Datos hasta {monthLong(data.data_through)} · RONI hasta {monthLong(data.roni_through)} · calibración del {new Date(`${data.calibration_date}T00:00:00`).toLocaleDateString('es-CR', { dateStyle: 'long' })}</p>
      </div>
    </header>

    <main>
      <section className="section pred-first" id="resumen" aria-labelledby="top-title">
        <div className="section-head reveal">
          <span className="eyebrow">Lo más importante</span>
          <h2 id="top-title">Resumen de las predicciones</h2>
        </div>
        <div className="pred-top"><NinoCard data={data} /><TemperatureCard data={data} /><RainCard data={data} /></div>
        <Suggestions data={data} />
      </section>

      <section className="section" id="fechas" aria-labelledby="dates-title">
        <div className="section-head reveal">
          <span className="eyebrow">Rango de fechas</span>
          <h2 id="dates-title">El Niño en el calendario</h2>
          <p className="lead">El RONI ya superó el umbral de 0,5 desde {data.enso.start ? monthLong(data.enso.start) : 'antes'}. Los rangos de pico y de fin comparan con los episodios fuertes anteriores: marcan lo que suele pasar, no una fecha segura.</p>
        </div>
        <div className="pred-panel reveal"><EnsoTimeline enso={data.enso} /></div>
        <p className="muted note reveal">{data.enso.definition} Los datos del RONI llegan hasta {monthLong(data.roni_through)}; la línea no se proyecta hacia adelante.</p>
      </section>

      <TemperatureSection data={data} />
      <RainSection data={data} />
      <MoreData data={data} />
      <TelegramSection alerts={alerts} failed={alertsFailed} />

      <section className="section" aria-labelledby="limits-title">
        <div className="section-head reveal"><span className="eyebrow">Para leer con cuidado</span><h2 id="limits-title">Límites de estas predicciones</h2></div>
        <ul className="facts reveal">{data.limits.map(limit => <li key={limit}>{limit}</li>)}</ul>
      </section>
    </main>

    <footer className="landing-footer">
      <p><strong>El Niño en CR — Predicciones experimentales.</strong> Calculadas con el motor de predicciones de Hefesto sobre series regionales de Copernicus (ERA5-Land), NASA POWER y el RONI de NOAA. No reemplazan los avisos del IMN, el AyA ni de tu ASADA.</p>
    </footer>
  </>
}

export function Predictions({ openMap, goHome }: { openMap: (mode: MapMode) => void; goHome: () => void }) {
  const [data, setData] = useState<PredictionsData>()
  const [failed, setFailed] = useState(false)
  const [alerts, setAlerts] = useState<TelegramAlert[]>()
  const [alertsFailed, setAlertsFailed] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    getPredictions(controller.signal).then(value => { if (!controller.signal.aborted) setData(value) })
      .catch(() => { if (!controller.signal.aborted) setFailed(true) })
    getAlerts(controller.signal).then(value => { if (!controller.signal.aborted) setAlerts(value.alerts) })
      .catch(() => { if (!controller.signal.aborted) setAlertsFailed(true) })
    return () => controller.abort()
  }, [])

  return <div className="landing pred">
    <nav className="landing-nav glass" aria-label="Navegación principal">
      <a className="brand" href="." onClick={event => { event.preventDefault(); goHome() }}>El Niño en CR</a>
      <div className="nav-links">
        <a href="#resumen">Resumen</a><a href="#temperatura">Temperatura</a><a href="#lluvia">Lluvia</a><a href="#mas-datos">Más datos</a><a href="#alertas">Alertas</a>
      </div>
      <div className="segmented" role="group" aria-label="Mapas y predicciones">
        <button onClick={() => openMap('grid')}>NASA POWER</button>
        <button onClick={() => openMap('cds')}>CDS</button>
        <button onClick={() => openMap('cantones')}>Nacionales</button>
        <button aria-pressed="true" aria-current="page">Predicciones</button>
      </div>
    </nav>
    {data ? <Body data={data} alerts={alerts} alertsFailed={alertsFailed} openMap={openMap} />
      : <header className="hero pred-hero loading">
        <div className="hero-veil" aria-hidden="true" />
        <div className="hero-inner"><h1>{failed ? 'No se pudieron cargar las predicciones' : 'Calculando…'}</h1>
          <p>{failed ? 'Generalas con «python -m src.predictions» y recargá la página.' : 'Cargando las predicciones.'}</p></div>
      </header>}
  </div>
}
