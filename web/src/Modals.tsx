import { useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'

export type InfoRequest = {
  id: string; zone: string; name: string; organization: string; email: string
  topics: string[]; message: string; createdAt: string
}

export const REQUEST_TOPICS = ['Temperatura', 'Precipitación', 'Cuencas', 'Servicio de agua', 'Otro']

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

export function AdminModal({ onClose }: { onClose: () => void }) {
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    if (!String(data.get('user') ?? '').trim() || !String(data.get('password') ?? '')) {
      setError('Completá usuario y contraseña.')
      return
    }
    setError('')
    setDone(true)
  }
  return <Modal title="Acceso Comisiones / Admin" onClose={onClose}>
    {done ? <>
      <p className="empty" role="status">Acceso para comisiones en preparación. Todavía no se guarda ni se verifica ninguna credencial. Podés seguir consultando el mapa sin iniciar sesión.</p>
      <div className="modal-actions"><button className="pill pill-primary" onClick={onClose}>Volver al mapa</button></div>
    </> : <form onSubmit={submit}>
      <p className="muted">La consulta pública no requiere cuenta. Este acceso es solo para comisiones y administración.</p>
      <label>Usuario<input type="text" name="user" autoComplete="username" /></label>
      <label>Contraseña<input type="password" name="password" autoComplete="current-password" /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="modal-actions">
        <button type="button" className="pill" onClick={onClose}>Cancelar</button>
        <button type="submit" className="pill pill-primary">Ingresar</button>
      </div>
    </form>}
  </Modal>
}

export function RequestModal({ zone, onClose, onSubmit }: {
  zone: string; onClose: () => void; onSubmit: (request: Omit<InfoRequest, 'id' | 'createdAt'>) => void
}) {
  const [error, setError] = useState('')
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const name = String(data.get('name') ?? '').trim()
    const email = String(data.get('email') ?? '').trim()
    const topics = data.getAll('topics').map(String)
    if (!name || !/^\S+@\S+\.\S+$/.test(email)) { setError('Indicá tu nombre y un correo válido.'); return }
    if (!topics.length) { setError('Elegí al menos un tipo de información.'); return }
    onSubmit({
      zone: String(data.get('zone') ?? zone).trim() || zone, name, email, topics,
      organization: String(data.get('organization') ?? '').trim(),
      message: String(data.get('message') ?? '').trim(),
    })
  }
  return <Modal title="Pedir información de esta zona" onClose={onClose}>
    <form onSubmit={submit}>
      <p className="muted">Usá este formulario para pedir datos de cantones o cuencas cuya información todavía está pendiente de ser facilitada.</p>
      <label>Zona<input type="text" name="zone" defaultValue={zone} /></label>
      <label>Tu nombre<input type="text" name="name" autoComplete="name" /></label>
      <label>Comisión u organización (opcional)<input type="text" name="organization" /></label>
      <label>Correo<input type="email" name="email" autoComplete="email" /></label>
      <fieldset><legend>Información que necesitás</legend>
        {REQUEST_TOPICS.map(topic => <label key={topic}><input type="checkbox" name="topics" value={topic} />{topic}</label>)}
      </fieldset>
      <label>Mensaje (opcional)<textarea name="message" rows={3} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="modal-actions">
        <button type="button" className="pill" onClick={onClose}>Cancelar</button>
        <button type="submit" className="pill pill-primary">Enviar solicitud</button>
      </div>
    </form>
  </Modal>
}
