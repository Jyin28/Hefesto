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
import { locale, t } from './i18n'

/** Ejemplo de formato (el importador acepta encabezados en español o en inglés). */
const sample = () => t(
  'canton,variable,fecha,valor,estacion\nEl Guarco,temperatura,2024-01,19.8,Estación de ejemplo\nEl Guarco,precipitacion,2024-01,85,Estación de ejemplo',
  'canton,variable,date,value,station\nEl Guarco,temperature,2024-01,19.8,Sample station\nEl Guarco,precipitation,2024-01,85,Sample station')


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
    if (value === null) found.push(t('El histórico de caudal es obligatorio y debe ser un número.', 'The flow history is required and must be a number.'))
    else if (value <= 0 || value > MAX_FLOW) found.push(t(`El caudal debe ser mayor que 0 y no pasar de ${MAX_FLOW.toLocaleString(locale())} L/s.`, `The flow must be greater than 0 and not exceed ${MAX_FLOW.toLocaleString(locale())} L/s.`))
    if (!/^\d{4}-\d{2}-\d{2}$/.test(measuredAt)) found.push(t('Indicá la fecha de la medición.', 'Enter the measurement date.'))
    else if (measuredAt > today()) found.push(t('La fecha de la medición no puede ser futura.', 'The measurement date cannot be in the future.'))
    if (!nino) found.push(t('Indicá si El Niño afectó a la ASADA (Sí o No).', 'Indicate whether El Niño affected the ASADA (Yes or No).'))
    const places = nino === 'si' ? addLocality(localityText) : []
    if (nino === 'si' && !places.length) found.push(t('Si hubo afectación, indicá al menos una localidad afectada dentro de la ASADA.', 'If there was an impact, enter at least one affected locality within the ASADA.'))
    setErrors(found)
    if (found.length || value === null) return
    const result = addAsadaReport({
      asadaId: session.asadaId, cantonCode: asada.cantonCode, caudal: value, measuredAt, ninoAffected: nino === 'si',
      localities: places, notes: notes.trim(), createdBy: session.username, organization: session.organization,
    }, session.asadaId)
    if (result === 'forbidden' || result === 'invalid') { setErrors([t('No se pudo guardar el reporte: revisá los datos.', 'The report could not be saved: check the data.')]); return }
    setCaudal(''); setNino(''); setLocalities([]); setLocalityText(''); setNotes('')
    notify(result === 'saved'
      ? t(`Reporte guardado: el caudal de ${asada.name} ahora es ${flowText(value)}. Ya se ve en el mapa y en el buscador.`, `Report saved: the flow of ${asada.name} is now ${flowText(value)}. It already shows on the map and in the search box.`)
      : t('Reporte guardado, pero este navegador no pudo almacenarlo: se perderá al recargar.', 'Report saved, but this browser could not store it: it will be lost on reload.'))
  }

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (file.size > MAX_CHARS) { setParsed({ records: [], rejected: [], total: 0, error: t('El archivo supera 1 MB. Dividilo en partes.', 'The file exceeds 1 MB. Split it into parts.') }); return }
    const content = await file.text()
    setText(content)
    setParsed(parseLocalData(content, resolveCanton))
  }

  function saveRecords() {
    if (!parsed?.records.length) return
    const saved = addRecords(parsed.records.map(item => ({ ...item, source: session.username })))
    notify(saved
      ? t(`${parsed.records.length} registros locales guardados. Ya cuentan en Calidad y en el Análisis de Experto.`, `${parsed.records.length} local records saved. They now count in Quality and in the Expert Analysis.`)
      : t('Los registros se cargaron, pero este navegador no pudo guardarlos: se perderán al recargar.', 'The records were loaded, but this browser could not save them: they will be lost on reload.'))
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
    <Tile title={t('Modo administrador', 'Administrator mode')}>
      <p className="muted">{t('Los reportes se guardan solo en este navegador (localStorage). Otras personas o dispositivos no los ven hasta que exista un servidor que los comparta. La sesión y los formularios son una demostración, sin seguridad real.', 'Reports are saved only in this browser (localStorage). Other people or devices do not see them until a server exists to share them. The session and forms are a demo, with no real security.')}</p>
    </Tile>

    <Tile title={t('Formulario de reporte de la ASADA', 'ASADA report form')} badge={<span className="chip nasa">{t('Solo tu ASADA', 'Your ASADA only')}</span>}>
      {asada ? <>
        <div className="asada-head">
          <strong>{asada.name}</strong>
          <span className="muted">{asada.type} · {asada.district}, {asada.canton}, {asada.province}</span>
          <span>{t('Caudal actual:', 'Current flow:')} <strong>{flowText(flow)}</strong>{mine.length === 0 && asada.caudal !== null && <small className="muted"> {t('(valor inicial de SAGA)', '(initial SAGA value)')}</small>}</span>
        </div>
        <form className="admin-form" onSubmit={saveReport} noValidate>
          <label>{t('Histórico de caudal (L/s) · obligatorio', 'Flow history (L/s) · required')}
            <input type="text" inputMode="decimal" value={caudal} onChange={event => setCaudal(event.target.value)}
              placeholder={t('Ej.: 12,5', 'E.g.: 12.5')} aria-required="true" />
            <small className="muted">{t('Este valor actualiza el caudal de la ASADA.', 'This value updates the ASADA’s flow.')}</small>
          </label>
          <label>{t('Fecha de la medición', 'Measurement date')}
            <input type="date" value={measuredAt} max={today()} onChange={event => setMeasuredAt(event.target.value)} />
          </label>
          <fieldset className="level-pick"><legend>{t('¿Hubo afectación por El Niño en la ASADA? · obligatorio', 'Was the ASADA affected by El Niño? · required')}</legend>
            <div className="segmented" role="group" aria-label={t('Afectación por El Niño', 'Impact from El Niño')}>
              <button type="button" aria-pressed={nino === 'si'} onClick={() => setNino('si')}>{t('Sí', 'Yes')}</button>
              <button type="button" aria-pressed={nino === 'no'} onClick={() => setNino('no')}>No</button>
            </div>
          </fieldset>
          {nino === 'si' && <div className="admin-form-field">
            <label htmlFor="locality-input">{t('Localidades afectadas dentro de la ASADA · al menos una', 'Affected localities within the ASADA · at least one')}</label>
            <div className="tags">
              {localities.map(item => <span className="tag" key={item}>{item}
                <button type="button" aria-label={t(`Quitar ${item}`, `Remove ${item}`)} onClick={() => setLocalities(localities.filter(place => place !== item))}>×</button></span>)}
              <input id="locality-input" type="text" value={localityText} maxLength={MAX_LOCALITY} onChange={event => setLocalityText(event.target.value)}
                onKeyDown={onLocalityKey} onBlur={() => addLocality(localityText)} placeholder={localities.length ? t('Otra localidad…', 'Another locality…') : t('Escribí y presioná Enter', 'Type and press Enter')} />
            </div>
            <small className="muted">{t('Separalas con Enter o con coma.', 'Separate them with Enter or a comma.')}</small>
          </div>}
          <label>{t('Notas (opcional)', 'Notes (optional)')}
            <textarea rows={3} maxLength={MAX_NOTES} value={notes} onChange={event => setNotes(event.target.value)} placeholder={t('Cómo se midió, desde cuándo y qué se observó.', 'How it was measured, since when and what was observed.')} />
            <small className="muted">{notes.length} / {MAX_NOTES}</small>
          </label>
          {errors.length > 0 && <div className="error" role="alert">{errors.map(item => <p key={item}>{item}</p>)}</div>}
          <button type="submit" className="pill pill-primary">{t('Enviar reporte', 'Submit report')}</button>
        </form>
      </> : <p className="empty">{t(`No se pudo cargar el catálogo de ASADAs. Sin él no se puede identificar la ASADA de esta cuenta (${session.asadaId}).`, `The ASADA catalog could not be loaded. Without it the ASADA of this account (${session.asadaId}) cannot be identified.`)}</p>}
    </Tile>

    <Tile title={t('Importador de datos locales', 'Local data importer')}>
      <p className="muted">{t('Pegá o subí un CSV (encabezados: canton, variable, fecha, valor, estacion) o un JSON con esos mismos campos. Fechas AAAA, AAAA-MM o AAAA-MM-DD. Hasta 5 000 registros.', 'Paste or upload a CSV (headers: canton, variable, date, value, station) or a JSON with those same fields. Dates YYYY, YYYY-MM or YYYY-MM-DD. Up to 5,000 records.')}</p>
      <textarea className="import-box" rows={5} value={text} onChange={event => { setText(event.target.value); setParsed(null) }}
        aria-label={t('Datos locales en CSV o JSON', 'Local data as CSV or JSON')} placeholder={sample()} spellCheck={false} />
      <div className="admin-actions">
        <label className="pill pill-ghost file-pick">{t('Subir archivo', 'Upload file')}
          <input type="file" accept=".csv,.json,.txt,text/csv,application/json" onChange={onFile} className="screen-reader" /></label>
        <button type="button" className="pill pill-ghost" onClick={() => { setText(sample()); setParsed(null) }}>{t('Insertar ejemplo de formato', 'Insert format example')}</button>
        <button type="button" className="pill" onClick={() => setParsed(parseLocalData(text, resolveCanton))}>{t('Validar', 'Validate')}</button>
      </div>
      <p className="muted">{t('El ejemplo usa valores inventados solo para probar el formato: no lo guardes como dato real.', 'The example uses made-up values only to test the format: do not save it as real data.')}</p>
      {parsed && <div className="card" role="status">
        {parsed.error ? <p className="error">{parsed.error}</p> : <>
          <p><strong>{parsed.records.length}</strong> {t('de', 'of')} {parsed.total} {t('registros válidos', 'valid records')}{parsed.rejected.length > 0 && <>, <strong>{parsed.rejected.length}</strong> {t('rechazados', 'rejected')}</>}.</p>
          {parsed.rejected.slice(0, 5).map(item => <p className="muted" key={item.row}>{t('Fila', 'Row')} {item.row}: {item.reason}</p>)}
          {parsed.rejected.length > 5 && <p className="muted">{t(`… y ${parsed.rejected.length - 5} más.`, `… and ${parsed.rejected.length - 5} more.`)}</p>}
          <button type="button" className="pill pill-primary" disabled={!parsed.records.length} onClick={saveRecords}>{t(`Guardar ${parsed.records.length} registros`, `Save ${parsed.records.length} records`)}</button>
        </>}
      </div>}
    </Tile>

    <Tile title={t('Lo guardado en este navegador', 'Saved in this browser')}>
      <h4>{t(`Reportes de tu ASADA (${mine.length})`, `Your ASADA's reports (${mine.length})`)}</h4>
      {mine.length ? mine.map(item => <div className="saved-row" key={item.id}>
        <div><strong>{flowText(item.caudal)}</strong> · {item.measuredAt}
          <small className="muted"> · {item.ninoAffected ? t(`Afectada por El Niño: ${item.localities.join(', ')}`, `Affected by El Niño: ${item.localities.join(', ')}`) : t('Sin afectación por El Niño', 'Not affected by El Niño')}</small></div>
        <button className="pill pill-ghost" onClick={() => { if (removeAsadaReport(item.id, session.asadaId)) notify(t('Reporte eliminado.', 'Report deleted.')) }}>{t('Eliminar', 'Delete')}</button>
      </div>) : <p className="muted">{t('Todavía no enviaste reportes.', 'You have not submitted any reports yet.')}</p>}
      <h4>{t(`Registros locales (${data.records.length})`, `Local records (${data.records.length})`)}</h4>
      {groups.size ? [...groups.values()].map(group => <div className="saved-row" key={`${group.code}|${group.variable}`}>
        <div><strong>{nameOf(group.code)}</strong> · {group.variable === 'T2M' ? t('Temperatura', 'Temperature') : t('Precipitación', 'Precipitation')} · {group.ids.size} {t('registros', 'records')}
          <small className="muted"> {group.from === group.to ? group.from : `${group.from} ${t('a', 'to')} ${group.to}`}</small></div>
        <button className="pill pill-ghost" onClick={() => { removeRecords(group.ids); notify(t(`Registros de ${nameOf(group.code)} eliminados.`, `Records for ${nameOf(group.code)} deleted.`)) }}>{t('Eliminar', 'Delete')}</button>
      </div>) : <p className="muted">{t('Todavía no hay registros locales cargados.', 'There are no local records loaded yet.')}</p>}
      <button className="pill pill-ghost" disabled={!mine.length && !data.records.length}
        onClick={() => { if (window.confirm(t('¿Borrar los reportes de tu ASADA y los registros locales guardados en este navegador?', 'Delete your ASADA\'s reports and the local records saved in this browser?'))) { resetCantonData(session.asadaId); notify(t('Se restableció la base inicial.', 'The initial database was restored.')) } }}>
        {t('Restablecer base inicial', 'Restore initial database')}</button>
    </Tile>
  </>
}
