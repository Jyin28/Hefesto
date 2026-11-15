import { useState } from 'react'
import type { FormEvent } from 'react'
import { ALERT_LABEL, ALERT_ORDER, defaultThresholds, fmt, levelFor } from './analysis'
import type { AlertLevel, Outcome, ProjectionResult } from './analysis'
import { Tile } from './Bento'
import { copy } from './copy'
import type { Level } from './copy'
import type { Variable } from './data'
import { t } from './i18n'

export type ForecastRow = { variable: Variable; projection: ProjectionResult; localStatus?: string }

/** Con getters: el nombre «básico» sale en el idioma activo (el técnico no se usa en la interfaz actual). */
const VARIABLE_NAME: Record<Variable, { basico: string; tecnico: string }> = {
  PRECTOTCORR: { get basico() { return t('Lluvia', 'Rain') }, tecnico: 'Precipitación (PRECTOTCORR)' },
  T2M: { get basico() { return t('Temperatura', 'Temperature') }, tecnico: 'Temperatura (T2M)' },
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
      ? t(`${fmt(Math.abs(dev), 0)} % ${dev < 0 ? 'menos' : 'más'} lluvia que lo habitual`, `${fmt(Math.abs(dev), 0)} % ${dev < 0 ? 'less' : 'more'} rain than usual`)
      : `${dev >= 0 ? '+' : '−'}${fmt(Math.abs(dev), 1)} % vs media 1981–2010`
  }
  return level === 'basico'
    ? t(`${fmt(Math.abs(dev), 1)} °C ${dev < 0 ? 'más fresco' : 'más caliente'} que lo habitual`, `${fmt(Math.abs(dev), 1)} °C ${dev < 0 ? 'cooler' : 'warmer'} than usual`)
    : `${dev >= 0 ? '+' : '−'}${fmt(Math.abs(dev), 2)} °C vs media 1981–2010`
}

const isExtreme = (variable: Variable, outcome: Outcome) =>
  variable === 'PRECTOTCORR' ? Math.abs(outcome.deviation) >= 100 : Math.abs(outcome.deviation) >= 3

export function ForecastTile({ level, zoneName, rows }: {
  level: Level; zoneName: string; rows: ForecastRow[]
}) {
  const thresholds = defaultThresholds
  const [contact, setContact] = useState('')
  const [trigger, setTrigger] = useState<AlertLevel>('naranja')
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<string[] | null>(null)

  function status(row: ForecastRow) {
    if (!row.projection.ok) return null
    const levels = [row.projection.corto, row.projection.mediano].map(outcome => levelFor(row.variable, outcome.deviation, thresholds))
    return levels.reduce((worst, item) => rank(item) > rank(worst) ? item : worst, 'verde' as AlertLevel)
  }

  function test(event: FormEvent) {
    event.preventDefault()
    const value = contact.trim()
    if (!CONTACT.test(value)) {
      setError(t('Escribí un @usuario de Telegram (5 a 32 caracteres) o un Chat ID numérico.', 'Enter a Telegram @username (5 to 32 characters) or a numeric Chat ID.'))
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
      return [t(`${VARIABLE_NAME[row.variable].basico}: nivel ${ALERT_LABEL[level]} (${describe(row.variable, projected, 'basico')}, proyección a ${projected.year}). ${fires ? 'Se enviaría esta alerta.' : `No se enviaría: no llega al umbral ${ALERT_LABEL[trigger]}.`}`,
        `${VARIABLE_NAME[row.variable].basico}: ${ALERT_LABEL[level]} level (${describe(row.variable, projected, 'basico')}, projection to ${projected.year}). ${fires ? 'This alert would be sent.' : `It would not be sent: it does not reach the ${ALERT_LABEL[trigger]} threshold.`}`)]
    })
    setPreview([t('AguaAlerta · Alerta preventiva', 'AguaAlerta · Preventive alert'), t(`Zona: ${zoneName}`, `Area: ${zoneName}`), t(`Destino: ${value}`, `Destination: ${value}`),
      ...(lines.length ? lines : [t('Sin proyección disponible para esta zona con el rango elegido.', 'No projection available for this area with the chosen range.')]),
      t('Proyección de tendencia, no es un pronóstico validado.', 'Trend projection, not a validated forecast.')])
  }

  const anyOk = rows.some(row => row.projection.ok)
  return <Tile title={t('Algoritmos de Predicción, Umbrales y Alertas Telegram', 'Prediction Algorithms, Thresholds and Telegram Alerts')}
    badge={<span className="badge-soft" title={copy[level].forecastNote}>{t('Proyección de tendencia', 'Trend projection')}</span>}>
    <p className="muted">{copy[level].forecastNote}</p>
    {rows.map(row => {
      const name = VARIABLE_NAME[row.variable][level]
      if (!row.projection.ok) {
        return <div className="forecast-row" key={row.variable}><strong>{name}</strong>
          <p className="muted">{row.projection.reason === 'range' ? t('Elegí un rango de al menos 10 años para proyectar.', 'Choose a range of at least 10 years to project.') : t('La serie no tiene años suficientes (1981–2010) para la referencia.', 'The series does not have enough years (1981–2010) for the reference.')}</p></div>
      }
      const { corto, mediano, reference } = row.projection
      return <div className="forecast-row" key={row.variable}>
        <strong>{name}</strong>
        <div className="forecast-cols">
          {[[t('Corto plazo', 'Short term'), corto], [t('Mediano plazo', 'Medium term'), mediano]].map(([label, outcome]) => {
            const item = outcome as Outcome
            return <div key={label as string}>
              <small>{label as string} · {item.year}</small>
              <AlertPill level={levelFor(row.variable, item.deviation, thresholds)} />
              <p>{describe(row.variable, item, level)}</p>
              {isExtreme(row.variable, item) && <p className="warn">{t('Proyección extrema: revisá la serie antes de usarla.', 'Extreme projection: check the series before using it.')}</p>}
            </div>
          })}
        </div>
        <p className="muted">{t('Referencia 1981–2010:', 'Reference 1981–2010:')} {fmt(reference, row.variable === 'T2M' ? 2 : 0)} {copy[level].unit[row.variable]}.
          {row.localStatus === 'local_data_pending' ? t(' Pronóstico con estaciones locales: pendiente de datos del IMN.', ' Forecast with local stations: pending IMN data.') : ''}</p>
      </div>
    })}
    <details>
      <summary>{t('Umbrales de advertencia', 'Warning thresholds')}</summary>
      {(['PRECTOTCORR', 'T2M'] as Variable[]).filter(variable => rows.some(row => row.variable === variable)).map(variable => <fieldset key={variable} className="thresholds">
        <legend>{VARIABLE_NAME[variable][level]} · {variable === 'PRECTOTCORR' ? t('déficit de lluvia (%)', 'rainfall deficit (%)') : t('anomalía térmica (°C)', 'temperature anomaly (°C)')}</legend>
        {TRIGGERS.map((name, index) => <p key={name}>
          <span aria-hidden="true" className={`dot ${name}`} /> {ALERT_LABEL[name]} {t('desde', 'from')} {fmt(thresholds[variable][index], variable === 'T2M' ? 1 : 0)}{variable === 'PRECTOTCORR' ? ' %' : ' °C'}
        </p>)}
      </fieldset>)}
      <p className="muted">{t('Umbrales fijos definidos por las comisiones; no se editan desde este panel.', 'Fixed thresholds set by the commissions; they cannot be edited from this panel.')}</p>
    </details>
    <form className="telegram" onSubmit={test}>
      <h4>{t('Alertas vía Telegram', 'Telegram alerts')}</h4>
      <label>{t('@usuario o Chat ID', '@username or Chat ID')}
        <input type="text" value={contact} onChange={event => setContact(event.target.value)} placeholder={t('@mi_usuario o 123456789', '@my_username or 123456789')} autoComplete="off" />
      </label>
      <div className="segmented" role="group" aria-label={t('Umbral de disparo', 'Trigger threshold')}>
        {TRIGGERS.map(name => <button type="button" key={name} aria-pressed={trigger === name} onClick={() => setTrigger(name)}>{ALERT_LABEL[name]}</button>)}
      </div>
      <p className="muted">{t(`Se avisaría a ${zoneName} cuando la proyección llegue al nivel ${ALERT_LABEL[trigger]} o más.`, `${zoneName} would be notified when the projection reaches the ${ALERT_LABEL[trigger]} level or higher.`)}</p>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" className="pill pill-primary" disabled={!anyOk}>{t('Probar vista previa', 'Try preview')}</button>
      {preview && <div className="telegram-preview" role="status" aria-label={t('Vista previa de la notificación', 'Notification preview')}>
        {preview.map(line => <p key={line}>{line}</p>)}
      </div>}
      <p className="muted">{t('Es una vista previa: no se envía ningún mensaje ni se guarda el contacto. Para recibir mensajes reales, buscá tu ASADA en Predicciones y suscribite al newsletter.', 'This is a preview: no message is sent and the contact is not saved. To receive real messages, search for your ASADA in Predictions and subscribe to the newsletter.')}</p>
    </form>
  </Tile>
}
