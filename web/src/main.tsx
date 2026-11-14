import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Chart } from './Chart'
import { ClimateDetails, WaterDetails } from './ClimateDetails'
import { Map } from './Map'
import { getBoundaries, getJson, getSnapshot, regions } from './data'
import type { Boundaries, Canton, Climate, Local, Region, Snapshot, Variable } from './data'
import './style.css'

const params = new URLSearchParams(window.location.search)
const emptyLocal: Local = { cantons: {}, notices: [], operators: [] }
const format = new Intl.NumberFormat('es-CR', { maximumFractionDigits: 2 })
const dateFormat = new Intl.DateTimeFormat('es-CR', { dateStyle: 'medium', timeZone: 'America/Costa_Rica' })
const defaultYears = [1981, 2002, 2003, 2024]

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>()
  const [boundaries, setBoundaries] = useState<Boundaries>()
  const [local, setLocal] = useState<Local>()
  const [remote, setRemote] = useState<{ key: string; data: Climate }>()
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(params.get('canton') || '503')
  const [tab, setTab] = useState<'agua' | 'clima'>(params.get('vista') === 'clima' ? 'clima' : 'agua')
  const [variable, setVariable] = useState<Variable>('PRECTOTCORR')
  const [regionOverride, setRegionOverride] = useState<Region>()
  const [cell, setCell] = useState('')
  const [years, setYears] = useState(defaultYears)
  const [appliedYears, setAppliedYears] = useState(defaultYears)
  const [requestError, setRequestError] = useState('')
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    const climateRequest = getSnapshot(signal).then(data => { if (!signal.aborted) setSnapshot(data) })
    const localRequest = getJson<Local>('/api/local', signal).then(data => { if (!signal.aborted) setLocal(data) })
    getBoundaries(signal).then(data => { if (!signal.aborted) setBoundaries(data) }).catch(() => {})
    void Promise.allSettled([climateRequest, localRequest]).then(() => { if (!signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [])

  const catalog = local ?? snapshot?.local ?? emptyLocal
  const choices = new globalThis.Map<string, Canton>()
  for (const feature of boundaries?.features ?? []) {
    const { code, name, province = '' } = feature.properties
    choices.set(code, { name, province })
  }
  for (const [code, canton] of Object.entries(catalog.cantons)) choices.set(code, canton)
  const canton = choices.get(selected)
  const region = regionOverride ?? canton?.regionId
  const chosenRegion = regions.find(item => item.id === region)
  const queryParams = new URLSearchParams({ canton: selected })
  if (cell) queryParams.set('celda', cell)
  const usesDefaults = defaultYears.every((year, index) => appliedYears[index] === year)
  if (!usesDefaults) {
    ['a_inicio', 'a_fin', 'b_inicio', 'b_fin'].forEach((label, index) => queryParams.set(label, String(appliedYears[index])))
  }
  const key = `${region}/${variable}?${queryParams}`
  const matchingRemote = remote?.key === key ? remote.data : undefined
  const climate = matchingRemote ?? (region && usesDefaults
    ? cell ? snapshot?.cells?.[region]?.[cell]?.[variable] : snapshot?.climate[region][variable]
    : undefined)

  useEffect(() => {
    if (!region || tab !== 'clima') return
    const controller = new AbortController()
    const { signal } = controller
    setRequestError('')
    getJson<Climate>(`/api/clima/${key}`, signal).then(data => {
      if (!signal.aborted) setRemote({ key, data })
    }).catch(() => {
      if (!signal.aborted) setRequestError('La API no pudo cargar esta selección.')
    })
    return () => controller.abort()
  }, [region, key, tab])

  function select(code: string) {
    setSelected(code)
    setRegionOverride(undefined)
    setCell('')
    setQuery('')
    setSearching(false)
    const url = new URL(window.location.href)
    url.searchParams.set('canton', code)
    url.searchParams.delete('aviso')
    history.replaceState(null, '', url)
  }

  function showTab(value: 'agua' | 'clima') {
    setTab(value)
    const url = new URL(window.location.href)
    url.searchParams.set('vista', value)
    history.replaceState(null, '', url)
  }

  function normalize(text: string) {
    return text.toLocaleLowerCase('es-CR').normalize('NFD').replace(/\p{Diacritic}/gu, '')
  }

  function printCard() {
    const collapsed = Array.from(document.querySelectorAll<HTMLDetailsElement>('#ficha details:not([open])'))
    collapsed.forEach(item => { item.open = true })
    try { window.print() } finally { collapsed.forEach(item => { item.open = false }) }
  }

  const search = normalize(query.trim())
  const results = [...choices].filter(([code, info]) => {
    const operators = catalog.operators.filter(operator => operator.cantonCodes.includes(code))
    return normalize(`${code} ${info.name} ${info.province} ${operators.map(item => item.name).join(' ')}`).includes(search)
  }).sort((a, b) => a[1].name.localeCompare(b[1].name, 'es-CR')).slice(0, 8)
  const notices = catalog.notices.filter(item => item.cantonCodes.includes(selected))
  const operators = catalog.operators.filter(item => item.cantonCodes.includes(selected))
  const unit = variable === 'T2M' ? '°C' : 'mm/año'

  return <>
    <header className="header"><div className="shell header-inner">
      <a className="brand" href={import.meta.env.BASE_URL}><span className="mark" aria-hidden="true"><svg width="19" height="23" viewBox="0 0 20 24" fill="none"><path d="M10 1.5C7 6.5 2.5 10.5 2.5 15a7.5 7.5 0 0 0 15 0C17.5 10.5 13 6.5 10 1.5Z" stroke="currentColor" strokeWidth="1.7"/><path d="M6 15a4 4 0 0 0 4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg></span>Detective Tico</a>
      <nav aria-label="Navegación principal"><a href="#explorar">Mapa</a><a href="#ficha" onClick={() => showTab('agua')}>Avisos</a></nav>
    </div></header>
    <main className="shell">
      <section className="intro">
        <h1>Clima y agua<br className="small-break" /> en tu cantón<span>.</span></h1>
        <p>Consultá avisos de tu comunidad y explorá cómo han cambiado la lluvia y la temperatura.</p>
      </section>
      <div className="search" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setSearching(false) }}>
        <form onSubmit={event => { event.preventDefault(); if (results[0]) select(results[0][0]) }}>
          <label className="screen-reader" htmlFor="search-canton">Buscá tu cantón o ASADA</label>
          <svg aria-hidden="true" width="21" height="21" viewBox="0 0 24 24" fill="none"><circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="1.8"/><path d="m16 16 4.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
          <input id="search-canton" type="search" value={query} placeholder="Buscá tu cantón o ASADA"
            onFocus={() => setSearching(true)} onChange={event => { setQuery(event.target.value); setSearching(true) }}
            onKeyDown={event => { if (event.key === 'Escape') setSearching(false) }} autoComplete="off" />
        </form>
        {searching && <div className="results" aria-label="Resultados">
          {results.length ? results.map(([code, info]) => <button key={code} onClick={() => select(code)}>{info.name}<small>{info.province}</small></button>)
            : <p>{loading ? 'Cargando cantones…' : 'Sin coincidencias en el catálogo disponible.'}</p>}
        </div>}
      </div>
      <div className="workspace">
        <section className="map-card" id="explorar" aria-label="Mapa">
          <Map boundaries={boundaries} snapshot={snapshot} selected={selected} select={select}
            explore={value => { setRegionOverride(value); setCell(''); showTab('clima') }} />
        </section>
        <section className="panel" id="ficha" aria-label="Ficha cantonal">
          <div className="panel-heading"><span>{canton?.province || 'Costa Rica'}</span><h2>{canton?.name ?? 'Ficha cantonal'}</h2></div>
          <div className="tabs" aria-label="Vista de la ficha">
            <button aria-pressed={tab === 'agua'} onClick={() => showTab('agua')}>Avisos y servicio de agua</button>
            <button aria-pressed={tab === 'clima'} onClick={() => showTab('clima')}>Datos y tendencias</button>
          </div>
          <div className="panel-content" aria-live="polite">
            {tab === 'agua' ? <>
              <h3>Avisos publicados</h3>
              {notices.length ? notices.map(notice => {
                const url = new URL(window.location.href)
                url.search = new URLSearchParams({ canton: selected, vista: 'agua', aviso: notice.id }).toString()
                return <article className={params.get('aviso') === notice.id && params.get('canton') === selected ? 'notice highlighted' : 'notice'} key={notice.id}>
                  <p className="source">{notice.source} · {dateFormat.format(new Date(notice.publishedAt))}</p>
                  <h4>{notice.title}</h4><p>{notice.summary}</p>
                  {notice.communities.length > 0 && <p>Comunidades · {notice.communities.join(', ')}</p>}
                  {notice.expiresAt && <p>{new Date(notice.expiresAt) < new Date() ? 'Venció el' : 'Vigencia publicada hasta el'} {dateFormat.format(new Date(notice.expiresAt))}</p>}
                  <div className="notice-links"><a href={notice.sourceUrl}>Ver comunicado</a><a href={`https://wa.me/?text=${encodeURIComponent(url.href)}`}>Compartir por WhatsApp</a></div>
                </article>
              }) : <p className="empty">{loading ? 'Cargando avisos…' : 'Todavía no hay comunicados verificados en la página para este cantón.'}</p>}
              <h3>ASADAS y operadores</h3>
              {operators.length ? operators.map(operator => <p key={operator.name}><strong>{operator.name}</strong><br />{operator.communities.join(', ')}{operator.phone && <> · <a href={`tel:${operator.phone}`}>{operator.phone}</a></>}{operator.sourceId && catalog.sources?.[operator.sourceId] && <> · <a href={catalog.sources[operator.sourceId].url}>Fuente</a></>}</p>)
                : <p className="muted">Directorio local pendiente de verificación.</p>}
              <WaterDetails local={catalog} canton={selected} />
              <button className="text-action" onClick={() => showTab('clima')}>Explorar lluvia y temperatura <span aria-hidden="true">→</span></button>
            </> : <>
              <div className="climate-controls">
                <div className="variables" aria-label="Variable climática">
                  <button aria-pressed={variable === 'PRECTOTCORR'} onClick={() => setVariable('PRECTOTCORR')}>Lluvia</button>
                  <button aria-pressed={variable === 'T2M'} onClick={() => setVariable('T2M')}>Temperatura</button>
                </div>
                <label>Zona climática <select value={region ?? ''} onChange={event => {
                  setRegionOverride((event.target.value || undefined) as Region | undefined); setCell('')
                }}>
                  <option value="" disabled>Elegir zona</option>
                  {regions.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select></label>
              </div>
              {region && <details>
                <summary>Ajustar ventanas A y B</summary>
                <form className="period-controls" onSubmit={event => {
                  event.preventDefault()
                  if (years[0] > years[1] || years[2] > years[3]) {
                    setRequestError('El año inicial debe ser anterior o igual al final.')
                  } else {
                    setRequestError('')
                    setAppliedYears([...years])
                  }
                }}>
                  {['Inicio A', 'Fin A', 'Inicio B', 'Fin B'].map((label, index) => <label key={label}>{label}
                    <input type="number" min={1981} max={2024} required value={years[index] || ''}
                      onChange={event => setYears(years.map((year, position) => position === index ? Number(event.target.value) : year))} />
                  </label>)}
                  <button type="submit">Aplicar</button>
                </form>
              </details>}
              {cell && <button type="button" onClick={() => setCell('')}>Volver al promedio del sector</button>}
              {requestError && (!climate || requestError.startsWith('El año')) && <p role="status">{requestError}</p>}
              {climate ? <>
                <h3>{variable === 'T2M' ? 'Temperatura media anual' : 'Precipitación acumulada anual'}</h3>
                <p className="muted">{chosenRegion?.name} · {cell || 'Promedio del sector'}</p>
                <Chart data={climate} unit={unit} />
                {climate.comparison && <div className="periods">
                  {[climate.comparison.window_a, climate.comparison.window_b].map((window, index) => <div key={index}><small>{window.start_year}–{window.end_year} · {window.n_years} años</small><strong>{window.mean === null ? 'Sin datos' : `${format.format(window.mean)} ${unit}`}</strong></div>)}
                </div>}
                <p className="trend">{climate.trend.slope_per_decade === null ? 'Tendencia sin datos suficientes.' : <>Cambio estimado por década · <strong>{format.format(climate.trend.slope_per_decade)} {unit}</strong> <span>({climate.trend.n_years} años válidos)</span></>}</p>
                <p className="muted">{climate.trend.significant === null ? 'Sin prueba de significancia disponible.' : climate.trend.significant ? 'Tendencia con evidencia estadística al 5 % (ajuste BY).' : 'Evidencia estadística insuficiente al 5 % (ajuste BY).'}</p>
                <p className="source"><a href={climate.sourceUrl}>{climate.source}</a></p>
                <ClimateDetails data={climate} unit={unit} selected={cell} choose={setCell} />
                {variable === 'PRECTOTCORR' && <WaterDetails local={catalog} canton={selected} />}
                <div className="exports" aria-label="Descargas">
                  <button type="button" onClick={printCard}>Imprimir ficha</button>
                  {matchingRemote && <>
                    <a download="ficha-detective-tico.json" href={`/api/ficha/${key}`}>JSON</a>
                    {['series', 'results', 'sources', 'enso',
                      ...(matchingRemote.water_coverage.length ? ['water'] : []),
                      ...(matchingRemote.distribution.length ? ['distribution'] : []),
                    ].map(table => <a key={table} href={`/api/ficha/${key}&tabla=${table}`}>CSV {({
                      series: 'serie', results: 'resultados', water: 'cobertura de agua', distribution: 'distribución',
                      sources: 'fuentes', enso: 'El Niño',
                    } as Record<string, string>)[table]}</a>)}
                  </>}
                </div>
              </> : <p className="empty">{region ? (loading ? 'Cargando la serie climática…' : 'Serie regional no disponible.') : 'Este cantón todavía no tiene una zona climática asociada. Podés explorar una de las zonas del menú.'}</p>}
            </>}
          </div>
        </section>
      </div>
      <footer>Detective Tico <span>·</span> NASA Space Apps Challenge</footer>
    </main>
  </>
}

createRoot(document.getElementById('root')!).render(<App />)
