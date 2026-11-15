import { getJson } from './data'

/** Forma de `web/public/data/predicciones.json` (lo escribe `python -m src.predictions`). */
export type RegionId = 'CR' | 'CR_PN' | 'CR_CAR'
export type ForecastRow = {
  target_month: string; lead_months: number; status: string
  estimate: number | null; lower90: number | null; upper90: number | null
  validation: { test_skill?: number; coverage90_recent?: number; skill_uncertain?: boolean } | null
  reference: { mean: number; p10: number; p90: number; n_years: number; period: string }
}
export type VariableBlock = { unit: string; source: string; data_through: string; regions: Record<RegionId, { model: string | null; rows: ForecastRow[] }> }
export type RainAnalogMonth = { month: string; n_years: number; mean_mm: number; reference_mean_mm: number; anomaly_pct: number; share_above_median: number; share_above_100mm: number }
export type Episode = { start: string; end: string; months: number; peak: number }
export type EnsoBlock = {
  status: 'active' | 'none'; definition: string
  latest: { month: string; value: number }
  series: { month: string; value: number }[]
  history: (Episode & { peak_month: string })[]
  start?: string; months_so_far?: number; category?: string; rising?: boolean
  peak_so_far?: { month: string; value: number }
  analog?: {
    basis: string; n: number; events: Episode[]
    duration_months: { p10: number; median: number; p90: number; min: number; max: number }
    end_window: { earliest: string; typical: string; latest: string }
    peak_window?: { earliest: string; typical: string; latest: string; n: number }
  }
}
export type Predictions = {
  schema: number; generated_at: string; forecast_start: string; calibration_date: string; data_through: string; roni_through: string
  region_names: Record<RegionId, string>
  enso: EnsoBlock
  variables: Record<'T2M' | 'PRECTOTCORR' | 'RH2M' | 'UV', VariableBlock>
  rain_analog: Partial<Record<RegionId, { criterion: string; years: number[]; months: RainAnalogMonth[] }>>
  temperature_validation: Record<string, { model: string; max_contiguous_horizon: number; horizons: Record<string, { test_skill: number; coverage90_recent: number; skill_uncertain: boolean }> }>
  limits: string[]
}
export type TelegramAlert = { kind: 'heat' | 'rain' | 'nino'; canton: string; province: string; zone: string; region: string; text: string; status: 'preview' | 'sent' | 'pending' | 'failed'; sent_at?: string }

const staticRoot = `${import.meta.env.BASE_URL}data/`
export const getPredictions = (signal: AbortSignal) => getJson<Predictions>(`${staticRoot}predicciones.json`, signal)
/** Vista previa o resultado de los avisos de Telegram (sin @usuarios). Puede no existir todavía. */
export const getAlerts = (signal: AbortSignal) => getJson<{ updated_at: string; alerts: TelegramAlert[] }>(`${staticRoot}alertas.json`, signal)

// --- Formato (es-CR: coma decimal) ---
export const num = (value: number, digits = 1) => value.toLocaleString('es-CR', { minimumFractionDigits: digits, maximumFractionDigits: digits })
export const signed = (value: number, digits = 1) => `${value < 0 ? '−' : '+'}${num(Math.abs(value), digits)}`
const date = (label: string) => { const [year, month] = label.split('-').map(Number); return new Date(year, month - 1, 1) }
export const monthLong = (label: string) => date(label).toLocaleDateString('es-CR', { month: 'long', year: 'numeric' })
export const monthShort = (label: string) => date(label).toLocaleDateString('es-CR', { month: 'short', year: 'numeric' }).replace('.', '')
export const monthOnly = (label: string) => date(label).toLocaleDateString('es-CR', { month: 'short' }).replace('.', '')

export const REGIONS: RegionId[] = ['CR', 'CR_PN', 'CR_CAR']
export const REGION_SHORT: Record<RegionId, string> = { CR: 'Costa Rica', CR_PN: 'Pacífico Norte', CR_CAR: 'Caribe' }

/** Diferencia con lo normal del primer mes con pronóstico de temperatura (las cifras redondeadas que se ven, para que cuadren). */
export function firstTemperature(data: Predictions, region: RegionId) {
  const row = data.variables.T2M.regions[region].rows.find(item => item.estimate !== null)
  if (!row || row.estimate === null || row.lower90 === null || row.upper90 === null) return undefined
  return { row, estimate: row.estimate, low: row.lower90, high: row.upper90, normal: row.reference.mean,
    anomaly: Math.round(row.estimate * 10) / 10 - Math.round(row.reference.mean * 10) / 10, aboveP90: row.estimate > row.reference.p90 }
}

/** Lluvia de los años análogos de El Niño frente a lo normal, para un mes dado. */
export const rainAnalog = (data: Predictions, region: RegionId, month: string) => data.rain_analog[region]?.months.find(item => item.month === month)
