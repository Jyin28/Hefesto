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
