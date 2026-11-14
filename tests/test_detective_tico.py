"""Integration checks using the repository's real NASA POWER package."""
from calendar import monthrange
from csv import DictReader
import json
from math import sqrt
import unittest

from src.contracts import REGION_IDS, VARIABLE_IDS, to_json
from src.enso import episode_comparison
from src.evidence import sen_mann_kendall
from src.export import csv_tables, evidence_card, format_csv
from src.forecast import evaluate_station
from src.web_data import climate, climate_package, local_catalog


class DetectiveTicoTest(unittest.TestCase):
    def test_all_four_real_queries(self):
        for region in REGION_IDS:
            for variable in VARIABLE_IDS:
                with self.subTest(region=region, variable=variable):
                    card = evidence_card(region, variable)
                    self.assertFalse(card["synthetic"])
                    self.assertEqual(len(card["series"]), 44)
                    self.assertTrue(all(row["complete"] for row in card["series"]))
                    self.assertEqual(card["comparison"]["window_a"]["n_years"], 22)
                    self.assertEqual(card["comparison"]["window_b"]["n_years"], 22)
                    self.assertEqual(card["families"]["regions"]["ols"]["planned_tests"], 4)
                    self.assertEqual(card["families"]["cells"]["ols"]["planned_tests"], 10)
                    self.assertEqual(len(card["cells"]), 5)
                    self.assertEqual(json.loads(to_json(card)), card)

    def test_cell_values_and_filtering_share_the_original_family(self):
        card = climate("CR_CAR", "PRECTOTCORR")
        cell = card["cells"][0]
        detail = climate("CR_CAR", "PRECTOTCORR", cell_id=cell["id"])
        self.assertEqual(detail["trend"], cell["evidence"]["ols"])
        self.assertEqual(detail["evidence"]["mann_kendall"], cell["evidence"]["mann_kendall"])
        with self.assertRaises(ValueError):
            climate("CR_PN", "PRECTOTCORR", cell_id=cell["id"])

        _, cells, _ = climate_package()
        expected_rain = sum(row["value"] * monthrange(2000, row["month"])[1]
                            for row in cells[cell["id"]]["monthly"]
                            if row["year"] == 2000 and row["variable"] == "PRECTOTCORR")
        annual = next(row for row in detail["series"] if row["year"] == 2000)
        self.assertAlmostEqual(expected_rain, annual["value"])

    def test_hac_matches_independent_sandwich_calculation(self):
        card = climate("CR_PN", "PRECTOTCORR")
        data = [(row["year"] - 1981, row["value"]) for row in card["series"]]
        n = len(data)
        sx, sy = (sum(row[i] for row in data) for i in (0, 1))
        sxx = sum(x * x for x, _ in data)
        sxy = sum(x * y for x, y in data)
        determinant = n * sxx - sx * sx
        slope = (n * sxy - sx * sy) / determinant
        intercept = (sxx * sy - sx * sxy) / determinant
        scores = [(y - intercept - slope * x, x * (y - intercept - slope * x)) for x, y in data]
        inverse_slope_row = (-sx / determinant, n / determinant)
        meat = [
            [
                sum((1 - abs(i - j) / 4) * scores[i][left] * scores[j][right]
                    for i in range(n) for j in range(n) if abs(i - j) <= 3)
                for right in range(2)
            ]
            for left in range(2)
        ]
        variance = sum(inverse_slope_row[i] * meat[i][j] * inverse_slope_row[j]
                       for i in range(2) for j in range(2)) * n / (n - 2)
        self.assertAlmostEqual(card["trend"]["slope_per_decade"], 10 * slope, places=8)
        self.assertAlmostEqual(card["trend"]["se_hac"], 10 * sqrt(variance), places=8)

    def test_custom_windows_and_exports_use_same_selection(self):
        card = evidence_card("CR_PN", "PRECTOTCORR", window_a=(1990, 2000), window_b=(2014, 2024))
        tables = csv_tables(card)
        results = list(DictReader(format_csv(tables["results"]).splitlines()))
        window_a = next(row for row in results if row["window"] == "window_a")
        self.assertEqual(int(window_a["start_year"]), 1990)
        self.assertEqual(float(window_a["mean"]), card["comparison"]["window_a"]["mean"])
        self.assertEqual({row["result_id"] for row in results}, {card["result_id"]})
        self.assertNotEqual(card["result_id"], evidence_card("CR_PN", "PRECTOTCORR")["result_id"])
        self.assertEqual(tables["water"][0]["denominator"], card["water_coverage"][0]["denominator"])
        ids = {row["source_id"] for row in tables["sources"]}
        self.assertTrue(all(row["source_id"] in ids for row in tables["water"] + tables["series"]))

    def test_documented_enso_and_leap_month(self):
        card = climate("CR_PN", "PRECTOTCORR")
        event = card["enso"]
        self.assertEqual(event["neutral_window"], ["2013-07", "2014-04"])
        self.assertEqual(len(event["months"]), 10)
        self.assertEqual(event["unit"], "mm/month")
        february = next(row for row in event["months"] if row["date"] == "2024-02")
        monthly = next(r for r in climate_package()[0]["regional_monthly"]
                       if r["year"] == 2024 and r["month"] == 2 and r["region_id"] == "CR_PN"
                       and r["variable"] == "PRECTOTCORR")
        self.assertAlmostEqual(february["value"], monthly["value"] * 29)
        self.assertAlmostEqual(february["vs_neutral"], february["value"] - february["neutral"])

    def test_unverified_enso_reference_leaves_climatology_available(self):
        monthly = [{"year": year, "month": 1, "variable": "T2M", "value": 20}
                   for year in range(1981, 2011)]
        monthly.append(dict(monthly[0], year=2024, value=21))
        catalog = {"episodes": [{"start": "2024-01", "end": "2024-01", "sources": ["IMN"]}],
                   "neutral_periods": []}
        event = episode_comparison(monthly, "T2M", catalog, 1981, 2024)
        self.assertEqual(event["status"], "neutral_unverified")
        self.assertEqual(event["months"][0]["anomaly"], 1)
        self.assertIsNone(event["months"][0]["neutral"])

    def test_mann_kendall_ties_and_gaps(self):
        rows = [{"year": year, "variable": "T2M", "region_id": "CR_PN", "value": 1.0}
                for year in range(1981, 2012)]
        constant = sen_mann_kendall(rows, 1981, 2011, "T2M", "CR_PN")
        self.assertEqual(constant["slope_per_decade"], 0)
        self.assertIsNone(constant["p_value"])
        for row in rows:
            row["value"] = float(row["year"])
        trend = sen_mann_kendall(rows, 1981, 2011, "T2M", "CR_PN")
        self.assertAlmostEqual(trend["slope_per_decade"], 10)
        self.assertLess(trend["p_value"], .001)
        self.assertIsNone(sen_mann_kendall(rows[:10] + rows[11:], 1981, 2011, "T2M", "CR_PN")["p_value"])

    def test_canton_catalog_is_national(self):
        catalog = local_catalog()
        self.assertEqual(len(catalog["cantons"]), 84)
        self.assertEqual(catalog["cantons"]["613"]["name"], "Puerto Jiménez")
        self.assertEqual(len([c for c in catalog["cantons"].values() if "regionId" in c]), 2)


class ForecastValidationTest(unittest.TestCase):
    def test_station_climatology_has_no_future_leakage(self):
        metadata = {"station_id": "fixture", "name": "Estación sintética", "latitude": 10,
                    "longitude": -85, "unit": "degC", "source_url": "fixture", "license": "fixture"}
        rows = [{"year": year, "month": month, "value": 20 + month}
                for year in range(2010, 2022) for month in range(1, 13)]
        result = evaluate_station(rows, metadata, "T2M")
        self.assertEqual(result["first_validation_training_period"][-1], "2019-12")
        self.assertEqual(result["validation_period"], ["2020-01", "2021-12"])
        self.assertEqual(result["baseline_mae"], 0)
        self.assertIsNone(result["forecast"])
        self.assertEqual(evaluate_station(rows[:-1], metadata, "T2M")["status"], "insufficient_station_data")


if __name__ == "__main__":
    unittest.main()
