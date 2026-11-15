import { getJson } from './data'
import { locale, t } from './i18n'

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
  /** Ids de las celdas NASA POWER de cada sector (mismo formato que `geo.json`). Una celda fuera de estas listas usa el promedio del país. */
  region_cells: Record<Exclude<RegionId, 'CR'>, string[]>
  enso: EnsoBlock
  variables: Record<'T2M' | 'PRECTOTCORR' | 'RH2M' | 'UV', VariableBlock>
  rain_analog: Partial<Record<RegionId, { criterion: string; years: number[]; months: RainAnalogMonth[] }>>
  temperature_validation: Record<string, { model: string; max_contiguous_horizon: number; horizons: Record<string, { test_skill: number; coverage90_recent: number; skill_uncertain: boolean; skill_ci95?: [number, number] }> }>
  limits: string[]
}

const staticRoot = `${import.meta.env.BASE_URL}data/`
export const getPredictions = (signal: AbortSignal) => getJson<Predictions>(`${staticRoot}predicciones.json`, signal)

/** Cantón con la celda NASA POWER que más lo cubre (lo escribe `npm run geo`). */
export type CantonIndexItem = { code: string; name: string; province: string; cell: string }
export const getCantonIndex = (signal: AbortSignal) => getJson<CantonIndexItem[]>(`${staticRoot}cantones-indice.json`, signal)

/** Sector de las predicciones que le toca a una celda: Pacífico Norte, Caribe o, si no está en ninguno, todo el país. */
export function regionForCell(data: Predictions, cell: string): RegionId {
  if (data.region_cells.CR_PN.includes(cell)) return 'CR_PN'
  if (data.region_cells.CR_CAR.includes(cell)) return 'CR_CAR'
  return 'CR'
}

/** «POWER:10.5:-85.625» → «10,5° N · 85,625° O» (en inglés, «10.5° N · 85.625° W») */
export function cellCoordinates(cell: string): string {
  const [, lat, lon] = cell.split(':')
  const degrees = (value: number) => Math.abs(value).toLocaleString(locale(), { maximumFractionDigits: 3 })
  return `${degrees(Number(lat))}° N · ${degrees(Number(lon))}° ${t('O', 'W')}`
}

// --- Formato (es-CR: coma decimal; en-US: punto decimal) ---
export const num = (value: number, digits = 1) => value.toLocaleString(locale(), { minimumFractionDigits: digits, maximumFractionDigits: digits })
export const signed = (value: number, digits = 1) => `${value < 0 ? '−' : '+'}${num(Math.abs(value), digits)}`
const date = (label: string) => { const [year, month] = label.split('-').map(Number); return new Date(year, month - 1, 1) }
export const monthLong = (label: string) => date(label).toLocaleDateString(locale(), { month: 'long', year: 'numeric' })
export const monthShort = (label: string) => date(label).toLocaleDateString(locale(), { month: 'short', year: 'numeric' }).replace('.', '')
export const monthOnly = (label: string) => date(label).toLocaleDateString(locale(), { month: 'short' }).replace('.', '')

export const REGIONS: RegionId[] = ['CR', 'CR_PN', 'CR_CAR']
/** Nombre corto de cada zona. Con getters para que siempre salga en el idioma activo. */
export const REGION_SHORT: Record<RegionId, string> = {
  get CR() { return 'Costa Rica' },
  get CR_PN() { return t('Pacífico Norte', 'North Pacific') },
  get CR_CAR() { return t('Caribe', 'Caribbean') },
}

// --- Textos que escribe el motor de Python en español: se traducen aquí (con el español como respaldo) ---
const DATA_TEXT: Record<string, string> = {
  'Episodio de El Niño: RONI ≥ 0,5 durante al menos 5 meses seguidos (NOAA).': 'El Niño episode: RONI ≥ 0.5 for at least 5 consecutive months (NOAA).',
  'Todo es regional (Costa Rica, Pacífico Norte y Caribe): no hay predicciones por cantón, celda ni ASADA.': 'Everything is regional (Costa Rica, North Pacific and Caribbean): there are no predictions per canton, grid cell or ASADA.',
  'Solo la temperatura tiene pronóstico experimental, y solo para los primeros meses: la validación no justifica más.': 'Only temperature has an experimental forecast, and only for the first months: validation does not justify more.',
  'Lluvia, humedad y UV son referencias históricas; los años análogos de El Niño son descriptivos, con pocos años.': 'Rain, humidity and UV are historical references; the El Niño analog years are descriptive, with few years.',
  'El rango de fechas de El Niño compara con episodios fuertes anteriores; no es un modelo dinámico del océano.': 'The El Niño date range compares with earlier strong episodes; it is not a dynamic ocean model.',
  'Sin validación contra estaciones locales. No usar para decidir racionamientos ni otras acciones operativas.': 'Not validated against local stations. Do not use to decide water rationing or other operational actions.',
  'Años con RONI de septiembre ≥ 1': 'Years with a September RONI ≥ 1',
}
export const fromData = (source: string) => t(source, DATA_TEXT[source] ?? source)

const CATEGORY_EN: Record<string, string> = { 'débil': 'weak', 'moderado': 'moderate', 'fuerte': 'strong', 'muy fuerte': 'very strong' }
/** Categoría del episodio de El Niño («muy fuerte» → «very strong»). */
export const ensoCategory = (category: string | undefined) => category ? t(category, CATEGORY_EN[category] ?? category) : ''

/** Diferencia con lo normal del primer mes con pronóstico de temperatura (las cifras redondeadas que se ven, para que cuadren). */
export function firstTemperature(data: Predictions, region: RegionId) {
  const row = data.variables.T2M.regions[region].rows.find(item => item.estimate !== null)
  if (!row || row.estimate === null || row.lower90 === null || row.upper90 === null) return undefined
  return { row, estimate: row.estimate, low: row.lower90, high: row.upper90, normal: row.reference.mean,
    anomaly: Math.round(row.estimate * 10) / 10 - Math.round(row.reference.mean * 10) / 10, aboveP90: row.estimate > row.reference.p90 }
}

/** Lluvia de los años análogos de El Niño frente a lo normal, para un mes dado. */
export const rainAnalog = (data: Predictions, region: RegionId, month: string) => data.rain_analog[region]?.months.find(item => item.month === month)
