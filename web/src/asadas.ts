import { normalizeText } from './localData'
import type { Operator } from './data'
import type { AsadaReport } from './data/cantonData'
import { locale, t } from './i18n'

/** Reporte más reciente por fecha de medición (si empatan, el último guardado). */
export function latestReports(reports: AsadaReport[]): Map<string, AsadaReport> {
  const latest = new Map<string, AsadaReport>()
  for (const item of reports) {
    const current = latest.get(item.asadaId)
    if (!current || item.measuredAt > current.measuredAt || (item.measuredAt === current.measuredAt && item.createdAt > current.createdAt)) latest.set(item.asadaId, item)
  }
  return latest
}

/** Caudal vigente en L/s: el del último reporte; si no hay, el inicial del Excel de SAGA. */
export const currentFlow = (operator: Operator, latest: Map<string, AsadaReport>) => latest.get(operator.id)?.caudal ?? operator.caudal

export type CantonSummary = { operators: number; reported: number; affected: number; localities: string[] }

/** Resumen por cantón. Una ASADA cuenta como afectada si su último reporte dice que sí. */
export function summarizeCantons(operators: Operator[], latest: Map<string, AsadaReport>): Record<string, CantonSummary> {
  const result: Record<string, CantonSummary> = {}
  for (const operator of operators) {
    const entry = result[operator.cantonCode] ??= { operators: 0, reported: 0, affected: 0, localities: [] }
    entry.operators += 1
    const report = latest.get(operator.id)
    if (!report) continue
    entry.reported += 1
    if (report.ninoAffected) { entry.affected += 1; entry.localities.push(...report.localities) }
  }
  return result
}

export const flowText = (value: number | null) => value == null ? t('sin dato', 'no data') : `${value.toLocaleString(locale(), { maximumFractionDigits: 2 })} L/s`

/** Búsqueda por palabras sueltas, sin tildes ni mayúsculas: «tamarindo cruz» encuentra «Playa Tamarindo de Santa Cruz». */
export function matchesAll(haystack: string, query: string) {
  const text = normalizeText(haystack)
  return normalizeText(query).split(/\s+/).filter(Boolean).every(word => text.includes(word))
}

export const operatorHaystack = (item: Operator) => `${item.name} ${item.id} ${item.type} ${item.district} ${item.canton} ${item.province}`
