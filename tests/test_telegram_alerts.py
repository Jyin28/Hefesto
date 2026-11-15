"""Avisos por Telegram: solo se arman si los datos los respaldan, y nunca filtran el token ni los @usuarios al sitio."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from src import predictions, telegram_alerts as tg

RECIPIENTS = [
    {"username": "Calor1", "alert": "heat", "canton_code": "501", "canton": "Liberia", "province": "Guanacaste", "zone": "Pacífico Norte", "region": "CR_PN"},
    {"username": "Lluvia1", "alert": "rain", "canton_code": "701", "canton": "Limón", "province": "Limón", "zone": "Caribe", "region": "CR_CAR"},
    {"username": "Nino1", "alert": "nino", "canton_code": "210", "canton": "San Carlos", "province": "Alajuela", "zone": "Zona Norte", "region": "CR"},
]
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

    def test_three_alerts_with_data_figures(self):
        alerts = tg.build_alerts(self.payload, RECIPIENTS)
        self.assertEqual([a["kind"] for a in alerts], ["heat", "rain", "nino"])
        for alert in alerts:
            self.assertIn("No es un aviso oficial", alert["text"])
            self.assertLess(len(alert["text"]), 4096)
        self.assertIn("24,9 °C", alerts[0]["text"])
        self.assertIn("277 mm", alerts[1]["text"])
        self.assertIn("mayo de 2026", alerts[2]["text"])

    def test_rain_alert_admits_it_is_not_a_validated_forecast(self):
        text = tg.build_alerts(self.payload, RECIPIENTS)[1]["text"]
        self.assertIn("No hay un pronóstico de lluvia validado", text)

    def test_heat_alert_rejected_without_warm_anomaly(self):
        payload = copy.deepcopy(self.payload)
        row = payload["variables"]["T2M"]["regions"]["CR_PN"]["rows"][0]
        row["estimate"] = row["reference"]["mean"] + 0.1
        with self.assertRaises(tg.AlertNotSupported):
            tg.build_alerts(payload, RECIPIENTS)

    def test_nino_alert_rejected_without_active_episode(self):
        payload = copy.deepcopy(self.payload)
        payload["enso"]["status"] = "none"
        with self.assertRaises(tg.AlertNotSupported):
            tg.build_alerts(payload, RECIPIENTS)

    def test_rain_alert_rejected_in_a_dry_region(self):
        dry = [dict(RECIPIENTS[1], region="CR_PN", zone="Pacífico Norte")]
        with self.assertRaises(tg.AlertNotSupported):
            tg.build_alerts(self.payload, dry)


class SendTests(unittest.TestCase):
    alerts = [{"kind": "heat", "username": "Calor1", "canton": "Liberia", "province": "Guanacaste", "zone": "Pacífico Norte", "region": "CR_PN", "text": "hola"},
              {"kind": "rain", "username": "Lluvia1", "canton": "Limón", "province": "Limón", "zone": "Caribe", "region": "CR_CAR", "text": "hola 2"}]

    def test_sends_only_to_known_chats_and_reports_pending(self):
        session = FakeSession([{"ok": True, "result": {}}])
        results = tg.send(TOKEN, self.alerts, {"calor1": 42}, session)
        self.assertEqual([r["status"] for r in results], ["sent", "pending"])
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0][1]["chat_id"], 42)

    def test_telegram_error_is_reported_without_the_token(self):
        session = FakeSession([{"ok": False, "description": "Forbidden: bot was blocked by the user", "error_code": 403}])
        results = tg.send(TOKEN, self.alerts[:1], {"calor1": 42}, session)
        self.assertEqual(results[0]["status"], "failed")
        self.assertNotIn(TOKEN, json.dumps(results))

    def test_network_error_never_shows_the_url(self):
        session = mock.Mock()
        session.post.side_effect = requests.ConnectionError(f"https://api.telegram.org/bot{TOKEN}/sendMessage")
        with self.assertRaises(tg.TelegramError) as caught:
            tg.call(TOKEN, "getMe", session=session)
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_discover_maps_usernames_case_insensitively_and_ignores_others(self):
        updates = [{"message": {"from": {"username": "CALOR1"}, "chat": {"id": 7, "type": "private"}}},
                   {"message": {"from": {"username": "alguien"}, "chat": {"id": 8, "type": "private"}}},
                   {"message": {"from": {"username": "Lluvia1"}, "chat": {"id": -9, "type": "group"}}}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chats.json"
            found = tg.discover(TOKEN, RECIPIENTS, path, FakeSession([{"ok": True, "result": updates}]))
            self.assertEqual(found, {"calor1": 7})
            self.assertEqual(json.loads(path.read_text()), {"calor1": 7})

    def test_public_view_hides_usernames_and_chat_ids(self):
        view = tg.public_view([{**self.alerts[0], "status": "sent", "sent_at": "x", "chat_id": 42}])
        self.assertNotIn("username", view[0])
        self.assertNotIn("chat_id", view[0])


class TokenTests(unittest.TestCase):
    def test_env_wins_then_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            dotenv = Path(tmp) / ".env"
            dotenv.write_text("OTRA=1\nTELEGRAM_BOT_TOKEN='abc:def'\n", encoding="utf-8")
            self.assertEqual(tg.load_token({"TELEGRAM_BOT_TOKEN": "env:tok"}, dotenv), "env:tok")
            self.assertEqual(tg.load_token({}, dotenv), "abc:def")
            self.assertIsNone(tg.load_token({}, Path(tmp) / "no-existe"))


if __name__ == "__main__":
    unittest.main()
