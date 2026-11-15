import { locale, t } from './i18n'

export type Level = 'basico' | 'tecnico'
export type Section = 'general' | 'temp' | 'precip' | 'uv' | 'humedad' | 'admin'
export type MapMode = 'grid' | 'cds' | 'cantones'
export type Alert = 'active' | 'expired' | 'none'

type Copy = {
  levelName: string
  sectionTip: Record<Section, string>
  mapTip: Record<MapMode, string>
  variableTitle: { T2M: string; PRECTOTCORR: string }
  unit: { T2M: string; PRECTOTCORR: string }
  trend: (slope: number | null, n: number, unit: string) => string
  significance: (significant: boolean | null) => string
  windows: string
  ensoTitle: string
  ensoBody: (start: string, end: string, unit: string) => string
  ensoUnknown: string
  tipSlope: string
  tipSignificance: string
  tipAnomaly: string
  tipCell: string
  tipRange: string
  technicalDetail: string
  alertLabel: Record<Alert, string>
  recommendationsTitle: string
  recommendations: string[]
  recommendationsNote: string
  confidenceRule: string
  aiNote: string
  forecastNote: string
}

/** Se arma al leerlo (no al cargar el módulo) para que los textos salgan siempre en el idioma activo. */
const basico = (): Copy => ({
  levelName: t('Explicación sencilla', 'Simple explanation'),
  sectionTip: {
    general: t('Resumen de El Niño y de la zona que elegiste.', 'Summary of El Niño and the area you chose.'),
    temp: t('Cómo ha cambiado el calor en la zona.', 'How the heat has changed in the area.'),
    precip: t('Cómo ha cambiado la lluvia en la zona.', 'How the rain has changed in the area.'),
    uv: t('Radiación UV: cuánta radiación del sol llega a la zona (tonos violetas en el mapa).', 'UV radiation: how much sun radiation reaches the area (violet tones on the map).'),
    humedad: t('Humedad del aire en la zona (tonos verdes en el mapa).', 'Air humidity in the area (green tones on the map).'),
    admin: t('Reportar el caudal de tu ASADA y cargar datos locales (solo administradores de ASADA).', "Report your ASADA's flow and upload local data (ASADA administrators only)."),
  },
  mapTip: {
    grid: t('Cada cuadro es un pedazo de Costa Rica de unos 55 km por 70 km donde NASA mide el clima desde el espacio. Con el interruptor del mapa elegís ver cuánto cambió con los años o cómo fue un año en particular.',
      'Each square is a piece of Costa Rica of about 55 km by 70 km where NASA measures the climate from space. With the map switch you choose to see how much it changed over the years or what a particular year was like.'),
    cds: t('Cada cuadro es un pedazo de Costa Rica de unos 11 km por 11 km, con datos del servicio de clima de Copernicus (Unión Europea), que mezcla satélites y estaciones en un modelo del clima. Con el interruptor del mapa elegís ver cuánto cambió con los años o cómo fue un año en particular.',
      'Each square is a piece of Costa Rica of about 11 km by 11 km, with data from the Copernicus climate service (European Union), which blends satellites and stations into a climate model. With the map switch you choose to see how much it changed over the years or what a particular year was like.'),
    cantones: t('Cada zona es un cantón. Naranja: hay operadores de agua afectados por El Niño; verde: reportaron sin afectación. También se ven los ríos y quebradas.',
      'Each area is a canton. Orange: there are water operators affected by El Niño; green: they reported no impact. Rivers and streams are also shown.'),
  },
  variableTitle: { T2M: t('Temperatura del aire', 'Air temperature'), PRECTOTCORR: t('Lluvia acumulada por año', 'Rainfall accumulated per year') },
  unit: { T2M: '°C', PRECTOTCORR: t('mm por año', 'mm per year') },
  trend: (slope, _n, unit) => slope === null
    ? t('Todavía no hay datos suficientes para ver hacia dónde va el clima.', 'There is not yet enough data to see where the climate is heading.')
    : t(`Cada 10 años ${slope >= 0 ? 'sube' : 'baja'} cerca de ${Math.abs(slope).toLocaleString(locale(), { maximumFractionDigits: 1 })} ${unit}.`,
      `Every 10 years it ${slope >= 0 ? 'rises' : 'falls'} by about ${Math.abs(slope).toLocaleString(locale(), { maximumFractionDigits: 1 })} ${unit}.`),
  significance: significant => significant === null
    ? t('No hay una prueba disponible para este dato.', 'There is no test available for this data.')
    : significant ? t('El cambio es claro: es poco probable que sea casualidad.', 'The change is clear: it is unlikely to be chance.')
      : t('Todavía no hay suficiente evidencia de que este cambio sea real.', 'There is not yet enough evidence that this change is real.'),
  windows: t('Comparamos dos períodos de años', 'We compare two periods of years'),
  ensoTitle: t('El Niño en el océano Pacífico', 'El Niño in the Pacific Ocean'),
  ensoBody: (start, end) => t(`Entre ${start} y ${end} el océano Pacífico estuvo más cálido de lo normal. A ese fenómeno se le llama El Niño y puede cambiar cuánto llueve en Costa Rica.`,
    `Between ${start} and ${end} the Pacific Ocean was warmer than normal. That phenomenon is called El Niño and it can change how much it rains in Costa Rica.`),
  ensoUnknown: t('Todavía no hay un episodio de El Niño cargado para esta zona.', 'There is no El Niño episode loaded for this area yet.'),
  tipSlope: t('Cuánto cambia el valor, en promedio, cada 10 años.', 'How much the value changes, on average, every 10 years.'),
  tipSignificance: t('Dice si el cambio parece real o podría ser casualidad.', 'Says whether the change seems real or could be chance.'),
  tipAnomaly: t('Cuánto se aleja un mes de lo que suele pasar en ese mes.', 'How far a month is from what usually happens in that month.'),
  tipCell: t('Un cuadro del mapa. Tocalo para ver sus datos.', 'A square on the map. Tap it to see its data.'),
  tipRange: t('Elegí qué años querés ver en el gráfico.', 'Choose which years you want to see in the chart.'),
  technicalDetail: t('Ver detalle técnico (opcional)', 'See technical detail (optional)'),
  alertLabel: { active: t('Hay aviso vigente', 'There is an active notice'), expired: t('Aviso vencido', 'Expired notice'), none: t('Sin avisos cargados', 'No notices loaded') },
  recommendationsTitle: t('Qué podés hacer', 'What you can do'),
  recommendations: [
    t('Guardá agua limpia para un par de días si te avisan de un corte.', 'Store clean water for a couple of days if you are told about an outage.'),
    t('Revisá fugas en tu casa: una gota constante desperdicia mucha agua.', 'Check for leaks at home: a constant drip wastes a lot of water.'),
    t('Seguí los avisos oficiales de tu ASADA o del AyA antes de compartir mensajes de redes.', 'Follow the official notices from your ASADA or the AyA before sharing social media messages.'),
  ],
  recommendationsNote: t('Son consejos generales. No sustituyen un comunicado oficial.', 'These are general tips. They do not replace an official statement.'),
  confidenceRule: t('La confianza sube si hay pocos años faltantes y casi todos los cuadros tienen datos. Sin estaciones locales que los comprueben, no pasa de «media».',
    'Confidence rises when few years are missing and almost all squares have data. Without local stations to check them, it does not go beyond “medium”.'),
  aiNote: t('Texto armado automáticamente con las cifras de este panel. No usa un modelo de lenguaje y no reemplaza a una persona experta.',
    'Text assembled automatically from the figures in this panel. It does not use a language model and does not replace an expert.'),
  forecastNote: t('Es una línea que sigue la tendencia de los años elegidos hacia adelante. No es un pronóstico del tiempo ni está validada.',
    'It is a line that continues the trend of the chosen years forward. It is not a weather forecast and it is not validated.'),
})

const tecnico: Copy = {
  levelName: 'Detalle técnico',
  sectionTip: {
    general: 'Episodio ENSO y síntesis de la celda o cantón seleccionado.',
    temp: 'T2M (MERRA-2 vía NASA POWER): serie anual, ventanas A/B y tendencia.',
    precip: 'PRECTOTCORR (NASA POWER): serie anual, ventanas A/B y tendencia.',
    uv: 'ALLSKY_SFC_UV_INDEX (NASA POWER, 2001–2024, malla nativa 1°): serie anual y pendiente descriptiva.',
    humedad: 'RH2M (NASA POWER): humedad relativa a 2 m, serie anual y pendiente descriptiva.',
    admin: 'Reporte de caudal y afectación por El Niño de la ASADA asignada; importación de registros locales.',
  },
  mapTip: {
    grid: 'Malla MERRA-2 de NASA POWER: 0,5° de latitud × 0,625° de longitud. Color = pendiente por década en el rango elegido, o valor de un año.',
    cds: 'Malla ERA5-Land del CDS de Copernicus: 0,1° × 0,1° (~11 km). Temperatura, lluvia y humedad (derivada de T y punto de rocío) de ERA5-Land. Color = pendiente por década en el rango elegido, o valor de un año.',
    cantones: 'Capa cantonal (DTA 2026) e hidrografía OSM. Color según reportes de operadores (SAGA) y estado del aviso. Sin malla climática.',
  },
  variableTitle: { T2M: 'Temperatura a 2 m (T2M)', PRECTOTCORR: 'Precipitación corregida (PRECTOTCORR)' },
  unit: { T2M: '°C', PRECTOTCORR: 'mm/año' },
  trend: (slope, n, unit) => slope === null
    ? 'Tendencia sin datos suficientes.'
    : `Pendiente por década: ${slope.toLocaleString('es-CR', { maximumFractionDigits: 2 })} ${unit} (${n} años válidos).`,
  significance: significant => significant === null
    ? 'Sin prueba de significancia disponible.'
    : significant ? 'Tendencia con evidencia estadística al 5 % (ajuste BY).'
      : 'Evidencia estadística insuficiente al 5 % (ajuste BY).',
  windows: 'Ventanas A y B',
  ensoTitle: 'Episodio ENSO (El Niño)',
  ensoBody: (start, end, unit) => `Episodio ${start} a ${end}. Anomalías mensuales frente a la climatología 1981–2010 (${unit}).`,
  ensoUnknown: 'Sin episodio ENSO cargado para esta selección.',
  tipSlope: 'Pendiente de largo plazo por década (Sen y OLS/HAC).',
  tipSignificance: 'p ajustado por Benjamini–Yekutieli sobre la familia de pruebas.',
  tipAnomaly: 'Desviación mensual respecto de la climatología 1981–2010.',
  tipCell: 'Celda de la malla NASA POWER. Click para fijar la selección.',
  tipRange: 'Filtra la serie anual; se envía como desde/hasta a la API.',
  technicalDetail: 'Detalle técnico',
  alertLabel: { active: 'Comunicado vigente', expired: 'Comunicado vencido', none: 'Sin comunicados' },
  recommendationsTitle: 'Medidas preventivas',
  recommendations: [
    'Verificar el comunicado en su fuente original (ASADA, AyA o IMN) antes de difundirlo.',
    'Contrastar anomalías de precipitación con el boletín ENOS vigente del IMN.',
    'Reportar al operador cualquier discrepancia entre el aviso y el servicio observado.',
  ],
  recommendationsNote: 'Orientación general. La decisión operativa corresponde al operador y a las comisiones.',
  confidenceRule: 'Regla: alta si continuidad ≥ 90 % y cuadros con datos ≥ 75 %; media si ≥ 70 % y ≥ 40 %; baja en otro caso. Sin estaciones locales vinculadas el máximo es «media».',
  aiNote: 'Redacción por plantillas sobre las cifras de este panel (sin modelo de lenguaje). Revisión por una persona experta pendiente.',
  forecastNote: 'Extrapolación lineal (OLS) del rango elegido frente a la media 1981–2010. No es un pronóstico validado; el pronóstico local depende de datos de estaciones del IMN.',
}

/** `copy[level]` se evalúa al usarse, así que siempre refleja el idioma activo. (`tecnico` no se usa en la interfaz actual y queda en español.) */
export const copy: Record<Level, Copy> = { get basico() { return basico() }, tecnico }
