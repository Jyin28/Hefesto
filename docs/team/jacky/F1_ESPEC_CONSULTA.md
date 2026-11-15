# F1 — Especificación de consulta y soporte (J1.2–J1.6) — PROPUESTA

Estado: **propuesta sin acuerdo ni aprobación**. Nada aquí está implementado. Los contratos v2 vigentes (`src/contracts.py`, `schema_version="2.0"`) no cambian; lo nuevo entra por adaptadores o con una versión nueva acordada.

## J1.2 Matriz de soporte
| Producto | Zona/celda | Resolución | Ventana | Fuente | Estado |
|---|---|---|---|---|---|
| historical (T2M, PRECTOTCORR) | CR_PN, CR_CAR; celdas nativas | ~0,5° × 0,625° | 1981–2024 [verificar] | NASA POWER mensual (Samuel) | datos en main; servicio real pendiente → mock `available`+synthetic |
| event (ENOS 1997-06..1998-05) | CR_PN, CR_CAR | mensual | baseline 1981–2010, ≥24 valores/mes | misma | P1; `unavailable` (`get_event_view`) |
| forecast | — | — | — | sin dataset ni modelo definido | `unavailable`, razón `forecast_not_validated` |
| water_distribution | — | — | — | sin registros ni fuente | `unavailable`, razón `no_source` |
| service_coverage | — | — | — | sin denominador | `unavailable`, razón `no_denominator` |
| zonas libres / IDN / EEP | — | — | — | fuera de MVP | `unsupported` |

## J1.3 AnalysisQuery, AnalysisScope, ServiceResponse
- `AnalysisQuery`: product, variable, zone_ids, cell_ids, spatial_level (zone|cell), start_date, end_date, time_resolution, preset_id, event_id, baseline. Selectores incompatibles → `ValueError`.
- `AnalysisScope`: scope_id, scope_version, zones, variables, cell_ids, window, correction_method, alpha, planned_tests. Cambiarlo cambia `family_id`; ocultar una zona no.
- `ServiceResponse`: schema_version, request_id, product, query_requested, query_effective, result_id, availability{status, reason_code, message, missing_requirements, available_range, checked_at, retryable}, source_mode (mock|real|mixed|unknown), synthetic (bool|null), payload, provenance, geographic_context, data_coverage, limitations, warnings.
- `availability.status`: available | partial | unavailable | unsupported | stale | error. Se mantiene **separado** de `TrendResult.status`, `level`, `synthetic` y frescura.
- Versionado: `QueryParams` y los wrappers v2 se conservan; `ServiceResponse` envuelve su salida. Si se rompe un campo, `schema_version="3.0"` + adaptador. Decisión con Kevin y Emanuel.

## J1.4 Catálogo de zonas y celdas
- `ZoneSpec`: zone_id, label, zone_kind, bbox, crs, zone_version, geometry_sha256, mask_version, cell_ids, source_ids, limitations. MVP: CR_PN y CR_CAR como presets (`RegionSpec` actual).
- `CellSpec`: cell_id (grid_id + lat/lon del centro nativo), grid_version, footprint, native_resolution. Una celda puede pertenecer a varias zonas; se deduplica por `cell_id` antes de la familia del mapa.
- Fuente del catálogo MVP: `regions.VERIFIED_LAND_CELLS` (5 celdas por sector).

## J1.5 Ejemplos de respuesta
```json
{"product":"historical","source_mode":"mock","synthetic":true,"availability":{"status":"available","reason_code":null}}
{"product":"historical","source_mode":"real","synthetic":false,"availability":{"status":"partial","reason_code":"missing_months","missing_requirements":["2024-11","2024-12"]}}
{"product":"forecast","source_mode":"unknown","synthetic":null,"availability":{"status":"unavailable","reason_code":"forecast_not_validated"},"payload":null}
{"product":"historical","source_mode":"real","synthetic":false,"availability":{"status":"stale","reason_code":"snapshot_expired"}}
```
Un resultado real esperado sale del servicio real (F2/F3); no se incluye un ejemplo numérico inventado.

## J1.6 Acuerdos pendientes
| Acuerdo | Aporta | Estado |
|---|---|---|
| Qué se pronostica, horizonte, validación | Emanuel + Samuel | abierto; sin él, `unavailable` |
| Fuente/granularidad/denominadores de agua | Samuel (+Emanuel, Joshua explica límites) | abierto |
| Familia BY para zonas nuevas | Emanuel | abierto; MVP usa 4 pruebas regionales + celdas de ambos sectores |
| Transporte: funciones locales vs. JSON/HTTP | Kevin + Jacky | abierto; por defecto funciones locales (Streamlit) |
| Criterios de URL, formato local, segundo equipo | Diego | abierto |
| Prioridad/costo de pronóstico y agua frente al plan v2 | Equipo | **fuera del presupuesto base (13 h + 2 h)** |

Handoff (sin enviar): Samuel → IDs de celda y muestra; Emanuel → familia/target; Kevin → estados de availability y forma de `build_evidence_card`.
