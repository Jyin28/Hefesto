# Pitch — Hefesto: Detective Tico (4:30)

> **Guion de ensayo con datos reales.** Las cifras y su verificación están en [Validación](validation.md). Las capturas quedan para el ensayo en navegador.

## Cronograma (total 4:30)

| Tiempo | Duración | Quién | Diapositiva | Tema |
|---|---|---|---|---|
| 0:00–0:30 | 0:30 | Joshua | 1 | Apertura |
| 0:30–1:10 | 0:40 | Joshua | 2 | Cómo funciona |
| 1:10–2:05 | 0:55 | Kevin | 3 | Caso 1: calor |
| 2:05–3:00 | 0:55 | Kevin | 4 | Caso 2: lluvia + ENOS |
| 3:00–3:50 | 0:50 | Emanuel | 5 | Rigor científico |
| 3:50–4:10 | 0:20 | Samuel | 5 | Datos y límites |
| 4:10–4:30 | 0:20 | Joshua | 6 | Ficha, offline y cierre |

## Guion

### 0:00–0:30 · Joshua · Diapositiva 1
"En Costa Rica todos hablamos del calor y de la lluvia: ¿hace más calor que antes?, ¿llueve distinto en el Caribe que en el Pacífico? Pasar de la intuición a la evidencia no es fácil. **Hefesto: Detective Tico** convierte una pregunta cotidiana en evidencia reproducible, paso a paso, para colegios y universidades. Funciona sin internet y sin inteligencia artificial generativa en producción."

### 0:30–1:10 · Joshua · Diapositiva 2
"El estudiante elige calor o lluvia. El sitio usa temperatura del aire a dos metros para calor y precipitación corregida para lluvia. Los datos son de NASA POWER mensual, del reanálisis MERRA-2, de 1981 a 2024: 44 años completos. Son estimaciones de un modelo con asimilación de observaciones, no mediciones de estaciones."

### 1:10–2:05 · Kevin · Diapositiva 3 (Caso calor, `CR_HEAT`)
"Primer caso: calor. Comparamos dos sectores didácticos, Pacífico Norte y Caribe, con cinco celdas terrestres cada uno. La app compara 1981–2002 con 2003–2024 con mapas de la misma escala. En el Caribe, la pendiente de temperatura del aire es +0,144 °C por década, con un intervalo individual de 0,081 a 0,207. En Pacífico Norte estimamos −0,036 °C por década y el intervalo incluye cero."

### 2:05–3:00 · Kevin · Diapositiva 4 (Caso lluvia, `CR_RAIN`)
"Segundo caso: lluvia, en milímetros por año. Comparamos de nuevo Pacífico Norte y Caribe. Las pendientes son +402 y +592 mm/año por década, respectivamente. Mostramos julio de 2023 a abril de 2024 frente al período neutral documentado de julio de 2013 a abril de 2014 y a la climatología 1981–2010. Un artículo de la UCR explica que El Niño y La Niña influyen de forma distinta en las dos vertientes. Pero eso es variabilidad interanual: no prueba una tendencia ni garantiza pendientes opuestas entre 1981 y 2024. Y recordemos: medimos lluvia, no caudal de ríos, ni recarga de acuíferos, ni agua potable."

### 3:00–3:50 · Emanuel · Diapositiva 5
"Para ser honestos con la estadística, usamos solo años con doce meses completos. Con menos de diez años no ajustamos nada; entre diez y veintinueve mostramos solo la pendiente descriptiva; con treinta o más años consecutivos usamos regresión OLS con errores estándar HAC, kernel Bartlett y L igual a 3, con sensibilidad en L igual a 1 y 5. Corregimos por comparaciones múltiples con Benjamini-Yekutieli, alfa 0.05, sobre dos variables por dos sectores. Y si algo no es significativo, decimos evidencia insuficiente, no ausencia de cambio."

### 3:50–4:10 · Samuel · Diapositiva 5
"Cada celda mide unos 55 por 69 kilómetros; no son provincias, cantones ni fincas, y las celdas costeras pueden mezclar tierra y mar. Es una herramienta educativa: no está validada para alertas, racionamiento, ASADAS ni agricultura, ni aún con usuarios externos."

### 4:10–4:30 · Joshua · Diapositiva 6
"Cada recorrido termina en una Ficha de Detective, descargable en JSON y CSV, reproducible con el paquete local. Detective Tico no promete respuestas; enseña a hacer buenas preguntas con evidencia. Gracias."

## Si el navegador o la publicación fallan

Usar la ejecución local de Streamlit y abrir el JSON y CSV del mismo resultado. Si el mapa interactivo falla, la ficha se puede cambiar con el selector de celdas. El cuadro de validación contiene las cifras de respaldo.

## Preguntas y respuestas (Q&A)

| # | Pregunta | Dueño | Ideas clave para responder |
|---|---|---|---|
| 1 | ¿Por qué datos de modelo? | Samuel | Cubren 1981–2024 sin huecos (44 años, 528 meses), son reproducibles y están en cuadrícula. No son mediciones de estación; lo decimos siempre. |
| 2 | ¿Qué tan local es? | Samuel | Celdas de ~55 × 69 km; 5 por sector. Es regional, no representa provincias, cantones ni fincas. Celdas costeras pueden mezclar tierra y mar. |
| 3 | ¿Qué significa p? | Emanuel | Qué tan compatible es el resultado con "no hay tendencia". No mide el tamaño ni la importancia del cambio. |
| 4 | ¿Por qué BY? | Emanuel | Hay 4 pruebas (2 variables × 2 sectores); BY corrige por comparaciones múltiples y es válido bajo dependencia, para evitar falsos hallazgos. |
| 5 | ¿Qué significa "no significativo"? | Emanuel | Evidencia insuficiente bajo este modelo, no ausencia de cambio. Más años no garantizan reducir p. |
| 6 | ¿Por qué ENOS no prueba tendencia? | Joshua | ENOS es variabilidad interanual; influye distinto en cada vertiente según la UCR, pero no demuestra causalidad ni garantiza pendientes opuestas en 1981–2024. |
| 7 | ¿Qué innovación aportan? | Kevin | Del dato a una pregunta cotidiana: ventanas comparables, selección de celdas, evidencia estadística y ficha reproducible en JSON y CSV. |

*(Dueños propuestos: ajustar si el equipo lo prefiere.)*
