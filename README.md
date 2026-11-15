# AguaAlerta (Costa Rica)
NASA Space Apps Hackathon · explorador educativo de cambios ambientales con datos NASA POWER.

El estudiante elige una pregunta (¿cambió la temperatura? ¿cambió la lluvia anual?), un sector (Pacífico Norte o Caribe de Costa Rica)
y un período. Recibe cuatro tarjetas (qué, dónde, cuánto, qué evidencia), series, mapa por celda nativa, comparación de sectores,
diagnósticos y una **Ficha de detective** reproducible (Markdown/JSON/CSV).
Es exploración histórica: **no pronostica** sequías, inundaciones ni disponibilidad de agua.

## Cómo abrir el sitio (Windows, PowerShell)

Usa Python 3.12 o posterior. Abre una terminal en la raíz del repositorio.

```powershell
.\scripts\run.ps1
```
`scripts\run.ps1` crea `.venv` e instala las dependencias si hacen falta. Después verifica los datos e inicia Streamlit.
Abre **http://localhost:8501** en el navegador cuando aparezca la dirección en la terminal.

Si ya tienes el entorno listo, puedes iniciar Streamlit directamente.
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

Ejecuta estos comandos desde el repositorio de Git. El ZIP de distribución incluye lo necesario para abrir la aplicación.

```powershell
.\.venv\Scripts\python.exe scripts\verify_data.py      # datos accesibles y consistentes
.\.venv\Scripts\python.exe -m pytest -q                 # pruebas (incluye statsmodels, AppTest offline)
.\scripts\package.ps1                                         # dist\hefesto-mvp.zip
```

## Mapa del repositorio
```
app.py              UI guiada (Streamlit)
src/                código Python: servicio, ciencia (prepare, statistics, evidence, enso), vistas, exportación
scripts/            build_*/prepare_*/verify_data.py y run.ps1 / package.ps1
tests/              pruebas y fixtures
config/             configuración (ENOS, descubrimiento)
data/
  raw/              fuentes originales (NASA POWER, agua/, lluvia/, cantones/, hidrografia/)
  processed/        datos derivados que consume la app
  web/              JSON para la app web
  mock/             datos sintéticos de desarrollo
docs/
  plan/             planes del proyecto
  project/          RELEASE, AI_USAGE, TEAM_AGREEMENT
  team/             notas y especificaciones por integrante
  limitations.md, validation.md, claims.csv, DATA_SOURCES.md, pitch.md, video_script.md ...
web/                app React (fuera del MVP)
```
Raíz: solo `README.md`, `LICENSE`, `THIRD_PARTY.md` y archivos de configuración.
Fuera del producto (se conservan sin usar): `web/` (React), `src/web_api.py`, `src/dashboard.py`, pronóstico y datos hídricos.
