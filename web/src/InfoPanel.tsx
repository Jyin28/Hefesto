import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { MapMode } from './copy'
import type { Canton, Operator } from './data'
import { PlacePicker } from './PlacePicker'
import { entryName, entrySub, highlight, inlineCompletion, loadRecent, recentEntries, rememberSearch, searchEntries, searchesAsadas } from './search'
import type { Entry } from './search'

const PILOTS = ['308', '501', '503', '502', '701', '703', '210', '119']

/** Encabezado del panel: número de celda (pequeño, arriba), provincias o nombre del lugar y, si aplica, los cantones de la celda. */
export type PanelHeader = { cellTag?: string; kicker?: string; title: string; cantons?: string }

const PinIcon = () => <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 21s-6.5-5.6-6.5-11A6.5 6.5 0 0 1 12 3.5 6.5 6.5 0 0 1 18.5 10c0 5.4-6.5 11-6.5 11Z" /><circle cx="12" cy="10" r="2.3" /></svg>
const DropIcon = () => <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3.5s6 6.2 6 10.4a6 6 0 0 1-12 0C6 9.7 12 3.5 12 3.5Z" /></svg>
const ClockIcon = () => <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></svg>

function Highlighted({ text, query }: { text: string; query: string }) {
  return <>{highlight(text, query).map((part, index) => part.bold ? <b key={index}>{part.text}</b> : <span key={index}>{part.text}</span>)}</>
}

/**
 * Panel derecho único, estilo Google Maps: el buscador con autocompletado vive arriba (cantones siempre, ASADAs además
 * en el mapa de cuencas) y, al elegir un resultado, el mismo panel se expande hacia abajo con el detalle de la zona.
 */
export function InfoPanel({ choices, asadas, mode, loading, blank, back, select, selectAsada, selectProvince,
  selected, cell, header, collapsed, mapTip, children }: {
  choices: Map<string, Canton>; asadas: Operator[]; mode: MapMode; loading: boolean
  /** Sin nada que mostrar: solo quedan el buscador y las zonas sugeridas. */
  blank: boolean; back: () => void
  select: (code: string) => void; selectAsada: (operator: Operator) => void; selectProvince: (province: string) => void
  selected: string; cell: string; header: PanelHeader
  collapsed: boolean; mapTip: string; children: ReactNode
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [picker, setPicker] = useState(false)
  const [active, setActive] = useState(0)
  const [recent, setRecent] = useState(loadRecent)
  const withAsadas = searchesAsadas(mode)
  const hasSelection = !!selected || !!cell
  const typing = query.trim() !== ''
  const entries = useMemo(() => searchEntries(query, choices, asadas, withAsadas), [query, choices, asadas, withAsadas])
  // Sin texto, el desplegable muestra las búsquedas recientes (sin ASADAs fuera del mapa de cuencas).
  const recents = useMemo(() => recentEntries(recent, choices, asadas, withAsadas), [recent, choices, asadas, withAsadas])
  const list = typing ? entries : recents
  const current = list[Math.min(active, list.length - 1)]
  const completion = typing ? inlineCompletion(query, current) : ''
  const showList = open && (typing || recents.length > 0)

  function choose(entry: Entry) {
    if (entry.kind === 'canton') select(entry.code); else selectAsada(entry.operator)
    rememberSearch(entry)
    setRecent(loadRecent())
    setQuery(''); setOpen(false); setActive(0)
  }
  function acceptCompletion() {
    if (completion) { setQuery(query + completion); setActive(0) }
  }
  const placeholder = withAsadas ? 'Buscar cantón o ASADA...' : 'Buscar cantón...'
  const chip = mode === 'cds' ? 'Copernicus ERA5-Land' : mode === 'grid' ? 'NASA POWER' : ''
  // En el mapa de cuencas, un cantón abierto muestra solo su lista de ASADAs: sin chips ni notas.
  const onlyAsadas = mode === 'cantones' && !!selected
  return <aside className="drawer glass" id="ficha" aria-label="Panel de información" inert={collapsed}
    onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}>
    <div className="drawer-top">
    <div className="drawer-search">
      {hasSelection && <button type="button" className="drawer-back" aria-label="Volver" onClick={back}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6" /></svg>
      </button>}
      <div className={showList ? 'search-box glass open' : 'search-box glass'}>
      <form role="search" onSubmit={event => { event.preventDefault(); if (current) choose(current) }}>
        <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="1.8" /><path d="m16 16 4.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
        <label className="screen-reader" htmlFor="search-zone">{placeholder}</label>
        <div className="search-field">
          {completion && <span className="search-ghost" aria-hidden="true"><span>{query}</span>{completion}</span>}
          <input id="search-zone" type="text" value={query} placeholder={placeholder} autoComplete="off" spellCheck={false}
            role="combobox" aria-expanded={showList} aria-controls="search-results" aria-autocomplete="both"
            aria-activedescendant={showList && current ? `search-opt-${Math.min(active, list.length - 1)}` : undefined}
            onFocus={() => setOpen(true)}
            onChange={event => { setQuery(event.target.value); setOpen(true); setActive(0) }}
            onKeyDown={event => {
              const atEnd = event.currentTarget.selectionStart === query.length && event.currentTarget.selectionEnd === query.length
              if (event.key === 'Escape') { if (open) setOpen(false); else setQuery('') }
              else if (event.key === 'ArrowDown') { event.preventDefault(); setOpen(true); setActive(index => Math.min(index + 1, list.length - 1)) }
              else if (event.key === 'ArrowUp') { event.preventDefault(); setActive(index => Math.max(index - 1, 0)) }
              else if ((event.key === 'Tab' || event.key === 'ArrowRight') && completion && atEnd) { event.preventDefault(); acceptCompletion() }
            }} />
        </div>
        {query && <button type="button" className="search-clear" aria-label="Borrar la búsqueda"
          onClick={() => { setQuery(''); setActive(0); document.getElementById('search-zone')?.focus() }}>×</button>}
      </form>
      {showList && <div className="results" id="search-results" role="listbox" aria-label={typing ? 'Resultados' : 'Búsquedas recientes'}>
      {!typing && <span className="group">Búsquedas recientes</span>}
      {list.length ? list.map((entry, index) => <button key={entry.key} id={`search-opt-${index}`} role="option" className="opt" type="button"
        aria-selected={index === active} onMouseEnter={() => setActive(index)} onMouseDown={event => event.preventDefault()} onClick={() => choose(entry)}>
        <span className={entry.kind === 'asada' ? 'opt-icon water' : 'opt-icon'}>{!typing ? <ClockIcon /> : entry.kind === 'canton' ? <PinIcon /> : <DropIcon />}</span>
        <span className="opt-text">
          <span className="opt-name">{typing ? <Highlighted text={entryName(entry)} query={query} /> : entryName(entry)}</span>
          <small>{entrySub(entry)}</small>
        </span>
      </button>) : <p>{loading ? 'Cargando…' : withAsadas ? 'Sin coincidencias. Probá con el nombre del cantón, del distrito o de la ASADA.' : 'Sin coincidencias. Buscá por cantón.'}</p>}
      </div>}
      </div>
    </div>
    <div className="suggestions" aria-label="Zonas sugeridas">
      <button className="pill pill-ghost" aria-expanded={picker} onClick={() => setPicker(value => !value)}>{picker ? 'Cerrar guía de lugar ▴' : 'Buscar por lugar ▾'}</button>
      {PILOTS.filter(code => choices.has(code)).map(code => <button key={code} className="pill pill-ghost" onClick={() => select(code)}>{choices.get(code)!.name}</button>)}
    </div>
    {picker && <PlacePicker mode={mode} choices={choices} asadas={asadas} onProvince={selectProvince} onCanton={select} onAsada={selectAsada} />}
    </div>
    {!blank && <div className="drawer-detail open">
      <div className="drawer-title">
        {header.cellTag && <small className="cell-tag">{header.cellTag}</small>}
        {header.kicker && <small>{header.kicker}</small>}
        <h2>{header.title}</h2>
        {header.cantons && <p className="cell-cantons"><strong>{header.cantons.includes(',') ? 'Cantones' : 'Cantón'}:</strong> {header.cantons}</p>}
        {chip && !onlyAsadas && <div className="chips"><span className="chip nasa">{chip}</span></div>}
      </div>
      <div className="bento">{children}</div>
      {!onlyAsadas && <p className="muted">{mapTip}</p>}
    </div>}
  </aside>
}
