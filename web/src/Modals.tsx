import { useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { demoAccounts, login } from './auth'
import type { Session } from './auth'
import { t } from './i18n'

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
      <header><h2>{title}</h2><button className="pill pill-ghost" onClick={onClose} aria-label={t('Cerrar', 'Close')}>✕</button></header>
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
    if (!username.trim() || !password) { setError(t('Completá usuario y contraseña.', 'Enter your username and password.')); return }
    const session = login(username, password)
    if (!session) { setError(t('Usuario o contraseña incorrectos.', 'Incorrect username or password.')); return }
    onLogin(session)
  }
  function fillDemo() {
    const account = demoAccounts[demo % demoAccounts.length]
    setUsername(account.username)
    setPassword(account.password)
    setError('')
    setDemo(value => value + 1)
  }
  return <Modal title={t('Acceso ASADAs / Admin', 'ASADA / Admin access')} onClose={onClose}>
    <form onSubmit={submit}>
      <p className="muted">{t('La consulta pública no requiere cuenta. Este acceso es solo para quienes administran una ASADA: cada usuario reporta únicamente sobre su propia ASADA.', 'Public browsing does not require an account. This access is only for those who manage an ASADA: each user reports only on their own ASADA.')}</p>
      <label>{t('Usuario de la ASADA', 'ASADA username')}<input type="text" name="user" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} /></label>
      <label>{t('Contraseña', 'Password')}<input type="password" name="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="button" className="pill pill-ghost" onClick={fillDemo}>{t('Autocompletar credenciales demo', 'Fill in demo credentials')}</button>
      <p className="muted">{t('Demostración: las cuentas viven en un archivo JSON del frontend, así que no ofrecen seguridad real. Cada clic prueba la siguiente cuenta demo.', 'Demo: the accounts live in a frontend JSON file, so they offer no real security. Each click tries the next demo account.')}</p>
      <div className="modal-actions">
        <button type="button" className="pill" onClick={onClose}>{t('Cancelar', 'Cancel')}</button>
        <button type="submit" className="pill pill-primary">{t('Ingresar', 'Log in')}</button>
      </div>
    </form>
  </Modal>
}
