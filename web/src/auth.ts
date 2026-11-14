import admins from './data/admins.json'

export type Session = { email: string; name: string; organization: string }
export type DemoAccount = { email: string; password: string }

const SESSION_KEY = 'hefesto.admin'

/** Cuentas de demostración, para el botón de autocompletar del modal. */
export const demoAccounts: DemoAccount[] = admins.admins.map(({ email, password }) => ({ email, password }))

const toSession = (admin: { email: string; name: string; organization: string }): Session =>
  ({ email: admin.email, name: admin.name, organization: admin.organization })

/** Valida contra admins.json. Es una demostración: no hay ninguna protección real. */
export function login(email: string, password: string): Session | null {
  const wanted = email.trim().toLowerCase()
  const admin = admins.admins.find(item => item.email.toLowerCase() === wanted && item.password === password)
  if (!admin) return null
  const session = toSession(admin)
  try { sessionStorage.setItem(SESSION_KEY, session.email) } catch { /* sin almacenamiento: la sesión dura hasta recargar */ }
  return session
}

export function logout() {
  try { sessionStorage.removeItem(SESSION_KEY) } catch { /* nada que limpiar */ }
}

/** Recupera la sesión de esta pestaña, solo si el correo sigue existiendo en admins.json. */
export function restoreSession(): Session | null {
  try {
    const email = sessionStorage.getItem(SESSION_KEY)
    const admin = admins.admins.find(item => item.email === email)
    return admin ? toSession(admin) : null
  } catch { return null }
}
