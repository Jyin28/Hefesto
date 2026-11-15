# Predicciones y avisos por Telegram

Página «Predicciones» del sitio (`?pagina=predicciones`), el motor que la alimenta y los avisos de prueba por Telegram.

## Cómo se genera

```powershell
python -m src.predictions            # escribe web/public/data/predicciones.json
python -m src.telegram_alerts preview  # muestra los 3 avisos y escribe web/public/data/alertas.json (no envía nada)
```

La página lee los JSON estáticos: el sitio sigue sin necesitar servidor. Además, `src/web_api.py` expone el motor en
`GET /api/predicciones?region=CR&variable=T2M&start=2026-12&months=6` (ver `hefesto_forecast/api.py`).

- `hefesto_forecast/`: motor del paquete de predicciones (seis modelos, calibración y bandas de 90 % ya validadas). Sus datos
  (`data/monthly_regional.csv`, `roni_noaa.csv`) llevan huella SHA-256: **si cambian, el motor responde 503** hasta repetir el
  backtest. No basta con reemplazar las huellas. La evidencia de la validación está en `docs/forecast_evidencia/`.
- `src/predictions.py`: llama al motor y agrega lo que el motor no hace: el episodio de El Niño en curso (rachas de RONI ≥ 0,5
  durante 5 meses o más) y los **años análogos**.

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

## Avisos por Telegram (`src/telegram_alerts.py`)

Tres avisos de prueba. Cada uno se arma solo si los datos lo respaldan (si no, se rechaza con el motivo y no se envía nada):

| Aviso | Zona asignada | Por qué esa zona |
|---|---|---|
| Calor | Liberia, Guanacaste (Pacífico Norte) | Diciembre y enero estimados sobre el P90 histórico (≥ 0,5 °C sobre lo normal). |
| Probabilidad de lluvia | Limón (Caribe) | Única región con alta probabilidad de lluvia mensual (≥ 70 % de años análogos con 100 mm o más). |
| Zona afectada por El Niño | San Carlos, Alajuela (Zona Norte) | Episodio en curso y déficit de lluvia en años análogos del promedio del país (≥ 20 % menos). |

Las asignaciones persona → aviso → zona están en `config/telegram_recipients.json` (no se versiona; hay un ejemplo en
`config/telegram_recipients.example.json`). Los avisos son regionales: la zona es la del sector, no una predicción para un cantón.

### Enviar

1. Crear un bot con **@BotFather** de Telegram y copiar su token.
2. Guardarlo en `.env` (ya está en `.gitignore`): `TELEGRAM_BOT_TOKEN=<token>`. Nunca va en el código ni en el chat.
3. Cada persona de prueba abre el bot y envía `/start`. **Telegram no deja que un bot le escriba primero a nadie ni lo busque por
   @usuario**: sin ese paso no hay forma de enviar.
4. `python -m src.telegram_alerts discover`: lee esos `/start` y guarda el Chat ID de cada @usuario en `data/telegram_chats.json`
   (no se versiona).
5. `python -m src.telegram_alerts send` muestra qué enviaría; con `--yes` envía de verdad y actualiza `alertas.json` con el estado.

La página pública muestra el texto y el estado de cada aviso, **sin** @usuarios ni Chat ID. Los errores nunca muestran el token.
