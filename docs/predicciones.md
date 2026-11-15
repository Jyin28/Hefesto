# Predicciones y avisos por Telegram

Página «Predicciones» de AguaAlerta (`?pagina=predicciones`), el motor que la alimenta y los avisos de prueba por Telegram.

## Cómo se genera

```powershell
python -m src.predictions            # escribe web/public/data/predicciones.json
```

La página lee los JSON estáticos: el sitio sigue sin necesitar servidor. Además, `src/web_api.py` expone el motor en
`GET /api/predicciones?region=CR&variable=T2M&start=2026-12&months=6` (ver `hefesto_forecast/api.py`).

- `hefesto_forecast/`: motor del paquete de predicciones (seis modelos, calibración y bandas de 90 % ya validadas). Sus datos
  (`data/monthly_regional.csv`, `roni_noaa.csv`) llevan huella SHA-256: **si cambian, el motor responde 503** hasta repetir el
  backtest. No basta con reemplazar las huellas. La evidencia de la validación está en `docs/forecast_evidencia/`.
- `src/predictions.py`: llama al motor y agrega lo que el motor no hace: el episodio de El Niño en curso (rachas de RONI ≥ 0,5
  durante 5 meses o más) y los **años análogos**.

## Cómo se organiza la página

1. **Resumen y sugerencias** (lo primero que se ve, en lenguaje sencillo): empieza con el promedio de todo el país. El buscador
   (cantones y ASADAs, con la guía «Buscar por lugar») cambia el resumen según el lugar elegido.
2. **Botones al final**: «Datos numéricos» (gráficos, tablas, calendario de El Niño, avisos de Telegram) y «Cómo obtenemos estos
   datos» (explicación simple + botón al PDF).
3. **Explicación completa** (`?pagina=metodologia`): documento con todo el detalle (fuentes, modelos, pruebas, límites). El botón
   «Descargar la explicación completa (PDF)» la abre con `&imprimir=1`, que abre el diálogo de impresión del navegador para
   «Guardar como PDF». No hay dependencias nuevas; los estilos de impresión están en `web/src/style.css` (`@media print`).

### Qué zona le toca a un cantón o una ASADA

Las predicciones siguen siendo solo regionales. Para el resumen de un lugar se usa la **cuadrícula NASA POWER**: cada cantón toma la
celda que más lo cubre (`cantonCells` de `geo.json`, índice liviano en `web/public/data/cantones-indice.json`, que escribe
`npm run geo`). Una ASADA usa la celda de su cantón. Si esa celda está en `region_cells` de `predicciones.json` (Pacífico Norte o
Caribe, las máscaras de `src/regions.py`), se muestran los datos de esa región; si no, el promedio de todo el país con una nota
que lo explica. Consecuencia conocida: por la cuadrícula, los cantones de Cartago y varios de San José y Heredia caen en «Caribe».

### Buscadores

Los cantones se buscan en todos los mapas y en Predicciones. Las **ASADAs (caudal)** solo en «Datos nacionales» y en Predicciones
(`searchesAsadas` en `web/src/search.ts`). En los resultados, el ícono **verde** (pin) es un cantón y el **azul** (gota) una ASADA.

## Qué dice y qué no

| Parte de la página | Qué es | Qué NO es |
|---|---|---|
| Temperatura | Pronóstico experimental del motor, con banda de 90 %. Solo hasta donde la validación lo respaldó (1 a 3 meses según el sector). | No hay pronóstico por cantón, celda ni ASADA: es regional (Costa Rica, Pacífico Norte, Caribe). |
| Rango de fechas de El Niño | El **inicio** es un dato (RONI). El **pico** y el **fin** comparan con los episodios fuertes anteriores (pico de RONI ≥ 1,5): percentiles 10, 50 y 90 de cuánto duraron y cuándo llegaron al máximo. | No es un modelo dinámico del océano: no predice el inicio de un Niño nuevo ni asegura una fecha de fin. |
| Lluvia | Referencia histórica del mes (1991–2020) y lo que llovió en los años con RONI de septiembre ≥ 1,0 (años análogos). | **No hay pronóstico de lluvia validado.** Son 7 años y no se hace prueba de significancia: es contexto. |
| Humedad y UV | Referencia estacional. | Sin pronóstico. El UV es el medio de 24 h de NASA POWER, no el del mediodía. |

Hallazgo que condiciona el texto de los avisos: en los 7 años análogos llovió **menos** de lo normal en diciembre y enero en las
tres regiones (de −39 % a −45 % en diciembre), también en el Caribe. Por eso el aviso de lluvia habla de *probabilidad de que
llueva* (en 6 de 7 años llovió al menos 100 mm en el Caribe en diciembre), no de lluvia por encima de lo normal, y lo dice.

## Newsletter por Telegram

Al buscar una **ASADA** en la página de Predicciones aparece un formulario para suscribirse a un newsletter por Telegram.
La persona da su usuario (con `@`), elige **una** de dos opciones y marca el consentimiento informado:

| Opción | Qué recibe | Excel donde se guarda |
|---|---|---|
| Alertas y sugerencias | Solo cuando los datos respaldan un riesgo (calor, lluvia o El Niño) en la zona de su ASADA, con qué hacer. No repite el mismo aviso hasta que cambian las predicciones. | `data/suscripciones/alertas_sugerencias.xlsx` |
| Resumen diario | Cada día, las cifras de su zona con sugerencias. Si los datos no advierten riesgos, dice que **no hubo cambios significativos**. | `data/suscripciones/resumen_diario.xlsx` |

Cada Excel tiene el usuario de Telegram y la ASADA asociada (más cantón, provincia, región, idioma, fecha, consentimiento y estado).
Esa carpeta tiene **datos personales**: está en `.gitignore` y la API nunca la devuelve. La misma persona con la misma ASADA no se
duplica; si cambia de opción, pasa de un Excel al otro.

Las personas de prueba y su configuración (`config/telegram_recipients*.json`, `alertas.json`) ya no existen.

### Cómo se activa (una sola vez)

1. En Telegram, abrir **@BotFather**, enviar `/newbot` y elegir un nombre y un usuario que termine en «bot». Esto lo tiene que
   hacer una persona del equipo desde su cuenta: no se puede automatizar.
2. Copiar el token que da BotFather en el archivo `.env` de la raíz (ya está en `.gitignore`; hay un ejemplo en `.env.example`):
   `TELEGRAM_BOT_TOKEN=<token>`. Nunca va en el código, en el chat ni en un commit. Opcional: `TELEGRAM_BOT_USERNAME=<usuario sin @>`.
3. Levantar el sitio con la API (`python -m uvicorn src.web_api:app`): el formulario guarda en los Excel mediante
   `POST /api/suscripciones`. Sin la API (sitio estático) el formulario avisa que el servicio no está disponible.

### Qué pasa después de suscribirse

- La suscripción nace **«Pendiente /start»**. Telegram no deja que un bot le escriba primero a nadie ni lo busque por @usuario:
  la persona debe abrir el bot (el sitio le muestra el botón) y enviar `/start`.
- **La API atiende el `/start` sola**: mientras `uvicorn src.web_api:app` está corriendo y hay token, un hilo revisa los mensajes del bot
  cada 5 segundos (`NEXO_TELEGRAM_POLL_SECONDS`; `NEXO_TELEGRAM_POLL=0` lo apaga). Si el token se agrega al `.env` con el sitio ya
  corriendo, empieza a funcionar solo.
- Solo si **la misma cuenta** (mismo @usuario) escribe `/start` **después** de suscribirse, se guarda su Chat ID
  (`data/telegram_chats.json`, no se versiona), pasa a **«Activo»** y recibe automáticamente:
  1. un mensaje de **bienvenida** (con cómo darse de baja), y
  2. un **mensaje de prueba** con lo que dicen los datos hoy: el resumen del día (opción «resumen diario») o los avisos vigentes
     (opción «alertas»; si no hay ninguno, lo dice). Lo ya enviado se anota para que el envío normal no lo repita.
  Eso es lo que comprueba que el @usuario es suyo. Un `/start` anterior a la suscripción se responde pidiendo repetirlo; si la
  persona no está suscrita, el bot le explica cómo hacerlo. `/stop` la da de **«Baja»**.
- `python -m src.telegram_newsletter send` muestra qué enviaría; con `--yes` envía de verdad (alertas: una vez por versión de las
  predicciones; resumen: una vez al día; se anota en `data/telegram_sent.json`).
- `python -m src.telegram_newsletter discover` hace lo mismo que el hilo de la API, a mano (úsese solo si la API no está corriendo).

Los textos salen en el idioma que la persona tenía elegido en el sitio (español o inglés) al suscribirse.

### Programar el envío diario en Windows

`scripts/newsletter.ps1` envía las alertas y el resumen diario a quienes ya están activos y deja un registro en `data/newsletter.log`.
Para que corra todos los días a las 7:00 (el equipo debe estar encendido), ejecutar **una vez** en PowerShell:

```powershell
schtasks /Create /SC DAILY /ST 07:00 /TN "AguaAlerta-Telegram" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\ruta\al\proyecto\scripts\newsletter.ps1\"" /F
```

Para quitarla: `schtasks /Delete /TN "AguaAlerta-Telegram" /F`. Las predicciones se actualizan con `python -m src.predictions`, normalmente una vez
al mes: entre actualizaciones, el resumen diario repite los mismos datos.

### Privacidad y límites

- Solo se guardan usuario, ASADA (con su cantón y región), idioma y la fecha del consentimiento. El texto del consentimiento está en
  `web/src/NewsletterForm.tsx`; si se cambia, hay que cambiar también `CONSENT_VERSION` en `src/newsletter.py` (el servidor rechaza
  versiones que no coincidan).
- Darse de baja con `/stop` marca la fila como «Baja», **no la borra**. Borrar los datos de una persona que lo pida es un paso manual
  sobre los Excel (y sobre `data/telegram_chats.json`).
- El formulario tiene un límite simple de intentos por dirección (10 por hora) y valida que el usuario cumpla el formato de Telegram.
- Son avisos regionales y experimentales: la zona es la de la cuadrícula del cantón de la ASADA, no una predicción para esa ASADA.
- Los errores nunca muestran el token.
