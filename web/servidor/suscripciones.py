"""Suscripciones al newsletter de Telegram en Vercel (versión de `src/newsletter.py` que guarda en Redis, no en Excel).

El contrato con el formulario (`web/src/NewsletterForm.tsx`) es el mismo: usuario con @, UNA de dos opciones (alertas y
sugerencias, o resumen diario) y consentimiento informado. Una suscripción nace «Pendiente /start» y solo pasa a «Activo» cuando
esa misma cuenta le escribe /start al bot después de suscribirse (ver `bot.py`): escribir un @usuario en un formulario no prueba
que sea suyo, y Telegram no deja que un bot escriba primero.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from . import telegram_alerts as tg
from .store import SUBS, FakeStore, RedisStore, StoreError

ROOT = Path(__file__).resolve().parents[1]  # la carpeta web/
WEB_DATA = ROOT / "public" / "data"
ASADAS = WEB_DATA / "asadas.json"
CANTON_INDEX = WEB_DATA / "cantones-indice.json"
PREDICTIONS = WEB_DATA / "predicciones.json"

KINDS = ("alertas", "resumen")
HEADERS = ["Usuario de Telegram", "ASADA", "ID de la ASADA", "Cantón", "Provincia", "Región", "Idioma", "Fecha de suscripción", "Consentimiento", "Estado"]
PENDING, ACTIVE, STOPPED = "Pendiente /start", "Activo", "Baja"
# Cambia cada vez que cambia el texto del consentimiento en `web/src/NewsletterForm.tsx` (y `CONSENT_VERSION` de `src/newsletter.py`).
CONSENT_VERSION = "2026-11-v1"
USERNAME_RE = re.compile(r"^@[A-Za-z][A-Za-z0-9_]{4,31}$")  # Telegram: 5 a 32 caracteres, empieza con letra
LANGS = ("es", "en")
TZ = ZoneInfo("America/Costa_Rica")
RATE_LIMIT, RATE_WINDOW = 10, 3600  # intentos por dirección y por hora

MESSAGES = {
    "username": ("Escribí tu usuario de Telegram empezando con @ (5 a 32 letras, números o guion bajo).", "Enter your Telegram username starting with @ (5 to 32 letters, numbers or underscores)."),
    "kind": ("Elegí una opción: alertas y sugerencias, o resumen diario.", "Choose one option: alerts and suggestions, or daily summary."),
    "consent": ("Tenés que aceptar el consentimiento informado para suscribirte.", "You must accept the informed consent to subscribe."),
    "consent_version": ("El texto del consentimiento cambió. Recargá la página e intentá de nuevo.", "The consent text has changed. Reload the page and try again."),
    "asada": ("No encontramos esa ASADA. Buscala de nuevo.", "We could not find that ASADA. Search for it again."),
    "rate": ("Hubo demasiados intentos. Probá de nuevo más tarde.", "Too many attempts. Try again later."),
    "storage": ("No pudimos guardar tu suscripción ahora. Probá de nuevo en un momento.", "We could not save your subscription right now. Try again in a moment."),
}


class SubscriptionError(ValueError):
    """Una validación falló. `code` identifica el campo; el mensaje sale en el idioma pedido."""

    def __init__(self, code: str, lang: str = "es"):
        self.code = code
        self.message = MESSAGES[code][1 if lang == "en" else 0]
        super().__init__(self.message)


# --- Catálogos (los mismos JSON que usa la página, incluidos en la función con `includeFiles`) ---

@lru_cache(maxsize=8)
def _read_json(path: str, mtime_ns: int) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_json(path: Path) -> Any:
    """Lee un JSON y lo recuerda mientras el archivo no cambie."""
    return _read_json(str(path), path.stat().st_mtime_ns)


def find_operator(asada_id: str, asadas_path: Path = ASADAS) -> dict | None:
    return next((item for item in read_json(asadas_path)["operators"] if item["id"] == asada_id), None)


def region_for_canton(code: str, index_path: Path = CANTON_INDEX, predictions_path: Path = PREDICTIONS) -> str:
    """Misma regla que la página: celda NASA que más cubre al cantón → Pacífico Norte, Caribe o, si no, todo el país."""
    cell = next((item["cell"] for item in read_json(index_path) if item["code"] == code), "")
    cells = read_json(predictions_path)["region_cells"]
    for region in ("CR_PN", "CR_CAR"):
        if cell in cells[region]:
            return region
    return "CR"


# --- Filas en el almacenamiento ---

def field_for(kind: str, username: str, asada_id: str) -> str:
    return f"{kind}|{username.lower()}|{asada_id}"


def now_text(now: datetime | None = None) -> str:
    return (now or datetime.now(TZ)).isoformat(timespec="seconds")


def subscribe(store: RedisStore | FakeStore, username: str, kind: str, asada_id: str, consent: bool, lang: str = "es",
              consent_version: str = CONSENT_VERSION, *, asadas_path: Path = ASADAS, index_path: Path = CANTON_INDEX,
              predictions_path: Path = PREDICTIONS, now: datetime | None = None) -> dict:
    """Valida y guarda la suscripción. Devuelve la fila guardada.

    La misma persona con la misma ASADA no se duplica: si cambia de opción, la fila pasa de una opción a la otra.
    """
    lang = lang if lang in LANGS else "es"
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise SubscriptionError("username", lang)
    if kind not in KINDS:
        raise SubscriptionError("kind", lang)
    if consent is not True:
        raise SubscriptionError("consent", lang)
    if consent_version != CONSENT_VERSION:
        raise SubscriptionError("consent_version", lang)
    operator = find_operator(asada_id, asadas_path)
    if operator is None:
        raise SubscriptionError("asada", lang)
    stamp = now_text(now)
    row = {
        "Usuario de Telegram": username, "ASADA": operator["name"], "ID de la ASADA": operator["id"], "Cantón": operator["canton"],
        "Provincia": operator["province"], "Región": region_for_canton(operator["cantonCode"], index_path, predictions_path),
        "Idioma": lang, "Fecha de suscripción": stamp, "Consentimiento": f"Aceptado ({CONSENT_VERSION}) {stamp}", "Estado": PENDING,
    }
    try:
        store.hset(SUBS, field_for(kind, username, operator["id"]), json.dumps(row, ensure_ascii=False))
        for other in KINDS:
            if other != kind:
                store.hdel(SUBS, field_for(other, username, operator["id"]))
    except StoreError:
        raise SubscriptionError("storage", lang) from None
    return row


def allow_attempt(store: RedisStore | FakeStore, ip: str, now: float | None = None) -> bool:
    """Máximo `RATE_LIMIT` intentos por dirección y por hora (el contador vive en Redis: las funciones no comparten memoria)."""
    hour = int((time.time() if now is None else now) // RATE_WINDOW)
    try:
        return store.incr_expire(f"rate:{ip}:{hour}", RATE_WINDOW) <= RATE_LIMIT
    except StoreError:
        return True  # si el contador falla no se bloquea a nadie; guardar la suscripción avisará del problema


# --- Lo que lee el bot ---

def all_subscribers(store: RedisStore | FakeStore) -> list[dict]:
    """Todas las suscripciones, con su opción en `kind` («alertas» o «resumen»)."""
    rows = []
    for field, raw in store.hgetall(SUBS).items():
        row = json.loads(raw)
        rows.append({**row, "kind": field.split("|", 1)[0]})
    return rows


def update_state(store: RedisStore | FakeStore, changes: list[tuple[str, str, str, str]]) -> int:
    """Cambia el estado de filas. Cada cambio es (kind, usuario, id de la ASADA, estado nuevo). Devuelve cuántas filas cambió."""
    changed = 0
    for kind, user, asada_id, state in changes:
        field = field_for(kind, user, asada_id)
        raw = store.hget(SUBS, field)
        if raw is None:
            continue
        row = json.loads(raw)
        if row["Estado"] != state:
            row["Estado"] = state
            store.hset(SUBS, field, json.dumps(row, ensure_ascii=False))
            changed += 1
    return changed


def as_recipient(row: dict) -> dict:
    """La fila guardada como la espera `telegram_alerts` (`asada`, `canton`, `province`, `region`, `lang`)."""
    return {"asada": row["ASADA"], "canton": row["Cantón"], "province": row["Provincia"], "region": row["Región"], "lang": row["Idioma"] or "es"}


# --- Datos del bot ---

@dataclass
class BotInfo:
    username: str

    @property
    def link(self) -> str:
        return f"https://t.me/{self.username}"


_BOT_CACHE: dict[str, tuple[float, BotInfo | None]] = {}


def bot_info(token: str | None, session: Any = requests, environ: dict[str, str] | None = None, ttl: float = 600.0) -> BotInfo | None:
    """Usuario del bot, para el botón «Abrir el bot». Sin token (o si Telegram no responde) devuelve None: el envío aún no está activo."""
    environ = os.environ if environ is None else environ
    if not token:
        return None
    cached = _BOT_CACHE.get(token)
    if cached and time.monotonic() - cached[0] < ttl:
        return cached[1]
    info: BotInfo | None = None
    named = (environ.get("TELEGRAM_BOT_USERNAME") or "").strip().lstrip("@")
    if named:
        info = BotInfo(named)
    else:
        try:
            info = BotInfo(tg.call(token, "getMe", session=session)["username"])
        except (tg.TelegramError, KeyError):
            info = None
    _BOT_CACHE[token] = (time.monotonic(), info)
    return info
