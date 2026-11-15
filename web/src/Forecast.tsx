import { useState } from 'react'
import type { FormEvent } from 'react'
import { ALERT_LABEL, ALERT_ORDER, defaultThresholds, fmt, levelFor } from './analysis'
import type { AlertLevel, Outcome, ProjectionResult, Thresholds } from './analysis'
import { Tile } from './Bento'
import { copy } from './copy'
import type { Level } from './copy'
import type { Variable } from './data'

export type ForecastRow = { variable: Variable; projection: ProjectionResult; localStatus?: string }

const VARIABLE_NAME: Record<Variable, { basico: string; tecnico: string }> = {
  PRECTOTCORR: { basico: 'Lluvia', tecnico: 'Precipitación (PRECTOTCORR)' },
  T2M: { basico: 'Temperatura', tecnico: 'Temperatura (T2M)' },
}
const rank = (level: AlertLevel) => ALERT_ORDER.indexOf(level)
const TRIGGERS: AlertLevel[] = ['amarillo', 'naranja', 'rojo']
const CONTACT = /^(@[A-Za-z][A-Za-z0-9_]{4,31}|-?\d{5,15})$/

export function AlertPill({ level }: { level: AlertLevel }) {
  return <span className={`alert-pill ${level}`}><span aria-hidden="true" className="dot" />{ALERT_LABEL[level]}</span>
}

function describe(variable: Variable, outcome: Outcome, level: Level) {
  const dev = outcome.deviation
  if (variable === 'PRECTOTCORR') {
    return level === 'basico'
      ? `${fmt(Math.abs(dev), 0)} % ${dev < 0 ? 'menos' : 'más'} lluvia que lo habitual`
      : `${dev >= 0 ? '+' : '−'}${fmt(Math.abs(dev), 1)} % vs media 1981–2010`
  }
  return level === 'basico'
    ? `${fmt(Math.abs(dev), 1)} °C ${dev < 0 ? 'más fresco' : 'más caliente'} que lo habitual`
    : `${dev >= 0 ? '+' : '−'}${fmt(Math.abs(dev), 2)} °C vs media 1981–2010`
}

const isExtreme = (variable: Variable, outcome: Outcome) =>
  variable === 'PRECTOTCORR' ? Math.abs(outcome.deviation) >= 100 : Math.abs(outcome.deviation) >= 3

export function ForecastTile({ level, zoneName, rows, thresholds, setThresholds }: {
  level: Level; zoneName: string; rows: ForecastRow[]; thresholds: Thresholds; setThresholds: (value: Thresholds) => void
}) {
  const [contact, setContact] = useState('')
  const [trigger, setTrigger] = useState<AlertLevel>('naranja')
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<string[] | null>(null)

  function setThreshold(variable: Variable, index: number, value: number) {
    const next = [...thresholds[variable]] as [number, number, number]
    next[index] = value
    for (let other = index + 1; other < 3; other++) next[other] = Math.max(next[other], value)
    for (let other = index - 1; other >= 0; other--) next[other] = Math.min(next[other], value)
    setThresholds({ ...thresholds, [variable]: next })
  }

  function status(row: ForecastRow) {
    if (!row.projection.ok) return null
    const levels = [row.projection.corto, row.projection.mediano].map(outcome => levelFor(row.variable, outcome.deviation, thresholds))
    return levels.reduce((worst, item) => rank(item) > rank(worst) ? item : worst, 'verde' as AlertLevel)
  }

  function test(event: FormEvent) {
    event.preventDefault()
    const value = contact.trim()
    if (!CONTACT.test(value)) {
      setError('Escribí un @usuario de Telegram (5 a 32 caracteres) o un Chat ID numérico.')
      setPreview(null)
      return
    }
    setError('')
    const lines = rows.flatMap(row => {
      const level = status(row)
      if (!level || !row.projection.ok) return []
      const projected = rank(levelFor(row.variable, row.projection.mediano.deviation, thresholds)) >= rank(levelFor(row.variable, row.projection.corto.deviation, thresholds))
        ? row.projection.mediano : row.projection.corto
      const fires = rank(level) >= rank(trigger)
      return [`${VARIABLE_NAME[row.variable].basico}: nivel ${ALERT_LABEL[level]} (${describe(row.variable, projected, 'basico')}, proyección a ${projected.year}). ${fires ? 'Se enviaría esta alerta.' : `No se enviaría: no llega al umbral ${ALERT_LABEL[trigger]}.`}`]
    })
    setPreview([`Detective Tico · Alerta preventiva`, `Zona: ${zoneName}`, `Destino: ${value}`, ...(lines.length ? lines : ['Sin proyección disponible para esta zona con el rango elegido.']),
      'Proyección de tendencia, no es un pronóstico validado.'])
  }

  const anyOk = rows.some(row => row.projection.ok)
  return <Tile title="Algoritmos de Predicción, Umbrales y Alertas Telegram"
    badge={<span className="badge-soft" title={copy[level].forecastNote}>Proyección de tendencia</span>}>
    <p className="muted">{copy[level].forecastNote}</p>
    {rows.map(row => {
      const name = VARIABLE_NAME[row.variable][level]
      if (!row.projection.ok) {
        return <div className="forecast-row" key={row.variable}><strong>{name}</strong>
          <p className="muted">{row.projection.reason === 'range' ? 'Elegí un rango de al menos 10 años para proyectar.' : 'La serie no tiene años suficientes (1981–2010) para la referencia.'}</p></div>
      }
      const { corto, mediano, reference } = row.projection
      return <div className="forecast-row" key={row.variable}>
        <strong>{name}</strong>
        <div className="forecast-cols">
          {[['Corto plazo', corto], ['Mediano plazo', mediano]].map(([label, outcome]) => {
            const item = outcome as Outcome
            return <div key={label as string}>
              <small>{label as string} · {item.year}</small>
              <AlertPill level={levelFor(row.variable, item.deviation, thresholds)} />
              <p>{describe(row.variable, item, level)}</p>
              {isExtreme(row.variable, item) && <p className="warn">Proyección extrema: revisá la serie antes de usarla.</p>}
            </div>
          })}
        </div>
        <p className="muted">Referencia 1981–2010: {fmt(reference, row.variable === 'T2M' ? 2 : 0)} {copy[level].unit[row.variable]}.
          {row.localStatus === 'local_data_pending' ? ' Pronóstico con estaciones locales: pendiente de datos del IMN.' : ''}</p>
      </div>
    })}
    <details>
      <summary>Configurar umbrales de advertencia</summary>
      {(['PRECTOTCORR', 'T2M'] as Variable[]).filter(variable => rows.some(row => row.variable === variable)).map(variable => <fieldset key={variable} className="thresholds">
        <legend>{VARIABLE_NAME[variable][level]} · {variable === 'PRECTOTCORR' ? 'déficit de lluvia (%)' : 'anomalía térmica (°C)'}</legend>
        {TRIGGERS.map((name, index) => <label key={name}>
          <span><span aria-hidden="true" className={`dot ${name}`} /> {ALERT_LABEL[name]} desde {fmt(thresholds[variable][index], variable === 'T2M' ? 1 : 0)}{variable === 'PRECTOTCORR' ? ' %' : ' °C'}</span>
          <input type="range" min={0} max={variable === 'PRECTOTCORR' ? 60 : 3} step={variable === 'PRECTOTCORR' ? 1 : 0.1}
            value={thresholds[variable][index]} onChange={event => setThreshold(variable, index, Number(event.target.value))} />
        </label>)}
      </fieldset>)}
      <button type="button" className="pill pill-ghost" onClick={() => setThresholds(defaultThresholds)}>Restablecer umbrales de ejemplo</button>
      <p className="muted">Los valores iniciales son de ejemplo. Las comisiones deben definir los umbrales operativos.</p>
    </details>
    <form className="telegram" onSubmit={test}>
      <h4>Alertas vía Telegram</h4>
      <label>@usuario o Chat ID
        <input type="text" value={contact} onChange={event => setContact(event.target.value)} placeholder="@mi_usuario o 123456789" autoComplete="off" />
      </label>
      <div className="segmented" role="group" aria-label="Umbral de disparo">
        {TRIGGERS.map(name => <button type="button" key={name} aria-pressed={trigger === name} onClick={() => setTrigger(name)}>{ALERT_LABEL[name]}</button>)}
      </div>
      <p className="muted">Se avisaría a {zoneName} cuando la proyección llegue al nivel {ALERT_LABEL[trigger]} o más.</p>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" className="pill pill-primary" disabled={!anyOk}>Probar vista previa</button>
      {preview && <div className="telegram-preview" role="status" aria-label="Vista previa de la notificación">
        {preview.map(line => <p key={line}>{line}</p>)}
      </div>}
      <p className="muted">Es una vista previa: no se envía ningún mensaje ni se guarda el contacto. El envío real requiere un bot de Telegram configurado por las comisiones.</p>
    </form>
  </Tile>
}
