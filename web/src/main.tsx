import { useCallback, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Header } from './Header'
import { Map } from './Map'
import { FloatingSearch, ZoneCard } from './MapOverlay'
import { AdminModal, RequestModal } from './Modals'
import type { InfoRequest } from './Modals'
import { ClimatePanel, GeneralPanel, NoticesPanel } from './Panels'
import { MAX_YEAR, MIN_YEAR } from './RangeSlider'
import { Sidebar } from './Sidebar'
import { copy } from './copy'
import type { Alert, Level, MapMode, Section } from './copy'
import { getBoundaries, getJson, getSnapshot, regions } from './data'
import type { Boundaries, Canton, Climate, Local, Region, Snapshot, Variable } from './data'
import './style.css'

const params = new URLSearchParams(window.location.search)
const emptyLocal: Local = { cantons: {}, notices: [], operators: [] }
const defaultYears = [1981, 2002, 2003, 2024]
const STORAGE_KEY = 'hefesto.solicitudes'
const sections: Section[] = ['general', 'temp', 'precip', 'avisos']

function initialSection(): Section {
  const view = params.get('vista')
  if (view === 'clima') return 'precip'
  if (view === 'agua') return 'avisos'
  return sections.find(item => item === view) ?? 'general'
}

function loadRequests(): InfoRequest[] {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(stored) ? stored : []
  } catch { return [] }
}

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>()
  const [boundaries, setBoundaries] = useState<Boundaries>()
  const [local, setLocal] = useState<Local>()
  const [remote, setRemote] = useState<{ key: string; data: Climate }>()
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(params.get('canton') || '503')
  const [section, setSectionState] = useState<Section>(initialSection)
  const [level, setLevel] = useState<Level>('basico')
  const [mapMode, setMapMode] = useState<MapMode>('grid')
  const [regionOverride, setRegionOverride] = useState<Region>()
  const [cell, setCell] = useState('')
  const [years, setYears] = useState(defaultYears)
  const [appliedYears, setAppliedYears] = useState(defaultYears)
  const [range, setRange] = useState<[number, number]>([MIN_YEAR, MAX_YEAR])
  const [appliedRange, setAppliedRange] = useState<[number, number]>([MIN_YEAR, MAX_YEAR])
  const [requestError, setRequestError] = useState('')
  const [focus, setFocus] = useState({ code: '', tick: 0 })
  const [modal, setModal] = useState<'admin' | 'request' | null>(null)
  const [requests, setRequests] = useState<InfoRequest[]>(loadRequests)
  const [toast, setToast] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    const climateRequest = getSnapshot(signal).then(data => { if (!signal.aborted) setSnapshot(data) })
    const localRequest = getJson<Local>('/api/local', signal).then(data => { if (!signal.aborted) setLocal(data) })
    getBoundaries(signal).then(data => { if (!signal.aborted) setBoundaries(data) }).catch(() => {})
    void Promise.allSettled([climateRequest, localRequest]).then(() => { if (!signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => setAppliedRange(range), 350)
    return () => clearTimeout(timer)
  }, [range])

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(''), 5000)
    return () => clearTimeout(timer)
  }, [toast])

  const catalog = local ?? snapshot?.local ?? emptyLocal
  const choices = useMemo(() => {
    const items = new globalThis.Map<string, Canton>()
    for (const feature of boundaries?.features ?? []) {
      const { code, name, province = '' } = feature.properties
      items.set(code, { name, province })
    }
    for (const [code, canton] of Object.entries(catalog.cantons)) items.set(code, canton)
    return items
  }, [boundaries, catalog])
  const alerts = useMemo(() => {
    const states: Record<string, Alert> = {}
    const now = new Date()
    for (const notice of catalog.notices) {
      const expired = notice.expiresAt ? new Date(notice.expiresAt) < now : false
      for (const code of notice.cantonCodes) if (!expired) states[code] = 'active'; else if (states[code] !== 'active') states[code] = 'expired'
    }
    return states
  }, [catalog])

  const canton = choices.get(selected)
  const region = regionOverride ?? canton?.regionId
  const variable: Variable = section === 'temp' ? 'T2M' : 'PRECTOTCORR'
  const queryParams = new URLSearchParams({ canton: selected })
  if (cell) queryParams.set('celda', cell)
  const usesDefaults = defaultYears.every((year, index) => appliedYears[index] === year)
  if (!usesDefaults) ['a_inicio', 'a_fin', 'b_inicio', 'b_fin'].forEach((label, index) => queryParams.set(label, String(appliedYears[index])))
  const rangeCustom = appliedRange[0] !== MIN_YEAR || appliedRange[1] !== MAX_YEAR
  if (rangeCustom) { queryParams.set('desde', String(appliedRange[0])); queryParams.set('hasta', String(appliedRange[1])) }
  const queryKey = `${region}/${variable}?${queryParams}`
  const matchingRemote = remote?.key === queryKey ? remote.data : undefined
  const snapshotClimate = region && usesDefaults
    ? cell ? snapshot?.cells?.[region]?.[cell]?.[variable] : snapshot?.climate[region][variable]
    : undefined
  const rangeApprox = !matchingRemote && rangeCustom && !!snapshotClimate
  const climate = matchingRemote ?? (snapshotClimate && rangeApprox
    ? { ...snapshotClimate, series: snapshotClimate.series.filter(point => point.year >= appliedRange[0] && point.year <= appliedRange[1]) }
    : snapshotClimate)

  useEffect(() => {
    if (!region || (section !== 'temp' && section !== 'precip')) return
    const controller = new AbortController()
    const { signal } = controller
    setRequestError('')
    getJson<Climate>(`/api/clima/${queryKey}`, signal).then(data => {
      if (!signal.aborted) setRemote({ key: queryKey, data })
    }).catch(() => {
      if (!signal.aborted) setRequestError('La API no pudo cargar esta selección.')
    })
    return () => controller.abort()
  }, [region, queryKey, section])

  function updateUrl(change: (url: URL) => void) {
    const url = new URL(window.location.href)
    change(url)
    history.replaceState(null, '', url)
  }

  const setSection = useCallback((value: Section) => {
    setSectionState(value)
    updateUrl(url => url.searchParams.set('vista', value))
  }, [])

  function select(code: string) {
    setSelected(code)
    setRegionOverride(undefined)
    setCell('')
    setFocus(previous => ({ code, tick: previous.tick + 1 }))
    updateUrl(url => { url.searchParams.set('canton', code); url.searchParams.delete('aviso') })
  }

  function selectCell(cellRegion: Region, id: string) {
    setRegionOverride(cellRegion)
    setCell(id)
    if (section === 'avisos') setSection('general')
  }

  function submitRequest(data: Omit<InfoRequest, 'id' | 'createdAt'>) {
    const request: InfoRequest = { ...data, id: `SOL-${Date.now().toString(36).toUpperCase()}`, createdAt: new Date().toISOString() }
    const next = [...requests, request]
    setRequests(next)
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)) } catch { /* sin almacenamiento local */ }
    setModal(null)
    setToast(`Solicitud ${request.id} guardada para «${request.zone}». Una comisión la revisará.`)
  }

  const notices = catalog.notices.filter(item => item.cantonCodes.includes(selected))
  const operators = catalog.operators.filter(item => item.cantonCodes.includes(selected))
  const alert = alerts[selected] ?? 'none'
  const zoneName = cell ? `Celda ${cell}` : canton?.name ?? 'Costa Rica'
  const regionName = regions.find(item => item.id === region)?.name

  return <div className="app">
    <Header level={level} setLevel={setLevel} mapMode={mapMode} setMapMode={setMapMode} openAdmin={() => setModal('admin')} />
    <div className="body">
      <Sidebar level={level} section={section} setSection={setSection} />
      <div className="stage">
        <section className="map-wrap" aria-label="Mapa">
          <Map boundaries={boundaries} snapshot={snapshot} mode={mapMode} variable={variable} level={level} selected={selected}
            selectedCell={cell} alerts={alerts} focus={focus} select={select} selectCell={selectCell} />
          <FloatingSearch choices={choices} operators={catalog.operators} loading={loading} select={select} />
          <ZoneCard level={level} name={zoneName} province={canton?.province} nasa={!!region} range={range} setRange={setRange}
            requestCount={requests.length} openRequest={() => setModal('request')} />
        </section>
        <aside className="drawer glass" id="ficha" aria-label="Panel de información" aria-live="polite">
          <div className="drawer-title"><small>{cell ? regionName : canton?.province || 'Costa Rica'}</small><h2>{zoneName}</h2></div>
          {section === 'general' && <GeneralPanel level={level} snapshot={snapshot} region={region} canton={canton} cell={cell}
            alert={alert} notices={notices} loading={loading} />}
          {(section === 'temp' || section === 'precip') && <ClimatePanel variable={variable} level={level} climate={climate}
            remote={matchingRemote} queryKey={queryKey} region={region} cell={cell} setCell={setCell}
            setRegion={setRegionOverride} years={years} setYears={setYears} setAppliedYears={setAppliedYears}
            requestError={requestError} setRequestError={setRequestError} loading={loading} catalog={catalog}
            selected={selected} rangeApprox={rangeApprox} />}
          {section === 'avisos' && <NoticesPanel level={level} loading={loading} notices={notices} operators={operators}
            catalog={catalog} selected={selected} alert={alert} highlight={params.get('aviso')} highlightCanton={params.get('canton')} />}
          <p className="muted">{copy[level].mapTip[mapMode]}</p>
        </aside>
      </div>
    </div>
    {modal === 'admin' && <AdminModal onClose={() => setModal(null)} />}
    {modal === 'request' && <RequestModal zone={zoneName} onClose={() => setModal(null)} onSubmit={submitRequest} />}
    {toast && <div className="toast glass" role="status">{toast}</div>}
  </div>
}

createRoot(document.getElementById('root')!).render(<App />)
