"""Lógica de las tres funciones de Vercel (`api/*.py`). Cada una recibe lo que llegó y devuelve `(estado HTTP, JSON)`.

Los handlers de `api/` solo leen la petición y llaman aquí: así todo se prueba sin levantar un servidor.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
from datetime import date
from typing import Any

import requests

from . import bot
from . import suscripciones as subs
from . import telegram_alerts as tg
from .store import FakeStore, RedisStore, StoreError, store_from_env

logger = logging.getLogger(__name__)
Store = RedisStore | FakeStore


def _same(given: str | None, expected: str | None) -> bool:
    """Compara secretos sin revelar dónde difieren. Sin secreto configurado, nada pasa."""
    return bool(expected) and hmac.compare_digest((given or "").encode(), expected.encode())


def _bot_payload(token: str | None, session: Any, environ: dict[str, str] | None):
    info = subs.bot_info(token, session, environ)
    return {"username": info.username, "link": info.link} if info else None


def suscribir(body: bytes, ip: str, store: Store | None = None, session: Any = requests, environ: dict[str, str] | None = None) -> tuple[int, dict]:
    """POST /api/suscripciones: guarda a la persona (ver `suscripciones.subscribe`)."""
    environ = os.environ if environ is None else environ
    try:
        data = json.loads(body or b"{}")
        username, kind, asada_id = str(data["username"]), str(data["kind"]), str(data["asada_id"])
        consent, version = data["consent"], str(data["consent_version"])
        lang = data.get("lang", "es")
        if not isinstance(consent, bool) or not isinstance(lang, str):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        return 422, {"detail": {"code": "bad_request", "message": "Faltan datos de la suscripción."}}
    lang = lang if lang in subs.LANGS else "es"
    try:
        store = store or store_from_env(environ)
    except StoreError as error:
        logger.error("%s", error)
        return 503, {"detail": {"code": "storage", "message": subs.MESSAGES["storage"][1 if lang == "en" else 0]}}
    if not subs.allow_attempt(store, ip):
        return 429, {"detail": {"code": "rate", "message": subs.MESSAGES["rate"][1 if lang == "en" else 0]}}
    try:
        row = subs.subscribe(store, username, kind, asada_id, consent, lang, version)
    except subs.SubscriptionError as error:
        return (503 if error.code == "storage" else 422), {"detail": {"code": error.code, "message": error.message}}
    # Solo se devuelve lo necesario para el siguiente paso: nunca las filas guardadas.
    return 200, {"ok": True, "kind": kind, "state": row["Estado"], "bot": _bot_payload(tg.load_token(environ), session, environ)}


def webhook(body: bytes, secret_header: str | None, store: Store | None = None, session: Any = requests,
            environ: dict[str, str] | None = None, today: date | None = None) -> tuple[int, dict]:
    """POST /api/telegram: Telegram entrega aquí cada mensaje del bot (se registra con `scripts/telegram_webhook.ps1`)."""
    environ = os.environ if environ is None else environ
    if not _same(secret_header, environ.get("TELEGRAM_WEBHOOK_SECRET")):
        return 401, {"ok": False}
    token = tg.load_token(environ)
    if not token:
        return 503, {"ok": False}
    try:
        update = json.loads(body or b"{}")
    except ValueError:
        return 400, {"ok": False}
    try:
        outcome = bot.handle_update(store or store_from_env(environ), token, update, today=today, session=session)
    except Exception:  # Telegram reintenta sin parar los errores 5xx: se registra y se responde 200
        logger.exception("Telegram: falló el procesamiento de un mensaje")
        return 200, {"ok": True, "result": "error"}
    return 200, {"ok": True, "result": outcome}


def enviar(authorization: str | None, store: Store | None = None, session: Any = requests, environ: dict[str, str] | None = None,
           today: date | None = None, dry_run: bool = False) -> tuple[int, dict]:
    """GET /api/enviar: lo llama el cron de Vercel una vez al día con `Authorization: Bearer <CRON_SECRET>`."""
    environ = os.environ if environ is None else environ
    secret = environ.get("CRON_SECRET")
    if not _same(authorization, f"Bearer {secret}" if secret else None):
        return 401, {"ok": False}
    token = tg.load_token(environ)
    if not token:
        return 503, {"ok": False, "detail": "Falta TELEGRAM_BOT_TOKEN."}
    try:
        results = bot.send_daily(store or store_from_env(environ), token, today=today, session=session, dry_run=dry_run)
    except (StoreError, tg.TelegramError) as error:
        logger.error("Envío diario: %s", error)
        return 500, {"ok": False}
    return 200, {
        "ok": True, "considerados": len(results),
        "enviados": sum(1 for item in results if item["status"] == "enviado"),
        "fallaron": sum(1 for item in results if item["status"] == "falló"),
    }
