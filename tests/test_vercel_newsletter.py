"""Newsletter de Telegram en Vercel (`web/api` + `web/servidor`): suscripción, webhook del bot y envío diario sobre un almacén falso."""
import copy
import json
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
sys.path.insert(0, str(WEB))

import requests  # noqa: E402

from servidor import bot, rutas, store as store_module, suscripciones as subs, telegram_alerts as tg  # noqa: E402

LIBERIA = "00007-2014"      # cantón 501 → Pacífico Norte
EL_GUARCO = "00818-2014"    # cantón 308 (Cartago) → su celda NASA cae en el Caribe
ALAJUELA = "05183-2022"     # cantón 201 → sin cálculo propio: promedio del país
TOKEN = "123456:SECRET-TOKEN"
T0 = datetime(2026, 11, 15, 10, 0, tzinfo=subs.TZ)
AFTER = int(T0.timestamp()) + 120
BEFORE = int(T0.timestamp()) - 3600
TODAY = date(2026, 11, 15)
ENV = {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_BOT_USERNAME": "AguaAlertaBot", "TELEGRAM_WEBHOOK_SECRET": "hook-secret", "CRON_SECRET": "cron-secret"}


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


def update(username, text, date=AFTER, chat=42, kind="private"):
    return {"update_id": 1, "message": {"from": {"username": username}, "chat": {"id": chat, "type": kind}, "text": text, "date": date}}


def body(**changes):
    data = {"username": "@Persona_1", "kind": "alertas", "asada_id": LIBERIA, "consent": True, "consent_version": subs.CONSENT_VERSION, "lang": "es"}
    data.update(changes)
    return json.dumps(data).encode()


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.store = store_module.FakeStore()
        subs._BOT_CACHE.clear()

    def subscribe(self, username="@Persona_1", kind="alertas", asada=LIBERIA, **extra):
        args = dict(consent=True, lang="es", consent_version=subs.CONSENT_VERSION, now=T0)
        args.update(extra)
        return subs.subscribe(self.store, username, kind, asada, **args)

    def rows(self, kind):
        return [row for row in subs.all_subscribers(self.store) if row["kind"] == kind]


class SubscribeTests(StoreCase):
    def test_each_option_is_saved_with_user_and_asada(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@Otra_persona", "resumen", EL_GUARCO)
        self.assertEqual([r["Usuario de Telegram"] for r in self.rows("alertas")], ["@Persona_1"])
        self.assertEqual([r["Usuario de Telegram"] for r in self.rows("resumen")], ["@Otra_persona"])
        row = self.rows("alertas")[0]
        self.assertEqual((row["ID de la ASADA"], row["Cantón"], row["Provincia"], row["Estado"], row["Idioma"]), (LIBERIA, "Liberia", "Guanacaste", subs.PENDING, "es"))
        self.assertTrue(row["ASADA"])
        self.assertIn(subs.CONSENT_VERSION, row["Consentimiento"])
        self.assertEqual(sorted(subs.HEADERS), sorted(k for k in row if k != "kind"))

    def test_region_follows_the_nasa_grid_cell_of_the_canton(self):
        for asada, region in ((LIBERIA, "CR_PN"), (EL_GUARCO, "CR_CAR"), (ALAJUELA, "CR")):
            self.assertEqual(self.subscribe(f"@Usuario_{region}", "alertas", asada)["Región"], region)

    def test_same_person_and_asada_is_not_duplicated(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@persona_1", "alertas", LIBERIA)  # otra vez, sin distinguir mayúsculas
        self.assertEqual(len(self.rows("alertas")), 1)

    def test_changing_option_moves_the_person_to_the_other_option(self):
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
            with self.assertRaises(subs.SubscriptionError, msg=bad) as caught:
                self.subscribe(bad, "alertas", LIBERIA)
            self.assertEqual(caught.exception.code, "username")
        self.assertEqual(subs.all_subscribers(self.store), [])

    def test_option_consent_version_and_asada_are_checked(self):
        for code, extra in (("kind", {"kind": "otra"}), ("consent", {"consent": False}), ("consent", {"consent": "true"}),
                            ("consent_version", {"consent_version": "viejo"}), ("asada", {"asada": "no-existe"})):
            with self.assertRaises(subs.SubscriptionError, msg=code) as caught:
                self.subscribe(**extra)
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(subs.all_subscribers(self.store), [])

    def test_messages_come_in_the_requested_language(self):
        with self.assertRaises(subs.SubscriptionError) as caught:
            self.subscribe("mal", lang="en")
        self.assertIn("Enter your Telegram username", caught.exception.message)

    def test_storage_failure_is_reported_without_details(self):
        broken = mock.Mock(hset=mock.Mock(side_effect=store_module.StoreError("secreto")))
        with self.assertRaises(subs.SubscriptionError) as caught:
            subs.subscribe(broken, "@Persona_1", "alertas", LIBERIA, True, "es", subs.CONSENT_VERSION, now=T0)
        self.assertEqual(caught.exception.code, "storage")
        self.assertNotIn("secreto", caught.exception.message)


class SubscribeRouteTests(StoreCase):
    def call(self, raw=None, ip="1.2.3.4", env=ENV, store=None):
        return rutas.suscribir(raw if raw is not None else body(), ip, store or self.store, session=FakeTelegram(), environ=env)

    def test_saves_and_returns_only_what_the_next_step_needs(self):
        status, result = self.call()
        self.assertEqual(status, 200)
        self.assertEqual(result, {"ok": True, "kind": "alertas", "state": subs.PENDING, "bot": {"username": "AguaAlertaBot", "link": "https://t.me/AguaAlertaBot"}})
        self.assertEqual(len(self.rows("alertas")), 1)

    def test_bot_is_null_while_there_is_no_token(self):
        status, result = self.call(env={})
        self.assertEqual((status, result["bot"]), (200, None))

    def test_validation_errors_are_422_with_code_and_message(self):
        status, result = self.call(body(username="sin-arroba"))
        self.assertEqual((status, result["detail"]["code"]), (422, "username"))
        self.assertTrue(result["detail"]["message"])

    def test_malformed_requests_are_422(self):
        for raw in (b"", b"no es json", b"[]", json.dumps({"username": "@Persona_1"}).encode(), body(consent="si")):
            self.assertEqual(self.call(raw)[0], 422, raw)

    def test_eleventh_attempt_from_the_same_address_is_limited(self):
        self.assertEqual([self.call(ip="9.9.9.9")[0] for _ in range(10)], [200] * 10)
        status, result = self.call(ip="9.9.9.9")
        self.assertEqual((status, result["detail"]["code"]), (429, "rate"))
        self.assertEqual(self.call(ip="8.8.8.8")[0], 200)

    def test_missing_storage_is_503_without_exposing_variables(self):
        status, result = rutas.suscribir(body(), "1.1.1.1", None, session=FakeTelegram(), environ={})
        self.assertEqual((status, result["detail"]["code"]), (503, "storage"))
        self.assertNotIn("KV_REST", json.dumps(result))


class WebhookTests(StoreCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = bot.load_payload()

    def hook(self, message, secret="hook-secret", fake=None, env=ENV):
        fake = fake or FakeTelegram()
        status, result = rutas.webhook(json.dumps(message).encode(), secret, self.store, fake, env, TODAY)
        return status, result, fake

    def test_wrong_missing_or_unconfigured_secret_is_rejected(self):
        self.subscribe()
        for secret, env in ((None, ENV), ("otro", ENV), ("hook-secret", {k: v for k, v in ENV.items() if k != "TELEGRAM_WEBHOOK_SECRET"})):
            status, _, fake = self.hook(update("persona_1", "/start"), secret, env=env)
            self.assertEqual(status, 401)
            self.assertEqual(fake.calls, [])
        self.assertEqual(self.rows("alertas")[0]["Estado"], subs.PENDING)

    def test_start_after_subscribing_activates_and_welcomes(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        status, result, fake = self.hook(update("PERSONA_1", "/start"))
        self.assertEqual((status, result["result"]), (200, "activated"))
        self.assertEqual(self.rows("alertas")[0]["Estado"], subs.ACTIVE)
        self.assertEqual(self.store.hgetall("chats"), {"persona_1": "42"})
        texts = [message["text"] for message in fake.sent()]
        self.assertIn("alertas y sugerencias", texts[0])      # bienvenida
        self.assertIn("Mensaje de prueba", texts[1])          # mensaje de prueba automático
        self.assertTrue(any("Aviso experimental de calor" in text for text in texts[2:]))  # y los avisos vigentes
        self.assertTrue(self.store.hgetall("sent"))           # lo enviado queda anotado

    def test_test_message_for_the_daily_summary_is_todays_summary_and_is_not_repeated(self):
        self.subscribe("@Persona_1", "resumen", LIBERIA)
        _, _, fake = self.hook(update("persona_1", "/start"))
        texts = [message["text"] for message in fake.sent()]
        self.assertEqual(len(texts), 2)
        self.assertIn("Resumen diario (15 de noviembre de 2026)", texts[1])
        status, result = rutas.enviar("Bearer cron-secret", self.store, again := FakeTelegram(), ENV, TODAY)
        self.assertEqual((status, result["enviados"]), (200, 0))
        self.assertEqual(again.sent(), [])

    def test_start_before_subscribing_does_not_activate(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        status, result, fake = self.hook(update("persona_1", "/start", date=BEFORE))
        self.assertEqual(result["result"], "ignored")
        self.assertEqual(self.rows("alertas")[0]["Estado"], subs.PENDING)
        self.assertEqual(self.store.hgetall("chats"), {})
        self.assertEqual(len(fake.sent()), 1)  # se le explica que falta enviar /start otra vez

    def test_start_from_someone_not_subscribed_is_told_so(self):
        _, result, fake = self.hook(update("desconocida", "/start"))
        self.assertEqual(result["result"], "ignored")
        self.assertEqual(len(fake.sent()), 1)

    def test_stop_unsubscribes_every_subscription_of_the_person(self):
        self.subscribe("@Persona_1", "alertas", LIBERIA)
        self.subscribe("@Persona_1", "resumen", EL_GUARCO)
        self.hook(update("persona_1", "/start"))
        _, result, fake = self.hook(update("persona_1", "/stop"))
        self.assertEqual(result["result"], "stopped")
        self.assertEqual({row["Estado"] for row in subs.all_subscribers(self.store)}, {subs.STOPPED})
        self.assertEqual(len(fake.sent()), 1)

    def test_groups_non_commands_and_bad_requests_are_ignored(self):
        self.subscribe()
        for message in (update("persona_1", "/start", kind="group"), update("persona_1", "hola"), update("", "/start"), {"update_id": 1}):
            self.assertEqual(self.hook(message)[1]["result"], "ignored")
        self.assertEqual(rutas.webhook(b"no es json", "hook-secret", self.store, FakeTelegram(), ENV, TODAY)[0], 400)
        self.assertEqual(self.rows("alertas")[0]["Estado"], subs.PENDING)

    def test_an_error_while_processing_still_answers_200_so_telegram_does_not_retry_forever(self):
        self.subscribe()
        with mock.patch.object(bot, "handle_update", side_effect=RuntimeError("boom")):
            status, result, _ = self.hook(update("persona_1", "/start"))
        self.assertEqual((status, result["result"]), (200, "error"))

    def test_without_token_the_webhook_is_unavailable(self):
        env = {k: v for k, v in ENV.items() if k != "TELEGRAM_BOT_TOKEN"}
        self.assertEqual(self.hook(update("persona_1", "/start"), env=env)[0], 503)


class SendTests(StoreCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = bot.load_payload()

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

    def activate(self, username="@Persona_1", kind="alertas", asada=LIBERIA, chat=42):
        self.subscribe(username, kind, asada)
        subs.update_state(self.store, [(kind, username, asada, subs.ACTIVE)])
        self.store.hset("chats", username.lstrip("@").lower(), str(chat))

    def send(self, payload=None, fake=None, **kwargs):
        fake = fake or FakeTelegram()
        return bot.send_daily(self.store, TOKEN, payload or self.payload, TODAY, fake, **kwargs), fake

    def test_alerts_are_sent_only_for_the_risks_the_data_back(self):
        self.activate()
        results, fake = self.send()
        self.assertTrue(results)
        self.assertEqual({item["status"] for item in results}, {"enviado"})
        self.assertEqual(len(fake.sent()), len(results))
        self.assertTrue(all(message["chat_id"] == 42 for message in fake.sent()))

    def test_alerts_are_not_repeated_until_the_predictions_change(self):
        self.activate()
        self.send()
        results, fake = self.send()
        self.assertEqual({item["status"] for item in results}, {"ya enviado"})
        self.assertEqual(fake.sent(), [])
        changed = copy.deepcopy(self.payload)
        changed["data_through"] = "2099-01"
        self.assertEqual({item["status"] for item in self.send(changed)[0]}, {"enviado"})

    def test_nothing_is_sent_when_no_risk_is_backed_by_the_data(self):
        self.activate()
        results, fake = self.send(self.calm())
        self.assertEqual((results, fake.sent()), ([], []))

    def test_daily_summary_is_sent_once_a_day_even_without_risks(self):
        self.activate(kind="resumen")
        results, fake = self.send(self.calm())
        self.assertEqual([item["status"] for item in results], ["enviado"])
        self.assertEqual(self.send(self.calm())[1].sent(), [])
        tomorrow = bot.send_daily(self.store, TOKEN, self.calm(), date(2026, 11, 16), FakeTelegram())
        self.assertEqual([item["status"] for item in tomorrow], ["enviado"])

    def test_only_active_subscriptions_with_a_chat_receive_messages(self):
        self.subscribe("@Pendiente_1", "resumen")                       # sin /start
        self.activate("@Activa_1", "resumen")
        self.subscribe("@Sin_chat_1", "resumen")
        subs.update_state(self.store, [("resumen", "@Sin_chat_1", LIBERIA, subs.ACTIVE)])  # activa pero sin Chat ID
        results, fake = self.send(self.calm())
        self.assertEqual(sorted((item["user"], item["status"]) for item in results), [("@Activa_1", "enviado"), ("@Sin_chat_1", "pendiente")])
        self.assertEqual(len(fake.sent()), 1)

    def test_dry_run_sends_and_records_nothing(self):
        self.activate()
        results, fake = self.send(dry_run=True)
        self.assertEqual((fake.sent(), self.store.hgetall("sent")), ([], {}))
        self.assertEqual({item["status"] for item in results}, {"listo"})

    def test_a_person_who_blocked_the_bot_is_unsubscribed(self):
        self.activate()
        fake = FakeTelegram(sendMessage=[{"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked by the user"}])
        results, _ = self.send(fake=fake)
        self.assertEqual(results[0]["status"], "falló")
        self.assertEqual(self.rows("alertas")[0]["Estado"], subs.STOPPED)

    def test_one_failure_does_not_stop_the_others_and_failed_ones_are_retried(self):
        self.activate("@Persona_1", "resumen")
        self.activate("@Persona_2", "resumen", chat=43)
        fake = FakeTelegram(sendMessage=[{"ok": False, "error_code": 500, "description": "boom"}])
        results, _ = self.send(self.calm(), fake)
        self.assertEqual(sorted(item["status"] for item in results), ["enviado", "falló"])
        retry, _ = self.send(self.calm())
        self.assertEqual(sorted(item["status"] for item in retry), ["enviado", "ya enviado"])


class CronRouteTests(StoreCase):
    def test_wrong_or_missing_bearer_is_rejected_and_sends_nothing(self):
        self.subscribe("@Persona_1", "resumen")
        subs.update_state(self.store, [("resumen", "@Persona_1", LIBERIA, subs.ACTIVE)])
        self.store.hset("chats", "persona_1", "42")
        no_secret = {k: v for k, v in ENV.items() if k != "CRON_SECRET"}
        for header, env in ((None, ENV), ("Bearer otro", ENV), ("cron-secret", ENV), ("Bearer ", no_secret), ("Bearer None", no_secret), (None, no_secret)):
            fake = FakeTelegram()
            self.assertEqual(rutas.enviar(header, self.store, fake, env, TODAY)[0], 401, header)
            self.assertEqual(fake.calls, [])

    def test_the_cron_sends_and_reports_only_counts(self):
        self.subscribe("@Persona_1", "resumen")
        subs.update_state(self.store, [("resumen", "@Persona_1", LIBERIA, subs.ACTIVE)])
        self.store.hset("chats", "persona_1", "42")
        fake = FakeTelegram()
        status, result = rutas.enviar("Bearer cron-secret", self.store, fake, ENV, TODAY)
        self.assertEqual((status, result), (200, {"ok": True, "considerados": 1, "enviados": 1, "fallaron": 0}))
        self.assertEqual(len(fake.sent()), 1)

    def test_without_token_it_is_unavailable(self):
        env = {k: v for k, v in ENV.items() if k != "TELEGRAM_BOT_TOKEN"}
        self.assertEqual(rutas.enviar("Bearer cron-secret", self.store, FakeTelegram(), env, TODAY)[0], 503)


class RedisStoreTests(unittest.TestCase):
    def session(self, *results, ok=True):
        queue = list(results)
        fake = mock.Mock()
        fake.post.side_effect = lambda url, json=None, headers=None, timeout=None: mock.Mock(ok=ok, status_code=200 if ok else 500, json=lambda: queue.pop(0))
        return fake

    def test_commands_go_as_a_json_array_with_the_bearer_token(self):
        session = self.session({"result": "valor"})
        redis = store_module.RedisStore("https://redis.example/", "tok", session)
        self.assertEqual(redis.hget("subs", "campo"), "valor")
        (url,), kwargs = session.post.call_args
        self.assertEqual((url, kwargs["json"], kwargs["headers"]), ("https://redis.example", ["HGET", "subs", "campo"], {"Authorization": "Bearer tok"}))

    def test_hgetall_reads_both_the_flat_list_and_the_object_form(self):
        self.assertEqual(store_module.RedisStore("u", "t", self.session({"result": ["a", "1", "b", "2"]})).hgetall("k"), {"a": "1", "b": "2"})
        self.assertEqual(store_module.RedisStore("u", "t", self.session({"result": {"a": "1"}})).hgetall("k"), {"a": "1"})
        self.assertEqual(store_module.RedisStore("u", "t", self.session({"result": []})).hgetall("k"), {})

    def test_counter_sets_its_lifetime_only_the_first_time(self):
        session = self.session({"result": 1}, {"result": 1}, {"result": 2})
        redis = store_module.RedisStore("u", "t", session)
        self.assertEqual((redis.incr_expire("rate", 3600), redis.incr_expire("rate", 3600)), (1, 2))
        self.assertEqual([call.kwargs["json"][0] for call in session.post.call_args_list], ["INCR", "EXPIRE", "INCR"])

    def test_errors_never_show_the_url_or_the_token(self):
        failing = mock.Mock()
        failing.post.side_effect = requests.ConnectionError("https://redis.secret.example tok-secret")
        for session in (failing, self.session({"error": "WRONGPASS"}, ok=False)):
            with self.assertRaises(store_module.StoreError) as caught:
                store_module.RedisStore("https://redis.secret.example", "tok-secret", session).hget("k", "f")
            self.assertNotIn("secret", str(caught.exception))

    def test_connection_comes_from_either_pair_of_variables(self):
        for url, token in (("KV_REST_API_URL", "KV_REST_API_TOKEN"), ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN")):
            redis = store_module.store_from_env({url: "https://r.example", token: "t"})
            self.assertEqual((redis.url, redis.token), ("https://r.example", "t"))
        with self.assertRaises(store_module.StoreError):
            store_module.store_from_env({})


class DeploymentFilesTests(unittest.TestCase):
    def test_telegram_alerts_is_an_exact_copy_of_the_one_in_src(self):
        self.assertEqual((WEB / "servidor" / "telegram_alerts.py").read_bytes(), (ROOT / "src" / "telegram_alerts.py").read_bytes())

    def test_consent_version_matches_the_one_of_the_form_and_of_the_local_api(self):
        form = (WEB / "src" / "NewsletterForm.tsx").read_text(encoding="utf-8")
        self.assertIn(f"CONSENT_VERSION = '{subs.CONSENT_VERSION}'", form)
        local = (ROOT / "src" / "newsletter.py").read_text(encoding="utf-8")  # se lee como texto: importarlo exige openpyxl
        self.assertIn(f'CONSENT_VERSION = "{subs.CONSENT_VERSION}"', local)

    def test_each_function_defines_a_handler_and_helpers_are_not_published_as_routes(self):
        self.assertEqual(sorted(p.name for p in (WEB / "api").glob("*.py")), ["enviar.py", "suscripciones.py", "telegram.py"])
        for path in (WEB / "api").glob("*.py"):
            self.assertIn("class handler(BaseHTTPRequestHandler)", path.read_text(encoding="utf-8"), path.name)

    def test_vercel_json_schedules_the_daily_send_once_and_ships_the_data_files(self):
        config = json.loads((WEB / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["crons"], [{"path": "/api/enviar", "schedule": "0 13 * * *"}])  # el plan Hobby solo permite una vez al día
        self.assertIn("public/data/*.json", config["functions"]["api/*.py"]["includeFiles"])
        self.assertIn("servidor/**", config["functions"]["api/*.py"]["includeFiles"])

    def test_runtime_requirements_are_minimal_so_vercel_does_not_pick_a_python_framework(self):
        names = {line.split("==")[0].strip().lower() for line in (WEB / "requirements.txt").read_text().splitlines() if line.strip()}
        self.assertEqual(names, {"requests", "tzdata"})

    def test_the_data_files_the_functions_read_exist(self):
        for path in (subs.ASADAS, subs.CANTON_INDEX, subs.PREDICTIONS):
            self.assertTrue(path.is_file(), path)

    def test_secret_files_that_vercel_writes_are_ignored_by_git(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for entry in ("web/.vercel/", "web/.env*.local"):
            self.assertIn(entry, ignore)


if __name__ == "__main__":
    unittest.main()
