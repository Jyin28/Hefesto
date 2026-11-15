import { useState } from 'react'
import type { ReactNode } from 'react'
import { matchesAll, operatorHaystack } from './asadas'
import type { MapMode } from './copy'
import type { Canton, Operator } from './data'
import { PlacePicker } from './PlacePicker'

const PILOTS = ['308', '501', '503', '502', '701', '703', '210', '119']

type Entry = { key: string; kind: 'canton'; code: string; name: string; province: string } | { key: string; kind: 'asada'; operator: Operator }

/**
 * Panel derecho único, estilo Google Maps: el buscador vive arriba (cantones siempre, ASADAs además en el
 * mapa de cuencas) y, al elegir un resultado, el mismo panel se expande hacia abajo con el detalle de la zona.
 */
export function InfoPanel({ choices, asadas, mode, loading, select, selectAsada, selectProvince,
  selected, cell, canton, zoneName, regionName, collapsed, mapTip, children }: {
  choices: Map<string, Canton>; asadas: Operator[]; mode: MapMode; loading: boolean
  select: (code: string) => void; selectAsada: (operator: Operator) => void; selectProvince: (province: string) => void
  selected: string; cell: string; canton?: Canton; zoneName: string; regionName?: string
  collapsed: boolean; mapTip: string; children: ReactNode
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [picker, setPicker] = useState(false)
  const [active, setActive] = useState(0)
  const withAsadas = mode === 'cantones'
  const hasSelection = !!selected || !!cell
  const entries: Entry[] = query.trim() === '' ? [] : [
    ...[...choices].filter(([code, info]) => matchesAll(`${code} ${info.name} ${info.province}`, query))
      .sort((a, b) => a[1].name.localeCompare(b[1].name, 'es-CR')).slice(0, withAsadas ? 4 : 8)
      .map(([code, info]): Entry => ({ key: `c${code}`, kind: 'canton', code, name: info.name, province: info.province })),
    ...(withAsadas ? asadas.filter(item => matchesAll(operatorHaystack(item), query))
      .map(item => ({ item, byName: matchesAll(item.name, query) ? 0 : 1 }))
      .sort((a, b) => a.byName - b.byName || a.item.name.localeCompare(b.item.name, 'es-CR')).slice(0, 8)
      .map(({ item }): Entry => ({ key: `a${item.id}`, kind: 'asada', operator: item })) : []),
  ]
  function choose(entry: Entry) {
    if (entry.kind === 'canton') select(entry.code); else selectAsada(entry.operator)
    setQuery(''); setOpen(false); setActive(0)
  }
  const placeholder = withAsadas ? 'Buscar cantón o ASADA...' : 'Buscar cantón...'
  const nasa = !!regionName
  return <aside className="drawer glass" id="ficha" aria-label="Panel de información" inert={collapsed}
    onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}>
    <div className="drawer-search">
      {hasSelection && <button type="button" className="drawer-back" aria-label="Volver a Costa Rica" onClick={() => select('')}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6" /></svg>
      </button>}
      <form className="glass" role="search" onSubmit={event => { event.preventDefault(); const pick = entries[active] ?? entries[0]; if (pick) choose(pick) }}>
        <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="1.8" /><path d="m16 16 4.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
        <label className="screen-reader" htmlFor="search-zone">{placeholder}</label>
        <input id="search-zone" type="search" value={query} placeholder={placeholder} autoComplete="off"
          role="combobox" aria-expanded={open} aria-controls="search-results"
          onFocus={() => setOpen(true)}
          onChange={event => { setQuery(event.target.value); setOpen(true); setActive(0) }}
          onKeyDown={event => {
            if (event.key === 'Escape') setOpen(false)
            else if (event.key === 'ArrowDown') { event.preventDefault(); setOpen(true); setActive(index => Math.min(index + 1, entries.length - 1)) }
            else if (event.key === 'ArrowUp') { event.preventDefault(); setActive(index => Math.max(index - 1, 0)) }
          }} />
      </form>
    </div>
    {open && query.trim() !== '' && <div className="results glass" id="search-results" role="listbox" aria-label="Resultados">
      {entries.length ? entries.map((entry, index) => <button key={entry.key} role="option" aria-selected={index === active}
        onMouseEnter={() => setActive(index)} onClick={() => choose(entry)}>
        {entry.kind === 'canton'
          ? <>{entry.name}<small>Cantón · {entry.province}</small></>
          : <>{entry.operator.name}<small>{entry.operator.type} · {entry.operator.district}, {entry.operator.canton}</small></>}
      </button>) : <p>{loading ? 'Cargando…' : withAsadas ? 'Sin coincidencias. Probá con el nombre del cantón, del distrito o de la ASADA.' : 'Sin coincidencias. Buscá por cantón.'}</p>}
    </div>}
    <div className="suggestions" aria-label="Zonas sugeridas">
      <button className="pill pill-ghost" aria-expanded={picker} onClick={() => setPicker(value => !value)}>{picker ? 'Cerrar guía de lugar ▴' : 'Buscar por lugar ▾'}</button>
      {PILOTS.filter(code => choices.has(code)).map(code => <button key={code} className="pill pill-ghost" onClick={() => select(code)}>{choices.get(code)!.name}</button>)}
    </div>
    {picker && <PlacePicker mode={mode} choices={choices} asadas={asadas} onProvince={selectProvince} onCanton={select} onAsada={selectAsada} />}
    <div className="drawer-detail open">
      <div className="drawer-title">
        <small>{canton ? canton.province : cell ? regionName : 'Costa Rica'}</small>
        <h2>{zoneName}</h2>
        <div className="chips">{mode === 'cds' ? <span className="chip nasa">Copernicus ERA5-Land</span>
          : nasa ? <span className="chip nasa">NASA POWER</span> : <span className="chip imn">IMN - Comisiones Nacionales · pendiente</span>}</div>
      </div>
      <div className="bento">{children}</div>
    </div>
    <p className="muted">{mapTip}</p>
  </aside>
}
