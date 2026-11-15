"""Bot de Telegram de AguaAlerta en Vercel (versión de `src/telegram_newsletter.py` que guarda en Redis).

Dos entradas, sin procesos que queden corriendo:

  handle_update  Un mensaje que Telegram le entrega al webhook (`api/telegram.py`). Cuando la MISMA cuenta que se suscribió le
                 escribe /start (después de suscribirse), guarda su Chat ID, la pasa a «Activo» y le manda la bienvenida y un
                 mensaje de prueba. /stop la da de baja.
  send_daily     Lo que corre el cron de Vercel una vez al día (`api/enviar.py`): envía a las suscripciones «Activo»
                 * alertas y sugerencias: los avisos (calor, lluvia, El Niño) que los datos respaldan para la zona de su ASADA;
                   si ninguno aplica no se envía nada, y no se repite el mismo aviso hasta que cambien las predicciones.
                 * resumen diario: una vez al día, las cifras de su zona con sugerencias.

Los textos salen de `telegram_alerts.py`, que es copia exacta de `src/telegram_alerts.py`.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import requests

from . import suscripciones as subs
from . import telegram_alerts as tg
from .store import CHATS, SENT, FakeStore, RedisStore

Store = RedisStore | FakeStore


def lang_of(row: dict) -> str:
    return row.get("Idioma") if row.get("Idioma") in tg.LANGS else "es"


def load_payload() -> dict:
    """Las predicciones que respaldan los avisos (`web/public/data/predicciones.json`)."""
    return json.loads(subs.PREDICTIONS.read_text(encoding="utf-8-sig"))


# --- /start y /stop (webhook) ---

def handle_update(store: Store, token: str, update: dict, payload: dict | None = None, today: date | None = None,
                  session: Any = requests) -> str:
    """Procesa un mensaje del bot. Devuelve «activated», «stopped» o «ignored». Solo un /start posterior a la suscripción activa a la persona."""
    today = today or date.today()
    message = update.get("message") or {}
    sender, chat = message.get("from") or {}, message.get("chat") or {}
    username = (sender.get("username") or "").lower()
    text = (message.get("text") or "").strip()
    if chat.get("type") != "private" or not username or not text.startswith("/"):
        return "ignored"
    command = text.split()[0].split("@")[0].lower()
    mine = [row for row in subs.all_subscribers(store) if row["Usuario de Telegram"].lstrip("@").lower() == username]

    if command == "/start":
        sent_at = message.get("date", 0)
        fresh = [row for row in mine if row["Estado"] == subs.PENDING
                 and datetime.fromisoformat(row["Fecha de suscripción"]).timestamp() <= sent_at]
        if not fresh:
            pending = [row for row in mine if row["Estado"] == subs.PENDING]
            if pending or not any(row["Estado"] == subs.ACTIVE for row in mine):  # se le explica qué falta
                reply = tg.resend_start_text(lang_of(pending[0])) if pending else tg.not_subscribed_text()
                try:
                    tg.send_message(token, chat["id"], reply, session)
                except tg.TelegramError:
                    pass
            return "ignored"
        store.hset(CHATS, username, str(chat["id"]))
        subs.update_state(store, [(row["kind"], row["Usuario de Telegram"], row["ID de la ASADA"], subs.ACTIVE) for row in fresh])
        if payload is None:
            payload = load_payload()
        sent = store.hgetall(SENT)
        before = dict(sent)
        for row in fresh:
            try:
                tg.send_message(token, chat["id"], tg.welcome_text(row["kind"], subs.as_recipient(row), lang_of(row)), session)
            except tg.TelegramError:
                pass  # quedó activa igual; el aviso de bienvenida es solo cortesía
            send_test_message(token, chat["id"], row, payload, sent, today, session)
        for key, value in sent.items():  # lo anotado como enviado, para que el envío diario no lo repita
            if before.get(key) != value:
                store.hset(SENT, key, value)
        return "activated"

    if command == "/stop" and mine:
        subs.update_state(store, [(row["kind"], row["Usuario de Telegram"], row["ID de la ASADA"], subs.STOPPED) for row in mine])
        try:
            tg.send_message(token, chat["id"], tg.goodbye_text(lang_of(mine[0])), session)
        except tg.TelegramError:
            pass
        return "stopped"
    return "ignored"


def send_test_message(token: str, chat_id: int, row: dict, payload: dict, sent: dict[str, str], today: date, session: Any = requests) -> None:
    """Mensaje de prueba al activarse: muestra lo que la persona va a recibir, con los datos de hoy.

    Resumen diario → el resumen de hoy (y se anota como enviado hoy). Alertas → los avisos vigentes, o una nota si no hay ninguno
    (los avisos enviados se anotan para no repetirlos en el envío diario).
    """
    lang, recipient, user = lang_of(row), subs.as_recipient(row), row["Usuario de Telegram"].lower()
    intro = tg.test_intro_text(row["kind"], lang)
    try:
        if row["kind"] == "resumen":
            text, _ = tg.daily_summary(payload, recipient, lang, today)
            tg.send_message(token, chat_id, f"{intro}\n\n{text}", session)
            sent[f"{user}|{row['ID de la ASADA']}|resumen"] = today.isoformat()
            return
        alerts = tg.supported_alerts(payload, recipient, lang)
        if not alerts:
            tg.send_message(token, chat_id, f"{intro}\n\n{tg.no_alerts_now_text(lang)}", session)
            return
        tg.send_message(token, chat_id, intro, session)
        for alert in alerts:
            tg.send_message(token, chat_id, tg.render_alert(alert, recipient, lang), session)
            sent[f"{user}|{row['ID de la ASADA']}|alertas|{alert.kind}"] = update_stamp(payload)
    except tg.TelegramError:
        pass  # el mensaje de prueba es solo cortesía


# --- Envío diario (cron) ---

def update_stamp(payload: dict) -> str:
    """Identifica una versión de las predicciones: cambia cuando cambian los datos, no cuando se vuelve a correr el cálculo."""
    return f"{payload['data_through']}/{payload['roni_through']}/{payload['forecast_start']}"


def plan_messages(payload: dict, rows: list[dict], chats: dict[str, int], sent: dict[str, str], today: date) -> list[dict]:
    """Qué se enviaría ahora: una entrada por mensaje, con su estado («listo», «pendiente» o «ya enviado»)."""
    stamp, plan = update_stamp(payload), []
    for row in rows:
        if row["Estado"] != subs.ACTIVE:
            continue
        user, lang, recipient = row["Usuario de Telegram"], lang_of(row), subs.as_recipient(row)
        chat_id = chats.get(user.lstrip("@").lower())
        base = {"user": user, "asada": row["ASADA"], "kind": row["kind"], "chat_id": chat_id, "asada_id": row["ID de la ASADA"]}
        if row["kind"] == "alertas":
            for alert in tg.supported_alerts(payload, recipient, lang):
                key = f"{user.lower()}|{row['ID de la ASADA']}|alertas|{alert.kind}"
                plan.append({**base, "key": key, "value": stamp, "alert": alert.kind, "text": tg.render_alert(alert, recipient, lang),
                             "status": "ya enviado" if sent.get(key) == stamp else "pendiente" if chat_id is None else "listo"})
        else:
            key = f"{user.lower()}|{row['ID de la ASADA']}|resumen"
            text, risky = tg.daily_summary(payload, recipient, lang, today)
            plan.append({**base, "key": key, "value": today.isoformat(), "alert": "riesgo" if risky else "sin cambios", "text": text,
                         "status": "ya enviado" if sent.get(key) == today.isoformat() else "pendiente" if chat_id is None else "listo"})
    return plan


def send_daily(store: Store, token: str | None, payload: dict | None = None, today: date | None = None, session: Any = requests,
               dry_run: bool = False) -> list[dict]:
    """Envía los mensajes que tocan. Con `dry_run` solo los arma. Devuelve el resultado por mensaje (sin el texto)."""
    today = today or date.today()
    payload = payload or load_payload()
    chats = {user: int(chat_id) for user, chat_id in store.hgetall(CHATS).items()}
    sent = store.hgetall(SENT)
    plan = plan_messages(payload, subs.all_subscribers(store), chats, sent, today)
    results, blocked = [], []
    try:
        for item in plan:
            status, detail = item["status"], ""
            if status == "listo" and not dry_run:
                try:
                    tg.send_message(token, item["chat_id"], item["text"], session)
                    store.hset(SENT, item["key"], item["value"])  # se anota mensaje por mensaje: si algo se corta, no se repite lo ya enviado
                    status = "enviado"
                except tg.TelegramError as error:
                    status, detail = "falló", str(error)
                    if "403" in detail:  # la persona bloqueó o borró el bot: se la da de baja
                        blocked.append((item["kind"], item["user"], item["asada_id"], subs.STOPPED))
            results.append({"user": item["user"], "asada": item["asada"], "kind": item["kind"], "mensaje": item["alert"], "status": status, "detail": detail})
    finally:
        if blocked:
            subs.update_state(store, blocked)
    return results
