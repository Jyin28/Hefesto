import type { EnsoBlock, ForecastRow, RainAnalogMonth } from './predictionsData'
import { monthLong, monthOnly, monthShort, num, signed } from './predictionsData'

/** Gráficos SVG de la página «Predicciones». Se animan cuando su contenedor `.reveal` entra en pantalla (ver style.css, `.pc-*`). */

const monthIndex = (label: string) => { const [year, month] = label.split('-').map(Number); return year * 12 + month - 1 }
const delay = (ms: number) => ({ animationDelay: `${ms}ms` })

// ---------------------------------------------------------------- El Niño

const AXIS_START = '2025-09'
const AXIS_END = '2027-12'

/**
 * RONI observado (línea) y, debajo, el episodio en curso y los rangos esperados de pico y de fin.
 * Los rangos salen de episodios fuertes anteriores: no se dibuja ninguna proyección del RONI.
 */
export function EnsoTimeline({ enso }: { enso: EnsoBlock }) {
  const W = 760, H = 330, L = 46, R = 22, T = 14, plot = 150
  const first = monthIndex(AXIS_START), last = monthIndex(AXIS_END)
  const x = (label: string) => L + ((monthIndex(label) - first) / (last - first)) * (W - L - R)
  const y = (value: number) => T + ((2.5 - value) / 4) * plot
  const series = enso.series.filter(point => point.month >= AXIS_START)
  const path = (points: { month: string; value: number }[]) => points.map((p, i) => `${i ? 'L' : 'M'}${x(p.month).toFixed(1)},${y(p.value).toFixed(1)}`).join(' ')
  const active = enso.status === 'active' && enso.start ? series.filter(point => point.month >= enso.start!) : []
  const ticks = Array.from({ length: last - first + 1 }, (_, i) => i).filter(i => i % 3 === 0)
    .map(i => { const year = Math.floor((first + i) / 12), month = (first + i) % 12 + 1; return `${year}-${String(month).padStart(2, '0')}` })
  const tracks = { episode: T + plot + 52, peak: T + plot + 90, end: T + plot + 128 }
  const bar = (from: string, to: string) => ({ x: x(from) - 6, width: Math.max(x(to) - x(from) + 12, 12) })
  const analog = enso.analog
  const latest = enso.latest

  return <svg className="pc" viewBox={`0 0 ${W} ${H}`} role="img"
    aria-label={`Línea de tiempo de El Niño. RONI de ${num(latest.value)} en ${monthLong(latest.month)}.${enso.start ? ` Episodio en curso desde ${monthLong(enso.start)}.` : ''}`}>
    <defs>
      <pattern id="pc-hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="7" height="7" fill="#fed7aa" /><line x1="0" y1="0" x2="0" y2="7" stroke="#f97316" strokeWidth="3" />
      </pattern>
    </defs>
    {ticks.map(label => <g key={label}>
      <line className="pc-grid" x1={x(label)} x2={x(label)} y1={T} y2={tracks.end + 24} />
      <text className="pc-axis" x={x(label)} y={T + plot + 18} textAnchor="middle">{monthOnly(label)} {label.slice(2, 4)}</text>
    </g>)}
    {[-1, 0, 1, 2].map(value => <g key={value}>
      <line className="pc-grid" x1={L} x2={W - R} y1={y(value)} y2={y(value)} />
      <text className="pc-axis" x={L - 8} y={y(value) + 4} textAnchor="end">{value}</text>
    </g>)}
    <line className="pc-threshold" x1={L} x2={W - R} y1={y(0.5)} y2={y(0.5)} />
    <text className="pc-note" x={W - R} y={y(0.5) - 6} textAnchor="end">0,5 = umbral de El Niño</text>
    <path className="pc-line pc-draw" d={path(series)} pathLength={1} style={delay(150)} />
    {active.length > 1 && <path className="pc-line hot pc-draw" d={path(active)} pathLength={1} style={delay(700)} />}
    {series.length > 0 && <g className="pc-pop" style={delay(1500)}>
      <circle cx={x(latest.month)} cy={y(latest.value)} r={6} className="pc-dot hot" />
      <text className="pc-label strong" x={x(latest.month) - 10} y={y(latest.value) - 6} textAnchor="end">RONI {num(latest.value)} · {monthShort(latest.month)}</text>
    </g>}
    <line className="pc-now" x1={x(latest.month)} x2={x(latest.month)} y1={T} y2={tracks.end + 24} />

    {enso.start && <g>
      <text className="pc-label" x={bar(enso.start, latest.month).x} y={tracks.episode - 7}>Episodio en curso · {enso.category}</text>
      <rect className="pc-bar hot pc-grow-x" style={delay(900)} rx={7} height={16} y={tracks.episode} {...bar(enso.start, latest.month)}>
        <title>{`Desde ${monthLong(enso.start)} (${enso.months_so_far} meses con RONI ≥ 0,5)`}</title>
      </rect>
    </g>}
    {analog?.peak_window && <g>
      <text className="pc-label" x={bar(analog.peak_window.earliest, analog.peak_window.latest).x} y={tracks.peak - 7}>
        Pico esperado · {monthShort(analog.peak_window.earliest)} a {monthShort(analog.peak_window.latest)}
      </text>
      <rect className="pc-bar soft pc-grow-x" style={delay(1200)} rx={7} height={16} y={tracks.peak} {...bar(analog.peak_window.earliest, analog.peak_window.latest)}>
        <title>{`Pico típico: ${monthLong(analog.peak_window.typical)} (${analog.peak_window.n} episodios fuertes anteriores)`}</title>
      </rect>
      <rect className="pc-mark pc-pop" style={delay(1900)} x={x(analog.peak_window.typical) - 5} y={tracks.peak - 2} width={10} height={20} rx={3} />
    </g>}
    {analog && <g>
      <text className="pc-label" x={bar(analog.end_window.earliest, analog.end_window.latest).x} y={tracks.end - 7}>
        Fin esperado · {monthShort(analog.end_window.earliest)} a {monthShort(analog.end_window.latest)}
      </text>
      <rect className="pc-bar hatch pc-grow-x" style={delay(1500)} rx={7} height={16} y={tracks.end} {...bar(analog.end_window.earliest, analog.end_window.latest)} fill="url(#pc-hatch)">
        <title>{`Fin típico: ${monthLong(analog.end_window.typical)} (${analog.n} episodios fuertes anteriores)`}</title>
      </rect>
      <rect className="pc-mark pc-pop" style={delay(2200)} x={x(analog.end_window.typical) - 5} y={tracks.end - 2} width={10} height={20} rx={3} />
    </g>}
  </svg>
}

// ---------------------------------------------------------------- Temperatura

/** Banda de lo normal (P10–P90 de 1991–2020), estimación experimental y su banda de 90 % por mes. */
export function TemperatureChart({ rows, unit }: { rows: ForecastRow[]; unit: string }) {
  const W = 760, H = 336, L = 52, R = 18, T = 18, B = 62
  const values = rows.flatMap(row => [row.reference.p10, row.reference.p90, row.lower90, row.upper90].filter((v): v is number => v !== null))
  const spread = Math.max(...values) - Math.min(...values)
  const unitStep = spread > 4 ? 1 : 0.5
  const lo = Math.floor((Math.min(...values) - 0.2) / unitStep) * unitStep, hi = Math.ceil((Math.max(...values) + 0.2) / unitStep) * unitStep
  const y = (value: number) => T + ((hi - value) / (hi - lo)) * (H - T - B)
  const step = (W - L - R) / rows.length
  const x = (i: number) => L + step * (i + 0.5)
  const ticks = Array.from({ length: Math.round((hi - lo) / unitStep) + 1 }, (_, i) => lo + i * unitStep)
  const band = `${rows.map((r, i) => `${i ? 'L' : 'M'}${x(i)},${y(r.reference.p90)}`).join(' ')} ${[...rows].reverse().map((r, i) => `L${x(rows.length - 1 - i)},${y(r.reference.p10)}`).join(' ')} Z`
  const mean = rows.map((r, i) => `${i ? 'L' : 'M'}${x(i)},${y(r.reference.mean)}`).join(' ')
  const forecast = rows.map((r, i) => ({ r, i })).filter(item => item.r.estimate !== null)
  const line = forecast.map((item, k) => `${k ? 'L' : 'M'}${x(item.i)},${y(item.r.estimate!)}`).join(' ')

  return <svg className="pc" viewBox={`0 0 ${W} ${H}`} role="img"
    aria-label={`Temperatura media mensual estimada frente a lo normal, ${rows[0] ? monthLong(rows[0].target_month) : ''} en adelante. Ver la tabla de abajo.`}>
    {ticks.map(value => <g key={value}>
      <line className="pc-grid" x1={L} x2={W - R} y1={y(value)} y2={y(value)} />
      <text className="pc-axis" x={L - 8} y={y(value) + 4} textAnchor="end">{num(value)}</text>
    </g>)}
    <text className="pc-note" x={L} y={12}>{unit}</text>
    <path className="pc-band pc-fade" d={band} />
    <path className="pc-mean pc-draw" d={mean} pathLength={1} style={delay(300)} />
    {rows.map((row, i) => <g key={row.target_month}>
      <text className={row.estimate === null ? 'pc-axis dim' : 'pc-axis strong'} x={x(i)} y={H - B + 20} textAnchor="middle">{monthOnly(row.target_month)}</text>
      <text className="pc-axis dim" x={x(i)} y={H - B + 35} textAnchor="middle">{row.target_month.slice(0, 4)}</text>
      {row.estimate === null && <text className="pc-axis dim" x={x(i)} y={H - B + 51} textAnchor="middle">sin pronóstico</text>}
    </g>)}
    {forecast.map(({ r, i }, k) => <g key={r.target_month}>
      <rect className="pc-whisker pc-grow-y" style={delay(900 + k * 250)} x={x(i) - 11} width={22} rx={11} y={y(r.upper90!)} height={y(r.lower90!) - y(r.upper90!)}>
        <title>{`${monthLong(r.target_month)}: banda de 90 %, ${num(r.lower90!)} a ${num(r.upper90!)}`}</title>
      </rect>
    </g>)}
    {line && <path className="pc-line amber pc-draw" d={line} pathLength={1} style={delay(800)} />}
    {forecast.map(({ r, i }, k) => <g key={`d${r.target_month}`} className="pc-pop" style={delay(1100 + k * 250)}>
      <circle className="pc-dot amber" cx={x(i)} cy={y(r.estimate!)} r={6.5}>
        <title>{`${monthLong(r.target_month)}: ${num(r.estimate!)} ${unit} (normal ${num(r.reference.mean)})`}</title>
      </circle>
      <text className="pc-label strong" x={x(i)} y={y(r.upper90!) - 8} textAnchor="middle">{num(r.estimate!)}</text>
    </g>)}
  </svg>
}

// ---------------------------------------------------------------- Lluvia

/** Rango de lo normal (P10–P90) y media por mes; el rombo marca lo que llovió en promedio en años parecidos de El Niño. */
export function RainChart({ rows, analog }: { rows: ForecastRow[]; analog: RainAnalogMonth[] }) {
  const W = 760, H = 320, L = 52, R = 18, T = 26, B = 46
  const peak = Math.max(...rows.map(r => r.reference.p90))
  const unitStep = [25, 50, 100, 200].find(candidate => peak / candidate <= 6) ?? 200
  const top = Math.ceil((peak * 1.04) / unitStep) * unitStep
  const y = (value: number) => T + ((top - value) / top) * (H - T - B)
  const step = (W - L - R) / rows.length
  const x = (i: number) => L + step * (i + 0.5)
  const ticks = Array.from({ length: Math.round(top / unitStep) + 1 }, (_, i) => i * unitStep)
  const analogOf = (month: string) => analog.find(item => item.month === month)

  return <svg className="pc" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Lluvia mensual normal y lluvia en años parecidos de El Niño. Ver la tabla de abajo.">
    {ticks.map(value => <g key={value}>
      <line className="pc-grid" x1={L} x2={W - R} y1={y(value)} y2={y(value)} />
      <text className="pc-axis" x={L - 8} y={y(value) + 4} textAnchor="end">{num(value, 0)}</text>
    </g>)}
    <text className="pc-note" x={L} y={14}>mm por mes</text>
    {rows.map((row, i) => {
      const found = analogOf(row.target_month)
      const dry = found && found.anomaly_pct < -5
      return <g key={row.target_month}>
        <rect className="pc-range pc-grow-y" style={delay(150 + i * 110)} x={x(i) - 17} width={34} rx={9} y={y(row.reference.p90)} height={y(row.reference.p10) - y(row.reference.p90)}>
          <title>{`${monthLong(row.target_month)}: normal ${num(row.reference.mean, 0)} mm; en 8 de cada 10 años entre ${num(row.reference.p10, 0)} y ${num(row.reference.p90, 0)} mm`}</title>
        </rect>
        <line className="pc-tick pc-pop" style={delay(450 + i * 110)} x1={x(i) - 22} x2={x(i) + 22} y1={y(row.reference.mean)} y2={y(row.reference.mean)} />
        {found && <g className="pc-pop" style={delay(900 + i * 110)}>
          <path className={dry ? 'pc-diamond dry' : 'pc-diamond'} d={`M${x(i)},${y(found.mean_mm) - 9} L${x(i) + 9},${y(found.mean_mm)} L${x(i)},${y(found.mean_mm) + 9} L${x(i) - 9},${y(found.mean_mm)} Z`}>
            <title>{`${monthLong(row.target_month)}: en ${found.n_years} años parecidos llovió ${num(found.mean_mm, 0)} mm en promedio (${signed(found.anomaly_pct, 0)} % frente a lo normal)`}</title>
          </path>
          <text className="pc-label strong" x={x(i) + 24} y={y(found.mean_mm) + 4}>{signed(found.anomaly_pct, 0)} %</text>
        </g>}
        <text className="pc-axis strong" x={x(i)} y={H - B + 20} textAnchor="middle">{monthOnly(row.target_month)}</text>
        <text className="pc-axis dim" x={x(i)} y={H - B + 35} textAnchor="middle">{row.target_month.slice(0, 4)}</text>
      </g>
    })}
  </svg>
}
