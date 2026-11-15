"""Contrato de /api/predicciones (sin abrir sockets) y su montaje en la API del sitio."""
import unittest

from fastapi import HTTPException

from hefesto_forecast.api import app, predictions
from src.web_api import app as site_app


class ApiTests(unittest.TestCase):
    def test_prediction_handler(self):
        result = predictions(region="CR", variable="T2M", start="2026-12", months=6)
        self.assertEqual(len(result["rows"]), 6)
        self.assertAlmostEqual(result["rows"][0]["estimate"], 22.785, places=3)

    def test_invalid_inputs_return_422(self):
        for changes in [{"region": "101"}, {"months": 7}, {"start": "2026-13"}]:
            args = dict(region="CR", variable="T2M", start="2026-12", months=6)
            args.update(changes)
            with self.assertRaises(HTTPException) as caught:
                predictions(**args)
            self.assertEqual(caught.exception.status_code, 422)

    def test_route_registered(self):
        operation = app.openapi()["paths"]["/api/predicciones"]["get"]
        params = {x["name"]: x for x in operation["parameters"]}
        self.assertEqual(params["region"]["schema"]["enum"], ["CR", "CR_PN", "CR_CAR"])
        self.assertEqual(params["months"]["schema"]["maximum"], 6)

    def test_mounted_in_site_api(self):
        self.assertIn("/api/predicciones", site_app.openapi()["paths"])


if __name__ == "__main__":
    unittest.main()
