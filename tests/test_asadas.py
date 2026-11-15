"""Catálogo de operadores de agua generado desde el Excel de SAGA."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "web" / "asadas.json").read_text(encoding="utf-8"))
CANTONS = json.loads((ROOT / "data" / "web" / "cantons.json").read_text(encoding="utf-8"))["cantons"]


class AsadasTest(unittest.TestCase):
    def test_count_and_unique_ids(self):
        operators = DATA["operators"]
        self.assertEqual(len(operators), 1334)
        self.assertEqual(len({item["id"] for item in operators}), 1334)

    def test_every_operator_has_a_valid_canton(self):
        for item in DATA["operators"]:
            self.assertIn(item["cantonCode"], CANTONS, item["id"])
            self.assertEqual(item["province"], CANTONS[item["cantonCode"]]["province"], item["id"])
            self.assertTrue(item["district"], item["id"])

    def test_initial_flow_is_sum_of_sources(self):
        for item in DATA["operators"]:
            flows = [s["caudal"] for s in item["sources"] if s["caudal"] is not None]
            if flows:
                self.assertAlmostEqual(item["caudal"], sum(flows), places=1, msg=item["id"])
            else:
                self.assertIsNone(item["caudal"], item["id"])

    def test_known_operators(self):
        by_id = {item["id"]: item for item in DATA["operators"]}
        self.assertEqual(by_id["00001-2014"]["caudal"], 5.4)  # una sola fuente con medición
        self.assertEqual(by_id["00001-2014"]["cantonCode"], "501")
        self.assertEqual(by_id["00114-2014"]["district"], "Tamarindo")
        self.assertAlmostEqual(by_id["00114-2014"]["caudal"], 27.32, places=2)

    def test_types_and_flow_coverage(self):
        types = {item["type"] for item in DATA["operators"]}
        self.assertIn("ASADA", types)
        self.assertEqual(sum(1 for item in DATA["operators"] if item["caudal"] is not None), 1175)


if __name__ == "__main__":
    unittest.main()
