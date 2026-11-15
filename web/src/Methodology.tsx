import { useEffect, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { locale, t, tx } from './i18n'
import { LangSwitch } from './LangSwitch'
import { REGIONS, REGION_SHORT, ensoCategory, fromData, getPredictions, monthLong, monthShort, num } from './predictionsData'
import type { Predictions, RegionId } from './predictionsData'
import { useReveal } from './useReveal'

/** Enlace a la explicación completa. Con `print`, la página abre el diálogo de impresión («Guardar como PDF») al cargar. */
export const methodUrl = (print = false) => `${window.location.pathname}?pagina=metodologia${print ? '&imprimir=1' : ''}`

const pct = (value: number) => `${num(value * 100, 0)} %`
const dateLong = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString(locale(), { dateStyle: 'long' })

/** Los seis modelos que compite el motor, con una frase que cualquiera entienda. */
const models = (): Record<string, { name: string; text: string }> => ({
  clim10: { name: t('Promedio de 10 años', '10-year average'), text: t('Repite el promedio de ese mes en los últimos 10 años.', 'Repeats the average of that month over the last 10 years.') },
  clim30: { name: t('Promedio de 30 años', '30-year average'), text: t('Repite el promedio de ese mes en los últimos 30 años.', 'Repeats the average of that month over the last 30 years.') },
  seasonal_naive: { name: t('Mismo mes del año pasado', 'Same month last year'), text: t('Repite lo que pasó en ese mismo mes un año antes.', 'Repeats what happened in that same month a year earlier.') },
  trend20: { name: t('Ciclo del año + tendencia', 'Yearly cycle + trend'), text: t('Calcula el valor típico de cada mes en los últimos 20 años y le suma la tendencia lineal de esos años.', 'Computes the typical value of each month over the last 20 years and adds the linear trend of those years.') },
  trend20_ar1: { name: t('Ciclo + tendencia + inercia', 'Cycle + trend + inertia'), text: t('Lo anterior, más la «inercia»: cuánto se aleja el último mes de lo típico, con un peso que baja a medida que pasan los meses.', 'The above, plus “inertia”: how far the last month is from the typical value, with a weight that fades as months go by.') },
  trend20_enso_direct: { name: t('Ciclo + tendencia + inercia + El Niño', 'Cycle + trend + inertia + El Niño'), text: t('Ciclo y tendencia de 20 años, corregidos con una regresión (con penalización para no sobreajustar) que usa la desviación del último mes y el RONI del mes anterior.', '20-year cycle and trend, corrected with a regression (penalized to avoid overfitting) that uses the last month’s deviation and the previous month’s RONI.') },
})

function Pdf({ label }: { label?: string }) {
  return <div className="pdf-box no-print">
    <a className="pill pill-primary" href={methodUrl(true)} target="_blank" rel="noopener">{label ?? t('Descargar la explicación completa (PDF)', 'Download the full explanation (PDF)')} <span aria-hidden="true">⤓</span></a>
    <small className="muted">{t('Se abre la explicación completa y el navegador ofrece guardarla: en el diálogo de impresión elegí «Guardar como PDF».', 'The full explanation opens and the browser offers to save it: in the print dialog choose “Save as PDF”.')}</small>
  </div>
}

// ------------------------------------------------------------------ Versión simple (panel de la página de predicciones)

/** Explicación sencilla del análisis estadístico, con las cifras reales de la última corrida. */
export function MethodSimple({ data }: { data: Predictions }) {
  const skill = data.temperature_validation['CDS/CR/T2M']?.horizons['1']
  const strong = data.enso.analog?.n
  const years = data.rain_analog.CR?.years.length
  const steps: { title: string; text: ReactNode }[] = [
    { title: t('Juntamos datos de varias fuentes', 'We gather data from several sources'), text: t('La temperatura, la lluvia y la humedad vienen de mediciones y modelos del clima que Copernicus (Unión Europea) y la NASA publican desde 1981. El Niño se sigue con el índice RONI de la agencia estadounidense NOAA, que dice qué tan caliente está el océano Pacífico.',
      'Temperature, rain and humidity come from climate measurements and models that Copernicus (European Union) and NASA have published since 1981. El Niño is tracked with the RONI index from the US agency NOAA, which says how warm the Pacific Ocean is.') },
    { title: t('Definimos qué es «lo normal»', 'We define what “normal” is'), text: t('Para cada mes miramos cómo fue entre 1991 y 2020. Lo «normal» es el promedio y el rango en el que cayó 8 de cada 10 años. Así podemos decir si un mes se espera más caliente, más fresco, más seco o más lluvioso de lo habitual.',
      'For each month we look at how it was between 1991 and 2020. “Normal” is the average and the range where 8 out of 10 years fell. That lets us say whether a month is expected to be warmer, cooler, drier or rainier than usual.') },
    { title: t('Calculamos el calor de los próximos meses', 'We calculate the heat for the coming months'), text: t('Un modelo estadístico aprende cómo cambia la temperatura a lo largo del año, cuánto ha subido en las últimas dos décadas y qué tan lejos de lo típico estuvo el último mes. Con eso estima los próximos meses y dibuja una banda donde esperamos que caiga la temperatura 9 de cada 10 veces.',
      'A statistical model learns how temperature changes through the year, how much it has risen over the last two decades and how far from typical the last month was. With that it estimates the coming months and draws a band where we expect the temperature to fall 9 out of 10 times.') },
    { title: t('Comprobamos si el pronóstico sirve', 'We check whether the forecast works'), text: tx(
      <>Antes de publicar, «escondemos» años pasados y vemos si el modelo los habría adivinado. {skill ? <>Para el mes siguiente, el modelo se equivocó {pct(skill.test_skill)} menos que repetir el clima normal, y su banda de 90 % acertó {pct(skill.coverage90_recent)} de las veces. </> : null}Solo publicamos un pronóstico hasta donde esa prueba lo respalda; más lejos mostramos únicamente lo normal.</>,
      <>Before publishing, we “hide” past years and see whether the model would have guessed them. {skill ? <>For the next month, the model was off {pct(skill.test_skill)} less than repeating normal weather, and its 90 % band was right {pct(skill.coverage90_recent)} of the time. </> : null}We only publish a forecast as far as that test backs it; beyond that we show only what is normal.</>) },
    { title: t('Para la lluvia miramos el pasado', 'For rain we look at the past'), text: t(`Todavía no hay un pronóstico de lluvia que pase esa prueba. Por eso buscamos los ${years ?? 'varios'} años en que El Niño estuvo parecido al actual y mostramos cuánto llovió entonces frente a lo normal. Son pocos años: es contexto, no una promesa.`,
      `There is not yet a rain forecast that passes that test. So we look for the ${years ?? 'several'} years when El Niño was similar to the current one and show how much it rained then compared with normal. It is few years: it is context, not a promise.`) },
    { title: t('Seguimos a El Niño', 'We follow El Niño'), text: t(`Damos por confirmado un episodio cuando el RONI se mantiene en 0,5 o más durante 5 meses seguidos. Para estimar cuándo llegará al máximo y cuándo terminará comparamos con los ${strong ?? 'otros'} episodios fuertes anteriores. Marca lo que suele pasar, no una fecha segura.`,
      `We consider an episode confirmed when the RONI stays at 0.5 or more for 5 months in a row. To estimate when it will peak and when it will end, we compare with the ${strong ?? 'other'} earlier strong episodes. It shows what usually happens, not a sure date.`) },
    { title: t('Pasamos del país a tu zona', 'We go from the country to your area'), text: t('El mapa de la NASA divide el país en cuadros de unos 55 × 70 km. Tu cantón (o el cantón de tu ASADA) usa el cuadro que más lo cubre. Si ese cuadro está en el Pacífico Norte o en el Caribe usamos los datos de esa zona; si no, el promedio del país. Aún no hay cálculos por cantón.',
      'The NASA map divides the country into cells of about 55 × 70 km. Your canton (or your ASADA’s canton) uses the cell that covers most of it. If that cell is in the North Pacific or the Caribbean we use that area’s data; otherwise, the national average. There are no per-canton calculations yet.') },
  ]
  return <section className="section" aria-labelledby="method-title">
    <div className="section-head reveal">
      <span className="eyebrow">{t('Análisis estadístico de AguaAlerta', "AguaAlerta's statistical analysis")}</span>
      <h2 id="method-title">{t('Cómo obtenemos estos datos', 'How we obtain this data')}</h2>
      <p className="lead">{t('En siete pasos y sin fórmulas. Para el detalle completo (modelos, pruebas y cifras) hay una versión en PDF.', 'In seven steps and without formulas. For the full detail (models, tests and figures) there is a PDF version.')}</p>
    </div>
    <ol className="method-steps">
      {steps.map((step, index) => <li key={index} className="reveal" style={{ '--i': index } as CSSProperties}>
        <span className="method-n" aria-hidden="true">{index + 1}</span>
        <div><h3>{step.title}</h3><p>{step.text}</p></div>
      </li>)}
    </ol>
    <div className="method-limits reveal">
      <h3>{t('Para leer con cuidado', 'To read with care')}</h3>
      <ul className="facts">{data.limits.map(limit => <li key={limit}>{fromData(limit)}</li>)}</ul>
    </div>
    <Pdf />
  </section>
}

// ------------------------------------------------------------------ Explicación completa (para imprimir o guardar como PDF)

function Table({ caption, head, rows }: { caption: string; head: string[]; rows: ReactNode[][] }) {
  return <div className="table-wrap"><table className="pred-table">
    <caption>{caption}</caption>
    <thead><tr>{head.map(item => <th key={item}>{item}</th>)}</tr></thead>
    <tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, i) => i === 0 ? <th key={i} scope="row">{cell}</th> : <td key={i}>{cell}</td>)}</tr>)}</tbody>
  </table></div>
}

function Full({ data }: { data: Predictions }) {
  const t2m = data.variables.T2M
  const catalog = models()
  const chosen = REGIONS.map(region => ({ region, model: t2m.regions[region].model ?? '' }))
  const rain = data.rain_analog.CR
  const rainRows = data.variables.PRECTOTCORR.regions.CR.rows
  const events = data.enso.analog?.events ?? []
  const validation = REGIONS.flatMap(region => Object.entries(data.temperature_validation[`CDS/${region}/T2M`]?.horizons ?? {}).map(([horizon, info]) => ({ region, horizon, info })))
  const cellList = (region: Exclude<RegionId, 'CR'>) => data.region_cells[region].map(cell => cell.replace('POWER:', '').replace(':', ' / ')).join(' · ')
  const criterion = rain ? fromData(rain.criterion) : ''
  return <article className="method-doc">
    <section>
      <h2>{t('1. Qué es esta página y qué no es', '1. What this page is and is not')}</h2>
      <p>{tx(
        <>Las predicciones de AguaAlerta son <strong>experimentales</strong>. Solo la temperatura tiene un pronóstico, y solo para los primeros meses, porque es lo único que pasó una prueba con años pasados. La lluvia, la humedad y la radiación UV se muestran como referencia histórica, y las fechas de El Niño comparan con episodios anteriores. Todo es <strong>regional</strong> (todo el país, Pacífico Norte y Caribe): no hay pronóstico por cantón, por cuadro del mapa ni por ASADA.</>,
        <>AguaAlerta’s predictions are <strong>experimental</strong>. Only temperature has a forecast, and only for the first months, because it is the only thing that passed a test with past years. Rain, humidity and UV radiation are shown as a historical reference, and the El Niño dates compare with earlier episodes. Everything is <strong>regional</strong> (the whole country, North Pacific and Caribbean): there is no forecast per canton, per map cell or per ASADA.</>)}</p>
      <p>{t('No reemplaza los avisos del Instituto Meteorológico Nacional (IMN), del AyA ni de cada ASADA, y no debe usarse para decidir racionamientos ni otras acciones operativas.',
        'It does not replace the notices from the Instituto Meteorológico Nacional (IMN), the AyA or each ASADA, and it must not be used to decide water rationing or other operational actions.')}</p>
    </section>

    <section>
      <h2>{t('2. Fuentes de datos', '2. Data sources')}</h2>
      <Table caption={t('Datos que usa el análisis', 'Data used by the analysis')} head={[t('Dato', 'Data'), t('Fuente', 'Source'), t('Período', 'Period'), t('Para qué se usa', 'What it is used for')]} rows={[
        [t('Temperatura del aire a 2 m, lluvia y humedad relativa', 'Air temperature at 2 m, rain and relative humidity'), t('Copernicus Climate Data Store, reanálisis ERA5-Land (0,1°, unos 11 km)', 'Copernicus Climate Data Store, ERA5-Land reanalysis (0.1°, about 11 km)'), `1981 – ${monthLong(data.data_through)}`, t('Pronóstico de temperatura, referencia de lo normal, años parecidos de El Niño', 'Temperature forecast, reference for what is normal, similar El Niño years')],
        [t('Radiación UV (índice medio de 24 horas)', 'UV radiation (24-hour mean index)'), 'NASA POWER', '2001 – 2024', t('Solo referencia estacional', 'Seasonal reference only')],
        [t('Mapa de cuadros por cantón', 'Map of grid cells per canton'), t('NASA POWER, cuadros de 0,5° × 0,625° (≈ 55 × 69 km)', 'NASA POWER, cells of 0.5° × 0.625° (≈ 55 × 69 km)'), '—', t('Decidir qué zona le toca a un cantón', 'Deciding which area a canton belongs to')],
        [t('El Niño: RONI (Relative Oceanic Niño Index)', 'El Niño: RONI (Relative Oceanic Niño Index)'), 'NOAA, Climate Prediction Center', t(`hasta ${monthLong(data.roni_through)}`, `through ${monthLong(data.roni_through)}`), t('Episodio en curso y comparación con episodios anteriores', 'Current episode and comparison with earlier episodes')],
      ]} />
      <p>{tx(
        <>Los datos de reanálisis son estimaciones de un modelo del clima que incorpora observaciones: <strong>no son mediciones de una estación en un punto</strong>. En lluvia y en zonas montañosas pueden diferir de lo que mide un pluviómetro local. La lluvia se acumula por mes (mm/mes) multiplicando la tasa diaria por los días del mes.</>,
        <>Reanalysis data are estimates from a climate model that incorporates observations: <strong>they are not measurements from a station at one point</strong>. For rain and in mountainous areas they can differ from what a local rain gauge measures. Rain is accumulated per month (mm/month) by multiplying the daily rate by the days in the month.</>)}</p>
    </section>

    <section>
      <h2>{t('3. Zonas: país, Pacífico Norte y Caribe', '3. Areas: country, North Pacific and Caribbean')}</h2>
      <p>{tx(
        <>Cada serie mensual es un promedio de varios cuadros del mapa. El promedio nacional pondera cada cuadro por el coseno de su latitud y por la fracción de tierra que contiene. Los dos sectores son cajas didácticas, <strong>no son límites oficiales</strong> de Guanacaste ni de Limón; los cuadros costeros incluyen algo de mar.</>,
        <>Each monthly series is an average of several map cells. The national average weights each cell by the cosine of its latitude and by the fraction of land it contains. The two sectors are didactic boxes, <strong>not official boundaries</strong> of Guanacaste or Limón; coastal cells include some sea.</>)}</p>
      <Table caption={t('Zonas con cálculo propio', 'Areas with their own calculation')} head={[t('Zona', 'Area'), t('Cuadros (latitud / longitud)', 'Cells (latitude / longitude)')]} rows={[
        [REGION_SHORT.CR, t('Todos los cuadros con tierra de la malla nacional (24 cuadros)', 'All the cells with land in the national grid (24 cells)')],
        [REGION_SHORT.CR_PN, cellList('CR_PN')],
        [REGION_SHORT.CR_CAR, cellList('CR_CAR')],
      ]} />
      <h3>{t('De un cantón (o una ASADA) a su zona', 'From a canton (or an ASADA) to its area')}</h3>
      <p>{t('Cada cantón usa el cuadro NASA POWER que ocupa la mayor parte de su territorio (se calcula intersectando los polígonos). Una ASADA usa el cuadro de su cantón. Si ese cuadro está en la lista del Pacífico Norte o del Caribe, el resumen usa los datos de esa zona; si no, usa el promedio del país. Por eso algunos cantones de San José, Heredia y todos los de Cartago caen en la zona «Caribe»: es lo que dice la cuadrícula, no un límite administrativo. Una consecuencia es que el resumen de un cantón puede coincidir con el de otro, y que no refleja diferencias locales dentro de un cuadro de 55 × 69 km.',
        'Each canton uses the NASA POWER cell that covers most of its territory (computed by intersecting the polygons). An ASADA uses the cell of its canton. If that cell is in the North Pacific or Caribbean list, the summary uses that area’s data; otherwise it uses the national average. That is why some cantons in San José, Heredia and all those in Cartago fall in the “Caribbean” area: it is what the grid says, not an administrative boundary. One consequence is that one canton’s summary can match another’s, and that it does not reflect local differences within a 55 × 69 km cell.')}</p>
    </section>

    <section>
      <h2>{t('4. «Lo normal»', '4. “Normal”')}</h2>
      <p>{tx(
        <>Para cada mes del año se toma la distribución de los años 1991–2020 (2001–2024 en UV): el promedio, el percentil 10 (P10) y el percentil 90 (P90). El rango P10–P90 es donde cayó 8 de cada 10 años. Es una descripción del pasado, <strong>no un intervalo de predicción</strong>. La «diferencia con lo normal» que se muestra es la estimación menos el promedio de ese mes, con las cifras redondeadas tal como se ven.</>,
        <>For each month of the year, the distribution of the years 1991–2020 (2001–2024 for UV) is taken: the average, the 10th percentile (P10) and the 90th percentile (P90). The P10–P90 range is where 8 out of 10 years fell. It is a description of the past, <strong>not a prediction interval</strong>. The “difference from normal” shown is the estimate minus that month’s average, using the rounded figures as displayed.</>)}</p>
    </section>

    <section>
      <h2>{t('5. Pronóstico de temperatura', '5. Temperature forecast')}</h2>
      <p>{tx(<>El motor <code>hefesto_forecast</code> compara seis modelos sencillos para cada serie y horizonte:</>, <>The <code>hefesto_forecast</code> engine compares six simple models for each series and horizon:</>)}</p>
      <Table caption={t('Modelos candidatos', 'Candidate models')} head={[t('Modelo', 'Model'), t('Qué hace', 'What it does')]} rows={Object.values(catalog).map(value => [value.name, value.text])} />
      <p>{t(`En la última calibración (${dateLong(data.calibration_date)}) el modelo elegido fue:`, `In the latest calibration (${dateLong(data.calibration_date)}) the chosen model was:`)}</p>
      <Table caption={t('Modelo elegido para la temperatura', 'Model chosen for temperature')} head={[t('Zona', 'Area'), t('Modelo', 'Model')]} rows={chosen.map(({ region, model }) => [REGION_SHORT[region], catalog[model]?.name ?? model])} />
      <h3>{t('Banda de 90 %', '90 % band')}</h3>
      <p>{t('La banda es la estimación ± un múltiplo (q90) de la variabilidad de ese mes en los últimos 20 años. El múltiplo se calibró con años que el modelo no vio, de modo que la banda cubra cerca del 90 % de lo observado. El «80 % de los años» de las gráficas no es lo mismo: ese es el rango normal histórico (P10–P90).',
        'The band is the estimate ± a multiple (q90) of that month’s variability over the last 20 years. The multiple was calibrated with years the model did not see, so that the band covers about 90 % of what was observed. The “80 % of years” in the charts is not the same thing: that is the historical normal range (P10–P90).')}</p>
    </section>

    <section>
      <h2>{t('6. Cómo se comprueba que el pronóstico sirve', '6. How we check that the forecast works')}</h2>
      <p>{t('El motor se prueba con años pasados: se simula cada mes como si fuera el momento de emitir el pronóstico, usando solo los datos disponibles hasta entonces, y se compara con lo que realmente pasó. Los resultados clave son:',
        'The engine is tested with past years: each month is simulated as if it were the moment of issuing the forecast, using only the data available up to then, and compared with what actually happened. The key results are:')}</p>
      <ul>
        <li>{tx(<><strong>Habilidad (skill):</strong> 1 − (error absoluto medio del modelo ÷ error absoluto medio de repetir lo normal). 0 % es empatar con «lo normal»; 100 % sería no equivocarse nunca; un valor negativo, peor que lo normal.</>,
          <><strong>Skill:</strong> 1 − (mean absolute error of the model ÷ mean absolute error of repeating normal). 0 % is tying with “normal”; 100 % would be never being wrong; a negative value, worse than normal.</>)}</li>
        <li>{tx(<><strong>Cobertura de la banda de 90 %:</strong> la fracción de meses recientes en que lo observado cayó dentro de la banda. Lo esperado es cerca de 90 %.</>,
          <><strong>Coverage of the 90 % band:</strong> the fraction of recent months in which the observed value fell inside the band. About 90 % is expected.</>)}</li>
        <li>{tx(<><strong>Horizonte máximo:</strong> el número de meses hasta donde la habilidad sigue siendo positiva de forma continua. Más allá no se publica ninguna estimación.</>,
          <><strong>Maximum horizon:</strong> the number of months up to which skill stays continuously positive. Beyond that no estimate is published.</>)}</li>
        <li>{tx(<><strong>Incertidumbre de la habilidad:</strong> la prueba tiene pocos bloques de años (cuatro años retenidos), así que se calcula un intervalo de confianza de 95 % para la habilidad. Si incluye el cero, el resultado se marca como incierto.</>,
          <><strong>Uncertainty of the skill:</strong> the test has few blocks of years (four held-out years), so a 95 % confidence interval is computed for the skill. If it includes zero, the result is marked as uncertain.</>)}</li>
      </ul>
      <Table caption={t('Resultados de la prueba (temperatura)', 'Test results (temperature)')}
        head={[t('Zona', 'Area'), t('Mes adelante', 'Months ahead'), t('Habilidad', 'Skill'), t('Intervalo 95 % de la habilidad', '95 % interval of the skill'), t('Cobertura banda 90 %', '90 % band coverage'), t('Observación', 'Remark')]}
        rows={validation.map(({ region, horizon, info }) => [REGION_SHORT[region], horizon, pct(info.test_skill),
          info.skill_ci95 ? t(`${pct(info.skill_ci95[0])} a ${pct(info.skill_ci95[1])}`, `${pct(info.skill_ci95[0])} to ${pct(info.skill_ci95[1])}`) : '—',
          pct(info.coverage90_recent), info.skill_uncertain ? t('Habilidad incierta', 'Uncertain skill') : t('Habilidad positiva', 'Positive skill')])} />
      <p>{tx(<>Además, los datos de entrada llevan una huella digital (SHA-256): si cambian, el motor se niega a responder hasta repetir toda la prueba, para que nunca se publique un modelo que no fue validado con los datos actuales. La evidencia completa está en <code>docs/forecast_evidencia/</code>.</>,
        <>In addition, the input data carry a digital fingerprint (SHA-256): if they change, the engine refuses to answer until the whole test is repeated, so that a model that was not validated with the current data is never published. The full evidence is in <code>docs/forecast_evidencia/</code>.</>)}</p>
    </section>

    <section>
      <h2>{t('7. Lluvia, humedad y UV: referencia, no pronóstico', '7. Rain, humidity and UV: reference, not forecast')}</h2>
      <p>{tx(<>En los meses que se muestran, la lluvia y la humedad no superaron la prueba contra repetir lo normal, y el UV no se pronostica (su serie llega hasta 2024). Por eso <strong>no se publica pronóstico</strong> de estas variables: solo lo normal de cada mes.</>,
        <>For the months shown, rain and humidity did not pass the test against repeating normal, and UV is not forecast (its series ends in 2024). That is why <strong>no forecast is published</strong> for these variables: only what is normal for each month.</>)}</p>
      {rain && <>
        <h3>{t('Años parecidos de El Niño (lluvia)', 'Similar El Niño years (rain)')}</h3>
        <p>{t(`${criterion}: ${rain.years.join(', ')} (${rain.years.length} años). Para cada mes se promedia la lluvia de esos años y se compara con lo normal. No se hace una prueba de significancia: con tan pocos años, es solo contexto histórico.`,
          `${criterion}: ${rain.years.join(', ')} (${rain.years.length} years). For each month the rainfall of those years is averaged and compared with normal. No significance test is done: with so few years, it is only historical context.`)}</p>
        <Table caption={`${REGION_SHORT.CR} · ${t('lluvia mensual (mm)', 'monthly rainfall (mm)')}`} head={[t('Mes', 'Month'), t('Lo normal (promedio)', 'Normal (average)'), t('En años parecidos', 'In similar years'), t('Diferencia', 'Difference')]}
          rows={rain.months.map(item => [monthLong(item.month), `${num(item.reference_mean_mm, 0)} mm`, `${num(item.mean_mm, 0)} mm`, `${item.anomaly_pct < 0 ? '−' : '+'}${num(Math.abs(item.anomaly_pct), 0)} %`])} />
        <p className="muted">{t(`Los primeros meses del pronóstico son ${rainRows.slice(0, 2).map(row => monthLong(row.target_month)).join(' y ')}.`, `The first months of the forecast are ${rainRows.slice(0, 2).map(row => monthLong(row.target_month)).join(' and ')}.`)}</p>
      </>}
    </section>

    <section>
      <h2>{t('8. El Niño: inicio, pico y fin', '8. El Niño: start, peak and end')}</h2>
      <p>{t('El RONI es la anomalía de la temperatura del mar en la región Niño 3.4 del Pacífico, restando el calentamiento general de los trópicos. ', 'The RONI is the anomaly of sea temperature in the Niño 3.4 region of the Pacific, subtracting the general warming of the tropics. ')}{fromData(data.enso.definition)}</p>
      <ul>
        <li>{tx(<><strong>Inicio:</strong> es un dato, no una predicción: el primer mes en que empezó la racha de RONI ≥ 0,5.</>, <><strong>Start:</strong> it is a data point, not a prediction: the first month of the streak of RONI ≥ 0.5.</>)}</li>
        <li>{tx(<><strong>Categoría:</strong> según el valor máximo del RONI (débil, moderado, fuerte, muy fuerte).</>, <><strong>Category:</strong> according to the peak RONI value (weak, moderate, strong, very strong).</>)}</li>
        <li>{tx(<><strong>Pico y fin:</strong> se comparan con los episodios fuertes anteriores (RONI máximo de 1,5 o más). Se toman los percentiles 10, 50 y 90 de cuándo llegaron al máximo y de cuánto duraron.</>,
          <><strong>Peak and end:</strong> they are compared with earlier strong episodes (peak RONI of 1.5 or more). The 10th, 50th and 90th percentiles of when they peaked and how long they lasted are taken.</>)}</li>
      </ul>
      {events.length > 0 && <Table caption={t('Episodios fuertes que sirven de comparación', 'Strong episodes used as a comparison')} head={[t('Inicio', 'Start'), t('Fin', 'End'), t('Duración (meses)', 'Duration (months)'), t('RONI máximo', 'Peak RONI')]}
        rows={events.map(event => [monthShort(event.start), monthShort(event.end), event.months, num(event.peak)])} />}
      <p>{tx(<>No es un modelo dinámico del océano: <strong>no predice cuándo empezará un Niño nuevo</strong> y no asegura una fecha de fin. La línea del RONI llega hasta {monthLong(data.roni_through)} y no se proyecta.</>,
        <>It is not a dynamic ocean model: <strong>it does not predict when a new El Niño will start</strong> and it does not guarantee an end date. The RONI line runs through {monthLong(data.roni_through)} and is not projected.</>)}</p>
      {data.enso.category && <p className="muted">{t(`Categoría del episodio actual: ${ensoCategory(data.enso.category)}.`, `Category of the current episode: ${ensoCategory(data.enso.category)}.`)}</p>}
    </section>

    <section>
      <h2>{t('9. Límites que conviene recordar', '9. Limits worth remembering')}</h2>
      <ul>{data.limits.map(limit => <li key={limit}>{fromData(limit)}</li>)}
        <li>{t('Los datos de reanálisis pueden diferir de las estaciones locales; no hay validación contra estaciones del IMN.', 'Reanalysis data can differ from local stations; there is no validation against IMN stations.')}</li>
        <li>{t('Un cuadro del mapa mezcla mar y tierra y no distingue valles, laderas ni cuencas.', 'A map cell mixes sea and land and does not distinguish valleys, slopes or watersheds.')}</li>
        <li>{t('Pocos episodios de El Niño y pocos años de prueba: las cifras tienen incertidumbre que no se ve en un solo número.', 'Few El Niño episodes and few test years: the figures carry uncertainty that a single number does not show.')}</li>
        <li>{t('«No significativo» o «sin pronóstico» significa evidencia insuficiente, no que no vaya a pasar nada.', '“Not significant” or “no forecast” means insufficient evidence, not that nothing will happen.')}</li>
      </ul>
    </section>

    <section>
      <h2>{t('10. Glosario', '10. Glossary')}</h2>
      <Table caption={t('Términos', 'Terms')} head={[t('Término', 'Term'), t('Significado', 'Meaning')]} rows={[
        [t('Anomalía / diferencia con lo normal', 'Anomaly / difference from normal'), t('Cuánto se aleja un valor del promedio de ese mes.', 'How far a value is from that month’s average.')],
        [t('P10 y P90', 'P10 and P90'), t('Valores que dejan por debajo al 10 % y al 90 % de los años; entre ambos cae 8 de cada 10 años.', 'Values that leave 10 % and 90 % of the years below them; between the two fall 8 out of 10 years.')],
        [t('Banda de 90 %', '90 % band'), t('Rango donde se espera que caiga la temperatura el 90 % de las veces, según la prueba.', 'Range where the temperature is expected to fall 90 % of the time, according to the test.')],
        [t('Habilidad (skill)', 'Skill'), t('Cuánto mejora el modelo frente a repetir lo normal.', 'How much the model improves over repeating normal.')],
        ['RONI', t('Índice del océano Pacífico para medir El Niño y La Niña.', 'Pacific Ocean index used to measure El Niño and La Niña.')],
        [t('Años parecidos (análogos)', 'Similar years (analogs)'), t('Años pasados en que El Niño estuvo parecido al actual.', 'Past years when El Niño was similar to the current one.')],
        ['ERA5-Land', t('Reanálisis del servicio Copernicus: mezcla observaciones y un modelo del clima.', 'Reanalysis from the Copernicus service: it blends observations and a climate model.')],
        [t('Cuadro / celda', 'Cell / grid cell'), t('Un recuadro del mapa de NASA POWER (≈ 55 × 69 km).', 'A square of the NASA POWER map (≈ 55 × 69 km).')],
      ]} />
    </section>

    <section className="method-repro">
      <h2>{t('11. Cómo se reproduce', '11. How to reproduce it')}</h2>
      <p>{tx(<>Versión de esta explicación: cálculo del {dateLong(data.generated_at)}, calibración del {dateLong(data.calibration_date)}, datos hasta {monthLong(data.data_through)} y RONI hasta {monthLong(data.roni_through)}. Las cifras se regeneran con <code>python -m src.predictions</code>. El código y la evidencia están en el repositorio de AguaAlerta (<code>hefesto_forecast/</code>, <code>src/predictions.py</code>, <code>docs/predicciones.md</code>, <code>docs/forecast_evidencia/</code>).</>,
        <>Version of this explanation: calculated on {dateLong(data.generated_at)}, calibration of {dateLong(data.calibration_date)}, data through {monthLong(data.data_through)} and RONI through {monthLong(data.roni_through)}. The figures are regenerated with <code>python -m src.predictions</code>. The code and the evidence are in the AguaAlerta repository (<code>hefesto_forecast/</code>, <code>src/predictions.py</code>, <code>docs/predicciones.md</code>, <code>docs/forecast_evidencia/</code>).</>)}</p>
    </section>
  </article>
}

/** Página `?pagina=metodologia`: la explicación completa. Con `?imprimir=1` abre el diálogo de impresión para guardar el PDF. */
export function Methodology({ goBack }: { goBack: () => void }) {
  const [data, setData] = useState<Predictions>()
  const [failed, setFailed] = useState(false)
  useReveal([data])

  useEffect(() => {
    const controller = new AbortController()
    getPredictions(controller.signal).then(value => { if (!controller.signal.aborted) setData(value) })
      .catch(() => { if (!controller.signal.aborted) setFailed(true) })
    return () => controller.abort()
  }, [])

  // Con ?imprimir=1 se imprime una vez dibujado el documento (un respiro para que carguen las fuentes y las tablas).
  useEffect(() => {
    if (!data || new URLSearchParams(window.location.search).get('imprimir') !== '1') return
    const timer = setTimeout(() => window.print(), 600)
    return () => clearTimeout(timer)
  }, [data])

  return <div className="landing pred method">
    <nav className="landing-nav glass no-print" aria-label={t('Navegación principal', 'Main navigation')}>
      <a className="brand" href="." onClick={event => { event.preventDefault(); goBack() }}>AguaAlerta</a>
      <div className="nav-links" />
      <div className="nav-tools">
        <LangSwitch />
        <div className="segmented" role="group" aria-label={t('Acciones', 'Actions')}>
          <button onClick={goBack}>{t('← Volver a Predicciones', '← Back to Predictions')}</button>
          <button onClick={() => window.print()}>{t('Guardar como PDF', 'Save as PDF')}</button>
        </div>
      </div>
    </nav>
    <header className="method-head">
      <span className="eyebrow">{t('AguaAlerta · Predicciones experimentales', 'AguaAlerta · Experimental predictions')}</span>
      <h1>{t('Cómo calcula AguaAlerta sus predicciones', 'How AguaAlerta calculates its predictions')}</h1>
      <p className="lead">{t('Explicación completa del análisis estadístico: fuentes, modelos, pruebas de validación y límites.', 'Full explanation of the statistical analysis: sources, models, validation tests and limits.')}</p>
    </header>
    {data ? <main><Full data={data} /></main> : <p className="empty method-empty">{failed ? t('No se pudieron cargar los datos de la explicación. Generalos con «python -m src.predictions» y recargá la página.', 'Could not load the data for the explanation. Generate them with "python -m src.predictions" and reload the page.') : t('Cargando la explicación…', 'Loading the explanation…')}</p>}
    <footer className="landing-footer"><p><strong>AguaAlerta.</strong> {t('Predicciones experimentales. No reemplazan los avisos del IMN, el AyA ni de tu ASADA.', 'Experimental predictions. They do not replace the notices from the IMN, the AyA or your ASADA.')}</p></footer>
  </div>
}
