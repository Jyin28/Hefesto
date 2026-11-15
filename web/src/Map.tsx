import { useEffect, useMemo, useRef, useState } from 'react'
import { Map as MapLibreMap, Marker, NavigationControl, Popup } from 'maplibre-gl'
import type { ExpressionSpecification, GeoJSONSource, LngLatBoundsLike } from 'maplibre-gl'
import type { Feature, FeatureCollection, Geometry, MultiPolygon, Polygon, Position } from 'geojson'
import { ALERT_LABEL } from './analysis'
import type { AlertLevel } from './analysis'
import { copy } from './copy'
import type { Alert, Level, MapMode } from './copy'
import { affectationLabel } from './store'
import type { Boundaries, Geo, Region, Snapshot, Variable } from './data'
import 'maplibre-gl/dist/maplibre-gl.css'

const empty: FeatureCollection = { type: 'FeatureCollection', features: [] }
// Límites del mapa: la malla NASA POWER 7×7 (8,25–11,75 °N · 86,5625–82,1875 °O) más 0,25° al sur para que
// quepa la punta de Burica. Fuera de este rectángulo no se puede navegar.
const VIEW_BOUNDS: LngLatBoundsLike = [[-86.5625, 8.0], [-82.1875, 11.75]]
const SKY = '#38BDF8'
const AMBER = '#f59e0b'
const SEA = '#cfeaf6'
const LAND = '#f1f6fa'
const NEIGHBOR = '#e4dfd5'
const NOTICE_ACTIVE = '#38BDF8'
const NOTICE_EXPIRED = '#bfdbfe'
const LEVEL_COLOR: Record<AlertLevel, string> = { verde: '#10B981', amarillo: '#FACC15', naranja: '#F97316', rojo: '#EF4444' }
export type CantonAffectation = { level: AlertLevel; type: string }

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

/**
 * Malla NASA POWER 7×7 completa. `lines` son los 49 cuadros enteros (las esquinas incluidas) y `land` solo la
 * porción de cada cuadro que cae dentro del territorio nacional, que es lo único que se colorea.
 */
export function buildGrid(snapshot: Snapshot | undefined, variable: Variable, geo: Geo | undefined) {
  const data = new globalThis.Map<string, { slope: number | null; significant: boolean | null }>()
  for (const cell of snapshot?.climate.CR?.[variable]?.cells ?? []) {
    data.set(cell.id, { slope: cell.long_term_slope, significant: cell.significant })
  }
  const lines: Feature<Polygon, GridProps>[] = []
  const land: Feature<Polygon | MultiPolygon, GridProps>[] = []
  let extent = 0
  let withData = 0
  for (const cell of geo?.cells ?? []) {
    const found = data.get(cell.id)
    const slope = found?.slope ?? null
    if (slope != null) extent = Math.max(extent, Math.abs(slope))
    const properties: GridProps = { id: cell.id, region: 'CR', has: slope == null ? 0 : 1, slope: slope ?? 0, significant: found?.significant ? 1 : 0 }
    const [west, south, east, north] = cell.bbox
    lines.push({ type: 'Feature', properties, geometry: { type: 'Polygon', coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]] } })
    if (cell.land && cell.landFraction >= 0.01) {
      land.push({ type: 'Feature', properties, geometry: cell.land })
      if (slope != null) withData += 1
    }
  }
  return {
    lines: { type: 'FeatureCollection', features: lines } as FeatureCollection<Polygon, GridProps>,
    land: { type: 'FeatureCollection', features: land } as FeatureCollection<Polygon | MultiPolygon, GridProps>,
    extent: extent || 1, withData, total: land.length,
  }
}

const collection = (features: Feature[] | undefined): FeatureCollection => ({ type: 'FeatureCollection', features: features ?? [] })

/** Ajusta el zoom mínimo y los límites al tamaño actual del contenedor (cambia al colapsar el panel). */
function lockView(instance: MapLibreMap) {
  const camera = instance.cameraForBounds(VIEW_BOUNDS)
  if (!camera || camera.zoom === undefined) return
  instance.setMinZoom(camera.zoom)
  instance.setMaxBounds(VIEW_BOUNDS)
}

function labelElement(text: string) {
  const element = document.createElement('div')
  element.className = 'geo-label'
  element.textContent = text
  return element
}

export function Map({ boundaries, geo, snapshot, mode, variable, level, selected, selectedCell, alerts, affectations, focus, select, selectCell }: {
  boundaries?: Boundaries; geo?: Geo; snapshot?: Snapshot; mode: MapMode; variable: Variable; level: Level
  selected: string; selectedCell: string; alerts: Record<string, Alert>; affectations: Record<string, CantonAffectation>
  focus: { code: string; tick: number }
  select: (code: string) => void; selectCell: (region: Region, id: string) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  const grid = useMemo(() => buildGrid(snapshot, variable, geo), [snapshot, variable, geo])
  const latest = useRef({ select, selectCell, mode, level, alerts, affectations, variable })
  latest.current = { select, selectCell, mode, level, alerts, affectations, variable }

  useEffect(() => {
    if (!container.current) return
    let instance: MapLibreMap
    try {
      instance = new MapLibreMap({
        container: container.current, bounds: VIEW_BOUNDS, dragRotate: false, pitchWithRotate: false, maxZoom: 11,
        style: { version: 8, sources: {}, layers: [{ id: 'water', type: 'background', paint: { 'background-color': SEA } }] },
      })
    } catch {
      setFailed(true)
      return
    }
    map.current = instance
    instance.addControl(new NavigationControl({ showCompass: false }), 'bottom-right')
    instance.touchZoomRotate.disableRotation()
    const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 8 })
    const labels = [
      new Marker({ element: labelElement('Nicaragua'), anchor: 'center' }).setLngLat([-84.3, 11.45]),
      new Marker({ element: labelElement('Panamá'), anchor: 'center' }).setLngLat([-82.75, 8.8]),
    ]
    instance.on('load', () => {
      for (const name of ['neighbors', 'cantons', 'grid-land', 'grid', 'provinces', 'country']) instance.addSource(name, { type: 'geojson', data: empty })
      // De abajo hacia arriba: vecinos, relleno cantonal, relleno de la malla, cuadrícula (tenue), cantones, provincias y país.
      instance.addLayer({ id: 'neighbors', source: 'neighbors', type: 'fill', paint: { 'fill-color': NEIGHBOR, 'fill-opacity': 1 } })
      instance.addLayer({ id: 'neighbor-lines', source: 'neighbors', type: 'line', paint: { 'line-color': '#b9b2a4', 'line-width': 1 } })
      instance.addLayer({ id: 'cantons', source: 'cantons', type: 'fill', paint: { 'fill-color': LAND, 'fill-opacity': 1 } })
      instance.addLayer({ id: 'grid-fill', source: 'grid-land', type: 'fill', paint: { 'fill-color': '#ffffff', 'fill-opacity': 0 } })
      instance.addLayer({ id: 'grid-line', source: 'grid', type: 'line', paint: { 'line-color': '#0c4a6e', 'line-opacity': 0.22, 'line-width': 0.6 } })
      instance.addLayer({ id: 'canton-lines', source: 'cantons', type: 'line', paint: { 'line-color': '#1e293b', 'line-opacity': 0.6, 'line-width': 0.9 } })
      instance.addLayer({ id: 'province-lines', source: 'provinces', type: 'line', layout: { 'line-join': 'round' }, paint: { 'line-color': '#0f172a', 'line-opacity': 0.85, 'line-width': 1.8 } })
      instance.addLayer({ id: 'country-line', source: 'country', type: 'line', layout: { 'line-join': 'round' }, paint: { 'line-color': '#082f49', 'line-width': 2.6 } })
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
        const { mode: current, level: lvl, alerts: states, affectations: affected, variable: variableNow } = latest.current
        const cell = current === 'grid' ? instance.queryRenderedFeatures(event.point, { layers: ['grid-fill'] })[0] : undefined
        const canton = instance.queryRenderedFeatures(event.point, { layers: ['cantons'] })[0]
        let text = ''
        if (cell?.properties?.has === 1) {
          const slope = Number(cell.properties.slope).toLocaleString('es-CR', { maximumFractionDigits: 2 })
          text = `${canton?.properties ? `${canton.properties.name} · ` : ''}Celda ${cell.properties.id} · ${slope} ${copy[lvl].unit[variableNow]}/década`
        } else if (cell) text = 'Celda sin descarga'
        else if (canton?.properties) {
          const code = String(canton.properties.code)
          const affectation = current === 'cantones' ? affected[code] : undefined
          text = affectation
            ? `${canton.properties.name} · ${affectationLabel(affectation.type)} · nivel ${ALERT_LABEL[affectation.level]}`
            : `${canton.properties.name} · ${copy[lvl].alertLabel[states[code] ?? 'none']}`
        }
        instance.getCanvas().style.cursor = text ? 'pointer' : ''
        if (text) popup.setLngLat(event.lngLat).setText(text).addTo(instance)
        else popup.remove()
      })
      instance.on('mouseout', () => popup.remove())
      const camera = instance.cameraForBounds(VIEW_BOUNDS)
      if (camera?.center && camera.zoom !== undefined) instance.jumpTo({ center: camera.center, zoom: camera.zoom })
      lockView(instance)
      labels.forEach(label => label.addTo(instance))
      setReady(true)
    })
    // El panel lateral se colapsa y cambia el ancho del contenedor: el mapa debe redibujarse y recalcular su zoom mínimo.
    const observer = new ResizeObserver(() => { instance.resize(); if (instance.loaded()) lockView(instance) })
    observer.observe(container.current)
    return () => { observer.disconnect(); popup.remove(); labels.forEach(label => label.remove()); instance.remove(); map.current = null }
  }, [])

  useEffect(() => {
    if (ready) (map.current?.getSource('cantons') as GeoJSONSource).setData(boundaries ?? empty)
  }, [ready, boundaries])

  useEffect(() => {
    const instance = map.current
    if (!ready || !instance) return
    ;(instance.getSource('neighbors') as GeoJSONSource).setData(collection(geo?.neighbors))
    ;(instance.getSource('provinces') as GeoJSONSource).setData(collection(geo?.provinces))
    ;(instance.getSource('country') as GeoJSONSource).setData(collection(geo ? [geo.country] : []))
  }, [ready, geo])

  useEffect(() => {
    if (!ready) return
    ;(map.current?.getSource('grid') as GeoJSONSource).setData(grid.lines)
    ;(map.current?.getSource('grid-land') as GeoJSONSource).setData(grid.land)
  }, [ready, grid])

  useEffect(() => {
    const instance = map.current
    if (!ready || !instance) return
    const isGrid = mode === 'grid'
    for (const layer of ['grid-fill', 'grid-line', 'grid-selected']) instance.setLayoutProperty(layer, 'visibility', isGrid ? 'visible' : 'none')
    // Una afectación registrada por las comisiones (semáforo) manda sobre el estado del aviso.
    const colors = new globalThis.Map<string, string>()
    for (const [code, state] of Object.entries(alerts)) if (state !== 'none') colors.set(code, state === 'active' ? NOTICE_ACTIVE : NOTICE_EXPIRED)
    for (const [code, item] of Object.entries(affectations)) colors.set(code, LEVEL_COLOR[item.level])
    const byAlert = ['match', ['get', 'code'], ...[...colors].flatMap(([code, color]) => [code, color]), LAND] as unknown as ExpressionSpecification
    instance.setPaintProperty('cantons', 'fill-color', isGrid || colors.size === 0 ? LAND : byAlert)
    instance.setFilter('canton-selected', ['==', ['get', 'code'], selected])
    instance.setFilter('grid-selected', ['==', ['get', 'id'], selectedCell])
    const [low, high] = variable === 'T2M' ? [SKY, AMBER] : [AMBER, SKY]
    instance.setPaintProperty('grid-fill', 'fill-color', ['case', ['==', ['get', 'has'], 1],
      ['interpolate', ['linear'], ['get', 'slope'], -grid.extent, low, 0, '#f8fafc', grid.extent, high], '#e2e8f0'])
    instance.setPaintProperty('grid-fill', 'fill-opacity', ['case', ['==', ['get', 'has'], 1], 0.8, 0.5])
  }, [ready, mode, alerts, affectations, selected, selectedCell, variable, grid])

  useEffect(() => {
    const instance = map.current
    if (!ready || !instance || focus.tick === 0) return
    if (!focus.code) {
      // Salir del cantón: de vuelta a la vista completa del país.
      instance.fitBounds(VIEW_BOUNDS, { padding: 0, duration: 800 })
      return
    }
    const feature = boundaries?.features.find(item => item.properties.code === focus.code)
    const box = feature && bboxOf(feature.geometry)
    if (box) instance.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 90, maxZoom: 10, duration: 700 })
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
        <span>Solo se colorea el territorio nacional.</span>
      </> : <>
        <strong>Afectaciones registradas</strong>
        {(Object.keys(LEVEL_COLOR) as AlertLevel[]).map(item => <div className="legend-row" key={item}>
          <span className="swatch" style={{ background: LEVEL_COLOR[item] }} />Nivel {ALERT_LABEL[item]}
        </div>)}
        <strong>Avisos publicados</strong>
        {(['active', 'expired', 'none'] as const).map(state => <div className="legend-row" key={state}>
          <span className="swatch" style={{ background: state === 'active' ? NOTICE_ACTIVE : state === 'expired' ? NOTICE_EXPIRED : LAND }} />{copy[level].alertLabel[state]}
        </div>)}
      </>}
    </div>}
    <p className="map-caption">{failed ? 'El mapa requiere WebGL. Podés seleccionar un cantón desde el buscador.'
      : boundaries ? `${boundaries.features.length} cantones con polígono propio.` : 'Cargando la capa cantonal…'}</p>
  </>
}
