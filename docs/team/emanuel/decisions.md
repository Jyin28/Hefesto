# Decisiones de análisis estadístico — EMANUEL-01

Revisión contra el contrato v2 de Jacky publicado en `main` (`4b17e3d`).
Las [decisiones del equipo](../../decisions.md) y [el contrato](../../../src/contracts.py)
definen la integración. Los fixtures de [EMANUEL-02](../../../tests/fixtures/stats/README.md)
aportan referencias numéricas sintéticas para Emanuel y Diego.

| Punto | Base de trabajo v2 | Por resolver |
|---|---|---|
| Regiones | Pacífico Norte (`CR_PN`) y Caribe (`CR_CAR`) de Costa Rica. La ventana objetivo es 1981–2024. | Samuel verifica cobertura, rejilla, máscara y pesos con datos reales. |
| Temperatura y precipitación | `T2M` anual en °C, ponderada por días reales. `PRECTOTCORR` mensual en `mm/day` según el contrato y anual acumulada en `mm/yr`: sumar tasa mensual × días del mes. Pendientes en `degC/decade` y `mm/yr/decade`. | Samuel verifica la unidad mensual y los códigos de faltantes en la fuente. |
| Cobertura y año completo | La propuesta de Emanuel usa pesos por región, máscara fija y 12 meses válidos. Una celda ausente reduce la cobertura ponderada de su propia región. El fixture devuelve una media ausente si falta cualquier peso positivo. | Jacky y Samuel confirman el umbral y cómo se resume la cobertura en `TrendResult.coverage_fraction`. El mock devuelve 1.0 porque simula datos completos. |
| Magnitud | OLS con años calendario. Para pendiente anual b, la pendiente por década es 10b y el cambio ajustado es b × (último año usado − primer año usado). El mock usa `none` / `insufficient_data` con menos de 10 años, y `descriptive` / `ok` de 10 a 29. | Jacky y Diego confirman el mapeo de huecos y ajustes degenerados. |
| Inferencia | El mock habilita el nivel `inferential` desde 30 años. Para el ajuste real, Emanuel propone 30 años completos y consecutivos, HAC Bartlett con L=3 y sensibilidad L=1 y L=5, prueba bilateral e IC individual del 95 %. | Confirmar tratamiento de huecos, corrección de muestra pequeña, referencia t y tolerancia para covarianza degenerada. Los valores inferenciales del mock son marcadores. |
| Multiplicidad | BY regional sobre las cuatro pruebas planificadas por ventana: dos variables × dos regiones. El filtrado conserva los p ajustados de la familia completa. | Jacky confirma el tratamiento de pruebas regionales no evaluables y la familia del mapa cuando publique el contrato de celdas. El fixture de cuatro pruebas usa todos los p válidos. |
| Anomalías (P1) | Se conserva una referencia matemática de anomalía mensual. | Confirmar alcance, fechas, cobertura de la climatología y esquema de la vista con Jacky y Samuel. |

Samuel aporta una muestra mensual cruda por región y su procedencia. Diego revisa
las referencias numéricas y las tolerancias antes de probar el ajuste real.

## EMANUEL-03 — `src/prepare.py` (preparación mensual/anual regional)

Implementado en stdlib puro (sin pandas/numpy: no están instalados en este
entorno y coincide con la convención `list[dict]` de `src/contracts.py` /
`src/service_mock.py`). Toma filas celda-mes con la misma forma de columnas
que producen `src/ingest.py` + `src/regions.py` (rama `feat/data-cr-v2` de
Samuel) y la máscara de pesos de `src/regions.py::build_masks_df`, y entrega
`RegionalMonthly` y `RegionalAnnual` como listas de dicts.

- 12 meses válidos y días reales: `T2M` anual = media ponderada por días de
  cada mes (`sum(dias_mes * valor) / dias_año`); `PRECTOTCORR` anual =
  acumulado (`sum(dias_mes * tasa_mm_día)`). Bisiestos vía `calendar.isleap` /
  `calendar.monthrange` (stdlib), no una fórmula propia.
- Cero (`0.0`) es un valor válido; solo `value is None` cuenta como faltante.
  Se guarda además una comprobación defensiva de sentinelas sin limpiar
  (`value <= -900`, ver `fill_value` de NASA POWER en `src/ingest.py`).
- Cobertura ponderada dentro de cada región: `weighted_mean()` replica
  exactamente `tests/fixtures/stats/generate_and_verify.py::weighted_mean`
  (mismos fixtures, mismos valores de referencia). **Política PROVISIONAL**:
  `COVERAGE_THRESHOLD = 1.0`, o sea que una sola celda ausente ese mes deja el
  valor regional-mes como ausente (no se promedia con lo disponible). Un año
  sin los 12 meses válidos también queda sin valor anual (`complete=False`,
  warning `incomplete_year`), siguiendo la fila "Cobertura y año completo" de
  arriba.
- Duplicados (misma celda-mes repetida) y pesos de máscara mal normalizados
  (no suman 1.0 por región) son errores fatales (`ValueError`); meses
  ausentes son solo informativos (`run_qc` los reporta, no los bloquea: un
  hueco real de NASA POWER es un dato legítimo, no un bug).

### Pendiente de confirmar con Jacky (y Samuel para el dato real)
1. ¿`COVERAGE_THRESHOLD=1.0` es la regla final, o se permite un umbral menor
   con datos reales (huecos legítimos de NASA POWER)? Define cuántos
   región-mes/región-año quedarán sin valor en la práctica.
2. ¿Año incompleto → valor anual ausente (regla actual) es lo que debe
   publicar el contrato v2, o se prefiere un promedio parcial con aviso?
3. `mean_monthly_coverage` es un campo nuevo que no existe en
   `TrendResult`/`contracts.py`: ¿viaja como parte del contrato `RegionalAnnual`
   cuando se defina ese tipo, o se queda como diagnóstico interno de
   `prepare.py`?
4. Sigue abierto Q1 de `docs/decisions.md` (unidad mensual `mm/day` y
   cobertura 1981–2024 con muestra real): `prepare.py` asume que `src/ingest.py`
   ya entrega datos limpios (sin `fill_value`) en esas unidades.
