"""Pruebas de EMANUEL-03: preparacion de series regionales mensuales/anuales.

Usa los fixtures sinteticos de EMANUEL-02 (tests/fixtures/stats/*.json) como
referencia numerica independiente donde aplica (cobertura, bisiesto, año
incompleto, estacionalidad).
"""
from __future__ import annotations

import copy
import json
import math
import unittest
from datetime import date
from pathlib import Path

from src import prepare

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "stats"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class LeapYearArithmeticTest(unittest.TestCase):
    def test_days_in_year_matches_known_cases(self):
        self.assertEqual(prepare.days_in_year(1999), 365)
        self.assertEqual(prepare.days_in_year(2000), 366)
        self.assertEqual(prepare.days_in_year(1900), 365)  # div 100, no div 400
        self.assertEqual(prepare.days_in_year(2024), 366)

    def test_verify_leap_year_arithmetic_passes(self):
        prepare.verify_leap_year_arithmetic()  # no debe lanzar


class WeightedMeanCoverageTest(unittest.TestCase):
    """Replica tests/fixtures/stats/regional_coverage.json."""

    def setUp(self):
        self.fx = load_fixture("regional_coverage")

    def test_both_cells_present(self):
        cells = self.fx["input"]["scenario_both_cells_present"]
        mean, coverage = prepare.weighted_mean([c["value"] for c in cells], [c["weight"] for c in cells])
        expected = self.fx["expected"]["both_cells_present"]
        self.assertEqual(mean, expected["weighted_mean"])
        self.assertEqual(coverage, expected["coverage"])

    def test_second_cell_missing(self):
        cells = self.fx["input"]["scenario_second_cell_missing"]
        mean, coverage = prepare.weighted_mean([c["value"] for c in cells], [c["weight"] for c in cells])
        expected = self.fx["expected"]["second_cell_missing"]
        self.assertEqual(mean, expected["weighted_mean"])
        self.assertEqual(coverage, expected["coverage"])
        self.assertTrue(expected["mean_is_absent_below_threshold"])


class BuildRegionalMonthlyTest(unittest.TestCase):
    """Dos celdas sinteticas de CR_PN con pesos 1/4 y 3/4 (normalizados), un mes."""

    def setUp(self):
        self.mask_rows = [
            {"region_id": "CR_PN", "lat": 10.0, "lon": -85.625, "weight": 0.25, "mask_version": "test"},
            {"region_id": "CR_PN", "lat": 10.5, "lon": -85.625, "weight": 0.75, "mask_version": "test"},
        ]

    def test_full_coverage_gives_weighted_value(self):
        cell_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625, "year": 2000, "month": 1,
             "value": 10.0, "unit": "degC", "synthetic": True},
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.5, "lon": -85.625, "year": 2000, "month": 1,
             "value": 14.0, "unit": "degC", "synthetic": True},
        ]
        rows = prepare.build_regional_monthly(
            cell_rows, self.mask_rows, regions=("CR_PN",), variables=("T2M",),
            start_year=2000, end_year=2000,
        )
        jan = next(r for r in rows if r["month"] == 1)
        self.assertAlmostEqual(jan["value"], 0.25 * 10.0 + 0.75 * 14.0)
        self.assertEqual(jan["coverage_fraction"], 1.0)
        self.assertEqual(jan["n_cells_valid"], 2)

    def test_missing_cell_makes_value_absent_not_fatal(self):
        cell_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625, "year": 2000, "month": 1,
             "value": 10.0, "unit": "degC", "synthetic": True},
            # celda (10.5, -85.625) sin fila -> ausente, no lanza
        ]
        rows = prepare.build_regional_monthly(
            cell_rows, self.mask_rows, regions=("CR_PN",), variables=("T2M",),
            start_year=2000, end_year=2000,
        )
        jan = next(r for r in rows if r["month"] == 1)
        self.assertIsNone(jan["value"])
        self.assertEqual(jan["coverage_fraction"], 0.25)
        self.assertEqual(jan["n_cells_valid"], 1)

    def test_zero_value_is_not_treated_as_missing(self):
        cell_rows = [
            {"region_id": "CR_PN", "variable": "PRECTOTCORR", "lat": 10.0, "lon": -85.625, "year": 2000, "month": 2,
             "value": 0.0, "unit": "mm/day", "synthetic": True},
            {"region_id": "CR_PN", "variable": "PRECTOTCORR", "lat": 10.5, "lon": -85.625, "year": 2000, "month": 2,
             "value": 0.0, "unit": "mm/day", "synthetic": True},
        ]
        rows = prepare.build_regional_monthly(
            cell_rows, self.mask_rows, regions=("CR_PN",), variables=("PRECTOTCORR",),
            start_year=2000, end_year=2000,
        )
        feb = next(r for r in rows if r["month"] == 2)
        self.assertEqual(feb["value"], 0.0)
        self.assertEqual(feb["coverage_fraction"], 1.0)
        self.assertEqual(feb["n_cells_valid"], 2)

    def test_duplicate_cell_month_raises(self):
        cell_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625, "year": 2000, "month": 1,
             "value": 10.0, "unit": "degC", "synthetic": True},
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625, "year": 2000, "month": 1,
             "value": 11.0, "unit": "degC", "synthetic": True},
        ]
        with self.assertRaises(ValueError):
            prepare.build_regional_monthly(
                cell_rows, self.mask_rows, regions=("CR_PN",), variables=("T2M",),
                start_year=2000, end_year=2000,
            )


class BuildRegionalAnnualTest(unittest.TestCase):
    """Cruza leap_year_precip.json e incomplete_year.json a traves de build_regional_annual."""

    def _single_cell_monthly_rows(self, variable: str, year: int, monthly_values: list[float | None], unit: str):
        return [
            {
                "region_id": "CR_PN", "variable": variable, "year": year, "month": m,
                "value": v, "unit": unit, "coverage_fraction": 1.0 if v is not None else 0.0,
                "n_cells_valid": 1 if v is not None else 0, "n_cells_total": 1,
            }
            for m, v in zip(range(1, 13), monthly_values)
        ]

    def test_leap_year_precip_accumulation(self):
        fx = load_fixture("leap_year_precip")
        rate = fx["input"]["monthly_value_constant"]
        for year_str, expected in fx["expected"].items():
            year = int(year_str)
            monthly = self._single_cell_monthly_rows("PRECTOTCORR", year, [rate] * 12, "mm/day")
            annual = prepare.build_regional_annual(monthly, regions=("CR_PN",), variables=("PRECTOTCORR",),
                                                     start_year=year, end_year=year)
            row = annual[0]
            self.assertTrue(row["complete"])
            self.assertAlmostEqual(row["value"], expected["annual_total_mm_per_year"])

    def test_incomplete_year_has_no_annual_value(self):
        fx = load_fixture("incomplete_year")
        year = fx["input"]["year"]
        monthly_values = fx["input"]["monthly_values"]
        monthly = self._single_cell_monthly_rows("PRECTOTCORR", year, monthly_values, "mm/day")
        annual = prepare.build_regional_annual(monthly, regions=("CR_PN",), variables=("PRECTOTCORR",),
                                                start_year=year, end_year=year)
        row = annual[0]
        self.assertEqual(row["months_valid"], fx["expected"]["valid_months"])
        self.assertEqual(row["complete"], fx["expected"]["year_complete"])
        self.assertIsNone(row["value"])
        self.assertIn("incomplete_year", row["warnings"])

    def test_zero_month_counts_as_valid_not_missing(self):
        fx = load_fixture("incomplete_year")
        monthly_values = fx["input"]["monthly_values"]
        self.assertEqual(monthly_values[1], 0.0)
        monthly = self._single_cell_monthly_rows(
            "PRECTOTCORR", fx["input"]["year"],
            [2.0 if v is None else v for v in monthly_values],  # mayo presente para aislar el caso cero
            "mm/day",
        )
        feb_row = monthly[1]
        self.assertEqual(feb_row["value"], 0.0)
        annual = prepare.build_regional_annual(monthly, regions=("CR_PN",), variables=("PRECTOTCORR",),
                                                start_year=fx["input"]["year"], end_year=fx["input"]["year"])
        self.assertEqual(annual[0]["months_valid"], 12)
        self.assertTrue(annual[0]["complete"])

    def test_t2m_annual_weighted_mean_matches_seasonality_fixture(self):
        fx = load_fixture("seasonality_no_trend")
        for year_str, detail in fx["input"]["detail_by_year"].items():
            year = int(year_str)
            monthly = self._single_cell_monthly_rows("T2M", year, detail["monthly_values"], "degC")
            annual = prepare.build_regional_annual(monthly, regions=("CR_PN",), variables=("T2M",),
                                                    start_year=year, end_year=year)
            self.assertAlmostEqual(annual[0]["value"], detail["annual_mean"])
            self.assertAlmostEqual(annual[0]["value"], 15.0)


class AdaptCellRowsTest(unittest.TestCase):
    """Adaptador de entrada Samuel: columna `time` -> year/month, NaN -> None."""

    def test_date_object_time_converted_to_year_month(self):
        raw_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625,
             "time": date(2000, 3, 1), "value": 12.5, "unit": "degC", "synthetic": True},
        ]
        adapted = prepare.adapt_cell_rows(raw_rows)
        self.assertEqual(adapted[0]["year"], 2000)
        self.assertEqual(adapted[0]["month"], 3)
        self.assertNotIn("time", adapted[0])
        self.assertEqual(adapted[0]["value"], 12.5)

    def test_iso_string_time_converted_to_year_month(self):
        raw_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625,
             "time": "2001-07-15T00:00:00", "value": 20.0, "unit": "degC", "synthetic": True},
        ]
        adapted = prepare.adapt_cell_rows(raw_rows)
        self.assertEqual(adapted[0]["year"], 2001)
        self.assertEqual(adapted[0]["month"], 7)

    def test_nan_value_becomes_none(self):
        raw_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625,
             "time": date(2000, 1, 1), "value": float("nan"), "unit": "degC", "synthetic": True},
        ]
        adapted = prepare.adapt_cell_rows(raw_rows)
        self.assertIsNone(adapted[0]["value"])

    def test_zero_value_is_preserved_not_treated_as_missing(self):
        raw_rows = [
            {"region_id": "CR_PN", "variable": "PRECTOTCORR", "lat": 10.0, "lon": -85.625,
             "time": date(2000, 2, 1), "value": 0.0, "unit": "mm/day", "synthetic": True},
        ]
        adapted = prepare.adapt_cell_rows(raw_rows)
        self.assertEqual(adapted[0]["value"], 0.0)
        self.assertIsNotNone(adapted[0]["value"])

    def test_none_value_stays_none(self):
        raw_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625,
             "time": date(2000, 1, 1), "value": None, "unit": "degC", "synthetic": True},
        ]
        adapted = prepare.adapt_cell_rows(raw_rows)
        self.assertIsNone(adapted[0]["value"])

    def test_original_input_is_not_mutated(self):
        raw_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625,
             "time": date(2000, 3, 1), "value": float("nan"), "unit": "degC", "synthetic": True},
        ]
        before = copy.deepcopy(raw_rows)
        prepare.adapt_cell_rows(raw_rows)
        self.assertEqual(raw_rows, before)
        self.assertIn("time", raw_rows[0])
        self.assertTrue(math.isnan(raw_rows[0]["value"]))

    def test_invalid_time_string_raises(self):
        raw_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625,
             "time": "not-a-date", "value": 1.0, "unit": "degC", "synthetic": True},
        ]
        with self.assertRaises(ValueError):
            prepare.adapt_cell_rows(raw_rows)


class CheckMaskWeightsValidationTest(unittest.TestCase):
    """EMANUEL-03: pesos individuales deben ser finitos y no negativos."""

    def test_negative_weight_raises(self):
        mask_rows = [
            {"region_id": "CR_PN", "lat": 10.0, "lon": -85.625, "weight": -0.25, "mask_version": "test"},
            {"region_id": "CR_PN", "lat": 10.5, "lon": -85.625, "weight": 1.25, "mask_version": "test"},
        ]
        with self.assertRaises(ValueError):
            prepare.check_mask_weights(mask_rows)

    def test_nan_weight_raises(self):
        mask_rows = [
            {"region_id": "CR_PN", "lat": 10.0, "lon": -85.625, "weight": float("nan"), "mask_version": "test"},
            {"region_id": "CR_PN", "lat": 10.5, "lon": -85.625, "weight": 1.0, "mask_version": "test"},
        ]
        with self.assertRaises(ValueError):
            prepare.check_mask_weights(mask_rows)

    def test_infinite_weight_raises(self):
        mask_rows = [
            {"region_id": "CR_PN", "lat": 10.0, "lon": -85.625, "weight": float("inf"), "mask_version": "test"},
            {"region_id": "CR_PN", "lat": 10.5, "lon": -85.625, "weight": 1.0, "mask_version": "test"},
        ]
        with self.assertRaises(ValueError):
            prepare.check_mask_weights(mask_rows)

    def test_zero_weight_is_valid_not_negative(self):
        mask_rows = [
            {"region_id": "CR_PN", "lat": 10.0, "lon": -85.625, "weight": 0.0, "mask_version": "test"},
            {"region_id": "CR_PN", "lat": 10.5, "lon": -85.625, "weight": 1.0, "mask_version": "test"},
            {"region_id": "CR_CAR", "lat": 9.5, "lon": -83.75, "weight": 0.5, "mask_version": "test"},
            {"region_id": "CR_CAR", "lat": 9.5, "lon": -83.125, "weight": 0.5, "mask_version": "test"},
        ]
        prepare.check_mask_weights(mask_rows)  # no debe lanzar


class RunQcTest(unittest.TestCase):
    def setUp(self):
        self.mask_rows = [
            {"region_id": "CR_PN", "lat": 10.0, "lon": -85.625, "weight": 0.25, "mask_version": "test"},
            {"region_id": "CR_PN", "lat": 10.5, "lon": -85.625, "weight": 0.75, "mask_version": "test"},
            {"region_id": "CR_CAR", "lat": 9.5, "lon": -83.75, "weight": 0.5, "mask_version": "test"},
            {"region_id": "CR_CAR", "lat": 9.5, "lon": -83.125, "weight": 0.5, "mask_version": "test"},
        ]

    def test_run_qc_reports_missing_months_without_raising(self):
        cell_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625, "year": 2000, "month": 1,
             "value": 10.0, "unit": "degC", "synthetic": True},
        ]
        report = prepare.run_qc(cell_rows, self.mask_rows, start_year=2000, end_year=2000)
        self.assertTrue(report["duplicates_ok"])
        self.assertGreater(report["cells_with_any_gap"], 0)

    def test_run_qc_raises_on_sentinel_value(self):
        cell_rows = [
            {"region_id": "CR_PN", "variable": "T2M", "lat": 10.0, "lon": -85.625, "year": 2000, "month": 1,
             "value": -999.0, "unit": "degC", "synthetic": True},
        ]
        with self.assertRaises(ValueError):
            prepare.run_qc(cell_rows, self.mask_rows, start_year=2000, end_year=2000)

    def test_run_qc_raises_on_bad_mask_weights(self):
        bad_masks = [{"region_id": "CR_PN", "lat": 10.0, "lon": -85.625, "weight": 0.5, "mask_version": "test"}]
        with self.assertRaises(ValueError):
            prepare.run_qc([], bad_masks, start_year=2000, end_year=2000)


if __name__ == "__main__":
    unittest.main()
