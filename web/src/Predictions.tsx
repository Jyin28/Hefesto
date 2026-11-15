import { useEffect, useMemo, useState } from 'react'
import { CountUp } from './CountUp'
import type { MapMode } from './copy'
import { getAsadas } from './data'
import type { Canton, Operator } from './data'
import { t } from './i18n'
import { LangSwitch } from './LangSwitch'
import { MethodSimple } from './Methodology'
import { NewsletterForm } from './NewsletterForm'
import { NumericData, stagger } from './PredictionDetails'
import { REGION_SHORT, cellCoordinates, ensoCategory, firstTemperature, getCantonIndex, getPredictions, monthLong, monthShort, num, rainAnalog, regionForCell, signed } from './predictionsData'
import type { CantonIndexItem, Predictions as PredictionsData, RegionId } from './predictionsData'
import { SearchBox } from './SearchBox'
import { useReveal } from './useReveal'

const img = (name: string) => `${import.meta.env.BASE_URL}img/${name}`

/** Lo que el público está mirando: todo el país (por defecto), un cantón o una ASADA. Los dos últimos se resuelven por su cuadro del mapa de NASA. */
type Place = { kind: 'country' } | { kind: 'canton'; code: string } | { kind: 'asada'; operator: Operator }
type Panel = 'datos' | 'metodo' | null

/** Cómo se nombra cada zona dentro de una frase (con getters: siempre en el idioma activo). */
const REGION_PLAIN: Record<RegionId, string> = {
  get CR() { return t('todo el país', 'the whole country') },
  get CR_PN() { return t('la zona del Pacífico Norte (Guanacaste)', 'the North Pacific area (Guanacaste)') },
  get CR_CAR() { return t('la zona del Caribe (Limón)', 'the Caribbean area (Limón)') },
}

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)
const panelFromHash = (): Panel => window.location.hash === '#datos' ? 'datos' : window.location.hash === '#metodo' ? 'metodo' : null

// ------------------------------------------------------------------ Resumen para el público

function NinoSummary({ data }: { data: PredictionsData }) {
  const { enso } = data
  const analog = enso.analog
  if (enso.status !== 'active' || !enso.start) {
    return <article className="pred-card reveal" style={stagger(0)}>
      <span className="eyebrow">El Niño</span>
      <p className="pred-big">No<small>{t('Ahora no hay un episodio de El Niño en el océano Pacífico.', 'There is no El Niño episode in the Pacific Ocean right now.')}</small></p>
      <p>{t('Si el océano vuelve a calentarse de forma sostenida, esta página lo va a avisar.', 'If the ocean warms up again for a sustained period, this page will let you know.')}</p>
    </article>
  }
  const category = ensoCategory(enso.category)
  return <article className="pred-card nino reveal" style={stagger(0)}>
    <span className="eyebrow"><span className="pulse-dot" aria-hidden="true" /> El Niño</span>
    <p className="pred-big">{t('Activo', 'Active')}<small>{t(
      `El océano Pacífico está más caliente de lo normal desde ${monthLong(enso.start)}. Es un episodio ${category}${enso.rising ? ' y sigue creciendo' : ''}.`,
      `The Pacific Ocean has been warmer than normal since ${monthLong(enso.start)}. It is a ${category} episode${enso.rising ? ' and still growing' : ''}.`)}</small></p>
    {analog && <p>{t(
      `Lo más probable es que termine hacia ${monthLong(analog.end_window.typical)}, aunque podría ser desde ${monthShort(analog.end_window.earliest)} hasta ${monthShort(analog.end_window.latest)}.`,
      `It will most likely end around ${monthLong(analog.end_window.typical)}, although it could be anywhere from ${monthShort(analog.end_window.earliest)} to ${monthShort(analog.end_window.latest)}.`)}</p>}
    <p className="muted">{t('Son fechas de referencia según otros episodios fuertes; nadie puede asegurar el día exacto.', 'These are reference dates based on other strong episodes; nobody can guarantee the exact day.')}</p>
  </article>
}

function HeatSummary({ data, region }: { data: PredictionsData; region: RegionId }) {
  const heat = firstTemperature(data, region)
  if (!heat) return null
  const diff = heat.anomaly
  const phrase = diff >= 0.3 ? t('más calor de lo normal', 'warmer than normal') : diff <= -0.3 ? t('más fresco de lo normal', 'cooler than normal') : t('casi igual de calor que lo normal', 'about as warm as normal')
  return <article className="pred-card heat reveal" style={stagger(1)}>
    <span className="eyebrow">{t('Calor', 'Heat')} · {monthLong(heat.row.target_month)}</span>
    <p className="pred-big"><CountUp value={diff} format={value => `${value < 0 ? '−' : '+'}${num(Math.abs(value))} °C`} /><small>{t(`${capitalize(phrase)} en ${REGION_PLAIN[region]}.`, `${capitalize(phrase)} in ${REGION_PLAIN[region]}.`)}</small></p>
    <p>{diff >= 0.5 ? t('Es bastante más de lo que suele pasar en ese mes.', 'That is quite a bit more than usual for that month.')
      : diff >= 0.3 ? t('Se va a sentir un poco más caliente que de costumbre.', 'It will feel a bit warmer than usual.')
        : t('No se espera una diferencia grande con un mes normal.', 'No big difference from a normal month is expected.')}</p>
    <p className="tag">{t('Pronóstico experimental', 'Experimental forecast')}</p>
  </article>
}

function RainSummary({ data, region }: { data: PredictionsData; region: RegionId }) {
  const month = data.variables.PRECTOTCORR.regions[region].rows[0]?.target_month
  const found = month ? rainAnalog(data, region, month) : undefined
  if (!month || !found) return null
  const less = found.anomaly_pct < 0
  return <article className="pred-card rain reveal" style={stagger(2)}>
    <span className="eyebrow">{t('Lluvia', 'Rain')} · {monthLong(month)}</span>
    <p className="pred-big"><CountUp value={found.anomaly_pct} format={value => `${value < 0 ? '−' : '+'}${num(Math.abs(value), 0)} %`} /><small>{t(
      `${less ? 'Menos' : 'Más'} lluvia que lo normal en ${REGION_PLAIN[region]}, en años parecidos de El Niño.`,
      `${less ? 'Less' : 'More'} rain than normal in ${REGION_PLAIN[region]}, in similar El Niño years.`)}</small></p>
    <p>{t(`No es una predicción: cuenta lo que pasó en los ${found.n_years} años con un Niño parecido al de ahora.`,
      `This is not a prediction: it counts what happened in the ${found.n_years} years with an El Niño similar to the current one.`)}</p>
    <p className="tag">{t('Sin pronóstico validado de lluvia', 'No validated rain forecast')}</p>
  </article>
}

type Tip = { tone: 'agua' | 'calor' | 'info' | 'ok'; label: string; title: string; text: string }

/** Consejos según lo que dicen los números de la zona. Si hay una ASADA elegida, se nombra. */
function buildTips(data: PredictionsData, region: RegionId, asada?: Operator): Tip[] {
  const month = data.variables.PRECTOTCORR.regions[region].rows[0]?.target_month
  const rain = month ? rainAnalog(data, region, month) : undefined
  const heat = firstTemperature(data, region)
  const provider = asada ? asada.name : t('tu ASADA', 'your ASADA')
  const tips: Tip[] = []
  if (data.enso.status === 'active' && rain && rain.anomaly_pct <= -20) tips.push({
    tone: 'agua', label: t('Agua', 'Water'), title: t('Preparate para menos lluvia', 'Get ready for less rain'),
    text: t(`En años parecidos llovió cerca de ${num(Math.abs(rain.anomaly_pct), 0)} % menos en ${monthLong(rain.month)}. Guardá agua limpia, revisá si hay fugas en tu casa y preguntale a ${provider} si habrá racionamientos.`,
      `In similar years it rained about ${num(Math.abs(rain.anomaly_pct), 0)} % less in ${monthLong(rain.month)}. Store clean water, check for leaks at home and ask ${provider} whether there will be rationing.`) })
  else if (rain && rain.anomaly_pct >= 20) tips.push({
    tone: 'agua', label: t('Agua', 'Water'), title: t('Puede llover más de lo normal', 'It may rain more than normal'),
    text: t(`En años parecidos llovió cerca de ${num(rain.anomaly_pct, 0)} % más en ${monthLong(rain.month)}. Mantené limpios los canales y desagües y no cruces ríos crecidos.`,
      `In similar years it rained about ${num(rain.anomaly_pct, 0)} % more in ${monthLong(rain.month)}. Keep gutters and drains clear and do not cross swollen rivers.`) })
  if (heat && heat.anomaly >= 0.5) tips.push({
    tone: 'calor', label: t('Calor', 'Heat'), title: t('Calor sobre lo normal', 'Heat above normal'),
    text: t(`Se espera cerca de ${num(heat.anomaly)} °C más que lo normal en ${monthLong(heat.row.target_month)}. Tomá agua seguido, evitá el sol de 10 a. m. a 2 p. m. y cuidá a niños y personas mayores.`,
      `About ${num(heat.anomaly)} °C above normal is expected in ${monthLong(heat.row.target_month)}. Drink water often, avoid the sun from 10 a.m. to 2 p.m. and look after children and older people.`) })
  if (!tips.length) tips.push({
    tone: 'ok', label: t('Todo en calma', 'All calm'), title: t('Nada fuera de lo común por ahora', 'Nothing out of the ordinary for now'),
    text: t('Los números de esta zona no muestran un cambio grande en el calor ni en la lluvia. Aun así, seguí los avisos oficiales.',
      'The numbers for this area do not show a big change in heat or rain. Even so, follow the official notices.') })
  tips.push({
    tone: 'info', label: t('Información', 'Information'), title: t('Verificá antes de decidir', 'Check before deciding'),
    text: t(`Son cifras de una zona amplia y experimentales, no avisos oficiales. Para tu comunidad confiá en el boletín del IMN y en los avisos de ${provider} o del AyA.`,
      `These are experimental figures for a wide area, not official notices. For your community, rely on the IMN bulletin and on the notices from ${provider} or the AyA.`) })
  return tips
}

function PlaceBar({ data, place, region, label, sub, cell, reset }: { data: PredictionsData; place: Place; region: RegionId; label: string; sub?: string; cell?: string; reset: () => void }) {
  const coords = cell ? cellCoordinates(cell) : ''
  return <div className="place-bar reveal">
    <div>
      <span className="eyebrow">{t('Resumen para', 'Summary for')}</span>
      <h2 id="top-title">{label}</h2>
      {sub && <p className="place-sub">{sub}</p>}
      <p className="place-note">
        {place.kind === 'country'
          ? t('Mostramos el promedio de todo el país. Buscá tu cantón o tu ASADA para ver lo que se espera en tu zona.', 'We show the national average. Search for your canton or your ASADA to see what is expected in your area.')
          : region === 'CR'
            ? t(`Este lugar queda en un cuadro del mapa (${coords}) que todavía no tiene un cálculo propio. Por eso mostramos el promedio de todo el país.`,
              `This place falls in a map grid cell (${coords}) that does not have its own calculation yet. That is why we show the national average.`)
            : t(`Este lugar queda en el cuadro del mapa ${coords}, que pertenece a ${REGION_PLAIN[region]}. Mostramos los datos de esa zona.`,
              `This place falls in the map grid cell ${coords}, which belongs to ${REGION_PLAIN[region]}. We show the data for that area.`)}
      </p>
    </div>
    <div className="place-actions">
      {place.kind !== 'country' && <button className="pill pill-ghost" onClick={reset}>{t('← Ver todo el país', '← See the whole country')}</button>}
      <span className="place-meta">{t('Datos hasta', 'Data through')} {monthLong(data.data_through)}</span>
    </div>
  </div>
}

function Summary({ data, place, region, label, sub, cell, reset }: { data: PredictionsData; place: Place; region: RegionId; label: string; sub?: string; cell?: string; reset: () => void }) {
  const tips = buildTips(data, region, place.kind === 'asada' ? place.operator : undefined)
  return <section className="section pred-first" id="resumen" aria-labelledby="top-title">
    <PlaceBar data={data} place={place} region={region} label={label} sub={sub} cell={cell} reset={reset} />
    <div className="pred-top" aria-live="polite"><NinoSummary data={data} /><HeatSummary data={data} region={region} /><RainSummary data={data} region={region} /></div>
    <div className="pred-tips">
      {tips.map((tip, index) => <article key={tip.tone + index} className={`pred-tip ${tip.tone} reveal`} style={stagger(index)}>
        <span className="chip">{tip.label}</span>
        <h3>{tip.title}</h3><p>{tip.text}</p>
      </article>)}
    </div>
  </section>
}

// ------------------------------------------------------------------ Página

function Body({ data, canton, asadas, searchLoading, panel, togglePanel }: {
  data: PredictionsData
  canton: CantonIndexItem[]; asadas: Operator[]; searchLoading: boolean
  panel: Panel; togglePanel: (next: Exclude<Panel, null>) => void
}) {
  const [place, setPlace] = useState<Place>({ kind: 'country' })
  const choices = useMemo(() => new Map<string, Canton>(canton.map(item => [item.code, { name: item.name, province: item.province }])), [canton])
  const cells = useMemo(() => new Map(canton.map(item => [item.code, item.cell])), [canton])

  const cantonCode = place.kind === 'canton' ? place.code : place.kind === 'asada' ? place.operator.cantonCode : ''
  const cell = cantonCode ? cells.get(cantonCode) ?? '' : ''
  const region: RegionId = cell ? regionForCell(data, cell) : 'CR'
  const info = choices.get(cantonCode)
  const label = place.kind === 'country' ? 'Costa Rica' : place.kind === 'asada' ? place.operator.name
    : info ? (info.name === info.province ? info.name : `${info.name}, ${info.province}`) : 'Costa Rica'
  const sub = place.kind === 'asada' ? `${place.operator.type} · ${place.operator.district}, ${place.operator.canton}, ${place.operator.province}` : undefined

  useReveal([panel, place, region])

  // Un enlace con #datos o #metodo abre su panel y baja hasta los botones; otro ancla (p. ej. #resumen) baja a su sección.
  useEffect(() => {
    if (panel) requestAnimationFrame(() => document.getElementById('mas')?.scrollIntoView())
    else if (window.location.hash) document.getElementById(window.location.hash.slice(1))?.scrollIntoView()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return <>
    <header className="hero pred-hero" id="inicio">
      <img className="hero-img" src={img('nino.jpg')} alt={t('Quebrada con pozas y rocas cubiertas de musgo dentro de un bosque verde en Guanacaste', 'Stream with pools and moss-covered rocks inside a green forest in Guanacaste')} fetchPriority="high" />
      <div className="hero-veil" aria-hidden="true" />
      <div className="hero-inner">
        <span className="hero-eyebrow pred-rise" style={stagger(0)}>{t('AguaAlerta · Predicciones experimentales', 'AguaAlerta · Experimental predictions')}</span>
        <h1 className="pred-rise" style={stagger(1)}>{t('Lo que viene para el clima de Costa Rica', "What is coming for Costa Rica's climate")}</h1>
      </div>
    </header>

    <main>
      <div className="pred-search section" role="search" aria-label={t('Buscar tu zona', 'Find your area')}>
        <SearchBox context="predicciones" inputId="search-pred" choices={choices} asadas={asadas} loading={searchLoading}
          districtNote={t('El resumen usa el cuadro del mapa de tu cantón.', "The summary uses your canton's map grid cell.")}
          onCanton={code => setPlace({ kind: 'canton', code })} onAsada={operator => setPlace({ kind: 'asada', operator })} onProvince={() => undefined} />
      </div>

      <Summary data={data} place={place} region={region} label={label} sub={sub} cell={cell || undefined} reset={() => setPlace({ kind: 'country' })} />

      {place.kind === 'asada' && <NewsletterForm key={place.operator.id} operator={place.operator} />}

      <section className="section pred-more" id="mas" aria-labelledby="more-title">
        <div className="section-head reveal">
          <span className="eyebrow">{t('Para quien quiere saber más', 'For those who want to know more')}</span>
          <h2 id="more-title">{t('Los números y cómo los calculamos', 'The numbers and how we calculate them')}</h2>
        </div>
        <div className="more-buttons reveal">
          <button id="btn-datos" className="more-button" aria-expanded={panel === 'datos'} aria-controls="panel-datos" onClick={() => togglePanel('datos')}>
            <strong>{t('Datos numéricos', 'Numeric data')}</strong>
            <span>{t('Gráficos, tablas y cifras de temperatura, lluvia y El Niño.', 'Charts, tables and figures on temperature, rain and El Niño.')}</span>
            <i aria-hidden="true">{panel === 'datos' ? '▴' : '▾'}</i>
          </button>
          <button id="btn-metodo" className="more-button" aria-expanded={panel === 'metodo'} aria-controls="panel-metodo" onClick={() => togglePanel('metodo')}>
            <strong>{t('Cómo obtenemos estos datos', 'How we obtain this data')}</strong>
            <span>{t('El análisis estadístico de AguaAlerta explicado en simple, con un PDF completo.', "AguaAlerta's statistical analysis explained simply, with a full PDF.")}</span>
            <i aria-hidden="true">{panel === 'metodo' ? '▴' : '▾'}</i>
          </button>
        </div>
      </section>

      {panel === 'datos' && <div id="panel-datos" role="region" aria-labelledby="btn-datos"><NumericData data={data} region={region} /></div>}
      {panel === 'metodo' && <div id="panel-metodo" role="region" aria-labelledby="btn-metodo"><MethodSimple data={data} /></div>}
    </main>

    <footer className="landing-footer">
      <p><strong>{t('AguaAlerta — Predicciones experimentales.', 'AguaAlerta — Experimental predictions.')}</strong> {t(
        'Calculadas con el motor de predicciones de AguaAlerta sobre series regionales de Copernicus (ERA5-Land), NASA POWER y el RONI de NOAA. No reemplazan los avisos del IMN, el AyA ni de tu ASADA.',
        "Calculated with the AguaAlerta prediction engine on regional series from Copernicus (ERA5-Land), NASA POWER and NOAA's RONI. They do not replace the notices from the IMN, the AyA or your ASADA.")}</p>
    </footer>
  </>
}

export function Predictions({ openMap, goHome }: { openMap: (mode: MapMode) => void; goHome: () => void }) {
  const [data, setData] = useState<PredictionsData>()
  const [failed, setFailed] = useState(false)
  const [canton, setCanton] = useState<CantonIndexItem[]>([])
  const [asadas, setAsadas] = useState<Operator[]>([])
  const [searchLoading, setSearchLoading] = useState(true)
  const [panel, setPanel] = useState<Panel>(panelFromHash)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    getPredictions(signal).then(value => { if (!signal.aborted) setData(value) })
      .catch(() => { if (!signal.aborted) setFailed(true) })
    // El buscador necesita los cantones (liviano) y las ASADAs (más pesado): si alguno falla, se busca con lo que haya.
    void Promise.allSettled([
      getCantonIndex(signal).then(value => { if (!signal.aborted) setCanton(value) }),
      getAsadas(signal).then(value => { if (!signal.aborted) setAsadas(value.operators) }),
    ]).then(() => { if (!signal.aborted) setSearchLoading(false) })
    return () => controller.abort()
  }, [])

  /** Los botones del final abren y cierran su panel; los enlaces de la barra solo lo abren (`toggle = false`). */
  function openPanel(next: Exclude<Panel, null>, toggle: boolean) {
    const closing = toggle && panel === next
    setPanel(closing ? null : next)
    history.replaceState(null, '', closing ? `${window.location.pathname}${window.location.search}` : `#${next}`)
    if (!closing) requestAnimationFrame(() => document.getElementById('mas')?.scrollIntoView({ behavior: 'smooth' }))
  }

  return <div className="landing pred">
    <nav className="landing-nav glass" aria-label={t('Navegación principal', 'Main navigation')}>
      <a className="brand" href="." onClick={event => { event.preventDefault(); goHome() }}>AguaAlerta</a>
      <div className="nav-links">
        <a href="#resumen">{t('Resumen', 'Summary')}</a>
        <button onClick={() => openPanel('datos', false)}>{t('Datos numéricos', 'Numeric data')}</button>
        <button onClick={() => openPanel('metodo', false)}>{t('Cómo lo obtenemos', 'How we get it')}</button>
      </div>
      <div className="nav-tools">
        <LangSwitch />
        <div className="segmented" role="group" aria-label={t('Mapas y predicciones', 'Maps and predictions')}>
          <button onClick={() => openMap('grid')}>NASA POWER</button>
          <button onClick={() => openMap('cds')}>CDS</button>
          <button onClick={() => openMap('cantones')}>{t('Nacionales', 'National')}</button>
          <button aria-pressed="true" aria-current="page">{t('Predicciones', 'Predictions')}</button>
        </div>
      </div>
    </nav>
    {data ? <Body data={data} canton={canton} asadas={asadas} searchLoading={searchLoading} panel={panel} togglePanel={next => openPanel(next, true)} />
      : <header className="hero pred-hero loading">
        <div className="hero-veil" aria-hidden="true" />
        <div className="hero-inner"><h1>{failed ? t('No se pudieron cargar las predicciones', 'Could not load the predictions') : t('Calculando…', 'Calculating…')}</h1>
          <p>{failed ? t('Generalas con «python -m src.predictions» y recargá la página.', 'Generate them with "python -m src.predictions" and reload the page.') : t('Cargando las predicciones.', 'Loading the predictions.')}</p></div>
      </header>}
  </div>
}
