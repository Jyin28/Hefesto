"""Capas anuales del mapa nacional (T2M, lluvia, humedad, UV)."""
import unittest

from src import layers
from src.layers import LAYERS, annual_series, build_layers
from src.web_data import national_package, raw_payloads


class AnnualSeriesTest(unittest.TestCase):
    def test_incomplete_year_is_none(self):
        monthly = {f"2020{m:02d}": 10.0 for m in range(1, 12)}  # falta diciembre
        self.assertEqual(annual_series(monthly, 2020, 2020, "mean"), [None])

    def test_fill_value_makes_year_incomplete(self):
        monthly = {f"2020{m:02d}": 10.0 for m in range(1, 13)}
        monthly["202006"] = -999.0
        self.assertEqual(annual_series(monthly, 2020, 2020, "mean"), [None])

    def test_constant_mean_and_daily_sum(self):
        monthly = {f"2021{m:02d}": 2.0 for m in range(1, 13)}
        self.assertEqual(annual_series(monthly, 2021, 2021, "mean"), [2.0])
        self.assertEqual(annual_series(monthly, 2021, 2021, "sum_daily"), [730.0])  # 2 mm/día x 365 días


class BuiltLayersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payloads, provenance = raw_payloads()
        cls.layers = build_layers(payloads, provenance)

    def test_shape(self):
        for layer_id, spec in LAYERS.items():
            layer = self.layers[layer_id]
            years = spec["end"] - spec["start"] + 1
            self.assertEqual(len(layer["national"]), years, layer_id)
            self.assertEqual(len(layer["cells"]), 24, layer_id)
            self.assertTrue(all(len(v) == years for v in layer["cells"].values()), layer_id)

    def test_uv_starts_in_2001_and_humidity_in_1981(self):
        self.assertEqual((self.layers["UV"]["start"], self.layers["UV"]["end"]), (2001, 2024))
        self.assertEqual(len(self.layers["RH2M"]["national"]), 44)
        self.assertEqual(len(self.layers["UV"]["national"]), 24)

    def test_value_ranges(self):
        for value in self.layers["RH2M"]["national"]:
            self.assertTrue(0 < value <= 100)
        for value in self.layers["UV"]["national"]:
            self.assertTrue(0 < value < 20)

    def test_temperature_matches_existing_pipeline(self):
        _, cells = national_package()
        cell_id, cell = next(iter(cells.items()))
        existing = {r["year"]: r["value"] for r in cell["annual"] if r["variable"] == "T2M"}
        mine = dict(zip(range(1981, 2025), self.layers["T2M"]["cells"][cell_id]))
        for year, value in existing.items():
            if value is not None:
                self.assertAlmostEqual(mine[year], value, delta=0.01)

    def test_provenance_of_downloaded_layers(self):
        for layer_id in layers.DOWNLOADED:
            self.assertEqual(len(self.layers[layer_id]["provenance"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
