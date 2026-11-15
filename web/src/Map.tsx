import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Map as MapLibreMap, Marker, NavigationControl, Popup } from 'maplibre-gl'
import type { ExpressionSpecification, GeoJSONSource, LngLatBoundsLike } from 'maplibre-gl'
import type { Feature, FeatureCollection, Geometry, Position } from 'geojson'
import { fmt } from './analysis'
import { copy } from './copy'
import type { Alert, Level, MapMode } from './copy'
import type { Boundaries, Geo, LayerVar, Region, Snapshot, Waterways } from './data'
import { buildLayerGrid, colorExpression, describe, legendGradient, legendTitle, META } from './layers'
import type { LayerMode } from './layers'
import 'maplibre-gl/dist/maplibre-gl.css'

const empty: FeatureCollection = { type: 'FeatureCollection', features: [] }
// Límites del mapa: la malla NASA POWER 7×7 (8,25–11,75 °N · 86,5625–82,1875 °O) más 0,25° al sur para que
// quepa la punta de Burica. Fuera de este rectángulo no se puede navegar.
const VIEW_BOUNDS: LngLatBoundsLike = [[-86.5625, 8.0], [-82.1875, 11.75]]
const SEA = '#cfeaf6'
const LAND = '#f1f6fa'
const NEIGHBOR = '#e4dfd5'
const NOTICE_ACTIVE = '#38BDF8'
const NOTICE_EXPIRED = '#bfdbfe'
const AFFECTED = '#F97316'
const REPORTED = '#10B981'
const RIVER = '#2563eb'
const WATER_FILL = '#7dd3fc'
const WATER_LAYERS = ['water-bodies', 'rivers', 'streams']
const WATER_NAMES = { river: 'Río', canal: 'Canal', stream: 'Quebrada', water: 'Cuerpo de agua' } as const

/** Resumen de los operadores de agua de un cantón, según el catálogo SAGA y los reportes de las ASADAs. */
export type CantonStatus = { operators: number; reported: number; affected: number }
/** Foco de cámara: un cantón por su código, una caja (provincia) o, sin ninguno de los dos, todo el país. */
export type Focus = { code: string; bbox?: [number, number, number, number]; tick: number }

export function bboxOf(geometry: Geometry): [number, number, number, number] | undefined {
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

/** Tarjeta del hover: lugar en negrita y una línea de explicación. Solo textContent, nunca HTML. */
function hoverCard(title: string, small?: string, detail?: string) {
  const card = document.createElement('div')
  card.className = 'hover-card'
  const head = document.createElement('strong')
  head.textContent = title
  card.append(head)
  if (small) { const element = document.createElement('small'); element.textContent = ` (${small})`; card.append(element) }
  if (detail) { const line = document.createElement('p'); line.textContent = detail; card.append(line) }
  return card
}

const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`

export function Map({ boundaries, geo, snapshot, waterways, mode, variable, layerMode, range, year, level, selected, selectedCell, alerts,
  cantonStatus, focus, controls, select, selectCell }: {
  boundaries?: Boundaries; geo?: Geo; snapshot?: Snapshot; waterways?: Waterways; mode: MapMode
  variable: LayerVar; layerMode: LayerMode; range: [number, number]; year: number; level: Level
  selected: string; selectedCell: string; alerts: Record<string, Alert>; cantonStatus: Record<string, CantonStatus>
  focus: Focus; controls?: ReactNode
  select: (code: string) => void; selectCell: (region: Region, id: string) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  const grid = useMemo(() => buildLayerGrid(snapshot?.layers, variable, geo, layerMode, range, year),
    [snapshot, variable, geo, layerMode, range, year])
  const latest = useRef({ select, selectCell, mode, level, alerts, cantonStatus, variable, layerMode, grid })
  latest.current = { select, selectCell, mode, level, alerts, cantonStatus, variable, layerMode, grid }

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
    const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 8, maxWidth: '280px' })
    const labels = [
      new Marker({ element: labelElement('Nicaragua'), anchor: 'center' }).setLngLat([-84.3, 11.45]),
      new Marker({ element: labelElement('Panamá'), anchor: 'center' }).setLngLat([-82.75, 8.8]),
    ]
    instance.on('load', () => {
      for (const name of ['neighbors', 'cantons', 'grid-land', 'grid', 'waterways', 'provinces', 'country']) instance.addSource(name, { type: 'geojson', data: empty })
      // De abajo hacia arriba: vecinos, relleno cantonal, relleno de la malla, cuadrícula (tenue), hidrografía, cantones, provincias y país.
      instance.addLayer({ id: 'neighbors', source: 'neighbors', type: 'fill', paint: { 'fill-color': NEIGHBOR, 'fill-opacity': 1 } })
      instance.addLayer({ id: 'neighbor-lines', source: 'neighbors', type: 'line', paint: { 'line-color': '#b9b2a4', 'line-width': 1 } })
      instance.addLayer({ id: 'cantons', source: 'cantons', type: 'fill', paint: { 'fill-color': LAND, 'fill-opacity': 1 } })
      instance.addLayer({ id: 'grid-fill', source: 'grid-land', type: 'fill', paint: { 'fill-color': '#ffffff', 'fill-opacity': 0 } })
      instance.addLayer({ id: 'grid-line', source: 'grid', type: 'line', paint: { 'line-color': '#0c4a6e', 'line-opacity': 0.22, 'line-width': 0.6 } })
      instance.addLayer({ id: 'water-bodies', source: 'waterways', type: 'fill', filter: ['==', ['get', 'kind'], 'water'],
        layout: { visibility: 'none' }, paint: { 'fill-color': WATER_FILL, 'fill-opacity': 0.85, 'fill-outline-color': RIVER } })
      instance.addLayer({ id: 'streams', source: 'waterways', type: 'line', filter: ['==', ['get', 'kind'], 'stream'], minzoom: 8.5,
        layout: { visibility: 'none', 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': RIVER, 'line-opacity': 0.55, 'line-width': 0.7 } })
      instance.addLayer({ id: 'rivers', source: 'waterways', type: 'line', filter: ['in', ['get', 'kind'], ['literal', ['river', 'canal']]],
        layout: { visibility: 'none', 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': RIVER, 'line-opacity': 0.85, 'line-width': ['interpolate', ['linear'], ['zoom'], 6, 0.5, 9, 1.4, 11, 2.4] } })
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
        const { mode: current, level: lvl, alerts: states, cantonStatus: status, variable: variableNow, layerMode: modeNow, grid: now } = latest.current
        const canton = instance.queryRenderedFeatures(event.point, { layers: ['cantons'] })[0]
        const place = canton?.properties ? `Cantón: ${canton.properties.name}` : 'Costa Rica'
        const province = canton?.properties?.province ? String(canton.properties.province) : undefined
        let content: HTMLElement | undefined
        if (current === 'grid') {
          const cell = instance.queryRenderedFeatures(event.point, { layers: ['grid-fill'] })[0]
          if (cell?.properties?.has === 1) {
            content = hoverCard(place, province, describe(variableNow, modeNow, Number(cell.properties.v), Number(cell.properties.nat), now))
          } else if (cell || canton) {
            content = hoverCard(place, province, modeNow === 'slope'
              ? `${META[variableNow].slopeTitle}: sin datos suficientes en este período`
              : `${META[variableNow].valueTitle(now.year)}: sin dato`)
          }
        } else {
          const box: [[number, number], [number, number]] = [[event.point.x - 4, event.point.y - 4], [event.point.x + 4, event.point.y + 4]]
          const water = instance.queryRenderedFeatures(box, { layers: WATER_LAYERS })[0]
          if (water?.properties) {
            const kind = String(water.properties.kind) as keyof typeof WATER_NAMES
            const label = water.properties.name ? String(water.properties.name) : `${WATER_NAMES[kind] ?? 'Curso de agua'} sin nombre`
            content = hoverCard(label, undefined, canton?.properties ? `En el cantón de ${canton.properties.name}` : undefined)
          } else if (canton?.properties) {
            const code = String(canton.properties.code)
            const info = status[code]
            const parts: string[] = []
            if (info?.operators) {
              parts.push(plural(info.operators, 'operador de agua', 'operadores de agua'))
              if (info.affected) parts.push(`${info.affected} ${info.affected === 1 ? 'reporta' : 'reportan'} afectación por El Niño`)
              else if (info.reported) parts.push(`${info.reported} ${info.reported === 1 ? 'reportó' : 'reportaron'} sin afectación`)
            } else parts.push('Sin operadores de agua cargados')
            if ((states[code] ?? 'none') !== 'none') parts.push(copy[lvl].alertLabel[states[code]])
            content = hoverCard(place, province, parts.join(' · '))
          }
        }
        instance.getCanvas().style.cursor = content ? 'pointer' : ''
        if (content) popup.setLngLat(event.lngLat).setDOMContent(content).addTo(instance)
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
    if (ready) (map.current?.getSource('waterways') as GeoJSONSource).setData(waterways ?? empty)
  }, [ready, waterways])

  useEffect(() => {
    const instance = map.current
    if (!ready || !instance) return
    ;(instance.getSource('neighbors') as GeoJSONSource).setData(collection(geo?.neighbors))
    ;(instance.getSource('provinces') as GeoJSONSource).setData(collection(geo?.provinces))
    ;(instance.getSource('country') as GeoJSONSource).setData(collection(geo ? [geo.country] : []))
  }, [ready, geo])

  // Cada cambio del switch, del rango o del año repinta las 24 celdas al instante (no hay red de por medio).
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
    for (const layer of WATER_LAYERS) instance.setLayoutProperty(layer, 'visibility', isGrid ? 'none' : 'visible')
    // Lo que reportan las ASADAs manda sobre el estado del aviso: naranja si alguna está afectada, verde si todas reportaron sin afectación.
    const colors = new globalThis.Map<string, string>()
    for (const [code, state] of Object.entries(alerts)) if (state !== 'none') colors.set(code, state === 'active' ? NOTICE_ACTIVE : NOTICE_EXPIRED)
    for (const [code, info] of Object.entries(cantonStatus)) {
      if (info.affected > 0) colors.set(code, AFFECTED)
      else if (info.reported > 0) colors.set(code, REPORTED)
    }
    const byStatus = ['match', ['get', 'code'], ...[...colors].flatMap(([code, color]) => [code, color]), LAND] as unknown as ExpressionSpecification
    instance.setPaintProperty('cantons', 'fill-color', isGrid || colors.size === 0 ? LAND : byStatus)
    instance.setFilter('canton-selected', ['==', ['get', 'code'], selected])
    instance.setFilter('grid-selected', ['==', ['get', 'id'], selectedCell])
    instance.setPaintProperty('grid-fill', 'fill-color', colorExpression(variable, layerMode, grid))
    instance.setPaintProperty('grid-fill', 'fill-opacity', ['case', ['==', ['get', 'has'], 1], 0.85, 0.5])
  }, [ready, mode, alerts, cantonStatus, selected, selectedCell, variable, layerMode, grid])

  useEffect(() => {
    const instance = map.current
    if (!ready || !instance || focus.tick === 0) return
    if (focus.bbox) {
      const [west, south, east, north] = focus.bbox
      instance.fitBounds([[west, south], [east, north]], { padding: 50, maxZoom: 9, duration: 700 })
      return
    }
    if (!focus.code) {
      // Salir del cantón: de vuelta a la vista completa del país.
      instance.fitBounds(VIEW_BOUNDS, { padding: 0, duration: 800 })
      return
    }
    const feature = boundaries?.features.find(item => item.properties.code === focus.code)
    const box = feature && bboxOf(feature.geometry)
    if (box) instance.fitBounds([[box[0], box[1]], [box[2], box[3]]], { padding: 90, maxZoom: 10, duration: 700 })
  }, [ready, focus, boundaries])

  const meta = META[variable]
  const lo = layerMode === 'slope' ? -grid.extent : grid.domain[0]
  const hi = layerMode === 'slope' ? grid.extent : grid.domain[1]
  const digits = layerMode === 'slope' ? meta.slopeDigits : meta.digits
  const legendNumber = (value: number) => (layerMode === 'slope' && value > 0 ? '+' : '') + fmt(value, digits)
  return <>
    <div className="map" ref={container} aria-label="Mapa de Costa Rica" />
    {!failed && <div className="map-hud">
      {mode === 'grid' && controls}
      <div className="legend glass" aria-label="Leyenda del mapa">
        {mode === 'grid' ? <>
          <strong>{legendTitle(variable, layerMode, grid)}</strong>
          <div className="legend-bar" style={{ background: legendGradient(variable, layerMode) }} />
          <div className="legend-scale">
            <span>{legendNumber(lo)}</span>{layerMode === 'slope' && <span>0</span>}<span>{legendNumber(hi)}</span>
          </div>
          {grid.withData < grid.total && <span>Gris: sin datos suficientes.</span>}
          <span>Solo se colorea el territorio nacional.</span>
        </> : <>
          <strong>Operadores de agua y El Niño</strong>
          <div className="legend-row"><span className="swatch" style={{ background: AFFECTED }} />Hay operadores afectados</div>
          <div className="legend-row"><span className="swatch" style={{ background: REPORTED }} />Reportaron sin afectación</div>
          <strong>Avisos publicados</strong>
          {(['active', 'expired', 'none'] as const).map(state => <div className="legend-row" key={state}>
            <span className="swatch" style={{ background: state === 'active' ? NOTICE_ACTIVE : state === 'expired' ? NOTICE_EXPIRED : LAND }} />{copy[level].alertLabel[state]}
          </div>)}
          <strong>Agua</strong>
          <div className="legend-row"><span className="swatch line" style={{ background: RIVER }} />Ríos y quebradas</div>
          <div className="legend-row"><span className="swatch" style={{ background: WATER_FILL }} />Lagos y embalses</div>
        </>}
      </div>
    </div>}
    <p className="map-caption">{failed ? 'El mapa requiere WebGL. Podés seleccionar un cantón desde el buscador.'
      : mode === 'cantones' ? `${boundaries ? `${boundaries.features.length} cantones con polígono propio. ` : 'Cargando la capa cantonal… '}Ríos y quebradas: © colaboradores de OpenStreetMap (ODbL).`
        : boundaries ? `${boundaries.features.length} cantones con polígono propio.` : 'Cargando la capa cantonal…'}</p>
  </>
}
