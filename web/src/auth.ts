import admins from './data/admins.json'

/** Un administrador representa a una sola ASADA: `asadaId` es su IDEO en el catálogo de SAGA. */
export type Session = { username: string; name: string; organization: string; asadaId: string }
export type DemoAccount = { username: string; password: string }

const SESSION_KEY = 'hefesto.admin.v2'

/** Cuentas de demostración, para el botón de autocompletar del modal. */
export const demoAccounts: DemoAccount[] = admins.admins.map(({ username, password }) => ({ username, password }))

const toSession = (admin: Session): Session =>
  ({ username: admin.username, name: admin.name, organization: admin.organization, asadaId: admin.asadaId })

/** Valida contra admins.json. Es una demostración: no hay ninguna protección real. */
export function login(username: string, password: string): Session | null {
  const wanted = username.trim().toLowerCase()
  const admin = admins.admins.find(item => item.username.toLowerCase() === wanted && item.password === password)
  if (!admin) return null
  const session = toSession(admin)
  try { sessionStorage.setItem(SESSION_KEY, session.username) } catch { /* sin almacenamiento: la sesión dura hasta recargar */ }
  return session
}

export function logout() {
  try { sessionStorage.removeItem(SESSION_KEY) } catch { /* nada que limpiar */ }
}

/** Recupera la sesión de esta pestaña, solo si el usuario sigue existiendo en admins.json. */
export function restoreSession(): Session | null {
  try {
    const username = sessionStorage.getItem(SESSION_KEY)
    const admin = admins.admins.find(item => item.username === username)
    return admin ? toSession(admin) : null
  } catch { return null }
}
