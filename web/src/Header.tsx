import type { Session } from './auth'
import { copy } from './copy'
import type { Level, MapMode } from './copy'

export function Header({ level, mapMode, setMapMode, openAdmin, session, logout }: {
  level: Level
  mapMode: MapMode; setMapMode: (mode: MapMode) => void; openAdmin: () => void
  session: Session | null; logout: () => void
}) {
  const tip = copy[level]
  return <header className="header glass">
    <h1>El Niño en CR — Monitor Climático y Territorial</h1>
    <div className="header-controls">
      <div className="segmented" role="group" aria-label="Tipo de mapa">
        <button aria-pressed={mapMode === 'grid'} onClick={() => setMapMode('grid')} title={tip.mapTip.grid}>Mapa Interactivo: Cuadrícula NASA POWER (0.5° × 0.625°)</button>
        <button aria-pressed={mapMode === 'cantones'} onClick={() => setMapMode('cantones')} title={tip.mapTip.cantones}>Cuencas Cantonales y Afectaciones</button>
      </div>
      {session ? <div className="admin-badge" role="status" title={`${session.name} · ${session.email}`}>
        <span className="dot verde" aria-hidden="true" />
        <span>Modo Administrador Activo (Comisión Nacional)</span>
        <small>{session.name}</small>
        <button className="pill pill-ghost" onClick={logout}>Cerrar sesión</button>
      </div> : <button className="pill pill-ghost admin-link" onClick={openAdmin}>Acceso Comisiones / Admin</button>}
    </div>
  </header>
}
