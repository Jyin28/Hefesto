# AguaAlerta (Costa Rica)
NASA Space Apps Hackathon · explorador educativo de cambios ambientales con datos NASA POWER.

El estudiante elige una pregunta (¿cambió la temperatura? ¿cambió la lluvia anual?), un sector (Pacífico Norte o Caribe de Costa Rica)
y un período. Recibe cuatro tarjetas (qué, dónde, cuánto, qué evidencia), series, mapa por celda nativa, comparación de sectores,
diagnósticos y una **Ficha de detective** reproducible (Markdown/JSON/CSV).
Es exploración histórica: **no pronostica** sequías, inundaciones ni disponibilidad de agua.

## Sitio web de AguaAlerta (lo principal)

Es el sitio que se publica: inicio, mapas (NASA POWER, Copernicus CDS y datos nacionales de caudales), página de **Predicciones**
con selector de idioma ES/EN, y el newsletter por Telegram. Se compone de una API (FastAPI) que sirve la web ya compilada.

Requisitos: **Python 3.12 o posterior** y **Node.js 20 o posterior**. En PowerShell, desde la raíz del repositorio:

```powershell
.\scripts\run-web.ps1
```

El script crea `.venv`, instala las dependencias de Python y de la web, compila la web y abre **http://localhost:8000**. No necesita
internet una vez instalado ni ninguna clave: los datos (`web/public/data/`, `hefesto_forecast/data/`) están en el repositorio.

- **Newsletter por Telegram (opcional):** copia `.env.example` como `.env` y pon el token del bot (se crea con @BotFather). Sin token, el sitio
  funciona igual y el formulario avisa que el envío aún no está activo. Guía completa en `docs/predicciones.md`.
- **Desarrollo con recarga:** `python -m uvicorn src.web_api:app --reload` y, en otra terminal, `cd web; npm.cmd run dev` (http://localhost:5173).
  Detalles en `web/README.md`.
- **Regenerar datos:** `python -m src.predictions` (predicciones, normalmente cada mes) y `npm run geo` en `web/` (mallas por cantón).
- **Pruebas:** `.\.venv\Scripts\python.exe -m pytest -q` y `cd web; npm.cmd run build`.

## Publicar en Vercel

El sitio se publica desde la carpeta `web/` (React + Vite). Todo es estático salvo el newsletter de Telegram, que usa tres funciones
de Python en `web/api/` y guarda las suscripciones en Upstash Redis (en Vercel no hay disco permanente ni procesos que queden
corriendo). La API local del puerto 8000 y los Excel siguen existiendo para desarrollo y no se usan en Vercel.

| Función | Para qué |
|---|---|
| `POST /api/suscripciones` | El formulario de Predicciones guarda la suscripción (queda «Pendiente /start»). |
| `POST /api/telegram` | Webhook del bot: Telegram entrega aquí el `/start` (activa la suscripción y manda bienvenida y mensaje de prueba) y el `/stop`. |
| `GET /api/enviar` | Cron de Vercel, una vez al día (13:00 UTC = 7:00 de Costa Rica): envía las alertas y el resumen diario. El plan Hobby solo permite una vez al día y con hasta ±59 min de atraso. |

**Una sola vez:**

1. En Vercel, crea el proyecto desde GitHub (rama `main`) con **Root Directory = `web`**. Vercel detecta Vite solo (`npm run build`, salida `dist`).
2. En *Storage → Marketplace* agrega **Upstash Redis** y conéctalo al proyecto (crea `KV_REST_API_URL` y `KV_REST_API_TOKEN`).
3. En *Settings → Environment Variables* agrega: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET` y `CRON_SECRET`
   (los dos secretos son texto al azar, solo letras, números, `_` y `-`; con `CRON_SECRET` definido, Vercel firma cada llamada del cron).
4. Haz el deploy. Después, para que Telegram entregue los mensajes al sitio, pon `TELEGRAM_BOT_TOKEN` y `TELEGRAM_WEBHOOK_SECRET` en tu `.env` local (el mismo secreto que en Vercel) y corre
   `.\scripts\telegram_webhook.ps1 -Url https://tu-sitio.vercel.app`. `-Estado` muestra a dónde entrega Telegram ahora.

**Cosas que conviene saber:**

- **El bot no puede atenderse desde Vercel y desde tu computadora a la vez.** Con el webhook activo, la API local no puede leer los `/start` (Telegram responde 409). Para volver al modo local: `.\scripts\telegram_webhook.ps1 -Quitar`.
- Para ver las suscripciones en Excel: en `web/`, `npx vercel env pull .env.local` y luego `python scripts/exportar_suscripciones.py` (escribe `data/suscripciones/*.xlsx`, que está en `.gitignore` por tener datos personales).
- `web/servidor/telegram_alerts.py` es copia exacta de `src/telegram_alerts.py`: si cambias uno, copia el otro (una prueba lo verifica). La versión del consentimiento (`CONSENT_VERSION`) debe coincidir en `web/src/NewsletterForm.tsx`, `src/newsletter.py` y `web/servidor/suscripciones.py` (también lo verifica una prueba).
- Para actualizar las predicciones: `python -m src.predictions`, haz commit de `web/public/data/predicciones.json` y Vercel vuelve a publicar.
- Pruebas de esta parte: `.\.venv\Scripts\python.exe -m pytest tests/test_vercel_newsletter.py -q`.

## App Streamlit (versión anterior)

La primera versión del proyecto, una app educativa en Streamlit. Es independiente del sitio web.

### Cómo abrir la app Streamlit (Windows, PowerShell)

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
