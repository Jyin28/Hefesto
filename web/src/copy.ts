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

const basico: Copy = {
  levelName: 'Explicación sencilla',
  sectionTip: {
    general: 'Resumen de El Niño y de la zona que elegiste.',
    temp: 'Cómo ha cambiado el calor en la zona.',
    precip: 'Cómo ha cambiado la lluvia en la zona.',
    uv: 'Radiación UV: cuánta radiación del sol llega a la zona (tonos violetas en el mapa).',
    humedad: 'Humedad del aire en la zona (tonos verdes en el mapa).',
    admin: 'Reportar el caudal de tu ASADA y cargar datos locales (solo administradores de ASADA).',
  },
  mapTip: {
    grid: 'Cada cuadro es un pedazo de Costa Rica de unos 55 km por 70 km donde NASA mide el clima desde el espacio. Con el interruptor del mapa elegís ver cuánto cambió con los años o cómo fue un año en particular.',
    cds: 'Cada cuadro es un pedazo de Costa Rica de unos 11 km por 11 km, con datos del servicio de clima de Copernicus (Unión Europea), que mezcla satélites y estaciones en un modelo del clima. Con el interruptor del mapa elegís ver cuánto cambió con los años o cómo fue un año en particular.',
    cantones: 'Cada zona es un cantón. Naranja: hay operadores de agua afectados por El Niño; verde: reportaron sin afectación. También se ven los ríos y quebradas.',
  },
  variableTitle: { T2M: 'Temperatura del aire', PRECTOTCORR: 'Lluvia acumulada por año' },
  unit: { T2M: '°C', PRECTOTCORR: 'mm por año' },
  trend: (slope, _n, unit) => slope === null
    ? 'Todavía no hay datos suficientes para ver hacia dónde va el clima.'
    : `Cada 10 años ${slope >= 0 ? 'sube' : 'baja'} cerca de ${Math.abs(slope).toLocaleString('es-CR', { maximumFractionDigits: 1 })} ${unit}.`,
  significance: significant => significant === null
    ? 'No hay una prueba disponible para este dato.'
    : significant ? 'El cambio es claro: es poco probable que sea casualidad.'
      : 'Todavía no hay suficiente evidencia de que este cambio sea real.',
  windows: 'Comparamos dos períodos de años',
  ensoTitle: 'El Niño en el océano Pacífico',
  ensoBody: (start, end) => `Entre ${start} y ${end} el océano Pacífico estuvo más cálido de lo normal. A ese fenómeno se le llama El Niño y puede cambiar cuánto llueve en Costa Rica.`,
  ensoUnknown: 'Todavía no hay un episodio de El Niño cargado para esta zona.',
  tipSlope: 'Cuánto cambia el valor, en promedio, cada 10 años.',
  tipSignificance: 'Dice si el cambio parece real o podría ser casualidad.',
  tipAnomaly: 'Cuánto se aleja un mes de lo que suele pasar en ese mes.',
  tipCell: 'Un cuadro del mapa. Tocalo para ver sus datos.',
  tipRange: 'Elegí qué años querés ver en el gráfico.',
  technicalDetail: 'Ver detalle técnico (opcional)',
  alertLabel: { active: 'Hay aviso vigente', expired: 'Aviso vencido', none: 'Sin avisos cargados' },
  recommendationsTitle: 'Qué podés hacer',
  recommendations: [
    'Guardá agua limpia para un par de días si te avisan de un corte.',
    'Revisá fugas en tu casa: una gota constante desperdicia mucha agua.',
    'Seguí los avisos oficiales de tu ASADA o del AyA antes de compartir mensajes de redes.',
  ],
  recommendationsNote: 'Son consejos generales. No sustituyen un comunicado oficial.',
  confidenceRule: 'La confianza sube si hay pocos años faltantes y casi todos los cuadros tienen datos. Sin estaciones locales que los comprueben, no pasa de «media».',
  aiNote: 'Texto armado automáticamente con las cifras de este panel. No usa un modelo de lenguaje y no reemplaza a una persona experta.',
  forecastNote: 'Es una línea que sigue la tendencia de los años elegidos hacia adelante. No es un pronóstico del tiempo ni está validada.',
}

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

export const copy: Record<Level, Copy> = { basico, tecnico }
