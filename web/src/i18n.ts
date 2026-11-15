import { useSyncExternalStore } from 'react'

/**
 * Idioma del sitio. El español es el idioma por defecto; el inglés se elige con el selector ES | EN.
 *
 * `t(es, en)` devuelve el texto del idioma activo y se puede llamar desde cualquier lugar (componentes, funciones que arman
 * frases, etc.). Como el estado vive en este módulo, `Root` (en `main.tsx`) se suscribe con `useLang()` y al cambiar el
 * idioma se vuelve a dibujar todo el árbol sin perder el estado de la pantalla (cantón elegido, panel abierto...).
 *
 * Regla para quien agregue textos: nunca guardar el resultado de `t()` en una constante de módulo ni en un `useMemo`
 * sin `lang` en sus dependencias; llamarlo al dibujar (o convertir la constante en una función).
 *
 * Los nombres propios (cantones, provincias, ASADAs, NASA POWER, Copernicus, «El Niño», «AguaAlerta»...) no se traducen.
 */
export type Lang = 'es' | 'en'

const STORAGE_KEY = 'nexoazul.lang'
const isLang = (value: unknown): value is Lang => value === 'es' || value === 'en'

function initialLang(): Lang {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get('lang')
    if (isLang(fromUrl)) return fromUrl
  } catch { /* sin ventana (pruebas): español */ }
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (isLang(stored)) return stored
  } catch { /* almacenamiento bloqueado: se usa el predeterminado */ }
  return 'es'
}

let current: Lang = initialLang()
const listeners = new Set<() => void>()

/** Título de la pestaña según el idioma. */
const pageTitle = () => current === 'en' ? 'AguaAlerta · Climate and Territorial Monitor' : 'AguaAlerta · Monitor Climático y Territorial'

function applyToDocument() {
  if (typeof document === 'undefined') return
  document.documentElement.lang = current === 'en' ? 'en' : 'es-CR'
  document.title = pageTitle()
}
applyToDocument()

export const getLang = (): Lang => current

export function setLang(next: Lang) {
  if (next === current) return
  current = next
  try { window.localStorage.setItem(STORAGE_KEY, next) } catch { /* se pierde solo la preferencia */ }
  applyToDocument()
  listeners.forEach(listener => listener())
}

const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }

/** Suscribe al componente al idioma: se vuelve a dibujar cuando cambia. */
export const useLang = (): Lang => useSyncExternalStore(subscribe, getLang, () => 'es')

/** El texto en el idioma activo. */
export const t = (es: string, en: string): string => current === 'en' ? en : es

/** Igual que `t`, pero para cualquier valor, p. ej. fragmentos de JSX con negritas o enlaces. */
export const tx = <T,>(es: T, en: T): T => current === 'en' ? en : es

/** Configuración regional para fechas, números y orden alfabético. */
export const locale = (): string => current === 'en' ? 'en-US' : 'es-CR'

/** Elige entre singular y plural según el idioma activo. */
export const plural = (count: number, es: [string, string], en: [string, string]): string => {
  const [one, many] = current === 'en' ? en : es
  return count === 1 ? one : many
}

// --- Formatos que dependen del idioma, con caché por idioma y opciones ---
const formatters = new Map<string, Intl.NumberFormat | Intl.DateTimeFormat | Intl.Collator>()
function cached<T extends Intl.NumberFormat | Intl.DateTimeFormat | Intl.Collator>(kind: string, options: object | undefined, make: () => T): T {
  const key = `${kind}|${current}|${JSON.stringify(options ?? {})}`
  let found = formatters.get(key)
  if (!found) { found = make(); formatters.set(key, found) }
  return found as T
}

/** Como `new Intl.NumberFormat(...)`, pero con el idioma activo al momento de formatear (se puede declarar a nivel de módulo). */
export const lazyNumberFormat = (options?: Intl.NumberFormatOptions) =>
  ({ format: (value: number | bigint) => cached('n', options, () => new Intl.NumberFormat(locale(), options)).format(value) })

/** Igual que `lazyNumberFormat`, para fechas. */
export const lazyDateFormat = (options?: Intl.DateTimeFormatOptions) =>
  ({ format: (value?: Date | number) => cached('d', options, () => new Intl.DateTimeFormat(locale(), options)).format(value) })

/** Orden alfabético según el idioma activo (para `Array.sort`). */
export const collate = (a: string, b: string): number => cached('c', undefined, () => new Intl.Collator(locale())).compare(a, b)
