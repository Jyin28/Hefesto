"""Newsletter de Telegram: suscripción a dos Excel, vinculación por /start y envío sin repetir ni filtrar datos."""
import copy
import json
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from fastapi import HTTPException
from openpyxl import load_workbook

from src import newsletter, predictions, telegram_alerts as tg, telegram_newsletter as bot, web_api

LIBERIA = "00007-2014"      # cantón 501 → Pacífico Norte
EL_GUARCO = "00818-2014"    # cantón 308 (Cartago) → su celda NASA cae en el Caribe
ALAJUELA = "05183-2022"     # cantón 201 → sin cálculo propio: promedio del país
TOKEN = "123456:SECRET-TOKEN"
T0 = datetime(2026, 11, 15, 10, 0, tzinfo=newsletter.TZ)
AFTER = int(T0.timestamp()) + 120
BEFORE = int(T0.timestamp()) - 3600


def sub(username="@Persona_1", kind="alertas", asada=LIBERIA, **extra):
    args = dict(consent=True, lang="es", consent_version=newsletter.CONSENT_VERSION, now=T0)
    args.update(extra)
    return newsletter.subscribe(username, kind, asada, **args)


class FakeTelegram:
    """Responde a cada método de la API del bot con la cola que se le indique (o {}) y guarda las llamadas."""

    def __init__(self, **replies):
        self.replies = {name: list(items) for name, items in replies.items()}
        self.calls = []

    def post(self, url, json=None, timeout=None):  # noqa: A002
        method = url.rsplit("/", 1)[1]
        self.calls.append((method, json))
        queue = self.replies.get(method)
        reply = queue.pop(0) if queue else {"ok": True, "result": {}}
        return mock.Mock(json=lambda: reply)

    def sent(self):
        return [payload for method, payload in self.calls if method == "sendMessage"]


def update(update_id, username, text, date=AFTER, chat=42, kind="private"):
    return {"update_id": update_id, "message": {"from": {"username": username}, "chat": {"id": chat, "type": kind}, "text": text, "date": date}}


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name) / "suscripciones"
        self.chats = Path(self._tmp.name) / "chats.json"
        self.state = Path(self._tmp.name) / "sent.json"

    def rows(self, kind):
        return newsletter.read_rows(newsletter.excel_path(kind, self.dir))

    def subscribe(self, *args, **kwargs):
        return sub(*args, data_dir=self.dir, **kwargs)


class SubscribeTests(TempDirCase):
    def test_each_option_goes_to_its_own_excel_with_user_and_asada(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@Otra_persona", "resumen", EL_GUARCO)
        self.assertEqual([r["Usuario de Telegram"] for r in self.rows("alertas")], ["@Persona_1"])
        self.assertEqual([r["Usuario de Telegram"] for r in self.rows("resumen")], ["@Otra_persona"])
        row = self.rows("alertas")[0]
        self.assertEqual((row["ID de la ASADA"], row["Cantón"], row["Provincia"], row["Estado"], row["Idioma"]), (LIBERIA, "Liberia", "Guanacaste", newsletter.PENDING, "es"))
        self.assertTrue(row["ASADA"])
        self.assertIn(newsletter.CONSENT_VERSION, row["Consentimiento"])
        self.assertEqual(newsletter.excel_path("alertas", self.dir).name, "alertas_sugerencias.xlsx")
        self.assertEqual(newsletter.excel_path("resumen", self.dir).name, "resumen_diario.xlsx")

    def test_excel_file_has_headers_and_text_cells(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        sheet = load_workbook(newsletter.excel_path("alertas", self.dir))[newsletter.SHEET]
        self.assertEqual([cell.value for cell in sheet[1]], newsletter.HEADERS)
        self.assertTrue(all(cell.data_type == "s" for cell in sheet[2]))

    def test_region_follows_the_nasa_grid_cell_of_the_canton(self):
        for asada, region in ((LIBERIA, "CR_PN"), (EL_GUARCO, "CR_CAR"), (ALAJUELA, "CR")):
            self.assertEqual(self.subscribe(f"@Usuario_{region}", "alertas", asada)["Región"], region)

    def test_same_person_and_asada_is_not_duplicated(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@persona_1", "alertas", LIBERIA)  # otra vez, sin distinguir mayúsculas
        self.assertEqual(len(self.rows("alertas")), 1)

    def test_changing_option_moves_the_person_to_the_other_excel(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@Persona_1", "resumen", LIBERIA)
        self.assertEqual(self.rows("alertas"), [])
        self.assertEqual(len(self.rows("resumen")), 1)

    def test_same_person_can_follow_two_different_asadas(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@Persona_1", "alertas", EL_GUARCO)
        self.assertEqual(len(self.rows("alertas")), 2)

    def test_username_must_start_with_at_and_be_valid(self):
        for bad in ("Persona_1", "@abc", "@1persona", "@con espacio", "@" + "a" * 33, "=cmd|x", "@per-sona", "", "  "):
            with self.assertRaises(newsletter.SubscriptionError, msg=bad) as caught:
                self.subscribe(bad, "alertas", LIBERIA)
            self.assertEqual(caught.exception.code, "username")
        self.assertEqual(self.rows("alertas"), [])

    def test_exactly_one_option_is_required(self):
        for bad in ("", "ambas", "alertas,resumen", None):
            with self.assertRaises(newsletter.SubscriptionError) as caught:
                self.subscribe("@Persona_1", bad, LIBERIA)
            self.assertEqual(caught.exception.code, "kind")

    def test_consent_is_required_and_must_match_the_current_text(self):
        for kwargs, code in (({"consent": False}, "consent"), ({"consent": None}, "consent"), ({"consent_version": "viejo"}, "consent_version")):
            with self.assertRaises(newsletter.SubscriptionError) as caught:
                self.subscribe("@Persona_1", "alertas", LIBERIA, **kwargs)
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.rows("alertas"), [])

    def test_unknown_asada_is_rejected(self):
        with self.assertRaises(newsletter.SubscriptionError) as caught:
            self.subscribe("@Persona_1", "alertas", "99999-9999")
        self.assertEqual(caught.exception.code, "asada")

    def test_error_messages_follow_the_language(self):
        with self.assertRaises(newsletter.SubscriptionError) as caught:
            self.subscribe("Persona_1", "alertas", LIBERIA, lang="en")
        self.assertIn("starting with @", caught.exception.message)
        with self.assertRaises(newsletter.SubscriptionError) as caught:
            self.subscribe("Persona_1", "alertas", LIBERIA, lang="fr")
        self.assertIn("empezando con @", caught.exception.message)

    def test_a_locked_excel_leaves_the_previous_file_intact(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        with mock.patch("src.newsletter.os.replace", side_effect=PermissionError("abierto en Excel")):
            with self.assertRaises(newsletter.SubscriptionError) as caught:
                self.subscribe("@Otra_persona", "alertas", LIBERIA)
        self.assertEqual(caught.exception.code, "storage")
        self.assertEqual([r["Usuario de Telegram"] for r in self.rows("alertas")], ["@Persona_1"])
        self.assertEqual([name for name in os.listdir(self.dir) if name.endswith(".xlsx") and "tmp" in name.lower()], [])

    def test_state_changes_by_person_and_asada(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@Persona_1", "alertas", EL_GUARCO)
        changed = newsletter.update_state([("alertas", "@persona_1", LIBERIA, newsletter.ACTIVE)], self.dir)
        self.assertEqual(changed, 1)
        self.assertEqual({r["ID de la ASADA"]: r["Estado"] for r in self.rows("alertas")}, {LIBERIA: newsletter.ACTIVE, EL_GUARCO: newsletter.PENDING})


class ApiTests(TempDirCase):
    def request(self, **overrides):
        body = dict(username="@Persona_1", kind="alertas", asada_id=LIBERIA, consent=True, consent_version=newsletter.CONSENT_VERSION, lang="es")
        body.update(overrides)
        return web_api.SubscriptionRequest(**body)

    def call(self, body, host="1.2.3.4"):
        with mock.patch.object(newsletter, "DATA_DIR", self.dir), mock.patch.object(web_api, "load_token", return_value=None), \
                mock.patch.object(web_api, "_subscription_limiter", newsletter.RateLimiter()):
            return web_api.subscribe(body, mock.Mock(client=mock.Mock(host=host)))

    def test_success_returns_state_and_no_rows(self):
        answer = self.call(self.request())
        self.assertEqual(answer, {"ok": True, "kind": "alertas", "state": newsletter.PENDING, "bot": None})
        self.assertEqual(len(self.rows("alertas")), 1)

    def test_validation_errors_are_422_with_code_and_message(self):
        with self.assertRaises(HTTPException) as caught:
            self.call(self.request(username="sin_arroba", lang="en"))
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(caught.exception.detail["code"], "username")
        self.assertIn("starting with @", caught.exception.detail["message"])

    def test_consent_must_be_a_real_boolean(self):
        with self.assertRaises(Exception):
            self.request(consent="true")

    def test_rate_limit(self):
        limiter = newsletter.RateLimiter(limit=2)
        with mock.patch.object(newsletter, "DATA_DIR", self.dir), mock.patch.object(web_api, "load_token", return_value=None), \
                mock.patch.object(web_api, "_subscription_limiter", limiter):
            request = mock.Mock(client=mock.Mock(host="9.9.9.9"))
            web_api.subscribe(self.request(), request)
            web_api.subscribe(self.request(), request)
            with self.assertRaises(HTTPException) as caught:
                web_api.subscribe(self.request(), request)
        self.assertEqual(caught.exception.status_code, 429)

    def test_rate_limiter_window(self):
        now = [0.0]
        limiter = newsletter.RateLimiter(limit=1, window=10, clock=lambda: now[0])
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        self.assertTrue(limiter.allow("b"))
        now[0] = 11
        self.assertTrue(limiter.allow("a"))


class BotInfoTests(unittest.TestCase):
    def setUp(self):
        newsletter._BOT_CACHE.clear()

    def test_without_token_there_is_no_bot(self):
        self.assertIsNone(newsletter.bot_info(None))
        self.assertIsNone(newsletter.bot_info(""))

    def test_username_comes_from_getme(self):
        info = newsletter.bot_info(TOKEN, FakeTelegram(getMe=[{"ok": True, "result": {"username": "NexoAzulBot"}}]), environ={})
        self.assertEqual((info.username, info.link), ("NexoAzulBot", "https://t.me/NexoAzulBot"))

    def test_env_username_avoids_the_network_call(self):
        fake = FakeTelegram()
        info = newsletter.bot_info(TOKEN, fake, environ={"TELEGRAM_BOT_USERNAME": "@MiBot"})
        self.assertEqual(info.username, "MiBot")
        self.assertEqual(fake.calls, [])

    def test_telegram_failure_means_no_bot_and_no_token_leak(self):
        info = newsletter.bot_info(TOKEN, FakeTelegram(getMe=[{"ok": False, "description": "Unauthorized", "error_code": 401}]), environ={})
        self.assertIsNone(info)


class DiscoverTests(TempDirCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = predictions.build()

    def run_discover(self, updates, fake=None):
        fake = fake or FakeTelegram(getUpdates=[{"ok": True, "result": updates}])
        summary = bot.discover(TOKEN, self.dir, self.chats, self.state, fake, payload=self.payload, today=date(2026, 11, 15))
        return summary, fake

    def test_start_after_subscribing_activates_and_welcomes(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        summary, fake = self.run_discover([update(10, "PERSONA_1", "/start")])
        self.assertEqual(summary["activated"], 1)
        self.assertEqual(self.rows("alertas")[0]["Estado"], newsletter.ACTIVE)
        self.assertEqual(json.loads(self.chats.read_text()), {"persona_1": 42})
        texts = [message["text"] for message in fake.sent()]
        self.assertIn("alertas y sugerencias", texts[0])          # bienvenida
        self.assertIn("Mensaje de prueba", texts[1])              # mensaje de prueba automático
        self.assertTrue(any("Aviso experimental de calor" in text for text in texts[2:]))  # y los avisos vigentes
        self.assertEqual(json.loads(self.state.read_text())["update_offset"], 11)

    def test_test_message_for_the_daily_summary_is_todays_summary(self):
        self.subscribe("@Persona_1", "resumen", LIBERIA)
        _, fake = self.run_discover([update(10, "persona_1", "/start")])
        texts = [message["text"] for message in fake.sent()]
        self.assertEqual(len(texts), 2)
        self.assertIn("Mensaje de prueba", texts[1])
        self.assertIn("Resumen diario (15 de noviembre de 2026)", texts[1])

    def test_the_test_message_is_not_repeated_by_the_normal_send(self):
        self.subscribe("@Persona_1", "resumen", LIBERIA)
        self.subscribe("@Persona_2", "alertas", LIBERIA)
        self.run_discover([update(10, "persona_1", "/start"), update(11, "persona_2", "/start", chat=43)])
        fake = FakeTelegram()
        results = bot.send(TOKEN, self.payload, self.dir, self.chats, self.state, fake, date(2026, 11, 15))
        self.assertEqual({r["status"] for r in results}, {"ya enviado"})
        self.assertEqual(fake.sent(), [])

    def test_test_message_says_so_when_there_are_no_alerts_now(self):
        calm = copy.deepcopy(self.payload)
        calm["enso"]["status"] = "none"
        for region in calm["variables"]["T2M"]["regions"].values():
            for row in region["rows"]:
                if row["estimate"] is not None:
                    row["estimate"] = row["reference"]["mean"]
        for region in calm["rain_analog"].values():
            for month in region["months"]:
                month["share_above_100mm"] = 0.1
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        fake = FakeTelegram(getUpdates=[{"ok": True, "result": [update(10, "persona_1", "/start")]}])
        bot.discover(TOKEN, self.dir, self.chats, self.state, fake, payload=calm, today=date(2026, 11, 15))
        texts = [message["text"] for message in fake.sent()]
        self.assertEqual(len(texts), 2)
        self.assertIn("no advierten riesgos", texts[1])

    def test_a_start_from_someone_not_subscribed_gets_instructions(self):
        _, fake = self.run_discover([update(10, "desconocido", "/start", chat=99)])
        self.assertEqual(len(fake.sent()), 1)
        self.assertEqual(fake.sent()[0]["chat_id"], 99)
        self.assertIn("suscribite", fake.sent()[0]["text"])

    def test_welcome_follows_the_subscription_language(self):
        self.subscribe("@Persona_1", "resumen", LIBERIA, lang="en")
        _, fake = self.run_discover([update(10, "persona_1", "/start")])
        self.assertIn("daily summary", fake.sent()[0]["text"])
        self.assertIn("Test message", fake.sent()[1]["text"])

    def test_start_before_subscribing_does_not_prove_ownership(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        summary, fake = self.run_discover([update(10, "persona_1", "/start", date=BEFORE)])
        self.assertEqual(summary["activated"], 0)
        self.assertEqual(self.rows("alertas")[0]["Estado"], newsletter.PENDING)
        self.assertEqual(len(fake.sent()), 1)
        self.assertIn("una vez más", fake.sent()[0]["text"])  # se le pide repetirlo; no se activa ni se le dice «suscribite»

    def test_someone_elses_start_never_activates_a_username(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        summary, fake = self.run_discover([update(10, "otra_cuenta", "/start")])
        self.assertEqual(summary["activated"], 0)
        self.assertEqual(self.rows("alertas")[0]["Estado"], newsletter.PENDING)
        self.assertNotIn("Mensaje de prueba", " ".join(message["text"] for message in fake.sent()))

    def test_groups_and_plain_text_are_ignored(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        summary, _ = self.run_discover([update(10, "persona_1", "/start", kind="group"), update(11, "persona_1", "hola")])
        self.assertEqual(summary, {"activated": 0, "stopped": 0, "ignored": 2})

    def test_stop_unsubscribes_every_subscription_of_that_person(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@Persona_1", "resumen", EL_GUARCO)
        self.run_discover([update(10, "persona_1", "/start")])
        summary, fake = self.run_discover([update(11, "persona_1", "/stop")])
        self.assertEqual(summary["stopped"], 2)
        self.assertEqual([r["Estado"] for r in self.rows("alertas") + self.rows("resumen")], [newsletter.STOPPED] * 2)
        self.assertIn("ya no vas a recibir", fake.sent()[0]["text"])

    def test_next_read_continues_after_the_last_update(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.run_discover([update(10, "persona_1", "/start")])
        _, fake = self.run_discover([], FakeTelegram(getUpdates=[{"ok": True, "result": []}]))
        self.assertEqual(fake.calls[0][1]["offset"], 11)


class SendTests(TempDirCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = predictions.build()

    def calm(self):
        payload = copy.deepcopy(self.payload)
        payload["enso"]["status"] = "none"
        for region in payload["variables"]["T2M"]["regions"].values():
            for row in region["rows"]:
                if row["estimate"] is not None:
                    row["estimate"] = row["reference"]["mean"]
        for region in payload["rain_analog"].values():
            for month in region["months"]:
                month["share_above_100mm"] = 0.1
        return payload

    def activate(self, username="@Persona_1", kind="alertas", asada=LIBERIA, chat=42, **kwargs):
        self.subscribe(username, kind, asada, **kwargs)
        newsletter.update_state([(kind, username, asada, newsletter.ACTIVE)], self.dir)
        chats = json.loads(self.chats.read_text()) if self.chats.is_file() else {}
        chats[username.lstrip("@").lower()] = chat
        self.chats.write_text(json.dumps(chats))

    def send(self, payload=None, fake=None, today=date(2026, 11, 15), **kwargs):
        fake = fake or FakeTelegram()
        return bot.send(TOKEN, payload or self.payload, self.dir, self.chats, self.state, fake, today, **kwargs), fake

    def test_alerts_are_sent_only_for_the_risks_the_data_back(self):
        self.activate()
        results, fake = self.send()
        self.assertEqual({r["mensaje"] for r in results}, {"heat", "nino"})
        self.assertTrue(all(r["status"] == "enviado" for r in results))
        self.assertEqual(len(fake.sent()), 2)
        self.assertEqual(fake.sent()[0]["chat_id"], 42)

    def test_alerts_with_no_risk_send_nothing(self):
        self.activate()
        results, fake = self.send(self.calm())
        self.assertEqual((results, fake.sent()), ([], []))

    def test_alerts_are_not_repeated_until_the_predictions_change(self):
        self.activate()
        self.send()
        again, fake = self.send(today=date(2026, 11, 16))
        self.assertEqual({r["status"] for r in again}, {"ya enviado"})
        self.assertEqual(fake.sent(), [])
        newer = copy.deepcopy(self.payload)
        newer["data_through"] = "2026-11"
        later, fake = self.send(newer, today=date(2026, 12, 2))
        self.assertEqual({r["status"] for r in later}, {"enviado"})

    def test_daily_summary_goes_once_per_day(self):
        self.activate(kind="resumen")
        first, fake = self.send()
        self.assertEqual([r["status"] for r in first], ["enviado"])
        self.assertIn("Resumen diario", fake.sent()[0]["text"])
        same_day, fake = self.send()
        self.assertEqual(([r["status"] for r in same_day], fake.sent()), (["ya enviado"], []))
        next_day, fake = self.send(today=date(2026, 11, 16))
        self.assertEqual([r["status"] for r in next_day], ["enviado"])

    def test_daily_summary_without_risks_says_no_significant_changes(self):
        self.activate(kind="resumen", lang="en")
        results, fake = self.send(self.calm())
        self.assertEqual(results[0]["mensaje"], "sin cambios")
        self.assertIn("No significant changes", fake.sent()[0]["text"])

    def test_pending_and_stopped_subscribers_get_nothing(self):
        self.subscribe("@Pendiente_1", "alertas", LIBERIA)
        self.activate("@Baja_1", "alertas", LIBERIA, chat=7)
        newsletter.update_state([("alertas", "@Baja_1", LIBERIA, newsletter.STOPPED)], self.dir)
        results, fake = self.send()
        self.assertEqual((results, fake.sent()), ([], []))

    def test_active_without_chat_id_is_reported_pending(self):
        self.activate()
        self.chats.write_text("{}")
        results, fake = self.send()
        self.assertEqual({r["status"] for r in results}, {"pendiente"})
        self.assertEqual(fake.sent(), [])

    def test_dry_run_sends_and_records_nothing(self):
        self.activate()
        results, fake = self.send(dry_run=True)
        self.assertEqual({r["status"] for r in results}, {"listo"})
        self.assertEqual(fake.sent(), [])
        self.assertFalse(self.state.exists())

    def test_blocked_bot_marks_the_person_as_unsubscribed_and_hides_the_token(self):
        self.activate()
        fake = FakeTelegram(sendMessage=[{"ok": False, "description": "Forbidden: bot was blocked by the user", "error_code": 403}] * 2)
        results, _ = self.send(fake=fake)
        self.assertEqual({r["status"] for r in results}, {"falló"})
        self.assertNotIn(TOKEN, json.dumps(results))
        self.assertEqual(self.rows("alertas")[0]["Estado"], newsletter.STOPPED)

    def test_results_never_include_message_text_or_chat_ids(self):
        self.activate()
        results, _ = self.send()
        self.assertNotIn("text", json.dumps(results))
        self.assertTrue(all("chat_id" not in r for r in results))

    def test_messages_use_the_zone_of_the_asada(self):
        self.activate("@Caribe_1", "alertas", EL_GUARCO, chat=5)
        _, fake = self.send()
        self.assertTrue(any("Caribe" in message["text"] for message in fake.sent()))


class NoSecretsInRepoTests(unittest.TestCase):
    def test_personal_data_locations_are_ignored_by_git(self):
        ignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
        for entry in ("data/suscripciones/", "data/telegram_chats.json", "data/telegram_sent.json", ".env"):
            self.assertIn(entry, ignore)

    def test_test_recipients_are_gone(self):
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / "config" / "telegram_recipients.json").exists())
        self.assertFalse((root / "web" / "public" / "data" / "alertas.json").exists())


if __name__ == "__main__":
    unittest.main()
