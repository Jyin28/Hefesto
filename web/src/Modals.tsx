import { useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { demoAccounts, login } from './auth'
import type { Session } from './auth'

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const root = box.current
    const focusable = () => Array.from(root?.querySelectorAll<HTMLElement>('button, input, textarea, select, a[href]') ?? [])
      .filter(item => !item.hasAttribute('disabled'))
    focusable()[1]?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') { onClose(); return }
      if (event.key !== 'Tab') return
      const items = focusable()
      if (!items.length) return
      const first = items[0], last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); previous?.focus() }
  }, [onClose])
  return <div className="backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <div className="modal glass" role="dialog" aria-modal="true" aria-label={title} ref={box}>
      <header><h2>{title}</h2><button className="pill pill-ghost" onClick={onClose} aria-label="Cerrar">✕</button></header>
      {children}
    </div>
  </div>
}

export function AdminModal({ onClose, onLogin }: { onClose: () => void; onLogin: (session: Session) => void }) {
  const [error, setError] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [demo, setDemo] = useState(0)
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!username.trim() || !password) { setError('Completá usuario y contraseña.'); return }
    const session = login(username, password)
    if (!session) { setError('Usuario o contraseña incorrectos.'); return }
    onLogin(session)
  }
  function fillDemo() {
    const account = demoAccounts[demo % demoAccounts.length]
    setUsername(account.username)
    setPassword(account.password)
    setError('')
    setDemo(value => value + 1)
  }
  return <Modal title="Acceso ASADAs / Admin" onClose={onClose}>
    <form onSubmit={submit}>
      <p className="muted">La consulta pública no requiere cuenta. Este acceso es solo para quienes administran una ASADA: cada usuario reporta únicamente sobre su propia ASADA.</p>
      <label>Usuario de la ASADA<input type="text" name="user" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} /></label>
      <label>Contraseña<input type="password" name="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="button" className="pill pill-ghost" onClick={fillDemo}>Autocompletar credenciales demo</button>
      <p className="muted">Demostración: las cuentas viven en un archivo JSON del frontend, así que no ofrecen seguridad real. Cada clic prueba la siguiente cuenta demo.</p>
      <div className="modal-actions">
        <button type="button" className="pill" onClick={onClose}>Cancelar</button>
        <button type="submit" className="pill pill-primary">Ingresar</button>
      </div>
    </form>
  </Modal>
}
