import type { ReactNode } from 'react'
import { copy } from './copy'
import type { Level, Section } from './copy'

const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' } as const
const items: { id: Section; label: string; icon: ReactNode; adminOnly?: boolean }[] = [
  { id: 'general', label: 'General', icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17M12 3.5c2.5 2.6 2.5 14.4 0 17M12 3.5c-2.5 2.6-2.5 14.4 0 17" /></svg> },
  { id: 'temp', label: 'Temp', icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><path d="M10 4a2 2 0 0 1 4 0v9.2a4 4 0 1 1-4 0Z" /><path d="M12 9v7" /></svg> },
  { id: 'precip', label: 'Precip', icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><path d="M12 3.5c-3 4.2-6 7-6 10.2a6 6 0 0 0 12 0c0-3.2-3-6-6-10.2Z" /></svg> },
  { id: 'avisos', label: 'Avisos Generales', icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><path d="M6 17V11a6 6 0 0 1 12 0v6l1.5 2h-15Z" /><path d="M10 21h4" /></svg> },
  { id: 'admin', label: 'Admin', adminOnly: true, icon: <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}><path d="M12 3.5 5 6.5v5c0 4.2 2.8 7.4 7 9 4.2-1.6 7-4.800 7-9v-5Z" /><path d="m9 12 2.200 2.200L15.500 10" /></svg> },
]

export function Sidebar({ level, section, setSection, admin }: {
  level: Level; section: Section; setSection: (section: Section) => void; admin: boolean
}) {
  return <nav className="rail glass" aria-label="Secciones">
    {items.filter(item => admin || !item.adminOnly).map(item => <button key={item.id} aria-pressed={section === item.id} title={copy[level].sectionTip[item.id]}
      onClick={() => setSection(item.id)}>{item.icon}<span>{item.label}</span></button>)}
  </nav>
}
