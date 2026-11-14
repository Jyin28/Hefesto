import { useSyncExternalStore } from 'react'
import { AFFECTATION_TYPES, WARNING_LEVELS, initialCantonData } from './data/cantonData'
import type { Affectation, CantonData, LocalRecord } from './data/cantonData'

const KEY = 'hefesto.cantonData.v1'
export const MAX_NOTES = 500

const typeIds = new Set<string>(AFFECTATION_TYPES.map(item => item.id))
const levels = new Set<string>(WARNING_LEVELS)
const text = (value: unknown, max: number) => typeof value === 'string' ? value.slice(0, max) : ''

/** Lo guardado en localStorage lo puede editar cualquiera: se descarta todo lo que no tenga la forma esperada. */
function sanitize(raw: unknown): CantonData {
  const source = (raw && typeof raw === 'object' ? raw : {}) as Partial<Record<keyof CantonData, unknown>>
  const affectations = (Array.isArray(source.affectations) ? source.affectations : []).flatMap((item): Affectation[] => {
    const value = item as Partial<Affectation> | null
    if (!value || !typeIds.has(String(value.type)) || !levels.has(String(value.level)) || !/^\d{3}$/.test(String(value.cantonCode))) return []
    return [{
      id: text(value.id, 64) || makeId(), cantonCode: String(value.cantonCode), type: value.type!, level: value.level!,
      notes: text(value.notes, MAX_NOTES), createdAt: text(value.createdAt, 40), createdBy: text(value.createdBy, 120),
      organization: text(value.organization, 120),
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
  return { affectations, records }
}

function makeId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function load(): CantonData {
  try {
    const stored = localStorage.getItem(KEY)
    // Sin nada guardado se parte de la base inicial de cantonData.js.
    return sanitize(stored ? JSON.parse(stored) : initialCantonData)
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

export const affectationLabel = (id: string) => AFFECTATION_TYPES.find(item => item.id === id)?.label ?? id

export const getCantonData = () => state
export function subscribeCantonData(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function useCantonData(): CantonData {
  return useSyncExternalStore(subscribeCantonData, getCantonData)
}

export function addAffectation(input: Omit<Affectation, 'id' | 'createdAt'>): boolean {
  const entry: Affectation = { ...input, notes: input.notes.slice(0, MAX_NOTES), id: makeId(), createdAt: new Date().toISOString() }
  return commit({ ...state, affectations: [entry, ...state.affectations] })
}

export const removeAffectation = (id: string) => commit({ ...state, affectations: state.affectations.filter(item => item.id !== id) })

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
export const resetCantonData = () => commit(sanitize(initialCantonData))
