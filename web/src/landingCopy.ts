import type { MapMode } from './copy'
import { t } from './i18n'

/**
 * Textos de la página de inicio. Mantienen el voseo del resto de la app. Todo se arma al llamar a la función (no al cargar
 * el módulo) para que salga en el idioma activo.
 */

export type TipTopic = 'agua' | 'calor' | 'campo' | 'salud' | 'info'

/** Etiqueta de cada tema (con getters: siempre en el idioma activo). */
export const TOPIC_LABEL: Record<TipTopic, string> = {
  get agua() { return t('Agua', 'Water') },
  get calor() { return t('Calor', 'Heat') },
  get campo() { return t('Campo', 'Farming') },
  get salud() { return t('Salud', 'Health') },
  get info() { return t('Información', 'Information') },
}

export type Tip = { topic: TipTopic; title: string; text: string }

/** Consejos generales. En la página se muestran tres al azar (uno del tema más urgente, si hay una advertencia). */
export const tipList = (): Tip[] => [
  { topic: 'agua', title: t('Guardá agua limpia', 'Store clean water'), text: t('Si te avisan de un corte, guardá agua limpia y tapada para un par de días. Un balde con tapa y una jarra bastan para empezar.', 'If you are told about an outage, store clean, covered water for a couple of days. A bucket with a lid and a pitcher are enough to start.') },
  { topic: 'agua', title: t('Cazá las fugas', 'Hunt down leaks'), text: t('Una gota constante desperdicia mucha agua. Cerrá las llaves y revisá el medidor: si se mueve con todo apagado, hay una fuga.', 'A constant drip wastes a lot of water. Close the taps and check the meter: if it moves with everything off, there is a leak.') },
  { topic: 'agua', title: t('Reusá el agua', 'Reuse water'), text: t('El agua del lavado de verduras o del aire acondicionado sirve para regar las plantas o limpiar patios.', 'Water from washing vegetables or from the air conditioner can be used to water plants or clean patios.') },
  { topic: 'agua', title: t('Regá a primera hora', 'Water early'), text: t('Regar de madrugada o al atardecer evita que el sol evapore el agua antes de que llegue a la raíz.', 'Watering at dawn or at dusk keeps the sun from evaporating the water before it reaches the roots.') },
  { topic: 'agua', title: t('Conocé tu ASADA', 'Know your ASADA'), text: t('Guardá el teléfono de tu ASADA o del AyA y seguí sus avisos: ellos saben primero cuándo habrá racionamientos.', 'Keep the phone number of your ASADA or the AyA and follow their notices: they know first when there will be rationing.') },
  { topic: 'calor', title: t('Hidratate seguido', 'Stay hydrated'), text: t('En días de mucho calor tomá agua aunque no tengás sed, sobre todo niños, personas mayores y quienes trabajan al sol.', 'On very hot days drink water even if you are not thirsty, especially children, older people and those who work in the sun.') },
  { topic: 'calor', title: t('Evitá el sol del mediodía', 'Avoid the midday sun'), text: t('Entre las 10 a. m. y las 2 p. m. el sol es más fuerte. Hacé las tareas pesadas temprano y buscá la sombra.', 'Between 10 a.m. and 2 p.m. the sun is strongest. Do heavy tasks early and look for shade.') },
  { topic: 'calor', title: t('Casa más fresca', 'A cooler home'), text: t('Abrí las ventanas de noche, cerrá cortinas de día y plantá un árbol de sombra: baja la temperatura sin gastar electricidad.', 'Open the windows at night, close the curtains by day and plant a shade tree: it lowers the temperature without using electricity.') },
  { topic: 'campo', title: t('Cuidá el suelo', 'Look after the soil'), text: t('Cubrir el suelo con hojas o residuos de cosecha (mulch) conserva la humedad en época seca.', 'Covering the soil with leaves or crop residue (mulch) keeps moisture in the dry season.') },
  { topic: 'campo', title: t('Cosechá agua de lluvia', 'Harvest rainwater'), text: t('Un tanque conectado a la canoa del techo guarda el agua de las lluvias para regar cuando falte.', 'A tank connected to the roof gutter stores rainwater to irrigate when there is a shortage.') },
  { topic: 'campo', title: t('Cuidado con el fuego', 'Be careful with fire'), text: t('En época seca una quema se sale de control muy fácil. No quemés basura ni rastrojos y reportá cualquier incendio al 9-1-1.', 'In the dry season a burn gets out of control very easily. Do not burn trash or stubble and report any fire to 9-1-1.') },
  { topic: 'salud', title: t('Protegete del UV', 'Protect yourself from UV'), text: t('Con índice UV alto usá sombrero, lentes y bloqueador, aunque el día esté nublado.', 'With a high UV index wear a hat, sunglasses and sunscreen, even if the day is cloudy.') },
  { topic: 'salud', title: t('Agua segura para beber', 'Safe drinking water'), text: t('Si el agua baja de caudal o cambia de color, hervila un minuto o usá agua embotellada hasta confirmar que es potable.', 'If the water flow drops or the water changes color, boil it for a minute or use bottled water until you confirm it is drinkable.') },
  { topic: 'info', title: t('Verificá antes de compartir', 'Verify before sharing'), text: t('Antes de reenviar un mensaje sobre cortes o sequía, confirmalo con tu ASADA, el AyA o el IMN.', 'Before forwarding a message about outages or drought, confirm it with your ASADA, the AyA or the IMN.') },
  { topic: 'info', title: t('Seguí el boletín del IMN', 'Follow the IMN bulletin'), text: t('El Instituto Meteorológico Nacional publica el boletín ENOS con el estado de El Niño y sus efectos esperados.', 'The Instituto Meteorológico Nacional publishes the ENSO bulletin with the state of El Niño and its expected effects.') },
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

export const dataCards = (): DataCard[] => [
  {
    mode: 'grid',
    chip: t('Satélite · NASA', 'Satellite · NASA'),
    title: t('Datos de NASA POWER', 'NASA POWER data'),
    summary: t('El clima de Costa Rica visto desde el espacio. NASA mezcla satélites y estaciones en un modelo (MERRA-2) y lo reparte en cuadros de unos 55 km por 70 km. Es la serie más larga: sirve para ver cómo cambió el calor y la lluvia en más de cuatro décadas.',
      "Costa Rica's climate seen from space. NASA blends satellites and stations in a model (MERRA-2) and spreads it over squares of about 55 km by 70 km. It is the longest series: it shows how heat and rain changed over more than four decades."),
    facts: [t('Temperatura, lluvia, humedad y radiación UV', 'Temperature, rain, humidity and UV radiation'), t('Años 1981 a 2024 (el UV desde 2001)', 'Years 1981 to 2024 (UV from 2001)'),
      t('Cuadros de 0,5° × 0,625° sobre todo el país', 'Squares of 0.5° × 0.625° across the whole country'), t('Cambio por década o valor de un año en particular', 'Change per decade or the value of one particular year')],
    button: t('Ir a Datos de NASA POWER', 'Go to NASA POWER data'),
    image: 'nasa.jpg',
    alt: t('Fotografía satelital de la NASA de las montañas y volcanes de Costa Rica vistos desde arriba, con bosque, cultivos y nubes', 'NASA satellite photo of the mountains and volcanoes of Costa Rica seen from above, with forest, crops and clouds'),
    technical: t('Malla MERRA-2 de NASA POWER: 0,5° de latitud × 0,625° de longitud. UV (ALLSKY_SFC_UV_INDEX) en malla nativa de 1°. Color = pendiente por década en el rango elegido, o valor de un año.',
      'NASA POWER MERRA-2 grid: 0.5° of latitude × 0.625° of longitude. UV (ALLSKY_SFC_UV_INDEX) on the native 1° grid. Color = slope per decade over the chosen range, or the value of one year.'),
  },
  {
    mode: 'cds',
    chip: t('Copernicus · Unión Europea', 'Copernicus · European Union'),
    title: t('Datos CDS', 'CDS data'),
    summary: t('El mismo clima, pero con más detalle. El servicio Copernicus de la Unión Europea (ERA5-Land) divide el país en cuadros de unos 11 km, cinco veces más finos que los de NASA, y es útil para ver diferencias entre valles, montañas y costas.',
      "The same climate, but in more detail. The European Union's Copernicus service (ERA5-Land) divides the country into squares of about 11 km, five times finer than NASA's, and it is useful for seeing differences between valleys, mountains and coasts."),
    facts: [t('Temperatura, lluvia, humedad y radiación UV', 'Temperature, rain, humidity and UV radiation'), t('Cuadros de 0,1° × 0,1° (≈ 11 km)', 'Squares of 0.1° × 0.1° (≈ 11 km)'),
      t('Mezcla de satélites y estaciones en un modelo del clima', 'A blend of satellites and stations in a climate model'), t('Para comparar con los datos de NASA', 'To compare with the NASA data')],
    button: t('Ir a Datos CDS', 'Go to CDS data'),
    image: 'cds.jpg',
    alt: t('Bosque nuboso de Monteverde, Costa Rica, con árboles cubiertos de musgo y neblina entre las ramas', 'Monteverde cloud forest, Costa Rica, with moss-covered trees and mist among the branches'),
    technical: t('Malla ERA5-Land del CDS de Copernicus: 0,1° × 0,1°. Humedad derivada de temperatura y punto de rocío. UV en superficie de ERA5 (0,25°, remuestreado al punto más cercano).',
      'Copernicus CDS ERA5-Land grid: 0.1° × 0.1°. Humidity derived from temperature and dew point. ERA5 surface UV (0.25°, resampled to the nearest point).'),
  },
  {
    mode: 'cantones',
    chip: t('Territorio · AyA · SAGA', 'Territory · AyA · SAGA'),
    title: t('Datos nacionales', 'National data'),
    summary: t('El territorio y el agua que usamos. Los cantones, los ríos y quebradas, y los operadores de agua (ASADAs y otros) con su caudal. Los administradores de cada ASADA reportan acá si El Niño las está afectando.',
      'The territory and the water we use. The cantons, the rivers and streams, and the water operators (ASADAs and others) with their flow. The administrators of each ASADA report here whether El Niño is affecting them.'),
    facts: [t('Cantones y provincias de Costa Rica', 'Cantons and provinces of Costa Rica'), t('Ríos, quebradas y canales (OpenStreetMap)', 'Rivers, streams and canals (OpenStreetMap)'),
      t('Operadores de agua y su caudal (SAGA del AyA)', "Water operators and their flow (the AyA's SAGA)"), t('Naranja = afectación por El Niño · Verde = sin afectación', 'Orange = affected by El Niño · Green = not affected')],
    button: t('Ir a Datos nacionales', 'Go to National data'),
    image: 'nacionales.jpg',
    alt: t('El río Sierpe rodeado de vegetación tropical en Costa Rica, con una lancha navegando', 'The Sierpe River surrounded by tropical vegetation in Costa Rica, with a boat sailing'),
    technical: t('Capa cantonal (DTA 2026) e hidrografía OSM. Color según reportes de operadores (SAGA) y estado del aviso. Sin malla climática.',
      'Cantonal layer (DTA 2026) and OSM hydrography. Color according to operator reports (SAGA) and notice status. No climate grid.'),
  },
]

export const sources = () => [
  { name: 'NASA POWER', text: t('Datos de clima (MERRA-2) para temperatura, lluvia, humedad y UV.', 'Climate data (MERRA-2) for temperature, rain, humidity and UV.'), url: 'https://power.larc.nasa.gov' },
  { name: 'Copernicus · Climate Data Store', text: t('ERA5-Land y ERA5. Contiene información modificada del Servicio de Cambio Climático de Copernicus.', 'ERA5-Land and ERA5. Contains modified Copernicus Climate Change Service information.'), url: 'https://cds.climate.copernicus.eu' },
  { name: 'IMN', text: t('Episodios de El Niño y boletines ENOS de Costa Rica.', 'El Niño episodes and ENSO bulletins from Costa Rica.'), url: 'https://www.imn.ac.cr' },
  { name: 'AyA · SAGA', text: t('Operadores de agua y sus fuentes, con su último caudal registrado.', 'Water operators and their sources, with their latest recorded flow.'), url: 'https://www.aya.go.cr' },
  { name: 'OpenStreetMap', text: t('Ríos, quebradas y canales. © colaboradores de OpenStreetMap (ODbL).', 'Rivers, streams and canals. © OpenStreetMap contributors (ODbL).'), url: 'https://www.openstreetmap.org/copyright' },
]

export const photoCredits = () => [
  { file: t('Bosque de Monteverde', 'Monteverde forest'), author: 'Cephas', license: 'CC BY-SA 4.0', url: 'https://commons.wikimedia.org/wiki/File:Monteverde_Reserve_Costa_Rica_02.jpg' },
  { file: t('Río Guanacaste', 'Guanacaste River'), author: 'MongeNajera', license: 'CC BY-SA 3.0', url: 'https://commons.wikimedia.org/wiki/File:Rio_Guanacaste.jpg' },
  { file: t('Costa Rica desde el espacio', 'Costa Rica from space'), author: 'NASA Goddard Space Flight Center', license: t('Dominio público', 'Public domain'), url: 'https://commons.wikimedia.org/wiki/File:Costa_Rica_(14214278247).jpg' },
  { file: t('Bosque nuboso de Monteverde', 'Monteverde cloud forest'), author: 'Dr. Alexey Yakovlev', license: 'CC BY-SA 2.0', url: 'https://commons.wikimedia.org/wiki/File:Monteverde_Cloud_Forest_(28367816878).jpg' },
  { file: t('Río Sierpe', 'Sierpe River'), author: 'Bernard Gagnon', license: 'CC0', url: 'https://commons.wikimedia.org/wiki/File:Sierpe_River,_Costa_Rica.jpg' },
  { file: t('Costa del Pacífico', 'Pacific coast'), author: 'PoeXinia', license: 'CC0', url: 'https://commons.wikimedia.org/wiki/File:Beach_on_the_Pacific_Coast_of_Costa_Rica.jpg' },
]
