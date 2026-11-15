// Precalcula la geometría del mapa: país, provincias, vecinos aproximados y la malla NASA POWER 7×7.
// Uso: npm run geo   (desde web/). Lee public/data/cantones.geojson y escribe public/data/geo.json
// y ../data/web/national_cells.json (celdas con tierra, que consume el pipeline de Python).
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import area from '@turf/area'
import difference from '@turf/difference'
import intersect from '@turf/intersect'
import simplify from '@turf/simplify'
import union from '@turf/union'
import { featureCollection, polygon } from '@turf/helpers'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const cantons = JSON.parse(readFileSync(resolve(root, 'public/data/cantones.geojson'), 'utf8'))
// Versión simplificada (~40 m) solo para país, provincias y celdas; la capa cantonal del mapa sigue completa.
const light = cantons.features.map(f => simplify(f, { tolerance: 0.0004, highQuality: false, mutate: false }))

const LAT0 = 8.5, LON0 = -86.25, LAT_STEP = 0.5, LON_STEP = 0.625, N = 7
const round = n => Math.round(n * 1e5) / 1e5
function walk(c) { return typeof c[0] === 'number' ? c.map(round) : c.map(walk) }

const polys = g => (g.type === 'Polygon' ? [g.coordinates] : g.coordinates)
const ringArea = ring => area(polygon([ring]))

/** Quita huecos diminutos (astillas entre cantones) y fragmentos minúsculos. */
function clean(feature, minHole = 2e6, minPart = 1e6) {
  const parts = polys(feature.geometry)
    .map(rings => [rings[0], ...rings.slice(1).filter(ring => ringArea(ring) > minHole)])
    .filter(rings => ringArea(rings[0]) > minPart)
  return { type: 'Feature', properties: {}, geometry: parts.length === 1 ? { type: 'Polygon', coordinates: parts[0] } : { type: 'MultiPolygon', coordinates: parts } }
}

function unionAll(features) {
  let acc = features[0]
  for (const next of features.slice(1)) acc = union(featureCollection([acc, next])) ?? acc
  return acc
}

// --- Provincias y país ---
const byProvince = new Map()
for (const f of light) {
  const list = byProvince.get(f.properties.province) ?? []
  list.push(f)
  byProvince.set(f.properties.province, list)
}
const provinces = []
for (const [name, list] of byProvince) {
  const merged = clean(unionAll(list))
  merged.properties = { name }
  provinces.push(merged)
  console.log(`provincia ${name}: ${list.length} cantones`)
}
const country = clean(unionAll(provinces))
country.properties = { name: 'Costa Rica' }

// --- Vecinos: contornos aproximados a mano [lon, lat]. Se extienden un poco hacia Costa Rica y
// se les resta el país, de modo que la frontera común calza exacta con los polígonos cantonales.
const NICARAGUA = [
  [-85.72, 11.0], [-85.72, 11.07], [-85.88, 11.25], [-86.1, 11.5], [-86.4, 11.7], [-86.8, 11.95], [-87.4, 12.4],
  [-87.4, 12.9], [-83.5, 12.9], [-83.7, 12.0], [-83.65, 11.5], [-83.68, 10.6],
  [-84.3, 10.5], [-84.9, 10.6], [-85.1, 10.85], [-85.5, 10.9],
]
const PANAMA = [
  [-83.0, 9.62], [-82.57, 9.7], [-82.4, 9.7], [-81.6, 9.5], [-81.6, 8.2], [-82.2, 8.2], [-82.5, 8.3],
  [-82.8, 8.25], [-82.85, 8.2], [-82.88, 8.03], [-83.0, 8.03], [-83.0, 8.5],
]
const neighbor = (name, points) => {
  const shape = polygon([[...points, points[0]]])
  const cut = difference(featureCollection([shape, country]))
  const out = clean(cut ?? shape, 0, 1e6)
  out.properties = { name }
  return out
}
const neighbors = [neighbor('Nicaragua', NICARAGUA), neighbor('Panamá', PANAMA)]

// --- Malla 7×7 ---
const box = (w, s, e, n) => polygon([[[w, s], [e, s], [e, n], [w, n], [w, s]]])
const cells = []
const names = []
for (let i = 0; i < N; i++) {
  for (let j = 0; j < N; j++) {
    const lat = LAT0 + i * LAT_STEP
    const lon = LON0 + j * LON_STEP
    const west = lon - LON_STEP / 2, east = lon + LON_STEP / 2, south = lat - LAT_STEP / 2, north = lat + LAT_STEP / 2
    const cell = box(west, south, east, north)
    const land = intersect(featureCollection([cell, country]))
    const landArea = land ? area(land) : 0
    const id = `POWER:${lat}:${lon}`
    names.push(id)
    cells.push({ id, lat, lon, bbox: [west, south, east, north], landFraction: Math.round((landArea / area(cell)) * 1e4) / 1e4,
      land: land ? { type: land.geometry.type, coordinates: walk(land.geometry.coordinates) } : null, cell })
  }
}

// --- Celda dominante de cada cantón (mayor área de intersección) y cantones que toca cada celda ---
/** Un cantón «pertenece» a una celda si ocupa más del 1 % de la celda o la celda contiene más del 5 % del cantón (descarta astillas). */
const belongs = (shared, cellArea, cantonArea) => shared > 0.01 * cellArea || shared > 0.05 * cantonArea
const cantonCells = {}
const cellCantons = {}
for (const f of cantons.features) {
  const cantonArea = area(f)
  let best = { id: '', value: 0 }
  for (const c of cells) {
    const shared = intersect(featureCollection([f, c.cell]))
    const value = shared ? area(shared) : 0
    if (value > best.value) best = { id: c.id, value }
    if (value > 0 && belongs(value, area(c.cell), cantonArea)) (cellCantons[c.id] ??= []).push({ code: f.properties.code, value })
  }
  cantonCells[f.properties.code] = best.id
}
const sortedCodes = map => Object.fromEntries(Object.entries(map).map(([id, list]) => [id, list.sort((a, b) => b.value - a.value).map(item => item.code)]))

const strip = f => ({ type: 'Feature', properties: f.properties, geometry: { type: f.geometry.type, coordinates: walk(f.geometry.coordinates) } })
const geo = {
  country: strip(country), provinces: provinces.map(strip), neighbors: neighbors.map(strip),
  cells: cells.map(({ cell, ...rest }) => rest), cantonCells, cellCantons: sortedCodes(cellCantons),
}
writeFileSync(resolve(root, 'public/data/geo.json'), JSON.stringify(geo))

// Índice liviano para la página «Predicciones»: cada cantón con su celda NASA POWER (sin cargar las geometrías).
const cantonIndex = cantons.features.map(f => ({ code: f.properties.code, name: f.properties.name, province: f.properties.province ?? '', cell: cantonCells[f.properties.code] ?? '' }))
writeFileSync(resolve(root, 'public/data/cantones-indice.json'), JSON.stringify(cantonIndex))

const national = cells.filter(c => c.landFraction >= 0.01).map(c => ({ lat: c.lat, lon: c.lon, land_fraction: c.landFraction }))
writeFileSync(resolve(root, '../data/web/national_cells.json'), JSON.stringify(national, null, 2) + '\n')

const used = new Set(Object.values(cantonCells))
console.log(`celdas: ${cells.length}, con tierra: ${national.length}, usadas por cantones: ${used.size}`)
console.log(`cantones asignados: ${Object.keys(cantonCells).length}, sin celda: ${Object.values(cantonCells).filter(v => !v).length}`)

// --- Malla ERA5-Land del Copernicus CDS: 0,1° × 0,1°, centros en múltiplos de 0,1° (≈11 km) ---
// La malla cubre TODO el rectángulo navegable del mapa (también mar y países vecinos) para que se vea completa; las celdas
// con menos de 1 % de tierra no llevan datos ni son clicables. Las celdas totalmente interiores no guardan polígono de
// tierra (el cliente usa su caja) para que el archivo no crezca. A Python (`cds_cells.json`) solo van las celdas con tierra.
const CDS_STEP = 0.1, CDS_LAT0 = 8.0, CDS_LAT_N = 38, CDS_LON0 = -86.5, CDS_LON_N = 44
const tenth = n => Math.round(n * 10) / 10
const bboxOfGeometry = geometry => {
  let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity
  const visit = value => {
    if (typeof value[0] === 'number') {
      west = Math.min(west, value[0]); east = Math.max(east, value[0]); south = Math.min(south, value[1]); north = Math.max(north, value[1])
    } else value.forEach(visit)
  }
  visit(geometry.coordinates)
  return [west, south, east, north]
}
const overlaps = (a, b) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1]
const countryBox = bboxOfGeometry(country.geometry)
const cdsCells = []
for (let i = 0; i < CDS_LAT_N; i++) {
  for (let j = 0; j < CDS_LON_N; j++) {
    const lat = tenth(CDS_LAT0 + i * CDS_STEP)
    const lon = tenth(CDS_LON0 + j * CDS_STEP)
    const bbox = [lon - CDS_STEP / 2, lat - CDS_STEP / 2, lon + CDS_STEP / 2, lat + CDS_STEP / 2].map(round)
    const id = `ERA5L:${lat}:${lon}`
    if (!overlaps(bbox, countryBox)) { cdsCells.push({ id, lat, lon, bbox, landFraction: 0, land: null, cell: null }); continue }
    const cell = box(...bbox)
    const land = intersect(featureCollection([cell, country]))
    const landFraction = land ? Math.round((area(land) / area(cell)) * 1e4) / 1e4 : 0
    if (landFraction < 0.01) { cdsCells.push({ id, lat, lon, bbox, landFraction: 0, land: null, cell: null }); continue }
    cdsCells.push({
      id, lat, lon, bbox, landFraction,
      land: landFraction >= 0.999 ? null : { type: land.geometry.type, coordinates: walk(land.geometry.coordinates) }, cell,
    })
  }
}
const cdsLand = cdsCells.filter(c => c.cell)
const cdsCantonCells = {}
const cdsCellCantons = {}
for (const f of cantons.features) {
  const featureBox = bboxOfGeometry(f.geometry)
  const cantonArea = area(f)
  let best = { id: '', value: 0 }
  for (const c of cdsLand) {
    if (!overlaps(featureBox, c.bbox)) continue
    const shared = intersect(featureCollection([f, c.cell]))
    const value = shared ? area(shared) : 0
    if (value > best.value) best = { id: c.id, value }
    if (value > 0 && belongs(value, area(c.cell), cantonArea)) (cdsCellCantons[c.id] ??= []).push({ code: f.properties.code, value })
  }
  cdsCantonCells[f.properties.code] = best.id
}
writeFileSync(resolve(root, 'public/data/geo-cds.json'),
  JSON.stringify({ cells: cdsCells.map(({ cell, ...rest }) => rest), cantonCells: cdsCantonCells, cellCantons: sortedCodes(cdsCellCantons) }))
writeFileSync(resolve(root, '../data/web/cds_cells.json'),
  JSON.stringify(cdsLand.map(c => ({ lat: c.lat, lon: c.lon, land_fraction: c.landFraction })), null, 2) + '\n')
console.log(`celdas CDS: ${cdsCells.length} (con tierra: ${cdsLand.length}), cantones asignados: ${Object.keys(cdsCantonCells).length}, sin celda: ${Object.values(cdsCantonCells).filter(v => !v).length}`)
