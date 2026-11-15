"""Predicciones del sitio: episodio de El Niño, análogos y forma del JSON publicado."""
import json
import unittest

import pandas as pd

from src import predictions


def roni(values, start="2020-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="MS"))


class EpisodeTests(unittest.TestCase):
    def test_needs_five_months(self):
        series = roni([0, 0.6, 0.7, 0.8, 0.6, 0.2, 0, 0.9, 1.0, 0.4])  # 4 meses y 2 meses: ninguno cuenta
        self.assertEqual(predictions.find_episodes(series), [])

    def test_open_episode_is_current(self):
        series = roni([0, 0, 0.5, 1.0, 1.4, 1.7, 2.0])
        episodes = predictions.find_episodes(series)
        self.assertEqual(len(episodes), 1)
        self.assertTrue(episodes[0]["open"])
        self.assertEqual(episodes[0]["months"], 5)
        self.assertEqual(predictions.category(episodes[0]["peak"]), "muy fuerte")

    def test_categories(self):
        self.assertEqual([predictions.category(v) for v in (0.6, 1.0, 1.5, 2.3)], ["débil", "moderado", "fuerte", "muy fuerte"])


class PublishedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = predictions.build()

    def test_json_is_strict(self):
        json.dumps(self.payload, allow_nan=False)

    def test_only_temperature_has_estimates(self):
        for variable, block in self.payload["variables"].items():
            has = any(row["estimate"] is not None for region in block["regions"].values() for row in region["rows"])
            self.assertEqual(has, variable == "T2M", variable)

    def test_regional_only(self):
        self.assertEqual(set(self.payload["variables"]["T2M"]["regions"]), {"CR", "CR_PN", "CR_CAR"})

    def test_end_window_is_ordered_and_after_start(self):
        enso = self.payload["enso"]
        self.assertEqual(enso["status"], "active")
        window = enso["analog"]["end_window"]
        self.assertLessEqual(enso["start"], window["earliest"])
        self.assertLessEqual(window["earliest"], window["typical"])
        self.assertLessEqual(window["typical"], window["latest"])

    def test_analog_is_descriptive_not_a_forecast(self):
        for region, block in self.payload["rain_analog"].items():
            self.assertGreaterEqual(len(block["years"]), predictions.ANALOG_MIN_YEARS, region)
            self.assertTrue(all(month["n_years"] >= predictions.ANALOG_MIN_YEARS for month in block["months"]))


if __name__ == "__main__":
    unittest.main()
