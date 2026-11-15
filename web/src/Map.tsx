import { useEffect, useRef, useState } from 'react'
import { Map as MapLibreMap, NavigationControl } from 'maplibre-gl'
import type { GeoJSONSource } from 'maplibre-gl'
import type { FeatureCollection, Polygon } from 'geojson'
import type { Boundaries, Region, Snapshot } from './data'
import 'maplibre-gl/dist/maplibre-gl.css'

const empty: FeatureCollection = { type: 'FeatureCollection', features: [] }

export function Map({ boundaries, snapshot, selected, select, explore }: {
  boundaries?: Boundaries; snapshot?: Snapshot; selected: string
  select: (code: string) => void; explore: (region: Region) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)
  const onSelect = useRef(select)
  const onExplore = useRef(explore)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  useEffect(() => { onSelect.current = select }, [select])
  useEffect(() => { onExplore.current = explore }, [explore])

  useEffect(() => {
    if (!container.current) return
    let instance: MapLibreMap
    try {
      instance = new MapLibreMap({
        container: container.current, center: [-84.15, 9.95], zoom: 6.4,
        scrollZoom: false, dragRotate: false, pitchWithRotate: false,
        style: { version: 8, sources: {}, layers: [
          { id: 'water', type: 'background', paint: { 'background-color': '#dcebec' } },
        ] },
      })
    } catch {
      setFailed(true)
      return
    }
    map.current = instance
    instance.addControl(new NavigationControl({ showCompass: false }), 'bottom-right')
    instance.on('load', () => {
      instance.addSource('regions', { type: 'geojson', data: empty })
      instance.addSource('cantons', { type: 'geojson', data: empty })
      instance.addLayer({ id: 'regions', source: 'regions', type: 'fill', paint: { 'fill-color': '#74a69c', 'fill-opacity': 0.35 } })
      instance.addLayer({ id: 'region-line', source: 'regions', type: 'line', paint: { 'line-color': '#54857b', 'line-dasharray': [2, 2] } })
      instance.addLayer({ id: 'cantons', source: 'cantons', type: 'fill', paint: { 'fill-color': '#c4d5bb' } })
      instance.addLayer({ id: 'canton-lines', source: 'cantons', type: 'line', paint: { 'line-color': '#f4f8ef', 'line-width': 1.2 } })
      instance.on('click', 'cantons', event => {
        const code = event.features?.[0]?.properties?.code
        if (code) onSelect.current(String(code))
      })
      instance.on('click', 'regions', event => {
        const region = event.features?.[0]?.properties?.region
        if (region === 'CR_PN' || region === 'CR_CAR') onExplore.current(region)
      })
      for (const layer of ['cantons', 'regions']) {
        instance.on('mouseenter', layer, () => { instance.getCanvas().style.cursor = 'pointer' })
        instance.on('mouseleave', layer, () => { instance.getCanvas().style.cursor = '' })
      }
      instance.fitBounds([[-86.05, 8.0], [-82.5, 11.35]], { padding: 24, duration: 0 })
      setReady(true)
    })
    return () => { instance.remove(); map.current = null }
  }, [])

  useEffect(() => {
    const instance = map.current
    if (!ready || !instance) return
    const cantonSource = instance.getSource('cantons') as GeoJSONSource
    cantonSource.setData(boundaries ?? empty)
    const areas: FeatureCollection<Polygon> = { type: 'FeatureCollection', features: [] }
    if (snapshot && !boundaries) {
      for (const [region, variables] of Object.entries(snapshot.climate)) {
        const [west, south, east, north] = variables.PRECTOTCORR.bbox
        areas.features.push({ type: 'Feature', properties: { region }, geometry: { type: 'Polygon', coordinates: [
          [[west, south], [east, south], [east, north], [west, north], [west, south]],
        ] } })
      }
    }
    const regionSource = instance.getSource('regions') as GeoJSONSource
    regionSource.setData(areas)
  }, [ready, boundaries, snapshot])

  useEffect(() => {
    if (ready) map.current?.setPaintProperty('cantons', 'fill-color', [
      'case', ['==', ['get', 'code'], selected], '#147967', '#c4d5bb',
    ])
  }, [ready, selected])

  return <>
    <div className="map" ref={container} aria-label="Mapa de exploración de Costa Rica" />
    <p className="map-caption">{failed ? 'El mapa requiere WebGL. Podés seleccionar un cantón desde el buscador.' : boundaries
      ? `Seleccioná un cantón en el mapa o en el buscador · ${boundaries.features.length} cantones cargados.`
      : 'Tocá un sector para explorar su clima. Capa cantonal pendiente.'}</p>
  </>
}
