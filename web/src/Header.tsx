import type { Session } from './auth'
import { copy } from './copy'
import type { Level, MapMode } from './copy'
import { t } from './i18n'
import { LangSwitch } from './LangSwitch'

export function Header({ level, mapMode, setMapMode, openAdmin, session, logout, goHome, openPredictions }: {
  level: Level
  mapMode: MapMode; setMapMode: (mode: MapMode) => void; openAdmin: () => void
  session: Session | null; logout: () => void; goHome: () => void; openPredictions: () => void
}) {
  const tip = copy[level]
  return <header className="header glass">
    <div className="header-title">
      <button className="pill pill-ghost home-link" onClick={goHome} title={t('Volver a la página de inicio', 'Back to the home page')}>{t('← Inicio', '← Home')}</button>
      <h1>{t('AguaAlerta — Monitor Climático y Territorial', 'AguaAlerta — Climate and Territorial Monitor')}</h1>
    </div>
    <div className="header-controls">
      <LangSwitch />
      <div className="segmented" role="group" aria-label={t('Tipo de mapa', 'Map type')}>
        <button aria-pressed={mapMode === 'grid'} onClick={() => setMapMode('grid')} title={tip.mapTip.grid}>{t('Datos de NASA POWER', 'NASA POWER data')}</button>
        <button aria-pressed={mapMode === 'cds'} onClick={() => setMapMode('cds')} title={tip.mapTip.cds}>{t('Datos CDS', 'CDS data')}</button>
        <button aria-pressed={mapMode === 'cantones'} onClick={() => setMapMode('cantones')} title={tip.mapTip.cantones}>{t('Datos nacionales', 'National data')}</button>
        <button aria-pressed="false" onClick={openPredictions} title={t('Cuándo podría durar El Niño y qué se espera de la temperatura y la lluvia. Página aparte, sin mapa.', 'How long El Niño could last and what is expected for temperature and rain. Separate page, no map.')}>{t('Predicciones', 'Predictions')}</button>
      </div>
      {session ? <div className="admin-badge" role="status" title={`${session.name} · ${session.username}`}>
        <span className="dot verde" aria-hidden="true" />
        <span>{t('Modo Administrador Activo', 'Administrator Mode Active')}</span>
        <small>{session.name}</small>
        <button className="pill pill-ghost" onClick={logout}>{t('Cerrar sesión', 'Log out')}</button>
      </div> : <button className="pill pill-ghost admin-link" onClick={openAdmin}>{t('Acceso ASADAs / Admin', 'ASADA / Admin access')}</button>}
    </div>
  </header>
}
