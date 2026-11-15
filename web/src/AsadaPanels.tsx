import { flowText } from './asadas'
import { Tile } from './Bento'
import type { Operator } from './data'
import type { AsadaReport } from './data/cantonData'

const dayFormat = new Intl.DateTimeFormat('es-CR', { dateStyle: 'medium', timeZone: 'UTC' })
const day = (value: string) => dayFormat.format(new Date(`${value}T00:00:00Z`))

/** Ficha de un operador de agua elegido en el buscador: caudal vigente, afectación por El Niño y fuentes. */
export function AsadaTile({ operator, reports, close }: { operator: Operator; reports: AsadaReport[]; close: () => void }) {
  // `reports` ya viene ordenado del más reciente al más antiguo.
  const latest = reports[0]
  const flow = latest?.caudal ?? operator.caudal
  return <Tile title={operator.name} badge={<span className="chip nasa">{operator.type}</span>}>
    <p className="muted">{operator.district}, {operator.canton}, {operator.province} · {operator.area}{operator.services ? ` · ${operator.services.toLocaleString('es-CR')} servicios` : ''}</p>
    <p className="big">{flowText(flow)}<small> caudal actual</small></p>
    <p className="muted">{latest ? `Último reporte: ${day(latest.measuredAt)}.${operator.caudal !== null ? ` Valor inicial de SAGA: ${flowText(operator.caudal)}.` : ''}`
      : operator.caudal === null ? 'SAGA no tiene caudal registrado para este operador. Su administrador puede reportarlo.' : 'Valor inicial de SAGA (suma del último caudal de sus fuentes).'}</p>
    {latest && <div className="chips">
      {latest.ninoAffected ? <span className="chip nino">Afectada por El Niño</span> : <span className="chip ok">Sin afectación por El Niño</span>}
    </div>}
    {latest?.ninoAffected && <p>Localidades afectadas: {latest.localities.join(', ')}.</p>}
    {latest?.notes && <p className="muted">«{latest.notes}»</p>}
    {operator.sources.length > 0 && <details>
      <summary>Fuentes de abastecimiento ({operator.sources.length})</summary>
      <table className="source-table"><thead><tr><th>Fuente</th><th>Último caudal</th><th>Cuenca</th></tr></thead>
        <tbody>{operator.sources.map((item, index) => <tr key={`${item.name}-${index}`}><td>{item.name}</td><td>{flowText(item.caudal)}</td><td>{item.basin || '—'}</td></tr>)}</tbody></table>
    </details>}
    {reports.length > 1 && <details>
      <summary>Histórico de reportes ({reports.length})</summary>
      {reports.slice(0, 10).map(item => <p className="muted" key={item.id}>{day(item.measuredAt)} · {flowText(item.caudal)} · {item.ninoAffected ? `afectada (${item.localities.join(', ')})` : 'sin afectación'}</p>)}
    </details>}
    <button type="button" className="pill pill-ghost" onClick={close}>Cerrar ficha</button>
    <p className="muted">Caudal en L/s según SAGA (AyA). Los reportes son autorreportes de la ASADA, sin verificación independiente.</p>
  </Tile>
}

/** Operadores de agua del cantón elegido, para tocar uno y abrir su ficha. */
export function CantonOperatorsTile({ cantonName, operators, flows, selectedId, pick }: {
  cantonName: string; operators: Operator[]; flows: Map<string, { flow: number | null; affected: boolean | null }>
  selectedId: string; pick: (operator: Operator) => void
}) {
  if (!operators.length) return null
  return <Tile title={`Operadores de agua en ${cantonName}`} badge={<span className="chip">{operators.length}</span>}>
    <div className="operator-list">
      {operators.map(item => {
        const info = flows.get(item.id)
        return <button key={item.id} type="button" className={item.id === selectedId ? 'operator-row on' : 'operator-row'} onClick={() => pick(item)}>
          <span>{item.name}<small className="muted"> · {item.type} · {item.district}</small></span>
          <span>{info?.affected ? <span className="chip nino">Afectada</span> : null} {flowText(info?.flow ?? null)}</span>
        </button>
      })}
    </div>
    <p className="muted">Catálogo SAGA (AyA). Estos operadores no se dibujan en el mapa: se encuentran con el buscador.</p>
  </Tile>
}
