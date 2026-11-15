import { useEffect, useMemo, useState } from 'react'
import { ALERT_LABEL, ALERT_ORDER, defaultThresholds, fmt, levelFor, project } from './analysis'
import type { AlertLevel } from './analysis'
import { latestReports } from './asadas'
import { copy } from './copy'
import type { MapMode } from './copy'
import { getSnapshot } from './data'
import type { Snapshot, Variable } from './data'
import { AlertPill } from './Forecast'
import { locale, t, useLang } from './i18n'
import { dataCards, photoCredits, sources, tipList, TOPIC_LABEL } from './landingCopy'
import type { Tip, TipTopic } from './landingCopy'
import { LangSwitch } from './LangSwitch'
import { getPredictions } from './predictionsData'
import type { Predictions } from './predictionsData'
import { PredictionsTeaser } from './PredictionsTeaser'
import { MAX_YEAR, MIN_YEAR } from './RangeSlider'
import { useCantonData } from './store'
import { useReveal, useScrollToHash } from './useReveal'

const img = (name: string) => `${import.meta.env.BASE_URL}img/${name}`
const rank = (level: AlertLevel) => ALERT_ORDER.indexOf(level)

type Warning = { id: string; level: AlertLevel; kicker: string; title: string; text: string; topic: TipTopic; href?: string }

const monthName = (value: string) => {
  const [year, month] = value.split('-').map(Number)
  return new Date(year, month - 1, 1).toLocaleDateString(locale(), { month: 'long', year: 'numeric' })
}
const monthsBetween = (start: string, end: string) => {
  const [y1, m1] = start.split('-').map(Number)
  const [y2, m2] = end.split('-').map(Number)
  return (y2 - y1) * 12 + (m2 - m1) + 1
}

/** Advertencias del momento: proyección nacional de tendencia, avisos oficiales vigentes y reportes de las ASADAs. */
function buildWarnings(snapshot: Snapshot | undefined, affectedOperators: number, reported: number): Warning[] {
  const found: Warning[] = []
  if (snapshot) {
    for (const variable of ['T2M', 'PRECTOTCORR'] as Variable[]) {
      const climate = snapshot.climate.CR?.[variable]
      if (!climate) continue
      const result = project(climate.series, variable, [MIN_YEAR, MAX_YEAR])
      if (!result.ok) continue
      const [short, long] = [result.corto, result.mediano]
      const levelShort = levelFor(variable, short.deviation, defaultThresholds)
      const levelLong = levelFor(variable, long.deviation, defaultThresholds)
      const [outcome, level] = rank(levelShort) > rank(levelLong) ? [short, levelShort] : [long, levelLong]
      const extreme = variable === 'PRECTOTCORR' ? Math.abs(outcome.deviation) >= 100 : Math.abs(outcome.deviation) >= 3
      const amount = variable === 'PRECTOTCORR'
        ? t(`${fmt(Math.abs(outcome.deviation), 0)} % ${outcome.deviation < 0 ? 'menos' : 'más'} lluvia que lo habitual`, `${fmt(Math.abs(outcome.deviation), 0)} % ${outcome.deviation < 0 ? 'less' : 'more'} rain than usual`)
        : t(`${fmt(Math.abs(outcome.deviation), 1)} °C ${outcome.deviation < 0 ? 'más fresco' : 'más caliente'} que lo habitual`, `${fmt(Math.abs(outcome.deviation), 1)} °C ${outcome.deviation < 0 ? 'cooler' : 'warmer'} than usual`)
      found.push({
        id: variable, level, kicker: t('Tendencia nacional · NASA POWER', 'National trend · NASA POWER'), topic: variable === 'T2M' ? 'calor' : 'agua',
        title: variable === 'T2M' ? t('Temperatura', 'Temperature') : t('Lluvia', 'Rain'),
        text: extreme
          ? t(`La tendencia ${MIN_YEAR}–${MAX_YEAR} da un resultado extremo: en ${outcome.year} habría ${amount}. Los datos de lluvia de reanálisis piden cautela; revisá la serie en el mapa antes de usarlo.`,
            `The ${MIN_YEAR}–${MAX_YEAR} trend gives an extreme result: in ${outcome.year} there would be ${amount}. Reanalysis rainfall data call for caution; check the series on the map before using it.`)
          : t(`Si sigue la tendencia ${MIN_YEAR}–${MAX_YEAR}, en ${outcome.year} el país tendría ${amount}.`, `If the ${MIN_YEAR}–${MAX_YEAR} trend continues, in ${outcome.year} the country would have ${amount}.`),
      })
    }
    const now = new Date()
    for (const notice of snapshot.local.notices) {
      if (notice.expiresAt && new Date(notice.expiresAt) < now) continue
      found.push({ id: notice.id, level: 'naranja', kicker: t(`Aviso oficial · ${notice.source}`, `Official notice · ${notice.source}`), title: notice.title, text: notice.summary, topic: 'info', href: notice.sourceUrl })
    }
  }
  if (affectedOperators > 0) {
    found.push({
      id: 'asadas', level: 'amarillo', kicker: t('Reportes de ASADAs', 'ASADA reports'), topic: 'agua',
      title: t(`${affectedOperators} ${affectedOperators === 1 ? 'operador reporta' : 'operadores reportan'} afectación por El Niño`, `${affectedOperators} ${affectedOperators === 1 ? 'operator reports' : 'operators report'} impacts from El Niño`),
      text: t('Las ASADAs reportaron caudal bajo o falta de agua en algunas localidades. Abrí «Datos nacionales» para verlas en el mapa.', 'The ASADAs reported low flow or lack of water in some localities. Open "National data" to see them on the map.'),
    })
  } else if (reported > 0) {
    found.push({
      id: 'asadas', level: 'verde', kicker: t('Reportes de ASADAs', 'ASADA reports'), topic: 'agua', title: t('Sin afectación reportada', 'No impact reported'),
      text: t(`${reported} ${reported === 1 ? 'operador reportó' : 'operadores reportaron'} que El Niño no los está afectando por ahora.`, `${reported} ${reported === 1 ? 'operator reported' : 'operators reported'} that El Niño is not affecting them for now.`),
    })
  }
  if (!found.some(item => item.topic === 'info')) {
    found.push({ id: 'avisos', level: 'verde', kicker: t('Avisos oficiales', 'Official notices'), topic: 'info', title: t('Sin avisos oficiales vigentes', 'No official notices in effect'),
      text: t('Cuando el IMN, el AyA o una ASADA publiquen un aviso, va a aparecer acá.', 'When the IMN, the AyA or an ASADA publishes a notice, it will appear here.') })
  }
  return found.sort((a, b) => rank(b.level) - rank(a.level))
}

/** Tres consejos de temas distintos. El primero sale del tema de la advertencia más seria, si hay alguna. */
function pickTips(focus: TipTopic | undefined): Tip[] {
  const shuffled = tipList().sort(() => Math.random() - 0.5)
  const chosen: Tip[] = []
  const first = focus ? shuffled.find(tip => tip.topic === focus) : undefined
  if (first) chosen.push(first)
  for (const tip of shuffled) {
    if (chosen.length === 3) break
    if (!chosen.includes(tip) && !chosen.some(item => item.topic === tip.topic)) chosen.push(tip)
  }
  for (const tip of shuffled) if (chosen.length < 3 && !chosen.includes(tip)) chosen.push(tip)
  return chosen
}

export function Landing({ openMap, openPredictions }: { openMap: (mode: MapMode) => void; openPredictions: () => void }) {
  const lang = useLang()
  const [snapshot, setSnapshot] = useState<Snapshot>()
  const [predictions, setPredictions] = useState<Predictions>()
  const [failed, setFailed] = useState(false)
  const data = useCantonData()
  const [tipRound, setTipRound] = useState(0)
  useReveal([predictions])
  useScrollToHash()

  useEffect(() => {
    const controller = new AbortController()
    getSnapshot(controller.signal).then(value => { if (!controller.signal.aborted) setSnapshot(value) })
      .catch(() => { if (!controller.signal.aborted) setFailed(true) })
    getPredictions(controller.signal).then(value => { if (!controller.signal.aborted) setPredictions(value) }).catch(() => {})
    return () => controller.abort()
  }, [])

  const latest = useMemo(() => latestReports(data.reports), [data.reports])
  const affected = useMemo(() => [...latest.values()].filter(item => item.ninoAffected).length, [latest])
  // `lang` en las dependencias: las advertencias y los consejos llevan texto y deben rehacerse al cambiar de idioma.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const warnings = useMemo(() => buildWarnings(snapshot, affected, latest.size), [snapshot, affected, latest, lang])
  const urgent = warnings.find(item => item.level !== 'verde')
  // `tipRound` cambia al pedir otros consejos; las advertencias cambian cuando llegan los datos.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const tips = useMemo(() => pickTips(urgent?.topic), [urgent?.topic, tipRound, lang])

  const temperature = snapshot?.climate.CR?.T2M
  const episode = temperature?.enso.episode
  const years = temperature?.series.filter(point => point.value !== null).length
  const slope = temperature?.trend.slope_per_decade
  const text = copy.basico

  return <div className="landing">
    <nav className="landing-nav glass" aria-label={t('Navegación principal', 'Main navigation')}>
      <a className="brand" href="#inicio">AguaAlerta</a>
      <div className="nav-links">
        <a href="#el-nino">El Niño</a>
        <a href="#advertencias">{t('Advertencias', 'Warnings')}</a>
        <a href="#predicciones">{t('Predicciones', 'Predictions')}</a>
        <a href="#datos">{t('Datos', 'Data')}</a>
        <a href="#fuentes">{t('Fuentes', 'Sources')}</a>
      </div>
      <div className="nav-actions">
        <LangSwitch />
        <a className="pill pill-ghost" href="?pagina=predicciones" onClick={event => { event.preventDefault(); openPredictions() }}>{t('Predicciones', 'Predictions')}</a>
        <button className="pill pill-primary" onClick={() => openMap('grid')}>{t('Abrir el mapa', 'Open the map')}</button>
      </div>
    </nav>

    <header className="hero" id="inicio">
      <img className="hero-img" src={img('hero.jpg')} alt={t('Sendero entre árboles cubiertos de musgo en el bosque nuboso de Monteverde, Costa Rica', 'Path between moss-covered trees in the Monteverde cloud forest, Costa Rica')} fetchPriority="high" />
      <div className="hero-veil" aria-hidden="true" />
      <div className="hero-inner">
        <span className="hero-eyebrow">{t('Monitor climático y territorial', 'Climate and territorial monitor')}</span>
        <h1>{t('Entender El Niño para cuidar el agua de Costa Rica', "Understanding El Niño to look after Costa Rica's water")}</h1>
        <p>{t('Cuatro décadas de datos de clima, un mapa para explorarlos y avisos para saber qué está pasando en tu zona.', 'Four decades of climate data, a map to explore them and notices to know what is happening in your area.')}</p>
        <div className="hero-actions">
          <button className="pill pill-primary hero-cta" onClick={() => openMap('grid')}>{t('Abrir el mapa', 'Open the map')}</button>
          <a className="pill hero-cta" href="#el-nino">{t('Conocer El Niño', 'Learn about El Niño')}</a>
        </div>
        {warnings[0] && <a className="hero-now glass" href="#advertencias">
          <AlertPill level={warnings[0].level} />
          <span><strong>{t('Ahora:', 'Now:')}</strong> {urgent ? urgent.title : t('sin advertencias activas', 'no active warnings')}</span>
        </a>}
      </div>
      <a className="scroll-cue" href="#el-nino" aria-label={t('Bajar a la ficha de El Niño', 'Scroll down to the El Niño fact sheet')}><span>{t('Bajá para ver más', 'Scroll down for more')}</span><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg></a>
    </header>

    <main>
      <section className="section" id="el-nino" aria-labelledby="nino-title">
        <div className="section-head reveal">
          <span className="eyebrow">{t('Ficha informativa', 'Fact sheet')}</span>
          <h2 id="nino-title">{t('¿Qué es El Niño?', 'What is El Niño?')}</h2>
          <p className="lead">{t('Es una etapa en la que el océano Pacífico, frente a la costa de Sudamérica, está más cálido de lo normal. Ese calor extra cambia los vientos y la lluvia en medio mundo, también en Costa Rica.',
            'It is a phase in which the Pacific Ocean, off the coast of South America, is warmer than normal. That extra heat changes winds and rain across half the world, including Costa Rica.')}</p>
        </div>
        <div className="split">
          <figure className="photo reveal">
            <img src={img('nino.jpg')} alt={t('Quebrada con pozas y rocas cubiertas de musgo dentro de un bosque verde en Guanacaste', 'Stream with pools and moss-covered rocks inside a green forest in Guanacaste')} loading="lazy" />
            <figcaption>{t('Una quebrada de Guanacaste. Cuando llueve menos, los caudales como este bajan primero.', 'A stream in Guanacaste. When it rains less, flows like this one drop first.')}</figcaption>
          </figure>
          <div className="fact-sheet reveal">
            <div className="fact"><span className="fact-icon" aria-hidden="true">🌊</span><div><h3>{t('Cómo se origina', 'How it starts')}</h3><p>{t('El Pacífico ecuatorial se calienta unos grados. Es la fase cálida del ciclo ENOS (El Niño–Oscilación del Sur).', 'The equatorial Pacific warms by a few degrees. It is the warm phase of the ENSO cycle (El Niño–Southern Oscillation).')}</p></div></div>
            <div className="fact"><span className="fact-icon" aria-hidden="true">🌦️</span><div><h3>{t('Cómo nos afecta', 'How it affects us')}</h3><p>{t('El Pacífico Norte, el Valle Central y la Zona Norte suelen tener menos lluvia y más calor. En el Caribe puede llover más de lo normal.', 'The North Pacific, the Central Valley and the Northern Zone usually get less rain and more heat. In the Caribbean it can rain more than normal.')}</p></div></div>
            <div className="fact"><span className="fact-icon" aria-hidden="true">⏳</span><div><h3>{t('Cada cuánto vuelve', 'How often it returns')}</h3><p>{t('Aparece cada 2 a 7 años y dura entre 9 y 12 meses. Sus efectos van desde sequías hasta cortes de agua y pérdidas en el campo.', 'It appears every 2 to 7 years and lasts between 9 and 12 months. Its effects range from droughts to water cuts and losses in agriculture.')}</p></div></div>
            <div className="fact now">
              <span className="fact-icon" aria-hidden="true">📅</span>
              <div>
                <h3>{t('Último episodio cargado', 'Latest episode loaded')}</h3>
                {episode
                  ? <p><strong>{monthName(episode.start)}</strong> {t('a', 'to')} <strong>{monthName(episode.end)}</strong> · {monthsBetween(episode.start, episode.end)} {t('meses', 'months')}.
                    {episode.sources?.length ? <> {t('Fuentes del IMN:', 'IMN sources:')} {episode.sources.map((url, index) => <span key={url}>{index > 0 && ', '}<a href={url} target="_blank" rel="noreferrer">{t('boletín', 'bulletin')} {index + 1}</a></span>)}.</> : null}</p>
                  : <p className="muted">{failed ? t('No se pudieron cargar los datos del episodio.', 'Could not load the episode data.') : t('Cargando el episodio…', 'Loading the episode…')}</p>}
              </div>
            </div>
          </div>
        </div>
        <div className="stat-row reveal">
          <div className="stat"><strong>{years ?? '—'}</strong><span>{t('años de datos del clima', 'years of climate data')}{temperature?.series.length ? ` (${temperature.series[0].year}–${temperature.series[temperature.series.length - 1].year})` : ''}</span></div>
          <div className="stat"><strong>{slope == null ? '—' : `${slope >= 0 ? '+' : '−'}${fmt(Math.abs(slope), 2)} °C`}</strong><span>{t('de temperatura por década.', 'of temperature per decade.')} {temperature ? text.significance(temperature.trend.significant) : ''}</span></div>
          <div className="stat"><strong>{episode ? `${monthsBetween(episode.start, episode.end)} ${t('meses', 'months')}` : '—'}</strong><span>{t('duró el último episodio de El Niño cargado', 'the latest El Niño episode loaded lasted')}</span></div>
          <div className="stat"><strong>4</strong><span>{t('variables en el mapa: temperatura, lluvia, humedad y UV', 'variables on the map: temperature, rain, humidity and UV')}</span></div>
        </div>
      </section>

      <section className="section band" id="advertencias" aria-labelledby="warn-title">
        <div className="section-head reveal">
          <span className="eyebrow">{t('Lo más importante ahora', 'What matters most right now')}</span>
          <h2 id="warn-title">{t('Advertencias y sugerencias', 'Warnings and suggestions')}</h2>
          <p className="lead">{t('Lo que dicen hoy los datos del país y los reportes de las ASADAs, ordenado de lo más serio a lo más tranquilo.', 'What the national data and the ASADA reports say today, ordered from most serious to calmest.')}</p>
        </div>
        {!snapshot && !failed && <p className="empty">{t('Cargando las advertencias…', 'Loading the warnings…')}</p>}
        {failed && <p className="empty">{t('No se pudieron cargar los datos del clima. Igual podés abrir el mapa y volver a intentarlo.', 'Could not load the climate data. You can still open the map and try again.')}</p>}
        <div className="warning-grid reveal">
          {warnings.map(item => <article key={item.id} className={`warning card ${item.level}`}>
            <div className="warning-top"><AlertPill level={item.level} /><small>{item.kicker}</small></div>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
            {item.href && <a href={item.href} target="_blank" rel="noreferrer">{t('Ver la fuente', 'See the source')}</a>}
          </article>)}
        </div>
        <p className="muted note reveal">{text.forecastNote} {t('Niveles:', 'Levels:')} {ALERT_ORDER.map(level => ALERT_LABEL[level]).join(' · ')}.</p>

        <div className="tips-head reveal">
          <h3>{t('Qué podés hacer', 'What you can do')}</h3>
          <button className="pill pill-ghost" onClick={() => setTipRound(round => round + 1)}>{t('Ver otros consejos', 'See other tips')}</button>
        </div>
        <div className="tips-grid" aria-live="polite">
          {tips.map(tip => <article key={tip.title} className="tip card">
            <span className="chip">{TOPIC_LABEL[tip.topic]}</span>
            <h4>{tip.title}</h4>
            <p>{tip.text}</p>
          </article>)}
        </div>
        <p className="muted note">{text.recommendationsNote}</p>
      </section>

      <PredictionsTeaser data={predictions} openPredictions={openPredictions} />

      <section className="section" id="datos" aria-labelledby="data-title">
        <div className="section-head reveal">
          <span className="eyebrow">{t('Explorá el mapa', 'Explore the map')}</span>
          <h2 id="data-title">{t('Tres formas de mirar el país', 'Three ways to look at the country')}</h2>
          <p className="lead">{t('Cada botón te lleva directo al mapa con esa fuente de datos. Podés cambiar de una a otra cuando quieras desde la barra de arriba.', 'Each button takes you straight to the map with that data source. You can switch from one to another whenever you want from the top bar.')}</p>
        </div>
        {dataCards().map((card, index) => <article key={card.mode} className={`split data-split${index % 2 ? ' reverse' : ''}`} id={`datos-${card.mode}`}>
          <figure className="photo reveal">
            <img src={img(card.image)} alt={card.alt} loading="lazy" />
          </figure>
          <div className="data-text reveal">
            <span className="chip nasa">{card.chip}</span>
            <h3>{card.title}</h3>
            <p>{card.summary}</p>
            <ul className="facts">{card.facts.map(fact => <li key={fact}>{fact}</li>)}</ul>
            <details>
              <summary>{t('Detalle técnico', 'Technical detail')}</summary>
              <p className="muted">{card.technical}</p>
            </details>
            <button className="pill pill-primary" onClick={() => openMap(card.mode)}>{card.button} <span aria-hidden="true">→</span></button>
          </div>
        </article>)}
      </section>

      <section className="cta" aria-labelledby="cta-title">
        <img src={img('costa.jpg')} alt={t('Playa de la costa del Pacífico de Costa Rica al atardecer', 'Beach on the Pacific coast of Costa Rica at sunset')} loading="lazy" />
        <div className="cta-veil" aria-hidden="true" />
        <div className="cta-inner reveal">
          <h2 id="cta-title">{t('El clima cambia. Conocerlo ayuda a prepararnos.', 'The climate is changing. Understanding it helps us prepare.')}</h2>
          <p>{t('Abrí el mapa, elegí tu cantón y mirá cómo han cambiado el calor y la lluvia donde vivís.', 'Open the map, choose your canton and see how heat and rain have changed where you live.')}</p>
          <button className="pill pill-primary hero-cta" onClick={() => openMap('grid')}>{t('Abrir el mapa', 'Open the map')}</button>
        </div>
      </section>

      <section className="section" id="fuentes" aria-labelledby="src-title">
        <div className="section-head reveal">
          <span className="eyebrow">{t('De dónde salen los datos', 'Where the data comes from')}</span>
          <h2 id="src-title">{t('Fuentes', 'Sources')}</h2>
        </div>
        <ul className="source-grid">
          {sources().map(source => <li key={source.name} className="card reveal">
            <h3><a href={source.url} target="_blank" rel="noreferrer">{source.name}</a></h3>
            <p className="muted">{source.text}</p>
          </li>)}
        </ul>
      </section>
    </main>

    <footer className="landing-footer">
      <p><strong>{t('AguaAlerta — Monitor Climático y Territorial.', 'AguaAlerta — Climate and Territorial Monitor.')}</strong> {t('Las cifras son de reanálisis y modelos; no reemplazan los avisos oficiales del IMN, el AyA ni de tu ASADA.', 'The figures come from reanalysis and models; they do not replace the official notices from the IMN, the AyA or your ASADA.')}</p>
      <details>
        <summary>{t('Créditos de las fotografías', 'Photo credits')}</summary>
        <ul>{photoCredits().map(photo => <li key={photo.url}><a href={photo.url} target="_blank" rel="noreferrer">{photo.file}</a> · {photo.author} · {photo.license} · Wikimedia Commons</li>)}</ul>
      </details>
    </footer>
  </div>
}
