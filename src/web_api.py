"""FastAPI routes used by the React app."""
import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, StrictBool

from hefesto_forecast.api import router as predictions_router

from . import newsletter, telegram_newsletter
from .contracts import COVERAGE_END_YEAR, COVERAGE_START_YEAR
from .web_data import ROOT, local_catalog
from .export import csv_tables, evidence_card, format_csv
from .telegram_alerts import TelegramError, load_token

logger = logging.getLogger(__name__)
# Cada cuántos segundos la API revisa los mensajes nuevos del bot. NEXO_TELEGRAM_POLL=0 apaga la revisión (por ejemplo, si otro
# proceso corre `python -m src.telegram_newsletter discover`).
TELEGRAM_POLL_SECONDS = float(os.environ.get("NEXO_TELEGRAM_POLL_SECONDS", "5"))


def _poll_telegram(stop: threading.Event) -> None:
    """Atiende el /start y el /stop del bot casi al instante: activa la suscripción y manda la bienvenida y el mensaje de prueba.

    El token se lee en cada vuelta: si se agrega al `.env` con el sitio ya corriendo, empieza a funcionar solo.
    """
    while not stop.is_set():
        token = load_token()
        if token:
            try:
                telegram_newsletter.discover(token)
            except TelegramError as error:  # sus mensajes nunca llevan el token
                logger.warning("Telegram: %s", error)
            except Exception:  # un error raro no debe tumbar la revisión
                logger.exception("Telegram: falló la revisión de mensajes nuevos")
        stop.wait(TELEGRAM_POLL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop = threading.Event()
    if os.environ.get("NEXO_TELEGRAM_POLL", "1") != "0":
        threading.Thread(target=_poll_telegram, args=(stop,), daemon=True, name="telegram-poll").start()
    try:
        yield
    finally:
        stop.set()


app = FastAPI(title="AguaAlerta", version="0.1.0", lifespan=lifespan)
# Predicciones regionales experimentales (/api/predicciones). Va antes del montaje de estáticos para que este no la capture.
app.include_router(predictions_router)


@app.get("/api/local")
def get_local():
    return local_catalog()


@app.get("/api/clima/{region}/{variable}")
@app.get("/api/ficha/{region}/{variable}")
def get_climate(region: str, variable: str, desde: int = COVERAGE_START_YEAR, hasta: int = COVERAGE_END_YEAR,
                a_inicio: int | None = None, a_fin: int | None = None,
                b_inicio: int | None = None, b_fin: int | None = None,
                celda: str | None = None, canton: str | None = None, tabla: str | None = None):
    try:
        periods = a_inicio, a_fin, b_inicio, b_fin
        if any(year is not None for year in periods) and any(year is None for year in periods):
            raise ValueError("Indique los cuatro años de inicio y fin de A y B")
        card = evidence_card(
            region, variable, start=desde, end=hasta, cell_id=celda, canton=canton,
            window_a=(a_inicio, a_fin) if a_inicio is not None else None,
            window_b=(b_inicio, b_fin) if b_inicio is not None else None,
        )
        if tabla is not None:
            tables = csv_tables(card)
            if tabla not in tables:
                raise ValueError("Tabla CSV desconocida")
            if not tables[tabla]:
                raise HTTPException(status_code=404, detail="La ficha no contiene datos para esta tabla")
            return Response(format_csv(tables[tabla]), media_type="text/csv; charset=utf-8",
                            headers={"Content-Disposition": f'attachment; filename="{tabla}.csv"'})
        return card
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except OSError as error:
        logger.exception("No se pudieron leer los datos climáticos")
        raise HTTPException(status_code=503, detail="Datos climáticos temporalmente no disponibles") from error


class SubscriptionRequest(BaseModel):
    username: str
    kind: str
    asada_id: str
    consent: StrictBool
    consent_version: str
    lang: str = "es"


_subscription_limiter = newsletter.RateLimiter()


def _bot_payload():
    info = newsletter.bot_info(load_token())
    return {"username": info.username, "link": info.link} if info else None


@app.post("/api/suscripciones")
def subscribe(body: SubscriptionRequest, request: Request):
    """Newsletter de Telegram: guarda a la persona en el Excel de la opción elegida (ver `src/newsletter.py`)."""
    lang = body.lang if body.lang in newsletter.LANGS else "es"
    if not _subscription_limiter.allow(request.client.host if request.client else "?"):
        raise HTTPException(status_code=429, detail={"code": "rate", "message": newsletter.MESSAGES["rate"][1 if lang == "en" else 0]})
    try:
        row = newsletter.subscribe(body.username, body.kind, body.asada_id, body.consent, lang, body.consent_version)
    except newsletter.SubscriptionError as error:
        raise HTTPException(status_code=503 if error.code == "storage" else 422, detail={"code": error.code, "message": error.message}) from error
    # Solo se devuelve lo necesario para el siguiente paso: nunca las filas del Excel.
    return {"ok": True, "kind": body.kind, "state": row["Estado"], "bot": _bot_payload()}


@app.get("/api/suscripciones/bot")
def subscription_bot():
    """Usuario del bot para el botón «Abrir el bot»; `bot` es null mientras no haya token configurado."""
    return {"bot": _bot_payload()}


dist = ROOT / "web" / "dist"
if (dist / "index.html").is_file():
    app.mount("/", StaticFiles(directory=dist, html=True), name="web")
