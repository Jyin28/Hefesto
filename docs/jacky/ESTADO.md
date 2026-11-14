# Estado Jacky

## F1 Base — 2026-11-14
- Estado: **parcial; revisión humana pendiente.** No se marca terminada. F2 no iniciada.
- Rama `feat/jacky-f1-contracts-complete` (desde `origin/main` 4343014); sin push.
- Hecho: contratos v2 completos (tipos, `result_id`, `recommend_variable`), mock con 9/10 firmas (celdas, procedencia, ficha, casos límite), 14 tests unittest OK (ninguno omitido; pandas 3.1.1 en `.venv`, la comparación de celdas mock vs `regions.VERIFIED_LAND_CELLS` corre y pasa), `tests/test_data_qc.py` 5 tests OK, `INVENTARIO.md` rehecho, `F1_ESPEC_CONSULTA.md` (J1.2–J1.6) como propuesta.
- Pendiente: acuerdos de J1.6; `get_event_view` (P1); servicio real (F2/F3); revisión ajena del PR.
- Límites: mock sintético, se/p/IC son marcadores; no se ejecutó Streamlit en este entorno.
