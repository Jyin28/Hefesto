import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson'

export const regions = [
  { id: 'CR_PN', name: 'Sector Pacífico Norte' },
  { id: 'CR_CAR', name: 'Sector Caribe' },
] as const
export type Region = typeof regions[number]['id']
export type Variable = 'PRECTOTCORR' | 'T2M'
export type Canton = { name: string; province: string; regionId?: Region }
export type Boundaries = FeatureCollection<Polygon | MultiPolygon, { code: string; name: string; province?: string }>
export type Notice = {
  id: string; cantonCodes: string[]; title: string; summary: string; source: string;
  sourceUrl: string; publishedAt: string; expiresAt?: string; communities: string[]
}
export type Local = {
  cantons: Record<string, Canton>
  notices: Notice[]
  operators: { cantonCodes: string[]; name: string; phone?: string; communities: string[]; sourceId?: string }[]
  waterCoverage?: WaterCoverage[]
  distribution?: Distribution[]
  sources?: Record<string, Source>
}
type Source = { label: string; url: string }
export type WaterCoverage = {
  cantonCode: string; geography: string; geographyLevel: string; year: number; indicator: string;
  value: number; unit: string; numerator: number; denominator: number; sourceId: string
}
export type Distribution = {
  cantonCode: string; year: number; value: number; unit: string; indicator: string;
  operator: string; limitation: string; sourceId: string
}
type WindowStats = {
  start_year: number; end_year: number; mean: number | null; n_years: number;
  slope_per_decade: number | null
}
export type Cell = {
  id: string; lat: number; lon: number; bbox: [number, number, number, number]
  window_a_mean: number | null; window_b_mean: number | null
  enso_mean_anomaly: number | null; enso_mean_vs_neutral: number | null
  long_term_slope: number | null; significant: boolean | null
}
export type Climate = {
  bbox: [number, number, number, number]; source: string; sourceUrl: string
  series: { year: number; value: number | null }[]
  comparison: { window_a: WindowStats; window_b: WindowStats; mean_diff_b_minus_a: number | null;
    slope_diff_b_minus_a: number | null } | null
  trend: { slope_per_decade: number | null; n_years: number; significant: boolean | null;
    p_adjusted: number | null; ci_low: number | null; ci_high: number | null; slope_unit: string }
  cells: Cell[]
  evidence: { mann_kendall: { slope_per_decade: number | null; p_adjusted: number | null } }
  methods_disagree: boolean | null
  enso: { status: string; unit?: string; episode?: { start: string; end: string; sources: string[] };
    neutral_window?: [string, string] | null; neutral_sources?: string[];
    months: { date: string; value: number | null; normal: number | null; neutral: number | null;
      anomaly: number | null; vs_neutral: number | null }[] }
  limitations: string[]
  water_coverage: WaterCoverage[]
  distribution: Distribution[]
  forecast: { status: string; message?: string; source_url?: string; unit?: string; forecast?: number | null;
    target?: string; model_mae?: number; baseline_mae?: number }
}
export type Snapshot = {
  climate: Record<Region, Record<Variable, Climate>>
  cells?: Record<Region, Record<string, Record<Variable, Climate>>>
  local: Local
}

export async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

const staticRoot = `${import.meta.env.BASE_URL}data/`
export const getSnapshot = (signal: AbortSignal) => getJson<Snapshot>(`${staticRoot}snapshot.json`, signal)
export const getBoundaries = (signal: AbortSignal) => getJson<Boundaries>(`${staticRoot}cantones.geojson`, signal)
