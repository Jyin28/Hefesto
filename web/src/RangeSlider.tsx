export const MIN_YEAR = 1981
export const MAX_YEAR = 2024

export function RangeSlider({ value, onChange, title }: {
  value: [number, number]; onChange: (value: [number, number]) => void; title?: string
}) {
  const [from, to] = value
  const span = MAX_YEAR - MIN_YEAR
  const left = ((from - MIN_YEAR) / span) * 100
  const right = ((to - MIN_YEAR) / span) * 100
  return <div className="range" title={title}>
    <div className="range-label"><span>{MIN_YEAR}</span><span>{from} — {to}</span><span>{MAX_YEAR}</span></div>
    <div className="range-track">
      <div className="range-fill" style={{ left: `${left}%`, width: `${right - left}%` }} />
      <input type="range" aria-label="Año inicial" min={MIN_YEAR} max={MAX_YEAR} value={from}
        onChange={event => onChange([Math.min(Number(event.target.value), to), to])} />
      <input type="range" aria-label="Año final" min={MIN_YEAR} max={MAX_YEAR} value={to}
        onChange={event => onChange([from, Math.max(Number(event.target.value), from)])} />
    </div>
  </div>
}
