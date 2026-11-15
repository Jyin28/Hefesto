import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import { fmt, ols, usable } from './analysis'
import type { Point, Range } from './analysis'
import type { GeoCell, Layer, LayerVar } from './data'
import { t } from './i18n'

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

/** Los textos son getters: se leen en el idioma activo cada vez que se usan (META se declara una sola vez, al cargar el módulo). */
export const META: Record<LayerVar, Meta> = {
  T2M: {
    get name() { return t('Temperatura', 'Temperature') }, valueTitle: year => t(`Temperatura promedio en ${year}`, `Average temperature in ${year}`),
    get slopeTitle() { return t('Cambio de temperatura', 'Temperature change') },
    unit: '°C', slopeUnit: '°C', digits: 1, slopeDigits: 2, flat: 0.03, same: 0.3,
    get more() { return t('más cálido', 'warmer') }, get less() { return t('más fresco', 'cooler') },
    values: ['#38BDF8', '#fef3c7', '#f59e0b', '#dc2626'], slope: [SKY, PAPER, AMBER],
    get about() { return t('Temperatura del aire a 2 metros del suelo, promediada en todo el año.', 'Air temperature 2 meters above the ground, averaged over the whole year.') },
  },
  PRECTOTCORR: {
    get name() { return t('Lluvia', 'Rain') }, valueTitle: year => t(`Lluvia total en ${year}`, `Total rainfall in ${year}`),
    get slopeTitle() { return t('Cambio de la lluvia anual', 'Change in annual rainfall') },
    unit: 'mm', slopeUnit: 'mm', digits: 0, slopeDigits: 0, flat: 20, same: 100,
    get more() { return t('más lluvioso', 'rainier') }, get less() { return t('más seco', 'drier') },
    values: ['#f1f5f9', '#7dd3fc', '#0369a1', '#1e3a8a'], slope: [AMBER, PAPER, SKY],
    get about() { return t('Lluvia total que cae en el año, en milímetros (1 mm = 1 litro por metro cuadrado).', 'Total rain that falls in the year, in millimeters (1 mm = 1 liter per square meter).') },
  },
  RH2M: {
    get name() { return t('Humedad', 'Humidity') }, valueTitle: year => t(`Humedad del aire en ${year}`, `Air humidity in ${year}`),
    get slopeTitle() { return t('Cambio de la humedad del aire', 'Change in air humidity') },
    unit: '%', get slopeUnit() { return t('puntos de humedad', 'humidity points') }, digits: 1, slopeDigits: 1, flat: 0.15, same: 1.5,
    get more() { return t('más húmedo', 'more humid') }, get less() { return t('menos húmedo', 'less humid') },
    values: ['#dcfce7', '#86efac', '#22c55e', '#14532d'], slope: ['#b45309', PAPER, '#16a34a'],
    get about() { return t('Humedad relativa del aire a 2 metros del suelo: qué tan cargado de vapor de agua está, de 0 a 100 %.', 'Relative humidity of the air 2 meters above the ground: how loaded with water vapor it is, from 0 to 100 %.') },
  },
  UV: {
    get name() { return t('Radiación UV', 'UV radiation') }, valueTitle: year => t(`Radiación UV (promedio del día) en ${year}`, `UV radiation (daily average) in ${year}`),
    get slopeTitle() { return t('Cambio de la radiación UV', 'Change in UV radiation') },
    unit: '', get slopeUnit() { return t('puntos del índice UV', 'UV index points') }, digits: 2, slopeDigits: 2, flat: 0.01, same: 0.03,
    get more() { return t('más radiación UV', 'more UV radiation') }, get less() { return t('menos radiación UV', 'less UV radiation') },
    values: ['#ede9fe', '#a78bfa', '#7c3aed', '#4c1d95'], slope: ['#94a3b8', PAPER, '#7c3aed'],
    get about() { return t('Índice UV promedio de las 24 horas del día (incluye la noche), por eso es mucho más bajo que el valor del mediodía que se anuncia en las noticias.', 'Average UV index over the 24 hours of the day (including the night), which is why it is much lower than the midday value announced in the news.') },
  },
}

/** De dónde salen los datos del mapa: la malla de NASA POWER o la de ERA5-Land del CDS. Solo cambia el texto del UV. */
export type Source = 'nasa' | 'cds'
/** El UV del CDS es energía (W/m² de UV-A + UV-B, promedio de 24 h), no el índice UV de NASA: otra unidad y otra escala. */
const CDS_UV: Meta = {
  // Sin `...META.UV`: copiar con spread evaluaría los getters al cargar el módulo y congelaría el idioma.
  get name() { return META.UV.name }, get slopeTitle() { return META.UV.slopeTitle }, get more() { return META.UV.more }, get less() { return META.UV.less },
  values: META.UV.values, slope: META.UV.slope,
  unit: 'W/m²', slopeUnit: 'W/m²', digits: 1, slopeDigits: 2, flat: 0.05, same: 0.5,
  valueTitle: year => t(`Radiación UV que llega al suelo (promedio del día) en ${year}`, `UV radiation reaching the ground (daily average) in ${year}`),
  get about() { return t('Energía de radiación ultravioleta (UV-A y UV-B) que llega a cada metro cuadrado del suelo, promediada las 24 horas del día (incluye la noche). Se mide en W/m²; no es el índice UV que se anuncia en las noticias.', 'Energy of ultraviolet radiation (UV-A and UV-B) reaching each square meter of ground, averaged over the 24 hours of the day (including the night). It is measured in W/m²; it is not the UV index announced in the news.') },
}
export const metaFor = (variable: LayerVar, source: Source = 'nasa'): Meta => source === 'cds' && variable === 'UV' ? CDS_UV : META[variable]

/** `approx` = 1 si el valor viene del punto de tierra más cercano (celda costera sin dato propio). */
export type GridProps = { id: string; region: string; has: number; v: number; nat: number; approx: number }
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
  const approximate = new Set(layer?.filled)
  const lines: Feature<Polygon, GridProps>[] = []
  const land: Feature<Polygon | MultiPolygon, GridProps>[] = []
  let withData = 0
  for (const cell of gridCells ?? []) {
    const value = measure(layer?.cells[cell.id])
    const properties: GridProps = { id: cell.id, region: 'CR', has: value == null ? 0 : 1, v: value ?? 0, nat: national ?? 0, approx: approximate.has(cell.id) ? 1 : 0 }
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
    ? `${meta.slopeTitle} ${t('cada 10 años', 'every 10 years')} (${grid.range[0]}–${grid.range[1]})${meta.slopeUnit ? ` · ${meta.slopeUnit}` : ''}`
    : `${meta.valueTitle(grid.year)}${meta.unit ? ` (${meta.unit})` : ''}`
}

const withUnit = (text: string, unit: string) => unit === '%' ? `${text} %` : unit ? `${text} ${unit}` : text

/** Frase para la gente general: «Cambio de temperatura: subió 0,2 °C cada 10 años (1981–2024)» (en inglés, «rose 0.2 °C every 10 years»). */
export function describe(variable: LayerVar, mode: LayerMode, value: number, national: number, grid: Pick<LayerGrid, 'range' | 'year'>,
  source: Source = 'nasa'): string {
  const meta = metaFor(variable, source)
  if (mode === 'slope') {
    const [from, to] = grid.range
    if (Math.abs(value) < meta.flat) return t(`${meta.slopeTitle}: casi no cambió entre ${from} y ${to}`, `${meta.slopeTitle}: barely changed between ${from} and ${to}`)
    return t(`${meta.slopeTitle}: ${value > 0 ? 'subió' : 'bajó'} ${withUnit(fmt(Math.abs(value), meta.slopeDigits), meta.slopeUnit)} cada 10 años (${from}–${to})`,
      `${meta.slopeTitle}: ${value > 0 ? 'rose' : 'fell'} ${withUnit(fmt(Math.abs(value), meta.slopeDigits), meta.slopeUnit)} every 10 years (${from}–${to})`)
  }
  const diff = value - national
  const against = Math.abs(diff) < meta.same ? t('similar al promedio del país', 'similar to the national average') : t(`${diff > 0 ? meta.more : meta.less} que el promedio del país`, `${diff > 0 ? meta.more : meta.less} than the national average`)
  return `${meta.valueTitle(grid.year)}: ${withUnit(fmt(value, meta.digits), meta.unit)} · ${against}`
}

/** Valor de un año o cambio del rango para la serie nacional o de una celda (para paneles). */
export function seriesPoints(layer: Layer | undefined, cellId?: string): Point[] {
  if (!layer) return []
  const series = cellId ? layer.cells[cellId] : layer.national
  return series ? pointsOf(layer, series) : []
}
