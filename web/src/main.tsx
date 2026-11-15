import { useCallback, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { AdminPanel } from './AdminPanel'
import { confidence as confidenceOf, continuity as continuityOf, defaultThresholds, ensoMean, localStat, project, spatialCoverage,
  stationsLinked, statsFor, synthesis } from './analysis'
import type { Thresholds } from './analysis'
import { logout as endSession, restoreSession } from './auth'
import type { Session } from './auth'
import { ChartTile, QualityTile, StatTiles, SynthesisTile, Tile } from './Bento'
import type { Affectation } from './data/cantonData'
import { ForecastTile } from './Forecast'
import type { ForecastRow } from './Forecast'
import { Header } from './Header'
import { normalizeText } from './localData'
import { buildGrid, Map } from './Map'
import type { CantonAffectation } from './Map'
import { FloatingSearch, ZoneCard } from './MapOverlay'
import { AdminModal } from './Modals'
import { ClimatePanel, GeneralPanel, LocalRecordsTile, NoticesPanel, worstOf } from './Panels'
import type { AffectationOverview } from './Panels'
import { affectationLabel, useCantonData } from './store'
import { MAX_YEAR, MIN_YEAR } from './RangeSlider'
import { Sidebar } from './Sidebar'
import { copy } from './copy'
import type { Alert, Level, MapMode, Section } from './copy'
import { getBoundaries, getGeo, getJson, getSnapshot, regions } from './data'
import type { Boundaries, Canton, Climate, Geo, Local, Region, Snapshot, Variable } from './data'
import './style.css'

const params = new URLSearchParams(window.location.search)
const emptyLocal: Local = { cantons: {}, notices: [], operators: [] }
const defaultYears = [1981, 2002, 2003, 2024]
// Nivel de lectura fijo: público general (el selector de escolaridad se retiró).
const level: Level = 'basico'
const sections: Section[] = ['general', 'temp', 'precip', 'avisos', 'admin']

function initialSection(): Section {
  const view = params.get('vista')
  if (view === 'clima') return 'precip'
  if (view === 'agua') return 'avisos'
  return sections.find(item => item === view) ?? 'general'
}

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>()
  const [boundaries, setBoundaries] = useState<Boundaries>()
  const [geo, setGeo] = useState<Geo>()
  const [local, setLocal] = useState<Local>()
  const [remote, setRemote] = useState<{ key: string; data: Climate }>()
  const [loading, setLoading] = useState(true)
  // Sin cantón elegido se ve el país completo; la región por defecto es la malla nacional.
  const [selected, setSelected] = useState(params.get('canton') || '')
  const [session, setSession] = useState<Session | null>(restoreSession)
  const [requestedSection, setSectionState] = useState<Section>(initialSection)
  // Sin sesión de administrador, la sección Admin nunca se muestra, aunque llegue por la URL.
  const section: Section = requestedSection === 'admin' && !session ? 'general' : requestedSection
  const data = useCantonData()
  const [mapMode, setMapMode] = useState<MapMode>('grid')
  const [regionOverride, setRegionOverride] = useState<Region>()
  const [cell, setCell] = useState('')
  const [years, setYears] = useState(defaultYears)
  const [appliedYears, setAppliedYears] = useState(defaultYears)
  const [range, setRange] = useState<[number, number]>([MIN_YEAR, MAX_YEAR])
  const [appliedRange, setAppliedRange] = useState<[number, number]>([MIN_YEAR, MAX_YEAR])
  const [requestError, setRequestError] = useState('')
  const [focus, setFocus] = useState({ code: '', tick: 0 })
  const [modal, setModal] = useState<'admin' | null>(null)
  const [toast, setToast] = useState('')
  const [collapsed, setCollapsed] = useState(false)
  const [thresholds, setThresholds] = useState<Thresholds>(defaultThresholds)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    const climateRequest = getSnapshot(signal).then(data => { if (!signal.aborted) setSnapshot(data) })
    const localRequest = getJson<Local>('/api/local', signal).then(data => { if (!signal.aborted) setLocal(data) })
    getBoundaries(signal).then(data => { if (!signal.aborted) setBoundaries(data) }).catch(() => {})
    getGeo(signal).then(data => { if (!signal.aborted) setGeo(data) }).catch(() => {})
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
  const region: Region = regionOverride ?? 'CR'
  const variable: Variable = section === 'temp' ? 'T2M' : 'PRECTOTCORR'
  const queryParams = new URLSearchParams()
  if (selected) queryParams.set('canton', selected)
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
  const climate = matchingRemote ?? snapshotClimate

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

  /** Cada cantón usa la celda de la malla que más lo cubre; sin polígono propio se usa el promedio nacional. */
  function select(code: string) {
    setSelected(code)
    setRegionOverride(undefined)
    setCell(code ? geo?.cantonCells[code] ?? '' : '')
    setFocus(previous => ({ code, tick: previous.tick + 1 }))
    updateUrl(url => { if (code) url.searchParams.set('canton', code); else url.searchParams.delete('canton'); url.searchParams.delete('aviso') })
  }

  // Un cantón que llega por la URL toma su celda en cuanto se carga la geometría.
  useEffect(() => {
    if (geo && selected) setCell(previous => previous || geo.cantonCells[selected] || '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geo])

  function onLogin(next: Session) {
    setSession(next)
    setModal(null)
    setToast(`Modo administrador activo: ${next.name}. Seguís en el mapa; la sección Admin está en la barra lateral.`)
  }

  /** «Enviar formulario de datos»: abre la sección Admin con el formulario puesto en el cantón actual. */
  function openAdminForm() {
    setSection('admin')
    setCollapsed(false)
  }

  function onLogout() {
    endSession()
    setSession(null)
    if (requestedSection === 'admin') setSection('general')
    setToast('Sesión de administrador cerrada.')
  }

  /** Acepta el código de tres dígitos o el nombre del cantón (sin tildes ni mayúsculas). */
  function resolveCanton(raw: string) {
    const wanted = normalizeText(raw)
    if (/^\d{3}$/.test(wanted) && choices.has(wanted)) return wanted
    for (const [code, info] of choices) if (normalizeText(info.name) === wanted) return code
    return null
  }

  function selectCell(cellRegion: Region, id: string) {
    setRegionOverride(cellRegion)
    setCell(id)
    if (section === 'avisos') setSection('general')
  }

  const notices = catalog.notices.filter(item => item.cantonCodes.includes(selected))
  const operators = catalog.operators.filter(item => item.cantonCodes.includes(selected))
  const alert = alerts[selected] ?? 'none'
  // Si la celda es la propia del cantón, el título sigue siendo el cantón; una celda distinta se nombra aparte.
  const ownCell = !!selected && cell === geo?.cantonCells[selected]
  const zoneName = cell && !ownCell ? `Celda ${cell}` : canton?.name ?? 'Costa Rica'
  const averageLabel = region === 'CR' ? 'Promedio nacional' : 'Promedio del sector'
  const regionName = regions.find(item => item.id === region)?.name

  // Tarjetas bento: usan el snapshot de la celda o del sector y el rango del slider (sin esperar a la API).
  const pick = (name: Variable) => region ? (cell ? snapshot?.cells?.[region]?.[cell]?.[name] : snapshot?.climate[region]?.[name]) : undefined
  const climateBy: Record<Variable, Climate | undefined> = { T2M: pick('T2M'), PRECTOTCORR: pick('PRECTOTCORR') }
  const primary = climateBy[variable]
  const continuity = primary ? continuityOf(primary.series, range) : { valid: 0, total: range[1] - range[0] + 1, pct: 0 }
  const coverage = spatialCoverage(primary?.cells ?? [])
  // Datos que cargan las comisiones (localStorage): afectaciones y registros locales.
  const cantonAffectations = useMemo(() => data.affectations.filter(item => item.cantonCode === selected), [data.affectations, selected])
  const cantonRecords = useMemo(() => data.records.filter(item => item.cantonCode === selected), [data.records, selected])
  const mapAffectations = useMemo(() => {
    const byCanton = new globalThis.Map<string, Affectation[]>()
    for (const item of data.affectations) byCanton.set(item.cantonCode, [...(byCanton.get(item.cantonCode) ?? []), item])
    const result: Record<string, CantonAffectation> = {}
    const rows: AffectationOverview[] = []
    for (const [code, items] of byCanton) {
      const worst = worstOf(items)!
      result[code] = { level: worst.level, type: worst.type }
      rows.push({ code, name: choices.get(code)?.name ?? code, level: worst.level, type: worst.type, count: items.length })
    }
    const order = ['rojo', 'naranja', 'amarillo', 'verde']
    rows.sort((a, b) => order.indexOf(a.level) - order.indexOf(b.level) || a.name.localeCompare(b.name, 'es-CR'))
    return { byCanton: result, overview: rows }
  }, [data.affectations, choices])
  const localStations = [...new Set(cantonRecords.map(item => item.station || 'Fuente local sin nombre'))]
  const stations = stationsLinked(primary, localStations)
  const confidence = confidenceOf(continuity.pct, coverage.pct, stations.count, !!primary)
  const gridStats = useMemo(() => {
    const { withData, total } = buildGrid(snapshot, 'PRECTOTCORR', geo)
    return { withData, total }
  }, [snapshot, geo])
  const projections = {
    T2M: climateBy.T2M ? project(climateBy.T2M.series, 'T2M', range) : undefined,
    PRECTOTCORR: climateBy.PRECTOTCORR ? project(climateBy.PRECTOTCORR.series, 'PRECTOTCORR', range) : undefined,
  }
  const forecastVariables: Variable[] = section === 'temp' ? ['T2M'] : section === 'precip' ? ['PRECTOTCORR'] : ['PRECTOTCORR', 'T2M']
  const forecastRows = forecastVariables.flatMap((name): ForecastRow[] => {
    const projection = projections[name]
    return projection ? [{ variable: name, projection, localStatus: climateBy[name]?.forecast.status }] : []
  })
  const episode = climateBy.PRECTOTCORR?.enso.episode
  const paragraphs = synthesis({
    level, zone: zoneName, regionName, range,
    precip: statsFor(climateBy.PRECTOTCORR, range), temp: statsFor(climateBy.T2M, range),
    enso: episode ? { start: episode.start, end: episode.end, precip: ensoMean(climateBy.PRECTOTCORR), temp: ensoMean(climateBy.T2M) } : undefined,
    confidence, continuityPct: continuity.pct, coveragePct: coverage.pct, stations: stations.count,
    affectations: [...cantonAffectations].sort((a, b) => ['rojo', 'naranja', 'amarillo', 'verde'].indexOf(a.level) - ['rojo', 'naranja', 'amarillo', 'verde'].indexOf(b.level))
      .map(item => ({ typeLabel: affectationLabel(item.type), level: item.level, notes: item.notes, by: item.organization || item.createdBy })),
    local: { temp: localStat(cantonRecords.filter(item => item.variable === 'T2M')), precip: localStat(cantonRecords.filter(item => item.variable === 'PRECTOTCORR')) },
  })
  const noData = <Tile title={copy[level].variableTitle[variable]}>
    <p className="empty">Esta zona todavía no tiene datos NASA POWER asociados: queda pendiente de las comisiones.</p>
  </Tile>
  const quality = <QualityTile level={level} hasData={!!primary} regionName={regionName} coverage={coverage} grid={gridStats}
    continuity={continuity} range={range} stations={stations} confidence={confidence} />
  const forecast = <ForecastTile level={level} zoneName={zoneName} rows={forecastRows} thresholds={thresholds} setThresholds={setThresholds} />

  return <div className="app">
    <Header level={level} mapMode={mapMode} setMapMode={setMapMode} openAdmin={() => setModal('admin')}
      session={session} logout={onLogout} />
    <div className="body">
      <Sidebar level={level} section={section} setSection={setSection} admin={!!session} />
      <div className={collapsed ? 'stage collapsed' : 'stage'}>
        <section className="map-wrap" aria-label="Mapa">
          <Map boundaries={boundaries} geo={geo} snapshot={snapshot} mode={mapMode} variable={variable} level={level} selected={selected}
            selectedCell={cell} alerts={alerts} affectations={mapAffectations.byCanton} focus={focus} select={select} selectCell={selectCell} />
          <FloatingSearch choices={choices} operators={catalog.operators} loading={loading} select={select} />
          <ZoneCard level={level} name={zoneName} province={canton?.province} nasa={!!region} range={range} setRange={setRange}
            selection={!!selected || !!cell} exitZone={() => select('')} admin={!!session} openForm={openAdminForm} />
          <button className="drawer-toggle glass" aria-expanded={!collapsed} aria-controls="ficha"
            aria-label={collapsed ? 'Mostrar el panel de información' : 'Ocultar el panel de información'}
            title={collapsed ? 'Mostrar el panel' : 'Ocultar el panel'} onClick={() => setCollapsed(value => !value)}>
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              {collapsed ? <path d="M20 12H4M10 6l-6 6 6 6" /> : <path d="M4 12h16M14 6l6 6-6 6" />}
            </svg>
          </button>
        </section>
        <aside className="drawer glass" id="ficha" aria-label="Panel de información" inert={collapsed}>
          <div className="drawer-title"><small>{canton ? canton.province : cell ? regionName : 'Costa Rica'}</small><h2>{zoneName}</h2></div>
          <div className="bento">
            {section === 'general' && <>
              {climateBy.T2M && <ChartTile variable="T2M" level={level} series={climateBy.T2M.series} range={range} />}
              {climateBy.PRECTOTCORR && <ChartTile variable="PRECTOTCORR" level={level} series={climateBy.PRECTOTCORR.series} range={range} />}
              {!primary && noData}
              <GeneralPanel level={level} climateBy={climateBy} region={region} canton={canton} cell={cell}
                alert={alert} notices={notices} loading={loading} worst={worstOf(cantonAffectations)} />
              <LocalRecordsTile level={level} records={cantonRecords} />
              {quality}
              <SynthesisTile level={level} paragraphs={paragraphs} />
              {forecast}
            </>}
            {(section === 'temp' || section === 'precip') && <>
              {primary ? <>
                {(() => { const result = projections[variable]; return <ChartTile variable={variable} level={level} series={primary.series} range={range}
                  projection={result?.ok ? result.points : undefined} caption={`${regionName ?? ''} · ${cell ? `Celda ${cell}` : averageLabel}`} /> })()}
                <StatTiles variable={variable} level={level} series={primary.series} range={range} />
              </> : noData}
              <LocalRecordsTile level={level} records={cantonRecords} variable={variable} />
              {quality}
              <SynthesisTile level={level} paragraphs={paragraphs} />
              {forecast}
              <ClimatePanel variable={variable} level={level} climate={climate}
                remote={matchingRemote} queryKey={queryKey} region={region} cell={cell} setCell={setCell}
                setRegion={setRegionOverride} years={years} setYears={setYears} setAppliedYears={setAppliedYears}
                requestError={requestError} setRequestError={setRequestError} loading={loading} catalog={catalog}
                selected={selected} rangeApprox={rangeApprox} />
            </>}
            {section === 'avisos' && <>
              <NoticesPanel level={level} loading={loading} notices={notices} operators={operators}
                catalog={catalog} selected={selected} alert={alert} highlight={params.get('aviso')} highlightCanton={params.get('canton')}
                affectations={cantonAffectations} overview={mapAffectations.overview} select={select} />
              {forecast}
            </>}
            {section === 'admin' && session && <AdminPanel key={selected} session={session} choices={choices} data={data} defaultCanton={selected}
              resolveCanton={resolveCanton} notify={setToast} />}
          </div>
          <p className="muted">{copy[level].mapTip[mapMode]}</p>
        </aside>
      </div>
    </div>
    {modal === 'admin' && !session && <AdminModal onClose={() => setModal(null)} onLogin={onLogin} />}
    {toast && <div className="toast glass" role="status">{toast}</div>}
  </div>
}

createRoot(document.getElementById('root')!).render(<App />)
