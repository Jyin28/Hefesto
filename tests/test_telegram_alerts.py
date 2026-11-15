"""Mensajes de Telegram: solo se arman si los datos los respaldan, en español e inglés, y nunca filtran el token."""
import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import requests

from src import predictions, telegram_alerts as tg

LIBERIA = {"asada": "ASADA de Liberia", "canton": "Liberia", "province": "Guanacaste", "region": "CR_PN"}
LIMON = {"asada": "ASADA de Limón", "canton": "Limón", "province": "Limón", "region": "CR_CAR"}
SAN_CARLOS = {"asada": "ASADA de San Carlos", "canton": "San Carlos", "province": "Alajuela", "region": "CR"}
TOKEN = "123456:SECRET-TOKEN"


class FakeSession:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def post(self, url, json=None, timeout=None):  # noqa: A002 (misma firma que requests)
        self.calls.append((url, json))
        reply = self.replies.pop(0)
        return mock.Mock(json=lambda: reply)


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = predictions.build()

    def test_alerts_carry_data_figures_in_spanish(self):
        heat, rain, nino = tg.heat_alert(self.payload, LIBERIA), tg.rain_alert(self.payload, LIMON), tg.nino_alert(self.payload, SAN_CARLOS)
        for text in (heat, rain, nino):
            self.assertIn("No es un aviso oficial", text)
            self.assertLess(len(text), 4096)
        self.assertIn("24,9 °C", heat)
        self.assertIn("277 mm", rain)
        self.assertIn("mayo de 2026", nino)
        self.assertIn("ASADA de Liberia", heat)

    def test_alerts_in_english_use_english_numbers_and_months(self):
        heat, rain, nino = (tg.heat_alert(self.payload, LIBERIA, "en"), tg.rain_alert(self.payload, LIMON, "en"), tg.nino_alert(self.payload, SAN_CARLOS, "en"))
        self.assertIn("24.9 °C", heat)
        self.assertIn("277 mm", rain)
        self.assertIn("since May 2026", nino)
        self.assertIn("very strong", nino)
        for text in (heat, rain, nino):
            self.assertIn("not an official notice", text)
            self.assertNotIn("Aviso", text)

    def test_rain_alert_admits_it_is_not_a_validated_forecast(self):
        self.assertIn("No hay un pronóstico de lluvia validado", tg.rain_alert(self.payload, LIMON))
        self.assertIn("no validated rain forecast", tg.rain_alert(self.payload, LIMON, "en"))

    def test_heat_alert_rejected_without_warm_anomaly(self):
        payload = copy.deepcopy(self.payload)
        row = payload["variables"]["T2M"]["regions"]["CR_PN"]["rows"][0]
        row["estimate"] = row["reference"]["mean"] + 0.1
        with self.assertRaises(tg.AlertNotSupported):
            tg.heat_alert(payload, LIBERIA)

    def test_nino_alert_rejected_without_active_episode(self):
        payload = copy.deepcopy(self.payload)
        payload["enso"]["status"] = "none"
        with self.assertRaises(tg.AlertNotSupported):
            tg.nino_alert(payload, SAN_CARLOS)

    def test_rain_alert_rejected_in_a_dry_region(self):
        with self.assertRaises(tg.AlertNotSupported):
            tg.rain_alert(self.payload, LIBERIA)

    def test_supported_alerts_returns_only_what_the_data_back(self):
        kinds = [alert.kind for alert in tg.supported_alerts(self.payload, LIBERIA)]
        self.assertIn("heat", kinds)
        self.assertNotIn("rain", kinds)

    def calm_payload(self):
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

    def test_daily_summary_with_risks_lists_them_and_the_tips(self):
        text, risky = tg.daily_summary(self.payload, LIBERIA, "es", date(2026, 11, 15))
        self.assertTrue(risky)
        self.assertIn("Resumen diario (15 de noviembre de 2026)", text)
        self.assertIn("Los datos advierten:", text)
        self.assertIn("Qué podés hacer:", text)
        self.assertNotIn("No hubo cambios significativos", text)

    def test_daily_summary_without_risks_says_there_were_no_significant_changes(self):
        text, risky = tg.daily_summary(self.calm_payload(), LIBERIA, "es", date(2026, 11, 15))
        self.assertFalse(risky)
        self.assertIn("No hubo cambios significativos", text)
        english, _ = tg.daily_summary(self.calm_payload(), LIBERIA, "en", date(2026, 11, 15))
        self.assertIn("No significant changes", english)
        self.assertIn("Daily summary (November 15, 2026)", english)

    def test_bot_texts_name_the_chosen_option(self):
        self.assertIn("alertas y sugerencias", tg.welcome_text("alertas", LIBERIA))
        self.assertIn("daily summary", tg.welcome_text("resumen", LIBERIA, "en"))
        self.assertIn("/stop", tg.welcome_text("resumen", LIBERIA))


class TelegramApiTests(unittest.TestCase):
    def test_telegram_error_is_reported_without_the_token(self):
        session = FakeSession([{"ok": False, "description": "Forbidden: bot was blocked by the user", "error_code": 403}])
        with self.assertRaises(tg.TelegramError) as caught:
            tg.send_message(TOKEN, 42, "hola", session)
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertIn("403", str(caught.exception))

    def test_network_error_never_shows_the_url(self):
        session = mock.Mock()
        session.post.side_effect = requests.ConnectionError(f"https://api.telegram.org/bot{TOKEN}/sendMessage")
        with self.assertRaises(tg.TelegramError) as caught:
            tg.call(TOKEN, "getMe", session=session)
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_send_message_posts_to_the_chat(self):
        session = FakeSession([{"ok": True, "result": {}}])
        tg.send_message(TOKEN, 42, "hola", session)
        self.assertEqual(session.calls[0][1]["chat_id"], 42)
        self.assertTrue(session.calls[0][1]["disable_web_page_preview"])


class TokenTests(unittest.TestCase):
    def test_env_wins_then_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text("OTRA=1\nTELEGRAM_BOT_TOKEN='abc:def'\n", encoding="utf-8")
            self.assertEqual(tg.load_token({"TELEGRAM_BOT_TOKEN": "env:tok"}, dotenv), "env:tok")
            self.assertEqual(tg.load_token({}, dotenv), "abc:def")
            self.assertIsNone(tg.load_token({}, Path(tmp) / "no-existe"))

    def test_empty_token_in_dotenv_counts_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text("TELEGRAM_BOT_TOKEN=\n", encoding="utf-8")
            self.assertIsNone(tg.load_token({}, dotenv))


if __name__ == "__main__":
    unittest.main()
