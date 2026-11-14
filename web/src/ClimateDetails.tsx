import type { ReactNode } from 'react'
import { copy } from './copy'
import type { Level } from './copy'
import type { Cell, Climate, Local } from './data'

const numberFormat = new Intl.NumberFormat('es-CR', { maximumSignificantDigits: 4 })
export const number = (value: number | null | undefined) => value == null ? 'Sin dato' : numberFormat.format(value)

function CellMap({ cells, field, title, unit, low, high, selected, choose }: {
  cells: Cell[]
  field: 'window_a_mean' | 'window_b_mean' | 'enso_mean_anomaly' | 'enso_mean_vs_neutral' | 'long_term_slope'
  title: string; unit: string; low: number; high: number; selected: string
  choose: (id: string) => void
}) {
  const west = Math.min(...cells.map(cell => cell.bbox[0]))
  const south = Math.min(...cells.map(cell => cell.bbox[1]))
  const east = Math.max(...cells.map(cell => cell.bbox[2]))
  const north = Math.max(...cells.map(cell => cell.bbox[3]))
  return <figure className="grid-map">
    <figcaption>{title}</figcaption>
    <svg role="group" aria-label={title} viewBox={`${west * 100} ${-north * 100} ${(east - west) * 100} ${(north - south) * 100}`}>
      {cells.map(cell => {
        const [left, bottom, right, top] = cell.bbox
        const value = cell[field]
        const share = high === low ? 0.5 : ((value ?? low) - low) / (high - low)
        const significant = field === 'long_term_slope' && cell.significant === true
        const label = `${cell.id} · ${number(value)} ${unit}${significant ? ' · Evidencia al 5 %' : ''}`
        return <rect key={cell.id} x={left * 100} y={-top * 100} width={(right - left) * 100}
          height={(top - bottom) * 100} fill={value == null ? '#d1d5db' : `hsl(${200 - 172 * share} 65% 57%)`}
          stroke={selected === cell.id || significant ? '#112526' : 'white'}
          strokeWidth={selected === cell.id || significant ? 2 : 0.7}
          role="button" tabIndex={0} aria-pressed={selected === cell.id} aria-label={label}
          onClick={() => choose(cell.id)} onKeyDown={event => {
            if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(cell.id) }
          }}><title>{label}</title></rect>
      })}
    </svg>
  </figure>
}

export function WaterDetails({ local, canton }: { local: Local; canton: string }) {
  const coverage = local.waterCoverage?.filter(row => row.cantonCode === canton) ?? []
  const distribution = local.distribution?.filter(row => row.cantonCode === canton) ?? []
  const source = (id: string) => {
    const item = local.sources?.[id]
    return item ? <a href={item.url}>{item.label}</a> : null
  }
  return <div className="water-details">
    <h3>Cobertura del servicio de agua</h3>
    {coverage.length ? coverage.map(row => <p key={row.sourceId}>
      <strong>{row.value} {row.unit}</strong> · {row.indicator} ({row.year})<br />
      {row.geography}, {row.geographyLevel} · {row.numerator.toLocaleString('es-CR')} de {row.denominator.toLocaleString('es-CR')} personas. {source(row.sourceId)}
    </p>) : <p>Sin indicador cantonal verificado.</p>}
    {distribution.map(row => <p key={row.sourceId}>
      <strong>{row.value} {row.unit}</strong> · {row.indicator} ({row.year}). {row.limitation} {source(row.sourceId)}
    </p>)}
    <p className="muted">Sin series de horas efectivas o volúmenes para este cantón.</p>
  </div>
}

export function ClimateDetails({ data, unit, selected, choose, level = 'tecnico' }: {
  data: Climate; unit: string; selected: string; choose: (id: string) => void; level?: Level
}) {
  const { cells, comparison, evidence, enso, forecast } = data
  const values = cells.flatMap(cell => [cell.window_a_mean, cell.window_b_mean])
    .filter((value): value is number => value != null)
  const low = values.length ? Math.min(...values) : 0
  const high = values.length ? Math.max(...values) : 1
  const mapProps = { cells, low, high, unit, selected, choose }
  const eventField = enso.status === 'ok' ? 'enso_mean_vs_neutral' : 'enso_mean_anomaly'
  const extent = Math.max(...cells.map(cell => Math.abs(cell[eventField] ?? 0)), 0) || 1
  const slopeExtent = Math.max(...cells.map(cell => Math.abs(cell.long_term_slope ?? 0)), 0) || 1
  const simple = level === 'basico'
  const technical = (children: ReactNode) => simple
    ? <details><summary>{copy.basico.technicalDetail}</summary>{children}</details> : <>{children}</>
  return <>
    {comparison && <>
      {simple
        ? <p>Entre el primer y el segundo período, el promedio cambió <strong>{number(comparison.mean_diff_b_minus_a)} {unit}</strong>.</p>
        : <>
          <p title={copy.tecnico.tipSlope}>Cambio de promedio B − A · <strong>{number(comparison.mean_diff_b_minus_a)} {unit}</strong></p>
          <p title={copy.tecnico.tipSlope}>Cambio de pendiente B − A · <strong>{number(comparison.slope_diff_b_minus_a)} {unit}/década</strong></p>
        </>}
      {cells.length > 0 && <>
        <div className="grid-maps">
          <CellMap {...mapProps} field="window_a_mean" title={`A · ${comparison.window_a.start_year}–${comparison.window_a.end_year}`} />
          <CellMap {...mapProps} field="window_b_mean" title={`B · ${comparison.window_b.start_year}–${comparison.window_b.end_year}`} />
        </div>
        <p className="muted">Escala compartida de {number(low)} a {number(high)} {unit}. Gris indica sin dato.</p>
      </>}
    </>}
    {technical(<>
    <details>
      <summary>Incertidumbre y comprobación estadística</summary>
      <p>IC individual del 95 % · {number(data.trend.ci_low)} a {number(data.trend.ci_high)} {unit}/década</p>
      <p>p ajustado BY (OLS/HAC) · {number(data.trend.p_adjusted)}</p>
      <p>Pendiente Sen · {number(evidence.mann_kendall.slope_per_decade)} {unit}/década.
        p ajustado BY (Mann–Kendall) · {number(evidence.mann_kendall.p_adjusted)}</p>
      {data.methods_disagree && <p>Los métodos difieren en la conclusión al 5 %.</p>}
      {cells.length > 0 && <>
        <CellMap {...mapProps} field="long_term_slope" title="Pendiente de largo plazo por celda"
          unit={`${unit}/década`} low={-slopeExtent} high={slopeExtent} />
        <p>Contorno oscuro en celdas con evidencia al 5 % tras el ajuste BY. La celda seleccionada también se resalta.</p>
      </>}
    </details>
    {enso.episode && <details>
      <summary>El Niño · {enso.episode.start} a {enso.episode.end}</summary>
      <p>Climatología 1981–2010 por mes calendario. Valores en {enso.unit}.</p>
      {enso.status === 'neutral_unverified' && <p>Período neutral anterior pendiente de verificación.</p>}
      {enso.neutral_window && <p>Referencia neutral documentada · {enso.neutral_window.join(' a ')}</p>}
      <table><thead><tr><th>Mes</th><th>Valor</th><th>Climatología</th><th>Anomalía</th>
        {enso.neutral_window && <><th>Neutral</th><th>Diferencia</th></>}</tr></thead>
        <tbody>{enso.months.map(month => <tr key={month.date}><td>{month.date}</td>
          <td>{number(month.value)}</td><td>{number(month.normal)}</td><td>{number(month.anomaly)}</td>
          {enso.neutral_window && <><td>{number(month.neutral)}</td><td>{number(month.vs_neutral)}</td></>}</tr>)}</tbody>
      </table>
      {cells.length > 0 && <CellMap {...mapProps} unit={enso.unit ?? unit} low={-extent} high={extent}
        field={eventField} title={enso.status === 'ok' ? 'Diferencia media frente al período neutral' : 'Anomalía mensual media'} />}
      {enso.episode.sources.map((url, index) => <p key={url}><a href={url}>Boletín del IMN {index + 1}</a></p>)}
      {enso.neutral_sources?.map((url, index) => <p key={url}><a href={url}>Referencia neutral del IMN {index + 1}</a></p>)}
    </details>}
    <details>
      <summary>Pronóstico local experimental</summary>
      {forecast.status === 'local_data_pending'
        ? <p>{forecast.message} <a href={forecast.source_url}>Datos del IMN</a></p>
        : forecast.status === 'station_data_invalid' ? <p>{forecast.message}</p>
        : <p>Mes objetivo {forecast.target ?? 'sin dato'}. Pronóstico {number(forecast.forecast)} {forecast.unit}.
          MAE del modelo {number(forecast.model_mae)} y MAE de climatología {number(forecast.baseline_mae)}.</p>}
    </details>
    </>)}
    {data.limitations.map(text => <p className="muted" key={text}>{text}</p>)}
  </>
}
