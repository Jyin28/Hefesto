# Decisiones y preguntas de contrato

## 2026-11-14 — F1 (Jacky)
- D1: Contratos en `src/contracts.py` con dataclasses frozen, solo stdlib, sin I/O al importar.
- D2: `RegionSpec` guarda `lat_min/lat_max/lon_min/lon_max` (plan §4.2); propiedad `bbox` devuelve (oeste, sur, este, norte).
- D3: Mock: `get_trend` calcula siempre la familia regional completa (4 pruebas) antes de filtrar; BY propio en puro Python.
- D4: Mock nivel inferential usa se/p/IC marcadores con warning `mock_inference_placeholder`; no es HAC.
- D5: Mock no tiene datos con huecos; el caso `temporal_gaps` queda para fixtures de Emanuel.
- D6: `src/service.py` real no se creó; cuando exista, dependencia faltante debe lanzar error explícito, nunca devolver mock.
- D7: Tests con `unittest` (pytest no instalado).
- Q1 (Emanuel/Samuel): confirmar `mm/day` mensual de PRECTOTCORR y cobertura 1981–2024 con muestra real.
- Q2 (Kevin): ¿`get_annual_series` devuelve lista de dicts (actual) o DataFrame? Mock añade clave extra `synthetic`.
- Q3 (Emanuel): ¿`coverage_fraction` del mock (1.0) y status para n<10 coinciden con sus fixtures?

## 2026-11-14 — F1 completo (Jacky)
- D8: `result_id` = sha256[:32] de query canónica + `data_sha256` + `mask_version` + `STATS_CONFIG` + versión de código. `generated_at` e hipótesis no entran.
- D9: Mock sigue stdlib-only: no importa `regions.py` (usa pandas); sus celdas se comparan con `regions` en un test.
- D10: Serie constante → `status=ok`, `level=descriptive`, slope 0, p/IC null, warning `degenerate_series`. Cobertura <80 % → `insufficient_data`, `coverage_failure`. Huecos → `temporal_gaps`, sin inferencia.
- D11: `get_cell_trends` devuelve `(list[CellTrends] de la región, metadatos)`; familia BY = celdas de ambos sectores. Metadatos como dict JSON.
- D12: `build_evidence_card`/`build_provenance` devuelven `dict`; `EvidenceCard` tipado queda pendiente.
- Q4 (Emanuel): ¿`degenerate_series` con `status=ok` o `fit_failed`? Ajustar D10 si difiere.
- Q5 (Kevin): ¿`ExportBundle` lo serializas tú desde el dict de la ficha? ¿Necesitas `get_cell_trends` con una región o ambas?

## 2026-11-14 — F2 (Jacky) J2.1–J2.3
- D13: Contratos nuevos en `src/contracts_ext.py` (version `2.1-proposal`), aditivos: v2 no cambia.
- D14: Mock F2 en `src/service_mock_f2.py`, stdlib-only. Zonas ficticias `MOCK_*` activan cada estado de `availability`; `MOCK_*` no son zonas reales.
- D15: Consulta mal formada lanza `ValueError`; ventana sin datos o fuera de cobertura usa `availability`, no excepcion (a diferencia de `validate_query` v2).
- D16: `get_map` ofrece metrica `slope|q|value`; `anomaly` devuelve `unsupported` (se sirve con `product=event`). `metric` es campo propuesto de `AnalysisQuery`.
- D17: Anios parciales no se rellenan: `months_valid` y `complete=false`; el mapa usa solo anios completos.
- D18 (superado por D19–D23): Productos forecast/agua/cobertura de servicio quedaban `unavailable / mock_product_pending` hasta J2.4.

## 2026-11-14 — F2 (Jacky) J2.4
- D19: Reloj inyectable `_today()` en `service_mock_f2.py`; el vencimiento del pronóstico se evalúa al consultar y no altera `issued_at`.
- D20: Pronóstico no validado o fallido (`not_evaluated`/`failed`) o sin modelo → `unavailable` con `forecast_metadata` presente y predicciones null. Nunca se extrapola la tendencia histórica.
- D21: Las correcciones de agua son registros versionados: el original queda con `superseded_by` y el corregido con `corrects_record_id`; el período usa solo la última versión. Pausa registrada (observado 0), cero y sin reporte son estados distintos (`paused`, `reported`, `not_reported`).
- D22: Indicadores de servicio: denominador ausente o cero → `value=null` con `reason_code`; valores >100 % se conservan con flag `exceeds_100`; no se promedia entre zonas (`no_cross_zone_average`). `variable` debe ser None en productos de agua (si no, `ValueError`).
- D23: Pronóstico exige exactamente una zona y no admite celda; agua tampoco admite celda. Ambos devuelven `unsupported`.
- Q6 (Emanuel): ¿target, horizonte y umbral de validación del pronóstico? El mock usa 6 meses, MAE y benchmark de climatología.
- Q7 (Samuel): ¿granularidad mensual, unidades (m3) y fuente del denominador de hogares? El mock usa una fila por área-mes.

## 2026-11-14 — F2 (Jacky) J2.5–J2.6
- D24: Clave de caché = `source_mode` + función + consulta normalizada + secciones del manifest que el producto usa. Mock y real no comparten entradas; `get_series` y `get_map` tampoco (la función es parte de la clave).
- D25: El adapter aporta los hooks `input_manifest`, `normalize_query` y `refresh_freshness`; `src/snapshots.py` no importa el mock. No se cachean `error` ni `unsupported`; la frescura se reevalúa al leer sin tocar `issued_at`.
- D26: `INVALIDATION_MATRIX` se deriva de `KEY_PARTS`, de modo que una sola tabla define clave e invalidación (probado cambio por cambio).
- D27: Export: una carpeta por resultado con `manifest.json` (presentes y ausentes con razón), `evidence.json`, `provenance.json`, `ficha.md` y CSV. Sin datos no se genera CSV. `presentable_as_real` solo con `source_mode=real` y `synthetic=false`. Hipótesis y hora de generación no alteran `result_id` ni `results`.
- Q8 (Kevin): ¿consumes funciones internas o un bundle JSON? Los ejemplos de `docs/team/jacky/examples/` sirven para ambos.
- Q9 (Kevin/Diego): ¿qué metadata es visible en pantalla y cómo se exportan las tablas no aplicables? El mock las lista en `tables_absent`.
