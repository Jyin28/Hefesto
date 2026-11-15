// Base inicial de datos locales. Lo que las ASADAs reportan o importan en el navegador se guarda en
// localStorage encima de esta base (ver ../store.ts). Empieza vacía a propósito: no se incluyen reportes
// ni registros de ejemplo para no mostrar datos inventados como reales.

export const initialCantonData = {
  // { id, asadaId, cantonCode, caudal (L/s), measuredAt (AAAA-MM-DD), ninoAffected, localities[], notes, createdAt, createdBy, organization }
  reports: [],
  // { id, cantonCode, variable: 'T2M' | 'PRECTOTCORR', date, value, unit, station, source, importedAt }
  records: [],
}
