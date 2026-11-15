import { useState } from 'react'
import { copy } from './copy'
import type { Level } from './copy'
import type { Canton, Local } from './data'
import { RangeSlider } from './RangeSlider'

const PILOTS = ['308', '501', '503', '502', '701', '703', '210', '119']

function normalize(text: string) {
  return text.toLocaleLowerCase('es-CR').normalize('NFD').replace(/\p{Diacritic}/gu, '')
}

export function FloatingSearch({ choices, operators, loading, select }: {
  choices: Map<string, Canton>; operators: Local['operators']; loading: boolean; select: (code: string) => void
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const search = normalize(query.trim())
  const results = [...choices].filter(([code, info]) => {
    const names = operators.filter(operator => operator.cantonCodes.includes(code)).map(item => item.name).join(' ')
    return normalize(`${code} ${info.name} ${info.province} ${names}`).includes(search)
  }).sort((a, b) => a[1].name.localeCompare(b[1].name, 'es-CR')).slice(0, 8)
  function choose(code: string) { select(code); setQuery(''); setOpen(false); setActive(0) }
  return <div className="floating-search" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}>
    <form className="glass" role="search" onSubmit={event => { event.preventDefault(); const pick = results[active] ?? results[0]; if (pick) choose(pick[0]) }}>
      <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="1.8" /><path d="m16 16 4.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
      <label className="screen-reader" htmlFor="search-zone">Buscar cantón o cuenca</label>
      <input id="search-zone" type="search" value={query} placeholder="Buscar cantón o cuenca..." autoComplete="off"
        role="combobox" aria-expanded={open} aria-controls="search-results"
        onFocus={() => setOpen(true)}
        onChange={event => { setQuery(event.target.value); setOpen(true); setActive(0) }}
        onKeyDown={event => {
          if (event.key === 'Escape') setOpen(false)
          else if (event.key === 'ArrowDown') { event.preventDefault(); setOpen(true); setActive(index => Math.min(index + 1, results.length - 1)) }
          else if (event.key === 'ArrowUp') { event.preventDefault(); setActive(index => Math.max(index - 1, 0)) }
        }} />
    </form>
    {open && query.trim() !== '' && <div className="results glass" id="search-results" role="listbox" aria-label="Resultados">
      {results.length ? results.map(([code, info], index) => <button key={code} role="option" aria-selected={index === active}
        onMouseEnter={() => setActive(index)} onClick={() => choose(code)}>{info.name}<small>{info.province}</small></button>)
        : <p>{loading ? 'Cargando cantones…' : 'Sin coincidencias. Todavía no hay una capa de cuencas cargada: buscá por cantón.'}</p>}
    </div>}
    <div className="suggestions" aria-label="Zonas sugeridas">
      {PILOTS.filter(code => choices.has(code)).map(code => <button key={code} className="pill pill-ghost" onClick={() => choose(code)}>{choices.get(code)!.name}</button>)}
    </div>
  </div>
}

export function ZoneCard({ level, name, province, nasa, range, setRange, selection, exitZone, admin, openForm }: {
  level: Level; name: string; province?: string; nasa: boolean
  range: [number, number]; setRange: (range: [number, number]) => void
  /** Hay un cantón o una celda elegidos: se ofrece volver a la vista de todo el país. */
  selection: boolean; exitZone: () => void
  /** Solo con sesión de administrador: abre el formulario de datos de las comisiones. */
  admin: boolean; openForm: () => void
}) {
  const [collapsed, setCollapsed] = useState(() => window.matchMedia('(max-width: 860px)').matches)
  return <section className="zone-card glass" aria-label="Zona seleccionada">
    <header>
      <div><h3>{name}</h3>{province && <span className="muted">{province}</span>}</div>
      <button className="toggle" aria-expanded={!collapsed} aria-label={collapsed ? 'Expandir tarjeta' : 'Contraer tarjeta'}
        onClick={() => setCollapsed(value => !value)}>{collapsed ? '▴' : '▾'}</button>
    </header>
    <div className="chips">
      {nasa ? <span className="chip nasa">NASA POWER</span> : <span className="chip imn">IMN - Comisiones Nacionales · pendiente</span>}
    </div>
    {!collapsed && <>
      <RangeSlider value={range} onChange={setRange} title={copy[level].tipRange} />
      {!nasa && <p className="muted">Información pendiente de ser facilitada para esta zona.</p>}
    </>}
    {selection && <button className="pill pill-ghost" onClick={exitZone}>← Salir del cantón</button>}
    {admin && <button className="pill pill-primary" onClick={openForm}>Enviar formulario de datos</button>}
  </section>
}
