import { useMemo, useState } from 'react'
import type { MapMode } from './copy'
import type { Canton, Operator } from './data'

const collator = new Intl.Collator('es-CR')

/**
 * Ayudante de búsqueda en cascada. Mapa NASA POWER: Provincia → Cantón. Mapa de cuencas: Provincia → Cantón → Distrito → ASADA.
 * Cada paso mueve el mapa: la provincia y el cantón se acercan solos; los distritos no tienen polígono propio, así
 * que al elegir uno el mapa se queda en su cantón.
 */
export function PlacePicker({ mode, choices, asadas, onProvince, onCanton, onAsada }: {
  mode: MapMode; choices: Map<string, Canton>; asadas: Operator[]
  onProvince: (province: string) => void; onCanton: (code: string) => void; onAsada: (operator: Operator) => void
}) {
  const [province, setProvince] = useState('')
  const [canton, setCanton] = useState('')
  const [district, setDistrict] = useState('')
  const withAsadas = mode === 'cantones'

  const provinces = useMemo(() => [...new Set([...choices.values()].map(item => item.province).filter(Boolean))].sort(collator.compare), [choices])
  const cantons = useMemo(() => [...choices].filter(([, item]) => item.province === province).sort((a, b) => collator.compare(a[1].name, b[1].name)), [choices, province])
  const inCanton = useMemo(() => asadas.filter(item => item.cantonCode === canton), [asadas, canton])
  const districts = useMemo(() => [...new Set(inCanton.map(item => item.district))].sort(collator.compare), [inCanton])
  const operators = useMemo(() => inCanton.filter(item => item.district === district).sort((a, b) => collator.compare(a.name, b.name)), [inCanton, district])
  const counts = useMemo(() => {
    const result = new Map<string, number>()
    for (const item of asadas) result.set(item.cantonCode, (result.get(item.cantonCode) ?? 0) + 1)
    return result
  }, [asadas])

  return <div className="place-picker glass" aria-label="Buscar por lugar">
    <label>Provincia
      <select value={province} onChange={event => { setProvince(event.target.value); setCanton(''); setDistrict(''); if (event.target.value) onProvince(event.target.value) }}>
        <option value="">Elegir provincia…</option>
        {provinces.map(item => <option key={item} value={item}>{item}</option>)}
      </select>
    </label>
    {province && <label>Cantón
      <select value={canton} onChange={event => { setCanton(event.target.value); setDistrict(''); if (event.target.value) onCanton(event.target.value) }}>
        <option value="">Elegir cantón…</option>
        {cantons.map(([code, item]) => <option key={code} value={code}>{item.name}{withAsadas ? ` (${counts.get(code) ?? 0})` : ''}</option>)}
      </select>
    </label>}
    {withAsadas && canton && (districts.length ? <label>Distrito
      <select value={district} onChange={event => setDistrict(event.target.value)}>
        <option value="">Elegir distrito…</option>
        {districts.map(item => <option key={item} value={item}>{item}</option>)}
      </select>
      <small className="muted">El mapa no dibuja distritos: se queda en el cantón.</small>
    </label> : <p className="muted">Este cantón no tiene operadores en el catálogo de SAGA.</p>)}
    {withAsadas && district && <label>ASADA u operador
      <select value="" onChange={event => { const found = operators.find(item => item.id === event.target.value); if (found) onAsada(found) }}>
        <option value="">Elegir operador…</option>
        {operators.map(item => <option key={item.id} value={item.id}>{item.name} · {item.type}</option>)}
      </select>
    </label>}
  </div>
}
