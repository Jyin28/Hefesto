# Estado Jacky

## F1 Base — 2026-11-14
- Estado: **parcial; revisión humana pendiente.** No se marca terminada. F2 no iniciada.
- Rama `feat/jacky-f1-contracts-complete` (desde `origin/main` 4343014); sin push.
- Hecho: contratos v2 completos (tipos, `result_id`, `recommend_variable`), mock con 9/10 firmas (celdas, procedencia, ficha, casos límite), 14 tests unittest OK (ninguno omitido; pandas 3.1.1 en `.venv`, la comparación de celdas mock vs `regions.VERIFIED_LAND_CELLS` corre y pasa), `tests/test_data_qc.py` 5 tests OK, `INVENTARIO.md` rehecho, `F1_ESPEC_CONSULTA.md` (J1.2–J1.6) como propuesta.
- Pendiente: acuerdos de J1.6; `get_event_view` (P1); servicio real (F2/F3); revisión ajena del PR.
- Límites: mock sintético, se/p/IC son marcadores; no se ejecutó Streamlit en este entorno.

## F2 Componentes — 2026-11-14
- Estado: **completa en mock (J2.1–J2.6); revisión humana y acuerdos pendientes.** Rama `feat/jacky-f2-componentes` (desde F1); sin commit ni push.
- Hecho: J2.1 estados de disponibilidad; J2.2 `F2_ESPEC_ADAPTADORES.md`; J2.3 catálogo y consultas (`get_series`, `get_map`, `get_event_series`, `get_capabilities`, `get_data_coverage`); J2.4 pronóstico, agua y cobertura del servicio; J2.5 `src/snapshots.py` (clave, matriz de invalidación, store); J2.6 `src/export_f2.py` y 14 ejemplos en `docs/jacky/examples/`. 97 tests OK con `.venv`. Resumen: `F2_RESUMEN_EJECUTIVO.md`.
- Pendiente: acuerdos de F1/F2 con Samuel, Emanuel, Kevin, Joshua y Diego (Q1–Q9); servicio real (`src/service.py`, F3); fixtures de huecos y series cortas por celda; revisión ajena del PR.
- Límites: todo sintético; firmas son [PROPUESTA]; `request_id` y `result_id` del mock son deterministas; no se ejecutó Streamlit.
