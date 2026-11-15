import type { Session } from './auth'
import { copy } from './copy'
import type { Level, MapMode } from './copy'

export function Header({ level, mapMode, setMapMode, openAdmin, session, logout, goHome, openPredictions }: {
  level: Level
  mapMode: MapMode; setMapMode: (mode: MapMode) => void; openAdmin: () => void
  session: Session | null; logout: () => void; goHome: () => void; openPredictions: () => void
}) {
  const tip = copy[level]
  return <header className="header glass">
    <div className="header-title">
      <button className="pill pill-ghost home-link" onClick={goHome} title="Volver a la página de inicio">← Inicio</button>
      <h1>El Niño en CR — Monitor Climático y Territorial</h1>
    </div>
    <div className="header-controls">
      <div className="segmented" role="group" aria-label="Tipo de mapa">
        <button aria-pressed={mapMode === 'grid'} onClick={() => setMapMode('grid')} title={tip.mapTip.grid}>Datos de NASA POWER</button>
        <button aria-pressed={mapMode === 'cds'} onClick={() => setMapMode('cds')} title={tip.mapTip.cds}>Datos CDS</button>
        <button aria-pressed={mapMode === 'cantones'} onClick={() => setMapMode('cantones')} title={tip.mapTip.cantones}>Datos nacionales</button>
        <button aria-pressed="false" onClick={openPredictions} title="Cuándo podría durar El Niño y qué se espera de la temperatura y la lluvia. Página aparte, sin mapa.">Predicciones</button>
      </div>
      {session ? <div className="admin-badge" role="status" title={`${session.name} · ${session.username}`}>
        <span className="dot verde" aria-hidden="true" />
        <span>Modo Administrador Activo</span>
        <small>{session.name}</small>
        <button className="pill pill-ghost" onClick={logout}>Cerrar sesión</button>
      </div> : <button className="pill pill-ghost admin-link" onClick={openAdmin}>Acceso ASADAs / Admin</button>}
    </div>
  </header>
}
