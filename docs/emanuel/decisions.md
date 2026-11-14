# Decisiones de análisis estadístico — EMANUEL-01

Revisión contra el contrato v2 de Jacky publicado en `main` (`4b17e3d`).
Las [decisiones del equipo](../decisions.md) y [el contrato](../../src/contracts.py)
definen la integración. Los fixtures de [EMANUEL-02](../../tests/fixtures/stats/README.md)
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
