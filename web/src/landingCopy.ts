import type { MapMode } from './copy'

/** Textos de la página de inicio. Mantienen el voseo del resto de la app. */

export type TipTopic = 'agua' | 'calor' | 'campo' | 'salud' | 'info'

export const TOPIC_LABEL: Record<TipTopic, string> = {
  agua: 'Agua', calor: 'Calor', campo: 'Campo', salud: 'Salud', info: 'Información',
}

export type Tip = { topic: TipTopic; title: string; text: string }

/** Consejos generales. En la página se muestran tres al azar (uno del tema más urgente, si hay una advertencia). */
export const TIPS: Tip[] = [
  { topic: 'agua', title: 'Guardá agua limpia', text: 'Si te avisan de un corte, guardá agua limpia y tapada para un par de días. Un balde con tapa y una jarra bastan para empezar.' },
  { topic: 'agua', title: 'Cazá las fugas', text: 'Una gota constante desperdicia mucha agua. Cerrá las llaves y revisá el medidor: si se mueve con todo apagado, hay una fuga.' },
  { topic: 'agua', title: 'Reusá el agua', text: 'El agua del lavado de verduras o del aire acondicionado sirve para regar las plantas o limpiar patios.' },
  { topic: 'agua', title: 'Regá a primera hora', text: 'Regar de madrugada o al atardecer evita que el sol evapore el agua antes de que llegue a la raíz.' },
  { topic: 'agua', title: 'Conocé tu ASADA', text: 'Guardá el teléfono de tu ASADA o del AyA y seguí sus avisos: ellos saben primero cuándo habrá racionamientos.' },
  { topic: 'calor', title: 'Hidratate seguido', text: 'En días de mucho calor tomá agua aunque no tengás sed, sobre todo niños, personas mayores y quienes trabajan al sol.' },
  { topic: 'calor', title: 'Evitá el sol del mediodía', text: 'Entre las 10 a. m. y las 2 p. m. el sol es más fuerte. Hacé las tareas pesadas temprano y buscá la sombra.' },
  { topic: 'calor', title: 'Casa más fresca', text: 'Abrí las ventanas de noche, cerrá cortinas de día y plantá un árbol de sombra: baja la temperatura sin gastar electricidad.' },
  { topic: 'campo', title: 'Cuidá el suelo', text: 'Cubrir el suelo con hojas o residuos de cosecha (mulch) conserva la humedad en época seca.' },
  { topic: 'campo', title: 'Cosechá agua de lluvia', text: 'Un tanque conectado a la canoa del techo guarda el agua de las lluvias para regar cuando falte.' },
  { topic: 'campo', title: 'Cuidado con el fuego', text: 'En época seca una quema se sale de control muy fácil. No quemés basura ni rastrojos y reportá cualquier incendio al 9-1-1.' },
  { topic: 'salud', title: 'Protegete del UV', text: 'Con índice UV alto usá sombrero, lentes y bloqueador, aunque el día esté nublado.' },
  { topic: 'salud', title: 'Agua segura para beber', text: 'Si el agua baja de caudal o cambia de color, hervila un minuto o usá agua embotellada hasta confirmar que es potable.' },
  { topic: 'info', title: 'Verificá antes de compartir', text: 'Antes de reenviar un mensaje sobre cortes o sequía, confirmalo con tu ASADA, el AyA o el IMN.' },
  { topic: 'info', title: 'Seguí el boletín del IMN', text: 'El Instituto Meteorológico Nacional publica el boletín ENOS con el estado de El Niño y sus efectos esperados.' },
]

export type DataCard = {
  mode: MapMode
  chip: string
  title: string
  summary: string
  facts: string[]
  button: string
  image: string
  alt: string
  technical: string
}

export const DATA_CARDS: DataCard[] = [
  {
    mode: 'grid',
    chip: 'Satélite · NASA',
    title: 'Datos de NASA POWER',
    summary: 'El clima de Costa Rica visto desde el espacio. NASA mezcla satélites y estaciones en un modelo (MERRA-2) y lo reparte en cuadros de unos 55 km por 70 km. Es la serie más larga: sirve para ver cómo cambió el calor y la lluvia en más de cuatro décadas.',
    facts: ['Temperatura, lluvia, humedad y radiación UV', 'Años 1981 a 2024 (el UV desde 2001)', 'Cuadros de 0,5° × 0,625° sobre todo el país', 'Cambio por década o valor de un año en particular'],
    button: 'Ir a Datos de NASA POWER',
    image: 'nasa.jpg',
    alt: 'Fotografía satelital de la NASA de las montañas y volcanes de Costa Rica vistos desde arriba, con bosque, cultivos y nubes',
    technical: 'Malla MERRA-2 de NASA POWER: 0,5° de latitud × 0,625° de longitud. UV (ALLSKY_SFC_UV_INDEX) en malla nativa de 1°. Color = pendiente por década en el rango elegido, o valor de un año.',
  },
  {
    mode: 'cds',
    chip: 'Copernicus · Unión Europea',
    title: 'Datos CDS',
    summary: 'El mismo clima, pero con más detalle. El servicio Copernicus de la Unión Europea (ERA5-Land) divide el país en cuadros de unos 11 km, cinco veces más finos que los de NASA, y es útil para ver diferencias entre valles, montañas y costas.',
    facts: ['Temperatura, lluvia, humedad y radiación UV', 'Cuadros de 0,1° × 0,1° (≈ 11 km)', 'Mezcla de satélites y estaciones en un modelo del clima', 'Para comparar con los datos de NASA'],
    button: 'Ir a Datos CDS',
    image: 'cds.jpg',
    alt: 'Bosque nuboso de Monteverde, Costa Rica, con árboles cubiertos de musgo y neblina entre las ramas',
    technical: 'Malla ERA5-Land del CDS de Copernicus: 0,1° × 0,1°. Humedad derivada de temperatura y punto de rocío. UV en superficie de ERA5 (0,25°, remuestreado al punto más cercano).',
  },
  {
    mode: 'cantones',
    chip: 'Territorio · AyA · SAGA',
    title: 'Datos nacionales',
    summary: 'El territorio y el agua que usamos. Los cantones, los ríos y quebradas, y los operadores de agua (ASADAs y otros) con su caudal. Los administradores de cada ASADA reportan acá si El Niño las está afectando.',
    facts: ['Cantones y provincias de Costa Rica', 'Ríos, quebradas y canales (OpenStreetMap)', 'Operadores de agua y su caudal (SAGA del AyA)', 'Naranja = afectación por El Niño · Verde = sin afectación'],
    button: 'Ir a Datos nacionales',
    image: 'nacionales.jpg',
    alt: 'El río Sierpe rodeado de vegetación tropical en Costa Rica, con una lancha navegando',
    technical: 'Capa cantonal (DTA 2026) e hidrografía OSM. Color según reportes de operadores (SAGA) y estado del aviso. Sin malla climática.',
  },
]

export const SOURCES = [
  { name: 'NASA POWER', text: 'Datos de clima (MERRA-2) para temperatura, lluvia, humedad y UV.', url: 'https://power.larc.nasa.gov' },
  { name: 'Copernicus · Climate Data Store', text: 'ERA5-Land y ERA5. Contiene información modificada del Servicio de Cambio Climático de Copernicus.', url: 'https://cds.climate.copernicus.eu' },
  { name: 'IMN', text: 'Episodios de El Niño y boletines ENOS de Costa Rica.', url: 'https://www.imn.ac.cr' },
  { name: 'AyA · SAGA', text: 'Operadores de agua y sus fuentes, con su último caudal registrado.', url: 'https://www.aya.go.cr' },
  { name: 'OpenStreetMap', text: 'Ríos, quebradas y canales. © colaboradores de OpenStreetMap (ODbL).', url: 'https://www.openstreetmap.org/copyright' },
]

export const PHOTO_CREDITS = [
  { file: 'Bosque de Monteverde', author: 'Cephas', license: 'CC BY-SA 4.0', url: 'https://commons.wikimedia.org/wiki/File:Monteverde_Reserve_Costa_Rica_02.jpg' },
  { file: 'Río Guanacaste', author: 'MongeNajera', license: 'CC BY-SA 3.0', url: 'https://commons.wikimedia.org/wiki/File:Rio_Guanacaste.jpg' },
  { file: 'Costa Rica desde el espacio', author: 'NASA Goddard Space Flight Center', license: 'Dominio público', url: 'https://commons.wikimedia.org/wiki/File:Costa_Rica_(14214278247).jpg' },
  { file: 'Bosque nuboso de Monteverde', author: 'Dr. Alexey Yakovlev', license: 'CC BY-SA 2.0', url: 'https://commons.wikimedia.org/wiki/File:Monteverde_Cloud_Forest_(28367816878).jpg' },
  { file: 'Río Sierpe', author: 'Bernard Gagnon', license: 'CC0', url: 'https://commons.wikimedia.org/wiki/File:Sierpe_River,_Costa_Rica.jpg' },
  { file: 'Costa del Pacífico', author: 'PoeXinia', license: 'CC0', url: 'https://commons.wikimedia.org/wiki/File:Beach_on_the_Pacific_Coast_of_Costa_Rica.jpg' },
]
