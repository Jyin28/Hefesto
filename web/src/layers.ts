import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import { fmt, ols, usable } from './analysis'
import type { Point, Range } from './analysis'
import type { GeoCell, Layer, LayerVar } from './data'

/** «slope» = cuánto cambia cada 10 años dentro de un rango de años; «value» = el valor de un año concreto. */
export type LayerMode = 'slope' | 'value'
export const LAYER_VARS: LayerVar[] = ['T2M', 'PRECTOTCORR', 'RH2M', 'UV']
export const MIN_SLOPE_YEARS = 10

const SKY = '#38BDF8'
const AMBER = '#f59e0b'
const PAPER = '#f8fafc'
const NO_DATA = '#e2e8f0'

type Meta = {
  /** Nombre corto para la gente. */
  name: string
  valueTitle: (year: number) => string
  slopeTitle: string
  /** Unidad escrita después del valor («21,3 °C»). */
  unit: string
  /** Cómo se dice el cambio cada 10 años («subió 0,2 °C…»). */
  slopeUnit: string
  digits: number; slopeDigits: number
  /** Cambios por década menores que esto se consideran «casi sin cambio». */
  flat: number
  /** Diferencia con el promedio del país que se considera «similar». */
  same: number
  more: string; less: string
  /** Escala secuencial para el valor de un año (de menos a más). */
  values: [string, string, string, string]
  /** Escala divergente para el cambio (baja, sin cambio, sube). */
  slope: [string, string, string]
  about: string
}

export const META: Record<LayerVar, Meta> = {
  T2M: {
    name: 'Temperatura', valueTitle: year => `Temperatura promedio en ${year}`, slopeTitle: 'Cambio de temperatura',
    unit: '°C', slopeUnit: '°C', digits: 1, slopeDigits: 2, flat: 0.03, same: 0.3, more: 'más cálido', less: 'más fresco',
    values: ['#38BDF8', '#fef3c7', '#f59e0b', '#dc2626'], slope: [SKY, PAPER, AMBER],
    about: 'Temperatura del aire a 2 metros del suelo, promediada en todo el año.',
  },
  PRECTOTCORR: {
    name: 'Lluvia', valueTitle: year => `Lluvia total en ${year}`, slopeTitle: 'Cambio de la lluvia anual',
    unit: 'mm', slopeUnit: 'mm', digits: 0, slopeDigits: 0, flat: 20, same: 100, more: 'más lluvioso', less: 'más seco',
    values: ['#f1f5f9', '#7dd3fc', '#0369a1', '#1e3a8a'], slope: [AMBER, PAPER, SKY],
    about: 'Lluvia total que cae en el año, en milímetros (1 mm = 1 litro por metro cuadrado).',
  },
  RH2M: {
    name: 'Humedad', valueTitle: year => `Humedad del aire en ${year}`, slopeTitle: 'Cambio de la humedad del aire',
    unit: '%', slopeUnit: 'puntos de humedad', digits: 1, slopeDigits: 1, flat: 0.15, same: 1.5, more: 'más húmedo', less: 'menos húmedo',
    values: ['#dcfce7', '#86efac', '#22c55e', '#14532d'], slope: ['#b45309', PAPER, '#16a34a'],
    about: 'Humedad relativa del aire a 2 metros del suelo: qué tan cargado de vapor de agua está, de 0 a 100 %.',
  },
  UV: {
    name: 'Radiación UV', valueTitle: year => `Radiación UV (promedio del día) en ${year}`, slopeTitle: 'Cambio de la radiación UV',
    unit: '', slopeUnit: 'puntos del índice UV', digits: 2, slopeDigits: 2, flat: 0.01, same: 0.03, more: 'más radiación UV', less: 'menos radiación UV',
    values: ['#ede9fe', '#a78bfa', '#7c3aed', '#4c1d95'], slope: ['#94a3b8', PAPER, '#7c3aed'],
    about: 'Índice UV promedio de las 24 horas del día (incluye la noche), por eso es mucho más bajo que el valor del mediodía que se anuncia en las noticias.',
  },
}

/** De dónde salen los datos del mapa: la malla de NASA POWER o la de ERA5-Land del CDS. Solo cambia el texto del UV. */
export type Source = 'nasa' | 'cds'
/** El UV del CDS es energía (W/m² de UV-A + UV-B, promedio de 24 h), no el índice UV de NASA: otra unidad y otra escala. */
const CDS_UV: Meta = {
  ...META.UV, unit: 'W/m²', slopeUnit: 'W/m²', digits: 1, slopeDigits: 2, flat: 0.05, same: 0.5,
  valueTitle: year => `Radiación UV que llega al suelo (promedio del día) en ${year}`,
  about: 'Energía de radiación ultravioleta (UV-A y UV-B) que llega a cada metro cuadrado del suelo, promediada las 24 horas del día (incluye la noche). Se mide en W/m²; no es el índice UV que se anuncia en las noticias.',
}
export const metaFor = (variable: LayerVar, source: Source = 'nasa'): Meta => source === 'cds' && variable === 'UV' ? CDS_UV : META[variable]

export type GridProps = { id: string; region: string; has: number; v: number; nat: number }
export type LayerGrid = {
  lines: FeatureCollection<Polygon, GridProps>
  land: FeatureCollection<Polygon | MultiPolygon, GridProps>
  /** Dominio fijo de la escala de valores (todos los años y celdas) y extensión simétrica de la escala de cambio. */
  domain: [number, number]; extent: number
  withData: number; total: number
  /** Rango o año realmente usado, recortado a los años que tiene la capa. */
  range: Range; year: number
  national: number | null
}

const yearsOf = (layer: Layer) => Array.from({ length: layer.end - layer.start + 1 }, (_, index) => layer.start + index)
const pointsOf = (layer: Layer, series: (number | null)[]): Point[] => yearsOf(layer).map((year, index) => ({ year, value: series[index] ?? null }))

/** Cambio cada 10 años dentro del rango (mínimos cuadrados); null si hay menos de 10 años con dato. */
export function slopePerDecade(layer: Layer, series: (number | null)[], range: Range): number | null {
  const points = usable(pointsOf(layer, series), range)
  if (points.length < MIN_SLOPE_YEARS) return null
  const fit = ols(points)
  return fit ? fit.slope * 10 : null
}

export function clampRange(layer: Layer | undefined, range: Range): Range {
  if (!layer) return range
  const from = Math.min(Math.max(range[0], layer.start), layer.end)
  const to = Math.min(Math.max(range[1], layer.start), layer.end)
  return [Math.min(from, to), to]
}

export const clampYear = (layer: Layer | undefined, year: number) => layer ? Math.min(Math.max(year, layer.start), layer.end) : year

export function buildLayerGrid(layers: Partial<Record<LayerVar, Layer>> | undefined, variable: LayerVar, gridCells: GeoCell[] | undefined,
  mode: LayerMode, range: Range, year: number): LayerGrid {
  const layer = layers?.[variable]
  const effectiveRange = clampRange(layer, range)
  const effectiveYear = clampYear(layer, year)
  const valueOf = (series?: (number | null)[]) => layer && series ? series[effectiveYear - layer.start] ?? null : null
  const measure = (series?: (number | null)[]) => !layer || !series ? null
    : mode === 'slope' ? slopePerDecade(layer, series, effectiveRange) : valueOf(series)

  let lo = Infinity, hi = -Infinity, extent = 0
  for (const series of Object.values(layer?.cells ?? {})) {
    for (const value of series) if (value != null) { lo = Math.min(lo, value); hi = Math.max(hi, value) }
    const slope = layer ? slopePerDecade(layer, series, effectiveRange) : null
    if (slope != null) extent = Math.max(extent, Math.abs(slope))
  }
  const national = measure(layer?.national)
  const lines: Feature<Polygon, GridProps>[] = []
  const land: Feature<Polygon | MultiPolygon, GridProps>[] = []
  let withData = 0
  for (const cell of gridCells ?? []) {
    const value = measure(layer?.cells[cell.id])
    const properties: GridProps = { id: cell.id, region: 'CR', has: value == null ? 0 : 1, v: value ?? 0, nat: national ?? 0 }
    const [west, south, east, north] = cell.bbox
    const box: Polygon = { type: 'Polygon', coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]] }
    lines.push({ type: 'Feature', properties, geometry: box })
    // Las celdas totalmente de tierra (malla del CDS) no guardan polígono propio: su caja ya es su tierra.
    const geometry = cell.land ?? (cell.landFraction >= 0.999 ? box : null)
    if (geometry && cell.landFraction >= 0.01) {
      land.push({ type: 'Feature', properties, geometry })
      if (value != null) withData += 1
    }
  }
  return {
    lines: { type: 'FeatureCollection', features: lines }, land: { type: 'FeatureCollection', features: land },
    domain: Number.isFinite(lo) ? [lo, hi > lo ? hi : lo + 1] : [0, 1], extent: extent || 1,
    withData, total: land.length, range: effectiveRange, year: effectiveYear, national,
  }
}

/** Expresión de MapLibre que pinta cada celda con su valor; las celdas sin dato quedan en gris. */
export function colorExpression(variable: LayerVar, mode: LayerMode, grid: Pick<LayerGrid, 'domain' | 'extent'>): ExpressionSpecification {
  const meta = META[variable] // los colores no cambian entre fuentes
  const scale: unknown[] = mode === 'slope'
    ? [-grid.extent, meta.slope[0], 0, meta.slope[1], grid.extent, meta.slope[2]]
    : meta.values.flatMap((color, index) => [grid.domain[0] + ((grid.domain[1] - grid.domain[0]) * index) / 3, color])
  return ['case', ['==', ['get', 'has'], 1], ['interpolate', ['linear'], ['get', 'v'], ...scale], NO_DATA] as unknown as ExpressionSpecification
}

export function legendGradient(variable: LayerVar, mode: LayerMode) {
  const meta = META[variable]
  return `linear-gradient(90deg, ${(mode === 'slope' ? meta.slope : meta.values).join(', ')})`
}

export function legendTitle(variable: LayerVar, mode: LayerMode, grid: Pick<LayerGrid, 'range' | 'year'>, source: Source = 'nasa') {
  const meta = metaFor(variable, source)
  return mode === 'slope'
    ? `${meta.slopeTitle} cada 10 años (${grid.range[0]}–${grid.range[1]})${meta.slopeUnit ? ` · ${meta.slopeUnit}` : ''}`
    : `${meta.valueTitle(grid.year)}${meta.unit ? ` (${meta.unit})` : ''}`
}

const withUnit = (text: string, unit: string) => unit === '%' ? `${text} %` : unit ? `${text} ${unit}` : text

/** Frase para la gente general: «Cambio de temperatura: subió 0,2 °C cada 10 años (1981–2024)». */
export function describe(variable: LayerVar, mode: LayerMode, value: number, national: number, grid: Pick<LayerGrid, 'range' | 'year'>,
  source: Source = 'nasa'): string {
  const meta = metaFor(variable, source)
  if (mode === 'slope') {
    const [from, to] = grid.range
    if (Math.abs(value) < meta.flat) return `${meta.slopeTitle}: casi no cambió entre ${from} y ${to}`
    return `${meta.slopeTitle}: ${value > 0 ? 'subió' : 'bajó'} ${withUnit(fmt(Math.abs(value), meta.slopeDigits), meta.slopeUnit)} cada 10 años (${from}–${to})`
  }
  const diff = value - national
  const against = Math.abs(diff) < meta.same ? 'similar al promedio del país' : `${diff > 0 ? meta.more : meta.less} que el promedio del país`
  return `${meta.valueTitle(grid.year)}: ${withUnit(fmt(value, meta.digits), meta.unit)} · ${against}`
}

/** Valor de un año o cambio del rango para la serie nacional o de una celda (para paneles). */
export function seriesPoints(layer: Layer | undefined, cellId?: string): Point[] {
  if (!layer) return []
  const series = cellId ? layer.cells[cellId] : layer.national
  return series ? pointsOf(layer, series) : []
}
