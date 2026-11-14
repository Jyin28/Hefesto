# AI_USAGE

| Fecha | Persona | Herramienta | Uso | Verificación humana |
|---|---|---|---|---|
| 2026-11-14 | Jacky | Claude Code (Sonnet 5.5) | F1: `src/contracts.py`, `src/service_mock.py`, tests, docs/jacky | Pendiente de revisión humana; tests unittest ejecutados |
| 2026-11-14 | Emanuel | Claude Code (Sonnet 5) | EMANUEL-03: `src/prepare.py` (preparación mensual/anual regional), `tests/test_prepare.py` | Pendiente de revisión humana; 23 tests unittest OK (`python -m unittest discover -s tests -t .`) |
| 2026-11-14 | Emanuel | Codex | Integración de series reales, evidencia, ENOS, cobertura hídrica, pronóstico experimental, fichas y validación | Pruebas locales de cálculo y exportación ejecutadas; revisión del equipo pendiente |
| 2026-11-14 | Jacky | Claude Code | Rama MVP: servicio real, UI Streamlit guiada, exportación, diagnóstico de homogeneidad, verificación de datos, empaquetado y documentación | Pruebas locales ejecutadas (pytest, verificación de datos, comparación HAC con statsmodels); revisión humana pendiente |
