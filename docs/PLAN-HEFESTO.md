> **Reemplazado** por [PLAN_HEFESTO_V2.md](PLAN_HEFESTO_V2.md) (alcance vigente del MVP: sin pronóstico, agua/ASADAS ni cantones).

# Hefesto · Plan del MVP Detective Tico

**NASA Space Apps · 14 de noviembre de 2026 · Alcance del MVP**

Detective Tico será un sitio web educativo para investigar cómo cambiaron el calor y la lluvia en Costa Rica, qué anomalías coincidieron con El Niño y qué evidencia respalda las conclusiones. Se reutiliza el sitio Streamlit de `app.py`, la descarga mensual de NASA POWER y la preparación temporal del repositorio.

## 1. Datos y zonas

| Fuente | Uso en el MVP | Condición para mostrarla |
|---|---|---|
| **NASA POWER mensual**, `T2M` y `PRECTOTCORR` | Única fuente de las series y mapas de tendencia climática. Las consultas y exportaciones se limitan a celdas terrestres verificadas de Costa Rica. Inventario inicial 1981–2024. | Validar cobertura, unidades, máscara, versión y procedencia por celda. |
| **IMN / COENOS** | Fechar el episodio oficial de El Niño y citar su contexto nacional. Las estaciones del IMN o series equivalentes de Costa Rica pueden alimentar el pronóstico local. | Citar boletín y fechas. Antes de entrenar, verificar acceso, licencia, metadatos y cobertura de cada serie de estaciones. |
| **AyA, ASADAS y ARESEP — distribución de agua** | Mostrar operadores y registros locales de distribución de agua. Priorizar al menos una muestra verificable de un acueducto o ASADA, con fechas y área de servicio cuando haya información. | Verificar qué mide el registro, por ejemplo horas de servicio, interrupciones o volumen distribuido. Identificar los faltantes de distribución para cada zona. |
| **AyA / Laboratorio Nacional de Aguas, INEC y operadores locales — cobertura del servicio de agua** | Incorporar datos de cobertura para saber qué población o viviendas reciben agua por acueducto, quién presta el servicio y qué áreas están atendidas cuando existan límites publicados. | Verificar el año, la unidad geográfica, la definición del indicador, el denominador de cada porcentaje y la fuente. Conservar el nivel geográfico original. Identificar por separado los indicadores de acceso por acueducto y de agua potable. |

**Cobertura del servicio en el mapa.** Mostrar un indicador verificable de cobertura en el recorrido de lluvia. Si hay áreas de servicio publicadas, superponerlas sobre el mapa de lluvia. Si solo hay indicadores agregados, mostrarlos con su nivel geográfico original (por ejemplo, cantón) en la ficha correspondiente. Marcar los faltantes como «sin dato» y mostrar el año de referencia para que el usuario pueda contrastarlo con las ventanas climáticas.

**Zonas variables.** Arrancar con Pacífico Norte (`CR_PN`) y Caribe (`CR_CAR`) porque el repositorio ya trae sus máscaras. Cada zona se define por configuración versionada con identificador, nombre, celdas verificadas, geometría y pesos. Cargar una zona adicional requiere validar esos datos y su cobertura temporal. El usuario puede cambiar de zona y seleccionar una celda. La cobertura visible se limita a las zonas verificadas.

**Resolución y unidades.** Conservar la grilla nativa de meteorología de POWER, documentada en el repositorio como 0,5° de latitud × 0,625° de longitud. Presentar la pérdida de detalle por relieve y mezcla costera. Mantener `T2M` mensual en °C y promediar anualmente con días reales de cada mes. Convertir la tasa mensual de lluvia de mm/día a mm/mes multiplicando por los días reales y sumar para obtener mm/año. Exigir 12 meses válidos por año, conservar los ceros y mostrar los faltantes. Mantener la máscara fija dentro de cada comparación y reportar cobertura.

## 2. Comparación automática

| Vista | Ventanas y regla | Salida |
|---|---|---|
| Tendencia histórica | Selección automática de dos bloques consecutivos de igual duración y sin solapamiento, dentro de la cobertura del paquete. Si hay un número impar de años, excluir el más antiguo del valor por defecto. Con 1981–2024, la configuración inicial propone 1981–2002 y 2003–2024. Permitir ajustar ambas ventanas dentro de la cobertura y recalcular al cambiar zona, celda o variable. | Fechas, años completos por período, diferencia de promedios B − A y diferencia descriptiva de pendientes B − A. Mapas A y B con escala común por variable. |
| Caso El Niño | Seleccionar por defecto el episodio más reciente que el IMN documente y que esté completo dentro del paquete. Comparar con la ventana neutral anterior más cercana de igual duración y los mismos meses calendario, con fase verificada en los boletines del IMN. Mostrar también anomalías respecto a 1981–2010 con base por mes calendario. | Series mensuales, anomalías y mapa de diferencia por celda. Para lluvia, usar mm/mes y comparar meses equivalentes. El sitio informa cuando falta una referencia neutral verificable y conserva la comparación con la climatología donde sea calculable. |
| Evidencia de largo plazo | Mostrar 1981–2024 como referencia complementaria si cada serie tiene cobertura suficiente. | Pendiente e inferencia por celda y zona. Las ventanas iniciales de 22 años muestran pendientes descriptivas. La inferencia requiere al menos 30 años anuales completos y consecutivos. |

La diferencia entre pendientes y los resultados por episodio se presentan como descriptivos. El sitio conserva las fechas y filas realmente usadas, muestra cobertura desigual y, ante datos insuficientes en una celda, señala el faltante sin mover la ventana del resto del mapa. La coincidencia temporal con El Niño permite formular hipótesis. Evaluar causalidad requeriría otro diseño.

## 3. Tendencia, incertidumbre y significancia

- **OLS** estima la pendiente por década y el cambio ajustado entre el primer y último año utilizados. Con menos de 10 años válidos, mostrar «datos insuficientes». Con al menos 10 años y sin cumplir los requisitos de inferencia, mostrar «tendencia descriptiva».
- **HAC de Newey–West** con pesos Bartlett, tres rezagos anuales, corrección de muestra pequeña y referencia t para el IC individual del 95 % y el p bilateral de OLS. Usar uno y cinco rezagos como sensibilidad. Exigir 30 años completos y consecutivos dentro de la ventana. En ajustes degenerados, reportar solo la magnitud identificable.
- **Benjamini–Yekutieli (BY)** ajusta los p válidos de las celdas de todas las zonas publicadas para cada variable y ventana. Las pruebas de promedios regionales se corrigen en su propia familia, con las dos variables y todas las zonas publicadas por ventana. El mapa usa p ajustado ≤ 0,05 para marcar evidencia. Filtrar el mapa conserva el ajuste original. Registrar tamaño de familia, alcance y cantidad de pruebas evaluables. El IC de HAC se etiqueta como individual.
- **Sen y Mann–Kendall** complementan OLS. Mostrar la pendiente de Sen usando años calendario. Para inferencia usar Mann–Kendall bilateral, con corrección de empates y variante de Hamed–Rao para autocorrelación, bajo los mismos requisitos de cobertura. Registrar la variante y sus parámetros. Si se publica p ajustado de Mann–Kendall, calcularlo con BY en familias propias del método. Mostrar desacuerdos entre métodos en el detalle y exportar ambos resultados.

## 4. Predicción con datos propios de Costa Rica

Entregar un pronóstico experimental a un mes para temperatura y lluvia por zona con series meteorológicas locales del IMN o datos del equipo con procedencia verificable. Entrenar y evaluar con datos costarricenses. Propuesta inicial: un modelo sencillo por estación representativa con el mes del año y rezagos locales, comparado con la climatología mensual de esa estación. Mostrar la ubicación de la estación y el período de entrenamiento. Incorporar fase ENOS como predictor solo si hay un registro oficial que reproduce lo que se conocía en la fecha del pronóstico.

Evaluar con cortes cronológicos y comparar el error absoluto medio con el de la climatología mensual, calculada solo con los datos de entrenamiento de cada corte. Reportar el error por variable y zona. Mostrar un rango predictivo solo si puede calibrarse con observaciones fuera de muestra. Publicar el pronóstico para las zonas con cobertura y validación suficientes y señalar la disponibilidad en las demás. Si las series locales no llegan a tiempo, conservar el estado «pronóstico pendiente de datos locales» y registrar el criterio como pendiente para el MVP. La comparación histórica permanece usable. Estimar la distribución futura de agua requiere históricos operativos y validación propios.

## 5. Recorrido del sitio

1. **¿Qué cambió?** Elegir un recorrido de **calor** o **lluvia** y ver las dos ventanas, su magnitud de cambio, la serie temporal y el caso El Niño.
2. **¿Dónde cambió?** Navegar por las zonas habilitadas, comparar mapas por celda con leyendas y seleccionar una celda para abrir su serie y estadísticas. En lluvia, consultar la cobertura del servicio de agua, los operadores y los registros disponibles de distribución. Mostrar el área geográfica, el período y la fuente de cada dato.
3. **¿Qué tan fuerte es la evidencia?** Revisar magnitud, incertidumbre, significancia e inferencia disponible, abrir la comprobación Sen/Mann–Kendall y consultar la predicción local cuando esté validada. Generar una ficha de detective para la selección actual.

La ficha reúne variable, zona/celda, fechas, cambios, evidencia, hallazgos del episodio, pronóstico si está disponible y las fuentes y limitaciones. En el recorrido de lluvia incluye la cobertura del servicio de agua disponible para el área consultada. La web la muestra en pantalla, permite imprimirla y ofrece las siguientes descargas.

- **CSV** en UTF-8, con tablas separadas para series, resultados y cobertura del servicio de agua. Las filas climáticas conservan claves de zona/celda y ventana, variable, unidad y estado. Las filas de cobertura incluyen período, unidad geográfica, indicador, unidad, valor, denominador del porcentaje y operador cuando corresponda. Usar identificadores para enlazar al CSV de fuentes y limitaciones.
- **JSON** versionado con ventanas, celdas, series, estadísticas, configuración de métodos, fecha de descarga, versiones, licencia cuando esté disponible, enlaces de origen y texto de las limitaciones. Incluir la procedencia y validación del pronóstico y los mismos campos de cobertura del servicio que en el CSV. Usar `null` para faltantes.

## 6. Orden de trabajo

| Entrega | Responsables propuestos | Criterio de salida |
|---|---|---|
| 1. Datos y catálogo | Samuel + Jacky | Confirmar las dos zonas iniciales, fechar El Niño con IMN y registrar la disponibilidad de estaciones, registros de distribución e indicadores de cobertura del servicio de agua. Definir las firmas de consulta y exportación. |
| 2. Comparación y ciencia | Emanuel + Jacky, revisión de Diego | Reutilizar `src/prepare.py`; entregar ambos modos de comparación, OLS/HAC/BY, Sen/Mann–Kendall y casos de prueba. Conectar el servicio real. |
| 3. Web y relato | Kevin + Joshua | Completar primero el recorrido de calor de extremo a extremo. Replicar para lluvia, conectar el mapa y la capa hídrica, y generar ficha, CSV y JSON. |
| 4. Pronóstico local | Emanuel + Samuel, validación de Diego | Entrenar y evaluar cronológicamente para la primera zona con datos locales aprovechables. Documentar resultado o bloqueo con la fuente que falta. |
| 5. Demostración | Jacky + Diego, con Kevin y Joshua | Arrancar en limpio, publicar una URL que abra en ventana privada y verificar ambos recorridos y descargas contra datos reales. Llevar como respaldo la ejecución local con el paquete de datos. |

## 7. Pruebas de aceptación

- Los dos recorridos funcionan con NASA POWER real. Cambiar la zona, la variable o la ventana actualiza series, mapas, ficha y descargas. Cada celda puede abrirse desde el mapa.
- El valor de una celda se puede rastrear desde el mapa y el CSV hasta el archivo crudo. La UI conserva unidades y las diferencias de cobertura.
- Validar bisiestos, valores cero, huecos, constantes, ≥30 años consecutivos, autocorrelación y BY con fixtures. Verificar que el filtrado conserve los p ajustados y que los mapas de las dos ventanas usen la misma escala.
- El caso El Niño abre con fechas documentadas y muestra cómo se eligió la referencia. El recorrido de lluvia muestra al menos un dato verificable de cobertura del servicio de agua con su año, indicador, unidad geográfica y fuente, junto con la disponibilidad de registros de distribución. La ficha, el CSV y el JSON conservan el mismo indicador de cobertura. El pronóstico incluye evaluación temporal o el bloqueo explícito.
- El sitio ofrece una ficha legible en móvil y escritorio. La misma selección da resultados concordantes en pantalla, CSV y JSON.

## Fuentes

- [AyA y Laboratorio Nacional de Aguas, estimación de cobertura y calidad del agua con datos del INEC](https://www.aya.go.cr/transparenciainst/rendicion_cuentas/planesespecificossectorial/agua%20para%20consumo%20humano%20y%20saneamiento%20en%20costa%20rica%20al%202020_%20brechas%20en%20tiempos%20de%20pandemia.pdf).

- [Reto NASA Space Apps](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/) · [NASA POWER y MERRA-2](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/) · [API mensual de NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/).
- [Boletín ENOS del IMN](https://imn.ac.cr/boletin-enos) · [Boletín COENOS](https://www.imn.ac.cr/es/web/imn/boletin-coenos) · [Servicios del IMN](https://imn.ac.cr/solicitud-de-servicios) · [Datos abiertos de ARESEP](https://aresep.go.cr/datos-abiertos/) · [AyA, información sobre interrupciones](https://www.aya.go.cr/transparenciaInst/acceso_informacion/Documents/Preguntas%20frecuentes.pdf).
- [HAC en statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html) · [Corrección por pruebas múltiples](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) · [Pendiente de Sen](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html) · [Mann–Kendall modificado por Hamed y Rao](https://doi.org/10.1016/S0022-1694(97)00125-X).
