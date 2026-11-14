import { useEffect, useMemo, useRef, useState } from 'react'
import { Map as MapLibreMap, NavigationControl, Popup } from 'maplibre-gl'
import type { ExpressionSpecification, GeoJSONSource } from 'maplibre-gl'
import type { Feature, FeatureCollection, Geometry, Polygon, Position } from 'geojson'
import { copy } from './copy'
import type { Alert, Level, MapMode } from './copy'
import type { Boundaries, Region, Snapshot, Variable } from './data'
import 'maplibre-gl/dist/maplibre-gl.css'

const empty: FeatureCollection = { type: 'FeatureCollection', features: [] }
const LAT_STEP = 0.5
const LON_STEP = 0.625
const CR_BOUNDS: [number, number, number, number] = [-86.05, 8.0, -82.5, 11.35]
const SKY = '#38BDF8'
const AMBER = '#f59e0b'

type GridProps = { id: string; region: string; has: number; slope: number; significant: number }

function bboxOf(geometry: Geometry): [number, number, number, number] | undefined {
  let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity
  const visit = (value: unknown) => {
    if (!Array.isArray(value)) return
    if (typeof value[0] === 'number') {
      const [lon, lat] = value as Position
      west = Math.min(west, lon); east = Math.max(east, lon); south = Math.min(south, lat); north = Math.max(north, lat)
    } else value.forEach(visit)
  }
  if (geometry.type === 'Polygon' || geometry.type === 'MultiPolygon') visit(geometry.coordinates)
  return Number.isFinite(west) ? [west, south, east, north] : undefined
}

/** Celdas con datos del snapshot y, alrededor, la malla vacía de NASA POWER (0,5° × 0,625°) sobre el territorio. */
export function buildGrid(snapshot: Snapshot | undefined, variable: Variable, boundaries: Boundaries | undefined) {
  const features: Feature<Polygon, GridProps>[] = []
  const taken = new Set<string>()
  const key = (lat: number, lon: number) => `${Math.round((lat + 90) / LAT_STEP)}_${Math.round((lon + 180) / LON_STEP)}`
  const rect = (west: number, south: number, east: number, north: number): Polygon => ({
    type: 'Polygon', coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
  })
  let extent = 0
  for (const [region, variables] of Object.entries(snapshot?.climate ?? {})) {
    for (const cell of variables[variable]?.cells ?? []) {
      const id = `${cell.id}`
      if (taken.has(key(cell.lat, cell.lon))) continue
      taken.add(key(cell.lat, cell.lon))
      const slope = cell.long_term_slope
      if (slope != null) extent = Math.max(extent, Math.abs(slope))
      features.push({ type: 'Feature', properties: { id, region, has: slope == null ? 0 : 1, slope: slope ?? 0, significant: cell.significant ? 1 : 0 },
        geometry: rect(...cell.bbox) })
    }
  }
  const boxes = (boundaries?.features ?? []).map(item => bboxOf(item.geometry)).filter((box): box is [number, number, number, number] => !!box)
  if (boxes.length) {
    for (let lat = Math.floor((CR_BOUNDS[1] + 90.25) / LAT_STEP) * LAT_STEP - 90.25; lat < CR_BOUNDS[3]; lat += LAT_STEP) {
      for (let lon = Math.floor((CR_BOUNDS[0] + 180.3125) / LON_STEP) * LON_STEP - 180.3125; lon < CR_BOUNDS[2]; lon += LON_STEP) {
        const [south, north, west, east] = [lat, lat + LAT_STEP, lon, lon + LON_STEP]
        if (taken.has(key((south + north) / 2, (west + east) / 2))) continue
        if (!boxes.some(box => box[0] < east && box[2] > west && box[1] < north && box[3] > south)) continue
        features.push({ type: 'Feature', properties: { id: '', region: '', has: 0, slope: 0, significant: 0 }, geometry: rect(west, south, east, north) })
      }
    }
  }
  return { data: { type: 'FeatureCollection', features } as FeatureCollection<Polygon, GridProps>, extent: extent || 1 }
}

export function Map({ boundaries, snapshot, mode, variable, level, selected, selectedCell, alerts, focus, select, selectCell }: {
  boundaries?: Boundaries; snapshot?: Snapshot; mode: MapMode; variable: Variable; level: Level
  selected: string; selectedCell: string; alerts: Record<string, Alert>; focus: { code: string; tick: number }
  select: (code: string) => void; selectCell: (region: Region, id: string) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  const grid = useMemo(() => buildGrid(snapshot, variable, boundaries), [snapshot, variable, boundaries])
  const latest = useRef({ select, selectCell, mode, level, alerts, variable })
  latest.current = { select, selectCell, mode, level, alerts, variable }

  useEffect(() => {
    if (!container.current) return
    let instance: MapLibreMap
    try {
      instance = new MapLibreMap({
        container: container.current, center: [-84.15, 9.95], zoom: 6.4, dragRotate: false, pitchWithRotate: false,
        style: { version: 8, sources: {}, layers: [{ id: 'water', type: 'background', paint: { 'background-color': '#cfeaf6' } }] },
      })
    } catch {
      setFailed(true)
      return
    }
    map.current = instance
    instance.addControl(new NavigationControl({ showCompass: false }), 'bottom-right')
    const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 8 })
    instance.on('load', () => {
      instance.addSource('cantons', { type: 'geojson', data: empty })
      instance.addSource('grid', { type: 'geojson', data: empty })
      instance.addLayer({ id: 'cantons', source: 'cantons', type: 'fill', paint: { 'fill-color': '#e2eef5', 'fill-opacity': 0.85 } })
      instance.addLayer({ id: 'canton-lines', source: 'cantons', type: 'line', paint: { 'line-color': '#ffffff', 'line-width': 1 } })
      instance.addLayer({ id: 'grid-fill', source: 'grid', type: 'fill', paint: { 'fill-color': '#ffffff', 'fill-opacity': 0 } })
      instance.addLayer({ id: 'grid-line', source: 'grid', type: 'line', paint: { 'line-color': '#0c4a6e', 'line-opacity': 0.45, 'line-width': 0.8 } })
      instance.addLayer({ id: 'grid-selected', source: 'grid', type: 'line', filter: ['==', ['get', 'id'], ''], paint: { 'line-color': '#0c4a6e', 'line-width': 3 } })
      instance.addLayer({ id: 'canton-selected', source: 'cantons', type: 'line', filter: ['==', ['get', 'code'], ''], paint: { 'line-color': '#0c4a6e', 'line-width': 3 } })

      instance.on('click', event => {
        const { mode: current } = latest.current
        if (current === 'grid') {
          const cell = instance.queryRenderedFeatures(event.point, { layers: ['grid-fill'] }).find(item => item.properties?.has === 1)
          if (cell?.properties) { latest.current.selectCell(String(cell.properties.region) as Region, String(cell.properties.id)); return }
        }
        const code = instance.queryRenderedFeatures(event.point, { layers: ['cantons'] })[0]?.properties?.code
        if (code) latest.current.select(String(code))
      })
      instance.on('mousemove', event => {
        const { mode: current, level: lvl, alerts: states, variable: variableNow } = latest.current
        const cell = current === 'grid' ? instance.queryRenderedFeatures(event.point, { layers: ['grid-fill'] })[0] : undefined
        const canton = instance.queryRenderedFeatures(event.point, { layers: ['cantons'] })[0]
        let text = ''
        if (cell?.properties?.has === 1) {
          const slope = Number(cell.properties.slope).toLocaleString('es-CR', { maximumFractionDigits: 2 })
          text = `Celda ${cell.properties.id} · ${slope} ${copy[lvl].unit[variableNow]}/década`
        } else if (cell) text = 'Celda sin descarga'
        else if (canton?.properties) text = `${canton.properties.name} · ${copy[lvl].alertLabel[states[String(canton.properties.code)] ?? 'none']}`
        instance.getCanvas().style.cursor = text ? 'pointer' : ''
        if (text) popup.setLngLat(event.lngLat).setText(text).addTo(instance)
        else popup.remove()
      })
      instance.on('mouseout', () => popup.remove())
      instance.fitBounds([[CR_BOUNDS[0], CR_BOUNDS[1]], [CR_BOUNDS[2], CR_BOUNDS[3]]], { padding: 24, duration: 0 })
      setReady(true)
    })
    // El panel lateral se colapsa y cambia el ancho del contenedor: el mapa debe redibujarse.
    const observer = new ResizeObserver(() => instance.resize())
    observer.observe(container.current)
    return () => { observer.disconnect(); popup.remove(); instance.remove(); map.current = null }
  }, [])

  useEffect(() => {
    if (ready) (map.current?.getSource('cantons') as GeoJSONSource).setData(boundaries ?? empty)
  }, [ready, boundaries])

  useEffect(() => {
    if (ready) (map.current?.getSource('grid') as GeoJSONSource).setData(grid.data)
  }, [ready, grid])

  useEffect(() => {
    const instance = map.current
    if (!ready || !instance) return
    const isGrid = mode === 'grid'
    for (const layer of ['grid-fill', 'grid-line', 'grid-selected']) instance.setLayoutProperty(layer, 'visibility', isGrid ? 'visible' : 'none')
    const byAlert = ['match', ['get', 'code'],
      ...Object.entries(alerts).filter(([, state]) => state !== 'none').flatMap(([code, state]) => [code, state === 'active' ? AMBER : SKY]),
      '#e2eef5'] as unknown as ExpressionSpecification
    const hasAlerts = Object.values(alerts).some(state => state !== 'none')
    instance.setPaintProperty('cantons', 'fill-color', isGrid ? '#ffffff' : hasAlerts ? byAlert : '#e2eef5')
    instance.setPaintProperty('cantons', 'fill-opacity', isGrid ? 0.4 : 0.9)
    instance.setPaintProperty('canton-lines', 'line-color', isGrid ? '#7aa7c2' : '#ffffff')
    instance.setPaintProperty('canton-lines', 'line-width', isGrid ? 0.6 : 1.2)
    instance.setFilter('canton-selected', ['==', ['get', 'code'], selected])
    instance.setFilter('grid-selected', ['==', ['get', 'id'], selectedCell])
    const [low, high] = variable === 'T2M' ? [SKY, AMBER] : [AMBER, SKY]
    instance.setPaintProperty('grid-fill', 'fill-color', ['case', ['==', ['get', 'has'], 1],
      ['interpolate', ['linear'], ['get', 'slope'], -grid.extent, low, 0, '#f8fafc', grid.extent, high], 'rgba(255,255,255,0)'])
    instance.setPaintProperty('grid-fill', 'fill-opacity', ['case', ['==', ['get', 'has'], 1], 0.8, 0])
    instance.setPaintProperty('grid-line', 'line-opacity', ['case', ['==', ['get', 'has'], 1], 0.55, 0.3])
  }, [ready, mode, alerts, selected, selectedCell, variable, grid])

  useEffect(() => {
    const instance = map.current
    const feature = boundaries?.features.find(item => item.properties.code === focus.code)
    const box = feature && bboxOf(feature.geometry)
    if (ready && instance && box && focus.tick > 0) {
      instance.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 90, maxZoom: 10, duration: 700 })
    }
  }, [ready, focus, boundaries])

  const unit = copy[level].unit[variable]
  const [low, high] = variable === 'T2M' ? [SKY, AMBER] : [AMBER, SKY]
  const extent = grid.extent.toLocaleString('es-CR', { maximumFractionDigits: 2 })
  return <>
    <div className="map" ref={container} aria-label="Mapa de Costa Rica" />
    {!failed && <div className="legend glass" aria-label="Leyenda del mapa">
      {mode === 'grid' ? <>
        <strong>Pendiente por década ({unit})</strong>
        <div className="legend-bar" style={{ background: `linear-gradient(90deg, ${low}, #f8fafc, ${high})` }} />
        <div className="legend-scale"><span>−{extent}</span><span>0</span><span>+{extent}</span></div>
        <span>Cuadros sin color: sin descarga de NASA POWER.</span>
      </> : <>
        <strong>Avisos por cantón</strong>
        {(['active', 'expired', 'none'] as const).map(state => <div className="legend-row" key={state}>
          <span className="swatch" style={{ background: state === 'active' ? AMBER : state === 'expired' ? SKY : '#e2eef5' }} />{copy[level].alertLabel[state]}
        </div>)}
      </>}
    </div>}
    <p className="map-caption">{failed ? 'El mapa requiere WebGL. Podés seleccionar un cantón desde el buscador.'
      : boundaries ? `${boundaries.features.length} cantones con polígono propio.` : 'Cargando la capa cantonal…'}</p>
  </>
}
