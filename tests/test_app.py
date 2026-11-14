"""Pruebas de la app Streamlit real (AppTest), recorridos calor/lluvia, offline y UI = exportación."""
import os
import socket
import unittest

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _run_tour(label):
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    next(b for b in at.sidebar.button if label in b.label).click().run()
    assert not at.exception, at.exception
    next(b for b in at.button if "Investigar" in b.label).click().run()
    return at


class AppTourTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("HEFESTO_USE_MOCK", None)
        # Sin red: cualquier conexión de salida debe fallar ruidosamente.
        self._real_connect = socket.socket.connect
        real = self._real_connect

        def guarded(sock, address, *a, **k):
            host = address[0] if isinstance(address, tuple) else address
            if host not in ("127.0.0.1", "::1", "localhost"):
                raise OSError(f"sin red en la prueba: {host}")
            return real(sock, address, *a, **k)

        socket.socket.connect = guarded

    def tearDown(self):
        socket.socket.connect = self._real_connect

    def test_heat_tour(self):
        at = _run_tour("calor")
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["stage"], "results")
        card = at.session_state["card"]
        self.assertFalse(card["synthetic"])
        self.assertEqual(card["query"]["variable"], "T2M")
        self.assertEqual(len(card["results"]), 2)
        self.assertGreaterEqual(len(card["family_metadata"]), 2)
        # UI = exportación: mismo result_id en todos los archivos
        bundle = at.session_state["bundle"]
        self.assertIn(card["result_id"].encode(), bundle.evidence_md)
        self.assertIn(card["result_id"].encode(), bundle.evidence_json)
        self.assertIn(card["result_id"].encode(), bundle.trends_csv)
        self.assertIn(card["result_id"].encode(), bundle.series_csv)

    def test_rain_tour_has_unit_and_caution(self):
        at = _run_tour("lluvia")
        self.assertFalse(at.exception)
        card = at.session_state["card"]
        self.assertEqual(card["query"]["variable"], "PRECTOTCORR")
        self.assertTrue(all(r["slope_unit"] == "mm/yr/decade" for r in card["results"]))
        self.assertIn("reanalysis_precip_caution", card["warnings"])
        self.assertTrue(any("no está validada" in w.value for w in at.warning))

    def test_wizard_reaches_results_with_hypothesis(self):
        at = AppTest.from_file(APP, default_timeout=60).run()
        at.radio(key="topic").set_value("rain").run()
        next(b for b in at.button if "Continuar" in b.label).click().run()
        at.text_area(key="hypothesis").set_value("Creo que llueve más <b>").run()
        next(b for b in at.button if "Investigar" in b.label).click().run()
        self.assertFalse(at.exception)
        self.assertNotIn("<b>", at.session_state["card"]["hypothesis"])



class MockModeTest(unittest.TestCase):
    def test_mock_mode_shows_permanent_synthetic_banner(self):
        os.environ["HEFESTO_USE_MOCK"] = "1"
        try:
            at = AppTest.from_file(APP, default_timeout=60).run()
            self.assertFalse(at.exception)
            self.assertTrue(any("SINTÉTICOS" in e.value for e in at.error))
            next(b for b in at.sidebar.button if "calor" in b.label).click().run()
            next(b for b in at.button if "Investigar" in b.label).click().run()
            self.assertFalse(at.exception)
            self.assertTrue(at.session_state["card"]["synthetic"])
        finally:
            os.environ.pop("HEFESTO_USE_MOCK", None)


if __name__ == "__main__":
    unittest.main()
