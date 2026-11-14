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
