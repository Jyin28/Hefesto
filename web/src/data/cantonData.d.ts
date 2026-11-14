export type AffectationType = 'sequia' | 'inundacion' | 'deslizamiento' | 'cuenca-asada'
export type WarningLevel = 'verde' | 'amarillo' | 'naranja' | 'rojo'

export type Affectation = {
  id: string
  cantonCode: string
  type: AffectationType
  level: WarningLevel
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

export type CantonData = { affectations: Affectation[]; records: LocalRecord[] }

export const AFFECTATION_TYPES: { id: AffectationType; label: string }[]
export const WARNING_LEVELS: WarningLevel[]
export const initialCantonData: CantonData
