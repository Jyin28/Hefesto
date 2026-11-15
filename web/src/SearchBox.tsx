import { useMemo, useState } from 'react'
import type { Canton, Operator } from './data'
import { PlacePicker } from './PlacePicker'
import { entryName, entrySub, highlight, inlineCompletion, loadRecent, recentEntries, rememberSearch, searchEntries, searchesAsadas } from './search'
import type { Entry, SearchContext } from './search'
import { t } from './i18n'

const PILOTS = ['308', '501', '503', '502', '701', '703', '210', '119']

const PinIcon = () => <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 21s-6.5-5.6-6.5-11A6.5 6.5 0 0 1 12 3.5 6.5 6.5 0 0 1 18.5 10c0 5.4-6.5 11-6.5 11Z" /><circle cx="12" cy="10" r="2.3" /></svg>
const DropIcon = () => <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3.5s6 6.2 6 10.4a6 6 0 0 1-12 0C6 9.7 12 3.5 12 3.5Z" /></svg>

function Highlighted({ text, query }: { text: string; query: string }) {
  return <>{highlight(text, query).map((part, index) => part.bold ? <b key={index}>{part.text}</b> : <span key={index}>{part.text}</span>)}</>
}

/**
 * Buscador con autocompletado, búsquedas recientes, zonas sugeridas y la guía «Buscar por lugar».
 * Lo usan el panel de los mapas y la página de predicciones. Los cantones se buscan siempre; las ASADAs solo donde
 * `searchesAsadas(context)` lo permite. En los resultados, el ícono verde es un cantón y el azul una ASADA.
 */
export function SearchBox({ context, choices, asadas, loading, onCanton, onAsada, onProvince, onSearchFocus, back, districtNote, inputId = 'search-zone' }: {
  context: SearchContext; choices: Map<string, Canton>; asadas: Operator[]; loading: boolean
  onCanton: (code: string) => void; onAsada: (operator: Operator) => void; onProvince: (province: string) => void
  /** Se llama al hacer clic (o enfocar) la barra de búsqueda; el mapa de caudales lo usa para cerrar la ASADA que dejó elegida la guía «Buscar por lugar». */
  onSearchFocus?: () => void
  /** Si se pasa, aparece la flecha «Volver» a la izquierda del buscador. */
  back?: () => void
  districtNote?: string
  inputId?: string
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [picker, setPicker] = useState(false)
  const [active, setActive] = useState(0)
  const [recent, setRecent] = useState(loadRecent)
  const withAsadas = searchesAsadas(context)
  const typing = query.trim() !== ''
  const entries = useMemo(() => searchEntries(query, choices, asadas, withAsadas), [query, choices, asadas, withAsadas])
  // Sin texto, el desplegable muestra las búsquedas recientes (sin ASADAs donde no se buscan caudales).
  const recents = useMemo(() => recentEntries(recent, choices, asadas, withAsadas), [recent, choices, asadas, withAsadas])
  const list = typing ? entries : recents
  const current = list[Math.min(active, list.length - 1)]
  const completion = typing ? inlineCompletion(query, current) : ''
  const showList = open && (typing || recents.length > 0)
  const placeholder = withAsadas ? t('Buscar cantón o ASADA...', 'Search canton or ASADA...') : t('Buscar cantón...', 'Search canton...')
  const listId = `${inputId}-results`

  function choose(entry: Entry) {
    if (entry.kind === 'canton') onCanton(entry.code); else onAsada(entry.operator)
    rememberSearch(entry)
    setRecent(loadRecent())
    setQuery(''); setOpen(false); setActive(0)
  }
  function acceptCompletion() {
    if (completion) { setQuery(query + completion); setActive(0) }
  }

  return <div className="search-block" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}>
    <div className="drawer-search">
      {back && <button type="button" className="drawer-back" aria-label={t('Volver', 'Back')} onClick={back}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 6l-6 6 6 6" /></svg>
      </button>}
      <div className={showList ? 'search-box glass open' : 'search-box glass'}>
        <form role="search" onSubmit={event => { event.preventDefault(); if (current) choose(current) }}>
          <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="1.8" /><path d="m16 16 4.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
          <label className="screen-reader" htmlFor={inputId}>{placeholder}</label>
          <div className="search-field">
            {completion && <span className="search-ghost" aria-hidden="true"><span>{query}</span>{completion}</span>}
            <input id={inputId} type="text" value={query} placeholder={placeholder} autoComplete="off" spellCheck={false}
              role="combobox" aria-expanded={showList} aria-controls={listId} aria-autocomplete="both"
              aria-activedescendant={showList && current ? `${inputId}-opt-${Math.min(active, list.length - 1)}` : undefined}
              onFocus={() => { setOpen(true); onSearchFocus?.() }}
              onClick={() => onSearchFocus?.()}
              onChange={event => { setQuery(event.target.value); setOpen(true); setActive(0) }}
              onKeyDown={event => {
                const atEnd = event.currentTarget.selectionStart === query.length && event.currentTarget.selectionEnd === query.length
                if (event.key === 'Escape') { if (open) setOpen(false); else setQuery('') }
                else if (event.key === 'ArrowDown') { event.preventDefault(); setOpen(true); setActive(index => Math.min(index + 1, list.length - 1)) }
                else if (event.key === 'ArrowUp') { event.preventDefault(); setActive(index => Math.max(index - 1, 0)) }
                else if ((event.key === 'Tab' || event.key === 'ArrowRight') && completion && atEnd) { event.preventDefault(); acceptCompletion() }
              }} />
          </div>
          {query && <button type="button" className="search-clear" aria-label={t('Borrar la búsqueda', 'Clear the search')}
            onClick={() => { setQuery(''); setActive(0); document.getElementById(inputId)?.focus() }}>×</button>}
        </form>
        {showList && <div className="results" id={listId} role="listbox" aria-label={typing ? t('Resultados', 'Results') : t('Búsquedas recientes', 'Recent searches')}>
          {!typing && <span className="group">{t('Búsquedas recientes', 'Recent searches')}</span>}
          {list.length ? list.map((entry, index) => <button key={entry.key} id={`${inputId}-opt-${index}`} role="option" className="opt" type="button"
            aria-selected={index === active} onMouseEnter={() => setActive(index)} onMouseDown={event => event.preventDefault()} onClick={() => choose(entry)}>
            <span className={entry.kind === 'asada' ? 'opt-icon water' : 'opt-icon canton'} title={entry.kind === 'asada' ? t('ASADA u operador de agua', 'ASADA or water operator') : t('Cantón', 'Canton')}>{entry.kind === 'canton' ? <PinIcon /> : <DropIcon />}</span>
            <span className="opt-text">
              <span className="opt-name">{typing ? <Highlighted text={entryName(entry)} query={query} /> : entryName(entry)}</span>
              <small>{entrySub(entry)}</small>
            </span>
          </button>) : <p>{loading ? t('Cargando…', 'Loading…') : withAsadas ? t('Sin coincidencias. Probá con el nombre del cantón, del distrito o de la ASADA.', 'No matches. Try the name of the canton, the district or the ASADA.') : t('Sin coincidencias. Buscá por cantón.', 'No matches. Search by canton.')}</p>}
        </div>}
      </div>
    </div>
    <div className="suggestions" aria-label={t('Zonas sugeridas', 'Suggested areas')}>
      <button className="pill pill-ghost" aria-expanded={picker} onClick={() => setPicker(value => !value)}>{picker ? t('Cerrar guía de lugar ▴', 'Close place guide ▴') : t('Buscar por lugar ▾', 'Search by place ▾')}</button>
      {PILOTS.filter(code => choices.has(code)).map(code => <button key={code} className="pill pill-ghost" onClick={() => onCanton(code)}>{choices.get(code)!.name}</button>)}
    </div>
    {withAsadas && <p className="legend-search" aria-label={t('Significado de los íconos', 'Meaning of the icons')}>
      <span><i className="opt-icon canton"><PinIcon /></i> {t('Cantón', 'Canton')}</span><span><i className="opt-icon water"><DropIcon /></i> {t('ASADA (caudal)', 'ASADA (flow)')}</span>
    </p>}
    {picker && <PlacePicker withAsadas={withAsadas} choices={choices} asadas={asadas} districtNote={districtNote} onProvince={onProvince} onCanton={onCanton} onAsada={onAsada} />}
  </div>
}
