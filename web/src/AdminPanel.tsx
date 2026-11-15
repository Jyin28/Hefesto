import { useState } from 'react'
import type { ChangeEvent, FormEvent, KeyboardEvent } from 'react'
import { currentFlow, flowText, latestReports } from './asadas'
import type { Session } from './auth'
import { Tile } from './Bento'
import type { Canton, Operator } from './data'
import type { CantonData } from './data/cantonData'
import { MAX_CHARS, parseLocalData } from './localData'
import type { ParseResult } from './localData'
import { MAX_FLOW, MAX_LOCALITIES, MAX_LOCALITY, MAX_NOTES, addAsadaReport, addRecords, removeAsadaReport, removeRecords, resetCantonData, today } from './store'

const SAMPLE = `canton,variable,fecha,valor,estacion
El Guarco,temperatura,2024-01,19.8,Estación de ejemplo
El Guarco,precipitacion,2024-01,85,Estación de ejemplo`


/** Acepta coma o punto decimal; devuelve null si no es un número. */
const parseFlow = (raw: string) => {
  const value = Number(raw.trim().replace(',', '.'))
  return raw.trim() !== '' && Number.isFinite(value) ? value : null
}

export function AdminPanel({ session, asada, choices, data, resolveCanton, notify }: {
  session: Session; asada?: Operator; choices: Map<string, Canton>; data: CantonData
  resolveCanton: (raw: string) => string | null; notify: (message: string) => void
}) {
  const nameOf = (code: string) => choices.get(code)?.name ?? code
  const mine = data.reports.filter(item => item.asadaId === session.asadaId)
    .sort((a, b) => b.measuredAt.localeCompare(a.measuredAt) || b.createdAt.localeCompare(a.createdAt))
  const flow = asada ? currentFlow(asada, latestReports(data.reports)) : null

  const [caudal, setCaudal] = useState('')
  const [measuredAt, setMeasuredAt] = useState(today)
  const [nino, setNino] = useState<'si' | 'no' | ''>('')
  const [localities, setLocalities] = useState<string[]>([])
  const [localityText, setLocalityText] = useState('')
  const [notes, setNotes] = useState('')
  const [errors, setErrors] = useState<string[]>([])

  const [text, setText] = useState('')
  const [parsed, setParsed] = useState<ParseResult | null>(null)

  function addLocality(raw: string) {
    const items = raw.split(',').map(item => item.trim().slice(0, MAX_LOCALITY)).filter(Boolean)
    if (!items.length) return localities
    const next = [...new Set([...localities, ...items])].slice(0, MAX_LOCALITIES)
    setLocalities(next)
    setLocalityText('')
    return next
  }

  function onLocalityKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' || event.key === ',') { event.preventDefault(); addLocality(localityText) }
    else if (event.key === 'Backspace' && !localityText && localities.length) setLocalities(localities.slice(0, -1))
  }

  function saveReport(event: FormEvent) {
    event.preventDefault()
    if (!asada) return
    const found: string[] = []
    const value = parseFlow(caudal)
    if (value === null) found.push('El histórico de caudal es obligatorio y debe ser un número.')
    else if (value <= 0 || value > MAX_FLOW) found.push(`El caudal debe ser mayor que 0 y no pasar de ${MAX_FLOW.toLocaleString('es-CR')} L/s.`)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(measuredAt)) found.push('Indicá la fecha de la medición.')
    else if (measuredAt > today()) found.push('La fecha de la medición no puede ser futura.')
    if (!nino) found.push('Indicá si El Niño afectó a la ASADA (Sí o No).')
    const places = nino === 'si' ? addLocality(localityText) : []
    if (nino === 'si' && !places.length) found.push('Si hubo afectación, indicá al menos una localidad afectada dentro de la ASADA.')
    setErrors(found)
    if (found.length || value === null) return
    const result = addAsadaReport({
      asadaId: session.asadaId, cantonCode: asada.cantonCode, caudal: value, measuredAt, ninoAffected: nino === 'si',
      localities: places, notes: notes.trim(), createdBy: session.username, organization: session.organization,
    }, session.asadaId)
    if (result === 'forbidden' || result === 'invalid') { setErrors(['No se pudo guardar el reporte: revisá los datos.']); return }
    setCaudal(''); setNino(''); setLocalities([]); setLocalityText(''); setNotes('')
    notify(result === 'saved'
      ? `Reporte guardado: el caudal de ${asada.name} ahora es ${flowText(value)}. Ya se ve en el mapa y en el buscador.`
      : 'Reporte guardado, pero este navegador no pudo almacenarlo: se perderá al recargar.')
  }

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (file.size > MAX_CHARS) { setParsed({ records: [], rejected: [], total: 0, error: 'El archivo supera 1 MB. Dividilo en partes.' }); return }
    const content = await file.text()
    setText(content)
    setParsed(parseLocalData(content, resolveCanton))
  }

  function saveRecords() {
    if (!parsed?.records.length) return
    const saved = addRecords(parsed.records.map(item => ({ ...item, source: session.username })))
    notify(saved
      ? `${parsed.records.length} registros locales guardados. Ya cuentan en Calidad y en el Análisis de Experto.`
      : 'Los registros se cargaron, pero este navegador no pudo guardarlos: se perderán al recargar.')
    setParsed(null)
    setText('')
  }

  // Los registros se agrupan por cantón y variable para poder borrarlos por grupo.
  const groups = new Map<string, { code: string; variable: string; ids: Set<string>; from: string; to: string }>()
  for (const record of data.records) {
    const key = `${record.cantonCode}|${record.variable}`
    const group = groups.get(key) ?? { code: record.cantonCode, variable: record.variable, ids: new Set<string>(), from: record.date, to: record.date }
    group.ids.add(record.id)
    if (record.date < group.from) group.from = record.date
    if (record.date > group.to) group.to = record.date
    groups.set(key, group)
  }

  return <>
    <Tile title="Modo administrador">
      <p className="muted">Los reportes se guardan solo en este navegador (localStorage). Otras personas o dispositivos no los ven hasta que exista un servidor que los comparta. La sesión y los formularios son una demostración, sin seguridad real.</p>
    </Tile>

    <Tile title="Formulario de reporte de la ASADA" badge={<span className="chip nasa">Solo tu ASADA</span>}>
      {asada ? <>
        <div className="asada-head">
          <strong>{asada.name}</strong>
          <span className="muted">{asada.type} · {asada.district}, {asada.canton}, {asada.province}</span>
          <span>Caudal actual: <strong>{flowText(flow)}</strong>{mine.length === 0 && asada.caudal !== null && <small className="muted"> (valor inicial de SAGA)</small>}</span>
        </div>
        <form className="admin-form" onSubmit={saveReport} noValidate>
          <label>Histórico de caudal (L/s) · obligatorio
            <input type="text" inputMode="decimal" value={caudal} onChange={event => setCaudal(event.target.value)}
              placeholder="Ej.: 12,5" aria-required="true" />
            <small className="muted">Este valor actualiza el caudal de la ASADA.</small>
          </label>
          <label>Fecha de la medición
            <input type="date" value={measuredAt} max={today()} onChange={event => setMeasuredAt(event.target.value)} />
          </label>
          <fieldset className="level-pick"><legend>¿Hubo afectación por El Niño en la ASADA? · obligatorio</legend>
            <div className="segmented" role="group" aria-label="Afectación por El Niño">
              <button type="button" aria-pressed={nino === 'si'} onClick={() => setNino('si')}>Sí</button>
              <button type="button" aria-pressed={nino === 'no'} onClick={() => setNino('no')}>No</button>
            </div>
          </fieldset>
          {nino === 'si' && <div className="admin-form-field">
            <label htmlFor="locality-input">Localidades afectadas dentro de la ASADA · al menos una</label>
            <div className="tags">
              {localities.map(item => <span className="tag" key={item}>{item}
                <button type="button" aria-label={`Quitar ${item}`} onClick={() => setLocalities(localities.filter(place => place !== item))}>×</button></span>)}
              <input id="locality-input" type="text" value={localityText} maxLength={MAX_LOCALITY} onChange={event => setLocalityText(event.target.value)}
                onKeyDown={onLocalityKey} onBlur={() => addLocality(localityText)} placeholder={localities.length ? 'Otra localidad…' : 'Escribí y presioná Enter'} />
            </div>
            <small className="muted">Separalas con Enter o con coma.</small>
          </div>}
          <label>Notas (opcional)
            <textarea rows={3} maxLength={MAX_NOTES} value={notes} onChange={event => setNotes(event.target.value)} placeholder="Cómo se midió, desde cuándo y qué se observó." />
            <small className="muted">{notes.length} / {MAX_NOTES}</small>
          </label>
          {errors.length > 0 && <div className="error" role="alert">{errors.map(item => <p key={item}>{item}</p>)}</div>}
          <button type="submit" className="pill pill-primary">Enviar reporte</button>
        </form>
      </> : <p className="empty">No se pudo cargar el catálogo de ASADAs. Sin él no se puede identificar la ASADA de esta cuenta ({session.asadaId}).</p>}
    </Tile>

    <Tile title="Importador de datos locales">
      <p className="muted">Pegá o subí un CSV (encabezados: canton, variable, fecha, valor, estacion) o un JSON con esos mismos campos. Fechas AAAA, AAAA-MM o AAAA-MM-DD. Hasta 5 000 registros.</p>
      <textarea className="import-box" rows={5} value={text} onChange={event => { setText(event.target.value); setParsed(null) }}
        aria-label="Datos locales en CSV o JSON" placeholder={SAMPLE} spellCheck={false} />
      <div className="admin-actions">
        <label className="pill pill-ghost file-pick">Subir archivo
          <input type="file" accept=".csv,.json,.txt,text/csv,application/json" onChange={onFile} className="screen-reader" /></label>
        <button type="button" className="pill pill-ghost" onClick={() => { setText(SAMPLE); setParsed(null) }}>Insertar ejemplo de formato</button>
        <button type="button" className="pill" onClick={() => setParsed(parseLocalData(text, resolveCanton))}>Validar</button>
      </div>
      <p className="muted">El ejemplo usa valores inventados solo para probar el formato: no lo guardes como dato real.</p>
      {parsed && <div className="card" role="status">
        {parsed.error ? <p className="error">{parsed.error}</p> : <>
          <p><strong>{parsed.records.length}</strong> de {parsed.total} registros válidos{parsed.rejected.length > 0 && <>, <strong>{parsed.rejected.length}</strong> rechazados</>}.</p>
          {parsed.rejected.slice(0, 5).map(item => <p className="muted" key={item.row}>Fila {item.row}: {item.reason}</p>)}
          {parsed.rejected.length > 5 && <p className="muted">… y {parsed.rejected.length - 5} más.</p>}
          <button type="button" className="pill pill-primary" disabled={!parsed.records.length} onClick={saveRecords}>Guardar {parsed.records.length} registros</button>
        </>}
      </div>}
    </Tile>

    <Tile title="Lo guardado en este navegador">
      <h4>Reportes de tu ASADA ({mine.length})</h4>
      {mine.length ? mine.map(item => <div className="saved-row" key={item.id}>
        <div><strong>{flowText(item.caudal)}</strong> · {item.measuredAt}
          <small className="muted"> · {item.ninoAffected ? `Afectada por El Niño: ${item.localities.join(', ')}` : 'Sin afectación por El Niño'}</small></div>
        <button className="pill pill-ghost" onClick={() => { if (removeAsadaReport(item.id, session.asadaId)) notify('Reporte eliminado.') }}>Eliminar</button>
      </div>) : <p className="muted">Todavía no enviaste reportes.</p>}
      <h4>Registros locales ({data.records.length})</h4>
      {groups.size ? [...groups.values()].map(group => <div className="saved-row" key={`${group.code}|${group.variable}`}>
        <div><strong>{nameOf(group.code)}</strong> · {group.variable === 'T2M' ? 'Temperatura' : 'Precipitación'} · {group.ids.size} registros
          <small className="muted"> {group.from === group.to ? group.from : `${group.from} a ${group.to}`}</small></div>
        <button className="pill pill-ghost" onClick={() => { removeRecords(group.ids); notify(`Registros de ${nameOf(group.code)} eliminados.`) }}>Eliminar</button>
      </div>) : <p className="muted">Todavía no hay registros locales cargados.</p>}
      <button className="pill pill-ghost" disabled={!mine.length && !data.records.length}
        onClick={() => { if (window.confirm('¿Borrar los reportes de tu ASADA y los registros locales guardados en este navegador?')) { resetCantonData(session.asadaId); notify('Se restableció la base inicial.') } }}>
        Restablecer base inicial</button>
    </Tile>
  </>
}
