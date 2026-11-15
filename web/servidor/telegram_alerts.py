"""Mensajes de Telegram de AguaAlerta (alertas, resumen diario y avisos del bot), en español e inglés.

Arma los textos con las cifras de `predicciones.json` y habla con la API del bot. No guarda personas ni envía por sí
mismo: las suscripciones están en `src/newsletter.py` y el envío en `src/telegram_newsletter.py`.

Cada alerta solo se arma si los datos la respaldan; si no, se rechaza con un motivo (`AlertNotSupported`). Son avisos
EXPERIMENTALES de una estimación regional: no reemplazan los avisos del IMN, el AyA ni de la ASADA, y los textos lo dicen.

Reglas de Telegram que condicionan el envío:
  * Un bot no puede escribirle primero a una persona ni buscarla por @usuario: cada persona debe abrir el bot y enviar /start.
  * El token del bot es secreto: va en la variable de entorno TELEGRAM_BOT_TOKEN o en el archivo `.env` (no se versiona).

Una «persona suscrita» (`subscriber`) es un dict con `asada`, `canton`, `province`, `region` (CR, CR_PN o CR_CAR) y, si se
quiere, `lang` («es» o «en»).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

import requests

ROOT = Path(__file__).resolve().parents[1]
DOTENV = ROOT / ".env"

LANGS = ("es", "en")
MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}
CATEGORY_EN = {"débil": "weak", "moderado": "moderate", "fuerte": "strong", "muy fuerte": "very strong"}
ALERT_KINDS = ("heat", "rain", "nino")
# Umbrales con los que un aviso se considera respaldado por los datos.
HEAT_MIN_ANOMALY = 0.5      # °C sobre el promedio 1991-2020 del mes
RAIN_MIN_SHARE = 0.7        # fracción de años análogos con al menos 100 mm en el mes
NINO_MIN_DEFICIT = -20.0    # % de lluvia frente a lo normal en los años análogos


class AlertNotSupported(ValueError):
    """Los datos no respaldan este aviso: no se envía."""


class TelegramError(RuntimeError):
    """Falla de la API de Telegram. Nunca incluye el token."""


def tr(lang: str, es: str, en: str) -> str:
    return en if lang == "en" else es


def disclaimer(lang: str) -> str:
    return tr(lang,
              "Es una estimación regional experimental, sin validar con estaciones locales. No es un aviso oficial: seguí los avisos del IMN, el AyA y tu ASADA.",
              "This is an experimental regional estimate, not validated against local stations. It is not an official notice: follow the notices from the IMN, AyA and your ASADA.")


# --- Formato (es: coma decimal; en: punto decimal) ---

def num(value: float, digits: int = 1, lang: str = "es") -> str:
    text = f"{value:,.{digits}f}"
    if lang == "en":
        return text
    return text.replace(",", " ").replace(".", ",")


def month_text(label: str, lang: str = "es") -> str:
    year, month = label.split("-")
    name = MONTHS[lang][int(month) - 1]
    return f"{name} {year}" if lang == "en" else f"{name} de {year}"


def month_short(label: str, lang: str = "es") -> str:
    year, month = label.split("-")
    return f"{MONTHS[lang][int(month) - 1]} {year}"


def month_name(label: str, lang: str = "es") -> str:
    return MONTHS[lang][int(label[5:]) - 1]


def date_text(day: date, lang: str = "es") -> str:
    name = MONTHS[lang][day.month - 1]
    return f"{name} {day.day}, {day.year}" if lang == "en" else f"{day.day} de {name} de {day.year}"


# --- Datos ---

def first_row(payload: dict, variable: str, region: str) -> dict:
    return payload["variables"][variable]["regions"][region]["rows"][0]


def place(subscriber: dict) -> str:
    """«Liberia, Guanacaste»; si cantón y provincia se llaman igual, solo «Limón»."""
    canton, province = subscriber["canton"], subscriber["province"]
    return canton if canton == province else f"{canton}, {province}"


def zone_name(region: str, lang: str = "es") -> str:
    return {"CR_PN": tr(lang, "Pacífico Norte", "North Pacific"), "CR_CAR": tr(lang, "Caribe", "Caribbean")}.get(region, tr(lang, "todo el país", "whole country"))


def area(region: str, lang: str = "es") -> str:
    """Cómo se nombra la zona dentro de una frase."""
    if region == "CR":
        return tr(lang, "el promedio del país", "the national average")
    return tr(lang, f"el sector {zone_name(region, lang)}", f"the {zone_name(region, lang)} sector")


def where_line(subscriber: dict, lang: str) -> str:
    zone = zone_name(subscriber["region"], lang)
    zone_text = zone if subscriber["region"] == "CR" else tr(lang, f"sector {zone}", f"{zone} sector")
    asada = f"{subscriber['asada']} · " if subscriber.get("asada") else ""
    return f"📍 {asada}{place(subscriber)} ({zone_text})"


# --- Alertas ---

@dataclass
class Alert:
    kind: str
    icon: str
    title: str
    lines: list[str]     # cuerpo completo del aviso
    short: str           # una línea, para el resumen diario
    tip: str             # qué hacer


def _heat(payload: dict, sub: dict, lang: str) -> Alert:
    region = sub["region"]
    rows = payload["variables"]["T2M"]["regions"][region]["rows"]
    row = rows[0]
    if row["estimate"] is None:
        raise AlertNotSupported(f"{region}: sin pronóstico de temperatura para {row['target_month']}.")
    ref = row["reference"]
    anomaly = row["estimate"] - ref["mean"]
    if anomaly < HEAT_MIN_ANOMALY:
        raise AlertNotSupported(f"{region}: la temperatura estimada solo supera lo normal en {num(anomaly)} °C (mínimo {HEAT_MIN_ANOMALY}).")
    diff = num(round(row["estimate"], 1) - round(ref["mean"], 1), 1, lang)
    above = row["estimate"] > ref["p90"]
    body = tr(lang,
              f"Para {month_text(row['target_month'], lang)} se estima una temperatura media de {num(row['estimate'], 1, lang)} °C en {area(region, lang)} "
              f"(banda de 90 %: {num(row['lower90'], 1, lang)} a {num(row['upper90'], 1, lang)} °C). Lo normal en ese mes (1991–2020) es {num(ref['mean'], 1, lang)} °C: "
              f"unos {diff} °C más caliente" + (", por encima del 90 % de los años de referencia." if above else "."),
              f"For {month_text(row['target_month'], lang)} an average temperature of {num(row['estimate'], 1, lang)} °C is estimated for {area(region, lang)} "
              f"(90 % band: {num(row['lower90'], 1, lang)} to {num(row['upper90'], 1, lang)} °C). The normal for that month (1991–2020) is {num(ref['mean'], 1, lang)} °C: "
              f"about {diff} °C warmer" + (", above 90 % of the reference years." if above else "."))
    lines = [body]
    second = rows[1] if len(rows) > 1 else None
    if second and second["estimate"] is not None:
        name = month_short(second["target_month"], lang)
        lines.append(tr(lang, f"{name.capitalize()}: {num(second['estimate'], 1, lang)} °C (normal {num(second['reference']['mean'], 1, lang)} °C).",
                        f"{name}: {num(second['estimate'], 1, lang)} °C (normal {num(second['reference']['mean'], 1, lang)} °C)."))
    tip = tr(lang, "hidratate seguido, evitá el sol de 10 a. m. a 2 p. m. y cuidá a niños y personas mayores.",
             "drink water often, avoid the sun from 10 a.m. to 2 p.m. and look after children and older people.")
    short = tr(lang, f"🌡️ Calor: en {month_text(row['target_month'], lang)} se estiman {num(row['estimate'], 1, lang)} °C, unos {diff} °C más que lo normal.",
               f"🌡️ Heat: {month_text(row['target_month'], lang)} is estimated at {num(row['estimate'], 1, lang)} °C, about {diff} °C above normal.")
    return Alert("heat", "🌡️", tr(lang, "Aviso experimental de calor", "Experimental heat alert"), lines, short, tip)


def _rain(payload: dict, sub: dict, lang: str) -> Alert:
    region = sub["region"]
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
    month = month_text(row["target_month"], lang)
    lines = [tr(lang,
                f"Alta probabilidad de lluvia en {month}: es uno de los meses más lluviosos de {area(region, lang)} "
                f"(lo normal son unos {num(ref['mean'], 0, lang)} mm y en 9 de cada 10 años llovió más de {num(ref['p10'], 0, lang)} mm). "
                f"En {rainy} de {n} años con un Niño como el actual llovió al menos 100 mm.",
                f"High chance of rain in {month}: it is one of the rainiest months in {area(region, lang)} "
                f"(normal is about {num(ref['mean'], 0, lang)} mm and in 9 out of 10 years it rained more than {num(ref['p10'], 0, lang)} mm). "
                f"In {rainy} of {n} years with an El Niño like the current one, at least 100 mm fell.")]
    if drier:
        lines += ["", tr(lang,
                         f"Ojo: en esos años llovió cerca de {num(abs(analog['anomaly_pct']), 0, lang)} % menos que lo normal (unos {num(analog['mean_mm'], 0, lang)} mm). "
                         "Es más probable un mes con menos lluvia de la habitual que con más.",
                         f"Careful: in those years it rained about {num(abs(analog['anomaly_pct']), 0, lang)} % less than normal (about {num(analog['mean_mm'], 0, lang)} mm). "
                         "A month with less rain than usual is more likely than one with more.")]
    lines += ["", tr(lang, "No hay un pronóstico de lluvia validado: esto combina la lluvia histórica del mes con lo que pasó en años parecidos.",
                      "There is no validated rain forecast: this combines the month's historical rainfall with what happened in similar years.")]
    tip = tr(lang, "tené a mano lo necesario para días de lluvia y no cruces ríos crecidos.", "keep what you need for rainy days at hand and do not cross swollen rivers.")
    short = tr(lang, f"🌧️ Lluvia: alta probabilidad de lluvia en {month} (en {rainy} de {n} años parecidos llovió 100 mm o más).",
               f"🌧️ Rain: high chance of rain in {month} (in {rainy} of {n} similar years at least 100 mm fell).")
    return Alert("rain", "🌧️", tr(lang, "Aviso de lluvia", "Rain alert"), lines, short, tip)


def _nino(payload: dict, sub: dict, lang: str) -> Alert:
    enso = payload["enso"]
    if enso["status"] != "active":
        raise AlertNotSupported("No hay un episodio de El Niño en curso en los datos de RONI.")
    region = sub["region"]
    months = payload["rain_analog"].get(region, {}).get("months", [])
    deficits = [m for m in months[:2] if m["anomaly_pct"] <= NINO_MIN_DEFICIT]
    if not deficits:
        raise AlertNotSupported(f"{region}: en los años análogos la lluvia no bajó {abs(NINO_MIN_DEFICIT):g} % ni más en los primeros meses.")
    category = tr(lang, enso["category"], CATEGORY_EN.get(enso["category"], enso["category"]))
    lines = [tr(lang,
                f"El Niño está en curso desde {month_text(enso['start'], lang)} y ya es {category} (RONI de {num(enso['latest']['value'], 1, lang)} en {month_short(enso['latest']['month'], lang)}).",
                f"El Niño has been under way since {month_text(enso['start'], lang)} and is now {category} (RONI of {num(enso['latest']['value'], 1, lang)} in {month_short(enso['latest']['month'], lang)}).")]
    analog = enso.get("analog")
    if analog:
        window = analog["end_window"]
        lines.append(tr(lang,
                        f"Según episodios fuertes anteriores, podría seguir hasta entre {month_short(window['earliest'], lang)} y {month_short(window['latest'], lang)} "
                        f"(lo más típico: {month_short(window['typical'], lang)}).",
                        f"According to earlier strong episodes, it could last until between {month_short(window['earliest'], lang)} and {month_short(window['latest'], lang)} "
                        f"(most typical: {month_short(window['typical'], lang)})."))
    drops = tr(lang, " y ", " and ").join(
        tr(lang, f"cerca de {num(abs(m['anomaly_pct']), 0, lang)} % menos en {month_name(m['month'], lang)}",
           f"about {num(abs(m['anomaly_pct']), 0, lang)} % less in {month_name(m['month'], lang)}") for m in deficits)
    lines += ["", tr(lang, f"En años parecidos, en {area(region, lang)} llovió {drops} de lo normal.",
                      f"In similar years, in {area(region, lang)} it rained {drops} than normal."),
              tr(lang, "Con menos lluvia bajan los caudales: ahorrá agua, revisá fugas y seguí los avisos de tu ASADA o del AyA.",
                 "With less rain, flows drop: save water, check for leaks and follow the notices from your ASADA or the AyA.")]
    tip = tr(lang, "ahorrá agua, revisá fugas y seguí los avisos de tu ASADA o del AyA.", "save water, check for leaks and follow the notices from your ASADA or the AyA.")
    short = tr(lang, f"⚠️ El Niño: en curso desde {month_text(enso['start'], lang)}; en años parecidos llovió {drops} de lo normal.",
               f"⚠️ El Niño: under way since {month_text(enso['start'], lang)}; in similar years it rained {drops} than normal.")
    return Alert("nino", "⚠️", tr(lang, "Aviso de El Niño", "El Niño alert"), lines, short, tip)


BUILDERS: dict[str, Callable[[dict, dict, str], Alert]] = {"heat": _heat, "rain": _rain, "nino": _nino}


def render_alert(alert: Alert, sub: dict, lang: str) -> str:
    """Texto completo de un aviso: título, lugar, cuerpo, qué hacer y aclaración."""
    lines = [f"{alert.icon} AguaAlerta · {alert.title}", where_line(sub, lang), "", *alert.lines]
    if alert.kind != "nino":  # el de El Niño ya termina con su recomendación
        lines += ["", tr(lang, "Qué podés hacer: ", "What you can do: ") + alert.tip]
    lines += ["", disclaimer(lang)]
    return "\n".join(lines)


def supported_alerts(payload: dict, sub: dict, lang: str = "es") -> list[Alert]:
    """Los avisos que los datos respaldan para esta persona (puede ser ninguno)."""
    found = []
    for kind in ALERT_KINDS:
        try:
            found.append(BUILDERS[kind](payload, sub, lang))
        except AlertNotSupported:
            continue
    return found


def heat_alert(payload: dict, sub: dict, lang: str = "es") -> str:
    return render_alert(_heat(payload, sub, lang), sub, lang)


def rain_alert(payload: dict, sub: dict, lang: str = "es") -> str:
    return render_alert(_rain(payload, sub, lang), sub, lang)


def nino_alert(payload: dict, sub: dict, lang: str = "es") -> str:
    return render_alert(_nino(payload, sub, lang), sub, lang)


# --- Resumen diario ---

def data_lines(payload: dict, sub: dict, lang: str) -> list[str]:
    """Las cifras del día, haya o no riesgo: El Niño, calor y lluvia de la zona."""
    region, lines = sub["region"], []
    enso = payload["enso"]
    if enso["status"] == "active" and enso.get("start"):
        category = tr(lang, enso["category"], CATEGORY_EN.get(enso["category"], enso["category"]))
        lines.append(tr(lang, f"🌊 El Niño: en curso desde {month_text(enso['start'], lang)} ({category}).",
                        f"🌊 El Niño: under way since {month_text(enso['start'], lang)} ({category})."))
    else:
        lines.append(tr(lang, "🌊 El Niño: ahora no hay un episodio en curso.", "🌊 El Niño: there is no episode under way right now."))
    row = next((r for r in payload["variables"]["T2M"]["regions"][region]["rows"] if r["estimate"] is not None), None)
    if row:
        delta = round(row["estimate"], 1) - round(row["reference"]["mean"], 1)
        sign = "+" if delta >= 0 else "−"
        lines.append(tr(lang, f"🌡️ Calor ({month_short(row['target_month'], lang)}): {num(row['estimate'], 1, lang)} °C estimados, {sign}{num(abs(delta), 1, lang)} °C frente a lo normal.",
                        f"🌡️ Heat ({month_short(row['target_month'], lang)}): {num(row['estimate'], 1, lang)} °C estimated, {sign}{num(abs(delta), 1, lang)} °C versus normal."))
    rain_row = first_row(payload, "PRECTOTCORR", region)
    analog = next((m for m in payload["rain_analog"].get(region, {}).get("months", []) if m["month"] == rain_row["target_month"]), None)
    if analog:
        pct = analog["anomaly_pct"]
        less = tr(lang, "menos", "less") if pct < 0 else tr(lang, "más", "more")
        lines.append(tr(lang, f"🌧️ Lluvia ({month_short(analog['month'], lang)}): en años parecidos llovió cerca de {num(abs(pct), 0, lang)} % {less} que lo normal (no es un pronóstico).",
                        f"🌧️ Rain ({month_short(analog['month'], lang)}): in similar years it rained about {num(abs(pct), 0, lang)} % {less} than normal (not a forecast)."))
    return lines


def daily_summary(payload: dict, sub: dict, lang: str = "es", today: date | None = None) -> tuple[str, bool]:
    """Resumen diario con sugerencias. Devuelve (texto, hay_riesgos). Sin riesgos dice que no hubo cambios significativos."""
    today = today or date.today()
    alerts = supported_alerts(payload, sub, lang)
    lines = [tr(lang, f"📰 AguaAlerta · Resumen diario ({date_text(today, lang)})", f"📰 AguaAlerta · Daily summary ({date_text(today, lang)})"),
             where_line(sub, lang), "", *data_lines(payload, sub, lang), ""]
    if alerts:
        lines += [tr(lang, "Los datos advierten:", "The data warn of:"), *[alert.short for alert in alerts], "",
                  tr(lang, "Qué podés hacer:", "What you can do:"), *[f"• {alert.tip[0].upper()}{alert.tip[1:]}" for alert in alerts]]
    else:
        lines += [tr(lang, "No hubo cambios significativos: los datos no advierten riesgos de calor, de lluvia ni por El Niño en tu zona.",
                     "No significant changes: the data do not warn of heat, rain or El Niño risks in your area."),
                  tr(lang, "De todos modos, seguí los avisos de tu ASADA y del AyA.", "Even so, follow the notices from your ASADA and the AyA.")]
    lines += ["", disclaimer(lang)]
    return "\n".join(lines), bool(alerts)


# --- Mensajes del bot ---

SUBSCRIPTION_LABEL = {
    "alertas": {"es": "alertas y sugerencias", "en": "alerts and suggestions"},
    "resumen": {"es": "resumen diario", "en": "daily summary"},
}


def welcome_text(kind: str, sub: dict, lang: str = "es") -> str:
    label = SUBSCRIPTION_LABEL[kind][lang]
    return tr(lang,
              f"✅ Listo, quedaste suscrito/a a {label} de AguaAlerta para {sub['asada']} ({place(sub)}).\n\n"
              "Para dejar de recibir mensajes, escribí /stop en este chat.\n\n" + disclaimer(lang),
              f"✅ Done, you are subscribed to AguaAlerta {label} for {sub['asada']} ({place(sub)}).\n\n"
              "To stop receiving messages, send /stop in this chat.\n\n" + disclaimer(lang))


def test_intro_text(kind: str, lang: str = "es") -> str:
    """Encabezado del mensaje de prueba que se envía solo al activarse la suscripción."""
    label = SUBSCRIPTION_LABEL[kind][lang]
    return tr(lang,
              f"🧪 Mensaje de prueba: así te va a llegar tu {label}. Esto es lo que dicen los datos hoy:",
              f"🧪 Test message: this is how your {label} will reach you. This is what the data say today:")


def no_alerts_now_text(lang: str = "es") -> str:
    return tr(lang,
              "Por ahora los datos no advierten riesgos de calor, de lluvia ni por El Niño en tu zona, así que no hay ninguna alerta que mostrarte. "
              "Cuando haya una, te va a llegar por acá.",
              "Right now the data do not warn of heat, rain or El Niño risks in your area, so there is no alert to show you. "
              "When there is one, it will reach you here.")


def not_subscribed_text() -> str:
    """Respuesta a un /start de alguien que no tiene una suscripción pendiente (no se conoce su idioma: va en los dos)."""
    return ("Hola 👋 Para recibir mensajes de AguaAlerta, primero suscribite desde la página de Predicciones (buscá tu ASADA) y después enviá /start otra vez.\n\n"
            "Hi 👋 To receive AguaAlerta messages, first subscribe on the Predictions page (search for your ASADA) and then send /start again.")


def resend_start_text(lang: str = "es") -> str:
    """Ya hay una suscripción, pero este /start llegó antes de ella: no prueba nada, hay que enviarlo otra vez."""
    return tr(lang, "Recibimos tu suscripción. Para activarla, enviá /start una vez más (el anterior llegó antes de suscribirte).",
              "We received your subscription. To activate it, send /start once more (the previous one arrived before you subscribed).")


def goodbye_text(lang: str = "es") -> str:
    return tr(lang, "Listo, ya no vas a recibir mensajes de AguaAlerta. Si querés volver, suscribite de nuevo en el sitio.",
              "Done, you will no longer receive AguaAlerta messages. If you want to come back, subscribe again on the site.")


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


def send_message(token: str, chat_id: int, text: str, session: Any = requests) -> None:
    call(token, "sendMessage", {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, session)
