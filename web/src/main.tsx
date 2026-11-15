import { useCallback, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { AdminPanel } from './AdminPanel'
import { logout as endSession, restoreSession } from './auth'
import type { Session } from './auth'
import { CantonAsadaTiles } from './AsadaPanels'
import { latestReports, summarizeCantons } from './asadas'
import { ChartsPanel } from './ChartsPanel'
import { Header } from './Header'
import { locale, t, useLang } from './i18n'
import { Landing } from './Landing'
import { Methodology } from './Methodology'
import { Predictions } from './Predictions'
import type { LayerMode } from './layers'
import { normalizeText } from './localData'
import { bboxOf, Map } from './Map'
import type { Focus } from './Map'
import { InfoPanel } from './InfoPanel'
import type { PanelHeader } from './InfoPanel'
import { AdminModal } from './Modals'
import { useCantonData } from './store'
import { MAX_YEAR, MIN_YEAR } from './RangeSlider'
import { Sidebar } from './Sidebar'
import { copy } from './copy'
import type { Alert, Level, MapMode, Section } from './copy'
import { getAsadas, getBoundaries, getCds, getCdsGeo, getGeo, getJson, getSnapshot, getWaterways } from './data'
import type { Boundaries, Canton, CdsData, Climate, Geo, GridGeo, LayerVar, Local, Operator, Region, Snapshot, Variable, Waterways } from './data'
import './style.css'

/** Valor de `?modo=` para cada mapa. */
const MODE_PARAM: Record<MapMode, string> = { grid: 'nasa', cds: 'cds', cantones: 'nacionales' }
const MAP_PARAMS = ['pagina', 'modo', 'canton', 'vista', 'capa', 'anio', 'asada']
const readParams = () => new URLSearchParams(window.location.search)
/** Un enlace con cualquier parámetro del mapa abre el mapa directo; sin parámetros se ve la página de inicio. */
const wantsMap = () => MAP_PARAMS.some(key => readParams().has(key))
type Page = 'inicio' | 'mapa' | 'predicciones' | 'metodologia'
/** `?pagina=predicciones` abre las predicciones, `?pagina=metodologia` su explicación completa; cualquier otro parámetro del mapa abre el mapa; sin parámetros, el inicio. */
const pageFromUrl = (): Page => {
  const page = readParams().get('pagina')
  return page === 'predicciones' || page === 'metodologia' ? page : wantsMap() ? 'mapa' : 'inicio'
}
const modeFromUrl = (): MapMode => {
  const wanted = readParams().get('modo')
  return (Object.keys(MODE_PARAM) as MapMode[]).find(mode => MODE_PARAM[mode] === wanted) ?? 'grid'
}
/** «POWER:9.5:-84.375» → «Celda 9,5° N · 84,375° O» (en inglés, «Cell 9.5° N · 84.375° W»). */
function cellLabel(id: string) {
  const [, lat, lon] = id.split(':')
  const degrees = (value: number) => Math.abs(value).toLocaleString(locale(), { maximumFractionDigits: 3 })
  return `${t('Celda', 'Cell')} ${degrees(Number(lat))}° N · ${degrees(Number(lon))}° ${t('O', 'W')}`
}
const emptyLocal: Local = { cantons: {}, notices: [], operators: [] }
// Nivel de lectura fijo: público general (el selector de escolaridad se retiró).
const level: Level = 'basico'
const sections: Section[] = ['general', 'temp', 'precip', 'uv', 'humedad', 'admin']
const DEFAULT_YEAR = MAX_YEAR
const initialYear = (params: URLSearchParams) => { const value = Number(params.get('anio')); return value >= MIN_YEAR && value <= MAX_YEAR ? Math.round(value) : DEFAULT_YEAR }

function initialSection(params: URLSearchParams): Section {
  const view = params.get('vista')
  if (view === 'clima') return 'precip'
  return sections.find(item => item === view) ?? 'general'
}

function App({ initialMode, goHome, openPredictions }: { initialMode: MapMode; goHome: () => void; openPredictions: () => void }) {
  // Se vuelve a dibujar al cambiar el idioma; `lang` también invalida lo que se calcula con useMemo y lleva textos.
  const lang = useLang()
  // Se leen al montar: el mapa se vuelve a montar cada vez que se entra desde el inicio.
  const [params] = useState(readParams)
  const [snapshot, setSnapshot] = useState<Snapshot>()
  const [boundaries, setBoundaries] = useState<Boundaries>()
  const [geo, setGeo] = useState<Geo>()
  const [local, setLocal] = useState<Local>()
  const [asadas, setAsadas] = useState<Operator[]>([])
  const [waterways, setWaterways] = useState<Waterways>()
  // Mapa «Datos CDS»: capas de Copernicus y su malla de 0,1°. `cdsMissing` = todavía no se corrió `python -m src.cds`.
  const [cds, setCds] = useState<CdsData>()
  const [cdsGeo, setCdsGeo] = useState<GridGeo>()
  const [cdsMissing, setCdsMissing] = useState(false)
  const [loading, setLoading] = useState(true)
  // Sin cantón elegido se ve el país completo; la región por defecto es la malla nacional.
  const [selected, setSelected] = useState(params.get('canton') || '')
  const [session, setSession] = useState<Session | null>(restoreSession)
  const [requestedSection, setSectionState] = useState<Section>(() => initialSection(params))
  // Sin sesión de administrador, la sección Admin nunca se muestra, aunque llegue por la URL.
  const section: Section = requestedSection === 'admin' && !session ? 'general' : requestedSection
  const data = useCantonData()
  const [mapMode, setMapMode] = useState<MapMode>(initialMode)
  const [layerMode, setLayerModeState] = useState<LayerMode>(params.get('capa') === 'valor' ? 'value' : 'slope')
  const [year, setYearState] = useState(() => initialYear(params))
  const [asadaId, setAsadaId] = useState(params.get('asada') || '')
  const [regionOverride, setRegionOverride] = useState<Region>()
  const [cell, setCell] = useState('')
  const [range, setRange] = useState<[number, number]>([MIN_YEAR, MAX_YEAR])
  const [focus, setFocus] = useState<Focus>({ code: '', tick: 0 })
  const [modal, setModal] = useState<'admin' | null>(null)
  const [toast, setToast] = useState('')
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    const climateRequest = getSnapshot(signal).then(data => { if (!signal.aborted) setSnapshot(data) })
    const localRequest = getJson<Local>('/api/local', signal).then(data => { if (!signal.aborted) setLocal(data) })
    getBoundaries(signal).then(data => { if (!signal.aborted) setBoundaries(data) }).catch(() => {})
    getGeo(signal).then(data => { if (!signal.aborted) setGeo(data) }).catch(() => {})
    getAsadas(signal).then(data => { if (!signal.aborted) setAsadas(data.operators) }).catch(() => {})
    void Promise.allSettled([climateRequest, localRequest]).then(() => { if (!signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [])

  // La hidrografía pesa unos 4,5 MB: solo se pide la primera vez que se abre el mapa de cuencas.
  useEffect(() => {
    if (mapMode !== 'cantones' || waterways) return
    const controller = new AbortController()
    getWaterways(controller.signal).then(data => { if (!controller.signal.aborted) setWaterways(data) }).catch(() => {})
    return () => controller.abort()
  }, [mapMode, waterways])

  // Los datos del CDS solo se piden la primera vez que se abre «Datos CDS».
  useEffect(() => {
    if (mapMode !== 'cds' || cdsGeo) return
    const controller = new AbortController()
    getCdsGeo(controller.signal).then(data => { if (!controller.signal.aborted) setCdsGeo(data) }).catch(() => {})
    return () => controller.abort()
  }, [mapMode, cdsGeo])
  useEffect(() => {
    if (mapMode !== 'cds' || cds || cdsMissing) return
    const controller = new AbortController()
    getCds(controller.signal).then(data => { if (!controller.signal.aborted) setCds(data) })
      .catch(() => { if (!controller.signal.aborted) setCdsMissing(true) })
    return () => controller.abort()
  }, [mapMode, cds, cdsMissing])

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
  // Cada cantón usa la celda que más lo cubre en la malla del mapa activo (NASA POWER 0,5° o ERA5-Land 0,1°).
  const cantonCells = (mapMode === 'cds' ? cdsGeo?.cantonCells : geo?.cantonCells) ?? {}
  // Secciones que no aplican en el mapa activo, con su motivo (sirve de tooltip). En «Datos CDS» el UV depende de que
  // exista su capa en cds.json: sin el archivo de ERA5 se desactiva y, al cargarlo, se reactiva sola.
  const noClimate = t('No aplica en el mapa de datos nacionales: este mapa no tiene datos climáticos.', 'Does not apply to the national data map: this map has no climate data.')
  const disabled: Partial<Record<Section, string>> = mapMode === 'cantones'
    ? { general: noClimate, temp: noClimate, precip: noClimate, uv: noClimate, humedad: noClimate }
    : mapMode === 'cds' && !cds?.layers.UV ? { uv: t('La radiación UV todavía no está disponible en el mapa de CDS.', 'UV radiation is not available yet on the CDS map.') } : {}
  // Una sección desactivada (p. ej. UV que llega por la URL o desde el mapa de NASA) cae a «general».
  const activeSection: Section = disabled[section] ? 'general' : section
  const variable: Variable = activeSection === 'temp' ? 'T2M' : 'PRECTOTCORR'
  // Capa que pinta el mapa nacional: UV y Humedad tienen su propia sección en la barra lateral.
  const mapVar: LayerVar = activeSection === 'uv' ? 'UV' : activeSection === 'humedad' ? 'RH2M' : variable

  function updateUrl(change: (url: URL) => void) {
    const url = new URL(window.location.href)
    url.searchParams.set('pagina', 'mapa')
    change(url)
    history.replaceState(null, '', url)
  }

  const setSection = useCallback((value: Section) => {
    setSectionState(value)
    updateUrl(url => url.searchParams.set('vista', value))
  }, [])

  const setLayerMode = useCallback((value: LayerMode) => {
    setLayerModeState(value)
    updateUrl(url => { if (value === 'value') url.searchParams.set('capa', 'valor'); else url.searchParams.delete('capa') })
  }, [])
  const setYear = useCallback((value: number) => {
    setYearState(value)
    updateUrl(url => url.searchParams.set('anio', String(value)))
  }, [])

  /** Cada cantón usa la celda de la malla que más lo cubre; sin polígono propio se usa el promedio nacional. */
  function select(code: string) {
    setSelected(code)
    setAsadaId('')
    setRegionOverride(undefined)
    setCell(code ? cantonCells[code] ?? '' : '')
    setFocus(previous => ({ code, tick: previous.tick + 1 }))
    if (code) setCollapsed(false)
    updateUrl(url => { if (code) url.searchParams.set('canton', code); else url.searchParams.delete('canton'); url.searchParams.delete('aviso'); url.searchParams.delete('asada') })
  }

  /** Elegir un operador de agua acerca el mapa a su cantón y abre su ficha. Los operadores no se dibujan en el mapa. */
  function selectAsada(operator: Operator) {
    select(operator.cantonCode)
    setAsadaId(operator.id)
    setCollapsed(false)
    updateUrl(url => url.searchParams.set('asada', operator.id))
  }

  /** Hacer clic en la barra de búsqueda cierra la ASADA elegida (por la guía «Buscar por lugar» o por el buscador): queda el cantón con todas sus ASADAs. */
  function closeAsada() {
    if (!asadaId) return
    setAsadaId('')
    updateUrl(url => url.searchParams.delete('asada'))
  }

  /** Elegir una provincia en el ayudante de búsqueda acerca el mapa a ella. */
  function selectProvince(name: string) {
    const wanted = normalizeText(name)
    const shape = geo?.provinces.find(item => normalizeText(item.properties?.name ?? '') === wanted)
    const bbox = shape && bboxOf(shape.geometry)
    setSelected('')
    setAsadaId('')
    setCell('')
    setRegionOverride(undefined)
    updateUrl(url => { url.searchParams.delete('canton'); url.searchParams.delete('aviso'); url.searchParams.delete('asada') })
    setFocus(previous => ({ code: '', bbox, tick: previous.tick + 1 }))
  }

  /** Cambiar de mapa deja atrás cualquier selección (cantón o celda) y aleja la cámara a la vista completa. */
  function changeMapMode(mode: MapMode) {
    setMapMode(mode)
    updateUrl(url => url.searchParams.set('modo', MODE_PARAM[mode]))
    setSelected('')
    setAsadaId('')
    setRegionOverride(undefined)
    setCell('')
    updateUrl(url => { url.searchParams.delete('canton'); url.searchParams.delete('aviso'); url.searchParams.delete('asada') })
    setFocus(previous => ({ code: '', tick: previous.tick + 1 }))
  }

  // Un cantón que llega por la URL toma su celda en cuanto se carga la geometría.
  useEffect(() => {
    if (geo && selected) setCell(previous => previous || geo.cantonCells[selected] || '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geo])

  function onLogin(next: Session) {
    setSession(next)
    setModal(null)
    setToast(t(`Modo administrador activo: ${next.name}. Seguís en el mapa; el formulario de tu ASADA está en la sección Admin.`, `Administrator mode active: ${next.name}. You are still on the map; your ASADA's form is in the Admin section.`))
  }

  function onLogout() {
    endSession()
    setSession(null)
    if (requestedSection === 'admin') setSection('general')
    setToast(t('Sesión de administrador cerrada.', 'Administrator session closed.'))
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
    setCollapsed(false)
  }

  // Si la celda es la propia del cantón, el título sigue siendo el cantón; una celda distinta se nombra por sus provincias.
  const ownCell = !!selected && cell === cantonCells[selected]
  const zoneName = cell && !ownCell ? `${t('Celda', 'Cell')} ${cell}` : canton?.name ?? 'Costa Rica'
  const inGrid = mapMode !== 'cantones'
  // Encabezado del panel: en los mapas de malla, la celda va pequeña arriba y debajo sus provincias y cantones.
  const cellCodes = (inGrid && cell ? (mapMode === 'cds' ? cdsGeo?.cellCantons : geo?.cellCantons)?.[cell] : undefined) ?? []
  const asadaOperator = useMemo(() => asadas.find(item => item.id === asadaId && item.cantonCode === selected), [asadas, asadaId, selected])
  const header: PanelHeader = useMemo(() => {
    const cellTag = inGrid && cell ? cellLabel(cell) : undefined
    if (cellTag && !ownCell) {
      const provinces = [...new Set(cellCodes.map(code => choices.get(code)?.province).filter((name): name is string => !!name))]
      const names = cellCodes.map(code => choices.get(code)?.name).filter((name): name is string => !!name)
      return { cellTag, title: provinces.join(' · ') || t('Fuera del territorio nacional', 'Outside the national territory'), cantons: names.join(', ') || undefined }
    }
    // Mapa de cuencas con una ASADA elegida: solo su provincia y su cantón (la ASADA va en su tarjeta).
    if (mapMode === 'cantones' && asadaOperator) return { kicker: asadaOperator.province, title: asadaOperator.canton }
    return { cellTag, kicker: canton ? canton.province : undefined, title: canton?.name ?? 'Costa Rica' }
  }, [inGrid, mapMode, asadaOperator, cell, ownCell, cellCodes, choices, canton, lang])

  // Tarjetas de gráfica: usan el snapshot de la celda o del sector (sin esperar a la API).
  const pick = (name: Variable) => region ? (cell ? snapshot?.cells?.[region]?.[cell]?.[name] : snapshot?.climate[region]?.[name]) : undefined
  const climateBy: Record<Variable, Climate | undefined> = { T2M: pick('T2M'), PRECTOTCORR: pick('PRECTOTCORR') }
  // Datos que cargan las ASADAs (localStorage): reportes de caudal y afectación.
  const latest = useMemo(() => latestReports(data.reports), [data.reports])
  const summaries = useMemo(() => summarizeCantons(asadas, latest), [asadas, latest])
  // Mapa de cuencas: un cantón abierto muestra solo sus ASADAs con el histórico de caudal.
  const cantonAsadas = useMemo(() => selected ? asadas.filter(item => item.cantonCode === selected) : [], [asadas, selected])
  // Una ASADA elegida (buscador o URL) de este cantón se muestra sola; sin ASADA elegida, todas las del cantón.
  const shownAsadas = useMemo(() => { const one = cantonAsadas.find(item => item.id === asadaId); return one ? [one] : cantonAsadas }, [cantonAsadas, asadaId])
  const cantonReports = useMemo(() => {
    const ids = new Set(cantonAsadas.map(item => item.id))
    return data.reports.filter(item => ids.has(item.asadaId))
  }, [data.reports, cantonAsadas])
  // Mapa de cuencas sin cantón elegido: el panel no muestra información (solo el buscador). El formulario del administrador sí queda.
  const blank = mapMode === 'cantones' && !selected && !(section === 'admin' && session)
  /** «Atrás»: de una ASADA vuelve a la lista de su cantón; de un cantón (o celda) vuelve a Costa Rica. */
  function goBack() {
    if (mapMode === 'cantones' && asadaId) { setAsadaId(''); updateUrl(url => url.searchParams.delete('asada')) } else select('')
  }
  const sessionAsada = session ? asadas.find(item => item.id === session.asadaId) : undefined

  return <div className="app">
    <Header level={level} mapMode={mapMode} setMapMode={changeMapMode} openAdmin={() => setModal('admin')}
      session={session} logout={onLogout} goHome={goHome} openPredictions={openPredictions} />
    <div className="body">
      <Sidebar level={level} section={activeSection} setSection={setSection} admin={!!session} disabled={disabled} />
      <div className={collapsed ? 'stage collapsed' : 'stage'}>
        <section className="map-wrap" aria-label={t('Mapa', 'Map')}>
          <Map boundaries={boundaries} geo={geo} snapshot={snapshot} cds={cds} cdsGeo={cdsGeo} cdsMissing={cdsMissing} waterways={waterways} mode={mapMode} variable={mapVar}
            layerMode={layerMode} range={range} year={year} level={level} selected={selected} selectedCell={cell} alerts={alerts}
            cantonStatus={summaries} focus={focus} select={select} selectCell={selectCell} />
          <button className="drawer-toggle glass" aria-expanded={!collapsed} aria-controls="ficha"
            aria-label={collapsed ? t('Mostrar el panel de información', 'Show the information panel') : t('Ocultar el panel de información', 'Hide the information panel')}
            title={collapsed ? t('Mostrar el panel', 'Show the panel') : t('Ocultar el panel', 'Hide the panel')} onClick={() => setCollapsed(value => !value)}>
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              {collapsed ? <path d="M20 12H4M10 6l-6 6 6 6" /> : <path d="M4 12h16M14 6l6 6-6 6" />}
            </svg>
          </button>
        </section>
        <InfoPanel choices={choices} asadas={asadas} mode={mapMode} loading={loading} blank={blank} back={goBack}
          select={select} selectAsada={selectAsada} selectProvince={selectProvince} closeAsada={closeAsada}
          selected={selected} cell={cell} header={header}
          collapsed={collapsed} mapTip={copy[level].mapTip[mapMode]}>
          {blank ? null : section === 'admin' && session
            ? <AdminPanel key={session.asadaId} session={session} asada={sessionAsada} choices={choices} data={data} resolveCanton={resolveCanton} notify={setToast} />
            : mapMode === 'cantones' && selected
              ? <CantonAsadaTiles operators={shownAsadas} reports={cantonReports} />
              : <ChartsPanel mapMode={mapMode} level={level} zoneName={zoneName} climateBy={climateBy} uvLayer={snapshot?.layers?.UV} humedadLayer={snapshot?.layers?.RH2M} cds={cds}
              cell={cell} range={range} setRange={setRange} layerMode={layerMode} setLayerMode={setLayerMode} year={year} setYear={setYear} />}
        </InfoPanel>
      </div>
    </div>
    {modal === 'admin' && !session && <AdminModal onClose={() => setModal(null)} onLogin={onLogin} />}
    {toast && <div className="toast glass" role="status">{toast}</div>}
  </div>
}

/** Elige entre la página de inicio y el mapa. Cada cambio queda en el historial: «Atrás» vuelve a la página anterior. */
function Root() {
  useLang() // al cambiar el idioma, Root se vuelve a dibujar y arrastra a todo el árbol (los textos salen de `t()`)
  const [page, setPage] = useState<Page>(pageFromUrl)
  const [mode, setMode] = useState<MapMode>(modeFromUrl)
  // Cambia cada vez que se entra al mapa, para que se monte de cero con la URL nueva.
  const [visit, setVisit] = useState(0)

  useEffect(() => {
    const onPop = () => {
      setPage(pageFromUrl())
      setMode(modeFromUrl())
      setVisit(value => value + 1)
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  function openMap(next: MapMode) {
    const url = new URL(window.location.href)
    url.search = ''
    url.hash = ''
    url.searchParams.set('pagina', 'mapa')
    url.searchParams.set('modo', MODE_PARAM[next])
    history.pushState(null, '', url)
    setMode(next)
    setVisit(value => value + 1)
    setPage('mapa')
    window.scrollTo(0, 0)
  }

  function openPredictions() {
    const url = new URL(window.location.href)
    url.search = ''
    url.hash = ''
    url.searchParams.set('pagina', 'predicciones')
    history.pushState(null, '', url)
    setPage('predicciones')
    window.scrollTo(0, 0)
  }

  function goHome() {
    history.pushState(null, '', window.location.pathname)
    setPage('inicio')
    window.scrollTo(0, 0)
  }

  if (page === 'mapa') return <App key={visit} initialMode={mode} goHome={goHome} openPredictions={openPredictions} />
  if (page === 'predicciones') return <Predictions openMap={openMap} goHome={goHome} />
  if (page === 'metodologia') return <Methodology goBack={openPredictions} />
  return <Landing openMap={openMap} openPredictions={openPredictions} />
}

createRoot(document.getElementById('root')!).render(<Root />)
