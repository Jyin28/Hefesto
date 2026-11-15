import { useMemo } from 'react'
import { flowText } from './asadas'
import { Tile } from './Bento'
import type { Operator } from './data'
import type { AsadaReport } from './data/cantonData'
import { collate, lazyDateFormat, t } from './i18n'

const dayFormat = lazyDateFormat({ dateStyle: 'medium', timeZone: 'UTC' })
const day = (value: string) => dayFormat.format(new Date(`${value}T00:00:00Z`))

/**
 * Panel de un cantón en el mapa de cuencas: una tarjeta por ASADA (como las de las gráficas) con su histórico de caudal.
 * El histórico son los reportes de la ASADA (del más reciente al más antiguo) y el valor inicial del catálogo SAGA.
 */
export function CantonAsadaTiles({ operators, reports }: { operators: Operator[]; reports: AsadaReport[] }) {
  const rows = useMemo(() => {
    const byAsada = new Map<string, AsadaReport[]>()
    for (const item of reports) byAsada.set(item.asadaId, [...(byAsada.get(item.asadaId) ?? []), item])
    for (const list of byAsada.values()) list.sort((a, b) => b.measuredAt.localeCompare(a.measuredAt) || b.createdAt.localeCompare(a.createdAt))
    return [...operators].sort((a, b) => collate(a.name, b.name))
      .map(operator => ({ operator, history: byAsada.get(operator.id) ?? [] }))
  }, [operators, reports])

  if (rows.length === 0) return <Tile title="ASADAs"><p className="empty">{t('Este cantón no tiene operadores en el catálogo de SAGA.', 'This canton has no operators in the SAGA catalog.')}</p></Tile>
  return <>
    {rows.map(({ operator, history }) => {
      const current = history[0]?.caudal ?? operator.caudal
      return <Tile key={operator.id}
        title={operator.name} badge={<span className="chip nasa">{flowText(current)}</span>}>
        <ul className="flow-history" aria-label={t(`Histórico de caudal de ${operator.name}`, `Flow history of ${operator.name}`)}>
          {history.map(item => <li key={item.id}><span>{day(item.measuredAt)}</span><span>{flowText(item.caudal)}</span></li>)}
          {operator.caudal !== null && <li className="initial"><span>{t('Valor inicial (SAGA)', 'Initial value (SAGA)')}</span><span>{flowText(operator.caudal)}</span></li>}
          {history.length === 0 && operator.caudal === null && <li className="initial"><span>{t('Sin caudal registrado', 'No flow recorded')}</span><span /></li>}
        </ul>
      </Tile>
    })}
  </>
}
