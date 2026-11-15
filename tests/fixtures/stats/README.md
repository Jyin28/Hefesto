# Fixtures sintéticos — EMANUEL-02

Los fixtures son referencias numéricas sintéticas para las pruebas de preparación y
estadística. Las regiones, unidades de salida y familia regional BY siguen el contrato
v2 publicado en `main`. Cada JSON documenta sus propias entradas y expectativas.
Las convenciones pendientes se registran en
[las decisiones de Emanuel](../../../docs/team/emanuel/decisions.md).

Todos los `.json` de este directorio:
- tienen `"synthetic": true`,
- declaran `unit` (y `unit_slope` o `unit_annual` cuando aplica),
- declaran `status` + `status_note` describiendo el estado inferencial o de cobertura,
- separan `input` (dato sintético) de `expected` (valor de referencia independiente).

Regenerarlos: `python tests/fixtures/stats/generate_and_verify.py` (determinista, sin
dependencias externas). El script comprueba los valores de referencia y falla con
`AssertionError` si alguno difiere.

## Mapeo a la tabla de EMANUEL-02

| Fixture | Caso de la tabla | Qué cubre |
|---|---|---|
| `linear_trend_increase.json` | Aumento | Inspección de una serie anual exacta, pendiente/cambio ajustado |
| `linear_trend_decrease.json` | Disminución | Idem, pendiente negativa |
| `seasonality_no_trend.json` | Estacionalidad | Ciclo julio/agosto (31 días cada uno) sin tendencia, anomalías cero |
| `ar1_seed42.json` | Autocorrelación | Serie AR(1) reproducible con `random.Random(42)`, referencia OLS por sumas centradas |
| `incomplete_year.json` | Año incompleto | **Un faltante**: 11 meses válidos, cero distinto de ausente |
| `regional_coverage.json` | Cobertura regional | Dos celdas de `CR_PN`. Cobertura de 100 % con ambas y de 25 % con la segunda ausente |
| `leap_year_precip.json` | Bisiesto | Acumulado anual de 730 y 732 mm/yr a partir de 2 mm/día |
| `constant_precip.json` | Constante | Serie anual en mm/yr, pendiente y cambio cero, ajuste degenerado |
| `by_correction.json` | BY | Familia regional de cuatro pruebas e invarianza ante permutación |
| `anomaly_enso.json` | Anomalía | **Una anomalía**: con y sin referencia disponible |

El caso AR(1) comprueba reproducibilidad y concordancia entre dos fórmulas OLS.
La verificación de la covarianza HAC corresponde a EMANUEL-07.
