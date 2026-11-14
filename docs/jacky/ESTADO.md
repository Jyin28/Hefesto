# Estado Jacky

## F1 Base — 2026-11-14
- Estado: **parcial; revisión humana pendiente.** No se marca terminada. F2 no iniciada.
- Rama `feat/jacky-f1-contracts-complete` (desde `origin/main` 4343014); sin push.
- Hecho: contratos v2 completos (tipos, `result_id`, `recommend_variable`), mock con 9/10 firmas (celdas, procedencia, ficha, casos límite), 14 tests unittest OK (1 omitido por falta de pandas), `INVENTARIO.md` rehecho, `F1_ESPEC_CONSULTA.md` (J1.2–J1.6) como propuesta.
- Pendiente: acuerdos de J1.6; `get_event_view` (P1); servicio real (F2/F3); revisión ajena del PR.
- Límites: mock sintético, se/p/IC son marcadores; no se ejecutó Streamlit ni `test_data_qc.py` en este entorno.
