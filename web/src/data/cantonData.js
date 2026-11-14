// Base inicial de datos cantonales. Lo que las comisiones registran o importan en el navegador
// se guarda en localStorage encima de esta base (ver ../store.ts). Empieza vacía a propósito:
// no se incluyen afectaciones ni registros de ejemplo para no mostrar datos inventados como reales.

export const AFFECTATION_TYPES = [
  { id: 'sequia', label: 'Sequía / Déficit hídrico' },
  { id: 'inundacion', label: 'Inundación' },
  { id: 'deslizamiento', label: 'Deslizamiento' },
  { id: 'cuenca-asada', label: 'Afectación en cuenca/ASADA' },
]

export const WARNING_LEVELS = ['verde', 'amarillo', 'naranja', 'rojo']

export const initialCantonData = {
  // { id, cantonCode, type, level, notes, createdAt, createdBy, organization }
  affectations: [],
  // { id, cantonCode, variable: 'T2M' | 'PRECTOTCORR', date, value, unit, station, source, importedAt }
  records: [],
}
