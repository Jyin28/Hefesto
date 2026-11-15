import { useEffect, useMemo, useState } from 'react'
import { ALERT_LABEL, ALERT_ORDER, defaultThresholds, fmt, levelFor, project } from './analysis'
import type { AlertLevel } from './analysis'
import { latestReports } from './asadas'
import { copy } from './copy'
import type { MapMode } from './copy'
import { getSnapshot } from './data'
import type { Snapshot, Variable } from './data'
import { AlertPill } from './Forecast'
import { DATA_CARDS, PHOTO_CREDITS, SOURCES, TIPS, TOPIC_LABEL } from './landingCopy'
import type { Tip, TipTopic } from './landingCopy'
import { MAX_YEAR, MIN_YEAR } from './RangeSlider'
import { useCantonData } from './store'

const img = (name: string) => `${import.meta.env.BASE_URL}img/${name}`
const rank = (level: AlertLevel) => ALERT_ORDER.indexOf(level)

type Warning = { id: string; level: AlertLevel; kicker: string; title: string; text: string; topic: TipTopic; href?: string }

const monthName = (value: string) => {
  const [year, month] = value.split('-').map(Number)
  return new Date(year, month - 1, 1).toLocaleDateString('es-CR', { month: 'long', year: 'numeric' })
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
        ? `${fmt(Math.abs(outcome.deviation), 0)} % ${outcome.deviation < 0 ? 'menos' : 'más'} lluvia que lo habitual`
        : `${fmt(Math.abs(outcome.deviation), 1)} °C ${outcome.deviation < 0 ? 'más fresco' : 'más caliente'} que lo habitual`
      found.push({
        id: variable, level, kicker: 'Tendencia nacional · NASA POWER', topic: variable === 'T2M' ? 'calor' : 'agua',
        title: variable === 'T2M' ? 'Temperatura' : 'Lluvia',
        text: extreme
          ? `La tendencia ${MIN_YEAR}–${MAX_YEAR} da un resultado extremo: en ${outcome.year} habría ${amount}. Los datos de lluvia de reanálisis piden cautela; revisá la serie en el mapa antes de usarlo.`
          : `Si sigue la tendencia ${MIN_YEAR}–${MAX_YEAR}, en ${outcome.year} el país tendría ${amount}.`,
      })
    }
    const now = new Date()
    for (const notice of snapshot.local.notices) {
      if (notice.expiresAt && new Date(notice.expiresAt) < now) continue
      found.push({ id: notice.id, level: 'naranja', kicker: `Aviso oficial · ${notice.source}`, title: notice.title, text: notice.summary, topic: 'info', href: notice.sourceUrl })
    }
  }
  if (affectedOperators > 0) {
    found.push({
      id: 'asadas', level: 'amarillo', kicker: 'Reportes de ASADAs', topic: 'agua',
      title: `${affectedOperators} ${affectedOperators === 1 ? 'operador reporta' : 'operadores reportan'} afectación por El Niño`,
      text: 'Las ASADAs reportaron caudal bajo o falta de agua en algunas localidades. Abrí «Datos nacionales» para verlas en el mapa.',
    })
  } else if (reported > 0) {
    found.push({ id: 'asadas', level: 'verde', kicker: 'Reportes de ASADAs', topic: 'agua', title: 'Sin afectación reportada', text: `${reported} ${reported === 1 ? 'operador reportó' : 'operadores reportaron'} que El Niño no los está afectando por ahora.` })
  }
  if (!found.some(item => item.topic === 'info')) {
    found.push({ id: 'avisos', level: 'verde', kicker: 'Avisos oficiales', topic: 'info', title: 'Sin avisos oficiales vigentes', text: 'Cuando el IMN, el AyA o una ASADA publiquen un aviso, va a aparecer acá.' })
  }
  return found.sort((a, b) => rank(b.level) - rank(a.level))
}

/** Tres consejos de temas distintos. El primero sale del tema de la advertencia más seria, si hay alguna. */
function pickTips(focus: TipTopic | undefined): Tip[] {
  const shuffled = [...TIPS].sort(() => Math.random() - 0.5)
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

/** Hace aparecer las secciones al bajar. Sin soporte o con movimiento reducido, todo se ve desde el principio. */
function useReveal() {
  useEffect(() => {
    const items = document.querySelectorAll<HTMLElement>('.reveal')
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      items.forEach(item => item.classList.add('in'))
      return
    }
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) { entry.target.classList.add('in'); observer.unobserve(entry.target) }
    }, { threshold: 0.12 })
    items.forEach(item => observer.observe(item))
    return () => observer.disconnect()
  }, [])
}

export function Landing({ openMap }: { openMap: (mode: MapMode) => void }) {
  const [snapshot, setSnapshot] = useState<Snapshot>()
  const [failed, setFailed] = useState(false)
  const data = useCantonData()
  const [tipRound, setTipRound] = useState(0)
  useReveal()

  useEffect(() => {
    const controller = new AbortController()
    getSnapshot(controller.signal).then(value => { if (!controller.signal.aborted) setSnapshot(value) })
      .catch(() => { if (!controller.signal.aborted) setFailed(true) })
    return () => controller.abort()
  }, [])

  const latest = useMemo(() => latestReports(data.reports), [data.reports])
  const affected = useMemo(() => [...latest.values()].filter(item => item.ninoAffected).length, [latest])
  const warnings = useMemo(() => buildWarnings(snapshot, affected, latest.size), [snapshot, affected, latest])
  const urgent = warnings.find(item => item.level !== 'verde')
  // `tipRound` cambia al pedir otros consejos; las advertencias cambian cuando llegan los datos.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const tips = useMemo(() => pickTips(urgent?.topic), [urgent?.topic, tipRound])

  const temperature = snapshot?.climate.CR?.T2M
  const episode = temperature?.enso.episode
  const years = temperature?.series.filter(point => point.value !== null).length
  const slope = temperature?.trend.slope_per_decade
  const text = copy.basico

  return <div className="landing">
    <nav className="landing-nav glass" aria-label="Navegación principal">
      <a className="brand" href="#inicio">El Niño en CR</a>
      <div className="nav-links">
        <a href="#el-nino">El Niño</a>
        <a href="#advertencias">Advertencias</a>
        <a href="#datos">Datos</a>
        <a href="#fuentes">Fuentes</a>
      </div>
      <button className="pill pill-primary" onClick={() => openMap('grid')}>Abrir el mapa</button>
    </nav>

    <header className="hero" id="inicio">
      <img className="hero-img" src={img('hero.jpg')} alt="Sendero entre árboles cubiertos de musgo en el bosque nuboso de Monteverde, Costa Rica" fetchPriority="high" />
      <div className="hero-veil" aria-hidden="true" />
      <div className="hero-inner">
        <span className="hero-eyebrow">Monitor climático y territorial</span>
        <h1>Entender El Niño para cuidar el agua de Costa Rica</h1>
        <p>Cuatro décadas de datos de clima, un mapa para explorarlos y avisos para saber qué está pasando en tu zona.</p>
        <div className="hero-actions">
          <button className="pill pill-primary hero-cta" onClick={() => openMap('grid')}>Abrir el mapa</button>
          <a className="pill hero-cta" href="#el-nino">Conocer El Niño</a>
        </div>
        {warnings[0] && <a className="hero-now glass" href="#advertencias">
          <AlertPill level={warnings[0].level} />
          <span><strong>Ahora:</strong> {urgent ? urgent.title : 'sin advertencias activas'}</span>
        </a>}
      </div>
      <a className="scroll-cue" href="#el-nino" aria-label="Bajar a la ficha de El Niño"><span>Bajá para ver más</span><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg></a>
    </header>

    <main>
      <section className="section" id="el-nino" aria-labelledby="nino-title">
        <div className="section-head reveal">
          <span className="eyebrow">Ficha informativa</span>
          <h2 id="nino-title">¿Qué es El Niño?</h2>
          <p className="lead">Es una etapa en la que el océano Pacífico, frente a la costa de Sudamérica, está más cálido de lo normal. Ese calor extra cambia los vientos y la lluvia en medio mundo, también en Costa Rica.</p>
        </div>
        <div className="split">
          <figure className="photo reveal">
            <img src={img('nino.jpg')} alt="Quebrada con pozas y rocas cubiertas de musgo dentro de un bosque verde en Guanacaste" loading="lazy" />
            <figcaption>Una quebrada de Guanacaste. Cuando llueve menos, los caudales como este bajan primero.</figcaption>
          </figure>
          <div className="fact-sheet reveal">
            <div className="fact"><span className="fact-icon" aria-hidden="true">🌊</span><div><h3>Cómo se origina</h3><p>El Pacífico ecuatorial se calienta unos grados. Es la fase cálida del ciclo ENOS (El Niño–Oscilación del Sur).</p></div></div>
            <div className="fact"><span className="fact-icon" aria-hidden="true">🌦️</span><div><h3>Cómo nos afecta</h3><p>El Pacífico Norte, el Valle Central y la Zona Norte suelen tener menos lluvia y más calor. En el Caribe puede llover más de lo normal.</p></div></div>
            <div className="fact"><span className="fact-icon" aria-hidden="true">⏳</span><div><h3>Cada cuánto vuelve</h3><p>Aparece cada 2 a 7 años y dura entre 9 y 12 meses. Sus efectos van desde sequías hasta cortes de agua y pérdidas en el campo.</p></div></div>
            <div className="fact now">
              <span className="fact-icon" aria-hidden="true">📅</span>
              <div>
                <h3>Último episodio cargado</h3>
                {episode
                  ? <p><strong>{monthName(episode.start)}</strong> a <strong>{monthName(episode.end)}</strong> · {monthsBetween(episode.start, episode.end)} meses.
                    {episode.sources?.length ? <> Fuentes del IMN: {episode.sources.map((url, index) => <span key={url}>{index > 0 && ', '}<a href={url} target="_blank" rel="noreferrer">boletín {index + 1}</a></span>)}.</> : null}</p>
                  : <p className="muted">{failed ? 'No se pudieron cargar los datos del episodio.' : 'Cargando el episodio…'}</p>}
              </div>
            </div>
          </div>
        </div>
        <div className="stat-row reveal">
          <div className="stat"><strong>{years ?? '—'}</strong><span>años de datos del clima{temperature?.series.length ? ` (${temperature.series[0].year}–${temperature.series[temperature.series.length - 1].year})` : ''}</span></div>
          <div className="stat"><strong>{slope == null ? '—' : `${slope >= 0 ? '+' : '−'}${fmt(Math.abs(slope), 2)} °C`}</strong><span>de temperatura por década. {temperature ? text.significance(temperature.trend.significant) : ''}</span></div>
          <div className="stat"><strong>{episode ? `${monthsBetween(episode.start, episode.end)} meses` : '—'}</strong><span>duró el último episodio de El Niño cargado</span></div>
          <div className="stat"><strong>4</strong><span>variables en el mapa: temperatura, lluvia, humedad y UV</span></div>
        </div>
      </section>

      <section className="section band" id="advertencias" aria-labelledby="warn-title">
        <div className="section-head reveal">
          <span className="eyebrow">Lo más importante ahora</span>
          <h2 id="warn-title">Advertencias y sugerencias</h2>
          <p className="lead">Lo que dicen hoy los datos del país y los reportes de las ASADAs, ordenado de lo más serio a lo más tranquilo.</p>
        </div>
        {!snapshot && !failed && <p className="empty">Cargando las advertencias…</p>}
        {failed && <p className="empty">No se pudieron cargar los datos del clima. Igual podés abrir el mapa y volver a intentarlo.</p>}
        <div className="warning-grid reveal">
          {warnings.map(item => <article key={item.id} className={`warning card ${item.level}`}>
            <div className="warning-top"><AlertPill level={item.level} /><small>{item.kicker}</small></div>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
            {item.href && <a href={item.href} target="_blank" rel="noreferrer">Ver la fuente</a>}
          </article>)}
        </div>
        <p className="muted note reveal">{text.forecastNote} Niveles: {ALERT_ORDER.map(level => ALERT_LABEL[level]).join(' · ')}.</p>

        <div className="tips-head reveal">
          <h3>Qué podés hacer</h3>
          <button className="pill pill-ghost" onClick={() => setTipRound(round => round + 1)}>Ver otros consejos</button>
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

      <section className="section" id="datos" aria-labelledby="data-title">
        <div className="section-head reveal">
          <span className="eyebrow">Explorá el mapa</span>
          <h2 id="data-title">Tres formas de mirar el país</h2>
          <p className="lead">Cada botón te lleva directo al mapa con esa fuente de datos. Podés cambiar de una a otra cuando quieras desde la barra de arriba.</p>
        </div>
        {DATA_CARDS.map((card, index) => <article key={card.mode} className={`split data-split${index % 2 ? ' reverse' : ''}`} id={`datos-${card.mode}`}>
          <figure className="photo reveal">
            <img src={img(card.image)} alt={card.alt} loading="lazy" />
          </figure>
          <div className="data-text reveal">
            <span className="chip nasa">{card.chip}</span>
            <h3>{card.title}</h3>
            <p>{card.summary}</p>
            <ul className="facts">{card.facts.map(fact => <li key={fact}>{fact}</li>)}</ul>
            <details>
              <summary>Detalle técnico</summary>
              <p className="muted">{card.technical}</p>
            </details>
            <button className="pill pill-primary" onClick={() => openMap(card.mode)}>{card.button} <span aria-hidden="true">→</span></button>
          </div>
        </article>)}
      </section>

      <section className="cta" aria-labelledby="cta-title">
        <img src={img('costa.jpg')} alt="Playa de la costa del Pacífico de Costa Rica al atardecer" loading="lazy" />
        <div className="cta-veil" aria-hidden="true" />
        <div className="cta-inner reveal">
          <h2 id="cta-title">El clima cambia. Conocerlo ayuda a prepararnos.</h2>
          <p>Abrí el mapa, elegí tu cantón y mirá cómo han cambiado el calor y la lluvia donde vivís.</p>
          <button className="pill pill-primary hero-cta" onClick={() => openMap('grid')}>Abrir el mapa</button>
        </div>
      </section>

      <section className="section" id="fuentes" aria-labelledby="src-title">
        <div className="section-head reveal">
          <span className="eyebrow">De dónde salen los datos</span>
          <h2 id="src-title">Fuentes</h2>
        </div>
        <ul className="source-grid">
          {SOURCES.map(source => <li key={source.name} className="card reveal">
            <h3><a href={source.url} target="_blank" rel="noreferrer">{source.name}</a></h3>
            <p className="muted">{source.text}</p>
          </li>)}
        </ul>
      </section>
    </main>

    <footer className="landing-footer">
      <p><strong>El Niño en CR — Monitor Climático y Territorial.</strong> Las cifras son de reanálisis y modelos; no reemplazan los avisos oficiales del IMN, el AyA ni de tu ASADA.</p>
      <details>
        <summary>Créditos de las fotografías</summary>
        <ul>{PHOTO_CREDITS.map(photo => <li key={photo.url}><a href={photo.url} target="_blank" rel="noreferrer">{photo.file}</a> · {photo.author} · {photo.license} · Wikimedia Commons</li>)}</ul>
      </details>
    </footer>
  </div>
}
