import { t } from './i18n'

export const MIN_YEAR = 1981
export const MAX_YEAR = 2024

export function RangeSlider({ value, onChange, title, min = MIN_YEAR, max = MAX_YEAR }: {
  value: [number, number]; onChange: (value: [number, number]) => void; title?: string; min?: number; max?: number
}) {
  // Un rango guardado fuera de los límites (por ejemplo 1981 con una capa que empieza en 2001) se ve recortado.
  const from = Math.min(Math.max(value[0], min), max)
  const to = Math.min(Math.max(value[1], min), max)
  const span = Math.max(1, max - min)
  const left = ((from - min) / span) * 100
  const right = ((to - min) / span) * 100
  return <div className="range" title={title}>
    <div className="range-label"><span>{min}</span><span>{from} — {to}</span><span>{max}</span></div>
    <div className="range-track">
      <div className="range-fill" style={{ left: `${left}%`, width: `${right - left}%` }} />
      <input type="range" aria-label={t('Año inicial', 'Start year')} min={min} max={max} value={from}
        onChange={event => onChange([Math.min(Number(event.target.value), to), to])} />
      <input type="range" aria-label={t('Año final', 'End year')} min={min} max={max} value={to}
        onChange={event => onChange([from, Math.max(Number(event.target.value), from)])} />
    </div>
  </div>
}
