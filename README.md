# Hefesto · Detective Tico (Costa Rica)
NASA Space Apps Hackathon · explorador educativo de cambios ambientales con datos NASA POWER.

El estudiante elige una pregunta (¿cambió la temperatura? ¿cambió la lluvia anual?), un sector (Pacífico Norte o Caribe de Costa Rica)
y un período. Recibe cuatro tarjetas (qué, dónde, cuánto, qué evidencia), series, mapa por celda nativa, comparación de sectores,
diagnósticos y una **Ficha de detective** reproducible (Markdown/JSON/CSV).
Es exploración histórica: **no pronostica** sequías, inundaciones ni disponibilidad de agua.

## Cómo abrir el sitio (Windows, PowerShell)
```powershell
cd <carpeta del repositorio>
git switch MVP
.\run.ps1
```
`run.ps1` crea `.venv` si falta, instala `requirements.txt`, verifica los datos y abre Streamlit. Luego entra a
**http://localhost:8501** (se abre solo en el navegador). Manual:
```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```
Funciona **sin internet** una vez instaladas las dependencias (sin teselas de mapa externas, telemetría desactivada).
Modo desarrollo sintético (banner permanente): `$env:HEFESTO_USE_MOCK = "1"` antes de arrancar.

## Datos y método (resumen)
- NASA POWER mensual, T2M (°C) y PRECTOTCORR (mm/día → anual = Σ tasa × días, mm/año), 1981–2024, 10 celdas nativas (5 por sector).
- Anualización con 12 meses válidos; máscara fija con ≥80 % del peso; OLS + HAC (Newey–West, Bartlett, L=3; sensibilidad L=1 y L=5);
  ≥30 años consecutivos para inferencia; Benjamini–Yekutieli sobre la familia completa (4 pruebas regionales; 10 celdas por mapa).
- Diagnósticos: sensibilidad HAC, prueba de Pettitt (salto de nivel) y contraste Sen + Mann–Kendall.
- Episodio ENOS jun 1997 – may 1998: anomalías vs 1981–2010, descriptivo.
- **Lluvia:** es lluvia de reanálisis sin validar con estaciones; sus pendientes (cientos de mm/año por década) deben leerse como patrón del
  producto, no como lluvia observada. Ver `docs/limitations.md`.

## Verificación
```powershell
.\.venv\Scripts\python.exe scripts\verify_data.py      # datos accesibles y consistentes
.\.venv\Scripts\python.exe -m pytest -q                 # pruebas (incluye statsmodels, AppTest offline)
.\package.ps1                                           # dist\hefesto-mvp.zip
```

## Mapa del repositorio
`app.py` UI guiada · `src/views.py` vistas · `src/service.py` servicio real (mismas firmas que `service_mock.py`) ·
`src/prepare.py`, `src/statistics.py`, `src/evidence.py`, `src/enso.py` ciencia · `src/export.py` ficha y exportación ·
`data/` datos · `docs/` limitaciones, claims, validación, guion · `RELEASE.md` checklist.
Fuera del producto (se conservan sin usar): `web/` (React), `src/web_api.py`, `src/dashboard.py`, pronóstico y datos hídricos.
