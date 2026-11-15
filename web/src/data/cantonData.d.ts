/** Reporte de una ASADA: último caudal medido y si El Niño la afecta. Solo lo envía el administrador de esa ASADA. */
export type AsadaReport = {
  id: string
  /** IDEO del operador en SAGA, por ejemplo «00114-2014». */
  asadaId: string
  cantonCode: string
  /** Caudal histórico medido, en L/s. Actualiza el caudal vigente de la ASADA. */
  caudal: number
  /** Fecha de la medición (AAAA-MM-DD). */
  measuredAt: string
  ninoAffected: boolean
  /** Localidades afectadas dentro de la ASADA (solo si ninoAffected). */
  localities: string[]
  notes: string
  createdAt: string
  createdBy: string
  organization: string
}

export type LocalRecord = {
  id: string
  cantonCode: string
  variable: 'T2M' | 'PRECTOTCORR'
  date: string
  value: number
  unit: string
  station: string
  source: string
  importedAt: string
}

export type CantonData = { reports: AsadaReport[]; records: LocalRecord[] }

export const initialCantonData: CantonData
