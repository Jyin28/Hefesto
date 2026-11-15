import { META } from './layers'
import type { LayerMode } from './layers'
import type { Layer, LayerVar } from './data'
import { RangeSlider } from './RangeSlider'

/**
 * Panel del mapa nacional: alterna entre «cómo cambia» (pendiente en un rango de años) y «valor de un año».
 * No tiene botón de aplicar: el mapa se repinta con cada movimiento de los controles.
 */
export function MapControls({ variable, layer, mode, setMode, range, setRange, year, setYear }: {
  variable: LayerVar; layer?: Layer; mode: LayerMode; setMode: (mode: LayerMode) => void
  range: [number, number]; setRange: (range: [number, number]) => void; year: number; setYear: (year: number) => void
}) {
  const meta = META[variable]
  const min = layer?.start ?? 1981
  const max = layer?.end ?? 2024
  const shown = Math.min(Math.max(year, min), max)
  return <section className="map-controls glass" aria-label="Controles del mapa">
    <strong>{meta.name}</strong>
    <div className="segmented" role="group" aria-label="Qué mostrar en el mapa">
      <button aria-pressed={mode === 'slope'} onClick={() => setMode('slope')}
        title="Colorea cuánto subió o bajó cada zona cada 10 años, dentro de los años que elijas.">Cambio en el tiempo</button>
      <button aria-pressed={mode === 'value'} onClick={() => setMode('value')}
        title="Colorea el valor que tuvo cada zona en un año específico.">Valor por año</button>
    </div>
    {mode === 'slope'
      ? <RangeSlider value={range} onChange={setRange} min={min} max={max}
        title="Elegí desde qué año hasta qué año se calcula el cambio. El mapa se actualiza al instante." />
      : <div className="range" title="Elegí el año que querés ver. El mapa se actualiza al instante.">
        <div className="range-label"><span>{min}</span><span className="year-big">{shown}</span><span>{max}</span></div>
        <input className="year-slider" type="range" aria-label="Año a mostrar" min={min} max={max} value={shown}
          onChange={event => setYear(Number(event.target.value))} />
      </div>}
    {layer?.resampled && <p className="muted">NASA publica esta capa en cuadros de 1° (unos 110 km): varias zonas del mapa comparten el mismo valor.</p>}
    {min > 1981 && <p className="muted">NASA tiene esta capa solo desde {min}.</p>}
  </section>
}
