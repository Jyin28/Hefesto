import { useSyncExternalStore } from 'react'
import { initialCantonData } from './data/cantonData'
import type { AsadaReport, CantonData, LocalRecord } from './data/cantonData'

const KEY = 'hefesto.cantonData.v2'
const LEGACY_KEY = 'hefesto.cantonData.v1'
export const MAX_NOTES = 500
export const MAX_FLOW = 10000
export const MAX_LOCALITIES = 30
export const MAX_LOCALITY = 80

const text = (value: unknown, max: number) => typeof value === 'string' ? value.slice(0, max) : ''
const validDate = (value: unknown) => {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const date = new Date(`${value}T00:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
}
/** Hoy en Costa Rica (AAAA-MM-DD): una medición no puede ser futura. */
export const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Costa_Rica' }).format(new Date())

/** Lo guardado en localStorage lo puede editar cualquiera: se descarta todo lo que no tenga la forma esperada. */
function sanitize(raw: unknown): CantonData {
  const source = (raw && typeof raw === 'object' ? raw : {}) as Partial<Record<keyof CantonData, unknown>>
  const reports = (Array.isArray(source.reports) ? source.reports : []).flatMap((item): AsadaReport[] => {
    const value = item as Partial<AsadaReport> | null
    if (!value || !/^\d{5}-\d{4}$/.test(String(value.asadaId)) || !/^\d{3}$/.test(String(value.cantonCode))
      || typeof value.caudal !== 'number' || !Number.isFinite(value.caudal) || value.caudal <= 0 || value.caudal > MAX_FLOW
      || !validDate(value.measuredAt) || typeof value.ninoAffected !== 'boolean') return []
    const localities = value.ninoAffected && Array.isArray(value.localities)
      ? [...new Set(value.localities.map(item => text(item, MAX_LOCALITY).trim()).filter(Boolean))].slice(0, MAX_LOCALITIES) : []
    // Si hay afectación, las localidades son obligatorias: un registro sin ellas no cumple el formulario.
    if (value.ninoAffected && !localities.length) return []
    return [{
      id: text(value.id, 64) || makeId(), asadaId: String(value.asadaId), cantonCode: String(value.cantonCode), caudal: value.caudal,
      measuredAt: String(value.measuredAt), ninoAffected: value.ninoAffected, localities, notes: text(value.notes, MAX_NOTES),
      createdAt: text(value.createdAt, 40), createdBy: text(value.createdBy, 120), organization: text(value.organization, 120),
    }]
  })
  const records = (Array.isArray(source.records) ? source.records : []).flatMap((item): LocalRecord[] => {
    const value = item as Partial<LocalRecord> | null
    if (!value || (value.variable !== 'T2M' && value.variable !== 'PRECTOTCORR') || !/^\d{3}$/.test(String(value.cantonCode))
      || typeof value.value !== 'number' || !Number.isFinite(value.value) || !/^\d{4}(-\d{2}(-\d{2})?)?$/.test(String(value.date))) return []
    return [{
      id: text(value.id, 64) || makeId(), cantonCode: String(value.cantonCode), variable: value.variable, date: String(value.date),
      value: value.value, unit: text(value.unit, 20), station: text(value.station, 120), source: text(value.source, 120),
      importedAt: text(value.importedAt, 40),
    }]
  })
  return { reports, records }
}

function makeId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function load(): CantonData {
  try {
    const stored = localStorage.getItem(KEY)
    if (stored) return sanitize(JSON.parse(stored))
    // Primera vez con el modelo por ASADA: se conservan los registros locales del modelo anterior; las afectaciones por cantón se descartan.
    const legacy = localStorage.getItem(LEGACY_KEY)
    return sanitize(legacy ? { records: (JSON.parse(legacy) as { records?: unknown }).records } : initialCantonData)
  } catch { return sanitize(initialCantonData) }
}

let state = load()
const listeners = new Set<() => void>()
const notify = () => listeners.forEach(listener => listener())

/** Actualiza en memoria al instante y devuelve false si el navegador no pudo guardarlo. */
function commit(next: CantonData): boolean {
  state = next
  notify()
  try { localStorage.setItem(KEY, JSON.stringify(next)); return true } catch { return false }
}

if (typeof window !== 'undefined') {
  // Otra pestaña del mismo navegador cambió los datos: la vista pública se actualiza sin recargar.
  window.addEventListener('storage', event => { if (event.key === KEY || event.key === null) { state = load(); notify() } })
}

export const getCantonData = () => state
export function subscribeCantonData(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function useCantonData(): CantonData {
  return useSyncExternalStore(subscribeCantonData, getCantonData)
}

export type SaveResult = 'saved' | 'memory' | 'forbidden' | 'invalid'

/**
 * Guarda un reporte. `allowedAsadaId` es la ASADA de la sesión: un administrador solo puede reportar sobre la suya.
 * El caudal vigente de la ASADA pasa a ser el del reporte más reciente por fecha de medición.
 */
export function addAsadaReport(input: Omit<AsadaReport, 'id' | 'createdAt'>, allowedAsadaId: string): SaveResult {
  if (input.asadaId !== allowedAsadaId) return 'forbidden'
  const entry: AsadaReport = { ...input, notes: input.notes.slice(0, MAX_NOTES), id: makeId(), createdAt: new Date().toISOString() }
  if (!validDate(entry.measuredAt) || entry.measuredAt > today()) return 'invalid'
  const [clean] = sanitize({ reports: [entry] }).reports
  if (!clean) return 'invalid'
  return commit({ ...state, reports: [clean, ...state.reports] }) ? 'saved' : 'memory'
}

/** Solo se puede eliminar un reporte de la propia ASADA. */
export function removeAsadaReport(id: string, allowedAsadaId: string): boolean {
  if (!state.reports.some(item => item.id === id && item.asadaId === allowedAsadaId)) return false
  commit({ ...state, reports: state.reports.filter(item => item.id !== id) })
  return true
}

/** Un registro con el mismo cantón, variable, fecha y estación reemplaza al anterior. */
export function addRecords(input: Omit<LocalRecord, 'id' | 'importedAt'>[]): boolean {
  const keyOf = (item: { cantonCode: string; variable: string; date: string; station: string }) =>
    `${item.cantonCode}|${item.variable}|${item.date}|${item.station}`
  const merged = new Map(state.records.map(item => [keyOf(item), item]))
  const importedAt = new Date().toISOString()
  for (const item of input) merged.set(keyOf(item), { ...item, id: makeId(), importedAt })
  return commit({ ...state, records: [...merged.values()] })
}

export const removeRecords = (ids: Set<string>) => commit({ ...state, records: state.records.filter(item => !ids.has(item.id)) })

/** Borra los registros locales y solo los reportes de la ASADA indicada; los de otras ASADAs no se tocan. */
export const resetCantonData = (asadaId: string) =>
  commit({ reports: state.reports.filter(item => item.asadaId !== asadaId), records: [] })
