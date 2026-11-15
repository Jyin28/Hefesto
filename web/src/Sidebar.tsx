import type { ReactNode } from 'react'
import { copy } from './copy'
import type { Level, Section } from './copy'
import { t } from './i18n'

const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' } as const
const items = (): { id: Section; label: string; icon: ReactNode; adminOnly?: boolean }[] => [
  { id: 'general', label: t('General', 'General'), icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17M12 3.5c2.5 2.6 2.5 14.4 0 17M12 3.5c-2.5 2.6-2.5 14.4 0 17" /></svg> },
  { id: 'temp', label: t('Temp', 'Temp'), icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><path d="M10 4a2 2 0 0 1 4 0v9.2a4 4 0 1 1-4 0Z" /><path d="M12 9v7" /></svg> },
  { id: 'precip', label: t('Precip', 'Rain'), icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><path d="M12 3.5c-3 4.2-6 7-6 10.2a6 6 0 0 0 12 0c0-3.2-3-6-6-10.2Z" /></svg> },
  { id: 'uv', label: 'UV', icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><circle cx="12" cy="12" r="3.8" /><path d="M12 3v2.4M12 18.6V21M3 12h2.4M18.6 12H21M5.6 5.6l1.7 1.7M16.7 16.7l1.7 1.7M5.6 18.4l1.7-1.7M16.7 7.3l1.7-1.7" /></svg> },
  { id: 'humedad', label: t('Humedad', 'Humidity'), icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><path d="M12 3.5c-2.6 3.7-5.2 6.2-5.2 9a5.2 5.2 0 0 0 10.4 0c0-2.8-2.6-5.300-5.200-9Z" /><path d="M3.5 20c1.200-.9 2.300-.9 3.500 0s2.300.9 3.500 0 2.300-.9 3.500 0 2.300.9 3.500 0 2.300-.9 3.500 0" /></svg> },
  { id: 'admin', label: 'Admin', adminOnly: true, icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><path d="M12 3.5 5 6.5v5c0 4.2 2.8 7.4 7 9 4.2-1.6 7-4.800 7-9v-5Z" /><path d="m9 12 2.200 2.200L15.500 10" /></svg> },
]

/** `disabled`: secciones que no aplican en el mapa activo, con el motivo que se muestra como tooltip. */
export function Sidebar({ level, section, setSection, admin, disabled }: {
  level: Level; section: Section; setSection: (section: Section) => void; admin: boolean
  disabled: Partial<Record<Section, string>>
}) {
  return <nav className="rail glass" aria-label={t('Secciones', 'Sections')}>
    {items().filter(item => admin || !item.adminOnly).map(item => {
      const reason = disabled[item.id]
      return <button key={item.id} aria-pressed={!reason && section === item.id} disabled={!!reason}
        title={reason ?? copy[level].sectionTip[item.id]}
        onClick={() => setSection(item.id)}>{item.icon}<span>{item.label}</span></button>
    })}
  </nav>
}
