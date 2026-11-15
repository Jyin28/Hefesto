import { useMemo, useState } from 'react'
import type { Canton, Operator } from './data'
import { collate, t } from './i18n'

/**
 * Ayudante de búsqueda en cascada. Sin ASADAs: Provincia → Cantón. Con ASADAs (mapa de cuencas y predicciones):
 * Provincia → Cantón → Distrito → ASADA. Cada paso mueve el mapa: la provincia y el cantón se acercan solos; los
 * distritos no tienen polígono propio, así que al elegir uno el mapa se queda en su cantón.
 */
export function PlacePicker({ withAsadas, choices, asadas, districtNote, onProvince, onCanton, onAsada }: {
  withAsadas: boolean; choices: Map<string, Canton>; asadas: Operator[]
  /** Aviso bajo el distrito: cambia según dónde se use (en predicciones no hay mapa). */
  districtNote?: string
  onProvince: (province: string) => void; onCanton: (code: string) => void; onAsada: (operator: Operator) => void
}) {
  const [province, setProvince] = useState('')
  const [canton, setCanton] = useState('')
  const [district, setDistrict] = useState('')

  const provinces = useMemo(() => [...new Set([...choices.values()].map(item => item.province).filter(Boolean))].sort(collate), [choices])
  const cantons = useMemo(() => [...choices].filter(([, item]) => item.province === province).sort((a, b) => collate(a[1].name, b[1].name)), [choices, province])
  const inCanton = useMemo(() => asadas.filter(item => item.cantonCode === canton), [asadas, canton])
  const districts = useMemo(() => [...new Set(inCanton.map(item => item.district))].sort(collate), [inCanton])
  const operators = useMemo(() => inCanton.filter(item => item.district === district).sort((a, b) => collate(a.name, b.name)), [inCanton, district])
  const counts = useMemo(() => {
    const result = new Map<string, number>()
    for (const item of asadas) result.set(item.cantonCode, (result.get(item.cantonCode) ?? 0) + 1)
    return result
  }, [asadas])

  return <div className="place-picker glass" aria-label={t('Buscar por lugar', 'Search by place')}>
    <label>{t('Provincia', 'Province')}
      <select value={province} onChange={event => { setProvince(event.target.value); setCanton(''); setDistrict(''); if (event.target.value) onProvince(event.target.value) }}>
        <option value="">{t('Elegir provincia…', 'Choose province…')}</option>
        {provinces.map(item => <option key={item} value={item}>{item}</option>)}
      </select>
    </label>
    {province && <label>{t('Cantón', 'Canton')}
      <select value={canton} onChange={event => { setCanton(event.target.value); setDistrict(''); if (event.target.value) onCanton(event.target.value) }}>
        <option value="">{t('Elegir cantón…', 'Choose canton…')}</option>
        {cantons.map(([code, item]) => <option key={code} value={code}>{item.name}{withAsadas ? ` (${counts.get(code) ?? 0})` : ''}</option>)}
      </select>
    </label>}
    {withAsadas && canton && (districts.length ? <label>{t('Distrito', 'District')}
      <select value={district} onChange={event => setDistrict(event.target.value)}>
        <option value="">{t('Elegir distrito…', 'Choose district…')}</option>
        {districts.map(item => <option key={item} value={item}>{item}</option>)}
      </select>
      <small className="muted">{districtNote ?? t('El mapa no dibuja distritos: se queda en el cantón.', 'The map does not draw districts: it stays on the canton.')}</small>
    </label> : <p className="muted">{t('Este cantón no tiene operadores en el catálogo de SAGA.', 'This canton has no operators in the SAGA catalog.')}</p>)}
    {withAsadas && district && <label>{t('ASADA u operador', 'ASADA or operator')}
      <select value="" onChange={event => { const found = operators.find(item => item.id === event.target.value); if (found) onAsada(found) }}>
        <option value="">{t('Elegir operador…', 'Choose operator…')}</option>
        {operators.map(item => <option key={item.id} value={item.id}>{item.name} · {item.type}</option>)}
      </select>
    </label>}
  </div>
}
