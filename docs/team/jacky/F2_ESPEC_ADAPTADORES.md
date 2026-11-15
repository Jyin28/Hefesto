# F2 — Especificación de adaptadores de datos y ciencia (J2.2)

Estado: **[PROPUESTA]**, pendiente de acuerdo con Samuel, Emanuel y Kevin. El mock (`src/service_mock_f2.py`) ya cumple estas formas con datos sintéticos; el servicio real (`src/service.py`, no creado) debe devolver las mismas firmas y tipos (`src/contracts_ext.py`) sin exigir los mismos números.

## Reglas comunes

- Toda función recibe `AnalysisQuery` y devuelve `ServiceResponse` (versión `2.1-proposal`). Los contratos v2 y sus wrappers (`get_annual_series`, `get_trend`, `get_comparison`, `get_cell_trends`, `build_*`) siguen intactos.
- Consulta mal formada → `ValueError` legible. Consulta válida sin datos → `availability` (`available|partial|unavailable|unsupported|stale|error`) con `reason_code`; nunca un cero ni un éxito falso.
- `source_mode` es `mock|real|mixed|unknown`; `synthetic` es `true|false|null`. `unknown`/`null` impide presentarlo como real.
- El servicio real nunca cae a mock en silencio (D6). Un módulo caído devuelve `error` con `retryable`, no `insufficient_data`.
- Fechas ISO inclusivas. Los huecos conservan el eje temporal real: nada se rellena ni se comprime.
- `query_effective` refleja la ventana realmente servida; la pedida queda en `query_requested`.

## Adaptador de datos (Samuel → servicio)

| Entrada requerida | Forma | Error esperado si falta |
|---|---|---|
| Catálogo de zonas y celdas | `ZoneSpec`, `CellSpec` con `zone_version`, hashes de geometría/máscara, `cell_id` nativo estable | `unavailable / no_data_for_zone` |
| Serie mensual por celda | `time` (primer día del mes), `value`, `unit`; NaN en DataFrame, `null` en JSON | huecos → `partial / window_truncated` |
| Manifest de fuente | `source_ids`, `retrieved_at`, `provider_version`, `data_sha256` | `provenance` con `unknown` |
| Registros de agua (J2.4) | ver sección 7 de `00_LEEME_JACKY.md` | `unavailable / mock_product_pending` hasta existir |

Una celda puede pertenecer a varias zonas. El mapa deduplica por `cell_id` antes de formar la familia.

## Adaptador de ciencia (Emanuel → servicio)

| Función | Qué recibe de Emanuel | Reglas |
|---|---|---|
| `get_series` | agregación anual y mensual (T2M ponderada por días; lluvia desde tasa mensual) | `months_valid` y `complete` obligatorios |
| `get_map` | pendiente, `p`, `q` por celda y metadatos de familia BY | familia completa antes de filtrar la vista |
| `get_event_series` | climatología mensual y baseline (default 1981–2010, mínimo 24 valores por mes) | descriptivo; baseline corto → `anomaly: null`, `partial / baseline_insufficient` |
| `get_local_forecast` (J2.4) | `ForecastMetadata`: modelo, emisión, corte, horizonte, validación, intervalos | sin modelo o validación → `unavailable`; sin extrapolar tendencia |

El servicio orquesta y transporta. No implementa una segunda HAC ni BY; el mock usa marcadores y lo declara (`mock_inference_placeholder`).

## Errores y estados esperados por adapter

| Situación | `status` | `reason_code` |
|---|---|---|
| zona sin celdas o datos | unavailable | `no_data_for_zone` |
| ventana fuera de cobertura | unavailable | `out_of_coverage` |
| cobertura parcial | partial | `window_truncated`, `zones_without_data` |
| baseline insuficiente | partial | `baseline_insufficient` |
| snapshot fuera de vigencia | stale | `snapshot_expired` |
| resolución/producto/métrica fuera de contrato | unsupported | `resolution_not_supported`, `wrong_product`, `metric_not_supported` |
| fallo técnico | error | `internal_error` (`retryable: true`) |

## Productos de J2.4 (forecast, agua, cobertura del servicio)

| Función | Entrada que debe aportar el adapter real | Códigos propios |
|---|---|---|
| `get_local_forecast` (Emanuel) | `ForecastMetadata` completo: modelo, emisión, corte, horizonte, `valid_until`, validación (método, período, benchmark, métrica) e intervalos con método y nivel | `no_forecast_model`, `forecast_not_validated`, `forecast_validation_failed`, `forecast_expired`, `out_of_forecast_range`, `forecast_cell_not_supported`, `forecast_single_zone_only` |
| `get_water_distribution` (Samuel) | `WaterRecord` versionado: programado, observado y corregido separados, con `corrects_record_id`/`superseded_by`; crosswalk zona→área de servicio | `no_water_records`, `out_of_water_range`, `zones_without_records`, `water_cell_not_supported` |
| `get_service_coverage` (Samuel + Emanuel) | Registros más denominador compatible (fuente y versión); definición del indicador acordada | `denominator_missing`, `denominator_zero`, `not_reported` (por indicador), `no_cross_zone_average` |

Reglas:
- Un pronóstico no validado no se muestra como predicción. La metadata viaja siempre para explicar la ausencia.
- Intervalo de pronóstico y IC de tendencia son objetos distintos; el `p` de tendencia no es confianza del pronóstico.
- Pausa registrada (observado 0), cero reportado y sin reporte son estados distintos. Planificado no equivale a entregado.
- Un porcentaje con denominador ausente o cero es `null` con razón. No se recorta a 100 % (flag `exceeds_100`) y no se promedia entre zonas.
- `variable` es `None` en productos de agua; la cobertura del servicio no se deduce de lluvia ni de la cobertura de datos.

## Caché y snapshots (J2.5: `src/snapshots.py`)

El adapter aporta tres hooks; la caché es agnóstica del proveedor. Mock: `input_manifest`, `normalize_query`, `refresh_freshness` en `service_mock_f2.py`.

- **Clave** = `<source_mode>:<sha32>` de función + consulta normalizada + solo las secciones del manifest que el producto usa. Mock y real no comparten entradas porque el prefijo difiere.
- **Normalización:** ids ordenados y sin duplicados; para evento se rellenan ventana y baseline por defecto.
- **Fuera de la identidad:** `generated_at`, `checked_at`, hipótesis y orden de los ids.
- **No se cachean** `error` ni `unsupported`. `unavailable` y `partial` sí.
- **Frescura:** se reevalúa en cada lectura (`valid_until` contra el reloj). El snapshot guardado y su `issued_at` no cambian.
- **Persistencia:** `save`/`load` escriben un JSON estricto por snapshot.

| Producto | Secciones del manifest en la clave |
|---|---|
| historical | schema, code, method, geo, family_data |
| event | historical + event (event_id, baseline, soporte temporal) |
| forecast | historical + forecast (modelo, config, emisión, corte, horizonte, validación) |
| water_distribution | schema, code, geo, water (dataset, correcciones), crosswalk |
| service_coverage | water_distribution + indicator_definition, denominator (fuente y versión) |

Matriz de invalidación (`INVALIDATION_MATRIX`, derivada de la tabla): zona/geometría/máscara/malla invalidan todo; `family_data` y `method`, los productos climáticos; `baseline` y `event_id`, evento; modelo/emisión/corte/horizonte, forecast; dataset/correcciones/crosswalk, agua y cobertura; definición y denominador, solo cobertura.

## Export y ficha (J2.6: `src/export_f2.py`)

Serializa el mismo `ServiceResponse` que muestra el sitio; no recalcula.

- `build_evidence_card_ext`: campos v2 de la ficha más `product`, `availability`, `source_mode`, `query_effective`, `geographic_context`, `data_coverage` y los tres `*_metadata`. Resumen por plantilla determinista. `presentable_as_real` solo es true con `source_mode=real` y `synthetic=false`.
- `build_export` devuelve `manifest.json` (tablas presentes y ausentes con razón), `evidence.json`, `provenance.json` (si existe), `ficha.md` y los CSV del producto: `series`, `cells`, `event_series`, `forecast`, `water_distribution`, `water_records`, `service_coverage`.
- CSV: UTF-8, coma, punto decimal, ausente = celda vacía, anidados = JSON compacto, booleanos `true/false`. Cada fila lleva `result_id`, `product` y sus claves de unión. Sin datos no hay CSV: la tabla va a `tables_absent`.
- Ejemplos reproducibles para Kevin: `docs/team/jacky/examples/` (14 casos), generados con `python scripts/build_examples_f2.py`.

## Identidad de resultado

`result_id = compute_result_id(query_effective, data_sha256, mask_version)`. `request_id` del mock es determinista; el real puede usar otro esquema. `generated_at`, `checked_at` y la hipótesis no entran en la identidad. Mock y real no comparten caché.

## Pendiente de acuerdo

Forma final de `QueryParams.regions` frente a `zone_ids`, tolerancias numéricas de Emanuel, y si Kevin consume funciones o un bundle JSON.
