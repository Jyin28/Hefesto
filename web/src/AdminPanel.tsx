import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { ALERT_LABEL, ALERT_ORDER } from './analysis'
import type { AlertLevel } from './analysis'
import type { Session } from './auth'
import { Tile } from './Bento'
import { AlertPill } from './Forecast'
import type { Canton } from './data'
import { AFFECTATION_TYPES } from './data/cantonData'
import type { AffectationType, CantonData } from './data/cantonData'
import { MAX_CHARS, parseLocalData } from './localData'
import type { ParseResult } from './localData'
import { MAX_NOTES, addAffectation, addRecords, affectationLabel, removeAffectation, removeRecords, resetCantonData } from './store'

const SAMPLE = `canton,variable,fecha,valor,estacion
El Guarco,temperatura,2024-01,19.8,Estación de ejemplo
El Guarco,precipitacion,2024-01,85,Estación de ejemplo`

const dateFormat = new Intl.DateTimeFormat('es-CR', { dateStyle: 'medium', timeZone: 'America/Costa_Rica' })

export function AdminPanel({ session, choices, data, defaultCanton, resolveCanton, notify }: {
  session: Session; choices: Map<string, Canton>; data: CantonData; defaultCanton: string
  resolveCanton: (raw: string) => string | null; notify: (message: string) => void
}) {
  const sorted = [...choices].sort((a, b) => a[1].name.localeCompare(b[1].name, 'es-CR'))
  const nameOf = (code: string) => choices.get(code)?.name ?? code

  const [canton, setCanton] = useState(defaultCanton || sorted[0]?.[0] || '')
  const [type, setType] = useState<AffectationType>('sequia')
  const [level, setLevel] = useState<AlertLevel>('amarillo')
  const [notes, setNotes] = useState('')

  const [text, setText] = useState('')
  const [parsed, setParsed] = useState<ParseResult | null>(null)

  function saveAffectation(event: FormEvent) {
    event.preventDefault()
    if (!choices.has(canton)) return
    const saved = addAffectation({ cantonCode: canton, type, level, notes: notes.trim(), createdBy: session.email, organization: session.organization })
    setNotes('')
    notify(saved
      ? `Afectación registrada en ${nameOf(canton)}. Ya se ve en el mapa, en Avisos Generales y en el Análisis de Experto.`
      : `Afectación registrada en ${nameOf(canton)}, pero este navegador no pudo guardarla: se perderá al recargar.`)
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
    const saved = addRecords(parsed.records.map(item => ({ ...item, source: session.email })))
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
      <p className="muted">Los registros se guardan solo en este navegador (localStorage). Otras personas o dispositivos no los ven hasta que exista un servidor que los comparta. La sesión y los formularios son una demostración, sin seguridad real.</p>
    </Tile>

    <Tile title="Formulario de afectación por cantón">
      <form className="admin-form" onSubmit={saveAffectation}>
        <label>Cantón
          <select value={canton} onChange={event => setCanton(event.target.value)}>
            {sorted.map(([code, info]) => <option key={code} value={code}>{info.name}{info.province ? ` (${info.province})` : ''}</option>)}
          </select>
        </label>
        <label>Tipo de afectación
          <select value={type} onChange={event => setType(event.target.value as AffectationType)}>
            {AFFECTATION_TYPES.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>
        <fieldset className="level-pick"><legend>Nivel de umbral de advertencia</legend>
          <div className="segmented" role="group" aria-label="Nivel de advertencia">
            {ALERT_ORDER.map(item => <button type="button" key={item} aria-pressed={level === item} onClick={() => setLevel(item)}>
              <span className={`dot ${item}`} aria-hidden="true" /> {ALERT_LABEL[item]}</button>)}
          </div>
        </fieldset>
        <label>Notas técnicas
          <textarea rows={3} maxLength={MAX_NOTES} value={notes} onChange={event => setNotes(event.target.value)} placeholder="Qué se observó, desde cuándo y qué fuente lo respalda." />
          <small className="muted">{notes.length} / {MAX_NOTES}</small>
        </label>
        <button type="submit" className="pill pill-primary">Registrar afectación</button>
      </form>
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
      <h4>Afectaciones ({data.affectations.length})</h4>
      {data.affectations.length ? data.affectations.map(item => <div className="saved-row" key={item.id}>
        <div><strong>{nameOf(item.cantonCode)}</strong> · {affectationLabel(item.type)} <AlertPill level={item.level} />
          <small className="muted"> {item.createdAt ? dateFormat.format(new Date(item.createdAt)) : ''} · {item.createdBy}</small></div>
        <button className="pill pill-ghost" onClick={() => { removeAffectation(item.id); notify(`Afectación de ${nameOf(item.cantonCode)} eliminada.`) }}>Eliminar</button>
      </div>) : <p className="muted">Todavía no hay afectaciones registradas.</p>}
      <h4>Registros locales ({data.records.length})</h4>
      {groups.size ? [...groups.values()].map(group => <div className="saved-row" key={`${group.code}|${group.variable}`}>
        <div><strong>{nameOf(group.code)}</strong> · {group.variable === 'T2M' ? 'Temperatura' : 'Precipitación'} · {group.ids.size} registros
          <small className="muted"> {group.from === group.to ? group.from : `${group.from} a ${group.to}`}</small></div>
        <button className="pill pill-ghost" onClick={() => { removeRecords(group.ids); notify(`Registros de ${nameOf(group.code)} eliminados.`) }}>Eliminar</button>
      </div>) : <p className="muted">Todavía no hay registros locales cargados.</p>}
      <button className="pill pill-ghost" disabled={!data.affectations.length && !data.records.length}
        onClick={() => { if (window.confirm('¿Borrar todas las afectaciones y registros guardados en este navegador?')) { resetCantonData(); notify('Se restableció la base inicial.') } }}>
        Restablecer base inicial</button>
    </Tile>
  </>
}
