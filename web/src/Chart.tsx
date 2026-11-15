import { useEffect, useRef, useState } from 'react'
import type { Climate } from './data'

export function Chart({ data, unit }: { data: Climate; unit: string }) {
  const container = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    const element = container.current
    if (!element) return
    let active = true
    let cleanup: (() => void) | undefined
    setFailed(false)
    import('plotly.js-basic-dist-min').then(({ default: plot }) => {
      if (!active) return
      cleanup = () => plot.purge(element)
      return plot.newPlot(element, [{
        x: data.series.map(point => point.year), y: data.series.map(point => point.value),
        type: 'scatter', mode: 'lines', line: { color: '#147967', width: 2.5 },
        hovertemplate: `%{x}: %{y:.2f} ${unit}<extra></extra>`, connectgaps: false,
      }], {
        height: 248, margin: { t: 12, r: 12, b: 38, l: 55 },
        paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        font: { family: 'system-ui, sans-serif', color: '#315651' },
        xaxis: { gridcolor: '#edf1ec', dtick: 10, tickformat: 'd' },
        yaxis: { gridcolor: '#edf1ec', title: { text: unit }, fixedrange: true },
      }, { responsive: true, displayModeBar: false })
    }).catch(() => { if (active) setFailed(true) })
    return () => { active = false; cleanup?.() }
  }, [data, unit])
  return <><div ref={container} role="img" aria-label={`Serie histórica anual en ${unit}`} />
    {failed && <p className="empty">El gráfico no pudo cargarse.</p>}</>
}
