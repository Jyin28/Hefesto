"""Suscripciones al newsletter de Telegram de AguaAlerta.

Una persona se suscribe desde la página de Predicciones, al buscar una ASADA: da su usuario de Telegram (con @), elige UNA de
dos opciones (alertas y sugerencias, o resumen diario) y acepta el consentimiento informado. Cada opción se guarda en su propio
Excel (`data/suscripciones/`), con el usuario y la ASADA asociada. Esa carpeta tiene datos personales: está en `.gitignore` y
la API nunca la devuelve.

Que alguien escriba un @usuario en un formulario NO prueba que ese usuario sea suyo. Por eso una suscripción nace
«Pendiente /start» y solo pasa a «Activo» cuando esa misma cuenta de Telegram le escribe /start al bot después de suscribirse
(`src/telegram_newsletter.py discover`). Telegram además no deja que un bot escriba primero.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "suscripciones"
WEB_DATA = ROOT / "web" / "public" / "data"
ASADAS = WEB_DATA / "asadas.json"
CANTON_INDEX = WEB_DATA / "cantones-indice.json"
PREDICTIONS = WEB_DATA / "predicciones.json"

# Una opción = un Excel. La persona elige una sola.
KINDS: dict[str, str] = {"alertas": "alertas_sugerencias.xlsx", "resumen": "resumen_diario.xlsx"}
SHEET = "Suscripciones"
HEADERS = ["Usuario de Telegram", "ASADA", "ID de la ASADA", "Cantón", "Provincia", "Región", "Idioma", "Fecha de suscripción", "Consentimiento", "Estado"]
PENDING, ACTIVE, STOPPED = "Pendiente /start", "Activo", "Baja"
# Cambia cada vez que cambia el texto del consentimiento en `web/src/NewsletterForm.tsx`.
CONSENT_VERSION = "2026-11-v1"
USERNAME_RE = re.compile(r"^@[A-Za-z][A-Za-z0-9_]{4,31}$")  # Telegram: 5 a 32 caracteres, empieza con letra
LANGS = ("es", "en")
TZ = ZoneInfo("America/Costa_Rica")

_LOCK = threading.Lock()

MESSAGES = {
    "username": ("Escribí tu usuario de Telegram empezando con @ (5 a 32 letras, números o guion bajo).", "Enter your Telegram username starting with @ (5 to 32 letters, numbers or underscores)."),
    "kind": ("Elegí una opción: alertas y sugerencias, o resumen diario.", "Choose one option: alerts and suggestions, or daily summary."),
    "consent": ("Tenés que aceptar el consentimiento informado para suscribirte.", "You must accept the informed consent to subscribe."),
    "consent_version": ("El texto del consentimiento cambió. Recargá la página e intentá de nuevo.", "The consent text has changed. Reload the page and try again."),
    "asada": ("No encontramos esa ASADA. Buscala de nuevo.", "We could not find that ASADA. Search for it again."),
    "rate": ("Hubo demasiados intentos. Probá de nuevo más tarde.", "Too many attempts. Try again later."),
    "storage": ("No pudimos guardar tu suscripción ahora (¿el archivo está abierto?). Probá de nuevo en un momento.", "We could not save your subscription right now (is the file open?). Try again in a moment."),
}


class SubscriptionError(ValueError):
    """Una validación falló. `code` identifica el campo; el mensaje sale en el idioma pedido."""

    def __init__(self, code: str, lang: str = "es"):
        self.code = code
        self.message = MESSAGES[code][1 if lang == "en" else 0]
        super().__init__(self.message)


# --- Catálogos (los mismos JSON que usa la página) ---

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


# --- Excel ---

def excel_path(kind: str, data_dir: Path | None = None) -> Path:
    return (data_dir or DATA_DIR) / KINDS[kind]


def read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    book = load_workbook(path, read_only=True)
    try:
        rows = list(book[SHEET].iter_rows(min_row=2, values_only=True))
    finally:
        book.close()
    return [dict(zip(HEADERS, ["" if value is None else str(value) for value in row])) for row in rows if row and row[0]]


def write_rows(path: Path, rows: list[dict]) -> None:
    """Escribe el Excel completo en un archivo temporal y lo reemplaza: nunca queda a medias."""
    book = Workbook()
    sheet = book.active
    sheet.title = SHEET
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append([row.get(header, "") for header in HEADERS])
    for line in sheet.iter_rows(min_row=2):
        for cell in line:
            cell.data_type = "s"  # texto siempre: ningún dato se interpreta como fórmula
    for index, header in enumerate(HEADERS, start=1):
        width = max([len(header), *(len(str(row.get(header, ""))) for row in rows)] or [len(header)])
        sheet.column_dimensions[get_column_letter(index)].width = min(width + 2, 60)
    sheet.freeze_panes = "A2"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(suffix=".xlsx", dir=path.parent)
    os.close(handle)
    try:
        book.save(temp)
        os.replace(temp, path)  # en Windows falla si el Excel está abierto
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def same_person(row: dict, username: str, asada_id: str) -> bool:
    return row["Usuario de Telegram"].lower() == username.lower() and row["ID de la ASADA"] == asada_id


# --- Suscribirse ---

def now_text(now: datetime | None = None) -> str:
    return (now or datetime.now(TZ)).isoformat(timespec="seconds")


def subscribe(username: str, kind: str, asada_id: str, consent: bool, lang: str = "es", consent_version: str = CONSENT_VERSION, *,
              data_dir: Path | None = None, asadas_path: Path = ASADAS, index_path: Path = CANTON_INDEX,
              predictions_path: Path = PREDICTIONS, now: datetime | None = None) -> dict:
    """Valida y guarda la suscripción. Devuelve la fila guardada.

    La misma persona con la misma ASADA no se duplica: si cambia de opción, pasa de un Excel al otro.
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
        with _LOCK:
            for other in KINDS:
                path = excel_path(other, data_dir)
                rows = read_rows(path)
                kept = [item for item in rows if not same_person(item, username, asada_id)]
                if other == kind:
                    kept.append(row)
                if other == kind or len(kept) != len(rows):
                    write_rows(path, kept)
    except OSError:
        raise SubscriptionError("storage", lang) from None
    return row


# --- Lo que lee el envío ---

def all_subscribers(data_dir: Path | None = None) -> list[dict]:
    """Todas las suscripciones, con su opción en `kind` («alertas» o «resumen»)."""
    return [{**row, "kind": kind} for kind in KINDS for row in read_rows(excel_path(kind, data_dir))]


def update_state(changes: list[tuple[str, str, str, str]], data_dir: Path | None = None) -> int:
    """Cambia el estado de filas. Cada cambio es (kind, usuario, id de la ASADA, estado nuevo). Devuelve cuántas filas cambió."""
    changed = 0
    with _LOCK:
        for kind in KINDS:
            wanted = {(user.lower(), asada): state for k, user, asada, state in changes if k == kind}
            if not wanted:
                continue
            path = excel_path(kind, data_dir)
            rows = read_rows(path)
            touched = False
            for row in rows:
                state = wanted.get((row["Usuario de Telegram"].lower(), row["ID de la ASADA"]))
                if state and row["Estado"] != state:
                    row["Estado"] = state
                    touched = True
                    changed += 1
            if touched:
                write_rows(path, rows)
    return changed


def as_recipient(row: dict) -> dict:
    """La fila del Excel como la espera `telegram_alerts` (`asada`, `canton`, `province`, `region`, `lang`)."""
    return {"asada": row["ASADA"], "canton": row["Cantón"], "province": row["Provincia"], "region": row["Región"], "lang": row["Idioma"] or "es"}


# --- Límite de intentos y datos del bot ---

class RateLimiter:
    """Máximo `limit` intentos por dirección en `window` segundos (en memoria; protege el formulario público)."""

    def __init__(self, limit: int = 10, window: float = 3600.0, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self.hits: dict[str, list[float]] = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self.lock:
            recent = [stamp for stamp in self.hits.get(key, []) if now - stamp < self.window]
            if len(recent) >= self.limit:
                self.hits[key] = recent
                return False
            self.hits[key] = [*recent, now]
            return True


@dataclass
class BotInfo:
    username: str

    @property
    def link(self) -> str:
        return f"https://t.me/{self.username}"


_BOT_CACHE: dict[str, tuple[float, BotInfo | None]] = {}


def bot_info(token: str | None, session: Any = requests, environ: dict[str, str] | None = None, ttl: float = 600.0) -> BotInfo | None:
    """Usuario del bot, para el botón «Abrir el bot». Sin token (o si Telegram no responde) devuelve None: el envío aún no está activo."""
    from .telegram_alerts import TelegramError, call
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
            info = BotInfo(call(token, "getMe", session=session)["username"])
        except (TelegramError, KeyError):
            info = None
    _BOT_CACHE[token] = (time.monotonic(), info)
    return info
