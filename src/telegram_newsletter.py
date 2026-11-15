"""Vincula a las personas suscritas con su chat de Telegram y les envía el newsletter.

Las suscripciones las guarda `src/newsletter.py` en dos Excel (`data/suscripciones/`). Este comando hace el resto:

  discover   Lee los mensajes que recibió el bot. Cuando la MISMA cuenta que se suscribió le escribe /start (después de
             suscribirse), guarda su Chat ID, la pasa a «Activo» y le manda un mensaje de bienvenida. /stop la da de baja.
  send       Envía lo que corresponda a las suscripciones «Activo»:
               * alertas y sugerencias: los avisos (calor, lluvia, El Niño) que los datos respaldan para la zona de su ASADA.
                 Si ninguno aplica no se envía nada, y no se repite el mismo aviso hasta que cambien las predicciones.
               * resumen diario: una vez al día, las cifras de su zona con sugerencias; si no hay riesgos, dice que no hubo
                 cambios significativos.
  run        `discover` y luego `send` (lo que se programa una vez al día).

Sin `--yes`, `send` y `run` solo muestran qué enviarían. El token va en TELEGRAM_BOT_TOKEN (variable de entorno o `.env`).
Las predicciones (`web/public/data/predicciones.json`) se actualizan con `python -m src.predictions`, normalmente una vez al mes.

Uso (desde la raíz del proyecto):
    python -m src.telegram_newsletter discover
    python -m src.telegram_newsletter send --yes
    python -m src.telegram_newsletter run --yes
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

from . import newsletter, telegram_alerts as tg

ROOT = Path(__file__).resolve().parents[1]
CHATS = ROOT / "data" / "telegram_chats.json"   # @usuario (minúsculas) → Chat ID. Datos personales: no se versiona.
STATE = ROOT / "data" / "telegram_sent.json"    # qué se envió ya y hasta qué mensaje se leyó. No se versiona.


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else default


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def lang_of(row: dict) -> str:
    return row.get("Idioma") if row.get("Idioma") in tg.LANGS else "es"


# --- discover ---

def discover(token: str, data_dir: Path | None = None, chats_path: Path | None = None, state_path: Path | None = None,
             session: Any = requests, payload: dict | None = None, today: date | None = None) -> dict[str, int]:
    """Procesa los mensajes nuevos del bot. Solo un /start posterior a la suscripción activa a la persona.

    Al activarse una suscripción se envía la bienvenida y un **mensaje de prueba** con lo que dicen los datos hoy
    (el resumen del día o los avisos vigentes), y se anota como enviado para que el envío normal no lo repita.
    """
    chats_path, state_path = chats_path or CHATS, state_path or STATE
    today = today or date.today()
    if payload is None and newsletter.PREDICTIONS.is_file():
        payload = json.loads(newsletter.PREDICTIONS.read_text(encoding="utf-8-sig"))
    state = load_json(state_path, {"update_offset": 0, "sent": {}})
    chats: dict[str, int] = load_json(chats_path, {})
    params: dict[str, Any] = {"timeout": 0, "allowed_updates": ["message"]}
    if state.get("update_offset"):
        params["offset"] = state["update_offset"]
    updates = tg.call(token, "getUpdates", params, session)
    subscribers = newsletter.all_subscribers(data_dir)
    summary = {"activated": 0, "stopped": 0, "ignored": 0}
    last_id = state.get("update_offset", 0) - 1
    for update in updates:
        last_id = max(last_id, update.get("update_id", last_id))
        message = update.get("message") or {}
        sender, chat = message.get("from") or {}, message.get("chat") or {}
        username = (sender.get("username") or "").lower()
        text = (message.get("text") or "").strip()
        if chat.get("type") != "private" or not username or not text.startswith("/"):
            summary["ignored"] += 1
            continue
        command = text.split()[0].split("@")[0].lower()
        mine = [row for row in subscribers if row["Usuario de Telegram"].lstrip("@").lower() == username]
        if command == "/start":
            sent_at = message.get("date", 0)
            fresh = [row for row in mine if row["Estado"] == newsletter.PENDING
                     and datetime.fromisoformat(row["Fecha de suscripción"]).timestamp() <= sent_at]
            if not fresh:
                summary["ignored"] += 1
                pending = [row for row in mine if row["Estado"] == newsletter.PENDING]
                if pending or not any(row["Estado"] == newsletter.ACTIVE for row in mine):  # se le explica qué falta
                    reply = tg.resend_start_text(lang_of(pending[0])) if pending else tg.not_subscribed_text()
                    try:
                        tg.send_message(token, chat["id"], reply, session)
                    except tg.TelegramError:
                        pass
                continue
            chats[username] = chat["id"]
            newsletter.update_state([(row["kind"], row["Usuario de Telegram"], row["ID de la ASADA"], newsletter.ACTIVE) for row in fresh], data_dir)
            for row in fresh:
                try:
                    tg.send_message(token, chat["id"], tg.welcome_text(row["kind"], newsletter.as_recipient(row), lang_of(row)), session)
                except tg.TelegramError:
                    pass  # quedó activa igual; el aviso de bienvenida es solo cortesía
                if payload is not None:
                    send_test_message(token, chat["id"], row, payload, state.setdefault("sent", {}), today, session)
            summary["activated"] += len(fresh)
        elif command == "/stop" and mine:
            newsletter.update_state([(row["kind"], row["Usuario de Telegram"], row["ID de la ASADA"], newsletter.STOPPED) for row in mine], data_dir)
            try:
                tg.send_message(token, chat["id"], tg.goodbye_text(lang_of(mine[0])), session)
            except tg.TelegramError:
                pass
            summary["stopped"] += len(mine)
        else:
            summary["ignored"] += 1
    if last_id >= 0:
        state["update_offset"] = last_id + 1  # confirma lo leído: Telegram no lo devuelve otra vez
    save_json(chats_path, chats)
    save_json(state_path, state)
    return summary


def send_test_message(token: str, chat_id: int, row: dict, payload: dict, sent: dict[str, str], today: date, session: Any = requests) -> None:
    """Mensaje de prueba al activarse: muestra lo que la persona va a recibir, con los datos de hoy.

    Resumen diario → el resumen de hoy (y se anota como enviado hoy). Alertas → los avisos vigentes, o una nota si no hay ninguno
    (los avisos enviados se anotan para no repetirlos en el envío normal).
    """
    lang, recipient, user = lang_of(row), newsletter.as_recipient(row), row["Usuario de Telegram"].lower()
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


# --- send ---

def update_stamp(payload: dict) -> str:
    """Identifica una versión de las predicciones: cambia cuando cambian los datos, no cuando se vuelve a correr el cálculo."""
    return f"{payload['data_through']}/{payload['roni_through']}/{payload['forecast_start']}"


def plan_messages(payload: dict, rows: list[dict], chats: dict[str, int], sent: dict[str, str], today: date) -> list[dict]:
    """Qué se enviaría ahora: una entrada por mensaje, con su estado («listo», «pendiente» o «ya enviado»)."""
    stamp, plan = update_stamp(payload), []
    for row in rows:
        if row["Estado"] != newsletter.ACTIVE:
            continue
        user, lang, recipient = row["Usuario de Telegram"], lang_of(row), newsletter.as_recipient(row)
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


def send(token: str | None, payload: dict, data_dir: Path | None = None, chats_path: Path | None = None, state_path: Path | None = None,
         session: Any = requests, today: date | None = None, dry_run: bool = False) -> list[dict]:
    """Envía los mensajes que tocan. Con `dry_run` solo los arma. Devuelve el resultado por mensaje (sin el texto)."""
    chats_path, state_path = chats_path or CHATS, state_path or STATE
    today = today or date.today()
    state = load_json(state_path, {"update_offset": 0, "sent": {}})
    chats = load_json(chats_path, {})
    plan = plan_messages(payload, newsletter.all_subscribers(data_dir), chats, state.setdefault("sent", {}), today)
    results, blocked = [], []
    try:
        for item in plan:
            status, detail = item["status"], ""
            if status == "listo" and not dry_run:
                try:
                    tg.send_message(token, item["chat_id"], item["text"], session)
                    state["sent"][item["key"]] = item["value"]
                    status = "enviado"
                except tg.TelegramError as error:
                    status, detail = "falló", str(error)
                    if "403" in detail:  # la persona bloqueó o borró el bot: se la da de baja
                        blocked.append((item["kind"], item["user"], item["asada_id"], newsletter.STOPPED))
            results.append({"user": item["user"], "asada": item["asada"], "kind": item["kind"], "mensaje": item["alert"], "status": status, "detail": detail})
    finally:
        if not dry_run:
            save_json(state_path, state)
            if blocked:
                newsletter.update_state(blocked, data_dir)
    return results


# --- CLI ---

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Newsletter de Telegram de AguaAlerta: vincula suscripciones y envía mensajes.")
    parser.add_argument("command", choices=("discover", "send", "run"))
    parser.add_argument("--yes", action="store_true", help="Confirma el envío real (sin esto, `send` y `run` solo muestran qué enviarían).")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    token = tg.load_token()
    if not token:
        print("Falta el token del bot: creá el bot con @BotFather y escribí TELEGRAM_BOT_TOKEN=... en el archivo .env (o definí la variable de entorno).", file=sys.stderr)
        return 2
    code = 0
    try:
        if args.command in ("discover", "run"):
            bot = tg.call(token, "getMe")
            found = discover(token)
            print(f"Bot @{bot['username']}: {found['activated']} suscripciones activadas, {found['stopped']} bajas, {found['ignored']} mensajes ignorados.")
        if args.command in ("send", "run"):
            payload = json.loads(newsletter.PREDICTIONS.read_text(encoding="utf-8-sig"))
            results = send(token, payload, dry_run=not args.yes)
            for item in results:
                print(f"  {item['kind']} → {item['user']} ({item['asada']}): {item['mensaje']} · {item['status']}" + (f" ({item['detail']})" if item["detail"] else ""))
            print(f"{len(results)} mensajes considerados." + ("" if args.yes else " Repetí con --yes para enviar de verdad."))
            code = 1 if any(item["status"] == "falló" for item in results) else 0
    except tg.TelegramError as error:
        print(error, file=sys.stderr)
        return 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
