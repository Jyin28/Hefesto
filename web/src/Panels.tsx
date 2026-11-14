import { ensoMean } from './analysis'
import { Tile } from './Bento'
import { ClimateDetails, WaterDetails } from './ClimateDetails'
import { copy } from './copy'
import type { Alert, Level } from './copy'
import { regions } from './data'
import type { Canton, Climate, Local, Notice, Region, Variable } from './data'

const format = new Intl.NumberFormat('es-CR', { maximumFractionDigits: 2 })
const dateFormat = new Intl.DateTimeFormat('es-CR', { dateStyle: 'medium', timeZone: 'America/Costa_Rica' })

export function GeneralPanel({ level, climateBy, region, canton, cell, alert, notices, loading }: {
  level: Level; climateBy: Record<Variable, Climate | undefined>; region?: Region; canton?: Canton; cell: string
  alert: Alert; notices: Notice[]; loading: boolean
}) {
  const text = copy[level]
  const enso = climateBy.PRECTOTCORR?.enso
  // La anomalía del episodio está en las unidades de cada variable (mm/mes y °C), no es un índice del océano.
  const rain = ensoMean(climateBy.PRECTOTCORR)
  const heat = ensoMean(climateBy.T2M)
  const regionName = regions.find(item => item.id === region)?.name
  return <>
    <Tile title={text.ensoTitle} tip={text.tipAnomaly}>
      {enso?.episode ? <>
        <p>{text.ensoBody(enso.episode.start, enso.episode.end, 'mm/mes y °C')}</p>
        {level === 'tecnico' && <p className="muted">Anomalía mensual media del episodio · {rain != null && `PRECTOTCORR ${format.format(rain)} mm/mes`}{rain != null && heat != null && ' · '}{heat != null && `T2M ${format.format(heat)} °C`}</p>}
        {level === 'basico' && (rain != null || heat != null) && <p className="muted">En esos meses, en promedio{rain != null && <>, llovió {format.format(Math.abs(rain))} mm al mes {rain < 0 ? 'menos' : 'más'} de lo habitual</>}{rain != null && heat != null && ' y'}{heat != null && <> la temperatura estuvo {format.format(Math.abs(heat))} °C {heat < 0 ? 'por debajo' : 'por encima'} de lo habitual</>}. Es una comparación, no prueba que El Niño sea la causa.</p>}
      </> : <p className="empty">{loading ? 'Cargando…' : text.ensoUnknown}</p>}
    </Tile>
    <Tile title={cell ? `Celda ${cell}` : canton?.name ?? 'Costa Rica'} span={2}>
      <div className="chips">
        <span className={`chip ${alert}`}>{text.alertLabel[alert]}</span>
        {regionName ? <span className="chip nasa">Datos NASA POWER · {regionName}</span> : <span className="chip imn">Información pendiente</span>}
      </div>
      <p className="muted" style={{ marginTop: 8 }}>{notices.length
        ? `${notices.length} ${notices.length === 1 ? 'comunicado asociado' : 'comunicados asociados'} a este cantón.`
        : 'Todavía no hay comunicados verificados para este cantón.'}</p>
      {!regionName && <p className="muted">Usá «Pedir información de esta zona» si tu comisión necesita estos datos.</p>}
    </Tile>
  </>
}

export function ClimatePanel({ variable, level, climate, remote, queryKey, region, cell, setCell, setRegion, years, setYears, setAppliedYears,
  requestError, setRequestError, loading, catalog, selected, rangeApprox }: {
  variable: Variable; level: Level; climate?: Climate; remote?: Climate; queryKey: string
  region?: Region; cell: string; setCell: (cell: string) => void; setRegion: (region?: Region) => void
  years: number[]; setYears: (years: number[]) => void; setAppliedYears: (years: number[]) => void
  requestError: string; setRequestError: (message: string) => void; loading: boolean
  catalog: Local; selected: string; rangeApprox: boolean
}) {
  const text = copy[level]
  const unit = text.unit[variable]
  const chosenRegion = regions.find(item => item.id === region)
  function printCard() {
    const collapsed = Array.from(document.querySelectorAll<HTMLDetailsElement>('#ficha details:not([open])'))
    collapsed.forEach(item => { item.open = true })
    try { window.print() } finally { collapsed.forEach(item => { item.open = false }) }
  }
  return <Tile title={level === 'tecnico' ? 'Detalle estadístico, ventanas A/B y descargas' : 'Más detalle y descargas'}>
    <div className="climate-controls">
      <label>Zona climática <select value={region ?? ''} onChange={event => { setRegion((event.target.value || undefined) as Region | undefined); setCell('') }}>
        <option value="" disabled>Elegir zona</option>
        {regions.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select></label>
    </div>
    {region && <details>
      <summary>{level === 'tecnico' ? 'Ajustar ventanas A y B' : 'Cambiar los períodos que se comparan'}</summary>
      <form className="period-controls" onSubmit={event => {
        event.preventDefault()
        if (years[0] > years[1] || years[2] > years[3]) setRequestError('El año inicial debe ser anterior o igual al final.')
        else { setRequestError(''); setAppliedYears([...years]) }
      }}>
        {['Inicio A', 'Fin A', 'Inicio B', 'Fin B'].map((label, index) => <label key={label}>{label}
          <input type="number" min={1981} max={2024} required value={years[index] || ''}
            onChange={event => setYears(years.map((year, position) => position === index ? Number(event.target.value) : year))} />
        </label>)}
        <button type="submit" className="pill">Aplicar</button>
      </form>
    </details>}
    {cell && <button type="button" className="pill pill-ghost" onClick={() => setCell('')}>Volver al promedio del sector</button>}
    {requestError && (!climate || requestError.startsWith('El año')) && <p role="status" className="error">{requestError}</p>}
    {climate ? <>
      <div><h3>{text.variableTitle[variable]}</h3>
        <p className="muted">{chosenRegion?.name} · {cell ? `Celda ${cell}` : 'Promedio del sector'}</p></div>
      {rangeApprox && <p className="muted">Sin conexión con la API: la tendencia oficial y la comparación siguen calculadas sobre 1981–2024. El gráfico sí usa el rango elegido.</p>}
      {climate.comparison && <div className="periods" aria-label={text.windows}>
        {[climate.comparison.window_a, climate.comparison.window_b].map((window, index) => <div className="card" key={index}>
          <small>{level === 'tecnico' ? ['A', 'B'][index] + ' · ' : ''}{window.start_year}–{window.end_year} · {window.n_years} años</small>
          <strong>{window.mean === null ? 'Sin datos' : `${format.format(window.mean)} ${unit}`}</strong></div>)}
      </div>}
      <p className="trend" title={text.tipSlope}>{text.trend(climate.trend.slope_per_decade, climate.trend.n_years, unit)}</p>
      <p className="muted" title={text.tipSignificance}>{text.significance(climate.trend.significant)}</p>
      <p className="source"><a href={climate.sourceUrl}>{climate.source}</a></p>
      <ClimateDetails data={climate} unit={unit} selected={cell} choose={setCell} level={level} />
      {variable === 'PRECTOTCORR' && <WaterDetails local={catalog} canton={selected} />}
      <div className="exports" aria-label="Descargas">
        <button type="button" className="pill pill-ghost" onClick={printCard}>Imprimir ficha</button>
        {remote && <>
          <a download="ficha-detective-tico.json" href={`/api/ficha/${queryKey}`}>JSON</a>
          {['series', 'results', 'sources', 'enso',
            ...(remote.water_coverage.length ? ['water'] : []),
            ...(remote.distribution.length ? ['distribution'] : []),
          ].map(table => <a key={table} href={`/api/ficha/${queryKey}&tabla=${table}`}>CSV {({
            series: 'serie', results: 'resultados', water: 'cobertura de agua', distribution: 'distribución',
            sources: 'fuentes', enso: 'El Niño',
          } as Record<string, string>)[table]}</a>)}
        </>}
      </div>
    </> : <p className="empty">{region ? (loading ? 'Cargando la serie climática…' : 'Serie regional no disponible.')
      : 'Esta zona todavía no tiene datos de NASA POWER asociados. Podés elegir un sector arriba o pedir la información.'}</p>}
  </Tile>
}

export function NoticesPanel({ level, loading, notices, operators, catalog, selected, alert, highlight, highlightCanton }: {
  level: Level; loading: boolean; notices: Notice[]; operators: Local['operators']; catalog: Local
  selected: string; alert: Alert; highlight: string | null; highlightCanton: string | null
}) {
  const text = copy[level]
  return <>
    <Tile title={level === 'tecnico' ? 'Comunicados activos' : 'Avisos publicados'} badge={<span className={`chip ${alert}`}>{text.alertLabel[alert]}</span>}>
    {notices.length ? notices.map(notice => {
      const url = new URL(window.location.href)
      url.search = new URLSearchParams({ canton: selected, vista: 'avisos', aviso: notice.id }).toString()
      const expired = notice.expiresAt && new Date(notice.expiresAt) < new Date()
      return <article className={highlight === notice.id && highlightCanton === selected ? 'card notice highlighted' : 'card notice'} key={notice.id}>
        <p className="source">{notice.source} · {dateFormat.format(new Date(notice.publishedAt))}</p>
        <h4>{notice.title}</h4><p>{notice.summary}</p>
        {notice.communities.length > 0 && <p>Comunidades · {notice.communities.join(', ')}</p>}
        {notice.expiresAt && <p>{expired ? 'Venció el' : 'Vigencia publicada hasta el'} {dateFormat.format(new Date(notice.expiresAt))}</p>}
        <div className="notice-links"><a href={notice.sourceUrl}>Ver comunicado</a><a href={`https://wa.me/?text=${encodeURIComponent(url.href)}`}>Compartir por WhatsApp</a></div>
      </article>
    }) : <p className="empty">{loading ? 'Cargando avisos…' : 'Todavía no hay comunicados verificados en la página para este cantón.'}</p>}
    </Tile>
    <Tile title={text.recommendationsTitle}>
      <ul className="tips">{text.recommendations.map(item => <li key={item}>{item}</li>)}</ul>
      <p className="muted">{text.recommendationsNote}</p>
    </Tile>
    <Tile title="ASADAS y operadores">
      {operators.length ? operators.map(operator => <p key={operator.name}><strong>{operator.name}</strong><br />{operator.communities.join(', ')}{operator.phone && <> · <a href={`tel:${operator.phone}`}>{operator.phone}</a></>}{operator.sourceId && catalog.sources?.[operator.sourceId] && <> · <a href={catalog.sources[operator.sourceId].url}>Fuente</a></>}</p>)
        : <p className="muted">Directorio local pendiente de verificación.</p>}
      <WaterDetails local={catalog} canton={selected} />
    </Tile>
  </>
}
