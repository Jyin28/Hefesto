import type { ReactNode } from 'react'
import type { MapMode } from './copy'
import type { Canton, Operator } from './data'
import { SearchBox } from './SearchBox'
import { t } from './i18n'

/** Encabezado del panel: número de celda (pequeño, arriba), provincias o nombre del lugar y, si aplica, los cantones de la celda. */
export type PanelHeader = { cellTag?: string; kicker?: string; title: string; cantons?: string }

/**
 * Panel derecho único, estilo Google Maps: el buscador con autocompletado vive arriba (cantones siempre, ASADAs solo
 * en el mapa de cuencas) y, al elegir un resultado, el mismo panel se expande hacia abajo con el detalle de la zona.
 */
export function InfoPanel({ choices, asadas, mode, loading, blank, back, select, selectAsada, selectProvince, closeAsada,
  selected, cell, header, collapsed, mapTip, children }: {
  choices: Map<string, Canton>; asadas: Operator[]; mode: MapMode; loading: boolean
  /** Sin nada que mostrar: solo quedan el buscador y las zonas sugeridas. */
  blank: boolean; back: () => void
  select: (code: string) => void; selectAsada: (operator: Operator) => void; selectProvince: (province: string) => void
  /** Cierra la ASADA elegida (deja el cantón abierto con la lista de sus ASADAs). Se usa al hacer clic en la barra de búsqueda. */
  closeAsada: () => void
  selected: string; cell: string; header: PanelHeader
  collapsed: boolean; mapTip: string; children: ReactNode
}) {
  const hasSelection = !!selected || !!cell
  const chip = mode === 'cds' ? 'Copernicus ERA5-Land' : mode === 'grid' ? 'NASA POWER' : ''
  // En el mapa de cuencas, un cantón abierto muestra solo su lista de ASADAs: sin chips ni notas.
  const onlyAsadas = mode === 'cantones' && !!selected
  return <aside className="drawer glass" id="ficha" aria-label={t('Panel de información', 'Information panel')} inert={collapsed}>
    <div className="drawer-top">
      <SearchBox context={mode} choices={choices} asadas={asadas} loading={loading} back={hasSelection ? back : undefined}
        onCanton={select} onAsada={selectAsada} onProvince={selectProvince} onSearchFocus={closeAsada} />
    </div>
    {!blank && <div className="drawer-detail open">
      <div className="drawer-title">
        {header.cellTag && <small className="cell-tag">{header.cellTag}</small>}
        {header.kicker && <small>{header.kicker}</small>}
        <h2>{header.title}</h2>
        {header.cantons && <p className="cell-cantons"><strong>{header.cantons.includes(',') ? t('Cantones', 'Cantons') : t('Cantón', 'Canton')}:</strong> {header.cantons}</p>}
        {chip && !onlyAsadas && <div className="chips"><span className="chip nasa">{chip}</span></div>}
      </div>
      <div className="bento">{children}</div>
      {!onlyAsadas && <p className="muted">{mapTip}</p>}
    </div>}
  </aside>
}
