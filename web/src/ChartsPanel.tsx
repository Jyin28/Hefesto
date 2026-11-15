import { project } from './analysis'
import { ChartTile, Tile } from './Bento'
import type { Level, MapMode } from './copy'
import type { CdsData, Climate, Layer, LayerVar, Variable } from './data'
import { ForecastTile } from './Forecast'
import type { ForecastRow } from './Forecast'
import { metaFor, seriesPoints } from './layers'
import type { LayerMode, Source } from './layers'
import { MAX_YEAR, MIN_YEAR, RangeSlider } from './RangeSlider'
import { SeriesChart } from './SeriesChart'

const TONE: Record<LayerVar, 'water' | 'emerald'> = { T2M: 'emerald', PRECTOTCORR: 'water', UV: 'water', RH2M: 'emerald' }

/** Tarjeta de una capa anual (Tile + SeriesChart). Sirve para UV/Humedad de NASA y para las cuatro capas del CDS. */
function LayerChartCard({ variable, layer, cell, range, source = 'nasa' }: {
  variable: LayerVar; layer?: Layer; cell: string; range: [number, number]; source?: Source
}) {
  const meta = metaFor(variable, source)
  if (!layer) return <Tile title={meta.name}><p className="empty">Todavía no se cargó esta capa {source === 'cds' ? 'del CDS de Copernicus' : 'de NASA POWER'}.</p></Tile>
  const points = seriesPoints(layer, cell || undefined)
  const unit = variable === 'PRECTOTCORR' ? 'mm por año' : variable === 'UV' && source === 'nasa' ? 'índice UV' : meta.unit
  return <Tile title={meta.name}>
    <SeriesChart series={points} range={range} unit={unit} tone={TONE[variable]} label={`${meta.name} anual`} digits={meta.digits} />
    <p className="muted">{meta.about}</p>
  </Tile>
}

/**
 * Panel derecho: en el mapa NASA POWER, las 4 gráficas (temperatura, UV, lluvia, humedad) siempre juntas.
 * En «Datos CDS», las mismas cuatro gráficas con las capas de Copernicus (sin proyección: esa usa las fichas de NASA).
 * En «Datos nacionales», solo lluvia y temperatura, y todavía sin datos reales (a propósito, por ahora).
 */
export function ChartsPanel({ mapMode, level, zoneName, climateBy, uvLayer, humedadLayer, cds, cell,
  range, setRange, layerMode, setLayerMode, year, setYear }: {
  mapMode: MapMode; level: Level; zoneName: string; climateBy: Record<Variable, Climate | undefined>
  uvLayer?: Layer; humedadLayer?: Layer; cds?: CdsData; cell: string
  range: [number, number]; setRange: (range: [number, number]) => void
  layerMode: LayerMode; setLayerMode: (mode: LayerMode) => void; year: number; setYear: (year: number) => void
}) {
  const shownYear = Math.min(Math.max(year, MIN_YEAR), MAX_YEAR)
  const controls = <Tile title="Controles del mapa">
    <div className="segmented" role="group" aria-label="Qué mostrar en el mapa">
      <button aria-pressed={layerMode === 'slope'} onClick={() => setLayerMode('slope')}
        title="Colorea cuánto subió o bajó cada zona cada 10 años, dentro de los años que elijas.">Cambio en el tiempo</button>
      <button aria-pressed={layerMode === 'value'} onClick={() => setLayerMode('value')}
        title="Colorea el valor que tuvo cada zona en un año específico.">Valor por año</button>
    </div>
    {layerMode === 'slope'
      ? <RangeSlider value={range} onChange={setRange} title="Elegí desde qué año hasta qué año se calcula el cambio. El mapa se actualiza al instante." />
      : <div className="range" title="Elegí el año que querés ver. El mapa se actualiza al instante.">
        <div className="range-label"><span>{MIN_YEAR}</span><span className="year-big">{shownYear}</span><span>{MAX_YEAR}</span></div>
        <input className="year-slider" type="range" aria-label="Año a mostrar" min={MIN_YEAR} max={MAX_YEAR} value={shownYear}
          onChange={event => setYear(Number(event.target.value))} />
      </div>}
  </Tile>
  if (mapMode === 'cds') return <>
    {controls}
    {(['T2M', 'UV', 'PRECTOTCORR', 'RH2M'] as LayerVar[]).filter(variable => variable !== 'UV' || cds?.layers.UV).map(variable =>
      <LayerChartCard key={variable} variable={variable} layer={cds?.layers[variable]} cell={cell} range={range} source="cds" />)}
  </>
  if (mapMode === 'cantones') return <>
    {controls}
    <ChartTile variable="PRECTOTCORR" level={level} series={[]} range={range} />
    <ChartTile variable="T2M" level={level} series={[]} range={range} />
    <LayerChartCard variable="UV" layer={uvLayer} cell={cell} range={range} />
    <LayerChartCard variable="RH2M" layer={humedadLayer} cell={cell} range={range} />
  </>
  const rows: ForecastRow[] = (['T2M', 'PRECTOTCORR'] as Variable[]).flatMap(variable => {
    const climate = climateBy[variable]
    return climate ? [{ variable, projection: project(climate.series, variable, range), localStatus: climate.forecast.status }] : []
  })
  return <>
    {controls}
    <ChartTile variable="T2M" level={level} series={climateBy.T2M?.series ?? []} range={range} />
    <LayerChartCard variable="UV" layer={uvLayer} cell={cell} range={range} />
    <ChartTile variable="PRECTOTCORR" level={level} series={climateBy.PRECTOTCORR?.series ?? []} range={range} />
    <LayerChartCard variable="RH2M" layer={humedadLayer} cell={cell} range={range} />
    <ForecastTile level={level} zoneName={zoneName} rows={rows} />
  </>
}
