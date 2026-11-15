import { useState } from 'react'
import type { CSSProperties } from 'react'
import { CountUp } from './CountUp'
import { t } from './i18n'
import { EnsoTimeline, RainChart, TemperatureChart } from './PredictionCharts'
import { REGIONS, REGION_SHORT, ensoCategory, firstTemperature, fromData, monthLong, monthOnly, monthShort, num, rainAnalog, signed } from './predictionsData'
import type { Predictions as PredictionsData, RegionId } from './predictionsData'

export const stagger = (index: number) => ({ '--i': index }) as CSSProperties
const meter = (percent: number) => ({ '--w': `${Math.max(0, Math.min(100, percent))}%` }) as CSSProperties

function RegionTabs({ value, onChange, label }: { value: RegionId; onChange: (region: RegionId) => void; label: string }) {
  return <div className="segmented pred-tabs" role="group" aria-label={label}>
    {REGIONS.map(region => <button key={region} aria-pressed={value === region} onClick={() => onChange(region)}>{REGION_SHORT[region]}</button>)}
  </div>
}

// ------------------------------------------------------------------ Lo más importante

function NinoCard({ data }: { data: PredictionsData }) {
  const { enso } = data
  const analog = enso.analog
  if (enso.status !== 'active' || !enso.start) {
    return <article className="pred-card reveal" style={stagger(0)}>
      <span className="eyebrow">El Niño</span>
      <p className="pred-big">{num(enso.latest.value)}<small> RONI · {monthShort(enso.latest.month)}</small></p>
      <p>{t('Ahora no hay un episodio de El Niño en curso: el RONI está por debajo de 0,5.', 'There is no El Niño episode under way right now: the RONI is below 0.5.')}</p>
    </article>
  }
  const typical = (label: string) => t(`lo más típico: ${monthLong(label)}`, `most typical: ${monthLong(label)}`)
  const phases = [
    { name: t('Inicio', 'Start'), value: monthLong(enso.start), note: t(`confirmado: ${enso.months_so_far} meses con RONI ≥ 0,5`, `confirmed: ${enso.months_so_far} months with RONI ≥ 0.5`) },
    ...(analog?.peak_window ? [{ name: t('Pico', 'Peak'), value: `${monthShort(analog.peak_window.earliest)} – ${monthShort(analog.peak_window.latest)}`, note: typical(analog.peak_window.typical) }] : []),
    ...(analog ? [{ name: t('Fin', 'End'), value: `${monthShort(analog.end_window.earliest)} – ${monthShort(analog.end_window.latest)}`, note: typical(analog.end_window.typical) }] : []),
  ]
  return <article className="pred-card nino reveal" style={stagger(0)}>
    <span className="eyebrow"><span className="pulse-dot" aria-hidden="true" /> {t('El Niño en curso · rango de fechas', 'El Niño under way · date range')}</span>
    <p className="pred-big"><CountUp value={enso.latest.value} format={value => num(value)} /><small> {t(`RONI en ${monthShort(enso.latest.month)} · ${ensoCategory(enso.category)}${enso.rising ? ' y subiendo' : ''}`, `RONI in ${monthShort(enso.latest.month)} · ${ensoCategory(enso.category)}${enso.rising ? ' and rising' : ''}`)}</small></p>
    <ol className="phases">
      {phases.map((phase, index) => <li key={phase.name} style={stagger(index)}>
        <span>{phase.name}</span><strong>{phase.value}</strong><em>{phase.note}</em>
      </li>)}
    </ol>
    {analog && <p className="muted">{t(`Pico y fin salen de ${analog.n} episodios fuertes anteriores. Es una comparación histórica, no un pronóstico del océano.`,
      `Peak and end come from ${analog.n} earlier strong episodes. It is a historical comparison, not an ocean forecast.`)}</p>}
  </article>
}

function TemperatureCard({ data }: { data: PredictionsData }) {
  const national = firstTemperature(data, 'CR')
  if (!national) return null
  const regions = REGIONS.map(region => ({ region, found: firstTemperature(data, region) })).filter(item => item.found)
  return <article className="pred-card heat reveal" style={stagger(1)}>
    <span className="eyebrow">{t('Temperatura', 'Temperature')} · {monthLong(national.row.target_month)}</span>
    <p className="pred-big"><CountUp value={national.anomaly} format={value => `${value < 0 ? '−' : '+'}${num(Math.abs(value))}`} /><small> {t('°C sobre lo normal en todo el país', '°C above normal across the country')}</small></p>
    <div className="meters">
      {regions.map(({ region, found }, index) => <div key={region} className="meter-row" style={stagger(index)}>
        <span>{REGION_SHORT[region]}</span>
        <div className="meter heat"><span style={meter((found!.anomaly / 2) * 100)} /></div>
        <strong>{signed(found!.anomaly)} °C</strong>
      </div>)}
    </div>
    <p className="muted">{t(`Pronóstico experimental. Estimación del país: ${num(national.estimate)} °C (banda de 90 %: ${num(national.low)} a ${num(national.high)}), frente a ${num(national.normal)} °C normales.`,
      `Experimental forecast. National estimate: ${num(national.estimate)} °C (90 % band: ${num(national.low)} to ${num(national.high)}), versus ${num(national.normal)} °C normal.`)}</p>
  </article>
}

function RainCard({ data }: { data: PredictionsData }) {
  const month = data.variables.PRECTOTCORR.regions.CR.rows[0]?.target_month
  const national = month ? rainAnalog(data, 'CR', month) : undefined
  if (!month || !national) return null
  return <article className="pred-card rain reveal" style={stagger(2)}>
    <span className="eyebrow">{t('Lluvia', 'Rain')} · {monthLong(month)}</span>
    <p className="pred-big"><CountUp value={national.anomaly_pct} format={value => `${value < 0 ? '−' : '+'}${num(Math.abs(value), 0)} %`} /><small> {t('en años parecidos de El Niño', 'in similar El Niño years')}</small></p>
    <div className="meters">
      {REGIONS.map((region, index) => {
        const found = rainAnalog(data, region, month)
        return found && <div key={region} className="meter-row" style={stagger(index)}>
          <span>{REGION_SHORT[region]}</span>
          <div className="meter rain"><span style={meter(Math.abs(found.anomaly_pct))} /></div>
          <strong>{signed(found.anomaly_pct, 0)} %</strong>
        </div>
      })}
    </div>
    <p className="tag">{t('Sin pronóstico validado de lluvia', 'No validated rain forecast')}</p>
    <p className="muted">{t(`Es lo que pasó en ${national.n_years} años con un Niño como el actual, frente a lo normal. Describe el pasado; no asegura lo que va a llover.`,
      `It is what happened in ${national.n_years} years with an El Niño like the current one, compared with normal. It describes the past; it does not guarantee how much it will rain.`)}</p>
  </article>
}

// ------------------------------------------------------------------ Detalle

function TemperatureSection({ data, initial }: { data: PredictionsData; initial: RegionId }) {
  const [region, setRegion] = useState<RegionId>(initial)
  const block = data.variables.T2M
  const rows = block.regions[region].rows
  const validation = data.temperature_validation[`CDS/${region}/T2M`]
  const best = validation ? validation.horizons['1'] : undefined
  const horizon = validation?.max_contiguous_horizon
  return <section className="section" id="temperatura" aria-labelledby="temp-title">
    <div className="section-head reveal">
      <span className="eyebrow">{t('Predicción experimental', 'Experimental prediction')}</span>
      <h2 id="temp-title">{t('Temperatura de los próximos meses', 'Temperature for the coming months')}</h2>
      <p className="lead">{t('La única variable con pronóstico: promedio mensual de cada sector, con su banda de 90 % de confianza. Solo se publica donde la prueba con datos pasados lo respaldó.',
        'The only variable with a forecast: monthly average for each sector, with its 90 % confidence band. It is only published where the test with past data backed it.')}</p>
    </div>
    <div className="pred-panel reveal">
      <div className="pred-panel-head"><RegionTabs value={region} onChange={setRegion} label={t('Sector de la predicción de temperatura', 'Sector of the temperature prediction')} />
        <div className="legend-inline"><span><i className="sw band" />{t('Lo normal (1991–2020, 8 de cada 10 años)', 'Normal (1991–2020, 8 out of 10 years)')}</span><span><i className="sw amber" />{t('Estimación y banda de 90 %', 'Estimate and 90 % band')}</span></div></div>
      <TemperatureChart key={region} rows={rows} unit={block.unit} />
    </div>
    <div className="table-wrap reveal"><table className="pred-table">
      <caption>{REGION_SHORT[region]} · {t('temperatura media mensual (°C)', 'monthly mean temperature (°C)')}</caption>
      <thead><tr><th>{t('Mes', 'Month')}</th><th>{t('Estimación', 'Estimate')}</th><th>{t('Banda de 90 %', '90 % band')}</th><th>{t('Lo normal (P10–P90)', 'Normal (P10–P90)')}</th><th>{t('Diferencia', 'Difference')}</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.target_month}>
        <th scope="row">{monthLong(row.target_month)}</th>
        <td>{row.estimate === null ? <span className="muted">{t('Sin pronóstico validado', 'No validated forecast')}</span> : num(row.estimate)}</td>
        <td>{row.estimate === null ? '—' : t(`${num(row.lower90!)} a ${num(row.upper90!)}`, `${num(row.lower90!)} to ${num(row.upper90!)}`)}</td>
        <td>{num(row.reference.mean)} ({num(row.reference.p10)}–{num(row.reference.p90)})</td>
        <td>{row.estimate === null ? '—' : `${signed(Math.round(row.estimate * 10) / 10 - Math.round(row.reference.mean * 10) / 10)} °C`}</td>
      </tr>)}</tbody>
    </table></div>
    {best && <p className="muted note reveal">{t(
      `En la prueba con años pasados, para el mes siguiente este modelo se equivocó ${num(best.test_skill * 100, 0)} % menos que simplemente repetir el clima normal, y su banda de 90 % acertó ${num(best.coverage90_recent * 100, 0)} % de las veces. Más allá de ${horizon} ${horizon === 1 ? 'mes' : 'meses'} la prueba no justifica publicar un pronóstico.`,
      `In the test with past years, for the next month this model was off ${num(best.test_skill * 100, 0)} % less than simply repeating normal weather, and its 90 % band was right ${num(best.coverage90_recent * 100, 0)} % of the time. Beyond ${horizon} ${horizon === 1 ? 'month' : 'months'} the test does not justify publishing a forecast.`)}</p>}
  </section>
}

function RainSection({ data, initial }: { data: PredictionsData; initial: RegionId }) {
  const [region, setRegion] = useState<RegionId>(initial)
  const rows = data.variables.PRECTOTCORR.regions[region].rows
  const analog = data.rain_analog[region]
  const criterion = analog ? fromData(analog.criterion) : ''
  return <section className="section band" id="lluvia" aria-labelledby="rain-title">
    <div className="section-head reveal">
      <span className="eyebrow">{t('Referencia histórica', 'Historical reference')}</span>
      <h2 id="rain-title">{t('Lluvia de los próximos meses', 'Rain for the coming months')}</h2>
      <p className="lead">{t('Todavía no hay un pronóstico de lluvia que haya pasado la validación. Lo que sí se puede mostrar es cuánto llueve normalmente cada mes y cuánto llovió en los años en que El Niño estaba como ahora.',
        'There is not yet a rain forecast that has passed validation. What can be shown is how much it normally rains each month and how much it rained in the years when El Niño was like now.')}</p>
    </div>
    <div className="pred-panel reveal">
      <div className="pred-panel-head"><RegionTabs value={region} onChange={setRegion} label={t('Sector de la referencia de lluvia', 'Sector of the rain reference')} />
        <div className="legend-inline"><span><i className="sw rain" />{t('Lo normal (8 de cada 10 años)', 'Normal (8 out of 10 years)')}</span><span><i className="sw tickmark" />{t('Promedio normal', 'Normal average')}</span><span><i className="sw diamond" />{t('Años parecidos de El Niño (rojo: llovió más de 5 % menos)', 'Similar El Niño years (red: it rained more than 5 % less)')}</span></div></div>
      <RainChart key={region} rows={rows} analog={analog?.months ?? []} />
    </div>
    <div className="table-wrap reveal"><table className="pred-table">
      <caption>{REGION_SHORT[region]} · {t('lluvia mensual (mm)', 'monthly rainfall (mm)')}</caption>
      <thead><tr><th>{t('Mes', 'Month')}</th><th>{t('Lo normal (P10–P90)', 'Normal (P10–P90)')}</th><th>{t('En años parecidos de El Niño', 'In similar El Niño years')}</th><th>{t('Años con 100 mm o más', 'Years with 100 mm or more')}</th></tr></thead>
      <tbody>{rows.map(row => {
        const found = analog?.months.find(item => item.month === row.target_month)
        return <tr key={row.target_month}>
          <th scope="row">{monthLong(row.target_month)}</th>
          <td>{num(row.reference.mean, 0)} ({num(row.reference.p10, 0)}–{num(row.reference.p90, 0)})</td>
          <td>{found ? `${num(found.mean_mm, 0)} mm (${signed(found.anomaly_pct, 0)} %)` : '—'}</td>
          <td>{found ? t(`${Math.round(found.share_above_100mm * found.n_years)} de ${found.n_years}`, `${Math.round(found.share_above_100mm * found.n_years)} of ${found.n_years}`) : '—'}</td>
        </tr>
      })}</tbody>
    </table></div>
    {analog && <p className="muted note reveal">{t(
      `Años parecidos: ${criterion.charAt(0).toLowerCase() + criterion.slice(1)} (${analog.years.join(', ')}). Son pocos años y no hay una prueba de significancia: sirve como contexto, no como promesa de lluvia.`,
      `Similar years: ${criterion.charAt(0).toLowerCase() + criterion.slice(1)} (${analog.years.join(', ')}). They are few years and there is no significance test: it serves as context, not as a promise of rain.`)}</p>}
  </section>
}

function MoreData({ data }: { data: PredictionsData }) {
  const analog = data.enso.analog
  const reference = (variable: 'RH2M' | 'UV') => data.variables[variable]
  return <section className="section" id="mas-datos" aria-labelledby="extra-title">
    <div className="section-head reveal">
      <span className="eyebrow">{t('Datos secundarios', 'Secondary data')}</span>
      <h2 id="extra-title">{t('Más datos para quien quiere profundizar', 'More data for those who want to dig deeper')}</h2>
      <p className="lead">{t('Referencias de humedad y radiación UV, qué tan confiable es la temperatura y los episodios de El Niño que sirvieron de comparación.',
        'Humidity and UV radiation references, how reliable the temperature forecast is, and the El Niño episodes used as a comparison.')}</p>
    </div>
    <div className="more-grid">
      {(['RH2M', 'UV'] as const).map((variable, index) => {
        const block = reference(variable)
        return <article key={variable} className="card more-card reveal" style={stagger(index)}>
          <h3>{variable === 'RH2M' ? t('Humedad relativa del aire', 'Relative humidity of the air') : t('Radiación UV (NASA POWER)', 'UV radiation (NASA POWER)')}</h3>
          <p className="muted">{variable === 'RH2M' ? t('Referencia 1991–2020 (%)', 'Reference 1991–2020 (%)') : t('Índice UV medio de 24 horas, 2001–2024. Incluye la noche: no es el índice del mediodía.', '24-hour mean UV index, 2001–2024. It includes the night: it is not the midday index.')} {t('Sin pronóstico validado.', 'No validated forecast.')}</p>
          <div className="table-wrap"><table className="pred-table compact">
            <thead><tr><th>{t('Mes', 'Month')}</th>{REGIONS.map(region => <th key={region}>{REGION_SHORT[region]}</th>)}</tr></thead>
            <tbody>{block.regions.CR.rows.map((row, i) => <tr key={row.target_month}>
              <th scope="row">{monthOnly(row.target_month)} {row.target_month.slice(2, 4)}</th>
              {REGIONS.map(region => { const ref = block.regions[region].rows[i].reference; return <td key={region}>{num(ref.mean, variable === 'UV' ? 2 : 1)}</td> })}
            </tr>)}</tbody>
          </table></div>
        </article>
      })}
      <article className="card more-card reveal" style={stagger(2)}>
        <h3>{t('Qué tan confiable es la temperatura', 'How reliable the temperature forecast is')}</h3>
        <p className="muted">{t('Mejora frente a repetir el clima normal, en la prueba con años pasados (cuanto más a la derecha, mejor).', 'Improvement over repeating normal weather, in the test with past years (the further right, the better).')}</p>
        <div className="meters">
          {REGIONS.flatMap(region => Object.entries(data.temperature_validation[`CDS/${region}/T2M`]?.horizons ?? {}).map(([horizon, info]) => ({ region, horizon, info })))
            .map(({ region, horizon, info }, index) => <div key={`${region}${horizon}`} className="meter-row" style={stagger(index)}>
              <span>{REGION_SHORT[region]} · {t('mes', 'month')} {horizon}</span>
              <div className="meter good"><span style={meter(info.test_skill * 100)} /></div>
              <strong>{num(info.test_skill * 100, 0)} %</strong>
            </div>)}
        </div>
      </article>
      {analog && <article className="card more-card reveal" style={stagger(3)}>
        <h3>{t('Episodios fuertes que sirvieron de comparación', 'Strong episodes used as a comparison')}</h3>
        <p className="muted">{t(`Cuánto duraron los ${analog.n} episodios de El Niño con RONI máximo de 1,5 o más (en meses).`, `How long the ${analog.n} El Niño episodes with a peak RONI of 1.5 or more lasted (in months).`)}</p>
        <div className="meters">
          {analog.events.map((event, index) => <div key={event.start} className="meter-row" style={stagger(index)}>
            <span>{event.start.slice(0, 4)} – {event.end.slice(0, 4)}</span>
            <div className="meter nino"><span style={meter((event.months / 20) * 100)} /></div>
            <strong>{event.months}</strong>
          </div>)}
        </div>
      </article>}
    </div>
  </section>
}

/** Todo el detalle numérico: tarjetas con cifras, calendario de El Niño y tablas y gráficos por sector. */
export function NumericData({ data, region }: { data: PredictionsData; region: RegionId }) {
  return <div id="datos-contenido">
    <section className="section" aria-labelledby="num-title">
      <div className="section-head reveal">
        <span className="eyebrow">{t('Datos numéricos', 'Numeric data')}</span>
        <h2 id="num-title">{t('Las cifras detrás del resumen', 'The figures behind the summary')}</h2>
        <p className="lead">{t('Para quien quiere ver los números, los gráficos y las tablas. Todo es regional y experimental.', 'For those who want to see the numbers, charts and tables. Everything is regional and experimental.')}</p>
      </div>
      <div className="pred-top"><NinoCard data={data} /><TemperatureCard data={data} /><RainCard data={data} /></div>
    </section>

    <section className="section" id="fechas" aria-labelledby="dates-title">
      <div className="section-head reveal">
        <span className="eyebrow">{t('Rango de fechas', 'Date range')}</span>
        <h2 id="dates-title">{t('El Niño en el calendario', 'El Niño on the calendar')}</h2>
        <p className="lead">{t(`El RONI ya superó el umbral de 0,5 desde ${data.enso.start ? monthLong(data.enso.start) : 'antes'}. Los rangos de pico y de fin comparan con los episodios fuertes anteriores: marcan lo que suele pasar, no una fecha segura.`,
          `The RONI has been above the 0.5 threshold since ${data.enso.start ? monthLong(data.enso.start) : 'before'}. The peak and end ranges compare with earlier strong episodes: they show what usually happens, not a sure date.`)}</p>
      </div>
      <div className="pred-panel reveal"><EnsoTimeline enso={data.enso} /></div>
      <p className="muted note reveal">{fromData(data.enso.definition)} {t(`Los datos del RONI llegan hasta ${monthLong(data.roni_through)}; la línea no se proyecta hacia adelante.`, `The RONI data run through ${monthLong(data.roni_through)}; the line is not projected forward.`)}</p>
    </section>

    <TemperatureSection key={`t${region}`} data={data} initial={region} />
    <RainSection key={`r${region}`} data={data} initial={region} />
    <MoreData data={data} />
  </div>
}
