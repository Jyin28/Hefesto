import { t } from './i18n'
import type { LocalRecord } from './data/cantonData'

export const MAX_ROWS = 5000
export const MAX_CHARS = 1_000_000
export const RANGES = { T2M: [-20, 60], PRECTOTCORR: [0, 20000] } as const

export type Parsed = Omit<LocalRecord, 'id' | 'importedAt' | 'source'>
export type ParseResult = { records: Parsed[]; rejected: { row: number; reason: string }[]; total: number; error?: string }

export const normalizeText = (value: string) => value.toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '').trim()
const normalize = normalizeText

const FIELDS: Record<string, string[]> = {
  canton: ['canton', 'cantoncode', 'codigo', 'code'],
  variable: ['variable', 'tipo', 'parametro'],
  date: ['fecha', 'date', 'periodo'],
  value: ['valor', 'value'],
  station: ['estacion', 'station'],
}
const VARIABLES: Record<string, 'T2M' | 'PRECTOTCORR'> = {
  t2m: 'T2M', temperatura: 'T2M', temp: 'T2M', temperature: 'T2M',
  prectotcorr: 'PRECTOTCORR', precipitacion: 'PRECTOTCORR', precip: 'PRECTOTCORR', lluvia: 'PRECTOTCORR', precipitation: 'PRECTOTCORR',
}

/** Divide una línea CSV respetando comillas. */
function splitLine(line: string, delimiter: string) {
  const cells: string[] = []
  let current = '', quoted = false
  for (let index = 0; index < line.length; index++) {
    const char = line[index]
    if (char === '"') { if (quoted && line[index + 1] === '"') { current += '"'; index++ } else quoted = !quoted }
    else if (char === delimiter && !quoted) { cells.push(current); current = '' }
    else current += char
  }
  cells.push(current)
  return cells.map(cell => cell.trim())
}

function toRows(input: string): { rows: Record<string, string>[]; error?: string } {
  const trimmed = input.trim()
  if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
    let data: unknown
    try { data = JSON.parse(trimmed) } catch { return { rows: [], error: t('El JSON no es válido.', 'The JSON is not valid.') } }
    const list = Array.isArray(data) ? data : (data as { records?: unknown })?.records
    if (!Array.isArray(list)) return { rows: [], error: t('El JSON debe ser una lista de registros o un objeto con «records».', 'The JSON must be a list of records or an object with "records".') }
    return { rows: list.map(item => Object.fromEntries(Object.entries((item && typeof item === 'object' ? item : {}) as Record<string, unknown>)
      .map(([key, value]) => [normalize(key), value == null ? '' : String(value)]))) }
  }
  const lines = trimmed.split(/\r?\n/).filter(line => line.trim())
  if (lines.length < 2) return { rows: [], error: t('El CSV necesita una fila de encabezados y al menos un registro.', 'The CSV needs a header row and at least one record.') }
  const delimiter = [';', '\t', ','].find(item => lines[0].includes(item)) ?? ','
  const headers = splitLine(lines[0], delimiter).map(normalize)
  return { rows: lines.slice(1).map(line => Object.fromEntries(splitLine(line, delimiter).map((cell, index) => [headers[index] ?? `col${index}`, cell]))) }
}

const pick = (row: Record<string, string>, field: string) => {
  for (const alias of FIELDS[field]) if (row[alias] != null && row[alias] !== '') return row[alias]
  return ''
}

function validDate(raw: string) {
  const match = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(raw)
  if (!match) return false
  const [year, month, day] = [Number(match[1]), match[2] ? Number(match[2]) : 1, match[3] ? Number(match[3]) : 1]
  if (year < 1900 || year > 2100 || month < 1 || month > 12) return false
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.getUTCMonth() === month - 1 && date.getUTCDate() === day
}

/**
 * Valida un JSON o CSV pegado/subido. `resolveCanton` recibe el nombre o el código y devuelve el código DTA de tres dígitos.
 * Nada se guarda aquí: devuelve los registros aceptados y los rechazados con su motivo.
 */
export function parseLocalData(input: string, resolveCanton: (raw: string) => string | null): ParseResult {
  if (!input.trim()) return { records: [], rejected: [], total: 0, error: t('Pegá o subí un JSON o CSV.', 'Paste or upload a JSON or CSV.') }
  if (input.length > MAX_CHARS) return { records: [], rejected: [], total: 0, error: t('El archivo supera 1 MB. Dividilo en partes.', 'The file exceeds 1 MB. Split it into parts.') }
  const { rows, error } = toRows(input)
  if (error) return { records: [], rejected: [], total: 0, error }
  if (rows.length > MAX_ROWS) return { records: [], rejected: [], total: rows.length, error: t(`Máximo ${MAX_ROWS} registros por carga.`, `Maximum ${MAX_ROWS} records per upload.`) }
  const records: Parsed[] = []
  const rejected: ParseResult['rejected'] = []
  rows.forEach((row, index) => {
    const reject = (reason: string) => rejected.push({ row: index + 1, reason })
    const code = resolveCanton(pick(row, 'canton'))
    if (!code) return reject(t(`cantón «${pick(row, 'canton')}» no reconocido`, `canton "${pick(row, 'canton')}" not recognized`))
    const variable = VARIABLES[normalize(pick(row, 'variable'))]
    if (!variable) return reject(t(`variable «${pick(row, 'variable')}» no reconocida (usá temperatura o precipitación)`, `variable "${pick(row, 'variable')}" not recognized (use temperature or precipitation)`))
    const date = pick(row, 'date')
    if (!validDate(date)) return reject(t(`fecha «${date}» inválida (usá AAAA, AAAA-MM o AAAA-MM-DD)`, `date "${date}" invalid (use YYYY, YYYY-MM or YYYY-MM-DD)`))
    const rawValue = pick(row, 'value').replace(/\s/g, '')
    const value = /^-?\d+([.,]\d+)?$/.test(rawValue) ? Number(rawValue.replace(',', '.')) : NaN
    if (!Number.isFinite(value)) return reject(t(`valor «${pick(row, 'value')}» no es un número`, `value "${pick(row, 'value')}" is not a number`))
    const [low, high] = RANGES[variable]
    if (value < low || value > high) return reject(t(`valor ${value} fuera del rango plausible (${low} a ${high})`, `value ${value} outside the plausible range (${low} to ${high})`))
    records.push({ cantonCode: code, variable, date, value, unit: variable === 'T2M' ? '°C' : 'mm', station: pick(row, 'station').slice(0, 120) })
  })
  return { records, rejected, total: rows.length }
}
