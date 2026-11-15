import { META } from './layers'
import type { LayerMode } from './layers'
import type { Layer, LayerVar } from './data'
import { RangeSlider } from './RangeSlider'
import { t } from './i18n'

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
  return <section className="map-controls glass" aria-label={t('Controles del mapa', 'Map controls')}>
    <strong>{meta.name}</strong>
    <div className="segmented" role="group" aria-label={t('Qué mostrar en el mapa', 'What to show on the map')}>
      <button aria-pressed={mode === 'slope'} onClick={() => setMode('slope')}
        title={t('Colorea cuánto subió o bajó cada zona cada 10 años, dentro de los años que elijas.', 'Colors how much each area rose or fell every 10 years, within the years you choose.')}>{t('Cambio en el tiempo', 'Change over time')}</button>
      <button aria-pressed={mode === 'value'} onClick={() => setMode('value')}
        title={t('Colorea el valor que tuvo cada zona en un año específico.', 'Colors the value each area had in a specific year.')}>{t('Valor por año', 'Value by year')}</button>
    </div>
    {mode === 'slope'
      ? <RangeSlider value={range} onChange={setRange} min={min} max={max}
        title={t('Elegí desde qué año hasta qué año se calcula el cambio. El mapa se actualiza al instante.', 'Choose from which year to which year the change is calculated. The map updates instantly.')} />
      : <div className="range" title={t('Elegí el año que querés ver. El mapa se actualiza al instante.', 'Choose the year you want to see. The map updates instantly.')}>
        <div className="range-label"><span>{min}</span><span className="year-big">{shown}</span><span>{max}</span></div>
        <input className="year-slider" type="range" aria-label={t('Año a mostrar', 'Year to show')} min={min} max={max} value={shown}
          onChange={event => setYear(Number(event.target.value))} />
      </div>}
    {layer?.resampled && <p className="muted">{t('NASA publica esta capa en cuadros de 1° (unos 110 km): varias zonas del mapa comparten el mismo valor.', 'NASA publishes this layer in 1° squares (about 110 km): several areas of the map share the same value.')}</p>}
    {min > 1981 && <p className="muted">{t(`NASA tiene esta capa solo desde ${min}.`, `NASA only has this layer since ${min}.`)}</p>}
  </section>
}
