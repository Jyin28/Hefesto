import type { ReactNode } from 'react'
import { confidenceLabel, fmt, mean, ols, usable } from './analysis'
import type { Confidence, Point, Range } from './analysis'
import { copy } from './copy'
import type { Level } from './copy'
import type { Variable } from './data'
import { SeriesChart } from './SeriesChart'

export function Tile({ title, badge, span = 2, tip, children }: {
  title: string; badge?: ReactNode; span?: 1 | 2; tip?: string; children: ReactNode
}) {
  return <section className={`tile span-${span}`} aria-label={title} title={tip}>
    <header className="tile-head"><h3>{title}</h3>{badge}</header>
    {children}
  </section>
}

export function ChartTile({ variable, level, series, range, projection, caption }: {
  variable: Variable; level: Level; series: Point[]; range: Range
  projection?: { year: number; value: number }[]; caption?: string
}) {
  const text = copy[level]
  return <Tile title={text.variableTitle[variable]} tip={text.sectionTip[variable === 'T2M' ? 'temp' : 'precip']}>
    <SeriesChart series={series} range={range} unit={text.unit[variable]} tone={variable === 'T2M' ? 'emerald' : 'water'}
      label={text.variableTitle[variable]} projection={projection} />
    {caption && <p className="muted">{caption}</p>}
  </Tile>
}

/** Promedio y pendiente descriptiva del rango elegido. */
export function StatTiles({ variable, level, series, range }: { variable: Variable; level: Level; series: Point[]; range: Range }) {
  const text = copy[level]
  const points = usable(series, range)
  const average = mean(points.map(point => point.value))
  const fit = ols(points)
  const unit = text.unit[variable]
  const digits = variable === 'T2M' ? 2 : 0
  return <>
    <Tile title={level === 'tecnico' ? 'Media del rango' : 'Promedio del rango'} span={1} tip={text.tipRange}>
      <p className="big">{average == null ? 'Sin dato' : fmt(average, digits)}<small> {unit}</small></p>
      <p className="muted">{range[0]}–{range[1]} · {points.length} años</p>
    </Tile>
    <Tile title={level === 'tecnico' ? 'Pendiente del rango' : 'Cambio cada 10 años'} span={1} tip={text.tipSlope}>
      <p className="big">{fit ? `${fit.slope >= 0 ? '+' : ''}${fmt(fit.slope * 10, digits)}` : 'Sin dato'}<small> {unit}</small></p>
      <p className="muted">{level === 'tecnico' ? 'OLS simple, descriptiva' : 'Calculado con los años elegidos'}</p>
    </Tile>
  </>
}

function Meter({ label, value, text, sub, tip }: { label: string; value: number; text: string; sub: string; tip: string }) {
  const percent = Math.round(Math.max(0, Math.min(1, value)) * 100)
  return <div className="meter" title={tip}>
    <div className="meter-row"><span>{label}</span><strong>{text}</strong></div>
    <div className="meter-track" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-valuetext={text}>
      <div className="meter-fill" style={{ width: `${percent}%` }} />
    </div>
    <p className="muted">{sub}</p>
  </div>
}

const CONFIDENCE_STEPS: Confidence[] = ['baja', 'media', 'alta']

export function QualityTile({ level, hasData, regionName, coverage, grid, continuity, range, stations, confidence }: {
  level: Level; hasData: boolean; regionName?: string
  coverage: { withData: number; total: number; pct: number }; grid: { withData: number; total: number }
  continuity: { valid: number; total: number; pct: number }; range: Range
  stations: { count: number; note: string }; confidence: Confidence
}) {
  const tech = level === 'tecnico'
  return <Tile title="Calidad, Continuidad y Cobertura">
    {!hasData && <p className="empty">Esta zona todavía no tiene datos NASA POWER asociados: no hay indicadores de calidad que mostrar.</p>}
    <Meter label={tech ? 'Cobertura espacial (malla 0,5° × 0,625°)' : 'Cobertura del mapa'} value={hasData ? coverage.pct : 0}
      text={hasData ? `${fmt(coverage.pct * 100, 0)} %` : 'Sin datos'}
      sub={hasData ? `${coverage.withData} de ${coverage.total} cuadros con datos en ${regionName ?? 'la zona'} · país: ${grid.withData} de ${grid.total} cuadros` : 'Sin cuadros asociados'}
      tip="Parte de los cuadros de la cuadrícula NASA POWER de la zona que tienen serie de datos." />
    <Meter label={tech ? `Continuidad temporal ${range[0]}–${range[1]}` : 'Años con datos completos'} value={hasData ? continuity.pct : 0}
      text={hasData ? `${fmt(continuity.pct * 100, 0)} %` : 'Sin datos'}
      sub={hasData ? `${continuity.valid} de ${continuity.total} años con los 12 meses válidos` : 'Sin serie'}
      tip="Años del rango elegido con valor y con los 12 meses válidos." />
    <div className="meter-row" title="Cuántas estaciones locales validan la serie de la malla.">
      <span>Estaciones locales vinculadas</span>
      <span className={`pill-count${stations.count ? ' on' : ''}`}>{stations.count}</span>
    </div>
    <p className="muted">{stations.note}</p>
    <div className="meter-row"><span>Nivel de confianza</span><strong>{confidenceLabel(confidence)}</strong></div>
    <div className="steps" role="img" aria-label={`Confianza ${confidenceLabel(confidence)}`}>
      {CONFIDENCE_STEPS.map(step => <span key={step} className={confidence === step ? `step on ${step}` : 'step'}>{step[0].toUpperCase() + step.slice(1)}</span>)}
    </div>
    <p className="muted">{copy[level].confidenceRule}</p>
  </Tile>
}

export function SynthesisTile({ level, paragraphs }: { level: Level; paragraphs: string[] }) {
  return <Tile title="Análisis de Experto (IA)" badge={<span className="badge-ai" title={copy[level].aiNote}>Síntesis IA</span>}>
    <div className="synthesis" aria-live="polite">{paragraphs.map(item => <p key={item}>{item}</p>)}</div>
    <p className="muted">{copy[level].aiNote}</p>
  </Tile>
}
