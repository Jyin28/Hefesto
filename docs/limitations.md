# Limitaciones de Hefesto v2 — Detective Tico

Este documento explica con honestidad qué puede y qué no puede decir Hefesto v2. Léelo antes de interpretar una Ficha de Detective.

> **Uso exclusivamente educativo** (colegios, universidades y aprendizaje comunitario). Hefesto v2 **no está validado** para alertas tempranas, racionamiento, operación de ASADAS, agricultura ni emergencias, y **aún no ha sido validado con usuarios externos**.

---

## 1. Fuente y naturaleza de los datos (verificado en `DATA_SOURCES.md`)

- **Fuente oficial:** datos mensuales de NASA POWER, basados en el sistema de reanálisis **MERRA-2**, período **1981–2024** (44 años completos, 528 meses). *(S1)*
- **Naturaleza del dato:** son **estimaciones de un modelo atmosférico con asimilación de observaciones**. **No** son mediciones directas de estaciones meteorológicas ni de satélites puntuales.
- Por ser un modelo, puede haber diferencias respecto a lo que mide una estación local, sobre todo en lluvia y en zonas de relieve complejo.

## 2. Escala espacial (verificado en `DATA_SOURCES.md`)

- La cuadrícula nativa es de **0.5° × 0.625°**, equivalente a **~55 km × 69 km por celda**. *(S2)*
- Cada sector didáctico agrupa **5 celdas terrestres elegibles**:
  - `CR_PN` (Pacífico Norte): bbox `[-86.0, 9.75, -85.0, 11.25]` → **5 celdas**.
  - `CR_CAR` (Caribe): bbox `[-84.0, 9.5, -82.75, 10.75]` → **5 celdas**.
- Los sectores **no son límites de provincias, cantones, fincas ni cuencas oficiales**. Hefesto no describe un lugar puntual.
- **Mezcla mar/tierra:** en las celdas costeras, un mismo valor puede reflejar una combinación de tierra y mar. Por eso los resultados se interpretan a escala regional.

## 3. Qué mide cada variable y qué no

| Variable | Sí sirve para | NO mide |
|---|---|---|
| `T2M` | Estudiar cambios del calor a escala regional (temperatura del aire a 2 m). | **Temperatura del mar** (aire ≠ mar), sensación térmica ni temperatura en un sitio puntual. |
| `PRECTOTCORR` | Evaluar la **precipitación acumulada (mm/año)** a escala regional. | **Caudal de ríos, recarga de acuíferos ni disponibilidad de agua potable** (lluvia ≠ caudal/recarga/suministro). |

## 4. Reglas estadísticas del producto

1. **Anualización:** solo se usan años con los **12 meses completos**.
2. Según la cantidad de años (`n`):

| Situación | Qué se calcula | Qué NO se calcula |
|---|---|---|
| `n < 10` | Sin ajuste. | Pendiente, valor p ni IC. |
| `10 <= n <= 29` | Pendiente descriptiva por década. | Valor p ni IC. |
| `n >= 30` años **consecutivos** | OLS con errores estándar HAC (kernel Bartlett, `L=3`; sensibilidad con `L=1` y `L=5`), IC 95 % y valor p. | — |
| Huecos internos | Pendiente descriptiva con los **años reales**. | No se comprimen los años faltantes ni se calcula p inferencial. |

3. **Corrección por comparaciones múltiples:** los valores p se ajustan con **Benjamini-Yekutieli (BY, `alpha=0.05`)** sobre la familia de **2 variables × 2 sectores** (4 pruebas). "Significativo" significa que sobrevive a esa corrección.

### Cómo leer el resultado

- **"No significativo" significa evidencia insuficiente bajo este modelo, no "ausencia de cambio".** Agregar más años **no garantiza** reducir `p`.
- **Descriptivo:** la pendiente solo resume los datos disponibles.
- Una **tendencia lineal** es un resumen simple: no captura ciclos ni saltos. Una pendiente por década **no es un pronóstico**.
- Un resultado significativo **no indica causa**.

## 5. Contexto de Costa Rica: ENOS

Un artículo de la Universidad de Costa Rica (UCR) explica que **El Niño y La Niña** son dos caras de un mismo fenómeno climático y que influyen de forma distinta en las vertientes del Pacífico y del Caribe. *(S5)*
Fuente: <https://www.ucr.ac.cr/noticias/2023/7/12/el-nino-y-la-nina-dos-caras-de-un-mismo-fenomeno-climatico/>

En Hefesto v2 hay que tener claro que:

- ENOS es **variabilidad interanual**, no una tendencia lineal de largo plazo.
- ENOS **no prueba causalidad** de ninguna pendiente de una Ficha de Detective.
- ENOS **no garantiza tendencias opuestas** entre `CR_PN` y `CR_CAR` en 1981–2024: pueden ser parecidas, distintas o no detectables.
- Hefesto v2 no separa ni cuantifica el efecto de ENOS.

## 6. Usos NO aptos

No usar los resultados para: alertas tempranas, racionamiento, operación de ASADAS o acueductos, agricultura (siembra, riego, cosecha), emergencias, decisiones sobre una finca, cantón o comunidad concretos, ni para atribuir causas. Para esos fines, consultar a las instituciones oficiales y a estaciones locales.

## 7. Reproducibilidad

Hefesto v2 **no usa LLM ni IA generativa en tiempo de ejecución**. Las recomendaciones, los cálculos y los textos de la Ficha de Detective son deterministas y reproducibles sin conexión. Ver `AI_USAGE.md`.

## 8. Referencias (IDs usados en `docs/claims.csv`)

| ID | Referencia |
|---|---|
| `DATA_SOURCES.md` | Metadatos verificados por Samuel. |
| S1 | NASA POWER, datos mensuales (reanálisis MERRA-2). |
| S2 | Documentación/metadatos de resolución de NASA POWER. |
| S3 | statsmodels: OLS con covarianza HAC. |
| S4 | Benjamini y Yekutieli (2001), control de la tasa de falsos descubrimientos bajo dependencia. |
| S5 | Artículo UCR sobre El Niño y La Niña (enlace en la sección 5). |

## 9. Calidad de la lluvia de reanálisis (diagnóstico de la rama MVP)

- Los totales anuales de `PRECTOTCORR` suben de ~1 000–1 500 mm/año (años 80–90) a más de 3 000 mm/año en años recientes en ambos sectores
  (p. ej. Caribe 803 mm en 1994 frente a 5 079 mm en 2024; Pacífico Norte 352 mm en 1994 frente a 3 732 mm en 2024).
  Las pendientes resultantes (+402 y +592 mm/año por década) son enormes y **no están validadas con estaciones**.
- NASA POWER indica que los datos más recientes pueden provenir de GEOS-IT, que carece de la normalización por pluviómetros de MERRA-2;
  no documenta una ruptura específica. La prueba de Pettitt sobre residuos **no** detecta un salto de nivel único (p≈0,2–0,4), y la
  tendencia es robusta al año final (2020, 2023 o 2024). Con esto, el patrón puede ser deriva del reanálisis o cambio real: **no se puede distinguir sin estaciones**.
- Regla del producto: la tendencia se muestra siempre (no se oculta ni se cambia el período), con la advertencia `reanalysis_precip_caution`
  en pantalla, ficha y exportación. Nunca presentar estas magnitudes como lluvia observada ni derivar decisiones de agua.
- La advertencia `possible_inhomogeneity` se activa solo si Pettitt (sobre residuos OLS) da p < 0,05 y se calcula igual para ambas variables.
- Pendiente humana: contrastar con estaciones del IMN.

## 10. Alcance del MVP
Fuera de alcance y no incluidos en la app: pronóstico, cobertura de agua/ASADAS, cantones, mapa web React.
