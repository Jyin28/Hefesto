import { useId, useState } from 'react'
import type { KeyboardEvent, PointerEvent } from 'react'
import { fmt, usable } from './analysis'
import type { Point, Range } from './analysis'

const W = 480, H = 220
const M = { top: 14, right: 14, bottom: 30, left: 52 }

function niceStep(span: number) { return span <= 12 ? 2 : span <= 25 ? 5 : 10 }

export function SeriesChart({ series, range, unit, tone, label, projection }: {
  series: Point[]; range: Range; unit: string; tone: 'water' | 'emerald'; label: string
  projection?: { year: number; value: number }[]
}) {
  const id = useId().replace(/:/g, '')
  const [active, setActive] = useState<number | null>(null)
  const inside = series.filter(point => point.year >= range[0] && point.year <= range[1])
  const valid = usable(inside)
  if (valid.length < 2) return <p className="empty" role="status">Sin datos suficientes en {range[0]}–{range[1]}. Ampliá el rango.</p>

  const extra = projection ?? []
  const years = [...inside.map(point => point.year), ...extra.map(point => point.year)]
  const x0 = Math.min(...years), x1 = Math.max(...years)
  const values = [...valid.map(point => point.value), ...extra.map(point => point.value)]
  let y0 = Math.min(...values), y1 = Math.max(...values)
  const pad = (y1 - y0) * 0.1 || Math.abs(y1) * 0.05 || 1
  y0 -= pad; y1 += pad
  const sx = (year: number) => M.left + ((year - x0) / Math.max(1, x1 - x0)) * (W - M.left - M.right)
  const sy = (value: number) => H - M.bottom - ((value - y0) / (y1 - y0)) * (H - M.top - M.bottom)

  // Línea con huecos donde falta el dato o el año está incompleto.
  let line = '', area = ''
  let run: { year: number; value: number }[] = []
  const flush = () => {
    if (run.length > 1) {
      line += run.map((point, index) => `${index ? 'L' : 'M'}${sx(point.year).toFixed(1)},${sy(point.value).toFixed(1)}`).join('')
      area += `M${sx(run[0].year).toFixed(1)},${sy(y0).toFixed(1)}` + run.map(point => `L${sx(point.year).toFixed(1)},${sy(point.value).toFixed(1)}`).join('')
        + `L${sx(run[run.length - 1].year).toFixed(1)},${sy(y0).toFixed(1)}Z`
    }
    run = []
  }
  for (const point of inside) {
    if (point.value != null && point.complete !== false) run.push({ year: point.year, value: point.value }); else flush()
  }
  flush()
  const lastObserved = valid[valid.length - 1]
  const dash = extra.length ? `M${sx(lastObserved.year).toFixed(1)},${sy(lastObserved.value).toFixed(1)}`
    + extra.map(point => `L${sx(point.year).toFixed(1)},${sy(point.value).toFixed(1)}`).join('') : ''

  const step = niceStep(x1 - x0)
  const xTicks: number[] = []
  for (let year = Math.ceil(x0 / step) * step; year <= x1; year += step) xTicks.push(year)
  const yTicks = Array.from({ length: 4 }, (_, index) => y0 + ((y1 - y0) * (index + 0.5)) / 4)
  const [c1, c2] = tone === 'water' ? ['#38BDF8', '#06B6D4'] : ['#10B981', '#0EA5E9']

  const selectable = [...valid.map(point => ({ ...point, projected: false })), ...extra.map(point => ({ ...point, projected: true }))]
  const current = active == null ? null : selectable.find(point => point.year === active) ?? null
  function nearest(event: PointerEvent<SVGSVGElement>) {
    const box = event.currentTarget.getBoundingClientRect()
    const year = x0 + (((event.clientX - box.left) / box.width) * W - M.left) / (W - M.left - M.right) * (x1 - x0)
    let best = selectable[0]
    for (const point of selectable) if (Math.abs(point.year - year) < Math.abs(best.year - year)) best = point
    setActive(best.year)
  }
  function onKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const index = current ? selectable.indexOf(current) : selectable.length - 1
    const next = Math.min(selectable.length - 1, Math.max(0, index + (event.key === 'ArrowRight' ? 1 : -1)))
    setActive(selectable[next].year)
  }
  const digits = Math.abs(y1) >= 100 ? 0 : 1

  return <div className="series-chart" tabIndex={0} onKeyDown={onKey} onBlur={() => setActive(null)}
    aria-label={`${label}, ${range[0]} a ${range[1]}. Usá las flechas izquierda y derecha para leer cada año.`}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${label} (${unit}), ${range[0]}–${range[1]}`}
      onPointerMove={nearest} onPointerLeave={() => setActive(null)}>
      <defs>
        <linearGradient id={`${id}-area`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={c1} stopOpacity=".55" /><stop offset="100%" stopColor={c2} stopOpacity=".04" />
        </linearGradient>
        <linearGradient id={`${id}-line`} x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor={c1} /><stop offset="100%" stopColor={c2} /></linearGradient>
      </defs>
      {yTicks.map(tick => <g key={tick}>
        <line x1={M.left} x2={W - M.right} y1={sy(tick)} y2={sy(tick)} className="chart-grid" />
        <text x={M.left - 6} y={sy(tick) + 3} textAnchor="end" className="chart-tick">{fmt(tick, digits)}</text>
      </g>)}
      {xTicks.map(tick => <text key={tick} x={sx(tick)} y={H - 10} textAnchor="middle" className="chart-tick">{tick}</text>)}
      <text x={12} y={M.top + 2} className="chart-tick" transform={`rotate(-90 12 ${M.top + 2})`} textAnchor="end">{unit}</text>
      <path d={area} fill={`url(#${id}-area)`} />
      <path d={line} fill="none" stroke={`url(#${id}-line)`} strokeWidth="2.6" strokeLinejoin="round" strokeLinecap="round" />
      {dash && <>
        <line x1={sx(lastObserved.year)} x2={sx(lastObserved.year)} y1={M.top} y2={H - M.bottom} className="chart-divider" />
        <path d={dash} fill="none" stroke={c2} strokeWidth="2.2" strokeDasharray="5 4" opacity=".9" />
      </>}
      {current && <g>
        <line x1={sx(current.year)} x2={sx(current.year)} y1={M.top} y2={H - M.bottom} className="chart-cursor" />
        <circle cx={sx(current.year)} cy={sy(current.value)} r="5" fill="#fff" stroke={c2} strokeWidth="2.5" />
      </g>}
    </svg>
    <p className="chart-readout" aria-live="polite">{current
      ? <>{current.year}: <strong>{fmt(current.value, digits === 0 ? 0 : 2)} {unit}</strong>{current.projected ? ' · proyección de tendencia' : ''}</>
      : <span className="muted">Pasá el cursor o usá las flechas para leer un año.{extra.length ? ' Línea punteada: proyección de tendencia.' : ''}</span>}</p>
  </div>
}
