import type { Cell, Climate, Variable } from './data'
import type { Level } from './copy'

export type Point = { year: number; value: number | null; complete?: boolean }
export type Range = [number, number]
export type AlertLevel = 'verde' | 'amarillo' | 'naranja' | 'rojo'
export type Confidence = 'sin-datos' | 'baja' | 'media' | 'alta'
export type Thresholds = Record<Variable, [number, number, number]>

/** Umbrales de ejemplo, editables en el panel. Lluvia: déficit en % frente a la referencia. Temperatura: anomalía en °C. */
export const defaultThresholds: Thresholds = { PRECTOTCORR: [10, 20, 30], T2M: [0.5, 1, 1.5] }
export const REFERENCE: Range = [1981, 2010]
export const HORIZONS = { corto: 3, mediano: 10 }
export const ALERT_ORDER: AlertLevel[] = ['verde', 'amarillo', 'naranja', 'rojo']
export const ALERT_LABEL: Record<AlertLevel, string> = { verde: 'Verde', amarillo: 'Amarillo', naranja: 'Naranja', rojo: 'Rojo' }

export const fmt = (value: number, digits = 1) =>
  new Intl.NumberFormat('es-CR', { maximumFractionDigits: digits }).format(value)

type Usable = { year: number; value: number }

/** Años con valor y con los 12 meses válidos, dentro del rango si se indica. */
export function usable(series: Point[], range?: Range): Usable[] {
  return series.filter((point): point is Usable => point.value != null && point.complete !== false
    && (!range || (point.year >= range[0] && point.year <= range[1])))
}

export const mean = (values: number[]) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null

/** Mínimos cuadrados ordinarios simple. Es una pendiente descriptiva del rango, sin ajuste por pruebas múltiples. */
export function ols(points: Usable[]) {
  if (points.length < 3) return null
  const xBar = points.reduce((sum, point) => sum + point.year, 0) / points.length
  const yBar = points.reduce((sum, point) => sum + point.value, 0) / points.length
  const sxx = points.reduce((sum, point) => sum + (point.year - xBar) ** 2, 0)
  if (sxx === 0) return null
  const slope = points.reduce((sum, point) => sum + (point.year - xBar) * (point.value - yBar), 0) / sxx
  return { slope, intercept: yBar - slope * xBar, n: points.length }
}

export function continuity(series: Point[], range: Range) {
  const total = range[1] - range[0] + 1
  const valid = usable(series, range).length
  return { valid, total, pct: total > 0 ? valid / total : 0 }
}

export function spatialCoverage(cells: Cell[]) {
  const withData = cells.filter(cell => cell.long_term_slope != null).length
  return { withData, total: cells.length, pct: cells.length ? withData / cells.length : 0 }
}

/**
 * Regla de confianza (transparente): continuidad y cobertura espacial altas dan «alta»; sin estaciones locales que
 * validen el reanálisis, el máximo es «media».
 */
export function confidence(continuityPct: number, coveragePct: number, stations: number, hasData: boolean): Confidence {
  if (!hasData) return 'sin-datos'
  let level: Confidence = continuityPct >= 0.9 && coveragePct >= 0.75 ? 'alta'
    : continuityPct >= 0.7 && coveragePct >= 0.4 ? 'media' : 'baja'
  if (level === 'alta' && stations === 0) level = 'media'
  return level
}

/** Estaciones o fuentes locales: la del pronóstico experimental más las cargadas por comisiones (sin validar). */
export function stationsLinked(climate?: Climate, localStations: string[] = []) {
  const status = climate?.forecast.status
  const base = !climate ? { count: 0, note: 'Sin zona con datos' }
    : status === 'local_data_pending' ? { count: 0, note: 'Datos de estaciones del IMN pendientes' }
    : status === 'station_data_invalid' ? { count: 0, note: 'Datos de estación inválidos' }
    : { count: 1, note: 'Estación local usada en el pronóstico experimental' }
  if (!localStations.length) return base
  return {
    count: base.count + localStations.length,
    note: `${base.note}. ${localStations.length} ${localStations.length === 1 ? 'fuente local cargada' : 'fuentes locales cargadas'} por comisiones, todavía sin validar contra NASA.`,
  }
}

export type LocalStat = { n: number; mean: number; from: string; to: string }

/** Resumen de registros locales de una variable (promedio simple y rango de fechas). */
export function localStat(records: { value: number; date: string }[]): LocalStat | undefined {
  if (!records.length) return undefined
  const dates = records.map(record => record.date).sort()
  return { n: records.length, mean: records.reduce((sum, record) => sum + record.value, 0) / records.length, from: dates[0], to: dates[dates.length - 1] }
}

export type Outcome = { year: number; value: number; deviation: number }
export type ProjectionResult =
  | { ok: true; reference: number; fitRange: Range; points: { year: number; value: number }[]; corto: Outcome; mediano: Outcome }
  | { ok: false; reason: 'range' | 'reference' }

/** Desviación frente a la referencia: lluvia en % (negativa = déficit), temperatura en °C (positiva = más cálido). */
export const deviation = (variable: Variable, value: number, reference: number) =>
  variable === 'PRECTOTCORR' ? ((value - reference) / reference) * 100 : value - reference

/** Extrapola la recta ajustada en el rango elegido. No es un pronóstico validado: es una proyección de tendencia. */
export function project(series: Point[], variable: Variable, range: Range): ProjectionResult {
  const fit = ols(usable(series, range))
  if (!fit || fit.n < 10) return { ok: false, reason: 'range' }
  const reference = mean(usable(series, REFERENCE).map(point => point.value))
  if (reference === null || usable(series, REFERENCE).length < 20 || reference === 0) return { ok: false, reason: 'reference' }
  const base = Math.max(...usable(series).map(point => point.year))
  const at = (year: number) => {
    const value = fit.intercept + fit.slope * year
    return variable === 'PRECTOTCORR' ? Math.max(0, value) : value
  }
  const outcome = (offset: number): Outcome => {
    const value = at(base + offset)
    return { year: base + offset, value, deviation: deviation(variable, value, reference) }
  }
  const points = Array.from({ length: HORIZONS.mediano }, (_, index) => ({ year: base + index + 1, value: at(base + index + 1) }))
  return { ok: true, reference, fitRange: range, points, corto: outcome(HORIZONS.corto), mediano: outcome(HORIZONS.mediano) }
}

export function levelFor(variable: Variable, dev: number, thresholds: Thresholds): AlertLevel {
  const [yellow, orange, red] = thresholds[variable]
  const amount = variable === 'PRECTOTCORR' ? -dev : dev
  return amount >= red ? 'rojo' : amount >= orange ? 'naranja' : amount >= yellow ? 'amarillo' : 'verde'
}

export type VarStats = {
  mean: number | null; slope: number | null; n: number; official: number | null; significant: boolean | null
}

export function statsFor(climate: Climate | undefined, range: Range): VarStats | undefined {
  if (!climate) return undefined
  const points = usable(climate.series, range)
  const fit = ols(points)
  return {
    mean: mean(points.map(point => point.value)), slope: fit ? fit.slope * 10 : null, n: points.length,
    official: climate.trend.slope_per_decade, significant: climate.trend.significant,
  }
}

/** Anomalía mensual media del episodio ENSO en las unidades de la variable (mm/mes o °C). */
export function ensoMean(climate?: Climate) {
  const values = climate?.enso.months.map(month => month.anomaly).filter((value): value is number => value != null) ?? []
  return mean(values)
}

export type SynthesisInput = {
  level: Level; zone: string; regionName?: string; range: Range
  precip?: VarStats; temp?: VarStats
  enso?: { start: string; end: string; precip: number | null; temp: number | null }
  confidence: Confidence; continuityPct: number; coveragePct: number; stations: number
  /** Afectaciones registradas por comisiones para el cantón (de mayor a menor nivel). */
  affectations?: { typeLabel: string; level: AlertLevel; notes: string; by: string }[]
  /** Registros locales cargados por comisiones, por variable. */
  local?: { temp?: LocalStat; precip?: LocalStat }
}

const CONFIDENCE_LABEL: Record<Confidence, string> = { 'sin-datos': 'sin datos', baja: 'baja', media: 'media', alta: 'alta' }
export const confidenceLabel = (value: Confidence) => CONFIDENCE_LABEL[value]

/** Redacción por plantillas a partir de las cifras del panel. No usa un modelo de lenguaje. */
export function synthesis(input: SynthesisInput): string[] {
  const { level, zone, range, precip, temp, enso } = input
  const basic = level === 'basico'
  const extras: string[] = []
  for (const item of (input.affectations ?? []).slice(0, 3)) {
    const level_ = ALERT_LABEL[item.level]
    extras.push(basic
      ? `Una comisión registró en ${zone} una afectación por ${item.typeLabel.toLowerCase()} con nivel de advertencia ${level_}.${item.notes ? ` Nota técnica: «${item.notes}».` : ''}`
      : `Afectación registrada en ${zone}: ${item.typeLabel}, nivel ${level_}${item.by ? ` (${item.by})` : ''}.${item.notes ? ` Notas: «${item.notes}».` : ''} Registro local, sin verificación independiente.`)
  }
  for (const [name, unit, stat, digits] of [['temperatura', '°C', input.local?.temp, 1], ['lluvia', 'mm', input.local?.precip, 0]] as const) {
    if (!stat) continue
    const span = stat.from === stat.to ? stat.from : `${stat.from} a ${stat.to}`
    extras.push(basic
      ? `Además hay ${stat.n} ${stat.n === 1 ? 'registro local' : 'registros locales'} de ${name} cargados por comisiones (promedio ${fmt(stat.mean, digits)} ${unit}, ${span}). Todavía no se comparan con los datos de NASA.`
      : `Registros locales ${name === 'lluvia' ? 'PRECTOTCORR' : 'T2M'}: n = ${stat.n}, media ${fmt(stat.mean, digits)} ${unit}, ${span}; sin conciliar con la serie MERRA-2.`)
  }
  if (!precip && !temp) {
    return [basic
      ? `Para ${zone} todavía no hay datos de NASA POWER asociados, así que no se puede explicar cómo cambió el clima ahí. Podés pedir la información con el botón de la tarjeta del mapa.`
      : `${zone}: sin datos NASA POWER asociados (cantón sin sector climático ni celda seleccionada). No se genera síntesis de serie; solicitar la información a las comisiones.`, ...extras]
  }
  const paragraphs: string[] = []
  const years = `${range[0]} y ${range[1]}`
  if (basic) {
    const parts: string[] = []
    if (precip?.slope != null && precip.mean != null) {
      parts.push(Math.abs(precip.slope) < 0.02 * precip.mean ? 'la lluvia anual casi no cambió'
        : `la lluvia anual ${precip.slope > 0 ? 'subió' : 'bajó'} unos ${fmt(Math.abs(precip.slope), 0)} mm cada 10 años`)
    }
    if (temp?.slope != null) {
      parts.push(Math.abs(temp.slope) < 0.05 ? 'la temperatura casi no cambió'
        : `la temperatura ${temp.slope > 0 ? 'subió' : 'bajó'} cerca de ${fmt(Math.abs(temp.slope), 2)} °C cada 10 años`)
    }
    paragraphs.push(parts.length ? `En ${zone}, entre ${years}, ${parts.join(' y ')}.`
      : `En ${zone} no hay años suficientes entre ${years} para ver una tendencia. Ampliá el rango.`)
    if (enso?.start) {
      const rain = enso.precip == null ? '' : Math.abs(enso.precip) < 1 ? 'llovió casi lo habitual'
        : `llovió ${fmt(Math.abs(enso.precip), 0)} mm al mes ${enso.precip < 0 ? 'menos' : 'más'} de lo habitual`
      const heat = enso.temp == null ? '' : Math.abs(enso.temp) < 0.05 ? 'la temperatura fue casi la habitual'
        : `la temperatura estuvo ${fmt(Math.abs(enso.temp), 1)} °C ${enso.temp < 0 ? 'por debajo' : 'por encima'} de lo habitual`
      const joined = [rain, heat].filter(Boolean).join(' y ')
      if (joined) paragraphs.push(`Durante El Niño de ${enso.start} a ${enso.end}, en esta zona ${joined}. Es una comparación descriptiva: no prueba que El Niño sea la causa.`)
    }
    paragraphs.push(`Qué tan seguros estamos: confianza ${CONFIDENCE_LABEL[input.confidence]}. Los datos vienen de satélites y modelos de NASA, no de estaciones locales${input.stations === 0 ? ' (todavía no hay estaciones vinculadas)' : ''}.`)
  } else {
    const line = (name: string, unit: string, stats: VarStats, digits: number) => {
      const own = stats.slope == null ? 'sin pendiente (n insuficiente)' : `pendiente OLS descriptiva ${fmt(stats.slope, digits)} ${unit}/década`
      const official = stats.official == null ? '' : `; serie 1981–2024: ${fmt(stats.official, digits)} ${unit}/década, ${stats.significant === null ? 'sin prueba' : stats.significant ? 'significativa al 5 % (BY)' : 'no significativa al 5 % (BY)'}`
      return `${name}: ${own}, media ${stats.mean == null ? 'sin dato' : fmt(stats.mean, digits)} ${unit} (n = ${stats.n})${official}`
    }
    const rows: string[] = []
    if (precip) rows.push(line('PRECTOTCORR', 'mm/año', precip, 0))
    if (temp) rows.push(line('T2M', '°C', temp, 2))
    paragraphs.push(`${zone}${input.regionName ? ` (${input.regionName})` : ''}, ${range[0]}–${range[1]}. ${rows.join('. ')}.`)
    if (enso?.start) {
      const bits = [enso.precip != null ? `PRECTOTCORR ${fmt(enso.precip, 1)} mm/mes` : '', enso.temp != null ? `T2M ${fmt(enso.temp, 2)} °C` : ''].filter(Boolean)
      if (bits.length) paragraphs.push(`Episodio ENSO ${enso.start} a ${enso.end} (IMN): anomalía mensual media frente a la climatología 1981–2010 · ${bits.join(' · ')}. Comparación descriptiva, sin atribución causal.`)
    }
    paragraphs.push(`Calidad: continuidad ${fmt(input.continuityPct * 100, 0)} %, celdas con datos ${fmt(input.coveragePct * 100, 0)} %, estaciones vinculadas ${input.stations}; confianza ${CONFIDENCE_LABEL[input.confidence]}. Reanálisis MERRA-2: la precipitación requiere cautela y no equivale a estaciones locales.`)
  }
  return [...paragraphs, ...extras]
}
