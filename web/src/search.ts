import { matchesAll, operatorHaystack } from './asadas'
import type { MapMode } from './copy'
import type { Canton, Operator } from './data'
import { normalizeText } from './localData'

/** Una sugerencia del buscador: un cantón o (solo en el mapa de cuencas) una ASADA. */
export type Entry =
  | { key: string; kind: 'canton'; code: string; name: string; province: string }
  | { key: string; kind: 'asada'; operator: Operator }

/** Las ASADAs solo se buscan en «Datos nacionales»; los otros dos mapas buscan únicamente cantones. */
export const searchesAsadas = (mode: MapMode) => mode === 'cantones'

export const entryName = (entry: Entry) => entry.kind === 'canton' ? entry.name : entry.operator.name
export const entrySub = (entry: Entry) => entry.kind === 'canton'
  ? `Cantón · ${entry.province}`
  : `${entry.operator.type} · ${entry.operator.district}, ${entry.operator.canton}`

/** 0 = el nombre empieza con lo escrito, 1 = una palabra del nombre empieza con eso, 2 = lo contiene (o coincide por otro campo). */
function rank(name: string, query: string) {
  const text = normalizeText(name)
  const wanted = normalizeText(query)
  if (text.startsWith(wanted)) return 0
  if (text.split(/[\s\-(),.]+/).some(word => word.startsWith(wanted))) return 1
  return text.includes(wanted) ? 2 : 3
}

const collator = new Intl.Collator('es-CR')

/**
 * Sugerencias para lo escrito, mejores primero. Cantones: por nombre o código. ASADAs (solo si `withAsadas`): por nombre,
 * distrito, cantón o provincia. En el mapa de cuencas se mezclan los dos tipos, pero un cantón que empieza igual va antes.
 */
export function searchEntries(query: string, choices: Map<string, Canton>, asadas: Operator[], withAsadas: boolean, limit = 8): Entry[] {
  if (query.trim() === '') return []
  const scored: { entry: Entry; score: number; name: string }[] = []
  for (const [code, info] of choices) {
    if (!matchesAll(`${code} ${info.name} ${info.province}`, query)) continue
    scored.push({ entry: { key: `c${code}`, kind: 'canton', code, name: info.name, province: info.province }, score: rank(info.name, query) * 2, name: info.name })
  }
  if (withAsadas) {
    for (const operator of asadas) {
      if (!matchesAll(operatorHaystack(operator), query)) continue
      // Un cantón empata a un operador del mismo rango y va primero (score par frente a impar).
      scored.push({ entry: { key: `a${operator.id}`, kind: 'asada', operator }, score: rank(operator.name, query) * 2 + 1, name: operator.name })
    }
  }
  return scored.sort((a, b) => a.score - b.score || collator.compare(a.name, b.name)).slice(0, limit).map(item => item.entry)
}

/**
 * Parte `text` en tramos para resaltar en negrita lo que coincide con `query` (sin tildes ni mayúsculas).
 * Cada palabra de la búsqueda se marca donde aparece; el resto del texto queda tal cual, con sus tildes.
 */
export function highlight(text: string, query: string): { text: string; bold: boolean }[] {
  const words = normalizeText(query).split(/\s+/).filter(Boolean)
  if (!words.length) return [{ text, bold: false }]
  // Se normaliza carácter por carácter para que los índices del texto sin tildes sean los del texto original.
  const chars = [...text]
  const plain = chars.map(char => normalizeText(char) || char.toLowerCase())
  const offsets: number[] = []
  let flat = ''
  plain.forEach((piece, index) => { for (let i = 0; i < piece.length; i++) offsets.push(index); flat += piece })
  const marked = new Array<boolean>(chars.length).fill(false)
  for (const word of words) {
    let from = flat.indexOf(word)
    while (from !== -1) {
      for (let i = from; i < from + word.length; i++) marked[offsets[i]] = true
      from = flat.indexOf(word, from + word.length)
    }
  }
  const parts: { text: string; bold: boolean }[] = []
  chars.forEach((char, index) => {
    const last = parts[parts.length - 1]
    if (last && last.bold === marked[index]) last.text += char
    else parts.push({ text: char, bold: marked[index] })
  })
  return parts
}

/**
 * Texto gris que se muestra dentro del campo: lo que le falta a la mejor sugerencia para completar lo escrito.
 * Solo existe si el nombre empieza exactamente con lo escrito (sin contar tildes ni mayúsculas).
 */
export function inlineCompletion(query: string, entry: Entry | undefined): string {
  if (!entry || query.trim() === '') return ''
  // Sin recortar espacios: «San » debe completar «José», no desalinearse.
  const fold = (value: string) => value.toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '')
  const name = entryName(entry)
  const typed = fold(query)
  if (!fold(name).startsWith(typed) || fold(name) === typed) return ''
  return [...name].slice([...query].length).join('')
}

// --- Búsquedas recientes (solo en este navegador) ---
const RECENT_KEY = 'hefesto.recent.v1'
const MAX_RECENT = 5
export type Recent = { kind: 'canton'; code: string } | { kind: 'asada'; id: string }

export function loadRecent(): Recent[] {
  try {
    const raw = JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]') as unknown
    if (!Array.isArray(raw)) return []
    return raw.flatMap((item): Recent[] => {
      const value = item as Partial<Record<string, unknown>> | null
      if (value?.kind === 'canton' && typeof value.code === 'string' && /^\d{3}$/.test(value.code)) return [{ kind: 'canton', code: value.code }]
      if (value?.kind === 'asada' && typeof value.id === 'string' && /^\d{5}-\d{4}$/.test(value.id)) return [{ kind: 'asada', id: value.id }]
      return []
    })
  } catch { return [] }
}

export function rememberSearch(entry: Entry): void {
  const item: Recent = entry.kind === 'canton' ? { kind: 'canton', code: entry.code } : { kind: 'asada', id: entry.operator.id }
  const same = (other: Recent) => other.kind === item.kind && (other.kind === 'canton' ? other.code === (item as { code: string }).code : other.id === (item as { id: string }).id)
  try { localStorage.setItem(RECENT_KEY, JSON.stringify([item, ...loadRecent().filter(other => !same(other))].slice(0, MAX_RECENT * 3))) } catch { /* sin almacenamiento: se omite */ }
}

/** Recientes que aplican al mapa activo: en los mapas de malla no aparecen ASADAs. */
export function recentEntries(recent: Recent[], choices: Map<string, Canton>, asadas: Operator[], withAsadas: boolean): Entry[] {
  const entries: Entry[] = []
  for (const item of recent) {
    if (item.kind === 'canton') {
      const info = choices.get(item.code)
      if (info) entries.push({ key: `c${item.code}`, kind: 'canton', code: item.code, name: info.name, province: info.province })
    } else if (withAsadas) {
      const operator = asadas.find(candidate => candidate.id === item.id)
      if (operator) entries.push({ key: `a${operator.id}`, kind: 'asada', operator })
    }
  }
  return entries.slice(0, MAX_RECENT)
}
