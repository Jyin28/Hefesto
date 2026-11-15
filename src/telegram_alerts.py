"""Avisos de prueba por Telegram a partir de las predicciones del sitio.

Genera tres avisos (calor, probabilidad de lluvia, zona afectada por El Niño) con las cifras de `predicciones.json`, los
asigna a las personas de prueba de `config/telegram_recipients.json` y los envía con un bot de Telegram.

Cada aviso solo se arma si los datos lo respaldan; si no, se rechaza con un motivo. Son avisos EXPERIMENTALES de una
estimación regional: no reemplazan los avisos del IMN, el AyA ni de la ASADA, y los textos lo dicen.

Reglas de Telegram que condicionan el envío:
  * Un bot no puede escribirle primero a una persona ni buscarla por @usuario: cada persona debe abrir el bot y enviar /start.
    `discover` lee esos mensajes y guarda el Chat ID de cada @usuario en `data/telegram_chats.json` (no se versiona).
  * El token del bot es secreto: va en la variable de entorno TELEGRAM_BOT_TOKEN o en el archivo `.env` (no se versiona).

Uso (desde la raíz de Hefesto):
    python -m src.telegram_alerts preview      # muestra los avisos y actualiza la vista previa del sitio (no envía nada)
    python -m src.telegram_alerts discover     # lee los /start recibidos y guarda los Chat ID
    python -m src.telegram_alerts send --yes   # envía los avisos
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "web" / "public" / "data" / "predicciones.json"
RECIPIENTS = ROOT / "config" / "telegram_recipients.json"
CHATS = ROOT / "data" / "telegram_chats.json"
PUBLIC_ALERTS = ROOT / "web" / "public" / "data" / "alertas.json"
DOTENV = ROOT / ".env"

MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DISCLAIMER = "Es una estimación regional experimental, sin validar con estaciones locales. No es un aviso oficial: seguí los avisos del IMN, el AyA y tu ASADA."
ALERT_KINDS = ("heat", "rain", "nino")
# Umbrales con los que un aviso se considera respaldado por los datos.
HEAT_MIN_ANOMALY = 0.5      # °C sobre el promedio 1991-2020 del mes
RAIN_MIN_SHARE = 0.7        # fracción de años análogos con al menos 100 mm en el mes
NINO_MIN_DEFICIT = -20.0    # % de lluvia frente a lo normal en los años análogos


class AlertNotSupported(ValueError):
    """Los datos no respaldan este aviso: no se envía."""


class TelegramError(RuntimeError):
    """Falla de la API de Telegram. Nunca incluye el token."""


# --- Formato ---

def num(value: float, digits: int = 1) -> str:
    """Coma decimal y espacio fino de miles, como en el resto del sitio (es-CR)."""
    text = f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")
    return text


def month_text(label: str) -> str:
    year, month = label.split("-")
    return f"{MONTHS[int(month) - 1]} de {year}"


def month_short(label: str) -> str:
    year, month = label.split("-")
    return f"{MONTHS[int(month) - 1]} {year}"


# --- Datos ---

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def first_row(payload: dict, variable: str, region: str) -> dict:
    return payload["variables"][variable]["regions"][region]["rows"][0]


def place(recipient: dict) -> str:
    """«Liberia, Guanacaste»; si cantón y provincia se llaman igual, solo «Limón»."""
    return recipient["canton"] if recipient["canton"] == recipient["province"] else f"{recipient['canton']}, {recipient['province']}"


# --- Avisos ---

def heat_alert(payload: dict, recipient: dict) -> str:
    region = recipient["region"]
    rows = payload["variables"]["T2M"]["regions"][region]["rows"]
    row = rows[0]
    if row["estimate"] is None:
        raise AlertNotSupported(f"{region}: sin pronóstico de temperatura para {row['target_month']}.")
    ref = row["reference"]
    anomaly = row["estimate"] - ref["mean"]
    if anomaly < HEAT_MIN_ANOMALY:
        raise AlertNotSupported(f"{region}: la temperatura estimada solo supera lo normal en {num(anomaly)} °C (mínimo {HEAT_MIN_ANOMALY}).")
    lines = [
        "🌡️ Hefesto · Aviso experimental de calor",
        f"📍 {place(recipient)} (sector {recipient['zone']})",
        "",
        f"Para {month_text(row['target_month'])} se estima una temperatura media de {num(row['estimate'])} °C en el sector "
        f"(banda de 90 %: {num(row['lower90'])} a {num(row['upper90'])} °C). Lo normal en ese mes (1991–2020) es {num(ref['mean'])} °C: "
        f"unos {num(round(row['estimate'], 1) - round(ref['mean'], 1))} °C más caliente" + (", por encima del 90 % de los años de referencia." if row["estimate"] > ref["p90"] else "."),
    ]
    second = rows[1] if len(rows) > 1 else None
    if second and second["estimate"] is not None:
        lines.append(f"{month_short(second['target_month']).capitalize()}: {num(second['estimate'])} °C (normal {num(second['reference']['mean'])} °C).")
    lines += ["", "Qué podés hacer: hidratate seguido, evitá el sol de 10 a. m. a 2 p. m. y cuidá a niños y personas mayores.", "", DISCLAIMER]
    return "\n".join(lines)


def rain_alert(payload: dict, recipient: dict) -> str:
    region = recipient["region"]
    row = first_row(payload, "PRECTOTCORR", region)
    analog = next((m for m in payload["rain_analog"].get(region, {}).get("months", []) if m["month"] == row["target_month"]), None)
    if analog is None:
        raise AlertNotSupported(f"{region}: sin años análogos para {row['target_month']}.")
    if analog["share_above_100mm"] < RAIN_MIN_SHARE:
        raise AlertNotSupported(f"{region}: solo {round(100 * analog['share_above_100mm'])} % de los años análogos llovió 100 mm o más.")
    ref = row["reference"]
    n = analog["n_years"]
    rainy = round(analog["share_above_100mm"] * n)
    drier = analog["anomaly_pct"] < -5
    lines = [
        "🌧️ Hefesto · Aviso de lluvia",
        f"📍 {place(recipient)} (sector {recipient['zone']})",
        "",
        f"Alta probabilidad de lluvia en {month_text(row['target_month'])}: es uno de los meses más lluviosos del sector "
        f"(lo normal son unos {num(ref['mean'], 0)} mm y en 9 de cada 10 años llovió más de {num(ref['p10'], 0)} mm). "
        f"En {rainy} de {n} años con un Niño como el actual llovió al menos 100 mm.",
    ]
    if drier:
        lines += ["", f"Ojo: en esos años llovió cerca de {num(abs(analog['anomaly_pct']), 0)} % menos que lo normal (unos {num(analog['mean_mm'], 0)} mm). "
                      "Es más probable un mes con menos lluvia de la habitual que con más."]
    lines += ["", "No hay un pronóstico de lluvia validado: esto combina la lluvia histórica del mes con lo que pasó en años parecidos.", "", DISCLAIMER]
    return "\n".join(lines)


def nino_alert(payload: dict, recipient: dict) -> str:
    enso = payload["enso"]
    if enso["status"] != "active":
        raise AlertNotSupported("No hay un episodio de El Niño en curso en los datos de RONI.")
    region = recipient["region"]
    months = payload["rain_analog"].get(region, {}).get("months", [])
    deficits = [m for m in months[:2] if m["anomaly_pct"] <= NINO_MIN_DEFICIT]
    if not deficits:
        raise AlertNotSupported(f"{region}: en los años análogos la lluvia no bajó {abs(NINO_MIN_DEFICIT):g} % ni más en los primeros meses.")
    analog = enso.get("analog")
    lines = [
        "⚠️ Hefesto · Aviso de El Niño",
        f"📍 {place(recipient)} ({recipient['zone']})",
        "",
        f"El Niño está en curso desde {month_text(enso['start'])} y ya es {enso['category']} (RONI de {num(enso['latest']['value'])} en {month_short(enso['latest']['month'])}).",
    ]
    if analog:
        window = analog["end_window"]
        lines.append(f"Según episodios fuertes anteriores, podría seguir hasta entre {month_short(window['earliest'])} y {month_short(window['latest'])} "
                     f"(lo más típico: {month_short(window['typical'])}).")
    where = "el promedio del país" if region == "CR" else f"el sector {recipient['zone']}"
    lines += ["", f"En años parecidos, en {where} llovió "
                  + " y ".join(f"cerca de {num(abs(m['anomaly_pct']), 0)} % menos en {MONTHS[int(m['month'][5:]) - 1]}" for m in deficits) + " de lo normal.",
              "Con menos lluvia bajan los caudales: ahorrá agua, revisá fugas y seguí los avisos de tu ASADA o del AyA.", "", DISCLAIMER]
    return "\n".join(lines)


BUILDERS = {"heat": heat_alert, "rain": rain_alert, "nino": nino_alert}


def build_alerts(payload: dict, recipients: list[dict]) -> list[dict]:
    """Un aviso por persona. Lanza `AlertNotSupported` si los datos no respaldan alguno: no se envía nada a medias."""
    alerts = []
    for recipient in recipients:
        kind = recipient["alert"]
        if kind not in BUILDERS:
            raise ValueError(f"Tipo de aviso desconocido: {kind}")
        alerts.append({"kind": kind, "username": recipient["username"], "canton": recipient["canton"], "province": recipient["province"],
                       "zone": recipient["zone"], "region": recipient["region"], "text": BUILDERS[kind](payload, recipient)})
    return alerts


# --- Telegram ---

def load_token(environ: dict[str, str] | None = None, dotenv: Path = DOTENV) -> str | None:
    environ = os.environ if environ is None else environ
    if environ.get("TELEGRAM_BOT_TOKEN"):
        return environ["TELEGRAM_BOT_TOKEN"].strip()
    if dotenv.is_file():
        for line in dotenv.read_text(encoding="utf-8-sig").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "TELEGRAM_BOT_TOKEN" and value.strip():
                return value.strip().strip("'\"")
    return None


def call(token: str, method: str, payload: dict | None = None, session: Any = requests) -> Any:
    """Llama a la API del bot. Los errores nunca muestran la URL (lleva el token)."""
    try:
        response = session.post(f"https://api.telegram.org/bot{token}/{method}", json=payload or {}, timeout=30)
        body = response.json()
    except (requests.RequestException, ValueError) as error:
        raise TelegramError(f"No se pudo hablar con Telegram ({type(error).__name__}).") from None
    if not body.get("ok"):
        raise TelegramError(f"Telegram rechazó {method}: {body.get('description', 'sin detalle')} (código {body.get('error_code')}).")
    return body["result"]


def discover(token: str, recipients: list[dict], chats_path: Path = CHATS, session: Any = requests) -> dict[str, int]:
    """Guarda el Chat ID de cada @usuario de prueba que ya le escribió al bot (chats privados)."""
    wanted = {recipient["username"].lower() for recipient in recipients}
    chats = load_json(chats_path) if chats_path.is_file() else {}
    for update in call(token, "getUpdates", {"timeout": 0, "allowed_updates": ["message"]}, session):
        message = update.get("message") or {}
        sender, chat = message.get("from") or {}, message.get("chat") or {}
        username = (sender.get("username") or "").lower()
        if chat.get("type") == "private" and username in wanted:
            chats[username] = chat["id"]
    chats_path.parent.mkdir(parents=True, exist_ok=True)
    chats_path.write_text(json.dumps(chats, indent=2) + "\n", encoding="utf-8")
    return {name: chats[name] for name in sorted(wanted) if name in chats}


def send(token: str, alerts: list[dict], chats: dict[str, int], session: Any = requests, now: datetime | None = None) -> list[dict]:
    """Envía cada aviso a su chat. Devuelve el resultado por aviso; los que no tienen Chat ID quedan pendientes."""
    now = now or datetime.now(timezone.utc)
    results = []
    for alert in alerts:
        chat_id = chats.get(alert["username"].lower())
        if chat_id is None:
            results.append({**alert, "status": "pending", "detail": "La persona todavía no le escribió al bot (/start)."})
            continue
        try:
            call(token, "sendMessage", {"chat_id": chat_id, "text": alert["text"], "disable_web_page_preview": True}, session)
            results.append({**alert, "status": "sent", "sent_at": now.isoformat(timespec="seconds")})
        except TelegramError as error:
            results.append({**alert, "status": "failed", "detail": str(error)})
    return results


def public_view(results: list[dict]) -> list[dict]:
    """Lo que ve el sitio: el texto y su estado, sin @usuarios ni Chat ID (son datos de personas)."""
    return [{key: item[key] for key in ("kind", "canton", "province", "zone", "region", "text", "status", "sent_at") if key in item} for item in results]


def write_public(results: list[dict], target: Path = PUBLIC_ALERTS) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "alerts": public_view(results)},
                                 ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Avisos de prueba por Telegram a partir de las predicciones del sitio.")
    parser.add_argument("command", choices=("preview", "discover", "send"))
    parser.add_argument("--yes", action="store_true", help="Confirma el envío real (sin esto, `send` solo muestra qué enviaría).")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    if not RECIPIENTS.is_file():
        print(f"Falta {RECIPIENTS.relative_to(ROOT)}. Copiá config/telegram_recipients.example.json y completalo.", file=sys.stderr)
        return 2
    recipients = load_json(RECIPIENTS)["recipients"]
    try:
        alerts = build_alerts(load_json(PREDICTIONS), recipients)
    except AlertNotSupported as error:
        print(f"Aviso no respaldado por los datos, no se envía nada: {error}", file=sys.stderr)
        return 3

    chats = load_json(CHATS) if CHATS.is_file() else {}
    if args.command == "preview":
        for alert in alerts:
            print(f"--- {alert['kind']} → @{alert['username']} · {alert['canton']} ---\n{alert['text']}\n")
        write_public([{**a, "status": "preview"} for a in alerts])
        print(f"Vista previa del sitio actualizada: {PUBLIC_ALERTS.relative_to(ROOT)}")
        return 0

    token = load_token()
    if not token:
        print("Falta el token del bot: definí TELEGRAM_BOT_TOKEN o escribilo en .env (TELEGRAM_BOT_TOKEN=...).", file=sys.stderr)
        return 2
    try:
        if args.command == "discover":
            bot = call(token, "getMe")
            found = discover(token, recipients)
            print(f"Bot: @{bot['username']} (https://t.me/{bot['username']}). Chat ID encontrados: {len(found)} de {len(recipients)}.")
            for recipient in recipients:
                state = "listo" if recipient["username"].lower() in found else "pendiente: abrir el bot y enviar /start"
                print(f"  @{recipient['username']}: {state}")
            return 0
        if not args.yes:
            print("Esto enviaría:")
            for alert in alerts:
                state = "con Chat ID" if alert["username"].lower() in chats else "SIN Chat ID (pendiente)"
                print(f"  {alert['kind']} → @{alert['username']} ({alert['canton']}) · {state}")
            print("Repetí con --yes para enviar.")
            return 0
        results = send(token, alerts, chats)
    except TelegramError as error:
        print(error, file=sys.stderr)
        return 1
    write_public(results)
    for item in results:
        print(f"  {item['kind']} → @{item['username']}: {item['status']}" + (f" ({item['detail']})" if item.get("detail") else ""))
    return 0 if all(item["status"] == "sent" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
